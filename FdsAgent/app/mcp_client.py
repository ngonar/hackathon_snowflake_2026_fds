import os
import asyncio
from mcp.client.streamable_http import streamable_http_client
from mcp import ClientSession
from dotenv import load_dotenv

load_dotenv()

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8001/mcp")

async def call_mcp_tool(tool_name: str, arguments: dict) -> dict:
    """Connects to the MCP server, initializes the session, and executes a tool."""
    try:
        async with streamable_http_client(MCP_SERVER_URL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                response = await session.call_tool(tool_name, arguments)
                return response
    except Exception as e:
        print(f"FDS Agent: call_mcp_tool failed for {tool_name}: {e}")
        import traceback
        traceback.print_exc()
        raise e

async def login_as_admin():
    """Logs in as admin on the MCP server to obtain and save the JWT token."""
    print("FDS Agent: Logging in as admin on the MCP server...")
    try:
        # Call the login tool
        response = await call_mcp_tool("login", {
            "username": "admin@remit.com",
            "password": "AdminPass123!"
        })
        print(f"FDS Agent: Login response: {response}")
        return response
    except Exception as e:
        print(f"FDS Agent: Failed to login as admin to MCP: {e}")
        return None

async def update_transaction_status(
    txn_id: int, 
    status_value: str,
    anomaly_score: float = None,
    velocity_flags: str = None,
    fraud_explanation: str = None,
    fraud_evidence: str = None
):
    """Updates the status of a specific transaction via the MCP tool."""
    print(f"FDS Agent: Updating transaction {txn_id} status to '{status_value}' via MCP...")
    try:
        args = {
            "txn_id": int(txn_id),
            "status_value": status_value.upper()
        }
        if anomaly_score is not None:
            args["anomaly_score"] = float(anomaly_score)
        if velocity_flags is not None:
            args["velocity_flags"] = velocity_flags
        if fraud_explanation is not None:
            args["fraud_explanation"] = fraud_explanation
        if fraud_evidence is not None:
            args["fraud_evidence"] = fraud_evidence

        response = await call_mcp_tool("update_transaction_status", args)
        print(f"FDS Agent: MCP update response: {response}")
        return response
    except Exception as e:
        print(f"FDS Agent: Failed to update transaction status: {e}")
        raise e
