-- Fraud Classification via Cortex AI_COMPLETE
-- Parameters: :prompt (VARCHAR) - The fully assembled classification prompt
-- Returns: Structured JSON fraud analysis result

SELECT SNOWFLAKE.CORTEX.AI_COMPLETE(
    'llama4-maverick',
    CONCAT(
        'You are the world''s best Fraud Detection System (FDS) for a remittance company.\n',
        'Your task is to analyze an incoming transaction, enriched with sender/recipient profiles and historical transactions, and decide if it is fraudulent.\n\n',
        'You must evaluate the transaction against these 7 remittance fraud types:\n',
        '1. Account Take Over (ATO): Check if a user''s transaction patterns suddenly change significantly.\n',
        '2. Impersonation: Check for mismatches in sender/recipient profiles, or multiple unrelated senders to the same recipient.\n',
        '3. Smurfing: Check if the sender is splitting a large sum into multiple small transactions below key limits.\n',
        '4. Circular or Cross-Channel Transfer: Check for circular loops of money (A→B→C→A).\n',
        '5. Rapid Onboarding and Transfer: Check if the user registered very recently and immediately created a large transaction.\n',
        '6. Probe Transaction: Check for a very small transaction quickly followed by a much larger one.\n',
        '7. Time-Based Evasion: Check for unusual hours or precise spacing to bypass velocity limits.\n\n',
        'Analyze the provided data thoroughly. Be objective, conservative, and precise. Cite specific values and times.\n\n',
        :prompt,
        '\n\nRespond ONLY with a valid JSON object matching this schema:\n',
        '{"is_fraud": boolean, "fraud_type": "string", "explanation": "string", "anomaly_score": float, "velocity_flags": ["string"], "evidence": ["string"]}\n',
        'Do not include any text outside the JSON object.'
    ),
    OBJECT_CONSTRUCT('max_tokens', 4096, 'temperature', 0)
) AS CLASSIFICATION_RESULT;
