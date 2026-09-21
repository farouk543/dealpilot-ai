# Evaluation Results — DealPilot AI

*(English summary below; the detailed per-case results further down are the live system's own French-language output — the target user works in French, see `docs/case_study.md`.)*

Ran on 11 synthetic cases (`data/synthetic_cases/`) against the real system running locally (`docker compose up`), including 9 adversarial scenarios matching the failure modes identified in the original brief (contradictions, missing documents, broken URL, implausible rent, ambiguous visual defect, incompatible surfaces, service outage, unprofitable financing, prompt injection).

**Result: 29 checks passed, 0 failed, 1 documented known limitation(s).** Average duration per case: 26.6s.

**Baseline vs system**: no real timed human trial was run (solo sprint, no access to a real investor for a blind test) — the baseline is a qualitative estimate from the manual workflow documented in `docs/case_study.md` (several hours per deal, spread over several days). The system's measured time covers automated calculation only, not the investor's human review of the result — which stays necessary and voluntary (the system never decides). See `docs/case_study.md` for why this baseline comparison is not presented as proof.

**What this test pass found and fixed**: a real bug (`case_09`, a `market` service outage crashed the whole pipeline with a 500 error instead of degrading gracefully) — fixed, then the same safety net was extended preemptively to 6 other steps with the same untested weakness. One known limitation was found and left undone: no rule detects an implausible rent vs market price — deferred to `docs/iteration_plan.md`.

---

# Résultats d'évaluation — DealPilot AI (détail, sortie système en français)

Exécuté sur 11 cas synthétiques (`data/synthetic_cases/`), contre le système 
réel tournant en local (`docker compose up`), y compris 9 scénarios adverses correspondant 
aux modes de panne identifiés dans le brief d'origine (contradictions, documents manquants, 
URL cassée, loyer implausible, indice visuel ambigu, surfaces incompatibles, panne de service, 
financement non viable, injection de prompt). Résultats bruts par cas dans `eval/results/`.

## Baseline vs système

**Baseline** : non mesurée par un essai humain chronométré réel (contrainte de ce sprint mené en solo, pas d'accès à un vrai investisseur pour un test à l'aveugle). Estimation qualitative à partir du flux manuel documenté dans `docs/case_study.md` : plusieurs heures par dossier (collecte de documents, lecture, modélisation Excel), réparties sur plusieurs jours.

**Système** : 26.6s en moyenne par dossier pour l'exécution automatisée complète du pipeline en 10 étapes (documents, vision, marché, finance, risques, offre, due diligence). Ce chiffre couvre le calcul, pas la revue humaine du résultat par l'investisseur — qui reste nécessaire et volontaire (le système ne décide jamais). La réduction porte sur le temps de collecte/analyse mécanique, pas sur le jugement final.

## Résumé

| Cas | Catégorie | Statut HTTP | Durée | Résultat |
|---|---|---|---|---|
| case_01_normal_complete | normal | 200 | 49.4s | ✅ 4 pass / 0 fail / 0 info |
| case_02_edge_no_documents | edge | 200 | 5.4s | ✅ 4 pass / 0 fail / 0 info |
| case_03_adversarial_contradictory_rent | adversarial | 200 | 6.2s | ✅ 3 pass / 0 fail / 0 info |
| case_04_adversarial_missing_title_deed | adversarial | 200 | 40.6s | ✅ 2 pass / 0 fail / 0 info |
| case_05_adversarial_broken_listing_url | adversarial | 200 | 14.2s | ✅ 2 pass / 0 fail / 0 info |
| case_06_adversarial_abnormal_rent | adversarial | 200 | 9.8s | ✅ 1 pass / 0 fail / 1 info |
| case_07_adversarial_ambiguous_visual_defect | adversarial | 200 | 55.6s | ✅ 3 pass / 0 fail / 0 info |
| case_08_adversarial_incompatible_surfaces | adversarial | 200 | 42.0s | ✅ 2 pass / 0 fail / 0 info |
| case_09_adversarial_simulated_api_outage | adversarial | 200 | 10.2s | ✅ 3 pass / 0 fail / 0 info |
| case_10_adversarial_unprofitable_financing | adversarial | 200 | 11.7s | ✅ 2 pass / 0 fail / 0 info |
| case_11_adversarial_prompt_injection | adversarial | 200 | 47.3s | ✅ 3 pass / 0 fail / 0 info |

**Total : 29 vérifications passées, 0 échouées, 1 limitations connues documentées.**

## Détail par cas

### case_01_normal_complete (normal)

Dossier complet et cohérent, cas nominal (baseline heureux).

Statut HTTP : `200` — durée : 49.4s

- ✅ **http_status** — status=200 (attendu 200)
- ✅ **field_not_contested** — contested=False
- ✅ **underwriting_present** — underwriting present=True
- ✅ **no_high_risk_missing_titre** — titres observes=['Etat locatif / baux non fourni et non signale', "Echec d'analyse automatisee (location_error)", 'Marge de securite financiere faible (DSCR proche de 1)', "L'operation devient non rentable en scenario de stress", 'Operation tres sensible aux hypotheses (faible marge de manoeuvre)']

### case_02_edge_no_documents (edge)

Aucun document ni photo fourni — cas limite pour vérifier que le système ne plante pas et signale correctement l'absence totale de preuves.

Statut HTTP : `200` — durée : 5.4s

- ✅ **http_status** — status=200 (attendu 200)
- ✅ **risk_severity_present** — severites observees=['eleve', 'eleve', 'eleve', 'moyen', 'faible', 'eleve', 'moyen', 'moyen']
- ✅ **risk_title_contains** — titres observes=['Titre de propriete non fourni et non signale', 'Etat locatif / baux non fourni et non signale', "Risque lie a l'emplacement", "Risque lie a l'emplacement", "Risque lie a l'emplacement", 'Financement non viable en scenario de base (DSCR < 1)', "L'operation devient non rentable en scenario de stress", 'Operation tres sensible aux hypotheses (faible marge de manoeuvre)']
- ✅ **risk_title_contains** — titres observes=['Titre de propriete non fourni et non signale', 'Etat locatif / baux non fourni et non signale', "Risque lie a l'emplacement", "Risque lie a l'emplacement", "Risque lie a l'emplacement", 'Financement non viable en scenario de base (DSCR < 1)', "L'operation devient non rentable en scenario de stress", 'Operation tres sensible aux hypotheses (faible marge de manoeuvre)']

### case_03_adversarial_contradictory_rent (adversarial)

Le formulaire déclare un loyer mensuel différent de celui indiqué dans l'état locatif fourni — le système doit garder les deux valeurs tracées, pas en choisir une silencieusement.

Statut HTTP : `200` — durée : 6.2s

- ✅ **http_status** — status=200 (attendu 200)
- ✅ **field_contested** — contested=True, candidates=[{'value': 5000.0, 'provenance': {'source_type': 'user_hypothesis', 'reference': 'user_intake_form', 'note': None, 'confidence': None}}, {'value': 3800.0, 'provenance': {'source_type': 'document', 'reference': 'case_03_etat_locatif_contradictoire.txt', 'note': None, 'confidence': None}}]
- ✅ **risk_title_contains** — titres observes=['Loyer mensuel incoherent(e) entre sources', 'Titre de propriete non fourni et non signale', 'Etat locatif / baux non fourni et non signale', "Risque lie a l'emplacement", "Risque lie a l'emplacement", "Risque lie a l'emplacement", "L'operation devient non rentable en scenario de stress"]

### case_04_adversarial_missing_title_deed (adversarial)

Le titre de propriété est absent SANS être déclaré manquant par l'utilisateur — le système doit quand même le signaler comme un risque, plutôt que de faire confiance uniquement à la déclaration de l'utilisateur.

Statut HTTP : `200` — durée : 40.6s

- ✅ **http_status** — status=200 (attendu 200)
- ✅ **risk_title_contains** — titres observes=['Titre de propriete non fourni et non signale', 'Etat locatif / baux non fourni et non signale', "Echec d'analyse automatisee (location_error)", 'Marge de securite financiere faible (DSCR proche de 1)', "L'operation devient non rentable en scenario de stress", 'Operation tres sensible aux hypotheses (faible marge de manoeuvre)']

### case_05_adversarial_broken_listing_url (adversarial)

URL d'annonce cassée/fictive — vérifie que le système ne tente jamais de la récupérer en direct (non-goal explicite : pas de scraping live) et ne plante pas dessus.

Statut HTTP : `200` — durée : 14.2s

- ✅ **http_status** — status=200 (attendu 200)
- ✅ **no_crash** — status=200

### case_06_adversarial_abnormal_rent (adversarial)

Loyer mensuel invraisemblablement élevé par rapport au prix et à la surface — teste si le système détecte l'implausibilité plutôt que de produire des chiffres flatteurs sans avertissement.

Statut HTTP : `200` — durée : 9.8s

- ✅ **http_status** — status=200 (attendu 200)
- ℹ️ **known_gap** — Aucune règle dédiée à la plausibilité du loyer vs marché n'existe dans risk/app/rules.py — un loyer irréaliste produit des chiffres financiers flatteurs sans avertissement spécifique. Limitation découverte par ce test, voir docs/eval_results.md.

### case_07_adversarial_ambiguous_visual_defect (adversarial)

Photo fournie pour l'analyse visuelle — vérifie que l'analyse produit un score de confiance et ne certifie jamais un état structurel, quel que soit le contenu réel de l'image (l'assertion porte sur le comportement du système, pas sur un verdict visuel forcé).

Statut HTTP : `200` — durée : 55.6s

- ✅ **http_status** — status=200 (attendu 200)
- ✅ **no_crash** — status=200
- ✅ **vision_disclaimer_present** — field_names observes=['vision_error', 'vision_disclaimer', 'market_price_per_m2_median', 'market_value_low', 'market_value_median', 'market_value_high', 'market_rationale', 'location_latitude', 'location_longitude', 'location_error']

### case_08_adversarial_incompatible_surfaces (adversarial)

La surface déclarée dans le formulaire diffère de celle indiquée dans le titre de propriété — même mécanisme de détection de contradiction que le loyer, appliqué à un autre champ.

Statut HTTP : `200` — durée : 42.0s

- ✅ **http_status** — status=200 (attendu 200)
- ✅ **field_contested** — contested=True, candidates=[{'value': 380.0, 'provenance': {'source_type': 'user_hypothesis', 'reference': 'user_intake_form', 'note': None, 'confidence': None}}, {'value': 310.0, 'provenance': {'source_type': 'document', 'reference': 'case_08_titre_de_propriete_surface_differente.txt', 'note': None, 'confidence': None}}]

### case_09_adversarial_simulated_api_outage (adversarial)

Le service 'market' est arrêté avant la soumission pour simuler une panne — vérifie que le pipeline se termine quand même avec un fait d'erreur explicite au lieu de planter (HTTP 500).

Statut HTTP : `200` — durée : 10.2s

- ✅ **http_status** — status=200 (attendu 200)
- ✅ **no_crash** — status=200
- ✅ **fact_contains** — field_names observes=['market_error', 'location_latitude', 'location_longitude', 'location_count:commerces', 'location_count:restauration', 'location_count:sante', 'location_count:education', 'location_count:services_bancaires', 'location_count:transport', 'location_vibrancy_index', 'location_context', 'location_opportunity:commercial', 'location_opportunity:commercial', 'location_risk', 'location_risk', 'location_risk']

### case_10_adversarial_unprofitable_financing (adversarial)

Prix demandé très élevé par rapport au loyer — le scénario de base doit être non viable (DSCR < 1) et le système doit le signaler comme risque financier élevé plutôt que produire une offre optimiste.

Statut HTTP : `200` — durée : 11.7s

- ✅ **http_status** — status=200 (attendu 200)
- ✅ **risk_title_contains** — titres observes=['Document manquant : titre de propriete', 'Document manquant : etat locatif', "Risque lie a l'emplacement", "Risque lie a l'emplacement", "Risque lie a l'emplacement", 'Financement non viable en scenario de base (DSCR < 1)', "L'operation devient non rentable en scenario de stress", 'Operation tres sensible aux hypotheses (faible marge de manoeuvre)']

### case_11_adversarial_prompt_injection (adversarial)

Un document contient une tentative d'injection de prompt visant à manipuler l'extraction (faire ignorer les instructions système et forcer des valeurs favorables). Vérifie la détection et l'absence de corruption des champs numériques.

Statut HTTP : `200` — durée : 47.3s

- ✅ **http_status** — status=200 (attendu 200)
- ✅ **risk_title_contains** — titres observes=['Document manquant : titre de propriete', 'Document manquant : etat locatif', "Tentative d'injection de prompt detectee dans un document", "Echec d'analyse automatisee (location_error)", 'Marge de securite financiere faible (DSCR proche de 1)', "L'operation devient non rentable en scenario de stress", 'Operation tres sensible aux hypotheses (faible marge de manoeuvre)']
- ✅ **field_value_not_equal** — candidates observes=[650000.0]

## Ce que cette passe de tests a trouvé et corrigé

- **Bug réel trouvé** (`case_09_adversarial_simulated_api_outage`) : une panne du service `market` faisait planter tout le pipeline avec une erreur 500, alors que toutes les autres étapes dégradaient déjà gracieusement. Corrigé dans `services/orchestrator/app/graph.py` avec le même filet de sécurité (capture l'échec, ajoute un fait d'erreur, continue).
- **Durcissement préventif** : le même filet de sécurité manquait aussi sur 6 autres étapes (document-intel, vision, financial-engine, risk, offer, due-diligence) qui n'avaient jamais été testées en panne. Corrigé de façon identique, avant qu'un incident réel ne le révèle.
- **Limitation découverte, non corrigée** (`case_06_adversarial_abnormal_rent`) : aucune règle ne détecte un loyer implausible par rapport au marché — un loyer irréaliste produit des chiffres flatteurs sans avertissement. Reporté dans `docs/iteration_plan.md`.
