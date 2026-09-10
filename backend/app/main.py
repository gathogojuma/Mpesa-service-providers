from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import auth, payments, transactions, manager, reports
from .websocket import websocket_endpoint
from .database import engine, Base, SessionLocal
from .models import Staff, Business
from .auth import get_password_hash

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="TillTrack API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(payments.router, prefix="/api/payments", tags=["payments"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["transactions"])
app.include_router(manager.router, prefix="/api/manager", tags=["manager"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])

# WebSocket endpoint
app.add_websocket_route("/ws", websocket_endpoint)


@app.get("/")
async def root():
    return {"message": "TillTrack API is running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/seed-demo-data")
async def seed_demo_data():
    """Smart seed endpoint that handles existing data."""
    db = SessionLocal()
    try:
        results = {"actions": []}

        # Check/create business
        business = db.query(Business).filter(Business.phone == "+254700000000").first()
        if not business:
            business = Business(name="Demo Bar", phone="+254700000000")
            db.add(business)
            db.commit()
            db.refresh(business)
            results["actions"].append("Created business")
        else:
            results["actions"].append(f"Business already exists: {business.id}")

        # Define users to create
        users_to_create = [
            ("Demo Manager", "+254700000001", "manager"),
            ("Demo Server 1", "+254700000002", "server"),
            ("Demo Server 2", "+254700000003", "server"),
            ("Demo Server 3", "+254700000004", "server"),
        ]

        for name, phone, role in users_to_create:
            existing = db.query(Staff).filter(Staff.phone == phone).first()
            if existing:
                existing.pin_hash = get_password_hash("1234")
                existing.business_id = business.id
                existing.role = role
                existing.name = name
                db.commit()
                results["actions"].append(f"Updated existing user: {phone}")
            else:
                s = Staff(
                    name=name,
                    phone=phone,
                    pin_hash=get_password_hash("1234"),
                    role=role,
                    business_id=business.id
                )
                db.add(s)
                db.commit()
                results["actions"].append(f"Created user: {phone}")

        # Final check
        all_staff = db.query(Staff).all()
        results["total_staff"] = len(all_staff)
        results["staff_list"] = [
            {"id": s.id, "name": s.name, "phone": s.phone, "role": s.role, "business_id": s.business_id}
            for s in all_staff
        ]
        results["business_id"] = business.id
        results["status"] = "success"

        return results
    except Exception as e:
        return {"status": "error", "message": str(e), "type": type(e).__name__}
    finally:
        db.close()
