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
                "montant_propose": _num(p, "Montant proposé"),
                "montant_execute": _num(p, "Montant exécuté"),
                "frais": _num(p, "Frais"),
                "qty": _num(p, "Qty"),
                "ordre": _num(p, "Ordre"),
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


def quantites_detenues(lignes: list[dict]) -> dict:
    """Quantite nette detenue par ticker Notion.
    Base = lignes 'Initial'. Ajustee par les transactions 'Execute'
    (achat/renforcement +qty, vente -qty)."""
    qte = {}
    # Base : positions initiales
    for l in lignes:
        if l["statut"] == "Initial" and l.get("qty"):
            qte[l["ticker"]] = qte.get(l["ticker"], 0) + l["qty"]
    # Ajustements par transactions executees
    for l in lignes:
        if l["statut"] != "Exécuté" or not l.get("qty"):
            continue
        t = l["ticker"]
        if l["action"] == "Vendre":
            qte[t] = qte.get(t, 0) - l["qty"]
        elif l["action"] in ("Acheter", "Renforcer"):
            qte[t] = qte.get(t, 0) + l["qty"]
    return {k: v for k, v in qte.items() if v > 0}


def max_ordre(lignes: list[dict]) -> int:
    """Plus grand numero d'ordre existant (0 si aucun)."""
    vals = [int(l["ordre"]) for l in lignes if l.get("ordre") is not None]
    return max(vals) if vals else 0


def page_dernier_ordre():
    """Retourne (page_id, ordre) de la ligne au plus grand Ordre, ou (None, 0).
    Sert a poser le Solde execute recalcule sur la derniere ligne existante."""
    ds = _data_source_id()
    best_id, best_ordre = None, -1
    cursor = None
    while True:
        kwargs = {"data_source_id": ds, "page_size": 100}
        if cursor:
            kwargs["start_cursor"] = cursor
        resp = notion.data_sources.query(**kwargs)
        for page in resp["results"]:
            o = _num(page["properties"], "Ordre")
            if o is not None and o > best_ordre:
                best_ordre, best_id = int(o), page["id"]
        if not resp.get("has_more"):
            break
        cursor = resp["next_cursor"]
    return best_id, best_ordre


def maj_solde_execute(page_id: str, solde: float):
    """Ecrit le Solde execute sur une ligne existante."""
    notion.pages.update(page_id=page_id, properties={"Solde exécuté": {"number": round(solde)}})


def ecrire_reco(reco: dict, ordre: int, solde_propose: float | None = None):
    ds = _data_source_id()
    props = {
        "Ticker": {"title": [{"text": {"content": reco["ticker"]}}]},
        "Nom": {"rich_text": [{"text": {"content": reco.get("nom", "")}}]},
        "Date": {"date": {"start": date.today().isoformat()}},
        "Ordre": {"number": ordre},
        "Action": {"select": {"name": reco["action"]}},
        "Conviction": {"select": {"name": reco["conviction"]}},
        "Justification": {"rich_text": [{"text": {"content": reco["justification"][:1900]}}]},
        "Statut": {"select": {"name": "Proposé"}},
    }
    if reco.get("plateforme"):
        props["Plateforme"] = {"select": {"name": reco["plateforme"]}}
    if reco.get("montant_propose") is not None:
        props["Montant proposé"] = {"number": reco["montant_propose"]}
    if reco.get("qty") is not None:
        props["Qty"] = {"number": reco["qty"]}
    if solde_propose is not None:
        props["Solde proposé"] = {"number": round(solde_propose)}
    notion.pages.create(parent={"type": "data_source_id", "data_source_id": ds}, properties=props)
