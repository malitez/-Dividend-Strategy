"""Classe Portfolio : collection d'actions analysées."""
from __future__ import annotations

from typing import List, Optional

import pandas as pd

from classes.Stock import Stock
from fonctions.calcul_metriques import COL_RATIO, LOWER_IS_BETTER, RESULT_COLUMNS, COL_YIELD, COL_VOL


class Portfolio:
    """Gère une liste de Stock et expose un DataFrame consolidé.

    Attributs:
        stocks: liste d'objets Stock valides.
        df_results: DataFrame consolidé (reconstruit à la demande).
    """

    def __init__(self) -> None:
        self.stocks: List[Stock] = []
        self._df: Optional[pd.DataFrame] = None

    def add_stock(self, stock: Stock) -> bool:
        """Ajoute une action. Calcule ses métriques si besoin.

        Retourne False (et n'ajoute rien) si l'action est invalide.
        Un ticker déjà présent est remplacé.
        """
        if not isinstance(stock, Stock):
            raise TypeError("add_stock attend un objet Stock")
        stock.calculate_metrics()
        if not stock.is_valid():
            return False
        self.stocks = [s for s in self.stocks if s.ticker != stock.ticker]
        self.stocks.append(stock)
        self._df = None  # invalide le cache du DataFrame
        return True

    @property
    def df_results(self) -> pd.DataFrame:
        """DataFrame consolidé, une ligne par action."""
        if self._df is None:
            rows = [s.get_summary() for s in self.stocks]
            self._df = pd.DataFrame(rows, columns=RESULT_COLUMNS)
        return self._df

    def filter_by_yield(self, min_yield: float) -> pd.DataFrame:
        """Actions avec rendement >= min_yield (%)."""
        df = self.df_results
        return df[df[COL_YIELD] >= min_yield].reset_index(drop=True)

    def filter_by_volatility(self, max_vol: float) -> pd.DataFrame:
        """Actions avec volatilité <= max_vol (%)."""
        df = self.df_results
        return df[df[COL_VOL] <= max_vol].reset_index(drop=True)

    def sort_by(self, column: str, ascending: Optional[bool] = None) -> pd.DataFrame:
        """Trie par colonne. Par défaut : meilleur en premier
        (décroissant, sauf Volatilité % où le plus bas est le meilleur)."""
        df = self.df_results
        if column not in df.columns:
            raise ValueError(f"Colonne inconnue: {column}")
        if ascending is None:
            ascending = column in LOWER_IS_BETTER
        return df.sort_values(column, ascending=ascending).reset_index(drop=True)

    def get_top_n(self, n: int, metric: str = COL_RATIO) -> pd.DataFrame:
        """Les N meilleures actions selon une métrique."""
        if n <= 0:
            raise ValueError("n doit être > 0")
        return self.sort_by(metric).head(n).reset_index(drop=True)

    def __len__(self) -> int:
        return len(self.stocks)
