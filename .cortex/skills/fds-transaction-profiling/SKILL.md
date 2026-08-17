---
name: fds-transaction-profiling
description: Builds behavioral profiles for senders and recipients by querying Snowflake transaction history. Computes average amounts, frequency, typical recipients, time-of-day patterns, and account age metrics. Use when enriching a transaction with historical context before fraud determination.
---

# FDS Transaction Profiling

Queries `NGONAROID_FDS.FDS` tables to build comprehensive behavioral profiles for fraud reasoning.

## Instructions

When a new transaction arrives for fraud analysis, run the profiling scripts to gather context:

1. **Sender Profile** — Run `scripts/sender_profile.sql` with the sender ID to retrieve account details, KYC status, wallet balance, and account age.

2. **Sender Behavioral Profile** — Run `scripts/sender_behavior.sql` with the sender ID to compute:
   - Total transaction count and lifetime volume
   - Average transaction amount and standard deviation
   - Typical transaction hour distribution
   - Unique recipient count and most frequent recipients
   - Days since last transaction
   - Account age in days

3. **Recipient Profile** — Run `scripts/recipient_profile.sql` with the recipient ID to retrieve bank details, country, currency, and how many distinct senders have used this recipient.

4. **Recipient Inflow History** — Run `scripts/recipient_inflow.sql` with the recipient ID to compute:
   - Total inflow count and volume
   - Distinct sender count (high count = potential mule)
   - Average inflow amount

## Output Format

Return a JSON object with keys: `sender`, `sender_behavior`, `recipient`, `recipient_inflow`. Each key maps to the result set from the corresponding query. This enriched context is passed downstream to the anomaly detection and classification skills.

## Example

```sql
-- Quick sender behavioral summary
EXECUTE SCRIPT @scripts/sender_behavior.sql USING (sender_id => 42);
```
