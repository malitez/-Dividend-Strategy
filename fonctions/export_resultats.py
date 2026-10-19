"""Export des résultats : CSV (Excel FR), JSON, HTML, rapport complet."""
from __future__ import annotations

import html
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from fonctions.calcul_metriques import COL_RATIO, COL_SCORE
from fonctions.recuperation_donnees import DATA_DIR

_STARS = {"Excellent": "⭐⭐⭐⭐", "Bon": "⭐⭐⭐", "Moyen": "⭐⭐", "Faible": "⭐", "N/A": "–"}


def _resolve(filename: str, ext: str) -> Path:
    """Nom simple -> data/<nom>.<ext> ; chemin avec dossier -> utilisé tel quel."""
    path = Path(filename).expanduser()
    if path.suffix.lower() != f".{ext}":
        path = path.with_name(path.name + f".{ext}")
    if path.parent == Path("."):
        path = DATA_DIR / path.name
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def export_csv(df: pd.DataFrame, filename: str) -> Path:
    """CSV pour Excel français : séparateur ';', décimale ',', UTF-8 avec BOM."""
    path = _resolve(filename, "csv")
    df.round(4).to_csv(path, index=False, sep=";", decimal=",", encoding="utf-8-sig")
    return path


def export_json(df: pd.DataFrame, filename: str) -> Path:
    """JSON : liste d'objets (NaN -> null)."""
    path = _resolve(filename, "json")
    records = json.loads(df.round(4).to_json(orient="records", force_ascii=False))
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def export_html(df: pd.DataFrame, filename: str, title: str = "Sélecteur d'Actions Dividendes",
                subtitle: str = "") -> Path:
    """Rapport HTML autonome (CSS inclus, aucune dépendance)."""
    path = _resolve(filename, "html")
    head = "".join(f"<th>{html.escape(str(c))}</th>" for c in ["#"] + list(df.columns))
    body = []
    for i, rec in enumerate(df.to_dict("records"), start=1):
        cells = [f"<td>{i}</td>"]
        for col, val in rec.items():
            if col == COL_SCORE:
                label = str(val)
                cells.append(f'<td class="s-{html.escape(label)}">{_STARS.get(label, "")} {html.escape(label)}</td>')
            elif isinstance(val, float):
                txt = "-" if not math.isfinite(val) else (f"{val:.4f}" if col == COL_RATIO else f"{val:.2f}")
                cells.append(f'<td class="num">{txt}</td>')
            else:
                cells.append(f"<td>{html.escape(str(val))}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")

    page = f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
body{{font-family:system-ui,sans-serif;background:#0d1117;color:#e6edf3;margin:2rem}}
h1{{margin-bottom:.2rem}} .sub{{color:#8b949e;margin-bottom:1.5rem}}
.wrap{{overflow-x:auto}}
table{{border-collapse:collapse;min-width:60%}}
th,td{{padding:.5rem .9rem;border-bottom:1px solid #30363d;text-align:left}}
th{{background:#161b22;position:sticky;top:0}} td.num{{text-align:right;font-variant-numeric:tabular-nums}}
tr:hover{{background:#161b22}}
.s-Excellent{{color:#3fb950}} .s-Bon{{color:#58a6ff}} .s-Moyen{{color:#d29922}} .s-Faible{{color:#f85149}}
footer{{margin-top:1.5rem;color:#8b949e;font-size:.85rem}}
</style></head><body>
<h1>{html.escape(title)}</h1>
<div class="sub">{html.escape(subtitle)} — généré le {datetime.now():%d/%m/%Y %H:%M}</div>
<div class="wrap"><table><thead><tr>{head}</tr></thead><tbody>
{"".join(body)}
</tbody></table></div>
<footer>Ratio Q = Rendement % / Volatilité % annualisée. Ceci n'est pas un conseil en investissement.</footer>
</body></html>"""
    path.write_text(page, encoding="utf-8")
    return path


def generate_report(portfolio, strategy, basename: Optional[str] = None) -> Dict[str, Path]:
    """Rapport complet : CSV + JSON + HTML du résultat courant de la stratégie.

    Retourne {'csv': Path, 'json': Path, 'html': Path}.
    """
    df = strategy.run_analysis(portfolio)
    name = basename or f"dividendes_{datetime.now():%Y%m%d_%H%M%S}"
    return {
        "csv": export_csv(df, name),
        "json": export_json(df, name),
        "html": export_html(df, name, subtitle=strategy.describe()),
    }
