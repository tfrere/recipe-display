# Rapport : Architecture du parallélisme — état des lieux

> Ce rapport documente l'architecture actuelle du parallélisme dans l'importer.
> Pour le plan d'action de scaling à 50 recettes, voir **THROUGHPUT_REPORT.md**.

## Architecture actuelle

```
Importer (main.py)                             Serveur FastAPI
──────────────────                             ───────────────
  asyncio.Queue(urls)                          POST /api/recipes
  N workers (concurrent_imports)                 └─ asyncio.create_task()
  │                                                  └─ subprocess Python
  ├─ worker 1 ─── POST ──────────────────────→      (recipe_scraper.cli)
  │               poll (adaptatif 1-5s) ←────→  GET /progress/{id}
  ├─ worker 2 ─── POST ──────────────────────→      ...
  │               poll ...
  └─ worker N ─── ...
```

Le parallélisme fonctionne sur 3 niveaux :

| Niveau | Mécanisme | Limité par |
|--------|-----------|------------|
| Client (importer) | `asyncio.Queue` + N workers | `concurrent_imports` (CLI `-c`) |
| Serveur (FastAPI) | `asyncio.create_task` par requête | ⚠️ Rien actuellement |
| Worker (scraper) | 1 subprocess OS par recette | RAM / CPU machine |

## Ce qui fonctionne bien ✅

1. **Pattern producer/consumer** — les URLs sont dans une `asyncio.Queue`, les workers consomment au fil de l'eau. Pas de création de 500 coroutines d'un coup.

2. **Session aiohttp partagée** — réutilise les connexions HTTP (keep-alive), bon pour le polling fréquent.

3. **Polling adaptatif** — 1s les 30 premières secondes, 3s jusqu'à 2 min, puis 5s. Réduit le nombre de requêtes de ~60%.

4. **Retry intelligent** — ne retente PAS sur les stall timeouts (le subprocess serveur tourne encore). Ne retente QUE sur les erreurs serveur réelles.

5. **Gestion des doublons** — HTTP 409 du serveur → skip propre, pas de retry inutile. L'index URL côté serveur rend le check O(1).

6. **`max_stall_s` = 900s** — laisse le temps au LLM structuring (3-8 min) sans faux timeout.

## Ce qui pose problème ⚠️

### Côté serveur : pas de contrôle de concurrence

Le serveur accepte TOUTES les requêtes et lance un subprocess immédiatement pour chacune. Avec `-c 50`, ça crée 50 subprocesses Python (~300 MB chacun) sans aucune protection.

→ **Fix dans THROUGHPUT_REPORT.md : sémaphore serveur**

### Côté serveur : `RecipeService` instancié par requête

Chaque appel HTTP crée un nouveau `RecipeService()`, qui reconstruit l'index URL (lecture de tous les fichiers JSON). Aucun état partagé entre les requêtes.

→ **Fix dans THROUGHPUT_REPORT.md : singleton**

### Côté serveur : détection du slug par mtime

`_find_latest_recipe_slug()` utilise `max(mtime)` sur le filesystem — race condition avec N subprocesses concurrents.

→ **Fix dans THROUGHPUT_REPORT.md : slug via stdout CLI**

## Patterns de 2026 — évaluation pragmatique

Le rapport précédent suggérait Celery, Redis, SSE, etc. Voici une évaluation honnête pour un projet perso :

| Pattern suggéré | Pertinence | Verdict |
|---|---|---|
| Worker pool (Celery/dramatiq) | Overkill pour 50 recettes | ❌ Un sémaphore asyncio suffit |
| Message broker (Redis) | Ajoute une dépendance infra | ❌ Pas nécessaire |
| SSE au lieu du polling | Nice-to-have | 🟡 Gain réel mais pas bloquant |
| Queue bornée côté client | Déjà implémenté | ✅ `asyncio.Queue` |
| Backpressure serveur (429) | Utile en prod multi-user | 🟡 Pas prioritaire |
| Circuit breaker + exp backoff | Utile en réseau instable | 🟡 Local = pas nécessaire |

**Philosophie :** le bottleneck est le LLM (3-8 min par recette). Optimiser l'infra au-delà d'un sémaphore serveur ne changerait rien au temps total. L'objectif est de **saturer la capacité machine sans la dépasser**, pas de construire une infra distribuée.

## Métriques utiles pour le monitoring

Pour suivre les performances en batch de 50 :

```
Throughput     = recettes terminées / minute
Utilisation    = subprocesses actifs / sémaphore max
Queue depth    = tâches en attente de slot serveur
Temps médian   = durée médiane d'une recette (scrape → save)
Taux de succès = succès / (succès + erreurs)
```

Ces métriques sont déjà partiellement trackées par `ImportMetrics` côté client. Le sémaphore serveur permettrait d'exposer `utilisation` et `queue depth` via un endpoint `/api/status` si besoin.
