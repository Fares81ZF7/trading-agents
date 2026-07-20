"""
Controle en AMONT, avant tout appel facture (Claude / web search).
Trois verrous, tous gratuits :
1. Config Notion : agent actif ? fenetre de pause en cours ?
2. Jour de bourse : week-end exclu, jours feries exclus par place.
3. Determine quelles places sont ouvertes aujourd'hui, pour filtrer l'univers.

Si aucune place n'est ouverte, ou agent inactif, ou pause : on s'arrete
avant la moindre depense.
"""

import os
import datetime as dt

import exchange_calendars as xcals
from notion_client import Client

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
CONFIG_DB_ID = os.environ.get("NOTION_CONFIG_DB_ID")

notion = Client(auth=NOTION_TOKEN)

# Calendriers officiels par place (codes exchange_calendars)
# XNYS = NYSE, XNAS = Nasdaq, XPAR = Euronext Paris, XAMS = Amsterdam,
# XLON = Londres, XETR = Xetra, XSWX = SIX Suisse, XMIL = Borsa Italiana
CALENDRIERS = {
    "XNYS": "US",
    "XPAR": "Europe",
    "XLON": "UK",
}


def _config_db_source_id() -> str | None:
    if not CONFIG_DB_ID:
        return None
    db = notion.databases.retrieve(database_id=CONFIG_DB_ID)
    sources = db.get("data_sources") or []
    return sources[0]["id"] if sources else CONFIG_DB_ID


def lire_config() -> dict:
    """Lit la ligne de config. Retourne agent_actif (bool) + fenetre de pause."""
    out = {"agent_actif": True, "pause_du": None, "pause_au": None}
    ds = _config_db_source_id()
    if not ds:
        return out
    try:
        resp = notion.data_sources.query(data_source_id=ds, page_size=1)
        if not resp["results"]:
            return out
        p = resp["results"][0]["properties"]
        actif = p.get("Agent actif", {}).get("checkbox")
        out["agent_actif"] = bool(actif) if actif is not None else True
        du = p.get("Pause du", {}).get("date")
        au = p.get("Pause au", {}).get("date")
        out["pause_du"] = du["start"] if du else None
        out["pause_au"] = au["start"] if au else None
    except Exception:
        pass
    return out


def en_pause(cfg: dict, jour: dt.date) -> bool:
    if not cfg.get("pause_du") or not cfg.get("pause_au"):
        return False
    try:
        d1 = dt.date.fromisoformat(cfg["pause_du"][:10])
        d2 = dt.date.fromisoformat(cfg["pause_au"][:10])
        return d1 <= jour <= d2
    except Exception:
        return False


def places_ouvertes(jour: dt.date) -> list[str]:
    """Retourne la liste des zones (US, Europe, UK) dont la bourse est ouverte ce jour."""
    ouvertes = []
    for code, zone in CALENDRIERS.items():
        try:
            cal = xcals.get_calendar(code)
            if cal.is_session(jour.isoformat()):
                ouvertes.append(zone)
        except Exception:
            # en cas de doute, on considere la zone ouverte (fail-open cote marche)
            ouvertes.append(zone)
    return sorted(set(ouvertes))


def decision() -> dict:
    """Decision de gating. Retourne :
    - run (bool) : faut-il lancer l'analyse ?
    - raison (str) : pourquoi on ne tourne pas (si run=False)
    - zones_ouvertes (list) : zones de marche ouvertes aujourd'hui."""
    jour = dt.date.today()
    cfg = lire_config()

    if not cfg["agent_actif"]:
        return {"run": False, "raison": "Agent desactive dans la config Notion.", "zones_ouvertes": []}

    if en_pause(cfg, jour):
        return {"run": False, "raison": f"Periode de pause ({cfg['pause_du']} -> {cfg['pause_au']}).",
                "zones_ouvertes": []}

    if jour.weekday() >= 5:
        return {"run": False, "raison": "Week-end : bourses fermees.", "zones_ouvertes": []}

    zones = places_ouvertes(jour)
    if not zones:
        return {"run": False, "raison": "Jour ferie sur toutes les places suivies.", "zones_ouvertes": []}

    return {"run": True, "raison": "", "zones_ouvertes": zones}
