# FdsAgent

Fraud Detection System (FDS) agent that analyzes remittance transactions for fraud using Snowflake Cortex Complete (llama4-maverick model). It consumes transaction events from RabbitMQ, enriches them with sender/recipient profiles and history, runs AI-powered fraud analysis, and updates transaction status via the MCP server.

## Features

- Real-time transaction fraud analysis via RabbitMQ consumer
- 7 remittance fraud type detection (ATO, Impersonation, Smurfing, Circular Transfer, Rapid Onboarding, Probe Transaction, Time-Based Evasion)
- Snowflake Cortex Complete (llama4-maverick) for AI inference
- Transaction enrichment with sender/recipient profiles and history
- Local SQLite database for analysis audit trail
- LangServe endpoint for manual invocation
- Automatic transaction status update via MCP

## Prerequisites

- Python 3.10+
- Snowflake account with Cortex AI access
- RabbitMQ running on localhost:5672
- MCP server running on localhost:8001

## Installation

```bash
cd FdsAgent
pip install -r requirements.txt
```

## Configuration

Copy `.env` and fill in your Snowflake credentials:

```
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_WAREHOUSE=your_warehouse
SNOWFLAKE_DATABASE=your_database
SNOWFLAKE_SCHEMA=your_schema
SNOWFLAKE_ROLE=your_role
```

## Run

```bash
python main.py
```

## Browser Access

- LangServe Playground: http://localhost:8002/fds/playground
- FDS Analysis History: http://localhost:8002/fds/history
- Root: http://localhost:8002/
