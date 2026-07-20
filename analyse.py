"""
Couche d'analyse Claude (Sonnet + web search).
Sortie structuree GARANTIE via un outil a schema JSON (tool_use),
ce qui evite les erreurs de parsing quand le modele ajoute du texte.
"""

import os
import json
import anthropic

MODEL = "claude-sonnet-4-6"
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM = """Tu es un gerant de conviction avec 25 ans de trading haut niveau.
Profil client : poche offensive, tolerance au risque maximale, perte totale acceptee sur une ligne.
Univers : actions et ETF uniquement, monde entier. Objectif : acheter au plus bas, vendre au plus haut,
sur un horizon court terme.

Regles imperatives :
- Ne JAMAIS inventer de ticker, societe ou position. Tu ne travailles que sur les donnees fournies.
- Top achats et top ventes plafonnes a 5 lignes chacun. Moins est permis, jamais de remplissage artificiel.
- Ventes uniquement sur les positions reellement detenues fournies.
- SEQUENCE OBLIGATOIRE : traite d'abord les ventes. Calcule ensuite un cash projete par plateforme =
  cash disponible actuel + produit net des ventes que tu proposes (hypothese : ces ventes seront executees).
  Dimensionne les achats sur ce cash projete, plateforme par plateforme.
- Un achat sur une plateforme ne peut jamais depasser le cash projete de cette meme plateforme.
- AUCUNE OBLIGATION DE TOUT PLACER : ne deploie pas le cash s'il n'y a pas de conviction suffisante.
  Tu peux ne rien acheter, ou n'acheter qu'une fraction du cash (ex. 1000 EUR sur 5000 EUR dispo).
  Tu ne deploies une large part du cash que sur conviction Forte etayee par des donnees fiables,
  actuelles et prospectives. En cas de doute, conserver du cash est une position legitime.
- Montants d'achat/vente : entiers, en euros. Qty : entier = montant / cours actuel du titre
  (champ "cours", converti en euros selon "devise"), arrondi.
- Coherence avec les theses precedentes : ne te contredis pas sans motif explicite.
- Analyse 360 : fondamentale, technique, macro, geopolitique, sentiment.
Utilise l'outil web_search si besoin, puis appelle IMPERATIVEMENT l'outil enregistrer_recommandations
pour livrer ta reponse finale."""

TOOL = {
    "name": "enregistrer_recommandations",
    "description": "Enregistre les recommandations du jour, structurees.",
    "input_schema": {
        "type": "object",
        "properties": {
            "achats": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "ticker": {"type": "string"},
                        "nom": {"type": "string"},
                        "plateforme": {"type": "string", "enum": ["DEGIRO", "Shares"]},
                        "conviction": {"type": "string", "enum": ["Faible", "Moyenne", "Forte"]},
                        "montant_propose": {"type": "integer"},
                        "qty": {"type": "integer"},
                        "justification": {"type": "string"},
                    },
                    "required": ["ticker", "plateforme", "conviction", "montant_propose", "qty", "justification"],
                },
            },
            "ventes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "ticker": {"type": "string"},
                        "nom": {"type": "string"},
                        "plateforme": {"type": "string", "enum": ["DEGIRO", "Shares"]},
                        "conviction": {"type": "string", "enum": ["Faible", "Moyenne", "Forte"]},
                        "montant_propose": {"type": "integer"},
                        "qty": {"type": "integer"},
                        "justification": {"type": "string"},
                    },
                    "required": ["ticker", "plateforme", "conviction", "montant_propose", "qty", "justification"],
                },
            },
            "synthese_macro": {"type": "string"},
        },
        "required": ["achats", "ventes", "synthese_macro"],
    },
}


def analyser(cash: dict, candidats: list[dict], positions: list[dict], theses: dict) -> dict:
    payload = {
        "cash_disponible_par_plateforme_eur": cash,
        "candidats_achat_avec_indicateurs": candidats,
        "positions_detenues_avec_indicateurs": positions,
        "theses_precedentes_par_ticker": theses,
    }
    user_msg = (
        "Donnees du jour ci-dessous. Analyse, puis appelle enregistrer_recommandations.\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )

    messages = [{"role": "user", "content": user_msg}]

    # Boucle : on laisse le modele faire ses web_search, puis on force l'outil final.
    for _ in range(6):
        resp = client.messages.create(
            model=MODEL,
            max_tokens=4000,
            system=SYSTEM,
            tools=[
                {"type": "web_search_20250305", "name": "web_search", "max_uses": 8},
                TOOL,
            ],
            messages=messages,
        )

        # Cherche un appel a notre outil final
        for block in resp.content:
            if block.type == "tool_use" and block.name == "enregistrer_recommandations":
                return block.input

        # Sinon on rejoue le tour (web_search gere cote serveur, on ajoute la reponse et on relance)
        messages.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason == "tool_use":
            # web search server-side : on relance en demandant la conclusion
            messages.append({
                "role": "user",
                "content": "Termine : appelle maintenant enregistrer_recommandations avec ta decision finale.",
            })
        else:
            messages.append({
                "role": "user",
                "content": "Appelle enregistrer_recommandations avec ta decision finale.",
            })

    # Fallback vide si le modele n'a jamais appele l'outil
    return {"achats": [], "ventes": [], "synthese_macro": "Aucune recommandation generee."}
