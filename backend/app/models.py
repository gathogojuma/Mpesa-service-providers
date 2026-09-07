from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Enum, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base
import uuid
import enum

class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    FLAGGED = "flagged"

class Business(Base):
    __tablename__ = "businesses"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    phone = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    staff = relationship("Staff", back_populates="business")
    transactions = relationship("Transaction", back_populates="business")

class Staff(Base):
    __tablename__ = "staff"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    phone = Column(String, unique=True, nullable=False)
    pin_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # 'server' or 'manager'
    business_id = Column(String, ForeignKey("businesses.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="staff")
    transactions = relationship("Transaction", back_populates="staff")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    staff_id = Column(String, ForeignKey("staff.id"))
    business_id = Column(String, ForeignKey("businesses.id"))
    mpesa_transaction_id = Column(String, unique=True, nullable=True)
    amount = Column(Float, nullable=False)
    customer_phone = Column(String, nullable=False)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING)
    initiated_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)
    table_number = Column(String, nullable=True)

    staff = relationship("Staff", back_populates="transactions")
    business = relationship("Business", back_populates="transactions")
    reconciliation_logs = relationship("ReconciliationLog", back_populates="transaction")

class ReconciliationLog(Base):
    __tablename__ = "reconciliation_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_id = Column(String, ForeignKey("transactions.id"))
    matched_by = Column(String)  # 'auto' or 'manual'
    manager_id = Column(String, ForeignKey("staff.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    transaction = relationship("Transaction", back_populates="reconciliation_logs")
    manager = relationship("Staff")
