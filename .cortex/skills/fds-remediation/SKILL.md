---
name: fds-remediation
description: Autonomously executes multi-step remediation workflows based on fraud risk tiers. Auto-freezes high-risk wallets, generates compliance audit records, dispatches KYC re-verification alerts, and logs all actions to Snowflake. Invoked after fraud classification produces a decision and anomaly score.
---

# FDS Remediation

Orchestrates contextual remediation actions based on the risk tier derived from fraud classification results.

## Risk Tier Definitions

| Tier | Anomaly Score | Actions |
|------|--------------|---------|
| **CRITICAL** | ≥ 85.0 | Freeze wallet + Fail transaction + Compliance audit + KYC re-verification |
| **HIGH** | ≥ 65.0 | Fail transaction + Compliance audit + Flag for manual review |
| **MEDIUM** | ≥ 50.0 | Mark suspicious + Compliance audit record |
| **LOW** | < 50.0 | Auto-fund + Standard audit log |

## Instructions

After `fds-fraud-classification` produces a result, determine the risk tier and execute the corresponding remediation chain:

### Step 1: Determine Risk Tier

```
IF anomaly_score >= 85.0 → CRITICAL
ELIF anomaly_score >= 65.0 → HIGH
ELIF anomaly_score >= 50.0 → MEDIUM
ELSE → LOW
```

### Step 2: Execute Actions by Tier

#### CRITICAL Tier (Score ≥ 85)

1. Run `scripts/freeze_wallet.sql` — Freezes sender wallet immediately (72h default)
2. Run `scripts/generate_compliance_audit.sql` — Creates full compliance record with evidence chain
3. Run `scripts/dispatch_kyc_reverification.sql` — Queues sender for urgent KYC re-check
4. Call MCP `update_transaction_status` with status=FAILED
5. Call MCP `freeze_user_wallet` to enforce freeze in the application layer
6. Run `scripts/log_remediation_action.sql` for each action taken

#### HIGH Tier (Score ≥ 65)

1. Run `scripts/generate_compliance_audit.sql` — Creates compliance record
2. Call MCP `update_transaction_status` with status=FAILED
3. Run `scripts/log_remediation_action.sql` with action_type=TRANSACTION_BLOCKED

#### MEDIUM Tier (Score ≥ 50)

1. Run `scripts/generate_compliance_audit.sql` — Creates compliance record (lower priority)
2. Call MCP `update_transaction_status` with status=SUSPICIOUS
3. Run `scripts/log_remediation_action.sql` with action_type=FLAGGED_SUSPICIOUS

#### LOW Tier (Score < 50)

1. Call MCP `update_transaction_status` with status=FUNDED
2. Run `scripts/log_remediation_action.sql` with action_type=AUTO_APPROVED

### Step 3: Verify Execution

After all actions complete, query `REMEDIATION_ACTIONS` to confirm all expected records were created for the transaction.

## Rollback

For false positives, use the `fds-remediation-monitor` skill to:
- Unfreeze wallets via `scripts/unfreeze_wallet.sql`
- Mark remediation actions as REVERSED
- Re-fund blocked transactions
