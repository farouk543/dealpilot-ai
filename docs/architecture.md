# Architecture — DealPilot AI

## Vue d'ensemble

16 microservices FastAPI + un frontend Streamlit, orchestrés par un service `orchestrator` qui
exécute un graphe LangGraph (10 étapes séquentielles pour l'acquisition), et proxy les appels du
module promoteur/citoyen (faisabilité, design conversationnel, rendu IA, résumé, export).

```
                          ┌─────────────┐
                          │  frontend   │  Streamlit (3 rôles : investisseur/promoteur/citoyen)
                          └──────┬──────┘
                                 │ HTTP
                          ┌──────▼──────┐
                          │ orchestrator│  LangGraph StateGraph + proxy REST
                          └──────┬──────┘
        ┌──────────┬─────────────┼─────────────┬──────────┬───────────┐
        ▼          ▼             ▼             ▼          ▼           ▼
   intake   document-intel   vision       market   location-intel  financial-engine
        │          │             │             │          │           │
        ▼          ▼             ▼             ▼          ▼           ▼
      risk  →   offer  →  due-diligence      land-feasibility   design-agent
                                                    │                 │
                                          interior-render      exterior-render
                                          (SDXL, façade 360°)  (Blender/Cycles, dans le
                                                                dépôt mais hors parcours
                                                                principal — voir plus bas)
                                                    │
                                             summary   report
```

Chaque service ne connaît que sa propre responsabilité ; seul l'orchestrator voit l'état complet
d'un dossier (`DealState`).

## Pourquoi des microservices (pas un monolithe)

Décision imposée dès le départ du projet : isoler chaque capacité métier (extraction documentaire,
vision, marché, finance, risque, offre, due diligence) permet de :
- Remplacer un fournisseur LLM sans toucher au reste (déjà arrivé deux fois : migration de modèles
  Groq et Gemini dépréciés en cours de sprint, changement isolé à `document-intel`/`vision`/etc.).
- Isoler les pannes : un service en panne ne doit pas faire tomber tout le pipeline (voir
  `docs/eval_results.md`, cas `case_09` — trouvé en défaut puis corrigé).
- Séparer les responsabilités de test : chaque service a sa propre suite `pytest` indépendante.

Coût accepté en échange : plus de complexité opérationnelle (17 conteneurs à faire tourner, un
`docker-compose.yml` de ~350 lignes), latence réseau interne, et — jusqu'à récemment — état partagé
minimal (voir plus bas).

## Contrats partagés (`shared/dealpilot_shared`)

Tous les services dépendent d'un seul package Python partagé contenant les modèles Pydantic des
contrats inter-services (`PropertyRecord`, `DealState`, `RiskRegister`, `LandFeasibility`, etc.).

**Piège découvert et documenté** : modifier ce package ne suffit pas — chaque service embarque sa
propre copie construite au moment du build Docker. Oublier de reconstruire un service après un
changement de contrat partagé le laisse tourner avec un schéma obsolète, silencieusement (Pydantic
ignore les champs qu'il ne connaît pas au lieu de lever une erreur). Rencontré concrètement lors de
l'ajout du champ `address` à `LandConstraints` : l'orchestrator ignorait le champ jusqu'à sa
reconstruction explicite. Voir `RUNBOOK.md` pour la procédure de reconstruction complète.

### Provenance et traçabilité

Chaque valeur numérique du dossier (`FieldWithCandidates`) porte la liste de ses candidats avec leur
`Provenance` (type de source, référence, confiance, note). Si deux sources donnent des valeurs
différentes, aucune n'est silencieusement choisie : le champ est marqué `contested=true` et les deux
restent visibles avec leur origine. C'est le mécanisme central de traçabilité du système, testé
explicitement par les cas adverses `case_03` et `case_08` (`docs/eval_results.md`).

## Persistance

**État du dossier** : `AsyncSqliteSaver` (LangGraph checkpointer), fichier SQLite dans un volume
Docker (`orchestrator_db`). Remplace un `MemorySaver` en mémoire qui perdait tous les dossiers en
cours au moindre redémarrage du conteneur orchestrator.

**Pas de base de données métier partagée** : chaque service reste sans état propre au-delà de son
appel ; le seul état durable du système est celui du graphe LangGraph. C'est une simplification
assumée pour ce sprint — un vrai produit multi-utilisateurs voudrait une base Postgres partagée avec
un historique interrogeable indépendamment du graphe d'exécution (voir `docs/iteration_plan.md`).

## Fiabilité

- **Retry avec backoff** (`shared/dealpilot_shared/http_retry.py`) sur tous les appels vers des APIs
  tierces (Groq, Gemini, DVF, BAN, Apicarto) : jusqu'à 2 tentatives supplémentaires avant d'abandonner.
- **Dégradation gracieuse systématique** : chaque nœud du graphe orchestrator capture les échecs de
  son service en aval et les transforme en un fait d'erreur visible (`*_error`) plutôt que de
  laisser l'exception remonter. Voir `docs/eval_results.md` pour la découverte et la correction du
  point qui manquait initialement (`market`).
- **Verrou GPU inter-services** (`shared/dealpilot_shared/gpu_lock.py`) : un seul GPU disponible,
  partagé entre `interior-render` (SDXL) et `exterior-render` (Blender/Cycles) — deux conteneurs
  séparés qu'un simple `threading.Lock` local ne peut pas coordonner. Un verrou de fichier
  (`flock`) sur un volume Docker monté dans les deux services fait office de mutex cross-process.
  Ajouté après qu'un test de contention réel a montré un ralentissement mutuel de ~2× sans lui
  (VRAM à moins de 300 Mo de la limite de la carte) ; `interior-render` garde en plus son propre
  `threading.Lock` pour les requêtes concurrentes au sein du même processus.
- **Logging structuré avec ID de corrélation** (`shared/dealpilot_shared/logging_utils.py`) : chaque
  dossier (`deal_id`) est propagé en en-tête HTTP (`X-Correlation-ID`) à travers tous les appels
  inter-services, permettant de retrouver tout le parcours d'un dossier dans les logs combinés des
  17 services.

## Sources de données externes

| Source | Usage | Pourquoi celle-là |
|---|---|---|
| Groq (`openai/gpt-oss-120b`) | Extraction documentaire, résumé, agent de conception, analyse d'emplacement | LLM rapide et peu coûteux pour de l'extraction structurée |
| Google Gemini (`gemini-3.6-flash`) | Analyse visuelle | Groq n'a pas de modèle vision au moment du sprint |
| DVF (`files.data.gouv.fr/geo-dvf`) | Comparables de marché | Données de transactions réelles, open data officiel — pas de scraping d'annonces (non-goal explicite) |
| BAN (`api-adresse.data.gouv.fr`) | Géocodage d'adresse | Base d'adresses nationale officielle, gratuite |
| Geoportail de l'Urbanisme / Apicarto (`apicarto.ign.fr`) | Zone PLU réelle d'une parcelle | Registre officiel — donne l'identité de la zone, pas les règles chiffrées (le registre ne les expose pas nationalement en format machine-lisible) |
| Overpass API (OpenStreetMap) | Points d'intérêt du quartier | Open data, gratuit, couverture dense en France |
| Stable Diffusion XL (auto-hébergé) | Rendu photoréaliste intérieur/jardin/façade 360° | Gratuit et illimité une fois le modèle téléchargé, contrairement aux APIs payantes (Replicate testé puis abandonné pour cette raison) |
| Blender/Cycles (auto-hébergé, `exterior-render`) | Maquette 3D mesurable animée par phase de construction | Piste explorée pour un volume géométriquement exact ; conservée dans le dépôt mais retirée du parcours principal après comparaison visuelle avec le rendu SDXL — voir `docs/case_study.md` |

## Non-goals techniques (rappel)

Voir `docs/case_study.md` pour la liste complète des non-goals produit. Techniquement, cela se
traduit par : `listing_url` n'est jamais récupéré en direct (stocké comme simple référence de
provenance), aucune valorisation n'est présentée comme garantie, et le zonage réel n'est jamais
traduit en règles chiffrées automatiques.
