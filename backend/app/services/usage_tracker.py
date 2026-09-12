"""
Usage tracking service.

Instead of storing individual transactions, we update a single
UsageStat row per business per day. This gives us:
- Transaction counts (for tiered pricing)
- Total value (for insights)
- Hourly distribution (for peak-hour analysis)
- Channel breakdown (app vs C2B vs cash)

without retaining any customer-level data.
"""
import json
from datetime import date
from sqlalchemy.orm import Session
from ..models import UsageStat
from ..utils.timezone import now_local


# Valid sources for a payment event
VALID_SOURCES = {"app", "c2b", "cash"}


def record_payment_event(
    db: Session,
    business_id: str,
    amount: float,
    source: str = "app",
) -> UsageStat:
    """
    Record a payment event into today's usage aggregate.

    Args:
        db: SQLAlchemy session
        business_id: UUID of the business receiving the payment
        amount: Transaction amount in KES
        source: 'app' (STK Push from our app), 'c2b' (direct to Till),
                or 'cash' (manually logged)

    Returns:
        The updated UsageStat row.

    Idempotent per (business, day): always updates the same row.
    """
    if source not in VALID_SOURCES:
        source = "app"

    today = now_local().date()
    current_hour = now_local().hour

    stat = db.query(UsageStat).filter(
        UsageStat.business_id == business_id,
        UsageStat.stat_date == today,
    ).first()

    if not stat:
        stat = UsageStat(
            business_id=business_id,
            stat_date=today,
            transaction_count=0,
            total_value=0.0,
            app_count=0, app_value=0.0,
            c2b_count=0, c2b_value=0.0,
            cash_count=0, cash_value=0.0,
            hourly_counts="{}",
        )
        db.add(stat)

    # Update totals
    stat.transaction_count += 1
    stat.total_value += amount

    # Update source-specific breakdown
    if source == "app":
        stat.app_count += 1
        stat.app_value += amount
    elif source == "c2b":
        stat.c2b_count += 1
        stat.c2b_value += amount
    elif source == "cash":
        stat.cash_count += 1
        stat.cash_value += amount

    # Update hourly histogram
    try:
        hourly = json.loads(stat.hourly_counts or "{}")
    except (ValueError, TypeError):
        hourly = {}
    key = str(current_hour)
    hourly[key] = hourly.get(key, 0) + 1
    stat.hourly_counts = json.dumps(hourly)

    db.commit()
    db.refresh(stat)
    return stat


def get_monthly_transaction_count(
    db: Session, business_id: str, year: int, month: int
) -> int:
    """
    Return the total transactions for a business in a given month.
    Used for tiered pricing decisions.
    """
    from sqlalchemy import func, extract

    total = db.query(
        func.coalesce(func.sum(UsageStat.transaction_count), 0)
    ).filter(
        UsageStat.business_id == business_id,
        extract("year", UsageStat.stat_date) == year,
        extract("month", UsageStat.stat_date) == month,
    ).scalar()

    return int(total or 0)
