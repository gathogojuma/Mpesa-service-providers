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
# Business (used by platform admin endpoints)
# ─────────────────────────────────────────────

class BusinessResponse(BaseModel):
    id: str
    name: str
    phone: str
    mpesa_till: Optional[str]
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
# Webhook payloads
# ─────────────────────────────────────────────

class MpesaCallbackPayload(BaseModel):
    """
    Loosely-typed incoming M-Pesa callback.

    We only read a handful of fields; the rest are ignored.
    """
    BusinessShortCode: Optional[str] = None
    TillNumber: Optional[str] = None
    ShortCode: Optional[str] = None
    TransAmount: Optional[float] = None
    Amount: Optional[float] = None
    TransID: Optional[str] = None
    TransactionType: Optional[str] = None
    TransTime: Optional[str] = None
