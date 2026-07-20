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
    qte_detenue = notion_io.quantites_detenues(lignes)
    print("Cash disponible:", cash)
    print("Quantites detenues:", qte_detenue)

    # 2. Indicateurs techniques des positions detenues (+ quantite reelle)
    positions = []
    for p in universe.POSITIONS_DETENUES:
        ind = technicals.indicateurs(p["ticker"])
        if ind:
            ind["nom"] = p["nom"]
            ind["plateforme"] = p["plateforme"]
            ind["ticker_notion"] = p["ticker_notion"]
            ind["qty_detenue"] = qte_detenue.get(p["ticker_notion"], 0)
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

    # 7. Maj du Solde execute (cash reel) sur la derniere ligne existante,
    #    a partir des transactions reellement executees (recalcul du lendemain).
    cash_reel = round(sum(cash.values()))
    pid, _ord = notion_io.page_dernier_ordre()
    if pid:
        notion_io.maj_solde_execute(pid, cash_reel)

    # 8. Ecriture Notion (une ligne par reco), ordre incremental continu.
    #    Ventes d'abord (elles alimentent le cash), puis achats.
    #    Le solde propose = cash de depart + ventes proposees - achats proposes,
    #    ecrit uniquement sur la derniere ligne du jour (Ordre le plus grand).
    ordre = notion_io.max_ordre(lignes)
    total_cash = round(sum(cash.values()))

    ventes = reco["ventes"]
    achats = reco["achats"]
    for r in ventes:
        total_cash += r.get("montant_propose") or 0
    for r in achats:
        total_cash -= r.get("montant_propose") or 0
    solde_final = total_cash

    sequence = [("Vendre", r) for r in ventes] + [("Acheter", r) for r in achats]
    n = len(sequence)
    for i, (action, r) in enumerate(sequence):
        ordre += 1
        r["action"] = action
        solde = solde_final if i == n - 1 else None  # solde seulement sur la derniere ligne
        notion_io.ecrire_reco(r, ordre=ordre, solde_propose=solde)
    print("Notion mis a jour")


if __name__ == "__main__":
    main()
