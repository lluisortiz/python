import re
from typing import Any, Dict, List, Optional, Tuple

from utils import get_route_position_km, point_to_route_distance_meters

# ---------------------------------------------------------------------------
# Mapillary object_value substrings that indicate speed-related signs
# ---------------------------------------------------------------------------
_SPEED_PATTERNS = (
    "maximum-speed-limit",
    "minimum-speed-limit",
    "advisory-maximum-speed-limit",
    "advisory-minimum-speed-limit",
    "end-of-maximum-speed-limit",
    "end-of-minimum-speed-limit",
    "end-of-speed-limit",
    "speed-limit",
    "speed-zone",
    "variable-speed",
)

# Human-readable label per object_value prefix (longest match wins)
_SIGN_LABELS: List[Tuple[str, str]] = [
    ("regulatory--end-of-maximum-speed-limit",    "Fin velocidad máxima"),
    ("regulatory--end-of-minimum-speed-limit",    "Fin velocidad mínima"),
    ("regulatory--end-of-speed-limit",            "Fin limitación velocidad"),
    ("regulatory--maximum-speed-limit",           "Velocidad máxima"),
    ("regulatory--minimum-speed-limit",           "Velocidad mínima"),
    ("regulatory--advisory-maximum-speed-limit",  "Velocidad máxima recomendada"),
    ("regulatory--advisory-minimum-speed-limit",  "Velocidad mínima recomendada"),
    ("complementary--maximum-speed-limit",        "Velocidad máxima (panel)"),
    ("complementary--minimum-speed-limit",        "Velocidad mínima (panel)"),
    ("warning--speed-bump",                       "Resalto / badén"),
    ("warning--speed-zone",                       "Zona de velocidad reducida"),
]


def is_speed_signal(object_value: str) -> bool:
    """Return True if the Mapillary object_value represents a speed sign."""
    ov = object_value.lower()
    return any(p in ov for p in _SPEED_PATTERNS)


def extract_speed_kmh(object_value: str) -> Optional[int]:
    """
    Parse the numeric speed from an object_value string.
    'regulatory--maximum-speed-limit-50--g1'  →  50
    Returns None when no number is found.
    """
    m = re.search(r"(?:limit|zone)-(\d+)(?:--|\Z)", object_value)
    return int(m.group(1)) if m else None


def sign_label(object_value: str) -> str:
    """Return a human-readable Spanish label for the sign type."""
    for prefix, label in _SIGN_LABELS:
        if object_value.startswith(prefix):
            return label
    # Generic fallback: prettify the raw value
    parts = object_value.split("--")
    if len(parts) >= 2:
        return f"{parts[0].capitalize()}: {parts[1].replace('-', ' ')}"
    return object_value


def mapillary_url(feature_id: str) -> str:
    return f"https://www.mapillary.com/map/signs/{feature_id}"


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def filter_speed_signals(
    features: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Keep only speed-related features from a raw Mapillary feature list."""
    return [f for f in features if is_speed_signal(f.get("object_value", ""))]


def find_signals_along_route(
    route: List[Tuple[float, float]],
    signals: List[Dict[str, Any]],
    radius_meters: float = 50.0,
) -> List[Dict[str, Any]]:
    """
    Filter speed signals to those within *radius_meters* of the route and
    return them sorted by their position (km) along the route.

    Each returned dict contains:
        id, lat, lon, object_value, sign_type, speed_kmh,
        distance_from_route_m, position_km,
        first_seen, last_seen, mapillary_url
    """
    results: List[Dict[str, Any]] = []

    for feature in signals:
        geom = feature.get("geometry", {})
        if geom.get("type") != "Point":
            continue
        coords = geom.get("coordinates", [])
        if len(coords) < 2:
            continue

        # Mapillary returns [longitude, latitude]
        lon, lat = float(coords[0]), float(coords[1])

        dist_m, _ = point_to_route_distance_meters(lat, lon, route)
        if dist_m > radius_meters:
            continue

        ov = feature.get("object_value", "")
        results.append({
            "id":                    feature.get("id", ""),
            "lat":                   lat,
            "lon":                   lon,
            "object_value":          ov,
            "sign_type":             sign_label(ov),
            "speed_kmh":             extract_speed_kmh(ov),
            "distance_from_route_m": round(dist_m, 1),
            "position_km":           round(get_route_position_km(lat, lon, route), 2),
            "first_seen":            feature.get("first_seen_at", ""),
            "last_seen":             feature.get("last_seen_at", ""),
            "mapillary_url":         mapillary_url(feature.get("id", "")),
        })

    results.sort(key=lambda x: x["position_km"])
    return results
