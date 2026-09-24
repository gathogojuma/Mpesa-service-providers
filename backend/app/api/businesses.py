"""
Business onboarding endpoints.

Allows a new business owner to register:
- Their business (name, M-Pesa Till, location)
- Their subscription (starter plan, free trial)
- Their first manager account (phone + PIN)
- Auto-generated mpesa_account_ref (e.g., TT0001)

Publicly accessible (no auth required).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..database import get_db
from ..services.businesses import create_business_with_manager

router = APIRouter()


# ─────────────────────────────────────────────────────────────
# Request / Response Schemas
# ─────────────────────────────────────────────────────────────

class BusinessRegisterRequest(BaseModel):
    # Business details
    business_name: str = Field(..., min_length=2, max_length=100)
    business_phone: str = Field(..., min_length=10, max_length=20)
    mpesa_till: str = Field(..., min_length=4, max_length=20)
    category: str = Field("bar", description="bar, club, supermarket, etc.")
    location_name: str = Field("", max_length=100)
    latitude: float = Field(0.0)
    longitude: float = Field(0.0)

    # Manager account details
    manager_name: str = Field(..., min_length=2, max_length=100)
    manager_phone: str = Field(..., min_length=10, max_length=20)
    manager_pin: str = Field(..., min_length=4, max_length=10)


class BusinessRegisterResponse(BaseModel):
    status: str
    message: str
    business_id: str
    business_name: str
    mpesa_account_ref: str
    manager_phone: str
    plan: str
    monthly_fee: float
    trial_ends: str


# ─────────────────────────────────────────────────────────────
# Endpoint
# ─────────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=BusinessRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_business(
    payload: BusinessRegisterRequest,
    db: Session = Depends(get_db),
):
    """
    Register a new business with a manager account and starter subscription.

    A short mpesa_account_ref (e.g., TT0001) is auto-generated. This is the
    code customers will type when paying the business via Paybill.
    """
    try:
        result = create_business_with_manager(
            db=db,
            business_name=payload.business_name,
            business_phone=payload.business_phone,
            mpesa_till=payload.mpesa_till,
            category=payload.category,
            location_name=payload.location_name,
            latitude=payload.latitude,
            longitude=payload.longitude,
            manager_name=payload.manager_name,
            manager_phone=payload.manager_phone,
            manager_pin=payload.manager_pin,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "status": "success",
        "message": f"Business registered. Your payment code is {result['account_ref']}.",
        "business_id": result["business"].id,
        "business_name": result["business"].name,
        "mpesa_account_ref": result["account_ref"],
        "manager_phone": result["manager"].phone,
        "plan": result["subscription"].plan,
        "monthly_fee": result["subscription"].monthly_fee,
        "trial_ends": result["subscription"].current_period_end.isoformat(),
    }
