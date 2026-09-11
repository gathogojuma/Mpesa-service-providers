"""
M-Pesa webhook receiver.

Accepts payment notifications from Safaricom's Daraja API, matches them
to a business by Till number, updates daily usage aggregates, and
immediately discards the customer details.

NOTHING about the individual customer is stored.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Business
from ..services.usage_tracker import record_payment_event

router = APIRouter()


@router.post("/mpesa/callback")
async def mpesa_callback(payload: dict, db: Session = Depends(get_db)):
    """
    Handle an M-Pesa C2B / STK Push callback.

    Expected payload (simplified):
        {
            "TransID": "...",
            "TransAmount": 500.0,
            "BusinessShortCode": "174379",
            "TransTime": "20260911143000",
            ... other fields
        }

    We ONLY extract:
    - The Till number (to identify the business)
    - The amount (for aggregation)

    We DISCARD: phone number, customer name, transaction ID, anything personal.
    """
    till = str(payload.get("BusinessShortCode") or payload.get("TillNumber") or "")
    amount_raw = payload.get("TransAmount") or payload.get("Amount") or 0

    if not till:
        raise HTTPException(status_code=400, detail="Missing till number")

    try:
        amount = float(amount_raw)
    except (TypeError, ValueError):
        amount = 0.0

    business = db.query(Business).filter(Business.mpesa_till == till).first()
    if not business:
        # Unknown till — ignore silently. Don't 404 because Safaricom retries.
        return {"status": "ignored", "reason": "unknown till"}

    # Update the aggregate. This is the only write that happens.
    record_payment_event(db, business_id=business.id, amount=amount)

    return {"status": "recorded"}
