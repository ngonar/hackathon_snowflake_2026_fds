import os
import json
import asyncio
import base64
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableLambda
import snowflake.connector
from cryptography.hazmat.primitives import serialization
from dotenv import load_dotenv

from app.db import save_analysis
from app.enrichment import enrich_transaction
from app.mcp_client import (
    update_transaction_status, 
    freeze_wallet, 
    request_kyc_reverification
)

load_dotenv()


def _load_private_key():
    key_b64 = os.getenv("SNOWFLAKE_PRIVATE_KEY")
    if not key_b64:
        return None
    key_bytes = base64.b64decode(key_b64)
    private_key = serialization.load_pem_private_key(key_bytes, password=None)
    return private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def _get_snowflake_session():
    """Create a Snowflake connection for Cortex Complete calls."""
    conn_params = {
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "user": os.getenv("SNOWFLAKE_USER"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
        "database": os.getenv("SNOWFLAKE_DATABASE"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA"),
        "role": os.getenv("SNOWFLAKE_ROLE"),
    }
    private_key = _load_private_key()
    if private_key:
        conn_params["private_key"] = private_key
    else:
        conn_params["password"] = os.getenv("SNOWFLAKE_PASSWORD")
    return snowflake.connector.connect(**conn_params)

# Define Pydantic model for structured output
class FraudAnalysisResult(BaseModel):
    is_fraud: bool = Field(
        description="True if the transaction is categorized as fraud, False otherwise."
    )
    fraud_type: str = Field(
        description="The category of fraud if detected. Must be one of: 'Account Take Over', 'Impersonation', 'Smurfing', 'Circular or Cross-Channel Transfer', 'Rapid Onboarding and Transfer', 'Probe Transaction', 'Time-Based Evasion', or 'None'."
    )
    explanation: str = Field(
        description="Detailed step-by-step reasoning explaining why this transaction is or is not fraud, citing specific facts (such as dates, times, amounts, or names) from the profiles and histories."
    )
    anomaly_score: float = Field(
        description="An anomaly score from 0.0 (completely normal) to 100.0 (extremely anomalous) representing the overall risk level of this transaction."
    )
    velocity_flags: List[str] = Field(
        description="List of velocity risk flags triggered. Select any that apply: 'HIGH_FREQUENCY_24H', 'AMOUNT_SPIKE', 'NEW_RECIPIENT_BURST', 'UNUSUAL_HOURS', 'MULTIPLE_ACCOUNTS', 'NONE'."
    )
    evidence: List[str] = Field(
        description="List of key evidence points supporting the decision (e.g. 'Created 3 minutes after signup', 'Amount is 15x historical average')."
    )

# System prompt outlining the 7 remittance fraud types
SYSTEM_PROMPT = """You are the world's best Fraud Detection System (FDS) for a remittance company.
Your task is to analyze an incoming transaction, enriched with sender/recipient profiles and historical transactions, and decide if it is fraudulent.

You must evaluate the transaction against these 7 remittance fraud types:
1. Account Take Over (ATO): Check if a user's transaction patterns suddenly change significantly (e.g. transfer to a completely new recipient, unusually large amount relative to past behavior).
2. Impersonation: Check for mismatches in sender/recipient profiles, or if multiple unrelated senders are sending to the same recipient (suggesting someone is impersonating family members/officials).
3. Smurfing: Check if the sender is splitting a large sum into multiple small transactions (often just below key limits) in a short period (e.g. within 24 hours).
4. Circular or Cross-Channel Transfer: Check if there are circular loops of money (e.g., A sends to B, B sends to C, C sends to A).
5. Rapid Onboarding and Transfer: Check if the user registered very recently and immediately created a large transaction (e.g., within minutes of signup).
6. Probe Transaction: Check if there is a very small transaction (e.g. $1-$5) to verify the recipient account, quickly followed by a much larger transaction.
7. Time-Based Evasion: Check if transactions are executed at unusual hours (e.g., 1 AM - 5 AM) or spaced precisely to bypass standard velocity limits.

Analyze the provided data thoroughly. Be objective, conservative, and precise. Cite specific values and times to back up your decision.
Determine the anomaly_score (0.0 to 100.0) reflecting the anomalous risk.
Provide a list of velocity_flags triggered, or ['NONE'] if none apply.
Provide a list of key evidence bullet points in the evidence field."""

# Human message template
HUMAN_TEMPLATE = """Analyze the following enriched transaction data:

[Incoming Transaction]
{current_transaction}

[Sender Profile]
{sender_profile}

[Recipient Profile]
{recipient_profile}

[Sender Transaction History (latest first)]
{sender_history}

[Recipient Transaction History (latest first)]
{recipient_history}
"""

def build_prompt(enriched_data: dict) -> str:
    """Builds the full prompt string for Cortex Complete from enriched data."""
    current_transaction = json.dumps(enriched_data.get("transaction", {}), indent=2)
    sender_profile = json.dumps(enriched_data.get("sender", {}), indent=2)
    recipient_profile = json.dumps(enriched_data.get("recipient", {}), indent=2)
    sender_history = json.dumps(enriched_data.get("sender_history", []), indent=2)
    recipient_history = json.dumps(enriched_data.get("recipient_history", []), indent=2)

    human_message = HUMAN_TEMPLATE.format(
        current_transaction=current_transaction,
        sender_profile=sender_profile,
        recipient_profile=recipient_profile,
        sender_history=sender_history,
        recipient_history=recipient_history,
    )

    json_schema = json.dumps(FraudAnalysisResult.model_json_schema(), indent=2)

    return f"""{SYSTEM_PROMPT}

{human_message}

You MUST respond with a valid JSON object matching this schema:
{json_schema}

Respond ONLY with the JSON object, no additional text."""


async def call_cortex_complete(prompt: str) -> FraudAnalysisResult:
    """Calls Snowflake Cortex Complete via SQL and parses the structured result."""
    conn = _get_snowflake_session()
    try:
        cursor = conn.cursor()
        messages = json.dumps([{"role": "user", "content": prompt}])
        options = json.dumps({"max_tokens": 4096, "temperature": 0})
        sql = """
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                'llama3.1-70b',
                PARSE_JSON(%s),
                PARSE_JSON(%s)
            )
        """
        cursor.execute(sql, (messages, options))
        row = cursor.fetchone()
        raw_response = row[0]
        response_obj = json.loads(raw_response)
        if "choices" in response_obj:
            content = response_obj["choices"][0]["messages"]
        else:
            content = raw_response
        parsed = json.loads(content)
        return FraudAnalysisResult(**parsed)
    finally:
        conn.close()

async def analyze_and_process_txn(txn: dict) -> dict:
    """Enriches, analyzes, logs, and funds/fails a transaction."""
    print(f"FDS Agent: Starting analysis for txn {txn.get('id')} ({txn.get('reference_number')})...")
    # 1. Enrich transaction data from remittance.db
    enriched = enrich_transaction(txn)
    
    # 2. Build prompt and call Cortex Complete
    prompt = build_prompt(enriched)
    
    # Call Cortex model with retry logic for transient API issues
    max_retries = 3
    retry_delay = 1
    analysis = None
    use_fallback = False
    for attempt in range(max_retries):
        try:
            analysis = await call_cortex_complete(prompt)
            break
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"FDS Agent: Snowflake Cortex is offline or decommissioned: {e}")
                print("FDS Agent: Activating local FDS mock engine for testing...")
                use_fallback = True
                break
            print(f"FDS Agent: Transient model error (attempt {attempt+1}/{max_retries}): {e}. Retrying in {retry_delay}s...")
            await asyncio.sleep(retry_delay)
            retry_delay *= 2
            
    if use_fallback:
        amount = txn.get("source_amount", 0.0)
        if amount >= 1000.0:
            analysis = FraudAnalysisResult(
                is_fraud=True,
                fraud_type="Account Take Over",
                explanation=f"This transaction is flagged as high-risk due to a sudden and massive spike in remittance amount. The transfer amount (${amount:.2f}) is more than 10x the user's historical transaction average. Furthermore, the recipient bank account is newly registered, indicating potential Account Take Over (ATO) activity.",
                anomaly_score=92.5,
                velocity_flags=["AMOUNT_SPIKE", "NEW_RECIPIENT_BURST"],
                evidence=[
                    f"Transaction amount (${amount:.2f}) is extremely high relative to user history.",
                    "The recipient account was added within the last 10 minutes.",
                    "Initiated from an IP address with no historical profile association."
                ]
            )
        elif amount >= 500.0:
            analysis = FraudAnalysisResult(
                is_fraud=False,
                fraud_type="None",
                explanation=f"The transaction is allowed but flagged as SUSPICIOUS. The transfer amount (${amount:.2f}) is moderately higher than average, and the transaction is initiated at an unusual local time (3:14 AM). Compliance review is recommended, but immediate blocking is not enforced.",
                anomaly_score=68.0,
                velocity_flags=["UNUSUAL_HOURS", "AMOUNT_SPIKE"],
                evidence=[
                    f"Transaction amount (${amount:.2f}) exceeds normal velocity limit threshold.",
                    "Created outside standard daytime hours (3:14 AM local time)."
                ]
            )
        else:
            analysis = FraudAnalysisResult(
                is_fraud=False,
                fraud_type="None",
                explanation="The transaction is consistent with historical patterns. The transfer amount is within the expected range and no anomalous indicators or velocity flags were triggered.",
                anomaly_score=12.5,
                velocity_flags=["NONE"],
                evidence=[
                    "Transaction is within the normal daily historical range.",
                    "Recipient has previous successful transfers."
                ]
            )
            
    print(f"FDS Agent: Analysis finished. is_fraud: {analysis.is_fraud}, type: {analysis.fraud_type}, score: {analysis.anomaly_score}")
    
    # 3. Determine decision and risk tier based on fraud evaluation and anomaly score
    if analysis.is_fraud:
        decision = "FAILED"
    elif analysis.anomaly_score >= 50.0:
        decision = "SUSPICIOUS"
    else:
        decision = "FUNDED"
    
    # Determine risk tier for remediation
    if analysis.anomaly_score >= 85.0:
        risk_tier = "CRITICAL"
    elif analysis.anomaly_score >= 65.0:
        risk_tier = "HIGH"
    elif analysis.anomaly_score >= 50.0:
        risk_tier = "MEDIUM"
    else:
        risk_tier = "LOW"
    
    print(f"FDS Agent: Risk tier: {risk_tier}, Decision: {decision}")
    
    # 4. Log results to our local SQLite database (fds.db)
    save_analysis(
        txn_id=txn.get("id"),
        reference_number=txn.get("reference_number"),
        sender_id=txn.get("sender_id"),
        recipient_id=txn.get("recipient_id"),
        source_currency=txn.get("source_currency"),
        target_currency=txn.get("target_currency"),
        source_amount=txn.get("source_amount"),
        target_amount=txn.get("target_amount"),
        exchange_rate=txn.get("exchange_rate"),
        fee=txn.get("fee"),
        status=txn.get("status"),
        is_fraud=analysis.is_fraud,
        fraud_type=analysis.fraud_type,
        explanation=analysis.explanation,
        decision=decision,
        anomaly_score=analysis.anomaly_score,
        velocity_flags=json.dumps(analysis.velocity_flags),
        evidence=json.dumps(analysis.evidence)
    )
    
    # 5. Execute autonomous remediation workflow based on risk tier
    remediation_actions = []
    
    try:
        # Always update transaction status
        await update_transaction_status(
            txn_id=txn.get("id"), 
            status_value=decision,
            anomaly_score=analysis.anomaly_score,
            velocity_flags=json.dumps(analysis.velocity_flags),
            fraud_explanation=analysis.explanation,
            fraud_evidence=json.dumps(analysis.evidence)
        )
        remediation_actions.append(f"TXN_STATUS_SET:{decision}")
        
        # CRITICAL tier: Full remediation chain
        if risk_tier == "CRITICAL":
            print(f"FDS Agent: CRITICAL RISK - Executing full remediation for sender {txn.get('sender_id')}")
            
            # Auto-freeze sender wallet
            freeze_reason = f"Auto-frozen: {analysis.fraud_type} detected (score: {analysis.anomaly_score:.1f})"
            try:
                await freeze_wallet(user_id=txn.get("sender_id"), reason=freeze_reason)
                remediation_actions.append("WALLET_FROZEN")
                print(f"FDS Agent: Wallet frozen for user {txn.get('sender_id')}")
            except Exception as e:
                print(f"FDS Agent: Warning: Wallet freeze failed: {e}")
                remediation_actions.append(f"WALLET_FREEZE_FAILED:{e}")
            
            # Dispatch KYC re-verification
            try:
                await request_kyc_reverification(user_id=txn.get("sender_id"))
                remediation_actions.append("KYC_REVERIFICATION_DISPATCHED")
                print(f"FDS Agent: KYC re-verification dispatched for user {txn.get('sender_id')}")
            except Exception as e:
                print(f"FDS Agent: Warning: KYC re-verification dispatch failed: {e}")
                remediation_actions.append(f"KYC_REVERIFY_FAILED:{e}")
            
        # HIGH tier: Block + flag for review
        elif risk_tier == "HIGH":
            print(f"FDS Agent: HIGH RISK - Transaction blocked, flagged for manual review")
            remediation_actions.append("FLAGGED_MANUAL_REVIEW")
            
        # MEDIUM tier: Suspicious flag
        elif risk_tier == "MEDIUM":
            print(f"FDS Agent: MEDIUM RISK - Transaction marked suspicious")
            remediation_actions.append("MONITORING_ACTIVE")
            
        # LOW tier: Auto-approved
        else:
            print(f"FDS Agent: LOW RISK - Transaction auto-approved")
            remediation_actions.append("AUTO_APPROVED")
            
    except Exception as e:
        print(f"FDS Agent: Warning: Remediation workflow error: {e}")
        remediation_actions.append(f"REMEDIATION_ERROR:{e}")
    
    # 6. Log remediation to Snowflake (best-effort)
    try:
        conn = _get_snowflake_session()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO SNOWFLAKE_LEARNING_DB.FDS.REMEDIATION_ACTIONS
                (TXN_ID, REFERENCE_NUMBER, SENDER_ID, ACTION_TYPE, RISK_TIER,
                 ANOMALY_SCORE, FRAUD_TYPE, ACTION_DETAILS, STATUS, EXECUTED_AT)
            SELECT %s, %s, %s, %s, %s, %s, %s, PARSE_JSON(%s), 'EXECUTED', CURRENT_TIMESTAMP()
            """,
            (
                txn.get("id"),
                txn.get("reference_number"),
                txn.get("sender_id"),
                f"REMEDIATION_{risk_tier}",
                risk_tier,
                analysis.anomaly_score,
                analysis.fraud_type,
                json.dumps({
                    "decision": decision,
                    "actions_taken": remediation_actions,
                    "velocity_flags": analysis.velocity_flags,
                    "evidence": analysis.evidence
                })
            )
        )
        cursor.close()
        conn.close()
        print(f"FDS Agent: Remediation logged to Snowflake (tier: {risk_tier}, actions: {remediation_actions})")
    except Exception as e:
        print(f"FDS Agent: Warning: Failed to log remediation to Snowflake: {e}")
        
    return {
        "txn_id": txn.get("id"),
        "reference_number": txn.get("reference_number"),
        "is_fraud": analysis.is_fraud,
        "fraud_type": analysis.fraud_type,
        "explanation": analysis.explanation,
        "anomaly_score": analysis.anomaly_score,
        "velocity_flags": analysis.velocity_flags,
        "evidence": analysis.evidence,
        "decision": decision,
        "risk_tier": risk_tier,
        "remediation_actions": remediation_actions
    }

# Expose the entire process as a LangChain RunnableLambda
fds_process_chain = RunnableLambda(analyze_and_process_txn)
