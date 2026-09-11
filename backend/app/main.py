from .api import auth, payments, transactions, manager, reports, admin, webhooks, insights, platform

# ... existing setup ...

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(payments.router, prefix="/api/payments", tags=["payments"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["transactions"])
app.include_router(manager.router, prefix="/api/manager", tags=["manager"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])
app.include_router(insights.router, prefix="/api/insights", tags=["insights"])
app.include_router(platform.router, prefix="/api/platform", tags=["platform"])
