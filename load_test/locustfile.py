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
import time
from datetime import datetime

from locust import HttpUser, between, events, task

# Will be populated before test starts
AUTH_TOKENS = []
SESSION_ID = None
UPSET_PRICE = None
SESSION_END_TIME = None  # Session end timestamp


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """
    Called ONCE before the test starts.
    Pre-authenticate users and get session info.
    """
    global AUTH_TOKENS, SESSION_ID, UPSET_PRICE, SESSION_END_TIME

    print("\n" + "=" * 70)
    print("🔧 PRE-TEST SETUP - Authenticating users...")
    print("=" * 70)

    import requests

    base_url = environment.host

    # Step 1: Get admin token for session info
    print("\n1️⃣  Logging in as admin to get session info...")
    admin_response = requests.post(
        f"{base_url}/api/auth/login",
        json={"username": "admin", "password": "admin123"},
        timeout=10,
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
        timeout=10,
    )

    if sessions_response.status_code == 200:
        sessions = sessions_response.json()
        if sessions:
            SESSION_ID = sessions[0]["session_id"]
            UPSET_PRICE = sessions[0]["base_price"]

            # Parse end_time to get timestamp
            end_time_str = sessions[0]["end_time"]
            # Handle different datetime formats
            try:
                # Try ISO format with timezone
                SESSION_END_TIME = datetime.fromisoformat(
                    end_time_str.replace("Z", "+00:00")
                ).timestamp()
            except:
                try:
                    # Try without timezone
                    SESSION_END_TIME = datetime.strptime(
                        end_time_str, "%Y-%m-%dT%H:%M:%S"
                    ).timestamp()
                except:
                    print(f"⚠️  Could not parse end_time: {end_time_str}")
                    SESSION_END_TIME = None

            print(f"✅ Session: {SESSION_ID}")
            print(f"   Base price: ${UPSET_PRICE}")
            print(f"   End time: {end_time_str}")
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
                timeout=5,
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
                        "is_admin": False,
                    },
                    timeout=5,
                )
                if reg_response.status_code == 200:
                    token = reg_response.json()["token"]
                    AUTH_TOKENS.append(token)

        except Exception:
            # Skip failed auths, we have others
            pass

    print(f"\n✅ Pre-authenticated {len(AUTH_TOKENS)} users")
    print("=" * 70)
    print("🚀 READY TO START - 100% BIDDING TEST")
    print("=" * 70)
    print(f"   Session ID: {SESSION_ID}")
    print(f"   Auth tokens ready: {len(AUTH_TOKENS)}")
    print("   All requests will be BIDS ONLY")
    print("=" * 70 + "\n")


class ExtremeBiddingUser(HttpUser):
    """
    Virtual user that does NOTHING but bid.

    - No login during test
    - No registration during test
    - Just picks a random pre-authenticated token
    - Submits bids with EXPONENTIALLY INCREASING frequency as deadline approaches
    """

    # Initial wait time (will be dynamically adjusted)
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

    def wait(self):
        """
        Override wait time with exponential growth based on time remaining.
        As deadline approaches, wait time decreases exponentially.
        """
        if SESSION_END_TIME is None:
            # Fallback to default wait time
            super().wait()
            return

        current_time = time.time()
        time_remaining = SESSION_END_TIME - current_time

        # If session has ended, use minimum wait time
        if time_remaining <= 0:
            time.sleep(0.05)
            return

        # Calculate time remaining percentage (0 to 1)
        # Assuming session duration is the time from now to end
        total_duration = max(time_remaining, 60)  # At least 60 seconds for calculation
        time_ratio = time_remaining / total_duration

        # Exponential decay: wait_time = max_wait * (time_ratio ^ exponent)
        # When time_ratio = 1 (start): wait_time = max_wait
        # When time_ratio = 0 (end): wait_time = min_wait
        max_wait = 10.0  # Start with 10 seconds between bids
        min_wait = 0.5  # End with 0.5 seconds between bids (2 bids/sec)
        exponent = 3.0  # Controls how aggressive the exponential curve is (higher = more aggressive near end)

        # Exponential formula: wait = min + (max - min) * ratio^exponent
        wait_seconds = min_wait + (max_wait - min_wait) * (time_ratio**exponent)

        # Add small random variation to avoid synchronized requests
        wait_seconds *= random.uniform(0.8, 1.2)

        time.sleep(wait_seconds)

    @task
    def submit_bid(self):
        """
        Submit a bid - THE ONLY REQUEST TYPE!
        Frequency increases exponentially as deadline approaches.
        """
        if not self.token or not SESSION_ID or not UPSET_PRICE:
            return

        # Random bid price
        bid_price = UPSET_PRICE + random.uniform(1, 100)

        self.client.post(
            "/api/bid",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"session_id": SESSION_ID, "price": round(bid_price, 2)},
            name="🎯 BID (Exponential)",  # Exponential frequency growth!
        )


# Optional: Version with occasional leaderboard checks
class BiddingWithLeaderboardUser(HttpUser):
    """
    95% bidding, 5% leaderboard checks.
    Bidding frequency increases exponentially as deadline approaches.
    """

    wait_time = between(0.2, 0.5)

    def on_start(self):
        """Pick random token - NO LOGIN"""
        if AUTH_TOKENS:
            self.token = random.choice(AUTH_TOKENS)
        else:
            self.token = None

    def wait(self):
        """
        Override wait time with exponential growth based on time remaining.
        """
        if SESSION_END_TIME is None:
            super().wait()
            return

        current_time = time.time()
        time_remaining = SESSION_END_TIME - current_time

        if time_remaining <= 0:
            time.sleep(0.05)
            return

        total_duration = max(time_remaining, 60)
        time_ratio = time_remaining / total_duration

        max_wait = 2.5
        min_wait = 0.1
        exponent = 3.0

        wait_seconds = min_wait + (max_wait - min_wait) * (time_ratio**exponent)
        wait_seconds *= random.uniform(0.8, 1.2)

        time.sleep(wait_seconds)

    @task(95)
    def submit_bid(self):
        """Bid - 95% of requests"""
        if not self.token or not SESSION_ID or not UPSET_PRICE:
            return

        bid_price = UPSET_PRICE + random.uniform(1, 100)

        self.client.post(
            "/api/bid",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"session_id": SESSION_ID, "price": round(bid_price, 2)},
            name="🎯 BID (Exponential-95%)",
        )

    @task(5)
    def check_leaderboard(self):
        """Leaderboard - 5% of requests"""
        if not self.token or not SESSION_ID:
            return

        self.client.get(
            f"/api/leaderboard/{SESSION_ID}?page=1&page_size=50",
            headers={"Authorization": f"Bearer {self.token}"},
            name="📊 Leaderboard (5%)",
        )
