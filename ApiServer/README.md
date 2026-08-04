# ApiServer

REST API server for the Ngonaroid Remittance platform. Built with FastAPI, it handles user registration, authentication, KYC verification, recipient management, exchange rates, and remittance transactions. When a transaction is created, it publishes an event to RabbitMQ for fraud detection processing.

## Features

- User registration and JWT authentication
- KYC document submission and admin approval
- Recipient management per user
- Exchange rate lookup (USD to EUR, KES, INR, PHP, GBP, MXN)
- Transaction creation with automatic fee calculation
- RabbitMQ event publishing for fraud detection pipeline
- Admin endpoints for user and transaction management

## Prerequisites

- Python 3.10+
- RabbitMQ running on localhost:5672

## Installation

```bash
cd ApiServer
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

## Browser Access

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Root: http://localhost:8000/
