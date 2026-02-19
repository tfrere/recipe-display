# Rapport : Suppression des subprocesses — Pipeline in-process

## Résumé exécutif

Le principal goulot d'étranglement du combo server/batch importer est le **spawn d'un subprocess Python complet** pour chaque recette. Chaque `python -m recipe_scraper.cli` :
- Prend **2-3s de startup** (imports, chargement des modèles)
- Consomme **~300 MB RAM** par process
- **Recharge tous les modèles** à chaque fois (CRF NER, BGE embeddings, clients LLM)
- **Aucune mutualisation** entre recettes concurrentes

Sur un batch de 677 recettes à 10 concurrents, cela représente **~1350-2000s de startup pur** (22-33 minutes gaspillées).

## Architecture actuelle (subprocess)

```
Batch Importer (client)
  │ POST /api/recipes {url}
  ▼
FastAPI Server (recipe_service.py)
  │ generate_recipe()
  │   ├─ check URL index (O(1)) ✅
  │   └─ asyncio.create_task(_process_recipe_generation)
  │        │
  │        ▼
  │   asyncio.create_subprocess_exec(
  │     "python", "-m", "recipe_scraper.cli",
  │     "--mode", "url", "--url", url, ...
  │   )
  │        │
  │        ▼  SUBPROCESS (nouveau process Python)
  │   cli.py main_async()
  │     ├─ _recipe_exists(url)        ← O(N) scan REDONDANT
  │     ├─ RecipeScraper()            ← INIT: charge tout
  │     │    ├─ WebScraper()
  │     │    ├─ RecipeStructurer()    ← charge CRF model
  │     │    ├─ RecipeEnricher()      ← charge BGE embeddings
  │     │    └─ RecipeReviewer()      ← init client LLM
  │     ├─ scraper.scrape_from_url()
  │     │    ├─ web_scraper.scrape_url()     1-5s   (réseau)
  │     │    ├─ recipe_structurer.structure()
  │     │    │    ├─ Pass 1: preformat       5-30s  (LLM)
  │     │    │    ├─ Pass 1.5: NER CRF       1-3s   (CPU)
  │     │    │    └─ Pass 2: DAG             10-60s (LLM)
  │     │    ├─ _download_image()            1-3s   (réseau)
  │     │    ├─ recipe_enricher.enrich_recipe_async()
  │     │    │    ├─ enrich_recipe()          <1s   (sync)
  │     │    │    ├─ translate_ingredients()  2-10s  (LLM)
  │     │    │    ├─ _determine_seasons()  ┐
  │     │    │    ├─ match_batch()         ┘ 2-8s   (parallèle ✅)
  │     │    │    ├─ _fill_missing_weights   2-5s   (LLM)
  │     │    │    └─ nutrition profile        <1s   (sync)
  │     │    └─ recipe_reviewer.review()     10-30s (LLM)
  │     └─ save JSON + copy image
  │        │
  │        ▼  stdout ">>> message"
  │   _run_cli_and_stream_logs()
  │     parse stdout → update ProgressService
  │
  ◄─ GET /api/recipes/progress/{id}  (polling client)
```

### Temps par recette : ~35-130s
- Startup subprocess : **2-3s** (gaspillé)
- Réseau (fetch + image) : 2-8s
- LLM (Pass 1 + 2 + traduction + poids + review) : **25-105s**
- CPU (NER + embeddings) : 3-11s
- I/O (save, debug traces) : <1s

## Architecture cible (in-process)

```
Batch Importer (client)
  │ POST /api/recipes {url}
  ▼
FastAPI Server (recipe_service.py)
  │ generate_recipe()
  │   ├─ check URL index (O(1)) ✅
  │   └─ asyncio.create_task(_process_recipe_generation)
  │        │
  │        ▼  APPEL DIRECT (même process)
  │   self._scraper.scrape_from_url(url, progress_callback)
  │     ├─ web_scraper.scrape_url()          1-5s
  │     ├─ recipe_structurer.structure()
  │     │    ├─ Pass 1: preformat            5-30s
  │     │    ├─ Pass 1.5: NER CRF (partagé) 0.1-0.5s  ← modèle déjà chargé
  │     │    └─ Pass 2: DAG                  10-60s
  │     ├─ _download_image()                 1-3s
  │     ├─ recipe_enricher.enrich_recipe_async()
  │     │    ├─ translate (cache partagé)    0.5-5s   ← cache hits
  │     │    ├─ seasons + nutrition           2-8s     ← BGE déjà chargé
  │     │    ├─ weights LLM                  2-5s
  │     │    └─ nutrition profile             <1s
  │     └─ recipe_reviewer.review()          10-30s
  │        │
  │        ▼  progress_callback → ProgressService direct
  │   save JSON + update URL index
  │
  ◄─ GET /api/recipes/progress/{id}  (polling client)
```

### Gains estimés par recette
- **-2-3s** : suppression startup subprocess
- **-0.5-2.5s** : NER CRF déjà chargé (vs reload)
- **-1-4s** : BGE embeddings déjà chargés (vs reload)
- **-0.5-5s** : cache traduction partagé entre recettes
- **-~300 MB RAM** par slot concurrent

## Plan d'implémentation

### Étape 1 : Instance partagée de RecipeScraper

**Fichier :** `server/services/recipe_service.py`

Dans `RecipeService.__init__`, créer une instance unique de `RecipeScraper` partagée entre toutes les requêtes :

```python
from recipe_scraper.scraper import RecipeScraper

class RecipeService:
    def __init__(self, base_path: str = "data"):
        # ... existing init ...

        # Shared scraper instance — models loaded once, reused across requests
        self._scraper = RecipeScraper()
        self._scraper._recipe_output_folder = self.recipes_path
        self._scraper._image_output_folder = self.images_path
        self._scraper._debug_output_folder = self.recipes_path / "debug"
```

### Étape 2 : Remplacer `_process_recipe_generation` (URL mode)

Remplacer le subprocess par un appel direct :

```python
async def _process_recipe_generation(self, progress_id: str, url: str, credentials=None):
    try:
        # Step 1: Check existence (déjà en place, O(1))
        await self.progress_service.update_step(progress_id, "check_existence", "in_progress")
        existing = await self._find_recipe_by_url(url)
        if existing:
            slug = existing["metadata"].get("slug", "")
            raise RecipeExistsError(f"Recipe already exists: {slug}")
        await self.progress_service.update_step(progress_id, "check_existence", "completed", 100)

        # Step 2: Progress callback → ProgressService
        async def on_progress(message: str):
            step = "scrape_content"
            if "Structuring" in message or "Building" in message:
                step = "structure_recipe"
            elif "Saving" in message or "Enriching" in message or "Reviewing" in message:
                step = "structure_recipe"
            await self.progress_service.update_step(progress_id, step, "in_progress", message=message)

        await self.progress_service.update_step(progress_id, "scrape_content", "in_progress")

        # Step 3: Appel direct — pas de subprocess
        auth_values = credentials.get("values") if credentials else None
        recipe_data = await self._scraper.scrape_from_url(url, auth_values, progress_callback=on_progress)

        if not recipe_data:
            raise Exception("Scraper returned empty data")

        # Step 4: Save recipe JSON
        slug = recipe_data.get("metadata", {}).get("slug", "unknown")
        file_path = self.recipes_path / f"{slug}.recipe.json"
        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(recipe_data, ensure_ascii=False, indent=2))

        # Step 5: Update URL index
        self._url_index[url] = slug

        # Step 6: Complete
        for step in ["scrape_content", "structure_recipe", "save_recipe"]:
            await self.progress_service.update_step(progress_id, step, "completed", 100)
        await self.progress_service.complete(progress_id, {"slug": slug})

    except RecipeExistsError as e:
        await self.progress_service.set_error(progress_id, str(e))
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        await self.progress_service.set_error(progress_id, str(e))
```

### Étape 3 : Idem pour `_process_text_recipe_generation` et `_process_image_recipe_generation`

Même pattern : remplacer le subprocess par `self._scraper.scrape_from_text()`.
Pour le mode image, appeler `OCRService` directement puis `scrape_from_text()`.

### Étape 4 : Paralléliser image download + enrichissement

**Fichier :** `server/packages/recipe_scraper/src/recipe_scraper/scraper.py`

Dans `_structure_recipe`, l'image download et l'enrichissement sont séquentiels.
L'enrichissement ne dépend pas de l'image. On peut les paralléliser :

```python
# AVANT (séquentiel)
image_filename = await self._download_image(source_image_url, slug, auth_values)
recipe_data = await self.recipe_enricher.enrich_recipe_async(recipe_data)

# APRÈS (parallèle)
async def _download_task():
    return await self._download_image(source_image_url, slug, auth_values)

async def _enrich_task():
    return await self.recipe_enricher.enrich_recipe_async(recipe_data)

image_filename, enriched_data = await asyncio.gather(
    _download_task(), _enrich_task()
)
recipe_data = enriched_data
if image_filename:
    recipe_data["metadata"]["image"] = image_filename
```

Gain : **1-3s par recette** (download image en parallèle de l'enrichissement).

### Étape 5 : Supprimer `_run_cli_and_stream_logs` et le code subprocess

Une fois les 3 pipelines migrés, supprimer :
- `_run_cli_and_stream_logs()`
- `_SUBPROCESS_BUFFER_LIMIT`
- `_find_latest_recipe_slug()` (plus nécessaire, on a le slug directement)
- Imports `asyncio.subprocess` devenus inutiles

Le CLI (`cli.py`) reste fonctionnel pour l'usage standalone.

## Points d'attention

### Concurrence et thread-safety
- `RecipeScraper` utilise `async with self.web_scraper` → crée une session par appel, OK
- `RecipeStructurer` utilise un `AsyncOpenAI` client → thread-safe
- `RecipeEnricher._nutrition_matcher` → partagé, chargé une fois, read-only après init
- `RecipeReviewer` → client async, OK

### `_find_similar_recipe` (mode texte uniquement)
- Scan O(N) de tous les fichiers JSON pour la similarité textuelle
- **Non critique** pour le batch URL (pas appelé)
- À optimiser plus tard si le mode texte devient frequent

### `_recipe_exists` dans le scraper
- Le scraper a sa propre vérification O(N) dans `_recipe_exists()`
- **Ne sera plus appelée** car le service fait déjà la vérification via l'index URL O(1)
- `scrape_from_url()` ne l'appelle pas (c'était le CLI qui le faisait)

## Gains totaux estimés

| Changement | Gain par recette | Gain batch 677 |
|---|---|---|
| Suppression subprocess startup | -2-3s | -22-33 min |
| Modèles partagés (CRF + BGE) | -1.5-6.5s | -17-73 min |
| Cache traduction partagé | -0.5-5s | -6-56 min |
| Parallélisation image + enrichissement | -1-3s | -11-34 min |
| Suppression duplicate check CLI | -0.5-2s | -6-22 min |
| **Total** | **-5.5-19.5s** | **-62-218 min (~1-3.6h)** |

La plus grande partie du gain vient de la **mutualisation des modèles** et de la **suppression du subprocess**, pas d'optimisations algorithmiques.

## Changements déjà appliqués (chat précédent)

Ces optimisations sont **déjà en place** et complémentaires :

1. ✅ Parallélisation `_determine_seasons` + `match_batch` avec `asyncio.gather` (recipe_enricher.py)
2. ✅ Suppression des `asyncio.sleep(0.5/0.2)` dans `progress_service.py` (-2.8s/recette)
3. ✅ Polling adaptatif 1s/3s/5s dans `recipe_processors.py` (-60% requêtes HTTP)
4. ✅ Provider routing `sort: "throughput"` sur tous les appels OpenRouter
5. ✅ Sleep post-process 0.1 → 0.01s
6. ✅ Suppression sémaphore redondant (workers suffisent)
