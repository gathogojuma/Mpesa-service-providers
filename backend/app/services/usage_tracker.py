"""
Usage tracking service.

Instead of storing individual transactions, we update a single
UsageStat row per business per day. This gives us:
- Transaction counts (for tiered pricing)
- Total value (for insights)
- Hourly distribution (for peak-hour analysis)

without retaining any customer-level data.
"""
import json
from datetime import date, datetime
from sqlalchemy.orm import Session
from ..models import UsageStat, Business
from ..utils.timezone import now_local


def record_payment_event(db: Session, business_id: str, amount: float, server_id: str = None):
    """
    Called when a payment is successfully received for a business.

    Updates (or creates) the UsageStat row for today. Does NOT store
    the transaction itself.
    """
    today = now_local().date()
    current_hour = now_local().hour

    stat = db.query(UsageStat).filter(
        UsageStat.business_id == business_id,
        UsageStat.stat_date == today
    ).first()

    if not stat:
        stat = UsageStat(
            business_id=business_id,
            stat_date=today,
            transaction_count=0,
            total_value=0.0,
            unique_servers=0,
            hourly_counts="{}"
        )
        db.add(stat)

    # Update totals
    stat.transaction_count += 1
    stat.total_value += amount

    # Update hourly histogram
    try:
        hourly = json.loads(stat.hourly_counts or "{}")
    except (ValueError, TypeError):
        hourly = {}
    key = str(current_hour)
    hourly[key] = hourly.get(key, 0) + 1
    stat.hourly_counts = json.dumps(hourly)

    db.commit()
    return stat


def get_monthly_transaction_count(db: Session, business_id: str, year: int, month: int) -> int:
    """
    Return the total transactions for a business in a given month.
    Used for tiered pricing decisions.
    """
    from sqlalchemy import func, extract

    total = db.query(func.coalesce(func.sum(UsageStat.transaction_count), 0)).filter(
        UsageStat.business_id == business_id,
        extract("year", UsageStat.stat_date) == year,
        extract("month", UsageStat.stat_date) == month
    ).scalar()

    return int(total or 0)
