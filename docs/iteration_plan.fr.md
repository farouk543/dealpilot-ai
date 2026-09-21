# Plan d'itération — 2 prochaines semaines

Ce plan part de l'état actuel (système fonctionnel, 17 microservices, 11 cas synthétiques évalués,
voir `docs/eval_results.md`) et priorise ce qui a le plus d'impact avant une exposition à de vrais
utilisateurs.

## Priorité 1 — Combler la limitation connue

**Règle de plausibilité du loyer vs marché** (`case_06_adversarial_abnormal_rent`, documenté dans
`docs/eval_results.md`). Aujourd'hui, `services/risk/app/rules.py` ne compare jamais le loyer déclaré
à une référence de marché : un loyer irréaliste (trop haut ou trop bas) passe sans avertissement,
alors que le service `market` calcule déjà un prix au m² médian.

- Ajouter une règle qui compare `market_rent_per_m2` (à créer, calculé depuis DVF ou une source
  locative complémentaire) au loyer déclaré, avec un seuil d'écart (ex. ±25%) déclenchant un risque
  de sévérité moyenne.
- Écrire d'abord le cas de test adversarial correspondant en version "doit maintenant échouer si non
  corrigé" pour éviter une fausse victoire.
- Effort estimé : 2-3 jours (le plus dur est de trouver une source fiable de loyers de marché en
  open data français — DVF ne couvre que les ventes, pas les locations).

## Priorité 2 — Essai utilisateur réel chronométré

Le rapport d'évaluation le signale explicitement : la comparaison baseline vs système n'est
aujourd'hui qu'une estimation qualitative (voir `docs/eval_results.md`, section "Baseline vs
système"), faute d'accès à un vrai investisseur pendant le sprint.

- Recruter 2-3 investisseurs immobiliers réels (réseaux professionnels, forums spécialisés).
- Leur faire analyser un même dossier réel (anonymisé) une fois manuellement (chronométré), une fois
  avec DealPilot AI.
- Mesurer : temps réel, nombre de risques identifiés dans chaque cas, confiance déclarée dans la
  décision finale.
- Effort estimé : 1 semaine (recrutement + sessions + synthèse).

## Priorité 3 — Base de données partagée et historique interrogeable

Aujourd'hui, le seul état durable est le checkpointer LangGraph (`docs/architecture.md`, section
Persistance) — correct pour la reprise après redémarrage, mais impossible à interroger
indépendamment ("montre-moi tous les dossiers avec un risque élevé non résolu").

- Introduire Postgres partagé, une table par service (pas de couplage de schéma), alimentée en
  parallèle du graphe LangGraph plutôt qu'à sa place.
- Premier cas d'usage concret : un tableau de bord multi-dossiers pour l'investisseur (au-delà de la
  comparaison ponctuelle déjà livrée).
- Effort estimé : 3-4 jours.

## Priorité 4 — Renforcer l'évaluation continue

- Étendre `eval/run_eval.py` pour tourner en CI (GitHub Actions) à chaque changement touchant
  `services/` ou `shared/`, pas seulement à la demande.
- Ajouter des cas synthétiques ciblant le module promoteur/citoyen (aujourd'hui, les 11 cas ne
  couvrent que le flux investisseur) : zone agricole refusant tout permis, terrain en zone AU non
  ouverte, terrain sans réseaux.
- Effort estimé : 2 jours.

## Priorité 5 — Fiabilité GPU en production

Le verrou GPU inter-services (`flock`, `docs/architecture.md`) sérialise correctement deux services
sur un seul GPU, mais suppose toujours un seul GPU physique. Pour plusieurs utilisateurs simultanés
en environnement réel :
- Ajouter une file d'attente visible côté frontend (position dans la file, temps d'attente estimé)
  plutôt qu'un blocage silencieux.
- Évaluer un second GPU ou un provider managé (Replicate/Modal) pour absorber les pics, en gardant le
  mode auto-hébergé comme option par défaut (déjà écarté une fois pour coût, voir
  `docs/architecture.md`, mais viable en scale-out ponctuel).
- Effort estimé : 2-3 jours.

## Priorité 6 — Couverture de tests unitaires manquante

Trouvé lors de l'audit global du système : `intake`, `document-intel`, `vision`, `market`,
`design-agent` et `exterior-render` n'ont aucun test unitaire (6 services sur 17). Certains de ces
services (`document-intel`, `design-agent`) instanciaient en plus leur client Groq au chargement du
module, rendant impossible le test de la moindre logique pure sans clé API réelle — déjà corrigé
pour 4 services par un chargement paresseux du client, à généraliser.

- Écrire des tests pour la logique pure de chaque service (parsing, validation, construction de
  requêtes) sans dépendre d'appels réseau réels — suivre le modèle déjà en place dans
  `location-intel/tests/test_osm.py` (teste `_build_query`/`aggregate_categories`, pas l'appel HTTP).
- `exterior-render` (bpy/Blender) reste difficile à tester unitairement de façon conventionnelle —
  envisager des tests de fumée automatisés plutôt que du pytest classique.
- Effort estimé : 2-3 jours.

## Ce qui n'est délibérément pas dans ce plan

- Décision d'achat automatisée, conseil juridique engageant, certification structurelle, négociation
  automatisée : restent des non-goals produit (`docs/case_study.md`), pas des limitations techniques
  temporaires.
- Scraping direct de portails d'annonces : risque CGU non réévalué, DVF reste la source de vérité.

## Métriques à suivre pendant ces deux semaines

- **Adoption** : nombre de dossiers réels soumis par les investisseurs testeurs (cible : ≥ 5 dossiers
  chacun sur la période).
- **Qualité** : taux de vérifications passées dans `eval/run_eval.py` (maintenir 100% hors
  limitations documentées) après chaque changement.
- **Confiance utilisateur** : note déclarée (1-5) sur "je ferais confiance à ce dossier pour appuyer
  une offre réelle", recueillie après chaque essai utilisateur de la Priorité 2.
