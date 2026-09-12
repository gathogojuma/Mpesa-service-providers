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
    """
    Authenticate a staff member and issue a JWT containing tenant context.

    `business_id` is derived from the Staff record in the DB.
    Platform admins have no business_id (they operate cross-tenant).
    """
    staff = db.query(Staff).filter(Staff.phone == credentials.phone).first()
    if not staff or not verify_password(credentials.pin, staff.pin_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone or PIN"
        )

    access_token = create_access_token(
        data={"sub": staff.id, "role": staff.role},
        business_id=staff.business_id,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "staff": staff,
    }


@router.post("/register", response_model=StaffResponse)
async def register(
    staff_data: StaffRegister,
    db: Session = Depends(get_db)
):
    """
    Register a new staff member.

    If no business_id is provided and the role is 'manager', a new
    Business is created automatically (useful for onboarding a tenant).
    """
    if staff_data.business_id:
        business = db.query(Business).filter(
            Business.id == staff_data.business_id
        ).first()
        if not business:
            raise HTTPException(status_code=404, detail="Business not found")
    elif staff_data.role == "manager":
        # Only managers can create a business on signup
        business = Business(
            name=f"{staff_data.name}'s Business",
            phone=staff_data.phone,
            mpesa_till=f"TEMP-{staff_data.phone[-6:]}",  # placeholder; update later
        )
        db.add(business)
        db.commit()
        db.refresh(business)
        staff_data.business_id = business.id
    else:
        raise HTTPException(
            status_code=400,
            detail="business_id is required for non-manager roles"
        )

    staff = Staff(
        name=staff_data.name,
        phone=staff_data.phone,
        pin_hash=get_password_hash(staff_data.pin),
        role=staff_data.role,
        business_id=staff_data.business_id,
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
