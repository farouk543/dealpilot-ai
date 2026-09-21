import contextvars
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

_CORRELATION_HEADER = "X-Correlation-ID"
_correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="-")


def new_correlation_id() -> str:
    return uuid.uuid4().hex[:12]


def get_correlation_id() -> str:
    return _correlation_id_var.get()


def set_correlation_id(correlation_id: str) -> None:
    _correlation_id_var.set(correlation_id)


class _CorrelationIdLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = _correlation_id_var.get()
        return True


def configure_logging(service_name: str) -> None:
    """Call once per service at startup. Every log line then carries the
    correlation ID of the deal/request it belongs to, so a single dossier's
    path across the 13 microservices can be grepped out of the combined logs."""
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(f"%(asctime)s [{service_name}] [%(correlation_id)s] %(levelname)s %(message)s"))
    handler.addFilter(_CorrelationIdLogFilter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Reads X-Correlation-ID from the incoming request (set by an upstream
    service) or mints a new one, makes it available via get_correlation_id()
    for the duration of the request, echoes it back on the response, and logs
    one line per request with method/path/status/duration."""

    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get(_CORRELATION_HEADER) or new_correlation_id()
        set_correlation_id(correlation_id)
        logger = get_logger("request")
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.exception(f"{request.method} {request.url.path} failed after {duration_ms:.0f}ms")
            raise
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers[_CORRELATION_HEADER] = correlation_id
        logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms:.0f}ms)")
        return response
