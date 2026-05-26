import logging
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(
                "Request failed: %s %s %.2fms",
                request.method,
                request.url.path,
                duration_ms,
            )
            raise
        
        duration_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "Request finished: %s %s status-%s %.2fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )

        response.headers["X-Process-Time-ms"] = f"{duration_ms: 2f}"

        return response