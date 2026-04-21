from math import radians, cos, sin, asin, sqrt
from typing import List, Tuple


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in meters between two GPS coordinates."""
    R = 6_371_000.0
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * R * asin(sqrt(a))


def _point_to_segment_dist_m(
    px: float, py: float,   # point   (projected metres)
    ax: float, ay: float,   # segment start
    bx: float, by: float,   # segment end
) -> float:
    """Euclidean distance from point P to segment AB (all in metres)."""
    dx, dy = bx - ax, by - ay
    if dx == 0.0 and dy == 0.0:
        return sqrt((px - ax) ** 2 + (py - ay) ** 2)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    cx, cy = ax + t * dx, ay + t * dy
    return sqrt((px - cx) ** 2 + (py - cy) ** 2)


def point_to_route_distance_meters(
    point_lat: float, point_lon: float,
    route: List[Tuple[float, float]],
) -> Tuple[float, int]:
    """
    Minimum distance from a GPS point to a route polyline.
    Returns (distance_metres, index_of_nearest_segment).
    Uses a flat-Earth projection centred on each segment for accuracy.
    """
    min_dist = float("inf")
    nearest_seg = 0

    for i in range(len(route) - 1):
        lat1, lon1 = route[i]
        lat2, lon2 = route[i + 1]

        mid_lat = (lat1 + lat2 + point_lat) / 3.0
        lat_scale = 111_320.0
        lon_scale = 111_320.0 * cos(radians(mid_lat))

        # Project everything relative to segment start
        px = (point_lon - lon1) * lon_scale
        py = (point_lat - lat1) * lat_scale
        bx = (lon2 - lon1) * lon_scale
        by = (lat2 - lat1) * lat_scale

        dist = _point_to_segment_dist_m(px, py, 0.0, 0.0, bx, by)
        if dist < min_dist:
            min_dist = dist
            nearest_seg = i

    return min_dist, nearest_seg


def get_route_position_km(
    point_lat: float, point_lon: float,
    route: List[Tuple[float, float]],
) -> float:
    """Approximate km position along the route for the nearest point."""
    _, nearest_seg = point_to_route_distance_meters(point_lat, point_lon, route)
    total = 0.0
    for i in range(nearest_seg):
        total += haversine(route[i][0], route[i][1], route[i + 1][0], route[i + 1][1])
    return total / 1000.0


def get_bounding_box(
    points: List[Tuple[float, float]],
    padding: float = 0.001,
) -> Tuple[float, float, float, float]:
    """Return (west, south, east, north) bounding box for a set of GPS points."""
    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    return (
        min(lons) - padding,
        min(lats) - padding,
        max(lons) + padding,
        max(lats) + padding,
    )


def split_route_into_segments(
    route: List[Tuple[float, float]],
    max_segment_km: float = 5.0,
) -> List[List[Tuple[float, float]]]:
    """
    Split a route into overlapping chunks of at most max_segment_km km.
    Adjacent chunks share their boundary point to avoid gaps.
    """
    if not route:
        return []

    segments: List[List[Tuple[float, float]]] = []
    current: List[Tuple[float, float]] = [route[0]]
    current_km = 0.0

    for i in range(1, len(route)):
        lat1, lon1 = route[i - 1]
        lat2, lon2 = route[i]
        current_km += haversine(lat1, lon1, lat2, lon2) / 1000.0
        current.append(route[i])

        if current_km >= max_segment_km:
            segments.append(current)
            current = [route[i]]
            current_km = 0.0

    if len(current) > 1:
        segments.append(current)
    elif segments:
        segments[-1].append(current[0])

    return segments


def calculate_route_total_km(route: List[Tuple[float, float]]) -> float:
    """Total length of the route in kilometres."""
    total = 0.0
    for i in range(len(route) - 1):
        total += haversine(route[i][0], route[i][1], route[i + 1][0], route[i + 1][1])
    return total / 1000.0
