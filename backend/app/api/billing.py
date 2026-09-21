"""
Billing endpoints.

- POST /api/billing/checkout — starts a payment session for a business
- POST /api/billing/callback — Pesapal IPN callback
- GET /api/billing/status — checks current subscription status
"""
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Business, Subscription
from ..auth import get_current_staff
from ..services.billing import pesapal_service
from ..utils.timezone import now_local

router = APIRouter()


@router.post("/checkout")
async def start_checkout(
    db: Session = Depends(get_db),
    current_staff = Depends(get_current_staff),
):
    """
    Start a payment session for the current business's subscription.
    Returns a redirect URL where the manager can complete payment.
    """
    if current_staff.role not in ("manager", "owner"):
        raise HTTPException(status_code=403, detail="Only managers can pay")

    if not current_staff.business_id:
        raise HTTPException(status_code=400, detail="No business associated")

    business = db.query(Business).filter(Business.id == current_staff.business_id).first()
    subscription = db.query(Subscription).filter(
        Subscription.business_id == business.id
    ).first()

    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    # STEP 1: Register IPN with Pesapal to get a valid IPN ID
    print("[BILLING] Registering IPN with Pesapal...")
    ipn_id = pesapal_service.register_ipn()

    if not ipn_id:
        print("[BILLING] ERROR: Failed to register IPN")
        raise HTTPException(
            status_code=500,
            detail="Failed to register IPN with Pesapal. Check backend logs for details."
        )

    print(f"[BILLING] Got IPN ID: {ipn_id}")

    # STEP 2: Generate unique merchant reference
    merchant_reference = f"SUB-{uuid.uuid4().hex[:12].upper()}"

    # STEP 3: Submit the order
    print(f"[BILLING] Submitting order for {merchant_reference}")
    order = pesapal_service.submit_order(
        merchant_reference=merchant_reference,
        amount=subscription.monthly_fee,
        description=f"TillTrack {subscription.plan} plan - {business.name}",
        callback_url="https://mpesa-service-dashboard.onrender.com/billing-callback.html",
        ipn_id=ipn_id,  # ✅ Valid IPN ID from Pesapal
    )

    if not order or not order.get("redirect_url"):
        print("[BILLING] ERROR: Order submission failed")
        raise HTTPException(status_code=500, detail="Failed to create payment session")

    print(f"[BILLING] SUCCESS — redirect_url: {order.get('redirect_url')}")

    return {
        "status": "success",
        "merchant_reference": merchant_reference,
        "redirect_url": order["redirect_url"],
        "order_tracking_id": order.get("order_tracking_id"),
        "amount": subscription.monthly_fee,
    }


@router.post("/callback")
async def pesapal_callback(request: Request, db: Session = Depends(get_db)):
    """
    Pesapal IPN callback — receives payment notifications.
    """
    try:
        payload = await request.json()
    except Exception:
        return {"status": "ignored", "reason": "invalid payload"}

    order_tracking_id = payload.get("OrderTrackingId")
    merchant_reference = payload.get("OrderMerchantReference")

    print(f"[BILLING CALLBACK] Received: {payload}")

    if not order_tracking_id:
        return {"status": "ignored", "reason": "no tracking id"}

    payment_status = pesapal_service.get_transaction_status(order_tracking_id)

    if payment_status != "COMPLETED":
        return {"status": "ignored", "reason": f"status was {payment_status}"}

    return {"status": "received", "order_tracking_id": order_tracking_id}


@router.get("/status")
async def billing_status(
    db: Session = Depends(get_db),
    current_staff = Depends(get_current_staff),
):
    """Return the current subscription status for the logged-in business."""
    if not current_staff.business_id:
        raise HTTPException(status_code=400, detail="No business associated")

    subscription = db.query(Subscription).filter(
        Subscription.business_id == current_staff.business_id
    ).first()

    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    return {
        "plan": subscription.plan,
        "monthly_fee": subscription.monthly_fee,
        "status": subscription.status,
        "current_period_start": subscription.current_period_start.isoformat(),
        "current_period_end": subscription.current_period_end.isoformat(),
        "days_remaining": (subscription.current_period_end - now_local()).days,
    }
