---
name: fds-investigation
description: Ad-hoc fraud investigation over historical analysis results in Snowflake. Query flagged transactions, drill into specific cases, trace circular transfers, compute fraud rate metrics, and generate compliance reports. Use when reviewing past fraud decisions or investigating suspicious patterns.
---

# FDS Investigation

Provides investigative queries over `NGONAROID_FDS.FDS.FRAUD_ANALYSIS_LOG` and transaction history for compliance review and pattern analysis.

## Instructions

Use these scripts for ad-hoc fraud investigation:

### 1. Fraud Summary Dashboard

Run `scripts/fraud_summary.sql` to get aggregate fraud metrics:
- Total transactions analyzed
- Fraud rate (% flagged as fraud)
- Breakdown by fraud type
- Average anomaly score by decision category
- Top flagged senders

### 2. Transaction Deep Dive

Run `scripts/txn_deep_dive.sql` with a transaction ID or reference number to retrieve:
- Full transaction details
- Fraud analysis result (type, score, flags, evidence)
- Sender's complete behavioral profile
- Related transactions from same sender in ±7 day window

### 3. Circular Transfer Trace

Run `scripts/trace_circular.sql` with a sender_id to map all potential circular money flows discovered in the last 30 days. Visualizes the graph of A→B→C→A patterns.

### 4. High-Risk Entity Report

Run `scripts/high_risk_entities.sql` to identify:
- Senders with multiple FAILED decisions
- Recipients receiving from 5+ distinct senders (potential mule accounts)
- Accounts created in last 7 days with transactions exceeding $500

### 5. Compliance Export

Run `scripts/compliance_export.sql` with a date range to generate a structured report of all flagged transactions for regulatory submission.

## Example

```sql
-- Get fraud summary for last 30 days
EXECUTE SCRIPT @scripts/fraud_summary.sql;

-- Deep dive into a specific transaction
EXECUTE SCRIPT @scripts/txn_deep_dive.sql USING (txn_id => 1234);
```
