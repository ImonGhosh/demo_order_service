from typing import Literal

from pydantic import BaseModel, Field


class PaymentSimulationRequest(BaseModel):
    order_id: int | None = Field(default=None, gt=0)
    amount_cents: int = Field(gt=0)
    outcome: Literal["success", "timeout", "declined", "provider_error"] = "success"


class PaymentSimulationResponse(BaseModel):
    status: str
    provider: str
    payment_id: str
    amount_cents: int
    order_id: int | None = None
