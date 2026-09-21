# DealPilot AI

Système intelligent d'acquisition, de promotion et de construction immobilière — France.

Transforme une opportunité immobilière (annonce + documents + photos) en dossier d'analyse
structuré et tracé : intelligence documentaire, analyse visuelle, comparables de marché,
souscription financière déterministe, registre de risques, stratégie d'offre et due diligence.
Inclut aussi un module promoteur/citoyen (faisabilité de terrain, maquette 3D, design IA
conversationnel, rendu intérieur/jardin photoréaliste).

**Ce que le système ne fait pas** : il ne décide jamais d'acheter à votre place, ne donne pas de
conseil juridique ou financier engageant, et ne certifie aucun état structurel. Voir
`docs/case_study.md` pour la liste complète des non-goals.

## Démarrage rapide (aucune connaissance technique requise)

### Pré-requis

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installé et lancé.
- Une clé API [Groq](https://console.groq.com/keys) (gratuite) et une clé
  [Google Gemini](https://aistudio.google.com/apikey) (gratuite).
- Pour le rendu 3D intérieur/jardin (optionnel) : un GPU NVIDIA avec au moins 8 Go de VRAM. Sans
  GPU, tout le reste de l'application fonctionne normalement.

### Installation (3 étapes)

1. Copier `.env.example` vers `.env` et renseigner `GROQ_API_KEY` et `GEMINI_API_KEY`.
2. Ouvrir un terminal dans le dossier du projet et lancer :
   ```
   docker compose up -d
   ```
   (premier lancement : plusieurs minutes, le temps de télécharger les images)
3. Ouvrir [http://localhost:8501](http://localhost:8501) dans le navigateur.

C'est tout. Choisir son rôle en haut de la page (Investisseur / Promoteur / Citoyen) et remplir le
formulaire à gauche.

### Arrêter l'application

```
docker compose down
```

Les dossiers déjà analysés restent enregistrés (base SQLite persistée dans un volume Docker) et
seront de nouveau accessibles au prochain démarrage.

## Les trois rôles

- **🏢 Investisseur** : soumet un bien locatif existant (annonce, documents, photos), obtient
  l'analyse complète en 10 étapes, peut simuler une contre-offre, comparer plusieurs dossiers,
  générer un résumé en langage simple, et exporter le dossier en PDF ou Excel.
- **🏗️ Promoteur** : évalue la faisabilité de construction sur un terrain (avec zone PLU réelle si
  une adresse est donnée), conçoit un bâtiment via un agent conversationnel, visualise une maquette
  3D avec simulation de chantier (4D/5D), génère des rendus intérieur/jardin photoréalistes.
- **🏠 Citoyen** : même module que le promoteur, pour un particulier qui veut comprendre ce qu'il
  peut construire sur son terrain.

## Pour aller plus loin

- `docs/architecture.md` — comment le système est construit et pourquoi.
- `docs/case_study.md` — utilisateur cible, flux manuel actuel, non-goals, métrique de succès.
- `docs/eval_results.md` — résultats des tests d'évaluation, y compris scénarios de panne.
- `docs/ai_collaboration_note.md` — comment ce projet a été construit avec l'assistance d'une IA.
- `docs/iteration_plan.md` — ce qui est prévu pour la suite.
- `RUNBOOK.md` — pour l'exploitant : variables d'environnement, pannes connues, comment déboguer.

## Licence des composants tiers

Modèle Stable Diffusion 1.5/XL sous licence CreativeML OpenRAIL-M / Stability AI Community License —
usage prototype/recherche, voir la licence du modèle avant tout usage commercial.
