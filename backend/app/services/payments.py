from app.clients.payment import FakePaymentClient, PaymentOutcome
from app.core.logging import get_logger

logger = get_logger(__name__)
payment_client = FakePaymentClient()


def simulate_payment(
    *,
    amount_cents: int,
    order_id: int | None = None,
    outcome: PaymentOutcome = "success",
) -> dict:
    result = payment_client.charge(
        amount_cents=amount_cents,
        order_id=order_id,
        outcome=outcome,
    )
    logger.info(
        "Payment simulation completed",
        extra={
            "dependency": result["provider"],
            "payment_status": result["status"],
            "amount_cents": amount_cents,
            "order_id": order_id,
            "payment_id": result["payment_id"],
        },
    )
    return result


def simulate_successful_payment(*, amount_cents: int, order_id: int | None = None) -> dict:
    return simulate_payment(amount_cents=amount_cents, order_id=order_id)
