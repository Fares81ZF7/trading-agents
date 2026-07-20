"""
Lecture / ecriture Notion (API data_sources 2025-09-03+).
Robuste a la normalisation Unicode des noms de proprietes (e accentue).
"""

import os
import unicodedata
from datetime import date
from notion_client import Client

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]

CASH_INITIAL = {"DEGIRO": 54.0, "Shares": 3.0}

notion = Client(auth=NOTION_TOKEN)

_DS_ID = None


def _data_source_id() -> str:
    global _DS_ID
    if _DS_ID:
        return _DS_ID
    db = notion.databases.retrieve(database_id=DATABASE_ID)
    sources = db.get("data_sources") or []
    _DS_ID = sources[0]["id"] if sources else DATABASE_ID
    return _DS_ID


def _norm(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def _prop(props: dict, nom: str):
    """Recupere une propriete par nom, insensible a la normalisation Unicode."""
    cible = _norm(nom)
    for k, v in props.items():
        if _norm(k) == cible:
            return v
    return {}


def _txt(props, nom):
    p = _prop(props, nom)
    try:
        return "".join(t["plain_text"] for t in p["rich_text"])
    except Exception:
        return ""


def _title(props, nom):
    p = _prop(props, nom)
    try:
        return "".join(t["plain_text"] for t in p["title"])
    except Exception:
        return ""


def _num(props, nom):
    return _prop(props, nom).get("number")


def _select(props, nom):
    v = _prop(props, nom).get("select")
    return v["name"] if v else None


def lire_historique() -> list[dict]:
    ds = _data_source_id()
    lignes = []
    cursor = None
    while True:
        kwargs = {"data_source_id": ds, "page_size": 100}
        if cursor:
            kwargs["start_cursor"] = cursor
        resp = notion.data_sources.query(**kwargs)
        for page in resp["results"]:
            p = page["properties"]
            lignes.append({
                "ticker": _title(p, "Ticker"),
                "nom": _txt(p, "Nom"),
                "plateforme": _select(p, "Plateforme"),
                "action": _select(p, "Action"),
                "conviction": _select(p, "Conviction"),
                "justification": _txt(p, "Justification"),
                "montant_propose": _num(p, "Montant proposé (€)"),
                "montant_execute": _num(p, "Montant exécuté (€)"),
                "frais": _num(p, "Frais (€)"),
                "statut": _select(p, "Statut"),
            })
        if not resp.get("has_more"):
            break
        cursor = resp["next_cursor"]
    return lignes


def calculer_cash(lignes: list[dict]) -> dict:
    cash = dict(CASH_INITIAL)
    for l in lignes:
        if l["statut"] != "Exécuté":
            continue
        plt = l["plateforme"]
        if plt not in cash:
            continue
        montant = l["montant_execute"] or 0
        frais = l["frais"] or 0
        if l["action"] == "Vendre":
            cash[plt] += montant - frais
        elif l["action"] in ("Acheter", "Renforcer"):
            cash[plt] -= montant + frais
    return {k: round(v, 2) for k, v in cash.items()}


def theses_par_ticker(lignes: list[dict]) -> dict:
    out = {}
    for l in lignes:
        if l["justification"]:
            out[l["ticker"]] = {
                "action": l["action"],
                "justification": l["justification"],
                "statut": l["statut"],
            }
    return out


def ecrire_reco(reco: dict):
    ds = _data_source_id()
    props = {
        "Ticker": {"title": [{"text": {"content": reco["ticker"]}}]},
        "Nom": {"rich_text": [{"text": {"content": reco.get("nom", "")}}]},
        "Date": {"date": {"start": date.today().isoformat()}},
        "Action": {"select": {"name": reco["action"]}},
        "Conviction": {"select": {"name": reco["conviction"]}},
        "Justification": {"rich_text": [{"text": {"content": reco["justification"][:1900]}}]},
        "Statut": {"select": {"name": "Proposé"}},
    }
    if reco.get("plateforme"):
        props["Plateforme"] = {"select": {"name": reco["plateforme"]}}
    if reco.get("montant_propose") is not None:
        props["Montant proposé (€)"] = {"number": reco["montant_propose"]}
    notion.pages.create(parent={"type": "data_source_id", "data_source_id": ds}, properties=props)
