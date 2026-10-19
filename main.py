"""Point d'entrée : menu interactif du Sélecteur d'Actions - Stratégie Dividende.

Lancement :  python main.py   (aucun argument CLI)
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from classes.AnalysisStrategy import AnalysisStrategy
from classes.Portfolio import Portfolio
from classes.Stock import Stock
from fonctions.affichage_filtrage import display_results
from fonctions.calcul_metriques import COL_RATIO, COL_VOL, COL_YIELD
from fonctions.export_resultats import export_csv, export_html, export_json, generate_report
from fonctions.recuperation_donnees import (
    CustomFileError, DataFetchError, cache_age_minutes, cache_data, fetch_cac40_data,
    fetch_history, get_cac40_tickers, load_cached_data, load_custom_portfolio,
)

CAC40_CACHE = "cac40_cache"
BANNER = """
╔════════════════════════════════════════════════╗
║  Sélecteur d'Actions - Stratégie Dividende     ║
╚════════════════════════════════════════════════╝
"""


# --------------------------------------------------------------------------
# Helpers de saisie
# --------------------------------------------------------------------------
def ask(prompt: str) -> str:
    """input() avec strip."""
    return input(prompt).strip()


def ask_choice(prompt: str, valid: List[str]) -> str:
    """Boucle jusqu'à obtenir une réponse dans `valid`."""
    while True:
        answer = ask(prompt)
        if answer in valid:
            return answer
        print(f"❌ Choix invalide. Options: {', '.join(valid)}")


def parse_float(text: str) -> Optional[float]:
    """'2,5' ou '2.5' -> 2.5 ; texte invalide -> None."""
    try:
        return float(text.replace(",", "."))
    except ValueError:
        return None


def ask_float(prompt: str, current: float, minimum: float = 0.0) -> float:
    """Demande un nombre ; Entrée garde la valeur actuelle."""
    while True:
        text = ask(f"{prompt} [{current:g}] : ")
        if text == "":
            return current
        value = parse_float(text)
        if value is not None and value >= minimum:
            return value
        print(f"❌ Entrez un nombre ≥ {minimum:g}.")


# --------------------------------------------------------------------------
# Construction du portfolio
# --------------------------------------------------------------------------
def build_portfolio(records: List[Dict[str, Any]]) -> tuple[Portfolio, List[str]]:
    """Records -> Portfolio. Retourne aussi les tickers rejetés (données incomplètes)."""
    portfolio = Portfolio()
    rejected: List[str] = []
    for r in records:
        stock = Stock(r["ticker"], r["current_price"], r["annual_dividend"], r["history"])
        if not portfolio.add_stock(stock):
            rejected.append(r["ticker"])
    return portfolio, rejected


# --------------------------------------------------------------------------
# Sous-menus
# --------------------------------------------------------------------------
def export_menu(df, strategy: AnalysisStrategy, portfolio: Portfolio) -> None:
    """Export du tableau affiché en CSV / JSON / HTML (ou les trois)."""
    if df.empty:
        print("⚠️ Rien à exporter (tableau vide).")
        return
    print("\nFormat d'export :  [1] CSV   [2] JSON   [3] HTML   [4] Les trois   [0] Annuler")
    choice = ask_choice("Choix : ", ["0", "1", "2", "3", "4"])
    if choice == "0":
        return
    default = f"dividendes_{datetime.now():%Y%m%d_%H%M%S}"
    name = ask(f"Nom du fichier (sans extension) [{default}] : ") or default
    try:
        if choice == "4":
            paths = generate_report(portfolio, strategy, basename=name)
            for p in paths.values():
                print(f"✅ Exporté : {p}")
            return
        if choice == "1":
            print(f"✅ Exporté : {export_csv(df, name)}")
        elif choice == "2":
            print(f"✅ Exporté : {export_json(df, name)}")
        else:
            print(f"✅ Exporté : {export_html(df, name, subtitle=strategy.describe())}")
    except OSError as exc:
        print(f"❌ Export impossible : {exc}")


def results_menu(portfolio: Portfolio, strategy: AnalysisStrategy, source: str) -> None:
    """Affiche le tableau puis propose tri / filtre / export, jusqu'au retour."""
    while True:
        df = strategy.run_analysis(portfolio)
        display_results(df, f"{source} — {strategy.describe()}")
        print("\n  [1] Trier par Rendement %     [2] Trier par Volatilité % (plus bas d'abord)")
        print("  [3] Trier par Ratio Q         [4] Filtrer (rendement min, volatilité max)")
        print("  [5] Exporter                  [0] Retour au menu principal")
        choice = ask_choice("Choix : ", ["0", "1", "2", "3", "4", "5"])
        if choice == "0":
            return
        if choice == "1":
            strategy.sort_metric = COL_YIELD
        elif choice == "2":
            strategy.sort_metric = COL_VOL
        elif choice == "3":
            strategy.sort_metric = COL_RATIO
        elif choice == "4":
            strategy.min_yield = ask_float("Rendement minimum (%)", strategy.min_yield, 0)
            strategy.max_volatility = ask_float("Volatilité maximum (%)", strategy.max_volatility, 0.01)
        else:
            export_menu(df, strategy, portfolio)


# --------------------------------------------------------------------------
# Modes
# --------------------------------------------------------------------------
def run_cac40_mode() -> None:
    """Mode 1 : récupération des tickers CAC 40 (cache 12h) puis analyse."""
    tickers = get_cac40_tickers()
    records = None

    age = cache_age_minutes(CAC40_CACHE)
    if age is not None:
        cached = load_cached_data(CAC40_CACHE)
        if cached:
            print(f"\n💾 Données en cache (il y a {age} min).")
            if ask("[Entrée] utiliser le cache   [r] retélécharger : ").lower() != "r":
                records = cached

    if records is None:
        print(f"\n📡 Récupération de {len(tickers)} tickers via Yahoo Finance...")
        try:
            records, failed = fetch_cac40_data(tickers)
        except DataFetchError as exc:
            print(f"⚠️ Erreur réseau. Réessayez dans quelques secondes. ({exc})")
            return
        if failed:
            print(f"⚠️ {len(failed)} ticker(s) ignoré(s) : {', '.join(failed)}")
        if not records:
            print("⚠️ Erreur réseau. Réessayez dans quelques secondes.")
            return
        try:
            cache_data(records, CAC40_CACHE)
        except OSError as exc:
            print(f"⚠️ Cache non sauvegardé : {exc}")

    portfolio, rejected = build_portfolio(records)
    if rejected:
        print(f"⚠️ Données incomplètes, ignorés : {', '.join(rejected)}")
    if len(portfolio) == 0:
        print("❌ Aucune action exploitable.")
        return
    strategy = AnalysisStrategy(tickers_list=tickers)
    results_menu(portfolio, strategy, f"CAC 40 ({len(portfolio)} actions)")


def run_custom_mode() -> None:
    """Mode 2 : fichier CSV/JSON perso (prix + dividende) ; la volatilité vient de yfinance."""
    print("\nEntrez le chemin absolu du fichier (CSV/JSON). Entrée vide = retour.")
    print("Format attendu :")
    print("  - CSV  : ticker, current_price, annual_dividend")
    print("  - JSON : [{ticker, current_price, annual_dividend}, ...]")
    print("Exemple : /home/user/mon_portefeuille.csv")

    while True:
        path = ask("Chemin : ")
        if not path:
            return
        try:
            file_records, warnings = load_custom_portfolio(path)
            break
        except CustomFileError as exc:
            print(exc)

    for w in warnings:
        print(f"⚠️ Ignoré : {w}")

    print(f"\n📡 Historique des prix de {len(file_records)} ticker(s) (pour la volatilité)...")
    records, failed = [], []
    for i, rec in enumerate(file_records, start=1):
        print(f"\r  {i}/{len(file_records)} : {rec['ticker']:<10}", end="", flush=True)
        try:
            records.append({**rec, "history": fetch_history(rec["ticker"])})
        except DataFetchError:
            failed.append(rec["ticker"])
    print()
    if failed:
        print(f"⚠️ Erreur réseau / ticker inconnu, ignorés : {', '.join(failed)}")
    if not records:
        print("⚠️ Erreur réseau. Réessayez dans quelques secondes.")
        return

    portfolio, rejected = build_portfolio(records)
    if rejected:
        print(f"⚠️ Données incomplètes, ignorés : {', '.join(rejected)}")
    if len(portfolio) == 0:
        print("❌ Aucune action exploitable.")
        return
    strategy = AnalysisStrategy(tickers_list=[r["ticker"] for r in records])
    results_menu(portfolio, strategy, f"Données personnalisées ({len(portfolio)} actions)")


def main() -> None:
    """Menu principal : boucle jusqu'à 'Quitter'."""
    try:
        while True:
            print(BANNER)
            print("Choisissez une source de données :\n")
            print("  [1] CAC 40 (analyse automatique des actions de l'indice)")
            print("  [2] Données personnalisées (importer votre propre fichier)")
            print("  [0] Quitter\n")
            choice = ask_choice("Entrée (1 ou 2) : ", ["0", "1", "2"])
            if choice == "0":
                break
            run_cac40_mode() if choice == "1" else run_custom_mode()
    except (KeyboardInterrupt, EOFError):
        print()
    print("À bientôt 👋")


if __name__ == "__main__":
    main()
