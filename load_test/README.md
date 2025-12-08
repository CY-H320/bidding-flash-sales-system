# Load Testing - Bidding Flash Sale System

## 🎯 Purpose

Test your bidding system's performance under high load (1000+ concurrent users).

## 🚀 Quick Start

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


## 📊 Success Criteria

Your system is production-ready when it achieves:

✅ **1000+ concurrent users**
✅ **< 500ms response time (P95)**
✅ **< 1% failure rate**
✅ **> 400 requests/second**
✅ **Sustained for 10+ minutes**

## 🔧 After Backend Fixes

The backend has been optimized with:
- ✅ PostgreSQL UPSERT (eliminates race conditions)
- ✅ WebSocket broadcast disabled (stops UI glitching)
- ✅ Connection pool increased to 50/100
- ✅ Redis caching for session parameters
- ✅ Database indexes added
- ✅ Print statements removed

**You should now see:**
- < 1% failure rate (was 38%)
- < 500ms response time (was 9.2 seconds)
- 400+ req/s throughput (was 80 req/s)
- Smooth leaderboard updates (was glitching)

## 📖 Full Documentation

See **[LOAD_TEST_GUIDE.md](LOAD_TEST_GUIDE.md)** for:
- Detailed explanation of the load test approach
- Comparison with failed attempts
- Performance optimization guide
- Troubleshooting tips

## 🎬 Example

```bash
cd load_test

# 1. Install dependencies
pip3 install -r requirements.txt

# 2. Run the test
./run_test.sh http://your-host 1000 100 5m

# 3. View results
# Opens automatically: results_TIMESTAMP/report.html
```

---

**Ready to test?** Run the script and watch your system handle 1000+ concurrent bidders! 🚀
