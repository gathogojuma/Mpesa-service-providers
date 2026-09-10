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
    """One-time endpoint to seed the demo data. Visit this URL once to create users."""
    db = SessionLocal()
    try:
        # Check if we already have data
        existing = db.query(Staff).count()
        if existing > 0:
            return {
                "status": "already_seeded",
                "message": f"Database already has {existing} staff members",
                "users": [
                    {"phone": s.phone, "role": s.role, "name": s.name}
                    for s in db.query(Staff).all()
                ]
            }

        # Create business
        business = Business(name="Demo Bar", phone="+254700000000")
        db.add(business)
        db.commit()
        db.refresh(business)

        # Create manager
        manager = Staff(
            name="Demo Manager",
            phone="+254700000001",
            pin_hash=get_password_hash("1234"),
            role="manager",
            business_id=business.id
        )
        db.add(manager)

        # Create servers
        servers = [
            ("Demo Server 1", "+254700000002"),
            ("Demo Server 2", "+254700000003"),
            ("Demo Server 3", "+254700000004"),
        ]
        for name, phone in servers:
            s = Staff(
                name=name,
                phone=phone,
                pin_hash=get_password_hash("1234"),
                role="server",
                business_id=business.id
            )
            db.add(s)

        db.commit()

        return {
            "status": "success",
            "message": "Demo data created successfully!",
            "business_id": business.id,
            "users": [
                {"phone": "+254700000001", "pin": "1234", "role": "manager", "name": "Demo Manager"},
                {"phone": "+254700000002", "pin": "1234", "role": "server", "name": "Demo Server 1"},
                {"phone": "+254700000003", "pin": "1234", "role": "server", "name": "Demo Server 2"},
                {"phone": "+254700000004", "pin": "1234", "role": "server", "name": "Demo Server 3"},
            ]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
