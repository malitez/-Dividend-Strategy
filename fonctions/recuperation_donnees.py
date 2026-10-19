"""Récupération des données (yfinance), cache local et import de fichiers perso."""
from __future__ import annotations

import json
import re
import time
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"

MAX_RETRIES = 3
REQUIRED_COLUMNS = ["ticker", "current_price", "annual_dividend"]

# Composants du CAC 40 (Euronext Paris). La composition change : si un ticker
# est sorti de l'indice ou n'existe plus, il est simplement ignoré (avertissement).
CAC40_TICKERS: List[str] = [
    "AC", "ACA", "AI", "AIR", "ALO", "BN", "BNP", "BVI", "CA", "CAP",
    "CS", "DG", "DSY", "EL", "EN", "ENGI", "ERF", "GLE", "HO", "KER",
    "LR", "MC", "ML", "OR", "ORA", "PUB", "RI", "RMS", "RNO", "SAF",
    "SAN", "SGO", "STLAP", "STMPA", "SU", "TEP", "TTE", "URW", "VIE", "WLN",
]


class DataFetchError(Exception):
    """Erreur de récupération réseau / yfinance."""


class CustomFileError(Exception):
    """Fichier personnalisé introuvable ou invalide (message déjà prêt à afficher)."""


def get_cac40_tickers() -> List[str]:
    """Liste des tickers CAC 40, suffixe '.PA' (Euronext Paris) inclus."""
    return [f"{t}.PA" for t in CAC40_TICKERS]


# ---------------------------------------------------------------------------
# yfinance
# ---------------------------------------------------------------------------
def _download_history(ticker: str, years: int) -> pd.DataFrame:
    """Télécharge l'historique journalier avec retries. Lève DataFetchError."""
    import yfinance as yf  # import local : le reste du module marche sans réseau

    last_error: Optional[Exception] = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            hist = yf.Ticker(ticker).history(period=f"{years}y", auto_adjust=False)
            if hist is not None and not hist.empty and "Close" in hist.columns:
                return hist
            last_error = DataFetchError("historique vide")
        except Exception as exc:  # timeout, 429, DNS...
            last_error = exc
            print(f"⚠️ {ticker}: tentative {attempt}/{MAX_RETRIES} échouée ({exc})")
        if attempt < MAX_RETRIES:
            time.sleep(1.5 * attempt)  # backoff : 1.5s puis 3s
    raise DataFetchError(f"{ticker}: {last_error}")


def fetch_history(ticker: str, years: int = 1) -> pd.DataFrame:
    """Historique OHLC journalier d'un ticker (utilisé pour la volatilité)."""
    return _download_history(ticker, years)


def fetch_dividend_data(ticker: str, years: int = 1) -> Dict[str, Any]:
    """Récupère prix, dividende annuel et historique pour UN ticker.

    - current_price : dernier cours de clôture de l'historique (inclut la séance
      en cours pendant les heures de marché) -> évite l'appel .info, lent et
      souvent limité (erreurs 429).
    - annual_dividend : somme des dividendes versés sur la période / nombre d'années.
    Lève DataFetchError si les données sont inexploitables.
    """
    hist = _download_history(ticker, years)
    close = pd.to_numeric(hist["Close"], errors="coerce").dropna()
    if close.empty:
        raise DataFetchError(f"{ticker}: aucun cours de clôture")
    dividends = hist["Dividends"] if "Dividends" in hist.columns else pd.Series(dtype=float)
    annual_dividend = float(dividends.sum()) / max(years, 1)
    return {
        "ticker": ticker,
        "current_price": float(close.iloc[-1]),
        "annual_dividend": annual_dividend,
        "history": hist,
    }


def fetch_cac40_data(
    tickers_list: Optional[List[str]] = None,
    years: int = 1,
    verbose: bool = True,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Récupère les données de PLUSIEURS tickers.

    Retourne (records, tickers_en_échec). Un ticker en échec n'arrête pas les autres.
    """
    tickers = tickers_list or get_cac40_tickers()
    records: List[Dict[str, Any]] = []
    failed: List[str] = []
    for i, ticker in enumerate(tickers, start=1):
        if verbose:
            print(f"\r  Téléchargement {i}/{len(tickers)} : {ticker:<10}", end="", flush=True)
        try:
            records.append(fetch_dividend_data(ticker, years))
        except DataFetchError:
            failed.append(ticker)
    if verbose:
        print()
    return records, failed


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
def _cache_path(filename: str) -> Path:
    name = Path(filename).name  # empêche d'écrire hors du dossier cache
    if not name.endswith(".json"):
        name += ".json"
    return CACHE_DIR / name


def cache_data(data: List[Dict[str, Any]], filename: str) -> Path:
    """Sauvegarde les records (historiques inclus) en JSON dans data/cache/."""
    path = _cache_path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "data": [
            {
                "ticker": r["ticker"],
                "current_price": r["current_price"],
                "annual_dividend": r["annual_dividend"],
                "history": r["history"].to_json(orient="split", date_format="iso"),
            }
            for r in data
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def load_cached_data(filename: str, max_age_hours: float = 12) -> Optional[List[Dict[str, Any]]]:
    """Charge le cache s'il existe, est lisible et a moins de max_age_hours. Sinon None."""
    path = _cache_path(filename)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        saved_at = datetime.fromisoformat(payload["saved_at"])
        if (datetime.now() - saved_at).total_seconds() > max_age_hours * 3600:
            return None
        records = []
        for r in payload["data"]:
            hist = pd.read_json(StringIO(r["history"]), orient="split")
            records.append({
                "ticker": r["ticker"],
                "current_price": float(r["current_price"]),
                "annual_dividend": float(r["annual_dividend"]),
                "history": hist,
            })
        return records
    except (OSError, ValueError, KeyError, TypeError):
        return None  # cache corrompu : on retélécharge


def cache_age_minutes(filename: str) -> Optional[int]:
    """Âge du cache en minutes (None s'il n'existe pas)."""
    path = _cache_path(filename)
    if not path.is_file():
        return None
    try:
        saved_at = datetime.fromisoformat(json.loads(path.read_text(encoding="utf-8"))["saved_at"])
        return int((datetime.now() - saved_at).total_seconds() // 60)
    except (OSError, ValueError, KeyError):
        return None


# ---------------------------------------------------------------------------
# Fichier personnalisé (CSV / JSON)
# ---------------------------------------------------------------------------
def _to_number(series: pd.Series) -> pd.Series:
    """Convertit en nombres ; accepte la virgule décimale française ('12,50')."""
    cleaned = series.astype(str).str.strip().str.replace(",", ".", regex=False)
    return pd.to_numeric(cleaned, errors="coerce")


def load_custom_portfolio(path_str: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Charge et valide un fichier CSV/JSON perso.

    Colonnes attendues : ticker, current_price, annual_dividend.
    Règles : champs présents, prix > 0, dividende > 0, ticker texte non vide.
    Les lignes invalides sont ignorées (listées dans les avertissements).

    Retourne (records, warnings). Lève CustomFileError avec le message à afficher.
    """
    path = Path(path_str.strip().strip("'\"")).expanduser()
    if not path.is_file():
        raise CustomFileError("❌ Fichier inexistant. Vérifiez le chemin.")

    suffix = path.suffix.lower()
    try:
        if suffix == ".csv":
            df = pd.read_csv(path, sep=None, engine="python", dtype=str)  # détecte , ou ;
        elif suffix == ".json":
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, list) or not all(isinstance(x, dict) for x in raw):
                raise ValueError("JSON attendu : liste d'objets")
            df = pd.DataFrame(raw).astype(object)
        else:
            raise CustomFileError("❌ Format CSV/JSON non valide.")
    except CustomFileError:
        raise
    except (ValueError, OSError, UnicodeDecodeError, pd.errors.ParserError, pd.errors.EmptyDataError):
        raise CustomFileError("❌ Format CSV/JSON non valide.")

    df.columns = [str(c).strip().lower() for c in df.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise CustomFileError(f"❌ Colonnes manquantes: [{', '.join(missing)}]")

    df = df[REQUIRED_COLUMNS].copy()
    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    df["current_price"] = _to_number(df["current_price"])
    df["annual_dividend"] = _to_number(df["annual_dividend"])

    warnings: List[str] = []
    records: List[Dict[str, Any]] = []
    for idx, row in df.iterrows():
        line = idx + 2  # +1 pour l'en-tête, +1 car idx démarre à 0
        if not row["ticker"] or row["ticker"] in ("NAN", "NONE"):
            warnings.append(f"ligne {line}: ticker vide")
        elif not (row["current_price"] > 0):          # NaN > 0 est False -> couvre NaN
            warnings.append(f"ligne {line} ({row['ticker']}): prix invalide ou <= 0")
        elif not (row["annual_dividend"] > 0):
            warnings.append(f"ligne {line} ({row['ticker']}): dividende invalide ou <= 0")
        else:
            records.append({
                "ticker": row["ticker"],
                "current_price": float(row["current_price"]),
                "annual_dividend": float(row["annual_dividend"]),
            })

    if not records:
        raise CustomFileError("❌ Aucune ligne valide dans le fichier (prix et dividende doivent être > 0).")
    return records, warnings
