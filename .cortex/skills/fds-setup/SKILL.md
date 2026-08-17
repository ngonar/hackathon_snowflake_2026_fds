---
name: fds-setup
description: Initialize the Ngonaroid FDS Snowflake schema, tables, streams, and tasks for fraud detection. Run this once to provision the data infrastructure.
---

# FDS Setup

Provisions the `NGONAROID_FDS.FDS` schema with all required tables, streams, and tasks for the fraud detection pipeline.

## Instructions

Run `setup.sql` against your Snowflake account to create:

- **USERS** — Sender profiles (KYC status, wallet balance, registration date)
- **RECIPIENTS** — Transfer recipients (bank details, country, currency)
- **TRANSACTIONS** — Full transaction history (amounts, rates, fees, status)
- **FRAUD_ANALYSIS_LOG** — Persisted fraud analysis results from agent skills
- **PENDING_TRANSACTIONS** — Staging queue for unprocessed transactions
- **TXN_STREAM** — Append-only stream on TRANSACTIONS for real-time triggering
- **ENQUEUE_PENDING_TXN** — Scheduled task that moves stream data to pending queue

## Usage

```sql
-- Execute the setup script
@setup.sql
```

## Prerequisites

- `ACCOUNTADMIN` or role with `CREATE DATABASE` privileges
- `COMPUTE_WH` warehouse available
