"""
Lecture / ecriture Notion.
- Lit l'historique (positions Initial + transactions Executees) pour reconstituer
  le cash disponible reel et l'historique des theses par ticker.
- Ecrit les nouvelles recommandations du jour (Statut = Propose).
"""

import os
from datetime import date
from notion_client import Client

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]

# Cash de depart hors positions (renseigne au cadrage)
CASH_INITIAL = {"DEGIRO": 54.0, "Shares": 3.0}

notion = Client(auth=NOTION_TOKEN)


def _txt(prop):
    try:
        return "".join(t["plain_text"] for t in prop["rich_text"])
    except Exception:
        return ""


def _num(prop):
    return prop.get("number")


def _select(prop):
    v = prop.get("select")
    return v["name"] if v else None


def lire_historique() -> list[dict]:
    """Retourne toutes les lignes de la base sous forme de dicts simples."""
    lignes = []
    cursor = None
    while True:
        kwargs = {"database_id": DATABASE_ID, "page_size": 100}
        if cursor:
            kwargs["start_cursor"] = cursor
        resp = notion.databases.query(**kwargs)
        for page in resp["results"]:
            p = page["properties"]
            lignes.append({
                "ticker": "".join(t["plain_text"] for t in p["Ticker"]["title"]),
                "nom": _txt(p["Nom"]),
                "plateforme": _select(p["Plateforme"]),
                "action": _select(p["Action"]),
                "conviction": _select(p["Conviction"]),
                "justification": _txt(p["Justification"]),
                "montant_propose": _num(p["Montant proposé (€)"]),
                "montant_execute": _num(p["Montant exécuté (€)"]),
                "frais": _num(p["Frais (€)"]),
                "statut": _select(p["Statut"]),
            })
        if not resp.get("has_more"):
            break
        cursor = resp["next_cursor"]
    return lignes


def calculer_cash(lignes: list[dict]) -> dict:
    """Cash dispo par plateforme = cash initial + ventes executees - achats executes - frais."""
    cash = dict(CASH_INITIAL)
    for l in lignes:
        if l["statut"] != "Exécuté":
            continue
        plt = l["plateforme"]
        if plt not in cash:
            continue
        montant = l["montant_execute"] or 0
        frais = l["frais"] or 0
        if l["action"] in ("Vendre",):
            cash[plt] += montant - frais
        elif l["action"] in ("Acheter", "Renforcer"):
            cash[plt] -= montant + frais
    return {k: round(v, 2) for k, v in cash.items()}


def theses_par_ticker(lignes: list[dict]) -> dict:
    """Derniere justification connue par ticker, pour eviter les contradictions."""
    out = {}
    for l in lignes:
        t = l["ticker"]
        if l["justification"]:
            out[t] = {"action": l["action"], "justification": l["justification"], "statut": l["statut"]}
    return out


def ecrire_reco(reco: dict):
    """Ecrit une recommandation du jour. reco contient :
    ticker, nom, plateforme, action, conviction, justification, montant_propose."""
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
    notion.pages.create(parent={"database_id": DATABASE_ID}, properties=props)
