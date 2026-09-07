from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from .models import TransactionStatus

class StaffLogin(BaseModel):
    phone: str
    pin: str

class StaffRegister(BaseModel):
    name: str
    phone: str
    pin: str
    role: str
    business_id: Optional[str] = None

class StaffResponse(BaseModel):
    id: str
    name: str
    phone: str
    role: str
    business_id: str
    created_at: datetime

class PaymentInitiate(BaseModel):
    amount: float
    customer_phone: str
    table_number: Optional[str] = None

class TransactionResponse(BaseModel):
    id: str
    staff_id: str
    business_id: str
    mpesa_transaction_id: Optional[str]
    amount: float
    customer_phone: str
    status: TransactionStatus
    initiated_at: datetime
    confirmed_at: Optional[datetime]
    table_number: Optional[str]
    staff_name: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    staff: StaffResponse

class DashboardResponse(BaseModel):
    total_revenue_today: float
    total_transactions_today: int
    pending_count: int
    flagged_count: int
    server_stats: List[dict]
    flagged_transactions: List[dict]

class ReconcileRequest(BaseModel):
    transaction_id: str
    notes: Optional[str] = None
