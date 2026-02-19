"""Tests for the SSE streaming endpoint GET /api/recipes/progress/{id}/stream."""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient

from services.progress_service import ProgressService


@pytest.fixture
def progress_service():
    return ProgressService()


@pytest.fixture
def app(progress_service):
    """Create a minimal FastAPI app with the recipes router."""
    from fastapi import FastAPI
    from api.routes.recipes import router
    from api.dependencies import get_recipe_service
    from services.recipe_service import RecipeService

    test_app = FastAPI()
    test_app.include_router(router)

    mock_service = AsyncMock(spec=RecipeService)
    mock_service.progress_service = progress_service
    mock_service.get_generation_progress = progress_service.get_progress

    test_app.dependency_overrides[get_recipe_service] = lambda: mock_service
    return test_app


def parse_sse_events(raw: str) -> list[dict]:
    """Parse raw SSE text into a list of dicts."""
    events = []
    for block in raw.split("\n\n"):
        for line in block.strip().split("\n"):
            if line.startswith("data: "):
                try:
                    events.append(json.loads(line[6:]))
                except json.JSONDecodeError:
                    pass
    return events


async def test_sse_streams_updates_until_complete(app, progress_service):
    await progress_service.register("sse-1", import_type="url")

    async def simulate_progress():
        await asyncio.sleep(0.05)
        await progress_service.update_step("sse-1", step="check_existence", status="in_progress")
        await asyncio.sleep(0.05)
        await progress_service.complete("sse-1", {"slug": "test-recipe"})

    task = asyncio.create_task(simulate_progress())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/recipes/progress/sse-1/stream", timeout=5.0)

    await task

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]

    events = parse_sse_events(resp.text)
    assert len(events) >= 2
    assert events[0]["status"] == "pending"
    assert events[-1]["status"] == "completed"
    assert events[-1]["recipe"]["metadata"]["slug"] == "test-recipe"


async def test_sse_streams_error(app, progress_service):
    await progress_service.register("sse-2", import_type="url")

    async def simulate_error():
        await asyncio.sleep(0.05)
        await progress_service.set_error("sse-2", "LLM crashed")

    task = asyncio.create_task(simulate_error())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/recipes/progress/sse-2/stream", timeout=5.0)

    await task

    events = parse_sse_events(resp.text)
    assert events[-1]["status"] == "error"
    assert events[-1]["error"] == "LLM crashed"


async def test_sse_not_found_for_unknown_id(app, progress_service):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/recipes/progress/nonexistent/stream", timeout=5.0)

    events = parse_sse_events(resp.text)
    assert len(events) == 1
    assert events[0].get("error") == "not_found"


async def test_sse_already_completed(app, progress_service):
    """If progress is already completed, SSE returns it and closes."""
    await progress_service.register("sse-3", import_type="url")
    await progress_service.complete("sse-3", {"slug": "already-done"})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/recipes/progress/sse-3/stream", timeout=5.0)

    events = parse_sse_events(resp.text)
    assert len(events) == 1
    assert events[0]["status"] == "completed"
    assert events[0]["recipe"]["metadata"]["slug"] == "already-done"


async def test_sse_full_lifecycle(app, progress_service):
    """Simulate a complete URL recipe generation lifecycle via SSE."""
    await progress_service.register("sse-4", import_type="url")

    async def simulate_full():
        await asyncio.sleep(0.02)
        await progress_service.update_step("sse-4", step="check_existence", status="in_progress")
        await asyncio.sleep(0.02)
        await progress_service.update_step("sse-4", step="check_existence", status="completed", progress=100)
        await asyncio.sleep(0.02)
        await progress_service.update_step("sse-4", step="scrape_content", status="in_progress", message="Fetching...")
        await asyncio.sleep(0.02)
        await progress_service.update_step("sse-4", step="structure_recipe", status="in_progress", message="Structuring...")
        await asyncio.sleep(0.02)
        await progress_service.complete("sse-4", {"slug": "carbonara"})

    task = asyncio.create_task(simulate_full())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/recipes/progress/sse-4/stream", timeout=5.0)

    await task

    events = parse_sse_events(resp.text)
    statuses = [e["status"] for e in events]
    assert statuses[0] == "pending"
    assert "in_progress" in statuses
    assert statuses[-1] == "completed"
