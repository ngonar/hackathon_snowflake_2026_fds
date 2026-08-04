from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database import engine, Base, SessionLocal
from app import crud, schemas, auth
from app.routers import auth as auth_router, users as users_router, recipients as recipients_router, rates as rates_router, transactions as transactions_router, admin as admin_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize Database Tables
    Base.metadata.create_all(bind=engine)
    
    # 2. Seed Default Admin User and Exchange Rates
    db = SessionLocal()
    try:
        # Seed Admin
        admin_email = auth.settings.DEFAULT_ADMIN_EMAIL
        admin_user = crud.get_user_by_email(db, admin_email)
        if not admin_user:
            admin_create = schemas.UserCreate(
                email=admin_email,
                full_name="Remittance Admin",
                password=auth.settings.DEFAULT_ADMIN_PASSWORD
            )
            created_admin = crud.create_user(db, admin_create, role="admin")
            crud.approve_user_kyc(db, created_admin.id, approve=True)
            # Add some initial admin wallet balance just in case
            crud.update_user_balance(db, created_admin.id, 10000.0)
            print(f"Default admin user seeded: {admin_email}")
            
        # Seed Exchange Rates
        default_rates = [
            ("USD", "EUR", 0.92, 0.01),    # 1% fee
            ("USD", "KES", 131.50, 0.015),  # 1.5% fee
            ("USD", "INR", 83.40, 0.012),   # 1.2% fee
            ("USD", "PHP", 56.80, 0.013),   # 1.3% fee
            ("USD", "GBP", 0.79, 0.009),    # 0.9% fee
            ("USD", "MXN", 18.25, 0.014),   # 1.4% fee
        ]
        for src, tgt, rate, fee in default_rates:
            rate_exists = crud.get_exchange_rate(db, src, tgt)
            if not rate_exists:
                crud.create_or_update_exchange_rate(db, src, tgt, rate, fee)
                print(f"Seeded exchange rate: {src} -> {tgt} (Rate: {rate}, Fee: {fee*100}%)")
    finally:
        db.close()
        
    yield
    # Shutdown logic (if any) can go here

# Create FastAPI app
app = FastAPI(
    title="RemitApp API Server",
    description="A secure and scalable API server for a remittance company to manage users, KYC, exchange rates, and currency transfers.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth_router.router)
app.include_router(users_router.router)
app.include_router(recipients_router.router)
app.include_router(rates_router.router)
app.include_router(transactions_router.router)
app.include_router(admin_router.router)

@app.get("/")
def read_root():
    return {
        "message": "Welcome to RemitApp API Server!",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "status": "active"
    }
