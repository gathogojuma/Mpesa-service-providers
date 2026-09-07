from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from ..database import get_db
from ..models import Transaction, Staff, TransactionStatus, ReconciliationLog
from ..schemas import DashboardResponse, ReconcileRequest
from ..auth import get_current_staff
from ..services.reconciliation import ReconciliationService

router = APIRouter()

@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    db: Session = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff)
):
    if current_staff.role != "manager":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers can access dashboard"
        )

    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)

    # Daily transactions
    daily_tx = db.query(Transaction).filter(
        Transaction.business_id == current_staff.business_id,
        Transaction.initiated_at >= today,
        Transaction.initiated_at < tomorrow
    )

    # Revenue
    confirmed = daily_tx.filter(Transaction.status == TransactionStatus.CONFIRMED)
    total_revenue = confirmed.with_entities(func.sum(Transaction.amount)).scalar() or 0
    total_count = daily_tx.count()
    pending_count = daily_tx.filter(Transaction.status == TransactionStatus.PENDING).count()
    flagged_count = daily_tx.filter(Transaction.status == TransactionStatus.FLAGGED).count()

    # Server stats
    staff_stats = db.query(
        Staff.id,
        Staff.name,
        func.count(Transaction.id).label("transaction_count"),
        func.sum(Transaction.amount).label("total_sales")
    ).outerjoin(
        Transaction,
        (Transaction.staff_id == Staff.id) &
        (Transaction.status == TransactionStatus.CONFIRMED) &
        (Transaction.confirmed_at >= today) &
        (Transaction.confirmed_at < tomorrow)
    ).filter(Staff.business_id == current_staff.business_id).group_by(Staff.id).all()

    server_stats = [
        {
            "id": s.id,
            "name": s.name,
            "transaction_count": s.transaction_count or 0,
            "total_sales": s.total_sales or 0.0
        }
        for s in staff_stats
    ]

    # Flagged transactions
    flagged_tx = db.query(Transaction).filter(
        Transaction.business_id == current_staff.business_id,
        Transaction.status == TransactionStatus.FLAGGED
    ).order_by(Transaction.initiated_at.desc()).limit(20).all()

    flagged_list = []
    for t in flagged_tx:
        flagged_list.append({
            "id": t.id,
            "staff_name": t.staff.name if t.staff else "Unknown",
            "amount": t.amount,
            "failure_reason": "No matching staff found",
            "initiated_at": t.initiated_at
        })

    return {
        "total_revenue_today": total_revenue,
        "total_transactions_today": total_count,
        "pending_count": pending_count,
        "flagged_count": flagged_count,
        "server_stats": server_stats,
        "flagged_transactions": flagged_list
    }

@router.post("/reconcile")
async def manual_reconcile(
    request: ReconcileRequest,
    db: Session = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff)
):
    if current_staff.role != "manager":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers can reconcile"
        )

    transaction = db.query(Transaction).filter(
        Transaction.id == request.transaction_id,
        Transaction.business_id == current_staff.business_id
    ).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Update transaction status
    transaction.status = TransactionStatus.CONFIRMED
    transaction.confirmed_at = datetime.utcnow()
    db.commit()

    # Create reconciliation log
    log = ReconciliationLog(
        transaction_id=transaction.id,
        matched_by="manual",
        manager_id=current_staff.id,
        notes=request.notes or "Manually reconciled by manager"
    )
    db.add(log)
    db.commit()

    return {"status": "reconciled", "transaction_id": transaction.id}
