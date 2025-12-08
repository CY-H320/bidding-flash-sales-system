"""
Create test users for load testing.

This script creates 100 test users that will be used by the optimized load test.
Run this ONCE before starting your load test.
"""

import sys
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed


def create_user(base_url, username, password, index):
    """Create a single test user"""
    try:
        response = requests.post(
            f"{base_url}/api/auth/register",
            json={
                "username": username,
                "email": f"{username}@loadtest.com",
                "password": password,
                "is_admin": False
            },
            timeout=10
        )

        if response.status_code == 200:
            return (index, True, username)
        elif response.status_code == 400 and "already exists" in response.text.lower():
            return (index, True, f"{username} (already exists)")
        else:
            return (index, False, f"{username} - {response.status_code}")
    except Exception as e:
        return (index, False, f"{username} - Error: {e}")


def create_test_users(base_url, num_users=100):
    """
    Create multiple test users concurrently.

    Args:
        base_url: API base URL
        num_users: Number of users to create (default: 100)
    """
    print(f"\n{'='*60}")
    print(f"🔧 CREATING {num_users} TEST USERS")
    print(f"{'='*60}")
    print(f"Target: {base_url}")
    print(f"\nThis may take a minute...\n")

    # Create users concurrently (10 at a time to avoid overwhelming server)
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for i in range(1, num_users + 1):
            username = f"testuser{i}"
            password = "test123"
            future = executor.submit(create_user, base_url, username, password, i)
            futures.append(future)

        # Collect results as they complete
        for future in as_completed(futures):
            index, success, message = future.result()
            results.append((index, success, message))

            # Show progress
            if len(results) % 10 == 0:
                success_count = sum(1 for _, s, _ in results if s)
                print(f"Progress: {len(results)}/{num_users} users ({success_count} successful)")

    # Sort results by index and display summary
    results.sort(key=lambda x: x[0])

    success_count = sum(1 for _, success, _ in results if success)
    failed_count = num_users - success_count

    print(f"\n{'='*60}")
    print(f"📊 SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Successfully created: {success_count}/{num_users}")
    print(f"❌ Failed: {failed_count}/{num_users}")

    if failed_count > 0:
        print(f"\n❌ Failed users:")
        for idx, success, message in results:
            if not success:
                print(f"   {message}")

    if success_count >= 50:
        print(f"\n{'='*60}")
        print(f"✅ READY FOR LOAD TESTING")
        print(f"{'='*60}")
        print(f"\n💡 Next steps:")
        print(f"   1. Make sure you have an active bidding session:")
        print(f"      python3 setup_test_session.py {base_url}")
        print(f"\n   2. Run the optimized load test:")
        print(f"      locust -f locustfile_bidding_only.py --host={base_url}")
        print(f"\n   3. Configure in web UI:")
        print(f"      - Users: 1000 (or any number)")
        print(f"      - Spawn rate: 50")
        print(f"      - Open: http://localhost:8089")
    else:
        print(f"\n❌ Not enough users created. Please check your server and try again.")
        sys.exit(1)


if __name__ == "__main__":
    # Get base URL from command line or use default
    if len(sys.argv) > 1:
        base_url = sys.argv[1].rstrip("/")
    else:
        base_url = "http://localhost:8000"

    # Get number of users (default 100)
    num_users = int(sys.argv[2]) if len(sys.argv) > 2 else 100

    print("\n" + "="*60)
    print("🎯 LOAD TEST USER CREATION")
    print("="*60)

    create_test_users(base_url, num_users)
