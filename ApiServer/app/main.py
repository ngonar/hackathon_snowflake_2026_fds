from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database import get_snowflake_connection
from app import crud, schemas, auth
from app.routers import auth as auth_router, users as users_router, recipients as recipients_router, rates as rates_router, transactions as transactions_router, admin as admin_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Seed Default Admin User and Exchange Rates on startup
    try:
        conn = get_snowflake_connection()

        # Seed Admin
        admin_email = auth.settings.DEFAULT_ADMIN_EMAIL
        admin_user = crud.get_user_by_email(conn, admin_email)
        if not admin_user:
            crud.create_user(conn, email=admin_email, full_name="Remittance Admin",
                           password=auth.settings.DEFAULT_ADMIN_PASSWORD, role="admin")
            admin_user = crud.get_user_by_email(conn, admin_email)
            crud.approve_user_kyc(conn, admin_user["id"], approve=True)
            crud.update_user_balance(conn, admin_user["id"], 10000.0)
            print(f"Default admin user seeded: {admin_email}")

        # Seed Test User
        test_email = "user@remit.com"
        test_user = crud.get_user_by_email(conn, test_email)
        if not test_user:
            crud.create_user(conn, email=test_email, full_name="Test User",
                           password="UserPass123!", role="user")
            test_user = crud.get_user_by_email(conn, test_email)
            crud.approve_user_kyc(conn, test_user["id"], approve=True)
            crud.update_user_balance(conn, test_user["id"], 5000.0)
            print(f"Default test user seeded: {test_email}")

        # Seed Exchange Rates
        default_rates = [
            ("USD", "EUR", 0.92, 0.01),
            ("USD", "KES", 131.50, 0.015),
            ("USD", "INR", 83.40, 0.012),
            ("USD", "PHP", 56.80, 0.013),
            ("USD", "GBP", 0.79, 0.009),
            ("USD", "MXN", 18.25, 0.014),
        ]
        for src, tgt, rate, fee in default_rates:
            rate_exists = crud.get_exchange_rate(conn, src, tgt)
            if not rate_exists:
                crud.create_or_update_exchange_rate(conn, src, tgt, rate, fee)
                print(f"Seeded exchange rate: {src} -> {tgt} (Rate: {rate}, Fee: {fee*100}%)")

        conn.close()
    except Exception as e:
        print(f"Warning: Startup seed failed: {e}")

    yield


app = FastAPI(
    title="RemitApp API Server",
    description="A secure and scalable API server for a remittance company to manage users, KYC, exchange rates, and currency transfers.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
