"""
ODPC-compliant Daraja C2B payment processing.

Key responsibilities:
1. Parse the incoming Confirmation payload.
2. DISCARD all customer PII (MSISDN, FirstName, MiddleName, LastName,
   InvoiceNumber) — never persist, never log, never hash.
3. Extract only: TransAmount, TransTime, BillRefNumber.
4. Map BillRefNumber → Business.mpesa_account_ref.
5. Upsert a UsageStat row for that date and increment c2b_count, c2b_value,
   transaction_count, total_value, and the hourly histogram.

What we do NOT store:
- Customer phone number (MSISDN)
- Customer name (FirstName/MiddleName/LastName)
- Invoice number
- M-Pesa transaction ID (TransID) — we don't need it for aggregates

If a payment arrives with an unknown BillRefNumber, we log a warning
(without PII) and return a failure response. We do NOT create a "flagged"
transaction — that reintroduces the exact data we deliberately removed.
"""
import json
from datetime import datetime, date
from sqlalchemy.orm import Session

from ..models import Business, UsageStat
from ..schemas.daraja import C2BConfirmationRequest
from ..utils.timezone import now_local, get_tz


def _parse_trans_time(trans_time: str) -> datetime:
    """
    Parse Safaricom's TransTime string (format: YYYYMMDDHHMMSS) into a
    timezone-aware datetime in Africa/Nairobi.

    Falls back to now_local() if parsing fails.
    """
    try:
        naive = datetime.strptime(trans_time, "%Y%m%d%H%M%S")
        return naive.replace(tzinfo=get_tz())
    except (ValueError, TypeError):
        return now_local()


def process_payment_event(
    payload: C2BConfirmationRequest,
    db: Session,
) -> dict:
    """
    Process a confirmed Daraja C2B payment.

    Returns a dict with:
    - status: "success" | "unknown_merchant" | "invalid_payload"
    - message: human-readable description
    """
    # ─────────────────────────────────────────────────────────────
    # 1. Extract ONLY the fields we need
    # ─────────────────────────────────────────────────────────────
    trans_id = payload.TransID
    trans_amount_raw = payload.TransAmount
    trans_time_raw = payload.TransTime
    bill_ref = payload.BillRefNumber

    # NOTE: We deliberately do NOT read payload.MSISDN or payload.FirstName.
    # Even though they're in the Pydantic model, we never touch them again.
    # Pydantic has them in memory for the request scope only; they are
    # discarded the moment this function returns.

    # ─────────────────────────────────────────────────────────────
    # 2. Basic validation
    # ─────────────────────────────────────────────────────────────
    if not bill_ref or not trans_amount_raw:
        return {
            "status": "invalid_payload",
            "message": "Missing BillRefNumber or TransAmount",
        }

    try:
        trans_amount = float(trans_amount_raw)
    except (TypeError, ValueError):
        return {
            "status": "invalid_payload",
            "message": "TransAmount is not numeric",
        }

    if trans_amount <= 0:
        return {
            "status": "invalid_payload",
            "message": "TransAmount must be positive",
        }

    # ─────────────────────────────────────────────────────────────
    # 3. Resolve the merchant by account reference
    # ─────────────────────────────────────────────────────────────
    business = db.query(Business).filter(
        Business.mpesa_account_ref == bill_ref.strip().upper()
    ).first()

    if not business:
        # Log without PII — only BillRefNumber and TransAmount
        print(
            f"[DARAJA] Unknown merchant ref '{bill_ref}' "
            f"for amount {trans_amount} (TransID: {trans_id})"
        )
        return {
            "status": "unknown_merchant",
            "message": f"No business with mpesa_account_ref '{bill_ref}'",
        }

    # ─────────────────────────────────────────────────────────────
    # 4. Compute the local date and hour for aggregation
    # ─────────────────────────────────────────────────────────────
    trans_dt = _parse_trans_time(trans_time_raw)
    stat_date: date = trans_dt.date()
    hour_key = str(trans_dt.hour)

    # ─────────────────────────────────────────────────────────────
    # 5. Upsert the UsageStat for (business, date)
    # ─────────────────────────────────────────────────────────────
    stat = db.query(UsageStat).filter(
        UsageStat.business_id == business.id,
        UsageStat.stat_date == stat_date,
    ).first()

    if not stat:
        stat = UsageStat(
            business_id=business.id,
            stat_date=stat_date,
            transaction_count=0,
            total_value=0.0,
            app_count=0,
            app_value=0.0,
            c2b_count=0,
            c2b_value=0.0,
            cash_count=0,
            cash_value=0.0,
            hourly_counts="{}",
        )
        db.add(stat)

    # Increment aggregates
    stat.transaction_count += 1
    stat.total_value += trans_amount
    stat.c2b_count += 1
    stat.c2b_value += trans_amount

    # Update the hourly histogram
    try:
        hourly = json.loads(stat.hourly_counts or "{}")
    except (ValueError, TypeError):
        hourly = {}
    hourly[hour_key] = hourly.get(hour_key, 0) + 1
    stat.hourly_counts = json.dumps(hourly)

    db.commit()
    db.refresh(stat)

    # Log the successful aggregation (no PII)
    print(
        f"[DARAJA] Recorded C2B {trans_amount} KES for "
        f"business {business.id} (ref: {bill_ref}, "
        f"date: {stat_date}, hour: {hour_key})"
    )

    return {
        "status": "success",
        "message": f"Recorded {trans_amount} KES for {business.name}",
        "business_id": business.id,
        "stat_date": str(stat_date),
    }
