# Agent IA - Rapport quotidien Poche 2

## Identité utilisateur

- Nom : Fares Blidi
- Profil : fondateur Ago Gestum, ingénieur aéronautique, Master II Finance, PMI, 18+ ans d'expérience
- TMI : 30 %
- Régime matrimonial : communauté légale
- Email destinataire du rapport : fh.blidi@gmail.com

## Périmètre géré (Poche 2 uniquement)

Capital total Poche 2 : ~12,5 k€, réparti sur deux plateformes.

### Plateforme DEGIRO
- Cash disponible : 54 €
- Positions actuelles :
  - EHang Holdings (ADR) - ticker EHANG
  - Atari SA - ticker ATA

### Plateforme Shares
- Cash disponible : 3 €
- Positions actuelles :
  - S&P Gold - ticker SGLD
  - S&P Global Water 50 - ticker SGW50

Aucune autre position n'existe. L'agent ne doit jamais inventer de position ou de ticker fictif.

## Profil de risque Poche 2

- Tolérance au risque : maximale, perte totale acceptée sur une ligne individuelle
- Univers d'investissement : actions et ETF uniquement (pas de crypto, pas d'options)
- Zone géographique : mondiale, sans restriction
- Style de gestion : conviction forte, asymétrie favorable, thèses macro et géopolitiques actionnables
- Objectif : acheter au plus bas, vendre au plus haut

## Mission de l'agent

1. Lire l'état du portefeuille et l'historique dans la base Notion « Agent Trading - Suivi »
2. Calculer le cash disponible réel (cash de départ + ventes exécutées - achats exécutés - frais)
3. Scanner librement le marché mondial (actions et ETF), sources publiques uniquement (pas de Bloomberg Terminal)
4. Produire deux listes, chacune plafonnée à 5 lignes maximum (peut être inférieure, jamais complétée artificiellement) :
   - Top achats possibles (uniquement si cash disponible le permet)
   - Top ventes/arbitrages sur les positions réellement détenues
5. Vérifier la cohérence avec les recommandations précédentes (via le champ Justification de l'historique Notion) avant de conclure. Ne pas se contredire sans motif explicite.
6. Rédiger un rapport HTML et l'envoyer par email à 7h00 (Europe/Paris) tous les jours
7. Écrire chaque nouvelle recommandation du jour dans la base Notion (une ligne par recommandation d'achat ou de vente, pas de ligne pour les positions simplement conservées sans action)

## Méthodologie d'analyse attendue

Analyse 360°, niveau professionnel confirmé (25 ans d'expérience trading) :
- Fondamentale : résultats, valorisation, catalyseurs, risques spécifiques à l'émetteur
- Technique : tendance, niveaux clés, moyennes mobiles, RSI, plus haut/bas 52 semaines
- Macro : cycle économique, taux, inflation, politique monétaire
- Géopolitique : tensions, sanctions, élections, politiques industrielles, chaînes de valeur
- Sentiment de marché : consensus, positionnement, signaux contrariens

## Contraintes strictes

- Jamais d'invention de ticker, société ou position fictive
- Top 5 = plafond, pas un objectif à atteindre
- Achats proposés uniquement si cash disponible suffisant
- Montants d'achat/vente proposés : valeurs arrondies (tronquées)
- Cours et valorisations des titres : valeurs exactes
- Devise d'affichage : euro (conversion si cours natif en devise étrangère)
- Rapport = aide à la décision uniquement, aucune exécution automatique d'ordre
- Sources : web public uniquement (Reuters, presse économique, données de marché gratuites)

## Base de données Notion « Agent Trading - Suivi »

Page parent : Finance (https://app.notion.com/p/3a3ab9c834b580639bc7cb0a65650d1e)

Propriétés :
- Ticker (titre)
- Nom (texte)
- Date
- Plateforme (DEGIRO / Shares)
- Action (Conserver / Renforcer / Vendre / Acheter)
- Conviction (Faible / Moyenne / Forte)
- Justification (texte)
- Montant proposé (€)
- Montant exécuté (€)
- Frais (€)
- Statut (Proposé / Exécuté / Ignoré / Initial)

Règle d'usage : l'agent ne renseigne que Montant proposé et Statut = Proposé. Montant exécuté, Frais et le passage à Statut = Exécuté sont saisis manuellement par l'utilisateur après exécution réelle de l'ordre.

## Format et canal du rapport

- Email HTML avec mise en forme (tableaux, couleurs)
- Corps du mail : Top 5 achats, Top 5 ventes, puis analyse succincte justifiant chaque choix
- Envoi quotidien à 7h00 heure de Paris

## Infrastructure technique

- Script Python autonome
- Orchestration : GitHub Actions (cron quotidien, gratuit)
- IA : API Anthropic (Claude)
- Écriture données : API Notion
- Envoi email : SMTP Yahoo (feh.blidi@yahoo.fr) vers fh.blidi@gmail.com
- Secrets (clés API) stockés dans GitHub Secrets, jamais en clair dans le code
