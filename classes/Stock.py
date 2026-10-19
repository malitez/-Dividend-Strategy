"""Classe Stock : une action et ses métriques."""
from __future__ import annotations

import math
from typing import Any, Dict, Optional

import pandas as pd

from fonctions.calcul_metriques import (
    COL_DIV, COL_PRICE, COL_RATIO, COL_SCORE, COL_TICKER, COL_VOL, COL_YIELD,
    MIN_HISTORY_POINTS, calculate_dividend_yield, calculate_quality_ratio,
    calculate_volatility, score_label,
)


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


class Stock:
    """Représente une action individuelle.

    Attributs:
        ticker: code de l'action (ex: "MC.PA").
        current_price: prix actuel.
        annual_dividend: dividende annuel (par action).
        history: DataFrame OHLC (au moins la colonne 'Close').
        dividend_yield: rendement en % (calculé).
        volatility: volatilité annualisée en % (calculée).
        quality_ratio: rendement / volatilité (calculé).
    """

    def __init__( self, ticker: str, price: float, dividend: float, history: Optional[pd.DataFrame] = None,) -> None:
        self.ticker: str = str(ticker).strip().upper()
        self.current_price: float = _to_float(price)
        self.annual_dividend: float = _to_float(dividend)
        self.history: pd.DataFrame = history if history is not None else pd.DataFrame()
        self.dividend_yield: float = math.nan
        self.volatility: float = math.nan
        self.quality_ratio: float = math.nan

    def calculate_metrics(self) -> None:
        """Calcule rendement, volatilité puis ratio qualité (dans cet ordre)."""
        self.dividend_yield = calculate_dividend_yield(self.annual_dividend, self.current_price)
        self.volatility = calculate_volatility(self.history)
        self.quality_ratio = calculate_quality_ratio(self.dividend_yield, self.volatility)

    def is_valid(self) -> bool:
        """True si les données d'entrée ET les métriques sont complètes et finies."""
        if not self.ticker:
            return False
        if not (math.isfinite(self.current_price) and self.current_price > 0):
            return False
        if not (math.isfinite(self.annual_dividend) and self.annual_dividend >= 0):
            return False
        if self.history is None or "Close" not in self.history.columns:
            return False
        if len(self.history) <= MIN_HISTORY_POINTS:
            return False
        return all(
            math.isfinite(m)
            for m in (self.dividend_yield, self.volatility, self.quality_ratio)
        )

    def get_summary(self) -> Dict[str, Any]:
        """Dict avec toutes les métriques (clés = noms de colonnes du tableau)."""
        return {
            COL_TICKER: self.ticker,
            COL_PRICE: self.current_price,
            COL_DIV: self.annual_dividend,
            COL_YIELD: self.dividend_yield,
            COL_VOL: self.volatility,
            COL_RATIO: self.quality_ratio,
            COL_SCORE: score_label(self.quality_ratio),
        }

    def __repr__(self) -> str:
        return (f"Stock({self.ticker}, prix={self.current_price:.2f}, "
                f"rdt={self.dividend_yield:.2f}%, vol={self.volatility:.2f}%)")
