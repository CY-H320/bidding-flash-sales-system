# Bidding Flash Sale System - Backend Setup Guide

## Prerequisites

- Python 3.12+
- PostgreSQL 15+
- Redis 7+
- Docker (optional, for containerized setup)

## Setup Options

### Option 1: Using Docker (Recommended)

1. **Fix Docker Desktop** if you're getting API errors:
   ```bash
   # Restart Docker Desktop
   killall Docker && open /Applications/Docker.app
   # Wait 10-15 seconds for it to fully restart
   ```

2. **Start services:**
   ```bash
   docker-compose up -d
   ```

3. **Verify services are running:**
   ```bash
   docker ps
   # Should show: postgres and redis containers
   ```

### Option 2: Using Homebrew (Local Installation)

1. **Install services:**
   ```bash
   brew install postgresql@15 redis
   ```

2. **Start services:**
   ```bash
   brew services start postgresql@15
   brew services start redis
   ```

3. **Create database:**
   ```bash
   createdb bidding-flash-sale-system
   ```

4. **Update `.env` file** to use your local credentials:
   ```env
   POSTGRES_USER=your_username
   POSTGRES_PASSWORD=
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_DB=bidding-flash-sale-system

   REDIS_HOST=localhost
   REDIS_PORT=6379
   ```

## Backend Setup

1. **Install Python dependencies:**
   ```bash
   # Using uv (recommended)
   uv pip install -r requirements.txt

   # Or using pip
   pip install -r requirements.txt
   ```

2. **Create `.env` file** (if not exists):
   ```bash
   cp .env.example .env  # If you have an example file
   # Or create manually with the settings below
   ```

   Required `.env` settings:
   ```env
   # Database
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=postgres
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_DB=bidding-flash-sale-system

   # Redis
   REDIS_HOST=localhost
   REDIS_PORT=6379
   REDIS_DB=0

   # JWT
   JWT_SECRET=your-secret-key-change-this-in-production
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=1440

   # App
   DEBUG=True
   ```

3. **Initialize database:**
   ```bash
   python init_db.py
   ```

   Expected output:
   ```
   Initializing database...
   ✅ Database tables created successfully!

   Testing Redis connection...
   ✅ Redis connection successful!
   ```

4. **Run the server:**
   ```bash
   python -m app.main
   # Or with the virtual environment
   .venv/bin/python -m app.main
   ```

5. **Test the API:**
   ```bash
   # Health check
   curl http://localhost:8000/health

   # API documentation
   open http://localhost:8000/docs
   ```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get JWT token
- `GET /api/auth/me` - Get current user info (requires auth)

### Admin (requires admin role)
- `POST /api/admin/products` - Create product
- `POST /api/admin/sessions` - Create bidding session
- `POST /api/admin/sessions/combined` - Create product + session
- `PUT /api/admin/sessions/{id}/activate` - Activate session
- `PUT /api/admin/sessions/{id}/deactivate` - Deactivate session
- `GET /api/admin/stats` - Get system statistics

### Bidding (requires authentication)
- `POST /api/bid` - Submit or update a bid
- `GET /api/leaderboard/{session_id}` - Get real-time leaderboard
- `GET /api/sessions/active` - Get all active sessions

## Quick Test Flow

1. **Register an admin user:**
   ```bash
   curl -X POST http://localhost:8000/api/auth/register \
     -H "Content-Type: application/json" \
     -d '{
       "username": "admin",
       "email": "admin@test.com",
       "password": "admin123"
     }'
   ```

   Save the `token` from the response.

2. **Create a bidding session:**
   ```bash
   curl -X POST http://localhost:8000/api/admin/sessions/combined \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "iPhone 15 Pro",
       "description": "Limited Edition",
       "upset_price": 200.0,
       "inventory": 5,
       "alpha": 0.5,
       "beta": 1000.0,
       "gamma": 2.0,
       "duration_minutes": 60
     }'
   ```

   Save the `session_id` from the response.

3. **Get active sessions:**
   ```bash
   curl http://localhost:8000/api/sessions/active
   ```

4. **Register regular users and submit bids:**
   ```bash
   # Register user
   curl -X POST http://localhost:8000/api/auth/register \
     -H "Content-Type: application/json" \
     -d '{
       "username": "user1",
       "email": "user1@test.com",
       "password": "test123"
     }'

   # Submit bid (use the token from registration)
   curl -X POST http://localhost:8000/api/bid \
     -H "Authorization: Bearer USER_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "session_id": "SESSION_UUID",
       "price": 250.0
     }'
   ```

5. **View leaderboard:**
   ```bash
   curl http://localhost:8000/api/leaderboard/SESSION_UUID
   ```

## Troubleshooting

### Docker Issues
- **Error: "request returned 500 Internal Server Error"**
  - Solution: Restart Docker Desktop and try again
  - Alternative: Use local PostgreSQL/Redis (Option 2 above)

### Database Connection Issues
- **Error: "could not connect to server"**
  - Check PostgreSQL is running: `pg_isready` or `docker ps`
  - Verify credentials in `.env` file
  - Check port 5432 is not in use: `lsof -i :5432`

### Redis Connection Issues
- **Error: "Redis connection failed"**
  - Check Redis is running: `redis-cli ping` or `docker ps`
  - Verify Redis host/port in `.env`
  - Check port 6379 is not in use: `lsof -i :6379`

### Import Errors
- **Error: "ModuleNotFoundError"**
  - Ensure virtual environment is activated
  - Reinstall dependencies: `pip install -r requirements.txt`

## Architecture

**Bidding Score Formula:**
```
Score = α × Price + β / (ResponseTime + 1) + γ × UserWeight
```

- **α (alpha)**: Price weight factor (default: 0.5)
- **β (beta)**: Time weight factor (default: 1000.0)
- **γ (gamma)**: User weight factor (default: 2.0)

**Data Flow:**
1. User submits bid → FastAPI endpoint
2. Bid validation (session active, price >= upset_price)
3. Score calculation with user weight
4. Update Redis leaderboard (sorted set)
5. Persist to PostgreSQL
6. Return current rank and score

**Redis Data Structures:**
- `ranking:{session_id}` - Sorted set for leaderboard
- `bid:{session_id}:{user_id}` - Hash for bid details
- `session:params:{session_id}` - Hash for session parameters
- `user:weight:{user_id}` - String for user weight cache

## Next Steps

- [ ] Set up WebSocket support for real-time updates
- [ ] Add automated session expiration
- [ ] Implement winner notification system
- [ ] Add rate limiting
- [ ] Set up monitoring and logging
- [ ] Configure production environment
