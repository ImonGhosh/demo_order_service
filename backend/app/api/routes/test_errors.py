import time

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.session import get_db
from app.exceptions import (
    BackgroundJobFailureError,
    MissingConfigurationError,
    PaymentDeclinedError,
    PaymentProviderError,
    PaymentTimeoutError,
)
from app.jobs.reconciliation import run_reconciliation_once
from app.repositories import products as product_repository
from app.repositories import users as user_repository
from app.schemas.errors import ErrorInjectionResponse
from app.schemas.orders import OrderCreate
from app.services import orders as order_service
from app.services.configuration import require_setting
from app.services.payments import simulate_payment

logger = get_logger(__name__)
router = APIRouter(prefix="/test/errors", tags=["error-injection"])


def error_response(
    *,
    status_code: int,
    error_category: str,
    message: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "error_injected",
            "error_category": error_category,
            "message": message,
        },
    )


def raise_runtime_failure() -> None:
    raise RuntimeError("Intentional runtime exception from error injection endpoint")


@router.post("/runtime-exception", response_model=ErrorInjectionResponse)
async def inject_runtime_exception():
    try:
        raise_runtime_failure()
    except RuntimeError as exc:
        logger.exception(
            "Intentional runtime exception injected",
            extra={
                "error_category": "runtime_exception",
                "error_type": exc.__class__.__name__,
                "error_message": str(exc),
            },
        )
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_category="runtime_exception",
            message=str(exc),
        )


@router.post("/db-connection", response_model=ErrorInjectionResponse)
async def inject_db_connection_failure():
    try:
        raise OperationalError(
            "SELECT 1",
            {},
            RuntimeError("Simulated database connection refused"),
        )
    except OperationalError as exc:
        logger.exception(
            "Intentional database connection failure injected",
            extra={
                "error_category": "database_connection_failure",
                "error_type": exc.__class__.__name__,
                "error_message": str(exc),
                "dependency": "sqlite",
            },
        )
        return error_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_category="database_connection_failure",
            message="Simulated database connection failure",
        )


@router.post("/db-slow-query", response_model=ErrorInjectionResponse)
async def inject_db_slow_query():
    start_time = time.perf_counter()
    try:
        time.sleep(0.75)
        raise TimeoutError("Simulated database query exceeded timeout threshold")
    except TimeoutError as exc:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.exception(
            "Intentional slow database query injected",
            extra={
                "error_category": "database_slow_query",
                "error_type": exc.__class__.__name__,
                "error_message": str(exc),
                "dependency": "sqlite",
                "duration_ms": duration_ms,
            },
        )
        return error_response(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            error_category="database_slow_query",
            message="Simulated database slow query timeout",
        )


@router.post("/validation", response_model=ErrorInjectionResponse)
async def inject_validation_error():
    try:
        raise ValueError("Intentional malformed order payload")
    except ValueError as exc:
        logger.exception(
            "Intentional validation error injected",
            extra={
                "error_category": "validation_error",
                "error_type": exc.__class__.__name__,
                "error_message": str(exc),
            },
        )
        return error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_category="validation_error",
            message=str(exc),
        )


@router.post("/inventory-mismatch", response_model=ErrorInjectionResponse)
async def inject_inventory_mismatch(db: Session = Depends(get_db)):
    user = user_repository.get_user_by_email(db, "inventory-test@example.com")
    if not user:
        user = user_repository.create_user(
            db,
            email="inventory-test@example.com",
            name="Inventory Test User",
        )

    product = product_repository.get_product_by_sku(db, "SKU-OUT-OF-STOCK")
    if not product:
        product = product_repository.create_product(
            db,
            sku="SKU-OUT-OF-STOCK",
            name="Out Of Stock Test Product",
            price_cents=999,
            inventory_count=0,
        )

    try:
        order_service.create_order(
            db,
            OrderCreate(user_id=user.id, product_id=product.id, quantity=1),
        )
    except Exception as exc:
        logger.exception(
            "Intentional inventory mismatch injected",
            extra={
                "error_category": "inventory_mismatch",
                "error_type": exc.__class__.__name__,
                "error_message": str(exc),
                "user_id": user.id,
                "product_id": product.id,
                "available_inventory": product.inventory_count,
                "requested_quantity": 1,
            },
        )
        return error_response(
            status_code=status.HTTP_409_CONFLICT,
            error_category="inventory_mismatch",
            message="Simulated inventory mismatch",
        )

    return error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_category="inventory_mismatch",
        message="Inventory mismatch injection did not fail as expected",
    )


@router.post("/payment-timeout", response_model=ErrorInjectionResponse)
async def inject_payment_timeout():
    try:
        simulate_payment(amount_cents=1299, outcome="timeout")
    except PaymentTimeoutError as exc:
        logger.exception(
            "Intentional payment timeout injected",
            extra={
                "error_category": "payment_timeout",
                "error_type": exc.__class__.__name__,
                "error_message": str(exc),
                "dependency": "fake-payment-provider",
                "duration_ms": 250,
            },
        )
        return error_response(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            error_category="payment_timeout",
            message=str(exc),
        )


@router.post("/payment-declined", response_model=ErrorInjectionResponse)
async def inject_payment_declined():
    try:
        simulate_payment(amount_cents=1299, outcome="declined")
    except PaymentDeclinedError as exc:
        logger.exception(
            "Intentional payment declined injected",
            extra={
                "error_category": "payment_declined",
                "error_type": exc.__class__.__name__,
                "error_message": str(exc),
                "dependency": "fake-payment-provider",
            },
        )
        return error_response(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            error_category="payment_declined",
            message=str(exc),
        )
    except PaymentProviderError as exc:
        logger.exception(
            "Unexpected payment provider error during declined injection",
            extra={
                "error_category": "payment_declined",
                "error_type": exc.__class__.__name__,
                "error_message": str(exc),
                "dependency": "fake-payment-provider",
            },
        )
        return error_response(
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_category="payment_declined",
            message=str(exc),
        )


@router.post("/config-missing", response_model=ErrorInjectionResponse)
async def inject_missing_config():
    try:
        require_setting("DEMO_REQUIRED_PAYMENT_API_KEY")
    except MissingConfigurationError as exc:
        logger.exception(
            "Intentional configuration error injected",
            extra={
                "error_category": "configuration_error",
                "error_type": exc.__class__.__name__,
                "error_message": str(exc),
                "config_key": "DEMO_REQUIRED_PAYMENT_API_KEY",
            },
        )
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_category="configuration_error",
            message=str(exc),
        )


@router.post("/background-job-failure", response_model=ErrorInjectionResponse)
async def inject_background_job_failure():
    try:
        run_reconciliation_once(force_failure=True)
    except BackgroundJobFailureError as exc:
        logger.exception(
            "Intentional background job failure injected",
            extra={
                "error_category": "background_job_failure",
                "error_type": exc.__class__.__name__,
                "error_message": str(exc),
                "job_name": "order_reconciliation",
            },
        )
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_category="background_job_failure",
            message=str(exc),
        )

