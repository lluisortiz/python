#!/usr/bin/env python3
"""
Extrae señales de VELOCIDAD de Mapillary a lo largo de una ruta GPS.

Uso:
    python main.py ruta.gpx
    python main.py ruta.kml --radius 100 --format html
    python main.py ruta.kmz --token MLY_xxxxxxxx --output resultado.csv

Variables de entorno:
    MAPILLARY_ACCESS_TOKEN   Token de la API de Mapillary (obligatorio)
"""

import argparse
import os
import sys
from typing import List

from config import (
    BBOX_PADDING_DEGREES,
    DEFAULT_SEARCH_RADIUS_METERS,
    DEFAULT_SEGMENT_LENGTH_KM,
    MAPILLARY_ACCESS_TOKEN,
)
from mapillary_client import MapillaryClient
from report_generator import (
    generate_text_report,
    save_csv_report,
    save_html_report,
    save_json_report,
)
from route_parser import parse_file
from speed_signals import filter_speed_signals, find_signals_along_route
from utils import (
    calculate_route_total_km,
    get_bounding_box,
    split_route_into_segments,
)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="main.py",
        description="Detecta señales de velocidad de Mapillary a lo largo de una ruta GPS.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("route_file", help="Archivo de ruta (.gpx / .kml / .kmz)")
    p.add_argument(
        "--radius", "-r", type=float, default=DEFAULT_SEARCH_RADIUS_METERS,
        metavar="METROS",
        help=f"Radio de búsqueda desde la ruta en metros (default: {DEFAULT_SEARCH_RADIUS_METERS})",
    )
    p.add_argument(
        "--segment-km", "-s", type=float, default=DEFAULT_SEGMENT_LENGTH_KM,
        metavar="KM",
        help=f"Longitud máxima de cada consulta a la API en km (default: {DEFAULT_SEGMENT_LENGTH_KM})",
    )
    p.add_argument(
        "--format", "-f", choices=["text", "csv", "html", "json", "all"],
        default="all",
        help="Formato del reporte de salida (default: all → genera CSV + HTML + JSON)",
    )
    p.add_argument(
        "--output", "-o", metavar="ARCHIVO",
        help="Ruta del archivo de salida (detecta formato por extensión: .csv / .html / .json / .txt)",
    )
    p.add_argument(
        "--token", "-t", metavar="TOKEN",
        help="Token de acceso a la API de Mapillary (sobreescribe MAPILLARY_ACCESS_TOKEN)",
    )
    p.add_argument(
        "--verbose", "-v", action="store_true",
        help="Mostrar información detallada de cada consulta a la API",
    )
    return p


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------

def main() -> None:
    args = _build_parser().parse_args()

    token = args.token or MAPILLARY_ACCESS_TOKEN
    if not token:
        print(
            "ERROR: Falta el token de acceso a Mapillary.\n"
            "  Opción 1: export MAPILLARY_ACCESS_TOKEN=tu_token\n"
            "  Opción 2: python main.py ruta.gpx --token tu_token\n"
            "  Obtén tu token en: https://www.mapillary.com/developer/api-documentation",
            file=sys.stderr,
        )
        sys.exit(1)

    if not os.path.isfile(args.route_file):
        print(f"ERROR: Archivo no encontrado: {args.route_file}", file=sys.stderr)
        sys.exit(1)

    # ------------------------------------------------------------------
    # 1. Parse route
    # ------------------------------------------------------------------
    print(f"\nParsing ruta: {args.route_file} ...", end=" ", flush=True)
    try:
        route = parse_file(args.route_file)
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    if len(route) < 2:
        print(f"\nERROR: La ruta tiene solo {len(route)} punto(s). Se necesitan al menos 2.")
        sys.exit(1)

    total_km = calculate_route_total_km(route)
    print(f"OK  ({len(route)} puntos, {total_km:.1f} km)")

    # ------------------------------------------------------------------
    # 2. Split into query segments
    # ------------------------------------------------------------------
    segments = split_route_into_segments(route, max_segment_km=args.segment_km)
    print(f"Segmentos de consulta : {len(segments)}  (máx. {args.segment_km} km c/u)")
    print(f"Radio de búsqueda     : {args.radius} m")

    # ------------------------------------------------------------------
    # 3. Query Mapillary
    # ------------------------------------------------------------------
    client = MapillaryClient(access_token=token)
    all_features = []
    seen_ids: set = set()

    print(f"\nConsultando Mapillary API ...")
    for idx, segment in enumerate(segments, 1):
        bbox = get_bounding_box(segment, padding=BBOX_PADDING_DEGREES)

        if args.verbose:
            w, s, e, n = bbox
            print(f"  [{idx:>3}/{len(segments)}] bbox=({w:.4f},{s:.4f},{e:.4f},{n:.4f})")
        else:
            pct = idx / len(segments) * 100
            print(f"  {pct:5.1f}%  ({idx}/{len(segments)})", end="\r", flush=True)

        try:
            features = client.get_map_features(bbox=bbox)
        except Exception as exc:
            print(f"\n  Advertencia en segmento {idx}: {exc}")
            continue

        for feat in features:
            fid = feat.get("id")
            if fid and fid not in seen_ids:
                seen_ids.add(fid)
                all_features.append(feat)

    print(f"\nFeatures únicos recibidos  : {len(all_features)}")

    # ------------------------------------------------------------------
    # 4. Filter speed signals
    # ------------------------------------------------------------------
    speed_feats = filter_speed_signals(all_features)
    print(f"Señales de velocidad (API) : {len(speed_feats)}")

    # ------------------------------------------------------------------
    # 5. Keep only signals close to the route
    # ------------------------------------------------------------------
    print("Calculando proximidad a la ruta ...", end=" ", flush=True)
    signals = find_signals_along_route(route, speed_feats, radius_meters=args.radius)
    print(f"OK  →  {len(signals)} señales en la ruta")

    # ------------------------------------------------------------------
    # 6. Text report (always printed to stdout)
    # ------------------------------------------------------------------
    text_report = generate_text_report(signals, total_km, args.route_file)
    print("\n" + text_report)

    if not signals:
        print("No hay señales que exportar.")
        return

    # ------------------------------------------------------------------
    # 7. Save output files
    # ------------------------------------------------------------------
    base = os.path.splitext(args.route_file)[0]

    # If --output given, detect format from extension
    out_fmt = args.format
    if args.output:
        _ext_map = {".csv": "csv", ".html": "html", ".json": "json", ".txt": "text"}
        detected = _ext_map.get(os.path.splitext(args.output)[1].lower())
        if detected:
            out_fmt = detected

    print("\nGuardando reportes:")
    if out_fmt in ("csv", "all"):
        path = args.output if (args.output and out_fmt == "csv") else f"{base}_senales_velocidad.csv"
        save_csv_report(signals, path)

    if out_fmt in ("html", "all"):
        path = args.output if (args.output and out_fmt == "html") else f"{base}_senales_velocidad.html"
        save_html_report(signals, total_km, args.route_file, path)

    if out_fmt in ("json", "all"):
        path = args.output if (args.output and out_fmt == "json") else f"{base}_senales_velocidad.json"
        save_json_report(signals, path)

    if out_fmt == "text":
        path = args.output if args.output else f"{base}_senales_velocidad.txt"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text_report)
        print(f"  TXT guardado  : {path}")

    print("\nHecho.")


if __name__ == "__main__":
    main()
