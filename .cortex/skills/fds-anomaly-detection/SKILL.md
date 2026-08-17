---
name: fds-anomaly-detection
description: Runs rule-based anomaly scoring against Snowflake transaction history tables. Detects velocity spikes, amount deviations, unusual hours, new-recipient bursts, smurfing patterns, and rapid onboarding signals. Use after transaction profiling to generate risk indicators.
---

# FDS Anomaly Detection

Executes anomaly detection queries against `NGONAROID_FDS.FDS.TRANSACTIONS` to produce velocity flags and an anomaly score for a given transaction.

## Instructions

Given a transaction and its sender behavioral profile, run the following detection scripts:

1. **Velocity Check** — Run `scripts/velocity_check.sql` with sender_id and a 24-hour window. Detects:
   - `HIGH_FREQUENCY_24H`: More than 5 transactions in 24 hours
   - `NEW_RECIPIENT_BURST`: 3+ new recipients added in 24 hours
   - `AMOUNT_SPIKE`: Current amount exceeds 3x the sender's historical average

2. **Time-Based Evasion** — Run `scripts/time_evasion.sql` with the transaction timestamp. Detects:
   - `UNUSUAL_HOURS`: Transaction initiated between 01:00–05:00 local time
   - Spacing patterns that suggest deliberate velocity-limit avoidance

3. **Smurfing Detection** — Run `scripts/smurfing_check.sql` with sender_id. Detects:
   - Multiple small transactions (just below threshold) within a short window
   - Aggregate volume that exceeds individual transaction limits

4. **Rapid Onboarding** — Run `scripts/rapid_onboarding.sql` with sender_id and transaction timestamp. Detects:
   - Account created within the last 60 minutes before a large transaction
   - First transaction amount exceeds $500

5. **Circular Transfer Detection** — Run `scripts/circular_check.sql` with sender_id and recipient_id. Detects:
   - A→B→C→A circular money flow patterns within 7 days

## Output Format

Return a JSON object:
```json
{
  "anomaly_score": 0.0-100.0,
  "velocity_flags": ["FLAG1", "FLAG2"],
  "details": { ... per-check breakdown ... }
}
```

The anomaly_score is computed by summing weighted flag contributions:
- HIGH_FREQUENCY_24H: +20
- AMOUNT_SPIKE: +25
- NEW_RECIPIENT_BURST: +15
- UNUSUAL_HOURS: +10
- SMURFING: +30
- RAPID_ONBOARDING: +25
- CIRCULAR_TRANSFER: +35

Score is capped at 100.0.
