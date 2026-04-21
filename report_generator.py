import csv
import json
import os
from datetime import datetime
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Text (console)
# ---------------------------------------------------------------------------

def generate_text_report(
    signals: List[Dict[str, Any]],
    route_total_km: float,
    source_file: str,
) -> str:
    sep = "=" * 72
    lines = [
        sep,
        "  SEÑALES DE VELOCIDAD DETECTADAS EN LA RUTA",
        sep,
        f"  Archivo  : {os.path.basename(source_file)}",
        f"  Longitud : {route_total_km:.1f} km",
        f"  Señales  : {len(signals)}",
        f"  Fecha    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        sep,
        "",
    ]

    if not signals:
        lines.append("  No se encontraron señales de velocidad en esta ruta.")
        return "\n".join(lines)

    header = f"{'PK(km)':<9} {'Tipo de señal':<36} {'km/h':<6} {'Dist(m)':<9} Coordenadas"
    lines += [header, "-" * 72]

    for s in signals:
        speed = str(s["speed_kmh"]) if s["speed_kmh"] is not None else "—"
        coords = f"{s['lat']:.5f}, {s['lon']:.5f}"
        lines.append(
            f"{s['position_km']:<9.2f}"
            f"{s['sign_type'][:35]:<36}"
            f"{speed:<6}"
            f"{s['distance_from_route_m']:<9.0f}"
            f"{coords}"
        )

    lines += [
        "",
        f"  Fuente: Mapillary  https://www.mapillary.com",
        sep,
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

_CSV_FIELDS = [
    "position_km", "sign_type", "speed_kmh", "distance_from_route_m",
    "lat", "lon", "first_seen", "last_seen", "object_value",
    "mapillary_url", "id",
]


def save_csv_report(signals: List[Dict[str, Any]], output_path: str) -> None:
    with open(output_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(signals)
    print(f"  CSV guardado  : {output_path}")


# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------

def save_json_report(signals: List[Dict[str, Any]], output_path: str) -> None:
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(signals, fh, ensure_ascii=False, indent=2, default=str)
    print(f"  JSON guardado : {output_path}")


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

def save_html_report(
    signals: List[Dict[str, Any]],
    route_total_km: float,
    source_file: str,
    output_path: str,
) -> None:
    rows = ""
    for s in signals:
        speed_str = f"{s['speed_kmh']} km/h" if s["speed_kmh"] is not None else "—"
        gmaps = f"https://maps.google.com/?q={s['lat']},{s['lon']}"
        rows += (
            f"<tr>"
            f"<td>{s['position_km']:.2f}</td>"
            f"<td>{_esc(s['sign_type'])}</td>"
            f"<td class='sp'>{speed_str}</td>"
            f"<td>{s['distance_from_route_m']:.0f}</td>"
            f"<td>{s['lat']:.5f}, {s['lon']:.5f}</td>"
            f"<td>"
            f"<a href='{s['mapillary_url']}' target='_blank'>Mapillary</a> · "
            f"<a href='{gmaps}' target='_blank'>Maps</a>"
            f"</td>"
            f"</tr>\n"
        )

    no_data = "" if signals else "<tr><td colspan='6' class='empty'>Sin señales encontradas</td></tr>"

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Señales de velocidad — {_esc(os.path.basename(source_file))}</title>
<style>
  body{{font-family:Arial,sans-serif;margin:24px;background:#f4f6f9;color:#222}}
  h1{{margin-bottom:4px;color:#1a252f}}
  .meta{{background:#ddeeff;border-radius:6px;padding:14px 18px;margin-bottom:20px;font-size:.95em;line-height:1.7}}
  table{{width:100%;border-collapse:collapse;background:#fff;border-radius:6px;overflow:hidden;
         box-shadow:0 1px 4px rgba(0,0,0,.12)}}
  th{{background:#1a252f;color:#fff;padding:11px 13px;text-align:left;font-size:.9em}}
  td{{padding:9px 13px;border-bottom:1px solid #eef;font-size:.9em}}
  tr:last-child td{{border-bottom:none}}
  tr:hover td{{background:#f0f8ff}}
  .sp{{font-weight:700;color:#c0392b;font-size:1.05em}}
  a{{color:#2471a3;text-decoration:none}}
  a:hover{{text-decoration:underline}}
  .empty{{text-align:center;padding:30px;color:#777}}
  .foot{{margin-top:16px;font-size:.82em;color:#666}}
</style>
</head>
<body>
<h1>Señales de velocidad en la ruta</h1>
<div class="meta">
  <b>Archivo:</b> {_esc(os.path.basename(source_file))}&nbsp;&nbsp;|&nbsp;&nbsp;
  <b>Longitud:</b> {route_total_km:.1f} km&nbsp;&nbsp;|&nbsp;&nbsp;
  <b>Señales:</b> {len(signals)}&nbsp;&nbsp;|&nbsp;&nbsp;
  <b>Generado:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
</div>
<table>
  <thead>
    <tr>
      <th>PK (km)</th><th>Tipo de señal</th><th>Velocidad</th>
      <th>Dist. ruta (m)</th><th>Coordenadas</th><th>Enlace</th>
    </tr>
  </thead>
  <tbody>
    {rows}{no_data}
  </tbody>
</table>
<div class="foot">
  Datos obtenidos de <a href="https://www.mapillary.com" target="_blank">Mapillary</a>
</div>
</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"  HTML guardado : {output_path}")


def _esc(text: str) -> str:
    """Minimal HTML escaping."""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
    )
