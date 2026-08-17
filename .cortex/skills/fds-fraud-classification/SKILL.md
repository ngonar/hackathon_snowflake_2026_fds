---
name: fds-fraud-classification
description: Classifies transactions into one of 7 remittance fraud types using Snowflake Cortex AI_COMPLETE. Takes enriched transaction context and anomaly signals as input, produces a structured fraud determination with reasoning. Use after profiling and anomaly detection are complete.
---

# FDS Fraud Classification

Invokes `SNOWFLAKE.CORTEX.AI_COMPLETE` with enriched transaction context to produce a structured fraud determination.

## Instructions

After the `fds-transaction-profiling` and `fds-anomaly-detection` skills have produced their outputs, assemble the full context and call the classification model.

### Step 1: Build the Classification Prompt

Assemble the following sections into the prompt:
- Current transaction details (amount, currency, sender, recipient, timestamp)
- Sender profile and behavioral metrics from profiling skill
- Recipient profile and inflow metrics from profiling skill
- Anomaly flags and scores from detection skill

### Step 2: Call Cortex AI_COMPLETE

Run `scripts/classify_fraud.sql` which calls `SNOWFLAKE.CORTEX.AI_COMPLETE('llama4-maverick', <prompt>)` with a system prompt defining the 7 fraud types:

1. **Account Take Over (ATO)** — Sudden pattern change, unknown recipient, unusual amount
2. **Impersonation** — Profile mismatches, multiple unrelated senders to same recipient
3. **Smurfing** — Split large sums into small transactions below reporting thresholds
4. **Circular/Cross-Channel Transfer** — Money loops (A→B→C→A)
5. **Rapid Onboarding and Transfer** — New account with immediate large transfer
6. **Probe Transaction** — Tiny test amount followed by large transfer
7. **Time-Based Evasion** — Off-hours transactions or precise spacing to bypass velocity limits

### Step 3: Parse Structured Output

The model returns a JSON object matching this schema:
```json
{
  "is_fraud": boolean,
  "fraud_type": "Account Take Over | Impersonation | Smurfing | Circular or Cross-Channel Transfer | Rapid Onboarding and Transfer | Probe Transaction | Time-Based Evasion | None",
  "explanation": "string (detailed reasoning with cited facts)",
  "anomaly_score": 0.0-100.0,
  "velocity_flags": ["FLAG1", ...],
  "evidence": ["evidence point 1", ...]
}
```

### Step 4: Determine Decision

Based on the classification result:
- `is_fraud = true` → Decision: **FAILED**
- `anomaly_score >= 50` → Decision: **SUSPICIOUS**
- Otherwise → Decision: **FUNDED**

### Step 5: Log Result

Run `scripts/log_analysis.sql` to persist the result to `FRAUD_ANALYSIS_LOG`.

## Example

```sql
-- Classify a transaction with assembled context
EXECUTE SCRIPT @scripts/classify_fraud.sql
  USING (prompt => '<assembled_prompt>');
```
