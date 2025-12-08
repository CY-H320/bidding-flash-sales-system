"""
EXTREME Bidding-Only Load Test - Zero Authentication During Test

This version:
1. Pre-authenticates users BEFORE the test starts
2. Reuses tokens across all virtual users
3. ZERO login/register requests during the test
4. 100% of requests are bids

This is the ONLY way to truly test bidding performance.
"""

import random
from locust import HttpUser, between, task, events


# Will be populated before test starts
AUTH_TOKENS = []
SESSION_ID = None
UPSET_PRICE = None


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """
    Called ONCE before the test starts.
    Pre-authenticate users and get session info.
    """
    global AUTH_TOKENS, SESSION_ID, UPSET_PRICE

    print("\n" + "="*70)
    print("🔧 PRE-TEST SETUP - Authenticating users...")
    print("="*70)

    import requests

    base_url = environment.host

    # Step 1: Get admin token for session info
    print("\n1️⃣  Logging in as admin to get session info...")
    admin_response = requests.post(
        f"{base_url}/api/auth/login",
        json={"username": "admin", "password": "admin123"},
        timeout=10
    )

    if admin_response.status_code != 200:
        print(f"❌ Admin login failed: {admin_response.status_code}")
        print("   Make sure admin user exists!")
        return

    admin_token = admin_response.json()["token"]

    # Step 2: Get active session
    print("2️⃣  Getting active session...")
    sessions_response = requests.get(
        f"{base_url}/api/sessions/active",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=10
    )

    if sessions_response.status_code == 200:
        sessions = sessions_response.json()
        if sessions:
            SESSION_ID = sessions[0]["session_id"]
            UPSET_PRICE = sessions[0]["base_price"]
            print(f"✅ Session: {SESSION_ID}")
            print(f"   Base price: ${UPSET_PRICE}")
        else:
            print("❌ No active sessions found!")
            print("   Run: python3 setup_test_session.py <host>")
            return
    else:
        print(f"❌ Failed to get sessions: {sessions_response.status_code}")
        return

    # Step 3: Pre-authenticate test users (slowly to avoid overwhelming server)
    print("3️⃣  Pre-authenticating test users...")
    print("   (This may take 30-60 seconds)")

    num_users = 50  # Pre-auth 50 users, they'll be reused by all virtual users

    for i in range(1, num_users + 1):
        try:
            username = f"testuser{i}"
            password = "test123"

            response = requests.post(
                f"{base_url}/api/auth/login",
                json={"username": username, "password": password},
                timeout=5
            )

            if response.status_code == 200:
                token = response.json()["token"]
                AUTH_TOKENS.append(token)
                if i % 10 == 0:
                    print(f"   Progress: {i}/{num_users} users authenticated")
            else:
                # Try to register if doesn't exist
                reg_response = requests.post(
                    f"{base_url}/api/auth/register",
                    json={
                        "username": username,
                        "email": f"{username}@test.com",
                        "password": password,
                        "is_admin": False
                    },
                    timeout=5
                )
                if reg_response.status_code == 200:
                    token = reg_response.json()["token"]
                    AUTH_TOKENS.append(token)

        except Exception as e:
            # Skip failed auths, we have others
            pass

    print(f"\n✅ Pre-authenticated {len(AUTH_TOKENS)} users")
    print("="*70)
    print("🚀 READY TO START - 100% BIDDING TEST")
    print("="*70)
    print(f"   Session ID: {SESSION_ID}")
    print(f"   Auth tokens ready: {len(AUTH_TOKENS)}")
    print(f"   All requests will be BIDS ONLY")
    print("="*70 + "\n")


class ExtremeBiddingUser(HttpUser):
    """
    Virtual user that does NOTHING but bid.

    - No login during test
    - No registration during test
    - Just picks a random pre-authenticated token
    - Submits bids non-stop
    """

    # Very aggressive wait time for maximum load
    wait_time = between(0.1, 0.3)

    def on_start(self):
        """
        Pick a random pre-authenticated token.
        NO NETWORK REQUESTS HERE!
        """
        if AUTH_TOKENS:
            self.token = random.choice(AUTH_TOKENS)
        else:
            self.token = None

    @task
    def submit_bid(self):
        """
        Submit a bid - THE ONLY REQUEST TYPE!
        """
        if not self.token or not SESSION_ID or not UPSET_PRICE:
            return

        # Random bid price
        bid_price = UPSET_PRICE + random.uniform(1, 100)

        self.client.post(
            "/api/bid",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "session_id": SESSION_ID,
                "price": round(bid_price, 2)
            },
            name="🎯 BID (100%)"  # This is all we're testing!
        )


# Optional: Version with occasional leaderboard checks
class BiddingWithLeaderboardUser(HttpUser):
    """
    95% bidding, 5% leaderboard checks.
    Use this if you want to test both endpoints.
    """

    wait_time = between(0.2, 0.5)

    def on_start(self):
        """Pick random token - NO LOGIN"""
        if AUTH_TOKENS:
            self.token = random.choice(AUTH_TOKENS)
        else:
            self.token = None

    @task(95)
    def submit_bid(self):
        """Bid - 95% of requests"""
        if not self.token or not SESSION_ID or not UPSET_PRICE:
            return

        bid_price = UPSET_PRICE + random.uniform(1, 100)

        self.client.post(
            "/api/bid",
            headers={"Authorization": f"Bearer {self.token}"},
            json={
                "session_id": SESSION_ID,
                "price": round(bid_price, 2)
            },
            name="🎯 BID (95%)"
        )

    @task(5)
    def check_leaderboard(self):
        """Leaderboard - 5% of requests"""
        if not self.token or not SESSION_ID:
            return

        self.client.get(
            f"/api/leaderboard/{SESSION_ID}?page=1&page_size=50",
            headers={"Authorization": f"Bearer {self.token}"},
            name="📊 Leaderboard (5%)"
        )
