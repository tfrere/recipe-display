"""Langfuse observability integration for the recipe pipeline.

This module provides a lightweight wrapper around Langfuse's `@observe()`
decorator. If Langfuse environment variables are not set, all decorators
become no-ops — zero overhead, zero side effects.

Required env vars for activation:
    LANGFUSE_PUBLIC_KEY
    LANGFUSE_SECRET_KEY
    LANGFUSE_HOST          (default: http://localhost:3000)

Usage in other modules:
    from recipe_scraper.observability import observe, langfuse_context

    @observe(name="my_step")
    async def my_pipeline_step(...):
        langfuse_context.update_current_trace(metadata={"tokens": 42})
        ...
"""

import logging
import os
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# ── Check if Langfuse is configured ─────────────────────────────────

_LANGFUSE_ENABLED = bool(
    os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")
)

if _LANGFUSE_ENABLED:
    try:
        from langfuse import observe as _lf_observe
        from langfuse import get_client as _lf_get_client

        # Verify import works (v3 API)
        _lf_client = _lf_get_client()
        logger.info(
            "Langfuse observability ENABLED (host=%s)",
            os.getenv("LANGFUSE_HOST", "http://localhost:3000"),
        )
    except ImportError:
        logger.warning("Langfuse keys set but package not installed — observability disabled")
        _LANGFUSE_ENABLED = False
    except Exception as e:
        logger.warning(f"Langfuse initialization failed: {e} — observability disabled")
        _LANGFUSE_ENABLED = False
else:
    logger.debug("Langfuse observability disabled (no LANGFUSE_PUBLIC_KEY/SECRET_KEY)")


# ── Public API ──────────────────────────────────────────────────────


def observe(name: Optional[str] = None, **kwargs) -> Callable:
    """Decorator that wraps Langfuse @observe() if enabled, otherwise no-op."""
    if _LANGFUSE_ENABLED:
        return _lf_observe(name=name, **kwargs)

    # No-op decorator: return function unchanged
    def noop_decorator(fn: Callable) -> Callable:
        return fn
    return noop_decorator


class _NoOpContext:
    """Stub that silently ignores all Langfuse context calls."""

    def update_current_observation(self, **kwargs: Any) -> None:
        pass

    def update_current_trace(self, **kwargs: Any) -> None:
        pass

    def score_current_trace(self, **kwargs: Any) -> None:
        pass

    def score_current_span(self, **kwargs: Any) -> None:
        pass

    def update_current_span(self, **kwargs: Any) -> None:
        pass

    def update_current_generation(self, **kwargs: Any) -> None:
        pass

    def get_current_trace_id(self) -> Optional[str]:
        return None

    def get_current_observation_id(self) -> Optional[str]:
        return None


class _LangfuseContextProxy:
    """Proxy that delegates to the Langfuse client (v3 API).

    In Langfuse v3, `langfuse_context` is replaced by methods on
    the client obtained via `get_client()`.
    """

    def update_current_trace(self, **kwargs: Any) -> None:
        try:
            _lf_get_client().update_current_trace(**kwargs)
        except Exception:
            pass

    def score_current_trace(self, **kwargs: Any) -> None:
        try:
            _lf_get_client().score_current_trace(**kwargs)
        except Exception:
            pass

    def update_current_span(self, **kwargs: Any) -> None:
        try:
            _lf_get_client().update_current_span(**kwargs)
        except Exception:
            pass

    def score_current_span(self, **kwargs: Any) -> None:
        try:
            _lf_get_client().score_current_span(**kwargs)
        except Exception:
            pass

    def update_current_generation(self, **kwargs: Any) -> None:
        try:
            _lf_get_client().update_current_generation(**kwargs)
        except Exception:
            pass

    def update_current_observation(self, **kwargs: Any) -> None:
        try:
            _lf_get_client().update_current_span(**kwargs)
        except Exception:
            pass

    def get_current_trace_id(self) -> Optional[str]:
        try:
            return _lf_get_client().get_current_trace_id()
        except Exception:
            return None

    def get_current_observation_id(self) -> Optional[str]:
        try:
            return _lf_get_client().get_current_observation_id()
        except Exception:
            return None


langfuse_context = _LangfuseContextProxy() if _LANGFUSE_ENABLED else _NoOpContext()


# ── OpenAI client wrapper ────────────────────────────────────────────

def get_async_openai_class():
    """Return the AsyncOpenAI class — instrumented if Langfuse is enabled.

    Usage:
        from recipe_scraper.observability import get_async_openai_class
        AsyncOpenAI = get_async_openai_class()
        client = AsyncOpenAI(api_key=..., base_url=...)
    """
    if _LANGFUSE_ENABLED:
        try:
            from langfuse.openai import AsyncOpenAI as LangfuseAsyncOpenAI
            logger.info("Using Langfuse-instrumented AsyncOpenAI (auto-captures generations)")
            return LangfuseAsyncOpenAI
        except ImportError:
            logger.warning("langfuse.openai not available — falling back to standard AsyncOpenAI")

    from openai import AsyncOpenAI
    return AsyncOpenAI
