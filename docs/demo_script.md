# Script de démo — 5 minutes

Destiné à l'enregistrement d'une vidéo de présentation. Chronométrage indicatif entre parenthèses.

## 1. Le problème et la baseline (0:00 – 0:45)

> "Un investisseur immobilier qui trouve un immeuble à acheter passe aujourd'hui plusieurs heures,
> réparties sur plusieurs jours, à lire manuellement des documents PDF, comparer des loyers, chercher
> des prix comparables, et modéliser un cash-flow dans Excel — sans filet contre l'erreur humaine ou
> l'oubli. [Montrer `docs/case_study.md`, le tableau des 10 étapes manuelles à l'écran quelques
> secondes.] DealPilot AI transforme ça en un dossier structuré et tracé, en quelques minutes,
> sans jamais décider à la place de l'investisseur."

## 2. Flux en direct sur un cas réel (0:45 – 3:00)

Utiliser le cas synthétique `case_01_normal_complete` (ou un dossier équivalent rempli en direct) :

1. Ouvrir [http://localhost:8501](http://localhost:8501), rôle **Investisseur**.
2. Remplir le formulaire : annonce, prix, loyer, upload des documents (`etat_locatif`,
   `titre_de_propriete`) et d'une photo.
3. Soumettre — montrer le dossier progresser à travers les 10 étapes (documents, vision, marché,
   finance, risques, offre, due diligence).
4. Une fois terminé, montrer :
   - Le **registre de risques** avec sévérité et preuve associée.
   - La **stratégie d'offre** (prix cible, prix max, conditions).
   - Un champ **contesté** si présent (ex. loyer incohérent entre deux sources) — souligner que le
     système ne choisit jamais silencieusement une valeur, il montre les deux avec leur origine.
5. Cliquer sur **"Résumé en langage simple"** — montrer le résumé en français courant.
6. Simuler une **contre-offre** — montrer la comparaison avant/après.
7. Exporter en **PDF** — ouvrir le fichier généré brièvement.

## 3. UX non-développeur (3:00 – 3:30)

> "Tout ceci tourne sans ligne de commande pour l'utilisateur final — trois étapes d'installation
> Docker documentées dans `README.md`, puis tout se passe dans le navigateur. Les trois rôles
> (investisseur, promoteur, citoyen) ont chacun leur propre parcours adapté à leur besoin, pas une
> interface technique générique."

Optionnel si le temps le permet : basculer rapidement sur le rôle **Promoteur/Citoyen**, montrer la
faisabilité de terrain avec la vraie zone PLU récupérée depuis une adresse, et un rendu intérieur
généré par IA.

## 4. Évaluation et gestion des pannes (3:30 – 4:30)

> "Le système a été testé contre 11 cas synthétiques, dont 9 scénarios adverses représentant les
> modes de panne identifiés dès le départ : documents contradictoires, documents manquants, loyer
> anormal, défaut visuel ambigu, panne de service externe, financement non viable, tentative
> d'injection de prompt dans un document. [Montrer `docs/eval_results.md`, le tableau de résumé.]
> 29 vérifications passées, 0 échec, une limitation connue documentée plutôt que cachée."

> "Un exemple concret : le test de panne du service de marché a révélé un vrai bug — le pipeline
> plantait entièrement au lieu de continuer sans les comparables. Corrigé, puis le même filet de
> sécurité a été ajouté préventivement sur 6 autres points du système qui avaient la même faiblesse
> non testée. [Montrer la section 'Ce que cette passe de tests a trouvé et corrigé'.]"

## 5. Résultats et limite principale (4:30 – 5:00)

> "Ce système ne remplace jamais le jugement de l'investisseur — il ne décide jamais d'acheter, ne
> donne pas de conseil juridique engageant, et ne certifie aucun état structurel. La limite
> actuelle la plus importante : aucune règle ne détecte encore un loyer anormalement élevé ou bas par
> rapport au marché — documentée dans `docs/eval_results.md` et planifiée comme première priorité
> dans `docs/iteration_plan.md`. Un essai réel avec de vrais investisseurs, chronométré contre leur
> flux manuel actuel, est la seconde priorité pour remplacer l'estimation qualitative de gain de temps
> par une mesure réelle."

## Notes pour l'enregistrement

- Préparer les conteneurs à l'avance (`docker compose up -d`, attendre que tout soit `healthy`) pour
  ne pas perdre de temps de démo sur un démarrage à froid.
- Le rendu SDXL prend ~30-60s — si démontré, le lancer puis continuer à parler pendant la génération
  plutôt que d'attendre en silence.
- Avoir `docs/eval_results.md` et `docs/case_study.md` déjà ouverts dans des onglets pour les montrer
  sans chercher.
