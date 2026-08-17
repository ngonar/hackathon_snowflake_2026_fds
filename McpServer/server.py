import os
import json
import threading
from typing import Optional, List, Dict, Any
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from fastmcp import FastMCP

# Configuration
API_URL = os.environ.get("REMIT_API_URL", "http://localhost:8000").rstrip("/")
SESSION_FILE = ".session.json"

# Initialize FastMCP Server
os.environ["FASTMCP_PORT"] = "8001"
os.environ["FASTMCP_HOST"] = "0.0.0.0"
mcp = FastMCP("RemitApp")


# Health check endpoint for SPCS readiness probe
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def start_health_server():
    server = HTTPServer(("0.0.0.0", 8081), HealthHandler)
    server.serve_forever()


# Session Token Helper Functions
def save_token(token: str) -> None:
    """Saves the authorization token to a local session file."""
    try:
        with open(SESSION_FILE, "w") as f:
            json.dump({"access_token": token}, f)
    except Exception as e:
        print(f"Warning: Failed to save session token: {e}")

def load_token() -> Optional[str]:
    """Loads the authorization token from the local session file."""
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r") as f:
                data = json.load(f)
                return data.get("access_token")
        except Exception:
            pass
    return None

def get_headers(token: Optional[str] = None) -> Dict[str, str]:
    """Constructs the headers for API requests, adding authorization if a token exists."""
    headers = {"Content-Type": "application/json"}
    t = token or load_token()
    if t:
        headers["Authorization"] = f"Bearer {t}"
    return headers

def make_request(
    method: str,
    path: str,
    json_data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    token: Optional[str] = None
) -> Any:
    """Utility function to make HTTP requests to the RemitApp API and handle errors."""
    url = f"{API_URL}{path}"
    headers = get_headers(token)
    
    # For form-urlencoded endpoints like /auth/token
    if data is not None:
        headers.pop("Content-Type", None)
        
    try:
        response = requests.request(
            method=method,
            url=url,
            json=json_data,
            params=params,
            data=data,
            headers=headers,
            timeout=15
        )
        response.raise_for_status()
        
        if response.status_code == 204 or not response.content:
            return {"status": "success"}
            
        try:
            return response.json()
        except ValueError:
            return {"text": response.text}
            
    except requests.exceptions.HTTPError as e:
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        return {
            "error": f"HTTP {response.status_code} Error",
            "detail": detail
        }
    except requests.exceptions.ConnectionError:
        return {
            "error": "Connection Error",
            "detail": f"Could not connect to API server at {API_URL}. Make sure it is running."
        }
    except Exception as e:
        return {
            "error": "Unexpected Error",
            "detail": str(e)
        }

# -----------------
# Authentication
# -----------------

@mcp.tool()
def register_user(email: str, full_name: str, password: str) -> Dict[str, Any]:
    """
    Register a new user.

    Args:
        email: Email address of the user.
        full_name: Full name of the user.
        password: Password (must be at least 6 characters).
    """
    payload = {
        "email": email,
        "full_name": full_name,
        "password": password
    }
    return make_request("POST", "/auth/register", json_data=payload)

@mcp.tool()
def login(username: str, password: str) -> Dict[str, Any]:
    """
    Login with username (email) and password to obtain an access token.
    The token is saved locally to authorize subsequent requests.

    Args:
        username: The registered email address of the user.
        password: The user's password.
    """
    form_data = {
        "username": username,
        "password": password
    }
    res = make_request("POST", "/auth/token", data=form_data)
    if isinstance(res, dict) and "access_token" in res:
        save_token(res["access_token"])
    return res

# -----------------
# Users Profile & Wallet
# -----------------

@mcp.tool()
def get_current_user(token: Optional[str] = None) -> Dict[str, Any]:
    """
    Get details of the currently authenticated user.

    Args:
        token: Optional custom access token. If not provided, the saved session token will be used.
    """
    return make_request("GET", "/users/me", token=token)

@mcp.tool()
def submit_kyc(kyc_document_type: str, kyc_document_number: str, token: Optional[str] = None) -> Dict[str, Any]:
    """
    Submit KYC (Know Your Customer) documents.

    Args:
        kyc_document_type: Type of document: passport, national_id, or drivers_license.
        kyc_document_number: ID or Document number (must be at least 4 characters).
        token: Optional custom access token. If not provided, the saved session token will be used.
    """
    payload = {
        "kyc_document_type": kyc_document_type,
        "kyc_document_number": kyc_document_number
    }
    return make_request("POST", "/users/me/kyc", json_data=payload, token=token)

@mcp.tool()
def deposit_funds(amount: float, token: Optional[str] = None) -> Dict[str, Any]:
    """
    Deposit funds into the user's wallet in USD.

    Args:
        amount: Amount to deposit (must be greater than 0).
        token: Optional custom access token. If not provided, the saved session token will be used.
    """
    payload = {
        "amount": amount
    }
    return make_request("POST", "/users/me/deposit", json_data=payload, token=token)

# -----------------
# Recipients Management
# -----------------

@mcp.tool()
def list_recipients(token: Optional[str] = None) -> Any:
    """
    List all saved recipients for the current user.

    Args:
        token: Optional custom access token. If not provided, the saved session token will be used.
    """
    return make_request("GET", "/recipients", token=token)

@mcp.tool()
def create_recipient(
    name: str,
    bank_name: str,
    account_number: str,
    country: str,
    currency: str,
    routing_number: Optional[str] = None,
    token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new recipient for transfers.

    Args:
        name: Full name of the recipient.
        bank_name: Name of the bank.
        account_number: Account number.
        country: Country of the recipient bank.
        currency: Currency of the recipient bank.
        routing_number: Optional bank routing number.
        token: Optional custom access token. If not provided, the saved session token will be used.
    """
    payload = {
        "name": name,
        "bank_name": bank_name,
        "account_number": account_number,
        "country": country,
        "currency": currency,
        "routing_number": routing_number
    }
    return make_request("POST", "/recipients", json_data=payload, token=token)

# -----------------
# Exchange Rates
# -----------------

@mcp.tool()
def get_rates() -> Any:
    """
    Get all active currency exchange rates.
    """
    return make_request("GET", "/rates")

@mcp.tool()
def estimate_transfer(source_currency: str, target_currency: str, source_amount: float) -> Dict[str, Any]:
    """
    Estimate a remittance transfer, including the fee and target amount.

    Args:
        source_currency: The currency being sent (e.g. USD).
        target_currency: The currency being received (e.g. EUR).
        source_amount: The amount being sent.
    """
    params = {
        "source_currency": source_currency,
        "target_currency": target_currency,
        "source_amount": source_amount
    }
    return make_request("GET", "/rates/estimate", params=params)

# -----------------
# Transactions Management
# -----------------

@mcp.tool()
def list_my_transactions(token: Optional[str] = None) -> Any:
    """
    List all remittance transactions created by the current user.

    Args:
        token: Optional custom access token. If not provided, the saved session token will be used.
    """
    return make_request("GET", "/transactions", token=token)

@mcp.tool()
def create_transaction(recipient_id: int, source_amount: float, token: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a new remittance transaction.

    Args:
        recipient_id: ID of the recipient.
        source_amount: Amount to transfer (excludes fee).
        token: Optional custom access token. If not provided, the saved session token will be used.
    """
    payload = {
        "recipient_id": recipient_id,
        "source_amount": source_amount
    }
    return make_request("POST", "/transactions", json_data=payload, token=token)

@mcp.tool()
def fund_transaction(txn_id: int, token: Optional[str] = None) -> Dict[str, Any]:
    """
    Fund a pending remittance transaction from the user's wallet balance.

    Args:
        txn_id: The ID of the transaction to fund.
        token: Optional custom access token. If not provided, the saved session token will be used.
    """
    return make_request("POST", f"/transactions/{txn_id}/fund", token=token)

@mcp.tool()
def get_transaction_details(txn_id: int, token: Optional[str] = None) -> Dict[str, Any]:
    """
    Get details of a specific remittance transaction.

    Args:
        txn_id: The ID of the transaction.
        token: Optional custom access token. If not provided, the saved session token will be used.
    """
    return make_request("GET", f"/transactions/{txn_id}", token=token)

# -----------------
# Admin Management
# -----------------

@mcp.tool()
def get_pending_kyc(token: Optional[str] = None) -> Any:
    """
    [Admin] Get a list of all users with pending KYC status.

    Args:
        token: Optional custom access token. If not provided, the saved session token will be used.
    """
    return make_request("GET", "/admin/kyc", token=token)

@mcp.tool()
def approve_kyc(user_id: int, approve: bool, token: Optional[str] = None) -> Dict[str, Any]:
    """
    [Admin] Approve or reject KYC submission for a user.

    Args:
        user_id: ID of the user.
        approve: True to approve, False to reject.
        token: Optional custom access token. If not provided, the saved session token will be used.
    """
    params = {
        "approve": approve
    }
    return make_request("POST", f"/admin/kyc/{user_id}/approve", params=params, token=token)

@mcp.tool()
def list_all_transactions(token: Optional[str] = None) -> Any:
    """
    [Admin] List all transactions in the system.

    Args:
        token: Optional custom access token. If not provided, the saved session token will be used.
    """
    return make_request("GET", "/admin/transactions", token=token)

@mcp.tool()
def update_transaction_status(
    txn_id: int, 
    status_value: str, 
    anomaly_score: Optional[float] = None,
    velocity_flags: Optional[str] = None,
    fraud_explanation: Optional[str] = None,
    fraud_evidence: Optional[str] = None,
    token: Optional[str] = None
) -> Dict[str, Any]:
    """
    [Admin] Update the status of a specific transaction with optional FDS risk information.

    Args:
        txn_id: The ID of the transaction.
        status_value: The new status value (e.g. pending, funded, processing, completed, failed, suspicious).
        anomaly_score: Optional anomaly score from FDS.
        velocity_flags: Optional velocity flags from FDS.
        fraud_explanation: Optional AI reasoning explanation from FDS.
        fraud_evidence: Optional AI reasoning key evidence.
        token: Optional custom access token. If not provided, the saved session token will be used.
    """
    params = {
        "status_value": status_value
    }
    if anomaly_score is not None:
        params["anomaly_score"] = anomaly_score
    if velocity_flags is not None:
        params["velocity_flags"] = velocity_flags
    if fraud_explanation is not None:
        params["fraud_explanation"] = fraud_explanation
    if fraud_evidence is not None:
        params["fraud_evidence"] = fraud_evidence
        
    return make_request("POST", f"/admin/transactions/{txn_id}/status", params=params, token=token)

@mcp.tool()
def create_or_update_rate(
    source_currency: str,
    target_currency: str,
    rate: float,
    fee_percentage: float,
    token: Optional[str] = None
) -> Dict[str, Any]:
    """
    [Admin] Create or update an exchange rate.

    Args:
        source_currency: Source currency code (e.g. USD).
        target_currency: Target currency code (e.g. EUR).
        rate: The exchange rate value.
        fee_percentage: The transfer fee percentage.
        token: Optional custom access token. If not provided, the saved session token will be used.
    """
    payload = {
        "source_currency": source_currency,
        "target_currency": target_currency,
        "rate": rate,
        "fee_percentage": fee_percentage
    }
    return make_request("POST", "/admin/rates", json_data=payload, token=token)

# -----------------
# Utility
# -----------------

@mcp.tool()
def get_root() -> Dict[str, Any]:
    """
    Read root endpoint to verify API connection.
    """
    return make_request("GET", "/")

if __name__ == "__main__":
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    mcp.run(transport="streamable-http", port=8001)
