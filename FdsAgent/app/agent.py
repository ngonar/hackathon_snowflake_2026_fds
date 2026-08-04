import os
import json
import asyncio
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from langchain_core.runnables import RunnableLambda
import snowflake.connector
from dotenv import load_dotenv

from app.db import save_analysis
from app.enrichment import enrich_transaction
from app.mcp_client import update_transaction_status

load_dotenv()

def _get_snowflake_session():
    """Create a Snowflake connection for Cortex Complete calls."""
    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
        role=os.getenv("SNOWFLAKE_ROLE"),
    )

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

Analyze the provided data thoroughly. Be objective, conservative, and precise. Cite specific values and times to back up your decision."""

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
        escaped_prompt = prompt.replace("'", "''")
        sql = f"""
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                'llama4-maverick',
                '{escaped_prompt}',
                {{'max_tokens': 4096, 'temperature': 0}}
            )
        """
        cursor.execute(sql)
        row = cursor.fetchone()
        raw_response = row[0]
        # The SQL COMPLETE with options returns a JSON object with choices
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
    retry_delay = 2
    analysis = None
    for attempt in range(max_retries):
        try:
            analysis = await call_cortex_complete(prompt)
            break
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"FDS Agent: Error calling model after {max_retries} attempts: {e}")
                raise e
            print(f"FDS Agent: Transient model error (attempt {attempt+1}/{max_retries}): {e}. Retrying in {retry_delay}s...")
            await asyncio.sleep(retry_delay)
            retry_delay *= 2
            
    print(f"FDS Agent: Analysis finished. is_fraud: {analysis.is_fraud}, type: {analysis.fraud_type}")
    
    decision = "FAILED" if analysis.is_fraud else "FUNDED"
    
    # 3. Log results to our local SQLite database (fds.db)
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
        decision=decision
    )
    
    # 4. Call MCP to update the transaction status in the main system
    try:
        await update_transaction_status(txn.get("id"), decision)
    except Exception as e:
        print(f"FDS Agent: Warning: MCP update failed: {e}")
        
    return {
        "txn_id": txn.get("id"),
        "reference_number": txn.get("reference_number"),
        "is_fraud": analysis.is_fraud,
        "fraud_type": analysis.fraud_type,
        "explanation": analysis.explanation,
        "decision": decision
    }

# Expose the entire process as a LangChain RunnableLambda
fds_process_chain = RunnableLambda(analyze_and_process_txn)
