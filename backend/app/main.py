from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.health import router as health_router
from app.api.routes.orders import router as orders_router
from app.api.routes.payments import router as payments_router
from app.api.routes.products import router as products_router
from app.api.routes.test_errors import router as test_errors_router
from app.api.routes.users import router as users_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.db.init_db import init_db, seed_products
from app.db.session import SessionLocal
from app.jobs.reconciliation import run_reconciliation_loop, stop_reconciliation_loop
from app.middleware.request_context import RequestContextMiddleware

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with SessionLocal() as db:
        seed_products(db)

    reconciliation_task: asyncio.Task[None] | None = None
    if settings.reconciliation_job_enabled:
        reconciliation_task = asyncio.create_task(
            run_reconciliation_loop(
                interval_seconds=settings.reconciliation_interval_seconds
            )
        )
        app.state.reconciliation_task = reconciliation_task
    else:
        logger.info("Order reconciliation job disabled by configuration")

    logger.info("Application startup completed")
    try:
        yield
    finally:
        await stop_reconciliation_loop(reconciliation_task)
        logger.info("Application shutdown completed")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.service_name,
        version=settings.version,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestContextMiddleware)
    app.include_router(health_router)
    app.include_router(users_router)
    app.include_router(products_router)
    app.include_router(orders_router)
    app.include_router(payments_router)
    app.include_router(test_errors_router)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.error(
            "Request validation failed",
            extra={
                "endpoint": request.url.path,
                "method": request.method,
                "error_type": exc.__class__.__name__,
                "error_message": str(exc),
                "error_category": "validation_error",
            },
        )
        return JSONResponse(
            status_code=422,
            content={
                "detail": exc.errors(),
                "error_category": "validation_error",
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error(
            "Unhandled application exception",
            exc_info=(type(exc), exc, exc.__traceback__),
            extra={
                "endpoint": request.url.path,
                "method": request.method,
                "error_type": exc.__class__.__name__,
                "error_message": str(exc),
                "error_category": "runtime_exception",
            },
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "error_category": "runtime_exception",
            },
        )

    return app


app = create_app()
