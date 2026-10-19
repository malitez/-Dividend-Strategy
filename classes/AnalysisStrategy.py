"""Classe AnalysisStrategy : encapsule les critères de sélection."""
from __future__ import annotations

from typing import List, Optional

import pandas as pd

from classes.Portfolio import Portfolio
from fonctions.affichage_filtrage import filter_results, sort_results
from fonctions.calcul_metriques import COL_RATIO, RESULT_COLUMNS


class AnalysisStrategy:
    """Stratégie : filtre (rendement mini, volatilité maxi) puis tri.

    Attributs:
        min_yield: rendement minimum (%).
        max_volatility: volatilité maximum (%).
        sort_metric: colonne de tri.
        tickers_list: tickers à analyser (informatif, utilisé par main.py).
    """

    def __init__( self, min_yield: float = 0, max_volatility: float = 100, sort_metric: str = COL_RATIO, tickers_list: Optional[List[str]] = None,) -> None:
        if sort_metric not in RESULT_COLUMNS:
            raise ValueError(f"sort_metric inconnu: {sort_metric}")
        if min_yield < 0 or max_volatility <= 0:
            raise ValueError("min_yield doit être >= 0 et max_volatility > 0")
        self.min_yield = float(min_yield)
        self.max_volatility = float(max_volatility)
        self.sort_metric = sort_metric
        self.tickers_list: List[str] = list(tickers_list) if tickers_list else []
        self._result: Optional[pd.DataFrame] = None

    def run_analysis(self, portfolio: Portfolio) -> pd.DataFrame:
        """Applique filtre + tri au portfolio et mémorise le résultat."""
        df = filter_results(portfolio.df_results, self.min_yield, self.max_volatility)
        self._result = sort_results(df, self.sort_metric)
        return self._result

    def get_recommendation(self, top_n: Optional[int] = None) -> pd.DataFrame:
        """Actions recommandées (résultat de run_analysis), éventuellement top N."""
        if self._result is None:
            raise RuntimeError("Appelez run_analysis(portfolio) avant get_recommendation().")
        return self._result if top_n is None else self._result.head(top_n)

    def describe(self) -> str:
        """Résumé lisible des paramètres (utilisé dans les rapports)."""
        return (f"Rendement ≥ {self.min_yield:g}% | Volatilité ≤ {self.max_volatility:g}% "
                f"| Tri: {self.sort_metric}")
