"""Affichage terminal (tableau coloré) et filtrage/tri de DataFrames."""
from __future__ import annotations

import math
import os
import sys
from typing import List, Optional

import pandas as pd

from fonctions.calcul_metriques import (
    COL_DIV, COL_PRICE, COL_RATIO, COL_SCORE, COL_TICKER, COL_VOL, COL_YIELD,
    LOWER_IS_BETTER,
)

_ANSI = {"reset": "\033[0m", "bold": "\033[1m", "green": "\033[92m",
         "yellow": "\033[93m", "red": "\033[91m", "cyan": "\033[96m", "dim": "\033[2m"}
_SCORE_COLOR = {"Excellent": "green", "Bon": "cyan", "Moyen": "yellow", "Faible": "red"}


def _use_color() -> bool:
    return sys.stdout.isatty() and "NO_COLOR" not in os.environ


def _paint(text: str, color: str) -> str:
    if not _use_color() or color not in _ANSI:
        return text
    return f"{_ANSI[color]}{text}{_ANSI['reset']}"


def filter_results(df: pd.DataFrame, min_yield: float = 0, max_volatility: float = 100) -> pd.DataFrame:
    """Garde rendement >= min_yield ET volatilité <= max_volatility."""
    mask = (df[COL_YIELD] >= min_yield) & (df[COL_VOL] <= max_volatility)
    return df[mask].reset_index(drop=True)


def sort_results(df: pd.DataFrame, sort_by: str = COL_RATIO, ascending: Optional[bool] = None) -> pd.DataFrame:
    """Trie par colonne. ascending=None -> meilleur d'abord (volatilité: croissant)."""
    if sort_by not in df.columns:
        raise ValueError(f"Colonne inconnue: {sort_by}")
    if ascending is None:
        ascending = sort_by in LOWER_IS_BETTER
    return df.sort_values(sort_by, ascending=ascending).reset_index(drop=True)


def _fmt(col: str, value) -> str:
    if col == COL_RATIO:
        return f"{value:.4f}" if isinstance(value, float) and math.isfinite(value) else "-"
    if col in (COL_PRICE, COL_DIV, COL_YIELD, COL_VOL):
        return f"{value:.2f}" if isinstance(value, (int, float)) and math.isfinite(value) else "-"
    return str(value)


def print_table(df: pd.DataFrame) -> None:
    """Tableau console aligné ; la colonne Score est colorée (si terminal couleur)."""
    if df.empty:
        print(_paint("Aucune action ne correspond aux critères.", "yellow"))
        return

    cols: List[str] = list(df.columns)
    headers = ["#"] + cols
    rows = [[str(i)] + [_fmt(c, v) for c, v in zip(cols, rec)]
            for i, rec in enumerate(df.itertuples(index=False, name=None), start=1)]
    widths = [max(len(h), *(len(r[j]) for r in rows)) for j, h in enumerate(headers)]
    left = {0: False, **{j + 1: c in (COL_TICKER, COL_SCORE) for j, c in enumerate(cols)}}

    def pad(text: str, j: int) -> str:
        return text.ljust(widths[j]) if left[j] else text.rjust(widths[j])

    print(_paint("  ".join(pad(h, j) for j, h in enumerate(headers)), "bold"))
    print(_paint("  ".join("─" * w for w in widths), "dim"))
    for r in rows:
        cells = []
        for j, text in enumerate(r):
            cell = pad(text, j)
            if headers[j] in (COL_SCORE, COL_RATIO):
                cell = _paint(cell, _SCORE_COLOR.get(r[headers.index(COL_SCORE)], ""))
            cells.append(cell)
        print("  ".join(cells))


def display_results(df: pd.DataFrame, title: str = "Résultats") -> None:
    """Titre encadré + tableau + nombre de lignes."""
    print()
    print(_paint(f"═══ {title} ═══", "bold"))
    print_table(df)
    print(_paint(f"\n{len(df)} action(s) affichée(s)", "dim"))


def display_with_filters(df: pd.DataFrame, min_yield: float, max_volatility: float,
                         sort_by: str) -> pd.DataFrame:
    """Filtre + trie + affiche. Retourne le DataFrame affiché."""
    out = sort_results(filter_results(df, min_yield, max_volatility), sort_by)
    display_results(out, f"Rendement ≥ {min_yield:g}% | Volatilité ≤ {max_volatility:g}% | Tri: {sort_by}")
    return out
