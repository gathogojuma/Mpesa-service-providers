from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import csv
from io import StringIO
from fastapi.responses import StreamingResponse
from ..database import get_db
from ..models import Transaction, Staff, TransactionStatus
from ..auth import get_current_staff

router = APIRouter()

@router.get("/shift")
async def export_shift_report(
    db: Session = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff)
):
    if current_staff.role != "manager":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers can export reports"
        )

    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)

    transactions = db.query(Transaction).filter(
        Transaction.business_id == current_staff.business_id,
        Transaction.initiated_at >= today,
        Transaction.initiated_at < tomorrow
    ).order_by(Transaction.initiated_at).all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Staff", "Amount", "Status", "Customer", "Table", "Time"])

    for t in transactions:
        writer.writerow([
            t.id[:8],
            t.staff.name if t.staff else "Unknown",
            t.amount,
            t.status.value,
            t.customer_phone,
            t.table_number or "-",
            t.initiated_at.strftime("%H:%M")
        ])

    response = StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=shift_report_{today.date()}.csv"}
    )
    return response
