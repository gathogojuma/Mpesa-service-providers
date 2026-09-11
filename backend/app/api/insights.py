"""
Merchant-facing insights.

Merchants see their own aggregated data: peak hours, daily counts,
monthly totals. No customer-level information is exposed.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import date, timedelta
from ..database import get_db
from ..models import UsageStat, Staff, Subscription
from ..auth import get_current_staff

router = APIRouter()


@router.get("/my-business/summary")
async def business_summary(
    db: Session = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff)
):
    """Overview metrics for the current merchant."""
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)

    stats = db.query(
        func.coalesce(func.sum(UsageStat.transaction_count), 0).label("total_count"),
        func.coalesce(func.sum(UsageStat.total_value), 0).label("total_value")
    ).filter(
        UsageStat.business_id == current_staff.business_id,
        UsageStat.stat_date >= thirty_days_ago
    ).first()

    sub = db.query(Subscription).filter(
        Subscription.business_id == current_staff.business_id
    ).first()

    return {
        "last_30_days_transactions": int(stats.total_count or 0),
        "last_30_days_value": float(stats.total_value or 0),
        "plan": sub.plan if sub else None,
        "monthly_fee": sub.monthly_fee if sub else None,
        "status": sub.status if sub else None,
    }


@router.get("/my-business/peak-hours")
async def peak_hours(
    db: Session = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff)
):
    """
    Return hourly transaction distribution across the last 30 days,
    so merchants can see their peak hours.
    """
    import json
    from collections import Counter

    today = date.today()
    thirty_days_ago = today - timedelta(days=30)

    rows = db.query(UsageStat).filter(
        UsageStat.business_id == current_staff.business_id,
        UsageStat.stat_date >= thirty_days_ago
    ).all()

    combined = Counter()
    for row in rows:
        try:
            hourly = json.loads(row.hourly_counts or "{}")
            for hour_str, count in hourly.items():
                combined[int(hour_str)] += count
        except (ValueError, TypeError):
            continue

    # Ensure all 24 hours are represented
    return {
        "hours": [
            {"hour": h, "count": combined.get(h, 0)}
            for h in range(24)
        ],
        "peak_hour": max(combined, key=combined.get) if combined else None
    }


@router.get("/my-business/daily-trend")
async def daily_trend(
    days: int = 30,
    db: Session = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff)
):
    """Return daily transaction counts for the last N days."""
    today = date.today()
    start = today - timedelta(days=days)

    rows = db.query(UsageStat).filter(
        UsageStat.business_id == current_staff.business_id,
        UsageStat.stat_date >= start
    ).order_by(UsageStat.stat_date).all()

    return {
        "days": [
            {
                "date": row.stat_date.isoformat(),
                "count": row.transaction_count,
                "value": row.total_value,
            }
            for row in rows
        ]
    }
