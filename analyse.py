"""
Couche d'analyse Claude (Sonnet + web search).
On envoie a Claude :
- les indicateurs techniques calcules localement (candidats achat + positions detenues)
- le cash disponible par plateforme
- les theses precedentes (memoire, pour eviter les contradictions)
Claude renvoie un JSON structure : top achats (<=5) et top ventes (<=5),
chacun avec conviction, montant propose (tronque) et justification 360.
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
- Achats uniquement si le cash disponible de la plateforme le permet.
- Ventes uniquement sur les positions reellement detenues fournies.
- Montants d'achat/vente proposes : nombres entiers (tronques), en euros.
- Coherence avec les theses precedentes fournies : ne te contredis pas sans motif explicite dans la justification.
- Analyse 360 : fondamentale, technique, macro, geopolitique, sentiment.

Tu reponds STRICTEMENT en JSON valide, sans texte autour, au format :
{
  "achats": [
    {"ticker": "...", "nom": "...", "plateforme": "DEGIRO|Shares", "conviction": "Faible|Moyenne|Forte",
     "montant_propose": 0, "justification": "..."}
  ],
  "ventes": [
    {"ticker": "...", "nom": "...", "plateforme": "DEGIRO|Shares", "conviction": "Faible|Moyenne|Forte",
     "montant_propose": 0, "justification": "..."}
  ],
  "synthese_macro": "2-3 phrases de contexte marche du jour"
}"""


def analyser(cash: dict, candidats: list[dict], positions: list[dict], theses: dict) -> dict:
    payload = {
        "cash_disponible_par_plateforme_eur": cash,
        "candidats_achat_avec_indicateurs": candidats,
        "positions_detenues_avec_indicateurs": positions,
        "theses_precedentes_par_ticker": theses,
    }
    user_msg = (
        "Donnees du jour ci-dessous. Produis les recommandations selon tes regles.\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )

    resp = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=SYSTEM,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 8}],
        messages=[{"role": "user", "content": user_msg}],
    )

    # Concatene les blocs texte de la reponse
    texte = "".join(b.text for b in resp.content if b.type == "text").strip()
    texte = texte.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(texte)
    except json.JSONDecodeError:
        # fallback : on isole le premier objet JSON
        debut = texte.find("{")
        fin = texte.rfind("}")
        return json.loads(texte[debut:fin + 1])
