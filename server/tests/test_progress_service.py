"""Tests for ProgressService — pub/sub, SSE notifications, and core operations."""

import asyncio
import json
import pytest

from services.progress_service import ProgressService


@pytest.fixture
def service():
    return ProgressService()


# ──────────────────────────────────────────────
# Core operations
# ──────────────────────────────────────────────


async def test_register_creates_entry(service: ProgressService):
    await service.register("test-1", import_type="url")
    progress = await service.get_progress("test-1")
    assert progress is not None
    assert progress.status == "pending"
    assert len(progress.steps) == 4


async def test_register_text_has_correct_steps(service: ProgressService):
    await service.register("test-2", import_type="text")
    progress = await service.get_progress("test-2")
    step_names = [s.step for s in progress.steps]
    assert "check_existence" in step_names
    assert "generate_recipe" in step_names


async def test_register_image_has_correct_steps(service: ProgressService):
    await service.register("test-3", import_type="image")
    progress = await service.get_progress("test-3")
    step_names = [s.step for s in progress.steps]
    assert "ocr_extract" in step_names
    assert len(progress.steps) == 3


async def test_update_step_changes_status(service: ProgressService):
    await service.register("test-4")
    await service.update_step("test-4", step="check_existence", status="in_progress")
    progress = await service.get_progress("test-4")
    assert progress.status == "in_progress"
    assert progress.current_step == "check_existence"


async def test_complete_sets_slug(service: ProgressService):
    await service.register("test-5")
    await service.complete("test-5", {"slug": "poulet-roti"})
    progress = await service.get_progress("test-5")
    assert progress.status == "completed"
    assert progress.recipe == {"metadata": {"slug": "poulet-roti"}}


async def test_set_error(service: ProgressService):
    await service.register("test-6")
    await service.set_error("test-6", "Something broke")
    progress = await service.get_progress("test-6")
    assert progress.status == "error"
    assert progress.error == "Something broke"


async def test_get_progress_returns_none_for_unknown(service: ProgressService):
    result = await service.get_progress("nonexistent")
    assert result is None


# ──────────────────────────────────────────────
# Pub/sub SSE notifications
# ──────────────────────────────────────────────


async def test_subscribe_creates_queue(service: ProgressService):
    await service.register("sub-1")
    queue = service.subscribe("sub-1")
    assert isinstance(queue, asyncio.Queue)
    assert "sub-1" in service._subscribers
    assert queue in service._subscribers["sub-1"]


async def test_unsubscribe_removes_queue(service: ProgressService):
    await service.register("sub-2")
    queue = service.subscribe("sub-2")
    service.unsubscribe("sub-2", queue)
    assert "sub-2" not in service._subscribers


async def test_unsubscribe_unknown_is_safe(service: ProgressService):
    queue = asyncio.Queue()
    service.unsubscribe("nonexistent", queue)


async def test_notify_on_update_step(service: ProgressService):
    await service.register("sub-3")
    queue = service.subscribe("sub-3")

    await service.update_step("sub-3", step="check_existence", status="in_progress")

    assert not queue.empty()
    data = json.loads(queue.get_nowait())
    assert data["status"] == "in_progress"
    assert data["currentStep"] == "check_existence"


async def test_notify_on_complete(service: ProgressService):
    await service.register("sub-4")
    queue = service.subscribe("sub-4")

    await service.complete("sub-4", {"slug": "tarte-pommes"})

    assert not queue.empty()
    data = json.loads(queue.get_nowait())
    assert data["status"] == "completed"
    assert data["recipe"]["metadata"]["slug"] == "tarte-pommes"


async def test_notify_on_error(service: ProgressService):
    await service.register("sub-5")
    queue = service.subscribe("sub-5")

    await service.set_error("sub-5", "LLM timeout")

    assert not queue.empty()
    data = json.loads(queue.get_nowait())
    assert data["status"] == "error"
    assert data["error"] == "LLM timeout"


async def test_multiple_subscribers_receive_same_event(service: ProgressService):
    await service.register("sub-6")
    q1 = service.subscribe("sub-6")
    q2 = service.subscribe("sub-6")

    await service.update_step("sub-6", step="scrape_content", status="in_progress")

    assert not q1.empty()
    assert not q2.empty()
    d1 = json.loads(q1.get_nowait())
    d2 = json.loads(q2.get_nowait())
    assert d1["currentStep"] == d2["currentStep"] == "scrape_content"


async def test_no_notification_without_subscribers(service: ProgressService):
    """Calling _notify without subscribers should not raise."""
    await service.register("sub-7")
    await service.update_step("sub-7", step="check_existence", status="completed", progress=100)


async def test_update_step_error_propagates_message(service: ProgressService):
    """When update_step sets status=error, the step message should be
    copied to the top-level error field so SSE clients get the detail."""
    await service.register("err-prop-1")
    queue = service.subscribe("err-prop-1")

    await service.update_step(
        "err-prop-1",
        step="check_existence",
        status="error",
        message="Recipe already exists with slug: foo",
    )

    data = json.loads(queue.get_nowait())
    assert data["status"] == "error"
    assert data["error"] == "Recipe already exists with slug: foo"


async def test_full_lifecycle_notifications(service: ProgressService):
    """Simulate a full recipe generation lifecycle and verify all events."""
    await service.register("life-1")
    queue = service.subscribe("life-1")

    await service.update_step("life-1", step="check_existence", status="in_progress")
    await service.update_step("life-1", step="check_existence", status="completed", progress=100)
    await service.update_step("life-1", step="scrape_content", status="in_progress", message="Fetching...")
    await service.update_step("life-1", step="structure_recipe", status="in_progress", message="Structuring...")
    await service.update_step("life-1", step="save_recipe", status="in_progress", message="Saving...")
    await service.complete("life-1", {"slug": "carbonara"})

    events = []
    while not queue.empty():
        events.append(json.loads(queue.get_nowait()))

    assert len(events) == 6
    assert events[0]["status"] == "in_progress"
    assert events[-1]["status"] == "completed"
    assert events[-1]["recipe"]["metadata"]["slug"] == "carbonara"
