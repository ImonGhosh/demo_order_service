import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger, request_id_ctx, trace_id_ctx

logger = get_logger(__name__)

REQUEST_ID_HEADER = "x-request-id"
TRACE_ID_HEADER = "x-trace-id"


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid4())
        trace_id = request.headers.get(TRACE_ID_HEADER) or request_id

        request_id_token = request_id_ctx.set(request_id)
        trace_id_token = trace_id_ctx.set(trace_id)
        start_time = time.perf_counter()

        logger.info(
            "Request started",
            extra={
                "endpoint": request.url.path,
                "method": request.method,
            },
        )

        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.info(
                "Request completed",
                extra={
                    "endpoint": request.url.path,
                    "method": request.method,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                },
            )

            request_id_ctx.reset(request_id_token)
            trace_id_ctx.reset(trace_id_token)

            if "response" in locals():
                response.headers[REQUEST_ID_HEADER] = request_id
                response.headers[TRACE_ID_HEADER] = trace_id

