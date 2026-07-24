"""
Calcul des indicateurs techniques via yfinance (gratuit, zero token).
On calcule : variation 1M et 3M, RSI 14, position vs MM50/MM200,
distance au plus haut/bas 52 semaines. Sert a produire un score momentum
pour ne garder que les meilleurs candidats avant l'analyse Claude.
"""

import yfinance as yf
import pandas as pd


def _rsi(closes: pd.Series, period: int = 14) -> float:
    delta = closes.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    return round(float(val), 1) if pd.notna(val) else None


def indicateurs(ticker: str) -> dict | None:
    """Retourne un dict d'indicateurs pour un ticker, ou None si echec."""
    try:
        hist = yf.Ticker(ticker).history(period="1y", interval="1d")
        if hist is None or len(hist) < 60:
            return None
        closes = hist["Close"].dropna()
        if closes.empty:
            return None

        dernier = float(closes.iloc[-1])
        mm50 = float(closes.rolling(50).mean().iloc[-1])
        mm200 = float(closes.rolling(200).mean().iloc[-1]) if len(closes) >= 200 else None
        haut52 = float(closes.max())
        bas52 = float(closes.min())

        def _var(n):
            if len(closes) <= n:
                return None
            ref = float(closes.iloc[-n])
            return round((dernier / ref - 1) * 100, 1) if ref else None

        return {
            "ticker": ticker,
            "cours": round(dernier, 2),
            "devise": _devise(ticker),
            "var_1m_pct": _var(21),
            "var_3m_pct": _var(63),
            "var_1an_pct": _var(252),
            "rsi14": _rsi(closes),
            "vs_mm50_pct": round((dernier / mm50 - 1) * 100, 1) if mm50 else None,
            "vs_mm200_pct": round((dernier / mm200 - 1) * 100, 1) if mm200 else None,
            "dist_haut52_pct": round((dernier / haut52 - 1) * 100, 1) if haut52 else None,
            "dist_bas52_pct": round((dernier / bas52 - 1) * 100, 1) if bas52 else None,
        }
    except Exception:
        return None


def meta(ticker: str) -> dict:
    """Type (Action/ETF), place de cotation, nom long et devise reelle via yfinance."""
    out = {"type": "Action", "place": "", "nom_long": "", "devise_reelle": ""}
    try:
        info = yf.Ticker(ticker).info or {}
        qtype = (info.get("quoteType") or "").upper()
        out["type"] = "ETF" if qtype == "ETF" else "Action"
        out["place"] = info.get("fullExchangeName") or info.get("exchange") or ""
        out["nom_long"] = info.get("longName") or info.get("shortName") or ""
        out["devise_reelle"] = info.get("currency") or ""
    except Exception:
        pass
    return out


_FX_CACHE = {}


def taux_vers_eur(devise: str) -> float | None:
    """Taux de conversion 1 unite de <devise> -> EUR.
    Gere le cas GBp (pence londoniens) : 1 GBp = 0,01 GBP."""
    if not devise:
        return None
    d = devise.strip()
    if d.upper() == "EUR":
        return 1.0
    if d in _FX_CACHE:
        return _FX_CACHE[d]

    facteur = 1.0
    code = d.upper()
    if d == "GBp" or code == "GBX":   # cotation en pence
        code = "GBP"
        facteur = 0.01

    try:
        px = yf.Ticker(f"{code}EUR=X").history(period="5d", interval="1d")["Close"].dropna()
        taux = float(px.iloc[-1]) * facteur if not px.empty else None
    except Exception:
        taux = None

    _FX_CACHE[d] = taux
    return taux


def saisonnalite(ticker: str) -> dict:
    """Statistiques saisonnieres calculees sur 10 ans d'historique.
    - rendement moyen du mois calendaire en cours (favorable/defavorable)
    - rendement moyen par jour de semaine, et biais du jour courant
    - effet turn-of-the-month (5 derniers / 3 premiers jours ouvres)
    Best effort : renvoie des None si pas assez d'historique."""
    import datetime as _dt
    out = {
        "mois_courant": None, "rdt_moyen_mois_pct": None,
        "jour_courant": None, "rdt_moyen_jour_pct": None,
        "turn_of_month": None,
    }
    try:
        hist = yf.Ticker(ticker).history(period="10y", interval="1d")
        if hist is None or len(hist) < 250:
            return out
        closes = hist["Close"].dropna()
        rdt = closes.pct_change().dropna()
        idx = rdt.index

        # Mois en cours
        mois = _dt.date.today().month
        m_mask = idx.month == mois
        if m_mask.any():
            out["mois_courant"] = mois
            out["rdt_moyen_mois_pct"] = round(float(rdt[m_mask].mean()) * 100 * 21, 2)  # approx mensuel

        # Jour de semaine courant (0=lundi)
        jour = _dt.date.today().weekday()
        j_mask = idx.weekday == jour
        if j_mask.any() and jour < 5:
            noms = ["lundi", "mardi", "mercredi", "jeudi", "vendredi"]
            out["jour_courant"] = noms[jour]
            out["rdt_moyen_jour_pct"] = round(float(rdt[j_mask].mean()) * 100, 3)

        # Turn of the month : jour du mois <=3 ou >=26
        today = _dt.date.today().day
        out["turn_of_month"] = bool(today <= 3 or today >= 26)
    except Exception:
        pass
    return out


def _devise(ticker: str) -> str:
    if ticker.endswith((".PA", ".AS", ".DE", ".MI")):
        return "EUR"
    if ticker.endswith(".L"):
        return "GBP"
    if ticker.endswith(".SW"):
        return "CHF"
    return "USD"


def score_momentum(ind: dict) -> float:
    """Score simple pour classer les candidats a l'achat (momentum court terme
    sans surchauffe extreme). Plus c'est haut, plus le titre est un candidat achat."""
    if not ind:
        return -999
    s = 0.0
    if ind.get("var_1m_pct") is not None:
        s += ind["var_1m_pct"] * 0.5
    if ind.get("var_3m_pct") is not None:
        s += ind["var_3m_pct"] * 0.3
    if ind.get("vs_mm50_pct") is not None:
        s += ind["vs_mm50_pct"] * 0.2
    # penalite si RSI en surchauffe (>75) ou survente severe (<25)
    rsi = ind.get("rsi14")
    if rsi is not None:
        if rsi > 75:
            s -= (rsi - 75) * 1.5
        elif rsi < 25:
            s -= (25 - rsi) * 0.5
    return round(s, 1)
