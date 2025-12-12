"""
EXTREME Bidding-Only Load Test - Zero Authentication During Test

This version:
1. Pre-authenticates users BEFORE the test starts
2. Reuses tokens across all virtual users
3. ZERO login/register requests during the test
4. 100% of requests are bids

This is the ONLY way to truly test bidding performance.
"""

import csv
import os
import random
import time
from datetime import datetime

from locust import HttpUser, between, events, task

# Will be populated before test starts
AUTH_TOKENS = []
SESSION_ID = None
UPSET_PRICE = None
SESSION_END_TIME = None  # Session end timestamp
TEST_START_TIME = None  # Test start timestamp for bid price calculation
BID_LOG_FILE = None  # CSV file for detailed bid logging


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """
    Called ONCE before the test starts.
    Pre-authenticate users and get session info.
    """
    global \
        AUTH_TOKENS, \
        SESSION_ID, \
        UPSET_PRICE, \
        SESSION_END_TIME, \
        TEST_START_TIME, \
        BID_LOG_FILE

    # Record test start time
    TEST_START_TIME = time.time()

    # Create bid log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = f"results_{timestamp}"
    os.makedirs(log_dir, exist_ok=True)
    BID_LOG_FILE = os.path.join(log_dir, "bid_requests.csv")

    # Initialize CSV file with headers
    with open(BID_LOG_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["timestamp", "elapsed_seconds", "bid_price", "success", "response_time_ms"]
        )

    print("\n" + "=" * 70)
    print("🔧 PRE-TEST SETUP - Authenticating users...")
    print("=" * 70)
    print(f"📊 Bid log file: {BID_LOG_FILE}")

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
            print(
                f"🔍 DEBUG: Globals set - SESSION_ID type: {type(SESSION_ID)}, value: {SESSION_ID}"
            )
            print(
                f"🔍 DEBUG: UPSET_PRICE type: {type(UPSET_PRICE)}, value: {UPSET_PRICE}"
            )
            print(
                f"🔍 DEBUG: SESSION_END_TIME type: {type(SESSION_END_TIME)}, value: {SESSION_END_TIME}"
            )
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
    print(f"   Bid log file: {BID_LOG_FILE}")
    print("   All requests will be BIDS ONLY")
    print("   💰 Bid prices will INCREASE over time")
    print("=" * 70)
    print("🔍 FINAL CHECK - Global variables:")
    print(f"   SESSION_ID = {SESSION_ID} (type: {type(SESSION_ID)})")
    print(f"   UPSET_PRICE = {UPSET_PRICE} (type: {type(UPSET_PRICE)})")
    print(f"   TEST_START_TIME = {TEST_START_TIME} (type: {type(TEST_START_TIME)})")
    print(f"   SESSION_END_TIME = {SESSION_END_TIME} (type: {type(SESSION_END_TIME)})")
    print(f"   AUTH_TOKENS count = {len(AUTH_TOKENS)}")
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
        Override wait time with TRUE exponential decay.
        This ensures bid rate (RPS) grows exponentially as deadline approaches.
        """
        if SESSION_END_TIME is None or TEST_START_TIME is None:
            # Fallback to default wait time
            super().wait()
            return

        current_time = time.time()
        time_remaining = SESSION_END_TIME - current_time

        # If session has ended, use minimum wait time
        if time_remaining <= 0:
            time.sleep(0.05)
            return

        # Calculate elapsed time and total duration
        elapsed_time = current_time - TEST_START_TIME
        total_duration = SESSION_END_TIME - TEST_START_TIME

        max_wait = 3.0
        min_wait = 0.2

        # Calculate decay constant so wait reaches min_wait at end
        import math

        k = math.log(max_wait / min_wait) / total_duration

        # TRUE exponential decay: wait = max_wait * exp(-k * elapsed_time)
        # This makes RPS grow exponentially!
        wait_seconds = max_wait * math.exp(-k * elapsed_time)
        wait_seconds = max(min_wait, wait_seconds)
        wait_seconds *= random.uniform(0.8, 1.2)

        time.sleep(wait_seconds) @ task

    def submit_bid(self):
        """
        Submit a bid - THE ONLY REQUEST TYPE!
        Frequency increases exponentially as deadline approaches.
        Bid price increases over time.
        """
        if not self.token or not SESSION_ID or not UPSET_PRICE or not TEST_START_TIME:
            print(
                f"⚠️  ExtremeBiddingUser skipping bid: token={bool(self.token)}, SESSION_ID={SESSION_ID}, UPSET_PRICE={UPSET_PRICE}, TEST_START_TIME={TEST_START_TIME}"
            )
            return

        # Calculate bid price that increases with time
        current_time = time.time()
        elapsed_seconds = current_time - TEST_START_TIME

        # Price increases linearly: base_price + (time_factor * elapsed_time) + random_variance
        # Example: if test runs 5 minutes, price increases by ~150 over that time
        time_factor = 0.5  # Price increases by $0.5 per second
        price_increase = elapsed_seconds * time_factor
        random_variance = random.uniform(0, 20)  # Add some randomness

        bid_price = UPSET_PRICE + price_increase + random_variance
        bid_price = round(bid_price, 2)

        # Record request start time
        request_start = time.time()

        # Use with-block for catch_response
        with self.client.post(
            "/api/bid",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"session_id": str(SESSION_ID), "price": bid_price},
            name="🎯 BID (Exponential)",
            catch_response=True,
        ) as response:
            # Mark response as success or failure for Locust statistics
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")

            # Log bid details to CSV
            if BID_LOG_FILE:
                response_time = (time.time() - request_start) * 1000  # Convert to ms
                success = response.status_code == 200

                try:
                    with open(BID_LOG_FILE, "a", newline="") as f:
                        writer = csv.writer(f)
                        writer.writerow(
                            [
                                datetime.now().isoformat(),
                                round(elapsed_seconds, 2),
                                bid_price,
                                success,
                                round(response_time, 2),
                            ]
                        )
                except Exception:
                    pass  # Don't fail the test if logging fails


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
        Override wait time with TRUE exponential decay.
        This ensures bid rate (RPS) grows exponentially as deadline approaches.
        """
        if SESSION_END_TIME is None or TEST_START_TIME is None:
            super().wait()
            return

        current_time = time.time()
        time_remaining = SESSION_END_TIME - current_time

        if time_remaining <= 0:
            time.sleep(0.05)
            return

        # Calculate elapsed time and total duration
        elapsed_time = current_time - TEST_START_TIME
        total_duration = SESSION_END_TIME - TEST_START_TIME

        max_wait = 5.0
        min_wait = 0.5

        # Calculate decay constant so wait reaches min_wait at end
        import math

        k = math.log(max_wait / min_wait) / total_duration

        # TRUE exponential decay: wait = max_wait * exp(-k * elapsed_time)
        # This makes RPS grow exponentially!
        wait_seconds = max_wait * math.exp(-k * elapsed_time)
        wait_seconds = max(min_wait, wait_seconds)
        wait_seconds *= random.uniform(0.8, 1.2)

        time.sleep(wait_seconds) @ task(95)

    def submit_bid(self):
        """Bid - 95% of requests, price increases over time"""
        if not self.token or not SESSION_ID or not UPSET_PRICE or not TEST_START_TIME:
            print(
                f"⚠️  Skipping bid: token={bool(self.token)}, SESSION_ID={SESSION_ID}, UPSET_PRICE={UPSET_PRICE}, TEST_START_TIME={TEST_START_TIME}"
            )
            return

        # Calculate bid price that increases with time
        current_time = time.time()
        elapsed_seconds = current_time - TEST_START_TIME

        time_factor = 0.5  # Price increases by $0.5 per second
        price_increase = elapsed_seconds * time_factor
        random_variance = random.uniform(0, 20)

        bid_price = UPSET_PRICE + price_increase + random_variance
        bid_price = round(bid_price, 2)

        # Record request start time
        request_start = time.time()

        # Use with-block for catch_response
        with self.client.post(
            "/api/bid",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"session_id": str(SESSION_ID), "price": bid_price},
            name="🎯 BID (Exponential-95%)",
            catch_response=True,
        ) as response:
            # Mark response as success or failure for Locust statistics
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")

            # Log bid details to CSV
            if BID_LOG_FILE:
                response_time = (time.time() - request_start) * 1000
                success = response.status_code == 200

                try:
                    with open(BID_LOG_FILE, "a", newline="") as f:
                        writer = csv.writer(f)
                        writer.writerow(
                            [
                                datetime.now().isoformat(),
                                round(elapsed_seconds, 2),
                                bid_price,
                                success,
                                round(response_time, 2),
                            ]
                        )
                except Exception:
                    pass

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
