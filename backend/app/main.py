from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import auth, payments, transactions, manager, reports
from .websocket import websocket_endpoint
from .database import engine, Base

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
