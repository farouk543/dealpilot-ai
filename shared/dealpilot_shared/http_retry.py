import asyncio
import time
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")


def with_retry(fn: Callable[[], T], attempts: int = 2, backoff_seconds: float = 1.0) -> T:
    """Retries a synchronous call on any exception, with linear backoff.

    attempts=2 means up to 3 total tries (1 initial + 2 retries) — enough to
    absorb a transient timeout/5xx from a third-party API (Groq, Gemini, DVF,
    BAN, Apicarto) without masking a genuinely broken endpoint.
    """
    last_exc: Exception | None = None
    for attempt in range(attempts + 1):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            if attempt < attempts:
                time.sleep(backoff_seconds * (attempt + 1))
    assert last_exc is not None
    raise last_exc


async def with_retry_async(fn: Callable[[], Awaitable[T]], attempts: int = 2, backoff_seconds: float = 1.0) -> T:
    last_exc: Exception | None = None
    for attempt in range(attempts + 1):
        try:
            return await fn()
        except Exception as exc:
            last_exc = exc
            if attempt < attempts:
                await asyncio.sleep(backoff_seconds * (attempt + 1))
    assert last_exc is not None
    raise last_exc
