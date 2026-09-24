"""
Daraja C2B webhook endpoints.

Safaricom sends two callbacks:
1. POST /api/v1/payments/daraja/validation
   → Checks if we want to accept the payment. Optional but recommended.
2. POST /api/v1/payments/daraja/confirmation
   → Records the confirmed payment into UsageStat.

Both endpoints MUST return Safaricom's expected JSON:
    {"ResultCode": 0, "ResultDesc": "Accepted"}
or
    {"ResultCode": 1, "ResultDesc": "Rejected"}

They must NEVER crash — if they do, Safaricom will retry and eventually
disable the URL.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.daraja import C2BValidationRequest, C2BConfirmationRequest, C2BResponse
from ..services.daraja import process_payment_event

router = APIRouter()


@router.post("/validation", response_model=C2BResponse)
async def daraja_validation(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Safaricom C2B Validation callback.

    We accept every payment here (ResultCode 0). Validation is only used
    for rejecting suspicious transactions. Our analytics pipeline is
    tolerant of unknown merchants — they simply get logged in the
    confirmation step, not rejected at validation time.

    Safaricom sometimes sends an empty POST as a connectivity test.
    We respond with Accept regardless.
    """
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    # Extract BillRefNumber for logging (no PII)
    bill_ref = (payload or {}).get("BillRefNumber", "—")

    print(f"[DARAJA VALIDATION] Received validation for ref '{bill_ref}'")

    # Always accept — we do the merchant lookup in the confirmation step
    return C2BResponse(ResultCode=0, ResultDesc="Accepted")


@router.post("/confirmation", response_model=C2BResponse)
async def daraja_confirmation(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Safaricom C2B Confirmation callback.

    Records the aggregate. Returns Safaricom's expected response.
    Never raises — always responds with Accept to avoid retries.
    """
    try:
        payload_dict = await request.json()
    except Exception:
        payload_dict = {}

    try:
        # Validate into the Pydantic model
        payload = C2BConfirmationRequest(**payload_dict)

        # Process — this handles all the logic and discards PII
        result = process_payment_event(payload, db)

        # Log the outcome (no PII)
        print(f"[DARAJA CONFIRMATION] Result: {result.get('status')} — {result.get('message')}")

        # Always respond Accept to Safaricom, even on unknown merchant.
        # Rejecting would cause Safaricom to retry indefinitely.
        return C2BResponse(ResultCode=0, ResultDesc="Accepted")

    except Exception as e:
        # Catch-all: never let an unexpected error crash the endpoint
        print(f"[DARAJA CONFIRMATION] Unexpected error: {type(e).__name__}: {e}")
        return C2BResponse(ResultCode=0, ResultDesc="Accepted")
