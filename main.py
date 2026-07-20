"""
Orchestrateur : screening technique -> analyse Claude -> email + ecriture Notion.
Lance par GitHub Actions chaque jour a 7h00 (Europe/Paris).
"""

import universe
import technicals
import notion_io
import analyse
import mailer


TOP_CANDIDATS = 12  # nb de candidats achat envoyes a Claude apres screening momentum


def main():
    # 1. Etat portefeuille et cash reel depuis Notion
    lignes = notion_io.lire_historique()
    cash = notion_io.calculer_cash(lignes)
    theses = notion_io.theses_par_ticker(lignes)
    print("Cash disponible:", cash)

    # 2. Indicateurs techniques des positions detenues
    positions = []
    for p in universe.POSITIONS_DETENUES:
        ind = technicals.indicateurs(p["ticker"])
        if ind:
            ind["nom"] = p["nom"]
            ind["plateforme"] = p["plateforme"]
            positions.append(ind)

    # 3. Screening momentum de l'univers de chasse
    scored = []
    for t in universe.UNIVERS_CHASSE:
        ind = technicals.indicateurs(t)
        if ind:
            ind["score"] = technicals.score_momentum(ind)
            scored.append(ind)
    scored.sort(key=lambda x: x["score"], reverse=True)
    candidats = scored[:TOP_CANDIDATS]
    print(f"{len(candidats)} candidats retenus apres screening")

    # 4. Analyse Claude
    reco = analyse.analyser(cash, candidats, positions, theses)

    # 5. Plafonnement de securite a 5 (au cas ou)
    reco["achats"] = (reco.get("achats") or [])[:5]
    reco["ventes"] = (reco.get("ventes") or [])[:5]

    # 6. Email
    html = mailer.construire_html(reco, cash)
    mailer.envoyer(html)
    print("Email envoye")

    # 7. Ecriture Notion (une ligne par reco)
    for r in reco["achats"]:
        r["action"] = "Acheter"
        notion_io.ecrire_reco(r)
    for r in reco["ventes"]:
        r["action"] = "Vendre"
        notion_io.ecrire_reco(r)
    print("Notion mis a jour")


if __name__ == "__main__":
    main()
