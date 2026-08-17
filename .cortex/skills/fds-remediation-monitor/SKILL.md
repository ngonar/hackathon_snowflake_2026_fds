---
name: fds-remediation-monitor
description: Monitors active remediation actions, wallet freezes, KYC re-verification queue, and provides rollback capabilities. Use for reviewing ongoing enforcement, checking freeze expirations, processing unfreeze requests, and tracking remediation SLA compliance.
---

# FDS Remediation Monitor

Provides observability and management over active remediation workflows.

## Instructions

### 1. Active Wallet Freezes

Run `scripts/active_freezes.sql` to view:
- All currently frozen wallets
- Time remaining before auto-expiration
- Originating fraud analysis details
- Whether freeze has been manually reviewed

### 2. KYC Re-Verification Queue

Run `scripts/kyc_queue_status.sql` to view:
- Pending re-verification requests ordered by priority
- Processing status and age of each request
- Users awaiting action

### 3. Remediation Action History

Run `scripts/remediation_history.sql` with optional date range to view:
- All actions taken (freeze, block, flag, audit, approve)
- Grouped by risk tier
- With execution timestamps and reversal status

### 4. Unfreeze Wallet (Rollback)

Run `scripts/unfreeze_wallet.sql` with user_id and operator name to:
- Mark freeze as EXPIRED/REVERSED in WALLET_FREEZE_LOG
- Log the reversal in REMEDIATION_ACTIONS
- Restore wallet access (must also call MCP `unfreeze_user_wallet`)

### 5. Expired Freeze Cleanup

Run `scripts/expire_stale_freezes.sql` to auto-expire wallet freezes that have exceeded their duration. Should be run periodically via a Snowflake task.

## Example

```sql
-- Check all active freezes
EXECUTE SCRIPT @scripts/active_freezes.sql;

-- Unfreeze a specific user
EXECUTE SCRIPT @scripts/unfreeze_wallet.sql USING (user_id => 42, operator => 'compliance_admin');
```
