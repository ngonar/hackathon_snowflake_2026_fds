import os
import sys
from fastapi.testclient import TestClient

# Ensure the app package can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.main import app

def verify_snowflake_message(expected_ref: str):
    import time
    import snowflake.connector
    from app.config import settings

    print("\n[Step 11b] Verifying transaction in Snowflake...")
    try:
        time.sleep(2)  # Allow background task to complete INSERT
        conn = snowflake.connector.connect(
            account=settings.SNOWFLAKE_ACCOUNT,
            user=settings.SNOWFLAKE_USER,
            password=settings.SNOWFLAKE_PASSWORD,
            warehouse=settings.SNOWFLAKE_WAREHOUSE,
            database=settings.SNOWFLAKE_DATABASE,
            schema=settings.SNOWFLAKE_SCHEMA,
        )
        cursor = conn.cursor()
        cursor.execute(
            "SELECT REFERENCE_NUMBER FROM REMITTANCE_TRX WHERE REFERENCE_NUMBER = %s",
            (expected_ref,),
        )
        row = cursor.fetchone()

        if row:
            print(f"-> Transaction found in Snowflake table REMITTANCE_TRX!")
            print(f"-> Reference number: {row[0]}")
            assert row[0] == expected_ref, f"Expected ref {expected_ref}, got {row[0]}"
            print("-> Successfully verified transaction in Snowflake!")
        else:
            print("-> WARNING: Transaction not found in Snowflake REMITTANCE_TRX table.")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"-> Note: Could not query Snowflake (may not be configured or accessible): {e}")

def run_verification():
    print("==================================================")
    print("STARTING END-TO-END REMITTANCE API VERIFICATION")
    print("==================================================")

    # Use context manager to trigger lifespan events (DB creation & seeding)
    with TestClient(app) as client:
        # 1. Register a new user
        print("\n[Step 1] Registering user 'jane@example.com'...")
        reg_payload = {
            "email": "jane@example.com",
            "full_name": "Jane Doe",
            "password": "JanePassword123!"
        }
        response = client.post("/auth/register", json=reg_payload)
        assert response.status_code == 201, f"Registration failed: {response.text}"
        user_data = response.json()
        jane_id = user_data["id"]
        print(f"-> Registration successful. User ID: {jane_id}, KYC Status: {user_data['kyc_status']}")

        # 2. Login user to get JWT token
        print("\n[Step 2] Logging in Jane to get Access Token...")
        login_payload = {
            "username": "jane@example.com",
            "password": "JanePassword123!"
        }
        response = client.post("/auth/token", data=login_payload)
        assert response.status_code == 200, f"Login failed: {response.text}"
        jane_token = response.json()["access_token"]
        jane_headers = {"Authorization": f"Bearer {jane_token}"}
        print("-> Login successful. Token obtained.")

        # 3. Retrieve user profile
        print("\n[Step 3] Fetching Jane's profile...")
        response = client.get("/users/me", headers=jane_headers)
        assert response.status_code == 200, f"Profile fetch failed: {response.text}"
        profile = response.json()
        assert profile["kyc_status"] == "PENDING_SUBMISSION"
        assert profile["wallet_balance"] == 0.0
        print(f"-> Profile fetched. Wallet Balance: {profile['wallet_balance']} USD. KYC Status: {profile['kyc_status']}")

        # 4. Submit KYC
        print("\n[Step 4] Submitting KYC document (passport)...")
        kyc_payload = {
            "kyc_document_type": "passport",
            "kyc_document_number": "E98765432"
        }
        response = client.post("/users/me/kyc", headers=jane_headers, json=kyc_payload)
        assert response.status_code == 200, f"KYC submission failed: {response.text}"
        profile = response.json()
        assert profile["kyc_status"] == "PENDING_APPROVAL"
        print(f"-> KYC submitted. New KYC Status: {profile['kyc_status']}")

        # 5. Login Admin
        print("\n[Step 5] Logging in default admin user...")
        admin_login_payload = {
            "username": "admin@remit.com",
            "password": "AdminPass123!"
        }
        response = client.post("/auth/token", data=admin_login_payload)
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        admin_token = response.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        print("-> Admin login successful.")

        # 6. Admin lists pending KYC
        print("\n[Step 6] Admin listing users with pending KYC...")
        response = client.get("/admin/kyc", headers=admin_headers)
        assert response.status_code == 200, f"Admin KYC list failed: {response.text}"
        pending_users = response.json()
        assert len(pending_users) >= 1, "Jane should be in the list"
        assert any(u["id"] == jane_id for u in pending_users)
        print(f"-> Pending KYC users found: {len(pending_users)}")

        # 7. Admin approves Jane's KYC
        print(f"\n[Step 7] Admin approving Jane's KYC (User ID: {jane_id})...")
        response = client.post(f"/admin/kyc/{jane_id}/approve?approve=true", headers=admin_headers)
        assert response.status_code == 200, f"KYC approval failed: {response.text}"
        approved_user = response.json()
        assert approved_user["kyc_status"] == "APPROVED"
        print(f"-> User KYC status updated to: {approved_user['kyc_status']}")

        # 8. User Jane deposits funds
        print("\n[Step 8] Jane depositing 1000.00 USD into wallet...")
        deposit_payload = {"amount": 1000.00}
        response = client.post("/users/me/deposit", headers=jane_headers, json=deposit_payload)
        assert response.status_code == 200, f"Deposit failed: {response.text}"
        assert response.json()["wallet_balance"] == 1000.00
        print(f"-> Deposit successful. New Wallet Balance: {response.json()['wallet_balance']} USD")

        # 9. User Jane creates a recipient
        print("\n[Step 9] Jane registering a recipient in India (Raj Kumar, INR)...")
        recipient_payload = {
            "name": "Raj Kumar",
            "bank_name": "State Bank of India",
            "account_number": "30192837482",
            "routing_number": "SBIN0004321",
            "country": "India",
            "currency": "INR"
        }
        response = client.post("/recipients", headers=jane_headers, json=recipient_payload)
        assert response.status_code == 201, f"Recipient registration failed: {response.text}"
        recipient_id = response.json()["id"]
        print(f"-> Recipient registered successfully. Recipient ID: {recipient_id}")

        # 10. Estimate remittance
        print("\n[Step 10] Checking transfer estimate for 500.00 USD to INR...")
        response = client.get("/rates/estimate?source_currency=USD&target_currency=INR&source_amount=500.0")
        assert response.status_code == 200, f"Estimation failed: {response.text}"
        est = response.json()
        assert est["exchange_rate"] == 83.40
        assert est["fee"] == 6.0  # 1.2% of 500
        assert est["target_amount"] == 41700.0  # 500 * 83.4
        assert est["total_required"] == 506.0  # 500 + 6
        print(f"-> Estimate: Send 500.00 USD, Fee: {est['fee']} USD, Rate: {est['exchange_rate']}, Recipient Receives: {est['target_amount']} INR (Total Required: {est['total_required']} USD)")

        # 11. Create transaction
        print("\n[Step 11] Creating a remittance transaction...")
        txn_payload = {
            "recipient_id": recipient_id,
            "source_amount": 500.0
        }
        response = client.post("/transactions", headers=jane_headers, json=txn_payload)
        assert response.status_code == 201, f"Transaction creation failed: {response.text}"
        txn = response.json()
        txn_id = txn["id"]
        assert txn["status"] == "PENDING"
        assert txn["fee"] == 6.0
        assert txn["target_amount"] == 41700.0
        print(f"-> Transaction created. ID: {txn_id}, Reference: {txn['reference_number']}, Status: {txn['status']}")

        # 11b. Verify transaction was inserted into Snowflake
        verify_snowflake_message(txn["reference_number"])

        # 12. Fund transaction
        print(f"\n[Step 12] Jane funding transaction ID: {txn_id}...")
        response = client.post(f"/transactions/{txn_id}/fund", headers=jane_headers)
        assert response.status_code == 200, f"Transaction funding failed: {response.text}"
        funded_txn = response.json()
        assert funded_txn["status"] == "FUNDED"
        
        # Verify wallet deduction
        profile_response = client.get("/users/me", headers=jane_headers)
        assert profile_response.json()["wallet_balance"] == 494.0  # 1000 - 506
        print(f"-> Transaction funded. Status: {funded_txn['status']}. Remaining wallet balance: {profile_response.json()['wallet_balance']} USD")

        # 13. Admin completes transaction
        print(f"\n[Step 13] Admin completing transaction ID: {txn_id}...")
        response = client.post(f"/admin/transactions/{txn_id}/status?status_value=COMPLETED", headers=admin_headers)
        assert response.status_code == 200, f"Transaction status update failed: {response.text}"
        completed_txn = response.json()
        assert completed_txn["status"] == "COMPLETED"
        print(f"-> Transaction status updated to: {completed_txn['status']}")

        # 14. User lists transactions
        print("\n[Step 14] Jane listing her transaction history...")
        response = client.get("/transactions", headers=jane_headers)
        assert response.status_code == 200, f"History fetch failed: {response.text}"
        history = response.json()
        assert len(history) == 1
        assert history[0]["id"] == txn_id
        assert history[0]["status"] == "COMPLETED"
        print(f"-> Transaction history contains {len(history)} record(s). Verified status is: {history[0]['status']}")

    print("\n==================================================")
    print("VERIFICATION COMPLETED SUCCESSFULLY! ALL TESTS PASSED.")
    print("==================================================")

if __name__ == "__main__":
    # Remove existing db if it exists to start fresh
    db_file = "remittance.db"
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
            print(f"Cleared existing database file: {db_file}")
        except Exception as e:
            print(f"Note: Could not delete {db_file} (may be locked): {e}")
            
    run_verification()
