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

- **`locustfile.py`** - Optimized load test (100% bidding, zero auth overhead, increasing bid prices)
- **`run_test.sh`** / **`run_test.ps1`** - Automated test runner
- **`create_test_users.py`** - Pre-create test users (run once)
- **`setup_test_session.py`** - Create active bidding session
- **`analyze_bid_logs.py`** - Analyze bid logs and generate charts
- **`requirements.txt`** - Python dependencies

## 📊 New Features

### 1. Bid Price Increases Over Time

Bids now increase by **$0.5 per second** to simulate realistic bidding behavior:
- Starting price: Base price (e.g., $100)
- After 5 minutes: Base price + $150
- Random variance: ±$20 for realistic fluctuation

### 2. Detailed Bid Request Logging

Every bid request is logged to `bid_requests.csv` with:
- Timestamp (ISO format)
- Elapsed seconds since test start
- Bid price
- Success/failure status
- Response time (ms)

### 3. Visualization & Analysis

Use `analyze_bid_logs.py` to generate charts:

```bash
# After running a test
python analyze_bid_logs.py results_20231211_120000
```

This generates:
1. **Requests per second** line chart
2. **Bid price over time** scatter plot with trend line
3. **Success rate over time** chart (5-second intervals)
4. **Response time distribution** histogram and box plot
5. **Combined dashboard** with all metrics

All charts saved to `results_<timestamp>/analysis/` folder

