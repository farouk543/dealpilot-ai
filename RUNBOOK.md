# RUNBOOK — DealPilot AI

Pour l'exploitant du système (pas pour l'utilisateur final — voir `README.md` pour ça).

## Démarrer / arrêter

```
docker compose up -d          # démarre tout
docker compose down           # arrête tout (les données persistées restent dans les volumes)
docker compose ps             # état de chaque service
docker compose logs -f <nom>  # logs en direct d'un service
```

## Variables d'environnement (`.env`)

| Variable | Obligatoire | Description |
|---|---|---|
| `GROQ_API_KEY` | Oui | Extraction documentaire, résumé, agent de conception, analyse d'emplacement |
| `GEMINI_API_KEY` | Oui | Analyse visuelle (Groq n'a pas de modèle vision) |
| `GROQ_MODEL` | Non (défaut `openai/gpt-oss-120b`) | Modèle Groq — les modèles Groq sont dépréciés régulièrement, voir plus bas |
| `GEMINI_MODEL` | Non (défaut `gemini-3.6-flash`) | Idem pour Gemini |
| `SD_MODEL_ID` | Non (défaut `stabilityai/stable-diffusion-xl-base-1.0`) | Modèle de rendu intérieur/jardin |
| `DVF_YEARS` | Non (défaut `2023,2022,2021`) | Années de transactions DVF à charger |

Aucune clé n'est nécessaire pour le zonage réel (Apicarto/IGN), la géolocalisation (BAN), les
comparables (DVF), ou le rendu 3D — toutes ces sources sont gratuites et sans authentification.

## Pannes connues et comment les reconnaître

### Un service reconstruit ne prend pas en compte un changement de contrat partagé

**Symptôme** : un champ ajouté à `shared/dealpilot_shared/` (ex: un nouveau champ Pydantic) semble
ignoré par un service, sans erreur.

**Cause** : ce service n'a pas été reconstruit après le changement — sa copie du package partagé
est obsolète.

**Correction** :
```
docker compose build <service-concerné>
docker compose up -d --force-recreate <service-concerné>
```
Vérifier que le nouveau champ est bien présent :
```
docker run --rm --entrypoint /app/.venv/bin/python dealpilot-ai-<service> \
  -c "from dealpilot_shared import LandConstraints; print(list(LandConstraints.model_fields.keys()))"
```
**Règle générale** : après tout changement dans `shared/`, reconstruire *tous* les services qui
l'utilisent (en pratique : tous), pas seulement celui qu'on modifie directement.

### `docker compose build` échoue avec `docker-credential-desktop: executable file not found`

**Cause** : Docker Desktop régénère parfois `credsStore: "desktop"` dans
`~/.docker/config.json`, qui référence un utilitaire d'authentification cloud non nécessaire pour
des images publiques.

**Correction** : retirer la ligne `"credsStore": "desktop",` de `~/.docker/config.json`, puis
relancer le build.

**Piège** : cette erreur peut se produire silencieusement au milieu d'un pipe (`docker compose build
X | tail -N`), qui masque le vrai code de sortie. Toujours vérifier le code de sortie réel de
`docker compose build`, pas seulement l'absence de sortie visible.

### Mémoire WSL2/Docker Desktop insuffisante (Windows)

**Symptôme** : des builds ou des générations GPU échouent ou deviennent extrêmement lents sans
message d'erreur clair ; `vmmem` consomme toute la limite configurée.

**Correction** :
1. Augmenter la limite dans `%UserProfile%\.wslconfig` :
   ```
   [wsl2]
   memory=11GB
   ```
2. `wsl --shutdown` puis relancer Docker Desktop.
3. Si le problème persiste, fermer les applications gourmandes en RAM sur l'hôte (le pipeline de
   génération d'image occupe temporairement plusieurs Go pendant le chargement du modèle sur GPU).

**Cas rencontré : tous les conteneurs crashent en même temps (code 255)**. Sous pression mémoire
critique de l'hôte (observé : moins de 700 Mo libres sur 16 Go), Docker Desktop/WSL2 peut tuer
brutalement l'ensemble des conteneurs d'un coup, sans lien avec le code applicatif — un seul
conteneur peut survivre (celui recréé juste avant l'incident). Vérifier avec
`docker compose ps -a` (colonne `STATUS`, chercher `Exited (255)` sur plusieurs services en même
temps) puis simplement `docker compose up -d` pour tout redémarrer — aucune perte de données
(chaque service est sans état, seul l'historique des dossiers en SQLite persiste). Vérifier la
mémoire libre avant de relancer un build ou une génération lourde :
`wmic OS get FreePhysicalMemory,TotalVisibleMemorySize`.

### Rendu intérieur/jardin anormalement lent (plusieurs minutes) ou en timeout côté frontend

**Symptôme rencontré** : le frontend affiche `500 Server Error ... /land/interior` alors que
l'image finit par se générer côté serveur (visible dans les logs `interior-render` bien après
l'expiration du timeout HTTP).

**Cause trouvée et corrigée** : le VAE par défaut de SDXL produit des artefacts en float16, donc
`diffusers` le bascule automatiquement en float32 au moment du décodage final. Sur un GPU 8 Go déjà
presque saturé par le reste du pipeline en float16, ce bascule fait déborder la VRAM dédiée ; le
pilote se rabat alors sur un swap mémoire très lent au lieu de planter — la boucle de diffusion
(30 steps) ne prenait que ~25s, mais le décodage final faisait grimper le temps total à ~295s, bien
au-delà des timeouts configurés (120s orchestrateur, 150s frontend).

**Correction appliquée** (`services/interior-render/app/generator.py`) : remplacement du VAE par
défaut par `madebyollin/sdxl-vae-fp16-fix`, un VAE communautaire réentraîné pour fonctionner
correctement en float16 sans jamais déclencher ce bascule. Temps de génération mesuré après
correction : ~45s de bout en bout (confirmé via l'orchestrateur, pas seulement en direct).

**Piège lié** : le tout premier appel après cette correction télécharge ce nouveau VAE (~330 Mo)
depuis Hugging Face, ce qui peut à nouveau prendre plusieurs minutes si le réseau est lent (voir
plus bas) — ce n'est qu'un coût ponctuel, mis en cache dans le volume `hf_cache` ensuite.

### Premier appel au rendu intérieur/jardin lent

**Normal** : le modèle Stable Diffusion XL (~7 Go) se télécharge au premier appel et est mis en
cache dans un volume Docker (`hf_cache`). Les appels suivants sont rapides (~45s/image, modèle déjà
chargé en mémoire GPU). Vérifier l'état réel via :
```
curl http://localhost:8022/health
```
`{"status": "ok", "model_loaded": false}` signifie que le processus tourne mais que le modèle n'est
pas encore chargé — la première génération va prendre du temps.

### Téléchargement Hugging Face anormalement lent

**Cause rencontrée** : le protocole accéléré `hf-xet` de Hugging Face peut être bridé à quasi zéro
sur certains réseaux. Le service `interior-render` le désinstalle explicitement au build (voir son
`Dockerfile`) pour forcer un téléchargement HTTP classique, nettement plus rapide dans ce cas précis.

### Un modèle Groq ou Gemini renvoie une erreur 404 « model does not exist »

**Cause** : les modèles Groq et Gemini sont dépréciés régulièrement. Rencontré plusieurs fois
pendant ce sprint (`llama-3.3-70b-versatile`, `gemini-2.0-flash`, `gemini-2.5-flash`).

**Correction** : mettre à jour `GROQ_MODEL` ou `GEMINI_MODEL` dans `.env` vers un modèle actif
(vérifier `https://console.groq.com/docs/models` ou la documentation Gemini), puis reconstruire les
services concernés (`document-intel`, `location-intel`, `design-agent`, `summary` pour Groq ;
`vision` pour Gemini).

### Deux générations d'image intérieur/jardin lancées en même temps

**Comportement attendu** : la deuxième attend son tour (un seul GPU, verrouillage explicite dans
`services/interior-render/app/generator.py`). Vérifiable dans les logs :
`"GPU busy, request for <pièce> queued behind the current generation"`. Ce n'est pas une panne.

## Observabilité

Chaque requête est loggée avec un ID de corrélation (`deal_id` pour un dossier, sinon un ID généré
par requête) propagé dans l'en-tête `X-Correlation-ID` à travers tous les services. Pour retracer le
parcours complet d'un dossier dans les logs :
```
docker compose logs | grep <deal_id>
```

## Tests

Chaque service a sa propre suite de tests, exécutable sans dépendance aux autres services :
```
docker run --rm --entrypoint uv dealpilot-ai-<service> run pytest -q
```
Pour l'évaluation de bout en bout sur des cas synthétiques (nécessite la stack lancée) :
```
py eval/run_eval.py
```
Régénère `docs/eval_results.md` avec les résultats réels.
