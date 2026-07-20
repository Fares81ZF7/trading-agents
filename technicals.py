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
            "rsi14": _rsi(closes),
            "vs_mm50_pct": round((dernier / mm50 - 1) * 100, 1) if mm50 else None,
            "vs_mm200_pct": round((dernier / mm200 - 1) * 100, 1) if mm200 else None,
            "dist_haut52_pct": round((dernier / haut52 - 1) * 100, 1) if haut52 else None,
            "dist_bas52_pct": round((dernier / bas52 - 1) * 100, 1) if bas52 else None,
        }
    except Exception:
        return None


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
