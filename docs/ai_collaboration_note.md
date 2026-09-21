# Note de collaboration avec l'IA

Ce projet a été construit avec Claude Code (Anthropic) comme assistant de développement, sur 5 jours,
en solo (pas d'équipe). Cette note documente honnêtement ce qui a été délégué, ce qui a été vérifié,
ce qui a été rejeté ou corrigé, et quelles décisions m'appartiennent réellement — critère explicite
du barème de ce sprint.

## Ce qui a été délégué à l'IA

- **Génération de code** pour chaque microservice une fois l'architecture et les choix techniques
  arrêtés (FastAPI, Pydantic, LangGraph, ReportLab/openpyxl, clients HTTP vers Groq/Gemini/DVF/BAN/
  Apicarto).
- **Rédaction de documentation** : ce fichier, ainsi que `README.md`, `RUNBOOK.md`,
  `docs/architecture.md`, `docs/case_study.md`, `docs/demo_script.md`, `docs/iteration_plan.md`.
- **Conception des cas de test synthétiques adversariaux** (11 cas, voir `data/synthetic_cases/`) —
  proposés par l'IA à partir de la liste de modes de panne du brief d'origine, puis vérifiés par moi
  contre le comportement réel du système avant exécution.
- **Diagnostic de bugs** : lecture de logs, formulation d'hypothèses, correctifs proposés.

## Ce qui a été vérifié avant d'être accepté

Rien n'a été accepté sur la seule confiance d'une affirmation de l'IA. Trois exemples concrets de
vérification qui a changé le résultat :

1. **Le cas de test `case_01`** : l'IA avait initialement nommé les fichiers de documents synthétiques
   `case_01_lease_summary.txt` / `case_01_title_deed.txt`. Avant de lancer quoi que ce soit, j'ai
   demandé une lecture du code réel de détection de documents manquants
   (`services/risk/app/rules.py`) — qui s'est révélée comparer des mots-clés français
   (« titre », « etat locatif ») contre le **nom du fichier**, pas son contenu. Les fichiers ont été
   renommés avant la première exécution, évitant un faux résultat de test.
2. **Le bug de zonage réel retournant `null`** : l'IA a proposé une hypothèse (l'orchestrateur n'avait
   pas été reconstruit après un changement du contrat Pydantic partagé). Vérifiée en inspectant
   directement le schéma chargé dans le conteneur avant/après reconstruction — confirmée, corrigée,
   et documentée dans `docs/architecture.md` comme piège récurrent de l'architecture microservices
   choisie.
3. **Le "bug" du cas 10** (financement non viable) : un premier passage d'évaluation l'a signalé en
   échec. Plutôt que d'accepter la théorie de l'IA sur la cause à la première tentative, j'ai demandé
   une reproduction isolée du même appel — qui a réussi. La vraie cause (timing du harnais de test,
   pas un bug produit) n'a été retenue qu'après cette vérification, pour éviter de corriger du code
   qui n'était pas cassé.
4. **Le cadrage des images de la vue 360°** : après un premier correctif de prompt jugé insuffisant à
   l'usage (images toujours trop resserrées), l'IA a proposé un deuxième correctif — qui n'a *presque
   rien changé*. Plutôt que d'en rester là, j'ai demandé une inspection des logs bruts du modèle, qui a
   révélé la vraie cause : le prompt dépassait la limite de 77 tokens du tokenizer CLIP, et c'est
   précisément la partie ajoutée par le premier correctif qui se faisait couper. Le correctif final
   (réordonner le prompt) n'a été appliqué qu'après cette vérification par les logs, pas par simple
   confiance dans la deuxième tentative de l'IA.

## Ce qui a été rejeté ou corrigé

- **Approche de rendu d'images initiale** : Replicate (API payante) a été testé puis explicitement
  écarté en faveur d'un modèle Stable Diffusion auto-hébergé, pour éviter un coût récurrent non
  maîtrisé sur un usage potentiellement fréquent.
- **`enable_vae_slicing()`** proposé par l'IA lors du passage à SDXL a levé une `AttributeError`
  (méthode inexistante sur cette classe de pipeline) — retiré immédiatement plutôt que contourné.
- **Le calcul du fichier `docs/eval_results.md`** est entièrement généré par script
  (`eval/run_eval.py`) à partir de résultats réels obtenus en frappant le système réellement démarré,
  jamais rédigé ou rempli à la main par l'IA — pour garantir qu'aucun résultat n'est inventé.
- **Aucun essai baseline humain chronométré n'a été fabriqué** : quand il est devenu clair qu'aucun
  vrai investisseur n'était disponible pendant le sprint, le choix a été de documenter cette limite
  explicitement dans `docs/eval_results.md` plutôt que de laisser l'IA produire un chiffre baseline
  inventé pour combler le trou.
- **La maquette 3D mesurable (Blender/Cycles)** — un chantier entier (portage de la géométrie,
  animation de phases de construction, HDRI, verrou GPU inter-services) a été construit et vérifié
  fonctionnel, puis **rejeté du parcours principal** après comparaison visuelle directe avec le rendu
  photoréaliste SDXL déjà utilisé pour l'intérieur : la précision géométrique ne compensait pas
  l'écart de qualité perçue pour cet usage de vente/présentation. Le code reste dans le dépôt (pas
  supprimé, juste débranché du parcours utilisateur) plutôt que jeté, au cas où l'exactitude
  dimensionnelle redevienne prioritaire.

## Décisions qui m'appartiennent

- **Le choix de l'architecture microservices** plutôt qu'un monolithe, dès le départ du projet — un
  choix délibéré de complexité opérationnelle accrue en échange d'isolation de panne et de
  remplaçabilité des fournisseurs LLM, assumé consciemment.
- **Le choix du marché (France, immobilier résidentiel locatif)** plutôt que d'autres marchés
  envisagés, pour la richesse des diagnostics réglementaires obligatoires (DPE, amiante, plomb, ERP)
  qui donnent une vraie structure au module d'intelligence documentaire.
- **Le périmètre complet du flux en 10 étapes** dès le premier jour, plutôt qu'une version réduite —
  un choix qui a augmenté le risque d'exécution sur 5 jours, assumé en connaissance de cause.
- **La priorisation, avant la documentation finale, du renforcement technique** (file GPU, retry,
  persistance, logging corrélé, distinction santé/modèle chargé) et de nouveaux usages produit
  (export, comparaison, checklist administrative, résumé, contre-offre) plutôt que de documenter un
  système figé plus tôt — pari que la profondeur produit pèserait plus que des livrables écrits plus
  longs.
- **La décision d'étendre un correctif de fiabilité à 6 services supplémentaires** dès qu'un bug réel
  a été trouvé par test de panne sur un seul service (`market`), plutôt que de corriger seulement le
  cas trouvé — jugement qu'un même trou architectural répété ailleurs valait la peine d'être
  anticipé avant qu'un incident réel ne le révèle service par service.
- **L'arbitrage final entre profondeur technique et documentation** dans le temps restreint du
  sprint, service par service, approuvé explicitement à chaque étape plutôt que délégué à l'IA en
  bloc.
- **Le pivot de la maquette 3D vers la vue 360° IA** — après avoir vu les deux résultats côte à côte,
  la décision de retirer la maquette mesurable du parcours principal au profit d'un rendu
  photoréaliste (moins précis géométriquement, mais nettement plus convaincant visuellement) a été
  une décision produit, pas une décision technique déléguée — l'IA avait construit les deux options
  correctement, le choix entre elles m'appartenait.

## Limite de cette collaboration

Ce projet a été construit en solo avec un seul relecteur (moi-même) et un assistant IA — aucune revue
de code par un pair humain indépendant n'a eu lieu, contrainte assumée du format de ce sprint. La
vérification de la partie 2 de cette note (« ce qui a été vérifié ») compense partiellement ce
manque mais ne le remplace pas.
