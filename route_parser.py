import os
import zipfile
from typing import List, Tuple
from xml.etree import ElementTree as ET

try:
    import gpxpy
    _HAS_GPXPY = True
except ImportError:
    _HAS_GPXPY = False


def parse_file(filepath: str) -> List[Tuple[float, float]]:
    """
    Parse a GPX, KML or KMZ file and return a list of (lat, lon) tuples.
    Raises ValueError for unsupported formats or empty routes.
    """
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Archivo no encontrado: {filepath}")

    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".gpx":
        points = _parse_gpx(filepath)
    elif ext == ".kml":
        with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
            points = _parse_kml_text(fh.read())
    elif ext == ".kmz":
        points = _parse_kmz(filepath)
    else:
        raise ValueError(f"Formato no soportado: '{ext}'. Usa .gpx, .kml o .kmz")

    if not points:
        raise ValueError("No se encontraron coordenadas en el archivo.")

    return points


# ---------------------------------------------------------------------------
# GPX
# ---------------------------------------------------------------------------

def _parse_gpx(filepath: str) -> List[Tuple[float, float]]:
    if _HAS_GPXPY:
        return _parse_gpx_gpxpy(filepath)
    return _parse_gpx_etree(filepath)


def _parse_gpx_gpxpy(filepath: str) -> List[Tuple[float, float]]:
    with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
        gpx = gpxpy.parse(fh)

    points: List[Tuple[float, float]] = []

    for track in gpx.tracks:
        for segment in track.segments:
            for pt in segment.points:
                points.append((pt.latitude, pt.longitude))

    if not points:
        for route in gpx.routes:
            for pt in route.points:
                points.append((pt.latitude, pt.longitude))

    if not points:
        for wpt in gpx.waypoints:
            points.append((wpt.latitude, wpt.longitude))

    return points


def _parse_gpx_etree(filepath: str) -> List[Tuple[float, float]]:
    """Fallback GPX parser using the standard library."""
    tree = ET.parse(filepath)
    root = tree.getroot()
    ns = _xml_namespace(root)

    points: List[Tuple[float, float]] = []

    for tag in (f"{ns}trkpt", f"{ns}rtept", f"{ns}wpt"):
        for elem in root.iter(tag):
            try:
                lat = float(elem.get("lat"))
                lon = float(elem.get("lon"))
                points.append((lat, lon))
            except (TypeError, ValueError):
                continue
        if points:
            break

    return points


# ---------------------------------------------------------------------------
# KML / KMZ
# ---------------------------------------------------------------------------

def _parse_kmz(filepath: str) -> List[Tuple[float, float]]:
    with zipfile.ZipFile(filepath, "r") as kmz:
        kml_names = [n for n in kmz.namelist() if n.lower().endswith(".kml")]
        if not kml_names:
            raise ValueError("El archivo KMZ no contiene ningún .kml.")
        main_kml = "doc.kml" if "doc.kml" in kml_names else kml_names[0]
        raw = kmz.read(main_kml).decode("utf-8", errors="replace")
    return _parse_kml_text(raw)


def _parse_kml_text(kml_text: str) -> List[Tuple[float, float]]:
    root = ET.fromstring(kml_text)
    ns = _xml_namespace(root)

    line_points: List[Tuple[float, float]] = []
    point_points: List[Tuple[float, float]] = []

    for coords_elem in root.iter(f"{ns}coordinates"):
        text = (coords_elem.text or "").strip()
        if not text:
            continue
        parsed = _parse_kml_coord_string(text)
        if len(parsed) > 1:
            line_points.extend(parsed)
        else:
            point_points.extend(parsed)

    # Prefer line geometries (tracks / routes) over individual points
    return line_points if line_points else point_points


def _parse_kml_coord_string(text: str) -> List[Tuple[float, float]]:
    """
    Parse KML coordinate strings: 'lon,lat[,alt] lon,lat[,alt] ...'
    Returns (lat, lon) tuples.
    """
    points: List[Tuple[float, float]] = []
    for token in text.split():
        parts = token.split(",")
        if len(parts) < 2:
            continue
        try:
            lon = float(parts[0])
            lat = float(parts[1])
            if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                points.append((lat, lon))
        except ValueError:
            continue
    return points


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _xml_namespace(element: ET.Element) -> str:
    """Extract the '{namespace}' prefix from an XML element tag, or ''."""
    tag = element.tag
    if tag.startswith("{"):
        return tag[: tag.index("}") + 1]
    return ""
