from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid
from ..models import Transaction, ReconciliationLog, TransactionStatus

class ReconciliationService:
    async def auto_reconcile(self, transaction_id: str, db: Session):
        """Auto-reconcile a transaction"""
        transaction = db.query(Transaction).filter(
            Transaction.id == transaction_id
        ).first()

        if not transaction:
            return {"status": "error", "message": "Transaction not found"}

        if transaction.status != TransactionStatus.CONFIRMED:
            return {"status": "skipped", "message": "Transaction not confirmed"}

        # Check if already reconciled
        existing = db.query(ReconciliationLog).filter(
            ReconciliationLog.transaction_id == transaction_id
        ).first()

        if existing:
            return {"status": "already_reconciled"}

        # Create reconciliation log
        log = ReconciliationLog(
            id=str(uuid.uuid4()),
            transaction_id=transaction.id,
            matched_by="auto",
            notes=f"Auto-reconciled on confirmation"
        )
        db.add(log)
        db.commit()

        return {"status": "reconciled"}

    async def match_pending_transaction(self, amount: float, phone: str, db: Session):
        """Match an incoming payment to a pending transaction"""
        # Look for pending transactions in the last 5 minutes
        time_window = datetime.utcnow() - timedelta(minutes=5)
        candidates = db.query(Transaction).filter(
            Transaction.status == TransactionStatus.PENDING,
            Transaction.amount == amount,
            Transaction.customer_phone == phone,
            Transaction.initiated_at >= time_window
        ).order_by(Transaction.initiated_at.desc()).all()

        if candidates:
            return candidates[0]

        # Try matching by amount only (more forgiving)
        candidates = db.query(Transaction).filter(
            Transaction.status == TransactionStatus.PENDING,
            Transaction.amount == amount,
            Transaction.initiated_at >= time_window
        ).order_by(Transaction.initiated_at.desc()).all()

        if candidates:
            return candidates[0]

        return None
