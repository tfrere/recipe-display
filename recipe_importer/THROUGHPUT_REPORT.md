# Rapport : Scaler l'import de recettes à 50 en batch

## Contexte

**Objectif :** pouvoir importer 50 recettes en un seul batch, de manière fiable et dans un temps raisonnable.

**Architecture actuelle :**
```
Importer (client Python)
  └─ N workers asyncio (limités par concurrent_imports)
       └─ POST /api/recipes → serveur FastAPI
            └─ asyncio.create_task → subprocess Python (1 par recette)
                 └─ recipe_scraper.cli (scrape + LLM structuring + enrichment + save)
       └─ GET /api/recipes/progress/{id} (polling adaptatif 1-5s)
```

**Performances actuelles (batch 10, `-c 10`) :**

| Métrique | Valeur |
|---|---|
| Temps moyen par recette | ~3-8 min (dominé par le LLM structuring) |
| Workers effectifs | 8-9 sur 10 |
| RAM par subprocess | ~300 MB |
| Taux de succès | ~85-90% |

---

## Ce qui a déjà été corrigé ✅

| Fix | Statut | Impact |
|---|---|---|
| `max_stall_s` passé de 300 à 900s | ✅ Done | -80% de faux timeouts |
| Pas de retry sur stall timeout | ✅ Done | Plus de subprocesses doublons |
| URL index O(1) via `_url_index` | ✅ Done | Lookup instantané |
| Pattern producer/consumer avec `asyncio.Queue` | ✅ Done | Mémoire stable côté client |
| Polling adaptatif (1s → 3s → 5s) | ✅ Done | -60% de requêtes polling |

---

## 🔴 Les 3 problèmes critiques pour scaler à 50

### 1. `RecipeService()` est recréé à chaque requête HTTP

```python
# server/api/routes/recipes.py:19-21
def get_recipe_service():
    return RecipeService()  # ← NOUVELLE instance à chaque appel !
```

**Conséquences avec 50 requêtes concurrentes :**

- `_build_url_index()` est appelé 50 fois en parallèle → chacun lit et parse TOUS les fichiers `.recipe.json` du disque
- Avec 500 recettes existantes : 50 × 500 fichiers = **25 000 lectures de fichier JSON** juste pour l'init
- Le dict `generation_tasks` est vide à chaque fois → aucun tracking des tâches en cours
- Le `_url_index` est reconstruit à chaque POST, mais les recettes ajoutées par d'autres requêtes en cours ne sont pas visibles (isolation totale entre instances)

**Estimation de l'impact :** 2-5s de latence ajoutée à CHAQUE requête, plus des race conditions sur les doublons.

**Fix : Singleton `RecipeService`**

```python
# server/api/routes/recipes.py
_recipe_service: RecipeService | None = None

def get_recipe_service():
    global _recipe_service
    if _recipe_service is None:
        _recipe_service = RecipeService()
    return _recipe_service
```

Ou mieux, utiliser une lifespan FastAPI :

```python
# server/main.py
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.recipe_service = RecipeService()
    yield

app = FastAPI(lifespan=lifespan)
```

### 2. Aucune limite de concurrence côté serveur → 50 subprocesses = machine morte

Actuellement, `generate_recipe()` appelle `asyncio.create_task()` sans aucune limite :

```python
# server/services/recipe_service.py:922-929
task = asyncio.create_task(
    self._process_recipe_generation(progress_id=progress_id, url=url, ...)
)
```

**Avec 50 requêtes simultanées :**

| Ressource | 10 concurrent | 50 concurrent |
|---|---|---|
| Subprocesses Python | 10 × ~300 MB = 3 GB | 50 × ~300 MB = **15 GB** |
| CPU (LLM calls) | Gérable | Thrashing, context switching |
| Disk I/O | OK | Contention sur l'écriture des .recipe.json |

La machine (ou le container Railway) n'a probablement pas 15 GB de RAM libre. Résultat : OOM kills, swap, lenteur extrême.

**Fix : Sémaphore serveur pour limiter les subprocesses actifs**

```python
# server/services/recipe_service.py
class RecipeService:
    # Limiter à N subprocesses simultanés (adapté à la RAM dispo)
    _subprocess_semaphore = asyncio.Semaphore(8)

    async def _process_recipe_generation(self, progress_id, url, ...):
        # Les étapes légères (check_existence) restent hors sémaphore
        await self._check_existence(progress_id, url)
        
        # Le subprocess lourd attend un slot
        async with self._subprocess_semaphore:
            await self._run_scraper_subprocess(progress_id, url, ...)
```

Le client peut envoyer 50 requêtes d'un coup. Le serveur les accepte toutes (réponse immédiate avec `progressId`) mais n'exécute que 8 subprocesses à la fois. Les autres attendent dans la queue asyncio, et le client les voit en status `in_progress` avec le step `check_existence` complété.

**Impact :** RAM contrôlée (~2.5 GB max), throughput maximal sans surcharger la machine.

### 3. `_find_latest_recipe_slug()` est une race condition avec N concurrent

```python
# server/services/recipe_service.py:381-389
def _find_latest_recipe_slug(self) -> Optional[str]:
    recipe_files = list(self.recipes_path.glob("*.recipe.json"))
    if not recipe_files:
        return None
    latest_file = max(recipe_files, key=lambda p: p.stat().st_mtime)
    slug = latest_file.stem.replace(".recipe", "")
    return slug
```

Cette méthode retourne le fichier `.recipe.json` le plus récent sur le disque. Avec 50 subprocesses qui terminent à quelques secondes d'intervalle :

- Subprocess A finit et sauve `poulet-roti.recipe.json` à 12:00:01
- Subprocess B finit et sauve `tarte-pommes.recipe.json` à 12:00:02
- Le handler de A appelle `_find_latest_recipe_slug()` → retourne `tarte-pommes` (le fichier de B !) au lieu de `poulet-roti`
- Le progress de A est marqué "completed" avec le mauvais slug

**Fix : Le CLI doit retourner le slug dans sa sortie stdout**

Faire en sorte que `recipe_scraper.cli` imprime une ligne structurée quand il sauvegarde :

```
>>> Saved recipe: slug=poulet-roti
```

Puis dans `_run_cli_and_stream_logs`, parser cette ligne pour extraire le slug :

```python
if ">>> Saved recipe: slug=" in line_text:
    saved_slug = line_text.split("slug=")[1].strip()
```

Cela élimine la race condition et le scan du filesystem.

---

## 🟠 Problèmes secondaires (optimisation)

### 4. Polling HTTP : 50 concurrent × toutes les 3s = ~17 req/s juste pour le suivi

Pas bloquant pour 50 recettes, mais ça fait ~1000 req/min de polling pur. FastAPI gère ça facilement, mais c'est du gaspillage.

**Fix optionnel : Polling plus espacé pour les tâches "en queue"**

Si le sémaphore serveur fait attendre une tâche, le status reste `in_progress` sur `check_existence` sans changement. On peut détecter ça côté client et espacer le polling à 10-15s pour les tâches en attente :

```python
# recipe_processors.py — dans _poll_until_done
if current_step == "check_existence" and elapsed > 60:
    await asyncio.sleep(10)  # La tâche est probablement en queue serveur
```

### 5. Stats partagées via `dict` mutable

```python
stats["in_progress"] += 1  # Pas de lock
```

En asyncio single-thread c'est safe car il n'y a pas de vrai parallélisme. Mais si un jour on passe en multiprocessing, ça casse. Pour 50 workers, on pourrait utiliser un `asyncio.Lock` léger :

```python
async with stats_lock:
    stats["in_progress"] += 1
```

**Verdict :** pas prioritaire, asyncio single-thread protège naturellement.

---

## Plan d'implémentation

### Phase 1 : Fixes critiques (30 min de travail)

| # | Fix | Fichier | Effort |
|---|---|---|---|
| 1 | Singleton `RecipeService` | `server/api/routes/recipes.py` | 5 min |
| 2 | Sémaphore serveur (8 subprocess max) | `server/services/recipe_service.py` | 15 min |
| 3 | Slug retourné par le CLI stdout | `recipe_scraper/cli.py` + `recipe_service.py` | 10 min |

**Après Phase 1 :** on peut lancer `-c 50` en sécurité. Le serveur throttle à 8 subprocesses actifs, la RAM reste sous contrôle, et les slugs sont correctement attribués.

### Phase 2 : Optimisation du client (15 min)

| # | Fix | Fichier | Effort |
|---|---|---|---|
| 4 | Polling espacé pour les tâches en queue | `recipe_processors.py` | 10 min |
| 5 | Logging amélioré pour les batches (ETA, throughput) | `progress_tracker.py` | 5 min |

### Phase 3 : Nice-to-have (si besoin)

| # | Fix | Impact | Effort |
|---|---|---|---|
| 6 | SSE au lieu du polling | -95% de requêtes HTTP polling | 2-3h |
| 7 | Endpoint `DELETE /progress/{id}` pour cancel | Nettoyage propre des subprocesses | 1h |
| 8 | Backpressure HTTP 429 si queue pleine | Protection contre les abus | 30 min |

---

## Projection des performances

### Batch de 50 recettes avec les fixes Phase 1 + 2

```
Config : -c 50, sémaphore serveur = 8

Timeline estimée :
  [0-10s]    50 POST envoyés, 50 progressId reçus
  [0-10s]    8 subprocesses lancés, 42 en queue serveur
  [3-8 min]  Les 8 premiers terminent → 8 nouveaux partent
  [~35 min]  50/50 terminés (50 recettes ÷ 8 slots × ~5 min/recette)

Métriques attendues :
  Temps total : ~30-40 min (vs ~25 min théorique avec 10 subprocesses non-limités)
  RAM serveur : ~2.5 GB stable (vs 15 GB sans sémaphore)
  Taux de succès : ~90%+ (pas de race conditions slug)
  Polling requests : ~3000 total (50 × ~60 polls × 3s interval moyen)
```

### Comparatif

| Scénario | Temps total | RAM max | Fiabilité |
|---|---|---|---|
| Actuel (`-c 10`, pas de sémaphore) | ~50 min | ~3 GB | ~85% |
| Phase 1 (`-c 50`, sémaphore 8) | ~35 min | ~2.5 GB | ~90% |
| Phase 1+2 (`-c 50`, polling smart) | ~35 min | ~2.5 GB | ~92% |
| Théorique max (sémaphore 12, 16GB RAM) | ~25 min | ~4 GB | ~90% |

---

## Résumé : ce qui bloque le scale à 50

| Cause | Sévérité | Impact | Fix |
|---|---|---|---|
| `RecipeService()` recréé par requête | 🔴 Critique | 25K lectures fichier inutiles, no state sharing | Singleton |
| Pas de limite subprocess serveur | 🔴 Critique | 15 GB RAM → OOM | Sémaphore asyncio |
| `_find_latest_recipe_slug()` race condition | 🔴 Critique | Mauvais slug attribué | Slug via stdout CLI |
| Polling trop fréquent pour tâches en queue | 🟠 Medium | ~1K req/min inutiles | Polling adaptatif |
| Stats sans lock | 🟡 Low | Safe en asyncio, fragile si migration | Asyncio Lock |

**En appliquant les 3 fixes critiques**, on peut passer de `-c 10` à `-c 50` en toute sécurité. Le bottleneck devient alors le temps LLM par recette (~3-8 min), qui est incompressible. Le sémaphore serveur garantit qu'on utilise 100% de la capacité machine sans la dépasser.
