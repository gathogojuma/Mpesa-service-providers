from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta

from .api import auth, insights, platform, webhooks, businesses, billing
from .websocket import websocket_endpoint
from .database import engine, Base, SessionLocal
from .models import Business, Staff, Subscription, UsageStat
from .auth import get_password_hash
from .utils.timezone import now_local

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="TillTrack API", version="2.0.0")

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
app.include_router(businesses.router, prefix="/api/businesses", tags=["businesses"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])
app.include_router(insights.router, prefix="/api/insights", tags=["insights"])
app.include_router(platform.router, prefix="/api/platform", tags=["platform"])
app.include_router(billing.router, prefix="/api/billing", tags=["billing"])

# WebSocket endpoint
app.add_websocket_route("/ws", websocket_endpoint)


@app.get("/")
async def root():
    return {"message": "TillTrack API v2 is running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/seed-demo-data")
async def seed_demo_data():
    """
    Idempotent seed endpoint for the subscription-based TillTrack schema.
    """
    db = SessionLocal()
    try:
        actions = []

        # Platform Admin
        admin_phone = "+254700000099"
        admin = db.query(Staff).filter(Staff.phone == admin_phone).first()
        if not admin:
            admin = Staff(
                name="Platform Admin",
                phone=admin_phone,
                pin_hash=get_password_hash("1234"),
                role="platform_admin",
                business_id=None,
            )
            db.add(admin)
            db.commit()
            actions.append(f"Created platform admin: {admin_phone}")
        else:
            admin.pin_hash = get_password_hash("1234")
            admin.role = "platform_admin"
            db.commit()
            actions.append(f"Platform admin already exists: {admin_phone}")

        # Demo Business
        demo_till = "174379"
        business = db.query(Business).filter(Business.mpesa_till == demo_till).first()
        if not business:
            business = Business(
                name="Demo Bar & Grill",
                phone="+254700000001",
                mpesa_till=demo_till,
                category="bar",
                location_name="Westlands, Nairobi",
                latitude=-1.2676,
                longitude=36.8108,
            )
            db.add(business)
            db.commit()
            db.refresh(business)
            actions.append(f"Created business: {business.name} (Till {demo_till})")
        else:
            actions.append(f"Business already exists: {business.name}")

        # Demo Staff
        demo_staff = [
            ("Demo Manager", "+254700000001", "manager"),
            ("Demo Server 1", "+254700000002", "server"),
            ("Demo Server 2", "+254700000003", "server"),
        ]
        for name, phone, role in demo_staff:
            existing = db.query(Staff).filter(Staff.phone == phone).first()
            if existing:
                existing.pin_hash = get_password_hash("1234")
                existing.business_id = business.id
                existing.role = role
                existing.name = name
                db.commit()
                actions.append(f"Updated staff: {phone} ({role})")
            else:
                s = Staff(
                    name=name,
                    phone=phone,
                    pin_hash=get_password_hash("1234"),
                    role=role,
                    business_id=business.id,
                )
                db.add(s)
                db.commit()
                actions.append(f"Created staff: {phone} ({role})")

        # Subscription
        sub = db.query(Subscription).filter(
            Subscription.business_id == business.id
        ).first()

        period_start = now_local().replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = period_start + timedelta(days=30)

        if not sub:
            sub = Subscription(
                business_id=business.id,
                plan="starter",
                monthly_fee=2500.0,
                transaction_limit=2000,
                status="active",
                current_period_start=period_start,
                current_period_end=period_end,
            )
            db.add(sub)
            db.commit()
            actions.append("Created subscription: starter @ KES 2,500/mo")
        else:
            sub.status = "active"
            actions.append("Subscription already exists (status: active)")

        # Usage stats
        import random
        from datetime import date, timedelta as td

        today = date.today()
        seeded_days = 0

        for i in range(30):
            stat_date = today - td(days=i)
            existing = db.query(UsageStat).filter(
                UsageStat.business_id == business.id,
                UsageStat.stat_date == stat_date,
            ).first()
            if existing:
                continue

            hourly = {}
            for hour in range(24):
                if 10 <= hour <= 14:
                    count = random.randint(2, 8)
                elif 17 <= hour <= 23:
                    count = random.randint(8, 25)
                else:
                    count = random.randint(0, 2)
                if count > 0:
                    hourly[str(hour)] = count

            total_count = sum(hourly.values())
            avg_amount = random.uniform(300, 900)
            total_value = round(total_count * avg_amount, 2)

            app_count = int(total_count * 0.7)
            c2b_count = total_count - app_count
            app_value = round(total_value * 0.7, 2)
            c2b_value = round(total_value - app_value, 2)

            stat = UsageStat(
                business_id=business.id,
                stat_date=stat_date,
                transaction_count=total_count,
                total_value=total_value,
                app_count=app_count,
                app_value=app_value,
                c2b_count=c2b_count,
                c2b_value=c2b_value,
                cash_count=0,
                cash_value=0.0,
                unique_servers=random.randint(2, 3),
                hourly_counts=__import__("json").dumps(hourly),
            )
            db.add(stat)
            seeded_days += 1

        db.commit()
        actions.append(f"Seeded {seeded_days} days of usage stats")

        return {
            "status": "success",
            "actions": actions,
            "credentials": {
                "platform_admin": {"phone": admin_phone, "pin": "1234"},
                "manager": {"phone": "+254700000001", "pin": "1234"},
                "server_1": {"phone": "+254700000002", "pin": "1234"},
                "server_2": {"phone": "+254700000003", "pin": "1234"},
            },
            "business": {
                "id": business.id,
                "name": business.name,
                "mpesa_till": business.mpesa_till,
                "category": business.category,
                "location": business.location_name,
            },
            "subscription": {
                "plan": sub.plan,
                "monthly_fee": sub.monthly_fee,
                "transaction_limit": sub.transaction_limit,
                "status": sub.status,
            },
            "test_endpoints": [
                "GET /api/insights/my-business/summary",
                "GET /api/insights/my-business/peak-hours",
                "GET /api/insights/my-business/daily-trend",
                "GET /api/platform/overview (platform admin only)",
                "GET /api/platform/businesses (platform admin only)",
                "POST /api/webhooks/mpesa/callback (M-Pesa test)",
                "POST /api/businesses/register (new business signup)",
                "POST /api/billing/checkout (start payment)",
                "GET /api/billing/status (check subscription)",
            ],
        }

    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e), "type": type(e).__name__}
    finally:
        db.close()
