import os
import asyncio
from mcp.client.streamable_http import streamable_http_client
from mcp import ClientSession
from dotenv import load_dotenv

load_dotenv()

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8001/mcp")

async def call_mcp_tool(tool_name: str, arguments: dict) -> dict:
    """Connects to the MCP server, initializes the session, and executes a tool."""
    async with streamable_http_client(MCP_SERVER_URL) as (read, write, get_session_id):
        async with ClientSession(read, write) as session:
            await session.initialize()
            response = await session.call_tool(tool_name, arguments)
            # FastMCP response content is usually a list of TextContent/ImageContent etc.
            # We extract it and try to parse it if it is JSON.
            return response

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

async def update_transaction_status(txn_id: int, status_value: str):
    """Updates the status of a specific transaction (FUNDED or FAILED) via the MCP tool."""
    print(f"FDS Agent: Updating transaction {txn_id} status to '{status_value}' via MCP...")
    try:
        response = await call_mcp_tool("update_transaction_status", {
            "txn_id": int(txn_id),
            "status_value": status_value.upper()
        })
        print(f"FDS Agent: MCP update response: {response}")
        return response
    except Exception as e:
        print(f"FDS Agent: Failed to update transaction status: {e}")
        raise e
