"""
Daraja C2B webhook endpoints.

Safaricom sends two callbacks:
1. POST /api/v1/payments/daraja/validation
2. POST /api/v1/payments/daraja/confirmation

Both endpoints MUST return Safaricom's expected JSON.
They must NEVER crash — if they do, Safaricom will retry and eventually
disable the URL.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import C2BValidationRequest, C2BConfirmationRequest, C2BResponse
from ..services.daraja import process_payment_event

router = APIRouter()


@router.post("/validation", response_model=C2BResponse)
async def daraja_validation(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Safaricom C2B Validation callback.

    We accept every payment here. Validation is only for rejecting
    suspicious transactions. Our analytics pipeline handles unknown
    merchants gracefully in the confirmation step.
    """
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    bill_ref = (payload or {}).get("BillRefNumber", "—")

    print(f"[DARAJA VALIDATION] Received validation for ref '{bill_ref}'")

    return C2BResponse(ResultCode=0, ResultDesc="Accepted")


@router.post("/confirmation", response_model=C2BResponse)
async def daraja_confirmation(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Safaricom C2B Confirmation callback.

    Records the aggregate. Returns Safaricom's expected response.
    Never raises — always responds with Accept.
    """
    try:
        payload_dict = await request.json()
    except Exception:
        payload_dict = {}

    try:
        payload = C2BConfirmationRequest(**payload_dict)
        result = process_payment_event(payload, db)
        print(f"[DARAJA CONFIRMATION] Result: {result.get('status')} — {result.get('message')}")
        return C2BResponse(ResultCode=0, ResultDesc="Accepted")

    except Exception as e:
        print(f"[DARAJA CONFIRMATION] Unexpected error: {type(e).__name__}: {e}")
        return C2BResponse(ResultCode=0, ResultDesc="Accepted")
