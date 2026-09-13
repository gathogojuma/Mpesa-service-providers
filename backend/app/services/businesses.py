"""
Business onboarding service.

Handles the creation of a new Business along with:
- Its first manager account
- An initial subscription

Used by the /api/businesses/register endpoint and any future
admin-side onboarding tools.
"""
from datetime import timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..models import Business, Staff, Subscription
from ..auth import get_password_hash
from ..utils.timezone import now_local


def create_business_with_manager(
    db: Session,
    business_name: str,
    business_phone: str,
    mpesa_till: str,
    category: str,
    location_name: str,
    latitude: float,
    longitude: float,
    manager_name: str,
    manager_phone: str,
    manager_pin: str,
    plan: str = "starter",
    monthly_fee: float = 2500.0,
    transaction_limit: int = 2000,
) -> dict:
    """
    Create a Business, its Subscription, and its first Manager in one transaction.

    Returns a dict with:
      - business: the created Business
      - manager:  the created Staff record
      - subscription: the created Subscription

    Raises:
      ValueError: if business_name, mpesa_till, or manager_phone is invalid/duplicate
    """
    # Basic validation
    if not business_name or not business_name.strip():
        raise ValueError("Business name is required")

    if not mpesa_till or not mpesa_till.strip():
        raise ValueError("M-Pesa Till number is required")

    if not manager_phone or not manager_phone.strip():
        raise ValueError("Manager phone number is required")

    # Check for duplicates
    if db.query(Business).filter(Business.mpesa_till == mpesa_till).first():
        raise ValueError(f"A business with Till {mpesa_till} already exists")

    if db.query(Staff).filter(Staff.phone == manager_phone).first():
        raise ValueError(f"A user with phone {manager_phone} already exists")

    # ─── Create Business ──────────────────────────────────
    business = Business(
        name=business_name.strip(),
        phone=business_phone.strip() if business_phone else manager_phone.strip(),
        mpesa_till=mpesa_till.strip(),
        category=category.strip() if category else None,
        location_name=location_name.strip() if location_name else None,
        latitude=latitude,
        longitude=longitude,
    )
    db.add(business)
    db.flush()  # get the ID without committing

    # ─── Create Subscription ──────────────────────────────
    period_start = now_local().replace(hour=0, minute=0, second=0, microsecond=0)
    period_end = period_start + timedelta(days=30)

    subscription = Subscription(
        business_id=business.id,
        plan=plan,
        monthly_fee=monthly_fee,
        transaction_limit=transaction_limit,
        status="trial",  # New businesses start on trial
        current_period_start=period_start,
        current_period_end=period_end,
    )
    db.add(subscription)

    # ─── Create Manager Account ───────────────────────────
    manager = Staff(
        name=manager_name.strip(),
        phone=manager_phone.strip(),
        pin_hash=get_password_hash(manager_pin),
        role="manager",
        business_id=business.id,
    )
    db.add(manager)

    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Database constraint error: {str(e)[:100]}")

    db.refresh(business)
    db.refresh(subscription)
    db.refresh(manager)

    return {
        "business": business,
        "manager": manager,
        "subscription": subscription,
    }
