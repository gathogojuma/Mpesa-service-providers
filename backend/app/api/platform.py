"""
Platform admin endpoints for the TillTrack operator.

Shows aggregate data about all merchants, subscriptions, and usage.
No customer data is ever exposed here either.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta
from ..database import get_db
from ..models import Business, Staff, Subscription, UsageStat
from ..auth import get_current_staff

router = APIRouter()


def require_admin(current_staff: Staff = Depends(get_current_staff)) -> Staff:
    if current_staff.role != "platform_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform admin access required"
        )
    return current_staff


@router.get("/overview")
async def platform_overview(
    db: Session = Depends(get_db),
    _admin: Staff = Depends(require_admin)
):
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)

    total_businesses = db.query(Business).count()
    active_subscriptions = db.query(Subscription).filter(
        Subscription.status == "active"
    ).count()
    mrr = db.query(func.coalesce(func.sum(Subscription.monthly_fee), 0)).filter(
        Subscription.status == "active"
    ).scalar()

    usage = db.query(
        func.coalesce(func.sum(UsageStat.transaction_count), 0).label("count"),
        func.coalesce(func.sum(UsageStat.total_value), 0).label("value")
    ).filter(UsageStat.stat_date >= thirty_days_ago).first()

    return {
        "total_businesses": total_businesses,
        "active_subscriptions": active_subscriptions,
        "monthly_recurring_revenue": float(mrr or 0),
        "last_30_days_transactions": int(usage.count or 0),
        "last_30_days_value": float(usage.value or 0),
    }


@router.get("/businesses")
async def list_businesses(
    db: Session = Depends(get_db),
    _admin: Staff = Depends(require_admin)
):
    """List every merchant with subscription status and 30-day usage."""
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)
    businesses = db.query(Business).all()
    result = []

    for biz in businesses:
        sub = db.query(Subscription).filter(
            Subscription.business_id == biz.id
        ).first()

        usage = db.query(
            func.coalesce(func.sum(UsageStat.transaction_count), 0).label("count"),
            func.coalesce(func.sum(UsageStat.total_value), 0).label("value")
        ).filter(
            UsageStat.business_id == biz.id,
            UsageStat.stat_date >= thirty_days_ago
        ).first()

        result.append({
            "id": biz.id,
            "name": biz.name,
            "category": biz.category,
            "location_name": biz.location_name,
            "latitude": biz.latitude,
            "longitude": biz.longitude,
            "plan": sub.plan if sub else None,
            "status": sub.status if sub else "no_subscription",
            "monthly_fee": sub.monthly_fee if sub else None,
            "last_30_days_transactions": int(usage.count or 0),
            "last_30_days_value": float(usage.value or 0),
        })

    return result
