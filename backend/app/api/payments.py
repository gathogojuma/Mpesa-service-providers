from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
import uuid
from ..database import get_db
from ..models import Transaction, Staff, TransactionStatus, Business
from ..schemas import PaymentInitiate, TransactionResponse
from ..auth import get_current_staff
from ..services.mpesa import MpesaService
from ..services.reconciliation import ReconciliationService
from ..websocket import manager as websocket_manager

router = APIRouter()
mpesa_service = MpesaService()
reconciliation_service = ReconciliationService()

@router.post("/initiate", response_model=TransactionResponse)
async def initiate_payment(
    payment: PaymentInitiate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff)
):
    # Create pending transaction
    transaction_id = str(uuid.uuid4())
    transaction = Transaction(
        id=transaction_id,
        staff_id=current_staff.id,
        business_id=current_staff.business_id,
        amount=payment.amount,
        customer_phone=payment.customer_phone,
        status=TransactionStatus.PENDING,
        table_number=payment.table_number
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    # Initiate M-Pesa payment
    try:
        mpesa_response = await mpesa_service.stk_push(
            phone_number=payment.customer_phone,
            amount=payment.amount,
            transaction_id=transaction_id
        )
    except Exception as e:
        transaction.status = TransactionStatus.FAILED
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"M-Pesa initiation failed: {str(e)}"
        )

    # Process payment in background (mock mode)
    if mpesa_service.is_mock:
        background_tasks.add_task(
            mpesa_service.simulate_approval,
            transaction_id
        )

    return transaction

@router.post("/callback")
async def mpesa_callback(data: dict, db: Session = Depends(get_db)):
    """M-Pesa webhook callback"""
    # Parse callback data
    transaction_id = data.get("transaction_id")
    amount = data.get("amount")
    phone = data.get("phone")
    mpesa_transaction_id = data.get("mpesa_transaction_id")
    status = data.get("status")

    # Find pending transaction
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.status == TransactionStatus.PENDING
    ).first()

    if not transaction:
        # If no pending transaction found, create flagged transaction
        transaction = Transaction(
            id=str(uuid.uuid4()),
            staff_id=None,
            business_id=None,
            amount=amount or 0,
            customer_phone=phone or "unknown",
            status=TransactionStatus.FLAGGED,
            mpesa_transaction_id=mpesa_transaction_id
        )
        db.add(transaction)
        db.commit()
        await websocket_manager.broadcast(
            "new_flagged_transaction",
            {"transaction_id": transaction.id}
        )
        return {"status": "flagged"}

    # Update transaction
    transaction.status = TransactionStatus.CONFIRMED
    transaction.mpesa_transaction_id = mpesa_transaction_id
    transaction.confirmed_at = datetime.utcnow()
    db.commit()

    # Auto-reconcile
    await reconciliation_service.auto_reconcile(transaction.id, db)

    # Notify via WebSocket
    await websocket_manager.broadcast(
        "payment_confirmed",
        {"transaction_id": transaction.id}
    )

    return {"status": "confirmed"}

@router.post("/simulate-approve/{transaction_id}")
async def simulate_approval(
    transaction_id: str,
    db: Session = Depends(get_db)
):
    """Mock approval for testing"""
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.status == TransactionStatus.PENDING
    ).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found or already processed")

    transaction.status = TransactionStatus.CONFIRMED
    transaction.mpesa_transaction_id = f"SIM{transaction_id[:8]}"
    transaction.confirmed_at = datetime.utcnow()
    db.commit()

    await reconciliation_service.auto_reconcile(transaction_id, db)

    await websocket_manager.broadcast(
        "payment_confirmed",
        {"transaction_id": transaction_id}
    )

    return {"status": "confirmed"}
