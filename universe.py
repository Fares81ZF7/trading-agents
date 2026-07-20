"""
Univers de screening V1.
Bornes : grands indices US + Europe + ETF thematiques momentum.
Volontairement compact pour limiter le temps de scan et le cout.
On elargira (emergents, small caps) apres la phase de rodage.
"""

# Positions actuellement detenues (toujours analysees, quel que soit le screen)
POSITIONS_DETENUES = [
    {"ticker": "EH", "nom": "EHang Holdings (ADR)", "plateforme": "DEGIRO"},
    {"ticker": "ATA.PA", "nom": "Atari SA", "plateforme": "DEGIRO"},
    {"ticker": "SGLD.L", "nom": "S&P Gold", "plateforme": "Shares"},
    {"ticker": "DH2O.L", "nom": "S&P Global Water 50", "plateforme": "Shares"},
]

# Univers de chasse (achats potentiels). Liste courte de valeurs liquides + ETF momentum.
# Note : les tickers yfinance des positions detenues sont a ajuster selon la cotation reelle
# (place de cotation DEGIRO/Shares). A verifier au premier run.
UNIVERS_ACTIONS_US = [
    "NVDA", "AMD", "AVGO", "MU", "TSM", "SMCI", "PLTR", "MRVL", "ARM", "QCOM",
    "TSLA", "META", "AMZN", "MSFT", "GOOGL", "AAPL", "NFLX", "CRWD", "SNOW", "NET",
    "COIN", "MSTR", "HOOD", "SOFI", "UBER", "SHOP", "DDOG", "PANW", "ANET", "VST",
]

UNIVERS_ACTIONS_EUROPE = [
    "ASML.AS", "STMPA.PA", "SIE.DE", "SAP.DE", "MC.PA", "AIR.PA", "RHM.DE",
    "NVO", "NOVN.SW", "OR.PA", "SU.PA", "BESI.AS", "ADYEN.AS",
]

UNIVERS_ETF = [
    "SMH", "SOXX", "XLK", "ARKK", "IHAK", "BOTZ", "URA", "URNM", "GLD",
    "XLE", "ITA", "PPA", "IWM", "EEM", "FXI", "KWEB", "TAN", "ICLN",
]

UNIVERS_CHASSE = UNIVERS_ACTIONS_US + UNIVERS_ACTIONS_EUROPE + UNIVERS_ETF
