# Recipe Import Pipeline — Quality & Reliability Audit Report

**Date:** 2026-02-18  
**Scope:** Recipe Importer CLI, Server Integration, Recipe Scraper, End-to-End Reliability

---

## 1. Recipe Importer CLI

### 1.1 Batch Importing & Error Handling

| Finding | Location | Severity |
|---------|----------|----------|
| **Batch isolation** | `importer.py:94–102`, `134–136` | ✅ Good |
| Workers use `asyncio.gather(*workers, return_exceptions=True)` — exceptions from one worker do not crash others. Failed recipes are counted in `stats["errors"]` and reported via the queue. | | |
| **Race on work_queue.empty()** | `importer.py:85–90`, `121–126` | ⚠️ Medium |
| Workers use `work_queue.get_nowait()` in a loop. The check `while not work_queue.empty()` is racy: multiple workers can see non-empty, then all call `get_nowait()`, and one may get `QueueEmpty` while others proceed. In practice, this often works because `get_nowait` is called repeatedly, but it can leave work unprocessed in edge cases. | | |
| **Generic exception catch** | `main.py:118–119` | ⚠️ Medium |
| `except Exception as e` swallows all errors and only prints to console. No structured logging, no exit code differentiation, no retry at CLI level. | | |

### 1.2 Retry Logic

| Finding | Location | Severity |
|---------|----------|----------|
| **Retry only on server/transient errors** | `recipe_processors.py:109–174` | ✅ Good |
| `MAX_RETRIES = 2`, `RETRY_DELAY_S = 5`. Retries are skipped for stall timeouts (“Bloqué depuis…”) to avoid duplicate submissions. | | |
| **Stall timeout handling** | `recipe_processors.py:224–228` | ✅ Good |
| `_check_stall` raises after `max_stall_s=900` (15 min) of no progress. Prevents infinite polling when the server subprocess hangs. | | |

### 1.3 Progress Tracking

| Finding | Location | Severity |
|---------|----------|----------|
| **TUI vs headless** | `importer.py:166–195` | ✅ Good |
| Rich Live TUI when `sys.stdout.isatty()`, otherwise periodic console logs. Shared stats dict and queue. | | |
| **SSE with polling fallback** | `recipe_processors.py:144–151` | ✅ Good |
| Tries SSE first; falls back to polling on `SSEConnectionError` or `aiohttp.ClientError`. Adaptive polling (1s → 3s → 5s). | | |

### 1.4 Parallelism & Rate Limiting

| Finding | Location | Severity |
|---------|----------|----------|
| **Domain semaphores** | `importer.py:66–74` | ✅ Good |
| `max_per_domain` (default 8) limits concurrent requests per domain to reduce 429 risk. | | |
| **Concurrency** | `main.py:40`, `importer.py:95–96` | ✅ Good |
| Default `concurrent_imports=10`, configurable via `-c`. | | |

---

## 2. Server-Side Recipe Service

### 2.1 Recipe Generation Request Flow

| Finding | Location | Severity |
|---------|----------|----------|
| **Async task spawning** | `recipe_service.py:643–714` | ✅ Good |
| `generate_recipe` validates input, creates `progress_id`, registers with `ProgressService`, spawns `asyncio.create_task` for the pipeline. Returns `progress_id` immediately. | | |
| **Duplicate check (URL)** | `recipe_service.py:396–413` | ✅ Good |
| Before spawning subprocess, `_find_recipe_by_url` checks in-memory `_url_index`. O(1) lookup. | | |
| **Duplicate check (text/image)** | `recipe_service.py:479–480` | ⚠️ Medium |
| Text/image pipelines delegate existence check to CLI. Server does not pre-check similarity before starting subprocess. Possible wasted work for near-duplicates. | | |

### 2.2 Subprocess Architecture

| Finding | Location | Severity |
|---------|----------|----------|
| **CLI invocation** | `recipe_service.py:426–439` | ✅ Documented |
| `asyncio.create_subprocess_exec("python", "-m", "recipe_scraper.cli", "--mode", "url", "--url", url, "--recipe-output-folder", …, "--image-output-folder", …, "--verbose")` | | |
| **No explicit subprocess timeout** | `recipe_service.py:410–378` | ⚠️ Medium |
| `_run_cli_and_stream_logs` reads stdout until `process.wait()`. No `timeout` on `create_subprocess_exec`. A stuck CLI can block indefinitely. | | |
| **Log parsing for progress** | `recipe_service.py:335–361` | ⚠️ Fragile |
| Progress inferred from lines containing `">>> "`. Steps derived from keywords: “Structuring”, “Fetching web content”, “Saved recipe: slug=”. Brittle if CLI output format changes. | | |
| **Slug detection** | `recipe_service.py:342–345` | ⚠️ Medium |
| Slug extracted from `">>> Saved recipe: slug=" + value`. Fallback: `_find_latest_recipe_slug()` (most recently modified `.recipe.json`). **Risk:** If two subprocesses run concurrently, `_find_latest_recipe_slug` could return the wrong slug. Mitigated by `_subprocess_semaphore(50)` — still 50 concurrent — and by slot ordering. | | |
| **Buffer limit** | `recipe_service.py:30`, `313` | ✅ Good |
| `_SUBPROCESS_BUFFER_LIMIT = 1MB` avoids `asyncio.LimitOverrunError` on long log lines. | | |

### 2.3 Error Handling & Timeouts

| Finding | Location | Severity |
|---------|----------|----------|
| **Non-zero returncode** | `recipe_service.py:450–467` | ✅ Good |
| Extracts error from `stderr_lines` and `step_logs`, sets progress to error via `progress_service.set_error`. | | |
| **RecipeExistsError** | `recipe_service.py:476–479` | ✅ Good |
| Propagates to `progress_service.set_error` with clear message. | | |
| **Task exception propagation** | `recipe_service.py:114–130` | ✅ Good |
| `_cleanup_task` reads `task.exception()` and calls `set_error` if present. | | |

### 2.4 Progress Communication (SSE / Polling)

| Finding | Location | Severity |
|---------|----------|----------|
| **SSE streaming** | `recipes.py:40–78`, `progress_service.py:51–60` | ✅ Good |
| `/api/recipes/progress/{task_id}/stream` yields events. Subscribers get `_notify` on every `update_step` / `complete` / `set_error`. | | |
| **Keepalive** | `recipes.py:66–67` | ✅ Good |
| 15s timeout on `queue.get()`; on timeout, sends `{"type":"keepalive"}` to prevent client disconnect. | | |

---

## 3. Server API Routes

### 3.1 Generation Endpoint

| Finding | Location | Severity |
|---------|----------|----------|
| **Request validation** | `GenerateRecipeRequest` in `models/requests.py:5–10` | ⚠️ Light |
| Pydantic model validates `type`, `url`, `text`, `image`, `credentials`. No URL format validation, no max length on `text`/`image`. Large payloads could stress memory. | | |
| **Error responses** | `recipes.py:101–120` | ✅ Good |
| `RecipeExistsError` → 409, `ValueError` → 400, other → 500 with traceback logged. | | |
| **No rate limiting** | `recipes.py:101–120` | ⚠️ Medium |
| No per-user or per-IP rate limit on `POST /api/recipes`. Batch importer can flood the server. | | |

---

## 4. Recipe Scraper Orchestration

### 4.1 Full Flow: URL → Saved Recipe

**`scrape_from_url`** (`scraper.py:116–186`):

1. Create `AuthPreset` from `auth_values` if provided  
2. `web_scraper.scrape_url(url, auth_preset)` → `WebContent`  
3. If no content → `_save_error_trace`, return `{}`  
4. `_structure_recipe(web_content, progress_callback, metadata={"sourceUrl": url})`

**`_structure_recipe`** (`scraper.py:323–377`):

1. `recipe_structurer.structure(web_content)` → `Recipe` object  
2. `recipe_structurer.to_dict()` → dict  
3. Generate slug, save debug traces (`raw`, `preformat`)  
4. Add `sourceImageUrl`, merge metadata  
5. `_download_image(source_image_url, slug)`  
6. `recipe_enricher.enrich_recipe_async(recipe_data)`  
7. (Optional) Pass 3: adversarial review  
8. Return `recipe_data`

**Saving** is done in **CLI** (`cli.py:263–266`), not in `RecipeScraper`. The scraper returns a dict; the CLI writes it to disk.

### 4.2 Silent Failure Points

| Finding | Location | Severity |
|---------|----------|----------|
| **Empty dict on scrape failure** | `scraper.py:171`, `377` | ⚠️ Medium |
| `scrape_from_url` returns `{}` on scrape failure or structure exception. CLI treats `recipe_data and "error" not in recipe_data` — empty dict is falsy, so CLI goes to `else` and returns 1. No distinction between “no content” and “structure failed”. | | |
| **Image download failure** | `scraper.py:399–409` | ✅ Handled |
| `_download_image` returns `None` on failure. Recipe continues without `metadata.image`; no crash. | | |
| **Enrichment failure** | `scraper.py:315–316` | ❓ Unclear |
| `recipe_enricher.enrich_recipe_async` is awaited. If it raises, the exception propagates to `_structure_recipe`’s `except` block, which returns `{}`. No partial save. | | |
| **Review failure (Pass 3)** | `scraper.py:346–347` | ✅ Good |
| Wrapped in `try/except`; non-blocking. Logged as warning. | | |

### 4.3 Recipe Save & Metadata

| Finding | Location | Severity |
|---------|----------|----------|
| **Save location** | `cli.py:264–266` | ✅ Good |
| `{recipe_output_folder}/{slug}.recipe.json`. Paths come from server. | | |
| **Metadata preserved** | `scraper.py:384–388` | ✅ Good |
| `sourceUrl`, `originalContent`, `slug`, `sourceImageUrl`, `image`, `createdAt`, `creationMode`, diets, seasons, times, nutrition. Debug data (`preformattedText`) popped before save. | | |
| **totalCookingTime** | `cli.py:261–263` | ✅ Good |
| Copied to root if present in metadata. | | |

### 4.4 Debug Traces

| Finding | Location | Severity |
|---------|----------|----------|
| **Raw + preformat** | `scraper.py:378–384`, `379–421` | ✅ Good |
| `{slug}.raw.txt`, `{slug}.preformat.txt` in `_debug_output_folder`. Non-critical: save failure only logs warning. | | |
| **Error traces** | `scraper.py:457–504` | ✅ Good |
| `errors/{timestamp}_{slug}.error.json` with url, title, stage, error_type, message, traceback, raw_text_preview. | | |
| **Review traces** | `scraper.py:423–438` | ✅ Good |
| `{slug}.review.json` for Pass 3. | | |

---

## 5. Recipe Scraper CLI

### 5.1 Invocation by Server

| Finding | Location | Severity |
|---------|----------|----------|
| **Command** | `recipe_service.py:426–439` | - |
| `python -m recipe_scraper.cli --mode url --url <url> --recipe-output-folder <path> --image-output-folder <path> [--credentials <file>] --verbose` | | |
| **CWD** | Implicit | ⚠️ Medium |
| Server does not set `cwd`. CLI uses relative `./data/recipes` by default but server passes absolute paths. Paths should be correct. | | |
| **Environment** | Not set | ⚠️ Medium |
| No explicit `env` for subprocess. Inherits server env. API keys (e.g. OPENROUTER) must be in server environment. | | |

### 5.2 Result Communication

| Finding | Location | Severity |
|---------|----------|----------|
| **Progress** | `cli.py:94–95` | ✅ Good |
| `print(f">>> {message}")` for each progress callback. Server parses these lines. | | |
| **Success** | `cli.py:257–259` | ✅ Good |
| `print(f">>> Saved recipe: slug={slug}")` — server uses this to get slug. | | |
| **Failure** | `cli.py:314–320` | ⚠️ Medium |
| Errors go to `logging.error` and sometimes `print(..., file=sys.stderr)`. With `merge_stderr=True`, server sees them in stdout. Stderr-only output might be missed if parsing is stdout-only. | | |
| **Exit codes** | `cli.py:0, 1, 100` | ✅ Good |
| 0 = success, 1 = error, 100 = duplicate (similar content). Server handles 100 for text mode. | | |

### 5.3 Error Handling

| Finding | Location | Severity |
|---------|----------|----------|
| **Credentials cleanup** | `cli.py:323–330` | ✅ Good |
| `finally` removes temp credentials file. | | |
| **Top-level exception** | `cli.py:316–320` | ✅ Good |
| Catches `Exception`, logs traceback, returns 1. | | |
| **Duplicate detection** | `cli.py:108–115`, `231–239` | ✅ Good |
| URL: `_recipe_exists` before scrape. Text: `scrape_from_text` returns `None` if similar; CLI exits 100. | | |

---

## 6. End-to-End Reliability: Data Loss & Silent Failures

### 6.1 Trace: User Submits URL → Recipe Saved

```
User (CLI/UI)
  → POST /api/recipes { type: "url", url }
  → RecipeService.generate_recipe()
     → ProgressService.register(progress_id)
     → asyncio.create_task(_process_recipe_generation())
  → Returns progressId

_process_recipe_generation:
  1. _find_recipe_by_url(url) → skip if exists
  2. _subprocess_semaphore.acquire()
  3. Create temp creds file (if auth)
  4. asyncio.create_subprocess_exec(python -m recipe_scraper.cli ...)
  5. _run_cli_and_stream_logs(): read stdout line-by-line, parse ">>> ", update ProgressService
  6. process.wait()
  7. If returncode != 0 → set_error, return
  8. saved_slug = from ">>> Saved recipe: slug=" else _find_latest_recipe_slug()
  9. progress_service.complete(progress_id, {slug})
```

### 6.2 Data Loss & Swallowed Error Points

| # | Location | Risk | Severity |
|---|----------|------|----------|
| 1 | `scraper.py:171` | `web_content` is None → return `{}`. Error trace saved. Client gets generic failure. | Medium |
| 2 | `scraper.py:362–377` | Any exception in `_structure_recipe` → return `{}`. Error trace saved. No partial recipe. | Medium |
| 3 | `recipe_service.py:342` | Slug regex fails → `saved_slug` stays None. Fallback `_find_latest_recipe_slug()` can pick wrong file under concurrency. | Medium |
| 4 | `recipe_service.py:375–378` | `returncode != 0` but no parseable error in logs → generic “Scraper failed (exit N) (no error details)”. | Low |
| 5 | `importer.py:98`, `recipe_processors.py:156` | `_stream_until_done` can raise “SSE stream ended unexpectedly” if stream closes before terminal event. Fallback to polling may recover. | Low |
| 6 | `progress_service.py:86–87` | `complete(progress_id)` when id not in `_progress_entries` → silent no-op. Rare if registration is correct. | Low |
| 7 | `cli.py:267` | `image_path` used for text mode with `--image-file`. If image copy fails (line 292), recipe JSON may be written before image; second write at 286–288 could fail. | Low |
| 8 | `recipe_service.py:449` | Credentials file `unlink()` can fail (e.g. permissions). Logged but temp file may persist. | Low |

### 6.3 Quality Degradation Without Detection

| Risk | Description |
|------|-------------|
| **LLM drift** | Recipe structurer uses LLM. Model or prompt changes can degrade quality. No automated quality checks in pipeline. |
| **Enrichment errors** | Diet/season/nutrition use curated data + embeddings. Stale data or mis-matches not flagged. |
| **Slug collisions** | `slugify(title)` can collide. No collision handling; last writer wins. |
| **Image absence** | Image download can fail silently (recipe saved without `metadata.image`). No alert. |

---

## 7. Recommendations

### High Priority

1. **Subprocess timeout**: Add a configurable timeout (e.g. 20 min) to `_run_cli_and_stream_logs`. On timeout, kill subprocess and report error.
2. **Slug detection robustness**: Prefer structured output (e.g. JSON line at end) instead of parsing `">>> Saved recipe: slug="`. Or have CLI write slug to a temp file for server to read.
3. **Concurrency safety for `_find_latest_recipe_slug`**: When multiple subprocesses can run, avoid relying on “latest file”. Either pass a unique output path per run or have CLI return slug via a defined channel.

### Medium Priority

4. **Worker queue race**: Replace `while not work_queue.empty()` + `get_nowait` with `while True` + `await work_queue.get()` and a sentinel (e.g. `None`) to signal shutdown.
5. **API request validation**: Add `Field(max_length=...)` on `text` and `image` to prevent huge payloads. Validate URL format.
6. **Rate limiting**: Add rate limiting (e.g. per-IP or per-token) on `POST /api/recipes`.

### Lower Priority

7. **Structured CLI output**: Consider JSONL or a final JSON blob for progress and result to make parsing reliable.
8. **Quality monitoring**: Add optional post-save checks (e.g. required fields, basic schema validation) and log anomalies.
9. **Duplicate pre-check for text**: Before spawning CLI for text mode, run a lightweight similarity check on the server if feasible.

---

## File Index

| File | Purpose |
|------|---------|
| `recipe_importer/src/main.py` | CLI entry, argparse, mode dispatch |
| `recipe_importer/src/importer.py` | RecipeImporter, batch orchestration |
| `recipe_importer/src/recipe_processors.py` | RecipeProcessor, retry, SSE/poll |
| `recipe_importer/src/api_client.py` | HTTP client for /api/recipes |
| `recipe_importer/src/progress_tracker.py` | Rich TUI / console progress |
| `server/services/recipe_service.py` | Generation pipelines, subprocess |
| `server/services/progress_service.py` | Progress state, SSE notify |
| `server/api/routes/recipes.py` | REST endpoints |
| `server/packages/recipe_scraper/.../scraper.py` | RecipeScraper, scrape/structure |
| `server/packages/recipe_scraper/.../cli.py` | recipe_scraper CLI |
