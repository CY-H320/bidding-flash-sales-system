"""
Setup script to create an active bidding session for load testing.

This script:
1. Logs in as admin
2. Creates a test product (if needed)
3. Creates an active bidding session that will be used for stress testing
"""

import sys
from datetime import datetime, timedelta, timezone

import requests


def create_test_session(base_url: str, admin_username: str = "admin", admin_password: str = "admin123"):
    """
    Create an active bidding session for load testing.

    Args:
        base_url: The base URL of the API (e.g., http://localhost:8000)
        admin_username: Admin username
        admin_password: Admin password
    """
    print(f"🚀 Setting up load test session on {base_url}")
    print("=" * 60)

    # Step 1: Login as admin
    print("\n1️⃣  Logging in as admin...")
    login_response = requests.post(
        f"{base_url}/api/auth/login",
        json={"username": admin_username, "password": admin_password}
    )

    if login_response.status_code != 200:
        print(f"❌ Failed to login as admin: {login_response.status_code}")
        print(f"   Response: {login_response.text}")
        print("\n💡 Make sure you have an admin user created.")
        print(f"   You can create one by registering with is_admin=true")
        return None

    admin_token = login_response.json()["token"]
    print(f"✅ Admin logged in successfully")

    headers = {"Authorization": f"Bearer {admin_token}"}

    # Step 2: Create product and session together (using combined endpoint)
    print("\n2️⃣  Creating test product and bidding session...")

    # Create both product and session in one request (2 hour duration)
    session_response = requests.post(
        f"{base_url}/api/admin/sessions/combined",
        headers=headers,
        json={
            "name": "Load Test Product - High Performance Laptop",
            "description": "This is a test product for stress testing the bidding system. 16GB RAM, 512GB SSD, RTX 4060",
            "upset_price": 100.0,  # Starting bid price
            "inventory": 10,  # 10 items available
            "alpha": 1.0,  # Price weight
            "beta": 100.0,  # User weight coefficient
            "gamma": 1.0,  # User weight offset
            "duration_minutes": 120  # 2 hours
        }
    )

    if session_response.status_code == 200:
        session_data = session_response.json()
        session_id = session_data["session_id"]
        product_id = session_data["product_id"]

        print(f"✅ Product and bidding session created successfully!")
        print(f"\n{'=' * 60}")
        print(f"📊 SESSION DETAILS:")
        print(f"{'=' * 60}")
        print(f"Product Name:  {session_data.get('name', 'Load Test Product')}")
        print(f"Product ID:    {product_id}")
        print(f"Session ID:    {session_id}")
        print(f"Base Price:    ${session_data.get('upset_price', 100)}")
        print(f"Inventory:     {session_data.get('inventory', 10)} items")
        print(f"Duration:      2 hours")
        print(f"{'=' * 60}")
        print(f"\n✅ Session is now ACTIVE and ready for load testing!")
        print(f"\n💡 You can now run the Locust load test.")
        return session_id
    else:
        print(f"❌ Failed to create session: {session_response.status_code}")
        print(f"   Response: {session_response.text}")
        return None


if __name__ == "__main__":
    # Get base URL from command line or use default
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"

    # Remove trailing slash if present
    base_url = base_url.rstrip("/")

    print("\n" + "=" * 60)
    print("🎯 LOAD TEST SESSION SETUP")
    print("=" * 60)

    session_id = create_test_session(base_url)

    if session_id:
        print(f"\n✅ Setup complete! Ready to start load testing.")
        print(f"\n📝 Next steps:")
        print(f"   1. Install locust: pip install locust")
        print(f"   2. Run load test: locust -f locustfile.py --host={base_url}")
        print(f"   3. Open browser: http://localhost:8089")
        print(f"   4. Configure test with 1000+ users")
        print(f"\n🔗 Session URL: {base_url}/api/bid/leaderboard/{session_id}")
    else:
        print(f"\n❌ Setup failed. Please check the errors above.")
        sys.exit(1)
