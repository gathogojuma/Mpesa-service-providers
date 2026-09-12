"""
M-Pesa webhook receiver.

Accepts two kinds of payment notifications:
1. STK Push callbacks (customer approved a prompt initiated by our app)
2. C2B callbacks (customer paid the Till directly)

Both are classified as 'app' or 'c2b' and recorded as aggregates.
No customer-level data is ever stored.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Business
from ..services.usage_tracker import record_payment_event

router = APIRouter()


def classify_source(payload: dict) -> str:
    """
    Determine the payment source from the callback payload.

    Returns 'app' or 'c2b'. Defaults to 'app' if ambiguous.
    """
    trans_type = str(payload.get("TransactionType", "")).lower()

    # C2B indicators
    c2b_markers = ["pay bill", "buy goods", "c2b", "customer paybill", "customer buygoods"]
    if any(marker in trans_type for marker in c2b_markers):
        return "c2b"

    return "app"


@router.post("/mpesa/callback")
async def mpesa_callback(payload: dict, db: Session = Depends(get_db)):
    """
    Handle an M-Pesa callback.

    We ONLY extract:
    - The Till number (to identify the business)
    - The amount (for aggregation)
    - The transaction type (to classify source)

    We DISCARD: phone number, customer name, transaction ID, anything personal.
    """
    till = str(
        payload.get("BusinessShortCode")
        or payload.get("TillNumber")
        or payload.get("ShortCode")
        or ""
    )
    amount_raw = payload.get("TransAmount") or payload.get("Amount") or 0

    if not till:
        raise HTTPException(status_code=400, detail="Missing till number")

    try:
        amount = float(amount_raw)
    except (TypeError, ValueError):
        amount = 0.0

    business = db.query(Business).filter(Business.mpesa_till == till).first()
    if not business:
        # Unknown Till — ignore silently. Safaricom retries on 4xx/5xx,
        # so we return 200 to avoid noise.
        return {"status": "ignored", "reason": "unknown till"}

    source = classify_source(payload)

    record_payment_event(
        db,
        business_id=business.id,
        amount=amount,
        source=source,
    )

    return {"status": "recorded", "source": source}
