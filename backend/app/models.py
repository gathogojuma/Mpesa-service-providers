from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, Boolean, Date
from sqlalchemy.orm import relationship
from datetime import datetime, date
from .database import Base
import uuid


class Business(Base):
    """
    A merchant using TillTrack. This is our customer — the bar, club,
    or small supermarket that pays the subscription.
    """
    __tablename__ = "businesses"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    phone = Column(String, unique=True, nullable=False)

    # The Safaricom Till that identifies this business (unique per business)
    mpesa_till = Column(String, unique=True, nullable=False, index=True)

    category = Column(String, nullable=True)                # 'bar', 'club', 'supermarket'
    location_name = Column(String, nullable=True)           # e.g. "Westlands, Nairobi"
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    staff = relationship("Staff", back_populates="business")
    subscription = relationship("Subscription", back_populates="business", uselist=False)
    usage_stats = relationship("UsageStat", back_populates="business")


class Staff(Base):
    """
    Staff members belonging to a business. Used for authentication
    into the merchant-facing dashboard.
    """
    __tablename__ = "staff"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    phone = Column(String, unique=True, nullable=False)
    pin_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)   # 'manager', 'server', 'platform_admin'
    business_id = Column(String, ForeignKey("businesses.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="staff")


class Subscription(Base):
    """
    The merchant's subscription record. One per business.
    """
    __tablename__ = "subscriptions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = Column(String, ForeignKey("businesses.id"), unique=True, nullable=False)
    plan = Column(String, nullable=False, default="starter")
    monthly_fee = Column(Float, nullable=False, default=2500.0)
    transaction_limit = Column(Integer, nullable=True)         # NULL = unlimited
    status = Column(String, nullable=False, default="active")  # 'active', 'past_due', 'cancelled'
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    business = relationship("Business", back_populates="subscription")


class UsageStat(Base):
    """
    Daily aggregated usage for a business.

    This is the CORE of the insight engine. Instead of storing individual
    transactions, we store a single row per business per day containing
    totals broken down by source.

    Sources:
    - 'app'  → customer approved an STK Push initiated by our app
    - 'c2b'  → customer paid the Till directly (C2B callback)
    - 'cash' → manually logged by staff (future feature)

    This is:
    - Enough for tiered pricing
    - Enough for business insights (peak hours, trends, channel mix)
    - NOT personal data (can't trace to any individual customer)
    """
    __tablename__ = "usage_stats"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    business_id = Column(String, ForeignKey("businesses.id"), nullable=False, index=True)
    stat_date = Column(Date, nullable=False, index=True)

    # Totals across all sources
    transaction_count = Column(Integer, nullable=False, default=0)
    total_value = Column(Float, nullable=False, default=0.0)

    # Breakdown by source
    app_count = Column(Integer, nullable=False, default=0)
    app_value = Column(Float, nullable=False, default=0.0)
    c2b_count = Column(Integer, nullable=False, default=0)
    c2b_value = Column(Float, nullable=False, default=0.0)
    cash_count = Column(Integer, nullable=False, default=0)
    cash_value = Column(Float, nullable=False, default=0.0)

    # Hourly histogram (JSON string: {"9": 3, "10": 8, ...})
    hourly_counts = Column(Text, nullable=True)

    unique_servers = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="usage_stats")
