# Load Testing - Bidding Flash Sale System

## Purpose

Test your bidding system's performance under high load (1000+ concurrent users).

## Quick Start

### Prerequisites

1. Backend deployed and accessible
2. Admin user exists (username: `admin`, password: `admin123`)
3. Python 3.8+ and pip installed

### Step 1: Install Dependencies

```bash
pip3 install -r requirements.txt
```

### Step 2: Run the Test

**Automated (Recommended):**
```bash
./run_test.sh http://your-host-url 1000 100 5m
```

**For AWS:**
```bash
./run_test.sh http://biddingflashsalesalb-1838681311.ap-southeast-2.elb.amazonaws.com 1000 100 5m
```

**Interactive Web UI:**
```bash
locust -f locustfile.py --host=http://your-host-url
```
Then open http://localhost:8089

## 📋 Files

- **`locustfile.py`** - Optimized load test (100% bidding, zero auth overhead)
- **`run_test.sh`** - Automated test runner
- **`create_test_users.py`** - Pre-create test users (run once)
- **`setup_test_session.py`** - Create active bidding session
- **`requirements.txt`** - Python dependencies

