import asyncio
from contextlib import suppress

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.exceptions import BackgroundJobFailureError
from app.repositories.orders import list_reconcilable_orders, mark_orders_completed

logger = get_logger(__name__)
JOB_NAME = "order_reconciliation"


def run_reconciliation_once(*, force_failure: bool = False) -> dict[str, int | str]:
    logger.info("Order reconciliation job started", extra={"job_name": JOB_NAME})

    if force_failure:
        raise BackgroundJobFailureError("Order reconciliation failed intentionally")

    with SessionLocal() as db:
        reconcilable_orders = list_reconcilable_orders(db)
        completed_count = mark_orders_completed(db, reconcilable_orders)

    logger.info(
        "Order reconciliation job completed",
        extra={
            "job_name": JOB_NAME,
            "reconcilable_order_count": len(reconcilable_orders),
            "completed_order_count": completed_count,
        },
    )
    return {
        "status": "completed",
        "reconcilable_order_count": len(reconcilable_orders),
        "completed_order_count": completed_count,
    }


async def run_reconciliation_loop(*, interval_seconds: float) -> None:
    logger.info(
        "Order reconciliation loop started",
        extra={"job_name": JOB_NAME, "interval_seconds": interval_seconds},
    )

    try:
        while True:
            try:
                run_reconciliation_once()
            except Exception as exc:
                logger.exception(
                    "Order reconciliation job failed",
                    extra={
                        "job_name": JOB_NAME,
                        "error_category": "background_job_failure",
                        "error_type": exc.__class__.__name__,
                        "error_message": str(exc),
                    },
                )

            await asyncio.sleep(interval_seconds)
    except asyncio.CancelledError:
        logger.info("Order reconciliation loop stopping", extra={"job_name": JOB_NAME})
        raise


async def stop_reconciliation_loop(task: asyncio.Task[None] | None) -> None:
    if task is None:
        return

    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
