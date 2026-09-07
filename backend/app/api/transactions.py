from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from ..database import get_db
from ..models import Transaction, Staff, TransactionStatus
from ..schemas import TransactionResponse
from ..auth import get_current_staff

router = APIRouter()

@router.get("/my-sales")
async def get_my_sales(
    db: Session = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff)
):
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)

    sales = db.query(Transaction).filter(
        Transaction.staff_id == current_staff.id,
        Transaction.status == TransactionStatus.CONFIRMED,
        Transaction.confirmed_at >= today,
        Transaction.confirmed_at < tomorrow
    )

    total_amount = sales.with_entities(func.sum(Transaction.amount)).scalar() or 0
    count = sales.count()

    return {
        "staff_name": current_staff.name,
        "total_sales_today": total_amount,
        "transaction_count": count,
        "transactions": sales.all()
    }

@router.get("/", response_model=list[TransactionResponse])
async def get_transactions(
    staff_id: str = None,
    status: TransactionStatus = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff)
):
    query = db.query(Transaction)

    if current_staff.role != "manager":
        query = query.filter(Transaction.staff_id == current_staff.id)

    if staff_id:
        query = query.filter(Transaction.staff_id == staff_id)
    if status:
        query = query.filter(Transaction.status == status)

    transactions = query.order_by(Transaction.initiated_at.desc()).limit(limit).all()

    # Add staff names
    for t in transactions:
        if t.staff:
            t.staff_name = t.staff.name

    return transactions
