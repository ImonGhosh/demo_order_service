import time
from typing import Literal
from uuid import uuid4

from app.core.logging import get_logger
from app.exceptions import PaymentDeclinedError, PaymentProviderError, PaymentTimeoutError

logger = get_logger(__name__)

PaymentOutcome = Literal["success", "timeout", "declined", "provider_error"]


class FakePaymentClient:
    provider_name = "fake-payment-provider"

    def charge(
        self,
        *,
        amount_cents: int,
        order_id: int | None = None,
        outcome: PaymentOutcome = "success",
    ) -> dict:
        payment_id = f"pay_{uuid4().hex[:12]}"

        logger.info(
            "Payment charge started",
            extra={
                "dependency": self.provider_name,
                "payment_id": payment_id,
                "order_id": order_id,
                "amount_cents": amount_cents,
                "requested_outcome": outcome,
            },
        )

        if outcome == "timeout":
            time.sleep(0.25)
            raise PaymentTimeoutError("Payment provider timed out while charging card")

        if outcome == "declined":
            raise PaymentDeclinedError("Payment provider declined the transaction")

        if outcome == "provider_error":
            raise PaymentProviderError("Payment provider returned an unexpected error")

        logger.info(
            "Payment charge completed",
            extra={
                "dependency": self.provider_name,
                "payment_id": payment_id,
                "payment_status": "paid",
                "order_id": order_id,
                "amount_cents": amount_cents,
            },
        )
        return {
            "status": "paid",
            "provider": self.provider_name,
            "payment_id": payment_id,
            "amount_cents": amount_cents,
            "order_id": order_id,
        }

