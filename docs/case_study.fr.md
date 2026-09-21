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
plus un module de faisabilité de terrain/construction neuve (promoteur/citoyen) avec vue 360°
photoréaliste du bâtiment, rendu IA intérieur/jardin, export PDF/Excel, résumé en langage naturel,
simulateur de contre-offre, comparaison multi-biens.

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

## Architecture et arbitrages majeurs

17 microservices FastAPI (dont un frontend Streamlit) plutôt qu'un monolithe — choix assumé dès le
départ pour isoler chaque capacité métier (extraction documentaire, vision, marché, finance, risque,
offre, due diligence) : remplacer un fournisseur LLM déprécié, ou faire tomber un service sans
faire tomber tout le pipeline, ne touche qu'une seule brique. Coût accepté en échange : plus de
complexité opérationnelle (17 conteneurs, un piège récurrent documenté — chaque service embarque sa
propre copie du contrat de données partagé et doit être reconstruit après tout changement de schéma).

Arbitrages notables :
- **Moteur financier déterministe** (jamais délégué au LLM) — la précision des calculs ne doit rien
  au hasard d'une génération de texte.
- **Provenance systématique** : chaque valeur numérique porte ses candidats et leurs sources ; deux
  sources contradictoires ne sont jamais résolues silencieusement (`contested=true`), elles restent
  visibles toutes les deux.
- **Persistance** : `AsyncSqliteSaver` (LangGraph) plutôt qu'un état en mémoire — un redémarrage du
  conteneur orchestrateur ne perd plus les dossiers en cours.
- **Visuels — pivot assumé en cours de sprint** : une première version générait une maquette 3D
  mesurable (Blender/Cycles, animée par phase de construction). Confrontée à la qualité photoréaliste
  du rendu SDXL déjà utilisé pour l'intérieur, la maquette 3D a été jugée visuellement insuffisante
  pour l'usage réel ; elle a été remplacée dans le parcours principal par une vue à 360° générée par
  IA (8 angles, seed partagé pour la cohérence visuelle). Le code Blender reste dans le dépôt mais
  n'est plus sur le chemin principal — un exemple concret d'arbitrage qualité perçue vs exactitude
  géométrique, tranché en faveur de la qualité perçue pour ce cas d'usage de vente/présentation.
- **Fiabilité GPU** : un seul GPU partagé entre deux capacités de génération d'image (SDXL et le
  pipeline Blender resté dans le dépôt) — verrouillé par un verrou de fichier inter-processus après
  qu'un test de contention réel a montré un ralentissement mutuel de ~2× sans lui.

Détail complet : `docs/architecture.md`.

## Travail délégué à l'IA et jugement humain conservé

Ce projet a été construit avec Claude Code comme assistant de développement. Délégué à l'IA :
génération de code une fois les choix techniques arrêtés, rédaction de la documentation, conception
des cas de test adverses, diagnostic de bugs. Conservé côté humain : le choix de l'architecture
microservices, le choix du marché (France résidentiel locatif), le périmètre complet en 10 étapes
dès le premier jour, l'arbitrage final entre profondeur technique et documentation, et la décision de
pivoter la maquette 3D vers la vue 360° après évaluation visuelle comparative. Chaque affirmation de
l'IA a été vérifiée avant d'être acceptée (exemples concrets, dont un cas où une hypothèse de l'IA
sur la cause d'un échec de test s'est révélée fausse après reproduction manuelle).

Détail complet, y compris ce qui a été rejeté ou corrigé : `docs/ai_collaboration_note.md`.

## Échecs trouvés, changements, résultats et limites

**Bug réel trouvé et corrigé** : le test de panne du service `market` a révélé un plantage complet du
pipeline (HTTP 500) au lieu d'une dégradation gracieuse — corrigé, puis le même filet de sécurité a
été étendu préventivement à 6 autres points du système qui présentaient la même faiblesse non testée,
avant qu'un incident réel ne la révèle.

**Bug de cadrage trouvé et corrigé** (vue 360°) : les premières générations photoréalistes du
bâtiment cadraient en gros plan sur 1-2 fenêtres au lieu de montrer le bâtiment entier. Cause racine :
le prompt dépassait la limite de 77 tokens du modèle de texte de SDXL (CLIP), et les instructions de
cadrage large étaient précisément la partie tronquée. Corrigé en réordonnant le prompt pour que les
instructions critiques arrivent avant la coupure — vérifié visuellement avant/après.

**Limitation connue, non corrigée** : aucune règle ne détecte un loyer déclaré anormalement élevé ou
bas par rapport au marché (`risk/app/rules.py`) — un loyer irréaliste produit des indicateurs
financiers flatteurs sans avertissement. Documenté et reporté au plan d'itération plutôt que masqué.

**Limitation structurelle assumée** : aucun essai utilisateur réel chronométré n'a été conduit (accès
à un vrai investisseur non disponible pendant le sprint) — le gain de temps affiché reste une
estimation qualitative, explicitement signalée comme telle plutôt que présentée comme une preuve.

Résultats mesurés complets (29/29 vérifications, 1 limitation documentée) : `docs/eval_results.md`.

## Plan d'itération — 2 prochaines semaines

Priorités, dans l'ordre : (1) règle de plausibilité loyer/marché — la seule lacune fonctionnelle
connue et non corrigée ; (2) essai utilisateur réel chronométré avec 2-3 investisseurs pour remplacer
l'estimation qualitative par une mesure réelle ; (3) base de données partagée interrogeable
indépendamment du graphe d'exécution ; (4) couverture de tests unitaires pour les 6 services qui en
sont encore dépourvus (`intake`, `document-intel`, `vision`, `market`, `design-agent`,
`exterior-render`) ; (5) plan de fiabilité GPU pour un usage multi-utilisateur simultané.

Détail complet avec métriques d'adoption et de qualité à suivre : `docs/iteration_plan.md`.
