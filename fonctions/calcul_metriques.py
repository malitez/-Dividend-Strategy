"""Formules mathématiques de la stratégie dividende.

Ce module ne fait ni réseau ni affichage : uniquement du calcul.
Il contient aussi les constantes de colonnes partagées par tout le projet.
"""
from __future__ import annotations

import math
from typing import Iterable, List, Union

import pandas as pd

# --- Constantes partagées -------------------------------------------------
TRADING_DAYS = 252          # nombre de jours de bourse par an (annualisation)
MIN_HISTORY_POINTS = 20     # en dessous, l'écart-type n'est pas fiable

COL_TICKER = "Ticker"
COL_PRICE = "Prix"
COL_DIV = "Div Annuel"
COL_YIELD = "Rendement %"
COL_VOL = "Volatilité %"
COL_RATIO = "Ratio Q"
COL_SCORE = "Score"

RESULT_COLUMNS: List[str] = [
    COL_TICKER, COL_PRICE, COL_DIV, COL_YIELD, COL_VOL, COL_RATIO, COL_SCORE,
]
SORTABLE_COLUMNS: List[str] = [COL_YIELD, COL_VOL, COL_RATIO, COL_PRICE]

# Pour ces colonnes, "meilleur" = plus petit (on veut peu de volatilité).
LOWER_IS_BETTER = {COL_VOL}


def calculate_dividend_yield(annual_dividend: float, current_price: float) -> float:
    """Rendement en dividende (%).

    Formule :  Rendement = (Dividende_annuel / Prix_actuel) x 100

    Exemple : 12,50 € de dividende pour une action à 450,25 € -> 2,78 %.
    Retourne NaN si le prix est invalide (<= 0 ou non numérique).
    """
    try:
        div = float(annual_dividend)
        price = float(current_price)
    except (TypeError, ValueError):
        return math.nan
    if not math.isfinite(div) or not math.isfinite(price) or price <= 0:
        return math.nan
    return div / price * 100.0


def calculate_volatility(
    history_data: Union[pd.DataFrame, pd.Series, None],
    annualize: bool = True,
) -> float:
    """Volatilité (%) = écart-type des rendements journaliers.

    Étapes :
      1. Rendement du jour   r_t = (P_t - P_{t-1}) / P_{t-1}
      2. Écart-type          sigma_jour = std(r_t)   (ddof=1, estimateur non biaisé)
      3. Annualisation       sigma_an = sigma_jour x sqrt(252)

    Pourquoi sqrt(252) ? Si les rendements journaliers sont indépendants, les
    variances s'additionnent : Var(an) = 252 x Var(jour), donc l'écart-type
    est multiplié par sqrt(252) (~15,87).

    Accepte un DataFrame avec une colonne 'Close' ou directement une Series de prix.
    Retourne NaN si l'historique est absent ou trop court.
    """
    if history_data is None:
        return math.nan
    if isinstance(history_data, pd.DataFrame):
        if history_data.empty or "Close" not in history_data.columns:
            return math.nan
        prices = history_data["Close"]
    else:
        prices = history_data

    prices = pd.to_numeric(prices, errors="coerce").dropna()
    prices = prices[prices > 0]
    returns = prices.pct_change().dropna()
    if len(returns) < MIN_HISTORY_POINTS:
        return math.nan

    sigma = float(returns.std(ddof=1))
    if annualize:
        sigma *= math.sqrt(TRADING_DAYS)
    return sigma * 100.0


def calculate_quality_ratio(dividend_yield: float, volatility: float) -> float:
    """Ratio qualité = Rendement / Volatilité (plus haut = meilleur).

    Idée : combien de % de dividende on touche pour chaque % de risque subi.
    Retourne NaN si la volatilité est nulle ou invalide (division impossible).
    """
    try:
        y = float(dividend_yield)
        v = float(volatility)
    except (TypeError, ValueError):
        return math.nan
    if not math.isfinite(y) or not math.isfinite(v) or v <= 0:
        return math.nan
    return y / v


def score_label(ratio: float) -> str:
    """Traduit le ratio qualité en label (mêmes seuils que le README)."""
    if ratio is None or not math.isfinite(ratio):
        return "N/A"
    if ratio >= 0.15:
        return "Excellent"
    if ratio >= 0.10:
        return "Bon"
    if ratio >= 0.05:
        return "Moyen"
    return "Faible"


def batch_calculate_metrics(stock_list: Iterable) -> int:
    """Lance calculate_metrics() sur chaque Stock. Retourne le nombre de stocks valides."""
    valid = 0
    for stock in stock_list:
        try:
            stock.calculate_metrics()
            if stock.is_valid():
                valid += 1
        except Exception as exc:  # un stock cassé ne doit pas bloquer les autres
            print(f"⚠️ Calcul impossible pour {getattr(stock, 'ticker', '?')}: {exc}")
    return valid
