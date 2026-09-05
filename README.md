# Ngonaroid FDS

AI-powered fraud detection system for international remittance transactions, built on Snowflake.

Ngonaroid FDS monitors money transfers in real time, combining rule-based anomaly scoring with LLM-powered classification (Snowflake Cortex AI) to detect seven types of remittance fraud. When threats are identified, the system auto-remediates — freezing wallets, blocking transactions, and dispatching KYC re-verification — without human intervention.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  ClientApp   │────▸│  ApiServer   │────▸│  Snowflake   │
│  React 19    │     │  FastAPI     │     │  (Primary DB)│
└─────────────┘     └──────┬──────┘     └──────┬──────┘
                           │                    │
                    ┌──────┴──────┐      Streams│& Tasks
                    │  McpServer   │             │
                    │  FastMCP 2.0 │◂────┐ ┌────▾──────┐
                    └─────────────┘     │ │  FdsAgent   │
                                        └─│  LangChain  │
                                          │  Cortex AI  │
                                          └─────────────┘
```

| Component | Description | Port |
|-----------|-------------|------|
| **ApiServer** | REST API for remittance operations — auth, transfers, recipients, exchange rates, admin | 8000 |
| **FdsAgent** | AI fraud detection engine — consumes Snowflake streams, profiles behavior, scores anomalies, classifies via LLM, auto-remediates | 8002 |
| **McpServer** | MCP bridge exposing 20+ API tools for AI agent integration | 8001 |
| **ClientApp** | React frontend — user dashboard, admin panel, fraud investigator | 5173 |

## Fraud Detection Pipeline

1. **Ingestion** — New transactions land in Snowflake via the API and are picked up by a stream
2. **Profiling** — Sender and recipient behavioral profiles are built from transaction history (averages, frequency, typical recipients, time-of-day patterns)
3. **Anomaly Detection** — Rule-based checks flag velocity spikes, amount deviations, smurfing patterns, circular transfers, rapid onboarding, and unusual-hour activity
4. **LLM Classification** — Snowflake Cortex Complete (`llama3.1-70b`) classifies transactions across 7 fraud types with structured reasoning
5. **Risk Scoring** — Rule-based and LLM scores are merged into a final risk tier: LOW / MEDIUM / HIGH / CRITICAL
6. **Remediation** — Actions are executed automatically based on risk tier: transaction blocking, wallet freezes, KYC re-verification dispatch, compliance audit logging

### Fraud Types Detected

- Structuring / Smurfing
- Velocity abuse
- Circular transfers (money laundering)
- Amount anomalies
- Time-based evasion (unusual hours)
- Rapid onboarding exploitation
- New-recipient burst patterns

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 19, Vite 8, Lucide React |
| API | FastAPI, SQLAlchemy, Snowflake Connector, JWT |
| Fraud Agent | LangChain Core, LangServe, Snowflake Cortex AI |
| MCP Bridge | FastMCP 2.0 |
| Database | Snowflake (primary), SQLite (local audit) |
| Deployment | Docker, Snowflake SPCS, Snowflake App Runtime |

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker
- A Snowflake account with Cortex AI enabled
- Snowflake CLI (`snow`)

## Setup

### 1. Snowflake Schema

Provision the FDS schema, tables, streams, and tasks in your Snowflake account. The system uses the `SNOWFLAKE_LEARNING_DB.FDS` schema by default.

### 2. Environment Variables

Each service reads Snowflake credentials from environment variables:

```
SNOWFLAKE_ACCOUNT=<your-account>
SNOWFLAKE_USER=<your-user>
SNOWFLAKE_PASSWORD=<your-password>
SNOWFLAKE_DATABASE=SNOWFLAKE_LEARNING_DB
SNOWFLAKE_SCHEMA=FDS
SNOWFLAKE_WAREHOUSE=<your-warehouse>
```

### 3. Local Development

**API Server:**
```bash
cd ApiServer
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**FDS Agent:**
```bash
cd FdsAgent
pip install -r requirements.txt
python main.py
```

**MCP Server:**
```bash
cd McpServer
pip install -r requirements.txt
python server.py
```

**Client App:**
```bash
cd ClientApp
npm install
npm run dev
```

### 4. Deploy to Snowflake SPCS

Build and push container images, then create the SPCS services:

```bash
./deploy.sh
```

Then run the service creation SQL:
```bash
snow sql -f deploy_services.sql
```

Deploy the client app:
```bash
cd ClientApp
snow app deploy
```

## Project Structure

```
Ngonaroid_FDS/
├── ApiServer/              # FastAPI remittance API
├── FdsAgent/               # AI fraud detection agent
├── McpServer/              # MCP bridge server
├── ClientApp/              # React frontend (Snowflake App)
├── .cortex/skills/         # Cortex Code FDS pipeline skills
├── deploy.sh               # Docker build & push script
├── deploy_services.sql     # SPCS service creation
└── bulk_transfer_template.csv
```

## Cortex Code Skills

The project includes 8 Cortex Code skills that expose the FDS pipeline as interactive commands:

| Skill | Purpose |
|-------|---------|
| `fds-setup` | Provision Snowflake schema and infrastructure |
| `fds-transaction-profiling` | Build sender/recipient behavioral profiles |
| `fds-anomaly-detection` | Run rule-based anomaly scoring |
| `fds-fraud-classification` | LLM-powered fraud type classification |
| `fds-investigation` | Ad-hoc fraud investigation queries |
| `fds-remediation` | Execute auto-remediation workflows |
| `fds-remediation-monitor` | Monitor active remediations and freezes |
| `fds-nl-query` | Natural language to fraud investigation SQL |

## API Documentation

When running locally, interactive API docs are available at:
- Swagger UI: `http://localhost:8000/docs`
- FDS Agent Playground: `http://localhost:8002/fds/playground`

## Security Notes

- Rotate any credentials found in `deploy.sh` and `deploy_services.sql` before production use
- When running inside SPCS, services authenticate via OAuth token (`/snowflake/session/token`)
- JWT tokens are used for API authentication with configurable expiry
- All fraud analysis results are logged to both Snowflake and local SQLite for audit trails

## License

Proprietary. All rights reserved.
