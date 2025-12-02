# Bidding Flash Sale System - Quick Start Guide

Complete guide to get your bidding system up and running in 5 minutes!

## 📋 Prerequisites

- Python 3.12+
- Node.js 16+
- PostgreSQL 15+
- Redis 7+
- Docker (optional)

## 🚀 Quick Start (3 Steps)

### Step 1: Start Backend Services

**Option A: Using Docker (Recommended)**
```bash
# Fix Docker if needed (restart Docker Desktop)
killall Docker && open /Applications/Docker.app
# Wait 15 seconds

# Start PostgreSQL and Redis
docker-compose up -d

# Verify services are running
docker ps
```

**Option B: Using Local Services**
```bash
# If you have PostgreSQL and Redis installed via Homebrew
brew services start postgresql@15
brew services start redis
```

### Step 2: Initialize and Start Backend

```bash
# Install Python dependencies
pip install -r requirements.txt

# Initialize database
python init_db.py

# Start backend server
python -m app.main
```

Backend will run on: **http://localhost:8000**
API Docs: **http://localhost:8000/docs**

### Step 3: Start Frontend

```bash
# In a new terminal
cd frontend
npm install
npm start
```

Frontend will run on: **http://localhost:3000**

## 🎮 Using the System

### For Regular Users

1. **Register:**
   - Open http://localhost:3000
   - Click "Register"
   - Enter username, email, password
   - Login automatically after registration

2. **Place Bids:**
   - View available products in sidebar
   - Click a product to select it
   - Enter your bid amount (must be >= base price)
   - Click "Submit Bid"
   - Watch your rank on the leaderboard!

3. **View Leaderboard:**
   - Updates automatically every 3 seconds
   - Green "Winner 🎉" badge for top K bidders
   - Shows your current rank and score

### For Admins

1. **Register as Admin:**
   - Click "Register"
   - Check ✅ "Login as Admin"
   - Enter credentials
   - Login

2. **Create Products:**
   - Fill in product details:
     - Name (e.g., "iPhone 15 Pro")
     - Description
     - Inventory (K) - number of winners
     - Base Price - minimum bid
     - Duration - session length in minutes
   - Set scoring parameters:
     - α (alpha) - Price weight (default: 0.5)
     - β (beta) - Time bonus (default: 1000)
     - γ (gamma) - User weight multiplier (default: 2.0)
   - Click "Create Product"

3. **Monitor:**
   - View all created products
   - Refresh to see latest status

## 📊 Understanding the Scoring System

**Formula:**
```
Score = α × Price + β / (ResponseTime + 1) + γ × UserWeight
```

**Example:**
- User bids $250
- Response time: 5 seconds after session start
- User weight: 1.5
- Parameters: α=0.5, β=1000, γ=2.0

```
Score = 0.5 × 250 + 1000 / (5 + 1) + 2.0 × 1.5
      = 125 + 166.67 + 3.0
      = 294.67
```

**What this means:**
- **Higher bids = Higher score** (price component)
- **Earlier bids = Higher score** (time bonus)
- **User reputation matters** (weight component)

## 🧪 Test the System

### Quick Test Scenario

**Terminal 1 - Backend:**
```bash
python -m app.main
```

**Terminal 2 - Frontend:**
```bash
cd frontend && npm start
```

**Browser:**

1. **Create Admin User:**
   - Register with admin checkbox
   - Login

2. **Create Test Product:**
   ```
   Name: Test iPhone
   Inventory: 3
   Base Price: 100
   Duration: 5 minutes
   α=0.5, β=1000, γ=2.0
   ```

3. **Create Multiple Users:**
   - Open incognito windows
   - Register users: user1, user2, user3
   - Each user places different bids

4. **Watch Competition:**
   - User1 bids $150 immediately → High time bonus
   - User2 bids $200 after 10s → Higher price, lower time bonus
   - User3 bids $180 after 5s → Balanced
   - Leaderboard updates in real-time

## 📡 API Testing (Optional)

**Using curl:**

```bash
# Register user
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "email": "test@example.com", "password": "test123"}'

# Login (save the token)
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "test123"}'

# Get active sessions
curl http://localhost:8000/api/sessions/active

# Submit bid (use your token)
curl -X POST http://localhost:8000/api/bid \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "SESSION_UUID", "price": 250.0}'

# View leaderboard
curl http://localhost:8000/api/leaderboard/SESSION_UUID
```

## 🔧 Troubleshooting

### Backend Issues

**"ModuleNotFoundError":**
```bash
# Activate virtual environment
source .venv/bin/activate
pip install -r requirements.txt
```

**"could not connect to server" (PostgreSQL):**
```bash
# Check PostgreSQL is running
pg_isready
# Or restart it
brew services restart postgresql@15
```

**"Redis connection failed":**
```bash
# Check Redis is running
redis-cli ping
# Should return: PONG
# Or restart it
brew services restart redis
```

### Frontend Issues

**"Connection error":**
- Ensure backend is running on port 8000
- Check: http://localhost:8000/health

**Dependencies issues:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**Port 3000 in use:**
```bash
# Kill process on port 3000
lsof -ti:3000 | xargs kill -9
npm start
```

## 📁 Project Structure

```
bidding-flash-sale-system-backend/
├── app/
│   ├── api/              # API endpoints
│   │   ├── auth.py      # Authentication
│   │   ├── admin.py     # Admin panel
│   │   └── bid.py       # Bidding logic
│   ├── core/            # Core functionality
│   │   ├── config.py    # Settings
│   │   ├── database.py  # PostgreSQL
│   │   └── redis.py     # Redis client
│   ├── models/          # Database models
│   ├── schemas/         # Pydantic schemas
│   └── services/        # Business logic
├── frontend/            # React app
│   └── src/
│       └── App.js      # Main component
├── docker-compose.yml   # Docker services
├── init_db.py          # Database setup
├── start.sh            # Quick start script
└── requirements.txt    # Python dependencies
```

## 🎯 Next Steps

1. **Customize Scoring:**
   - Adjust α, β, γ parameters
   - Test different scenarios

2. **Add Features:**
   - Email notifications
   - Payment processing
   - User profiles
   - Bid history

3. **Deploy:**
   - Set up production environment
   - Configure environment variables
   - Enable SSL/HTTPS
   - Set up monitoring

## 📚 Documentation

- **Backend API:** http://localhost:8000/docs
- **Setup Guide:** [SETUP.md](SETUP.md)
- **Frontend Integration:** [frontend/INTEGRATION.md](frontend/INTEGRATION.md)

## 🆘 Need Help?

- Check API documentation at http://localhost:8000/docs
- Review error messages in terminal
- Check browser console for frontend errors
- Ensure all services are running

## 🎉 Success!

You should now have:
- ✅ Backend running on port 8000
- ✅ Frontend running on port 3000
- ✅ PostgreSQL storing data
- ✅ Redis managing leaderboards
- ✅ Complete bidding system working!

Happy bidding! 🚀
