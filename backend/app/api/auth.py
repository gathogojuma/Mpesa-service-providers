from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..database import get_db
from ..models import Staff, Business
from ..schemas import StaffLogin, StaffRegister, StaffResponse, TokenResponse
from ..auth import verify_password, get_password_hash, create_access_token

router = APIRouter()

@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: StaffLogin,
    db: Session = Depends(get_db)
):
    # Find staff by phone
    staff = db.query(Staff).filter(Staff.phone == credentials.phone).first()
    if not staff or not verify_password(credentials.pin, staff.pin_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone or PIN"
        )

    # Create access token
    access_token = create_access_token(data={"sub": staff.id})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "staff": staff
    }

@router.post("/register", response_model=StaffResponse)
async def register(
    staff_data: StaffRegister,
    db: Session = Depends(get_db)
):
    # Check if business exists
    if staff_data.business_id:
        business = db.query(Business).filter(Business.id == staff_data.business_id).first()
        if not business:
            raise HTTPException(status_code=404, detail="Business not found")
    else:
        # Create new business
        business = Business(
            name=f"{staff_data.name}'s Business",
            phone=staff_data.phone
        )
        db.add(business)
        db.commit()
        db.refresh(business)
        staff_data.business_id = business.id

    # Create staff
    staff = Staff(
        name=staff_data.name,
        phone=staff_data.phone,
        pin_hash=get_password_hash(staff_data.pin),
        role=staff_data.role,
        business_id=staff_data.business_id
    )
    try:
        db.add(staff)
        db.commit()
        db.refresh(staff)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Phone number already registered"
        )
    return staff
