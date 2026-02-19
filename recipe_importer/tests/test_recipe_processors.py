"""Tests for RecipeProcessor — SSE streaming with polling fallback."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

import aiohttp

from src.models import ImportMetrics
from src.api_client import RecipeApiClient, SSEConnectionError
from src.recipe_processors import RecipeProcessor


@pytest.fixture
def metrics():
    return ImportMetrics()


@pytest.fixture
def mock_api_client():
    client = MagicMock(spec=RecipeApiClient)
    client.api_url = "http://localhost:3001"
    return client


@pytest.fixture
def mock_session():
    return AsyncMock(spec=aiohttp.ClientSession)


@pytest.fixture
def processor(mock_api_client, metrics, mock_session):
    return RecipeProcessor(mock_api_client, metrics, mock_session)


@pytest.fixture
def stats():
    return {
        "total": 10,
        "success": 0,
        "errors": 0,
        "skipped": 0,
        "in_progress": 0,
        "completed": 0,
        "concurrent_imports": 5,
    }


# ──────────────────────────────────────────────
# _stream_until_done
# ──────────────────────────────────────────────


async def test_stream_success(processor, stats):
    """SSE stream that completes successfully."""
    queue = asyncio.Queue()

    async def fake_stream(*args, **kwargs):
        yield {"status": "in_progress", "current_step": "scraping", "step_message": "Fetching..."}
        yield {"status": "in_progress", "current_step": "structuring", "step_message": "Structuring..."}
        yield {"status": "completed", "slug": "poulet-roti"}

    processor.api_client.stream_progress = MagicMock(return_value=fake_stream())

    result = await processor._stream_until_done("prog-1", "http://example.com/recipe", stats, queue)

    assert result is True
    assert stats["success"] == 1
    assert processor.metrics.success_count == 1


async def test_stream_error(processor, stats):
    """SSE stream that reports an error."""
    queue = asyncio.Queue()

    async def fake_stream(*args, **kwargs):
        yield {"status": "in_progress", "current_step": "scraping"}
        yield {"status": "error", "error": "LLM timeout"}

    processor.api_client.stream_progress = MagicMock(return_value=fake_stream())

    with pytest.raises(Exception, match="LLM timeout"):
        await processor._stream_until_done("prog-2", "http://example.com/recipe", stats, queue)


async def test_stream_skip_on_already_exists(processor, stats):
    """SSE stream with 'already exists' error is treated as skip."""
    queue = asyncio.Queue()

    async def fake_stream(*args, **kwargs):
        yield {"status": "error", "error": "Recipe already exists with slug: foo"}

    processor.api_client.stream_progress = MagicMock(return_value=fake_stream())

    result = await processor._stream_until_done("prog-3", "http://example.com/recipe", stats, queue)

    assert result is True
    assert stats["skipped"] == 1
    assert processor.metrics.skip_count == 1


async def test_stream_keepalive_does_not_crash(processor, stats):
    """Keepalive events should be ignored and not cause issues."""
    queue = asyncio.Queue()

    async def fake_stream(*args, **kwargs):
        yield {"status": "keepalive"}
        yield {"status": "in_progress", "current_step": "scraping", "step_message": ""}
        yield {"status": "completed", "slug": "ok"}

    processor.api_client.stream_progress = MagicMock(return_value=fake_stream())

    result = await processor._stream_until_done("prog-4", "http://example.com/recipe", stats, queue)
    assert result is True


async def test_stream_reports_steps_to_queue(processor, stats):
    """Progress updates should be forwarded to the TUI queue."""
    queue = asyncio.Queue()

    async def fake_stream(*args, **kwargs):
        yield {"status": "in_progress", "current_step": "scraping", "step_message": "Fetching URL"}
        yield {"status": "in_progress", "current_step": "structuring", "step_message": "Running LLM"}
        yield {"status": "completed", "slug": "test"}

    processor.api_client.stream_progress = MagicMock(return_value=fake_stream())

    await processor._stream_until_done("prog-5", "http://example.com/recipe", stats, queue)

    events = []
    while not queue.empty():
        events.append(queue.get_nowait())

    step_events = [e for e in events if e[1] == "step"]
    assert len(step_events) == 2
    assert "scraping" in step_events[0][2]
    assert "structuring" in step_events[1][2]


async def test_stream_unexpected_end_raises(processor, stats):
    """If stream ends without terminal status, raise."""
    queue = asyncio.Queue()

    async def fake_stream(*args, **kwargs):
        yield {"status": "in_progress", "current_step": "scraping"}
        # Stream ends without completed/error

    processor.api_client.stream_progress = MagicMock(return_value=fake_stream())

    with pytest.raises(Exception, match="SSE stream ended unexpectedly"):
        await processor._stream_until_done("prog-6", "http://example.com/recipe", stats, queue)


# ──────────────────────────────────────────────
# Fallback: SSE fails → polling
# ──────────────────────────────────────────────


async def test_fallback_to_polling_on_sse_connection_error(processor, stats):
    """If SSE connection fails, _process_with_retry falls back to polling."""
    queue = asyncio.Queue()

    async def failing_stream(*args, **kwargs):
        raise SSEConnectionError("SSE endpoint returned 404")
        yield  # noqa: make it an async generator

    processor.api_client.stream_progress = MagicMock(return_value=failing_stream())

    start_fn = AsyncMock(return_value="prog-fb")

    async def fake_poll(progress_id, item_id, stats_arg, queue_arg):
        stats_arg["success"] += 1
        processor.metrics.success_count += 1
        return True

    processor._poll_until_done = AsyncMock(side_effect=fake_poll)

    await processor._process_with_retry("http://example.com/recipe", stats, queue, start_fn)

    processor._poll_until_done.assert_called_once()
    assert stats["success"] == 1


async def test_fallback_to_polling_on_aiohttp_error(processor, stats):
    """If aiohttp client errors, fall back to polling."""
    queue = asyncio.Queue()

    async def failing_stream(*args, **kwargs):
        raise aiohttp.ClientError("Connection reset")
        yield  # noqa

    processor.api_client.stream_progress = MagicMock(return_value=failing_stream())

    start_fn = AsyncMock(return_value="prog-fb2")

    async def fake_poll(progress_id, item_id, stats_arg, queue_arg):
        stats_arg["success"] += 1
        processor.metrics.success_count += 1
        return True

    processor._poll_until_done = AsyncMock(side_effect=fake_poll)

    await processor._process_with_retry("http://example.com/recipe", stats, queue, start_fn)

    processor._poll_until_done.assert_called_once()


# ──────────────────────────────────────────────
# _process_with_retry — HTTP 409 (duplicate)
# ──────────────────────────────────────────────


async def test_duplicate_detected_on_start(processor, stats):
    """start_fn returning None means HTTP 409 duplicate."""
    queue = asyncio.Queue()

    start_fn = AsyncMock(return_value=None)

    await processor._process_with_retry("http://example.com/recipe", stats, queue, start_fn)

    assert stats["skipped"] == 1
    assert processor.metrics.skip_count == 1
