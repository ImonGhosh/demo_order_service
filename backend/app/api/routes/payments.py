from fastapi import APIRouter

from app.schemas.payments import PaymentSimulationRequest, PaymentSimulationResponse
from app.services.payments import simulate_payment as simulate_payment_service

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/simulate", response_model=PaymentSimulationResponse)
async def simulate_payment(payload: PaymentSimulationRequest):
    return simulate_payment_service(
        amount_cents=payload.amount_cents,
        order_id=payload.order_id,
        outcome=payload.outcome,
    )
