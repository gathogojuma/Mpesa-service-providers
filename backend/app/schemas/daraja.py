"""
Pydantic schemas for Safaricom Daraja C2B (Customer-to-Business) callbacks.

Safaricom sends two callbacks to our URLs for every C2B payment:
1. Validation — sent BEFORE the payment is accepted. We respond with
   Accept or Reject. (Optional but recommended for Paybill fraud control.)
2. Confirmation — sent AFTER the payment is processed. We record the
   aggregate into UsageStat.

Docs: https://developer.safaricom.co.ke/Documentation

IMPORTANT ODPC NOTE:
These schemas will receive customer PII (MSISDN, FirstName).
They MUST NOT be persisted anywhere. The service layer discards them
immediately. These schemas exist only to validate the incoming shape.
"""
from pydantic import BaseModel, Field
from typing import Optional


class C2BValidationRequest(BaseModel):
    """
    Sent by Safaricom to our Validation URL before accepting a C2B payment.

    All fields are marked Optional because Safaricom sometimes omits fields
    in Sandbox. Real production payloads include all fields.
    """
    TransactionType: Optional[str] = None      # e.g. "Pay Bill"
    TransID: Optional[str] = None              # e.g. "RKTQDM7W6S"
    TransTime: Optional[str] = None            # e.g. "20191122063845"
    TransAmount: Optional[str] = None          # e.g. "10" (string, not float)
    BusinessShortCode: Optional[str] = None    # Our Paybill number
    BillRefNumber: Optional[str] = None        # The merchant's account ref (e.g. "TT0001")
    InvoiceNumber: Optional[str] = None
    OrgAccountBalance: Optional[str] = None
    ThirdPartyTransID: Optional[str] = None
    MSISDN: Optional[str] = None               # Customer phone — MUST NOT be persisted
    FirstName: Optional[str] = None            # Customer name — MUST NOT be persisted
    MiddleName: Optional[str] = None
    LastName: Optional[str] = None

    class Config:
        extra = "allow"  # Tolerate extra fields Safaricom may send


class C2BConfirmationRequest(BaseModel):
    """
    Sent by Safaricom to our Confirmation URL after a C2B payment succeeds.

    Same shape as Validation, but arrives only on success.
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
    MSISDN: Optional[str] = None               # Customer phone — MUST NOT be persisted
    FirstName: Optional[str] = None            # Customer name — MUST NOT be persisted
    MiddleName: Optional[str] = None
    LastName: Optional[str] = None

    class Config:
        extra = "allow"


class C2BResponse(BaseModel):
    """
    The response format Safaricom expects from both endpoints.
    ResultCode 0 = Accepted, anything else = Rejected.
    """
    ResultCode: int
    ResultDesc: str
