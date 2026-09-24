from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


# ─────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────

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
    business_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    staff: StaffResponse


# ─────────────────────────────────────────────
# Business
# ─────────────────────────────────────────────

class BusinessResponse(BaseModel):
    id: str
    name: str
    phone: str
    mpesa_till: Optional[str]
    mpesa_account_ref: Optional[str] = None
    category: Optional[str]
    location_name: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# Subscription
# ─────────────────────────────────────────────

class SubscriptionResponse(BaseModel):
    id: str
    business_id: str
    plan: str
    monthly_fee: float
    transaction_limit: Optional[int]
    status: str
    current_period_start: datetime
    current_period_end: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# Insights
# ─────────────────────────────────────────────

class PeakHour(BaseModel):
    hour: int
    count: int


class DailyTrendPoint(BaseModel):
    date: str
    count: int
    value: float


# ─────────────────────────────────────────────
# M-Pesa Legacy (kept for backward compatibility)
# ─────────────────────────────────────────────

class MpesaCallbackPayload(BaseModel):
    """
    Loosely-typed incoming M-Pesa callback (legacy STK Push).
    """
    BusinessShortCode: Optional[str] = None
    TillNumber: Optional[str] = None
    ShortCode: Optional[str] = None
    TransAmount: Optional[float] = None
    Amount: Optional[float] = None
    TransID: Optional[str] = None
    TransactionType: Optional[str] = None
    TransTime: Optional[str] = None


# ─────────────────────────────────────────────
# Daraja C2B (Customer-to-Business) Webhooks
# ─────────────────────────────────────────────

class C2BValidationRequest(BaseModel):
    """
    Sent by Safaricom to our Validation URL before accepting a C2B payment.

    All fields are Optional because Safaricom sometimes omits fields
    in Sandbox. Real production payloads include all fields.

    NOTE: MSISDN, FirstName, etc. are received but MUST NOT be persisted.
    """
    TransactionType: Optional[str] = None
    TransID: Optional[str] = None
    TransTime: Optional[str] = None
    TransAmount: Optional[str] = None
    BusinessShortCode: Optional[str] = None
    BillRefNumber: Optional[str] = None
    InvoiceNumber: Optional[str] = None
    OrgAccountBalance: Optional[str] = None
    ThirdPartyTransID: Optional[str] = None
    MSISDN: Optional[str] = None
    FirstName: Optional[str] = None
    MiddleName: Optional[str] = None
    LastName: Optional[str] = None

    class Config:
        extra = "allow"


class C2BConfirmationRequest(BaseModel):
    """
    Sent by Safaricom to our Confirmation URL after a C2B payment succeeds.
    """
    TransactionType: Optional[str] = None
    TransID: Optional[str] = None
    TransTime: Optional[str] = None
    TransAmount: Optional[str] = None
    BusinessShortCode: Optional[str] = None
    BillRefNumber: Optional[str] = None
    InvoiceNumber: Optional[str] = None
    OrgAccountBalance: Optional[str] = None
    ThirdPartyTransID: Optional[str] = None
    MSISDN: Optional[str] = None
    FirstName: Optional[str] = None
    MiddleName: Optional[str] = None
    LastName: Optional[str] = None

    class Config:
        extra = "allow"


class C2BResponse(BaseModel):
    """
    Response format Safaricom expects from both C2B endpoints.
    ResultCode 0 = Accepted, anything else = Rejected.
    """
    ResultCode: int
    ResultDesc: str
