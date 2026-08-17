---
name: fds-nl-query
description: Translates natural language fraud investigation queries into executable Snowflake SQL. Enables compliance officers to ask plain English questions about transactions, fraud patterns, remediation actions, and risk metrics. Powered by Cortex AI_COMPLETE with schema-aware prompting.
---

# FDS Natural Language Query

Allows compliance officers and fraud investigators to query the FDS data model using natural language, without writing SQL.

## Instructions

When a user asks a natural language question about fraud data:

### Step 1: Build Schema-Aware Prompt

Construct a prompt that includes:
- Full table schema definitions (TRANSACTIONS, USERS, RECIPIENTS, FRAUD_ANALYSIS_LOG, REMEDIATION_ACTIONS, WALLET_FREEZE_LOG, KYC_REVERIFICATION_QUEUE)
- Common join relationships
- Rules: SELECT only, fully qualified names, 100 row limit, relevant ordering

### Step 2: Generate SQL via Cortex

Run `scripts/nl_to_sql.sql` with the user's question to call `AI_COMPLETE('llama4-maverick', <prompt>)` and retrieve a safe SELECT query.

### Step 3: Validate Safety

Before execution, verify the generated SQL:
- Starts with SELECT or WITH
- Contains no DML keywords (INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, TRUNCATE)

### Step 4: Execute and Return

Execute the validated query and return structured results with:
- The generated SQL (for transparency)
- Column names
- Result rows (max 100)
- Row count

## Example Queries

| Natural Language | Generated SQL Pattern |
|---|---|
| "Show all transactions from the last 24 hours with anomaly score above 80" | `SELECT ... FROM FRAUD_ANALYSIS_LOG WHERE ANOMALY_SCORE > 80 AND ANALYZED_AT >= DATEADD(...)` |
| "List all currently frozen wallets" | `SELECT ... FROM WALLET_FREEZE_LOG WHERE STATUS = 'ACTIVE'` |
| "Which senders have multiple fraud flags?" | `SELECT SENDER_ID, COUNT(*) FROM FRAUD_ANALYSIS_LOG WHERE IS_FRAUD GROUP BY ... HAVING COUNT(*) > 1` |
| "Show KYC re-verification queue by priority" | `SELECT ... FROM KYC_REVERIFICATION_QUEUE ORDER BY PRIORITY` |
| "Total remediation actions by risk tier this week" | `SELECT RISK_TIER, COUNT(*) FROM REMEDIATION_ACTIONS WHERE EXECUTED_AT >= ... GROUP BY RISK_TIER` |

## Safety Guardrails

- Only SELECT/WITH queries are allowed
- All queries are constrained to `SNOWFLAKE_LEARNING_DB.FDS` schema
- Results are capped at 100 rows
- Sensitive fields (passwords, tokens) are excluded from schema context
