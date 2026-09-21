# DealPilot AI — Case Study

## Utilisateur cible

**Persona** : investisseur immobilier indépendant / gestionnaire d'un petit portefeuille locatif en
France, qui source lui-même des immeubles de rapport (résidentiel multi-unités) via des sites
d'annonces, puis analyse manuellement chaque opportunité avant de faire une offre.

**Profil réaliste** : quelques deals étudiés par mois, pas d'équipe d'analystes dédiée, Excel et
lecture manuelle de documents comme seuls outils. Compétent financièrement mais pas juriste ni
architecte — dépend de professionnels externes (notaire, diagnostiqueur, agence) pour les points
spécialisés, mais doit d'abord savoir *lesquels* engager et sur *quoi* leur poser des questions.

Deux rôles secondaires couverts par le système, dérivés du même besoin sous-jacent
(transformer une opportunité floue en dossier structuré) :
- **Promoteur** : évalue la faisabilité de construction neuve sur un terrain.
- **Citoyen** : particulier qui veut comprendre ce qu'il peut construire sur son terrain, sans
  connaissances techniques.

## Job-to-be-done

> "Quand je trouve un immeuble qui m'intéresse, je veux transformer une annonce + des documents
> disparates + des photos en une décision d'offre défendable, sans y passer ma soirée et sans
> risquer de rater un problème qu'un document contenait déjà."

## Flux de travail manuel actuel (avant le système)

| Étape | Déclencheur | Entrée | Jugement requis | Outil actuel | Validation | Sortie | Exception typique |
|---|---|---|---|---|---|---|---|
| 1. Repérage | Nouvelle annonce vue | Annonce web | Correspond-elle aux critères ? | Site d'annonces | Aucune | Décision de creuser ou non | Annonce incomplète |
| 2. Collecte docs | Contact agence/vendeur | PDF, mails | Quels docs sont indispensables ? | Email | Aucune | Dossier de documents | Documents manquants non signalés |
| 3. Lecture documents | Docs reçus | PDF/scans | Repérer incohérences (loyers, surfaces) | Lecture manuelle | Aucune | Notes éparses | Contradiction non vue faute de comparaison systématique |
| 4. Analyse photos | Photos reçues | JPEG | Repérer défauts visibles | Œil nu | Aucune | Impression subjective | Sur-confiance sans expertise structurelle |
| 5. Comparables marché | Besoin de valoriser | Mémoire, sites d'annonces | Quels comparables sont pertinents ? | Recherche manuelle | Aucune | Fourchette de prix approximative | Biais de confirmation |
| 6. Modèle financier | Prix + loyers connus | Excel | Quelles hypothèses de stress tester ? | Excel personnel | Auto-vérification | Cap rate, cash-flow | Erreur de formule non détectée |
| 7. Risques | Analyse terminée | Tout ce qui précède | Que faut-il vraiment vérifier avant d'acheter ? | Mémoire/expérience | Aucune | Liste informelle | Risque oublié car non priorisé |
| 8. Offre | Risques connus | Analyse financière | Quel prix proposer et sous quelles conditions ? | Intuition + Excel | Aucune | Prix verbal ou email | Offre non défendable si négociation |
| 9. Due diligence | Offre acceptée | Registre de risques | Quoi demander, dans quel ordre ? | Mémoire | Aucune | Checklist ad hoc | Tâche liée à un risque oubliée |
| 10. Décision finale | Due diligence avancée | Tout le dossier | Acheter ou non ? | Jugement humain | Aucune formelle | Décision d'achat | Décision prise sans revoir tous les points |

**Temps estimé actuel** : plusieurs heures par dossier (collecte + lecture + modélisation), réparti
sur plusieurs jours au gré des documents reçus.

## Ce que le système fait (et ne fait pas)

**Dans le périmètre** : les 10 étapes ci-dessus pour de l'immobilier résidentiel locatif en France,
plus un module de faisabilité de terrain/construction neuve (promoteur/citoyen) avec maquette 3D et
rendu IA intérieur/extérieur, export PDF/Excel, résumé en langage naturel, simulateur de
contre-offre, comparaison multi-biens.

**Hors périmètre (non-goals explicites)** :
- Décision d'achat autonome — le système ne décide jamais, il éclaire une décision humaine.
- Conseil juridique ou financier personnalisé engageant.
- Certification de sécurité structurelle (l'analyse visuelle signale, ne certifie jamais).
- Valorisation garantie (les comparables DVF sont indicatifs, jamais une expertise).
- Négociation automatisée avec le vendeur.
- Exécution transactionnelle engageante (aucune signature, aucun engagement financier réel).
- Scraping en direct de portails d'annonces (risque CGU) — utilisation de données synthétiques et
  de DVF (open data officiel) à la place.
- Extraction automatique des règles chiffrées d'un règlement PLU (le système donne la zone réelle,
  pas les seuils numériques qu'elle impose — voir `docs/architecture.md`).

## Métrique de succès

**Temps jusqu'à décision** : temps manuel/ChatGPT seul (baseline, voir `docs/eval_results.md`) vs
temps avec DealPilot AI, sur un même dossier synthétique représentatif.

**Métriques secondaires (issues du brief d'origine)** :
- Exactitude des calculs financiers déterministes vs moteur de référence (calcul à la main) : cible 100%.
- Rappel sur les documents/risques critiques manquants : cible ≥ 90%.
- Zéro affirmation non tracée à une source dans les sorties critiques (prix, risques, conformité).
- Traçabilité à 100% des faits critiques vers une source, une hypothèse ou un calcul (voir le modèle
  de provenance dans `shared/dealpilot_shared/provenance.py`).

Voir `docs/eval_results.md` pour les résultats mesurés sur les cas synthétiques.
