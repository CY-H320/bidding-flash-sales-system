# Bidding Flash Sale System

A high-performance bidding and flash sale system built with FastAPI, React, PostgreSQL, and Redis.

## Features

- **High-Performance Backend** - FastAPI with async/await support
- **Real-Time Bidding** - Redis-powered leaderboard and inventory management
- **Modern Frontend** - React with Tailwind CSS
- **Secure Authentication** - JWT-based user authentication
- **Database Management** - PostgreSQL with SQLAlchemy ORM and Alembic migrations
- **Caching Layer** - Redis for high-speed data access
- **Admin Dashboard** - Manage products and bidding sessions
- **User Weights** - Customizable scoring formula with user weights

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **PostgreSQL 15+** - Primary database
- **Redis** - Caching and real-time leaderboards
- **SQLAlchemy 2.0** - ORM
- **Alembic** - Database migrations
- **Pydantic** - Data validation
- **JWT** - Authentication

### Frontend
- **React 19** - UI framework
- **Tailwind CSS** - Styling
- **Lucide React** - Icons
- **React Scripts** - Build tooling

## System Requirements

- **Python 3.12+**
- **Node.js 16+** and **npm**
- **PostgreSQL 15+**
- **Redis 7+**
- **Docker & Docker Compose** (recommended)

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd bidding-flash-sale-system-backend
```

### 2. Environment Setup

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
# Application Settings
APP_NAME=Bidding Flash Sale System
DEBUG=True

# PostgreSQL Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=bidding-flash-sale-system

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# JWT Authentication
SECRET_KEY=your-secret-key-please-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS Settings
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]
```

### 3. Start Infrastructure Services

Using Docker Compose (recommended):

```bash
cd backend
docker-compose up -d
```

This will start:
- PostgreSQL on port 5432
- Redis on port 6379

### 4. Backend Setup

#### Install Python Dependencies

Using `uv` (recommended):

```bash
cd backend
uv sync
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

Or using `pip`:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

#### Run Database Migrations

```bash
# Create initial migration
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head
```

#### Load Test Data (Optional)

```bash
# Connect to PostgreSQL
psql -h localhost -U postgres -d bidding-flash-sale-system

# Run the SQL file
\i ../frontend/data_generate.sql
```

This creates:
- 11 test users (1 admin + 10 regular users)
- 5 products
- 5 bidding sessions
- Sample bids

**Test Credentials:**
- Admin: `admin` / `admin123`
- Users: `user1` to `user10` / `test123`

#### Start Backend Server

```bash
# Using the startup script
./start.sh

# Or directly with uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at:
- API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Alternative Docs: http://localhost:8000/redoc

### 5. Frontend Setup

In a new terminal:

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

Frontend will be available at: http://localhost:3000

## Project Structure

```
bidding-flash-sale-system-backend/
├── backend/                      # Backend application
│   ├── alembic/                 # Database migrations
│   │   ├── versions/           # Migration versions
│   │   └── env.py              # Alembic environment
│   ├── app/                     # Main application
│   │   ├── api/                # API routes
│   │   ├── core/               # Core configuration
│   │   │   ├── config.py      # App settings
│   │   │   ├── database.py    # Database connection
│   │   │   └── redis.py       # Redis connection
│   │   ├── db/                 # Database models
│   │   │   └── models.py      # SQLAlchemy models
│   │   ├── models/             # Pydantic models
│   │   ├── schemas/            # API schemas
│   │   ├── services/           # Business logic
│   │   └── main.py            # Application entry
│   ├── docker-compose.yml      # Docker services
│   ├── pyproject.toml          # Python dependencies
│   ├── requirements.txt        # Pip requirements
│   └── start.sh               # Startup script
├── frontend/                    # React frontend
│   ├── public/                 # Static files
│   ├── src/                    # Source code
│   │   ├── App.js             # Main app component
│   │   └── index.js           # Entry point
│   ├── data_generate.sql       # Test data SQL
│   └── package.json           # Node dependencies
├── .env.example                # Environment template
└── README.md                   # This file
```

## Database Schema

### Users
- `id` (UUID) - Primary key
- `username` (String) - Unique username
- `email` (String) - User email
- `password` (String) - Hashed password
- `is_admin` (Boolean) - Admin flag
- `weight` (Float) - User weight for scoring

### Bidding Products
- `id` (UUID) - Primary key
- `name` (String) - Product name
- `description` (Text) - Product description
- `admin_id` (UUID) - Creator admin

### Bidding Sessions
- `id` (UUID) - Primary key
- `product_id` (UUID) - Foreign key to products
- `admin_id` (UUID) - Creator admin
- `upset_price` (Float) - Starting price
- `final_price` (Float) - Final price (null until ended)
- `inventory` (Integer) - Available quantity
- `alpha`, `beta`, `gamma` (Float) - Scoring formula parameters
- `start_time`, `end_time` (DateTime) - Session timing
- `duration` (Interval) - Session duration
- `is_active` (Boolean) - Active status

### Bidding Session Bids
- `id` (UUID) - Primary key
- `session_id` (UUID) - Foreign key to sessions
- `user_id` (UUID) - Foreign key to users
- `bid_price` (Float) - Bid amount
- `bid_score` (Float) - Calculated score

### Bidding Session Rankings
- `id` (UUID) - Primary key
- `session_id` (UUID) - Foreign key to sessions
- `user_id` (UUID) - Foreign key to users
- `ranking` (Integer) - User ranking
- `bid_price` (Float) - Final bid
- `bid_score` (Float) - Final score
- `is_winner` (Boolean) - Winner flag

## API Endpoints

### Health Check
- `GET /` - Basic health check
- `GET /health` - Detailed health status (database + Redis)

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/register` - User registration

### Users
- `GET /api/users/me` - Get current user
- `PUT /api/users/me` - Update current user

### Products
- `GET /api/products` - List all products
- `POST /api/products` - Create product (admin only)
- `GET /api/products/{id}` - Get product details
- `PUT /api/products/{id}` - Update product (admin only)
- `DELETE /api/products/{id}` - Delete product (admin only)

### Bidding Sessions
- `GET /api/sessions` - List all sessions
- `POST /api/sessions` - Create session (admin only)
- `GET /api/sessions/{id}` - Get session details
- `GET /api/sessions/{id}/leaderboard` - Get real-time leaderboard
- `POST /api/sessions/{id}/bid` - Place a bid

## Development Commands

### Backend

```bash
# Start development server
uvicorn app.main:app --reload

# Create database migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# View migration history
alembic history

# Format code
ruff format .

# Lint code
ruff check .
```

### Frontend

```bash
# Start development server
npm start

# Build for production
npm run build

# Run tests
npm test

# Eject configuration (irreversible)
npm run eject
```

### Docker

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Remove all data
docker-compose down -v

# Restart a service
docker-compose restart redis
```

## Scoring Formula

The bidding score is calculated using:

```
score = alpha × bid_price + beta / (gamma + user_weight)
```

Where:
- `alpha` - Price weight coefficient
- `beta` - User weight coefficient
- `gamma` - User weight offset
- `user_weight` - Individual user weight

This formula allows admins to balance between bid price and user reputation/loyalty.

## Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_NAME` | Application name | Bidding Flash Sale System |
| `APP_VERSION` | Application version | 1.0.0 |
| `DEBUG` | Debug mode | True |
| `POSTGRES_USER` | PostgreSQL username | postgres |
| `POSTGRES_PASSWORD` | PostgreSQL password | postgres |
| `POSTGRES_HOST` | PostgreSQL host | localhost |
| `POSTGRES_PORT` | PostgreSQL port | 5432 |
| `POSTGRES_DB` | Database name | bidding-flash-sale-system |
| `REDIS_HOST` | Redis host | localhost |
| `REDIS_PORT` | Redis port | 6379 |
| `REDIS_DB` | Redis database index | 0 |
| `SECRET_KEY` | JWT secret key | (must change in production) |
| `ALGORITHM` | JWT algorithm | HS256 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiration | 30 |
| `BACKEND_CORS_ORIGINS` | Allowed CORS origins | ["http://localhost:3000"] |

## Troubleshooting

### Backend won't start

1. Check if PostgreSQL is running:
```bash
docker-compose ps
# or
pg_isready -h localhost -p 5432
```

2. Check if Redis is running:
```bash
redis-cli ping
```

3. Verify environment variables in `.env`

4. Check database migrations:
```bash
alembic current
alembic upgrade head
```

### Frontend won't start

1. Clear node modules and reinstall:
```bash
rm -rf node_modules package-lock.json
npm install
```

2. Check if backend is running on port 8000

3. Verify CORS settings in backend `.env`

### Database connection errors

1. Check credentials in `.env`
2. Ensure PostgreSQL is accepting connections
3. Try resetting the database:
```bash
docker-compose down -v
docker-compose up -d
alembic upgrade head
```

### Redis connection errors

1. Check Redis is running:
```bash
docker-compose ps redis
```

2. Verify Redis connection:
```bash
redis-cli -h localhost -p 6379 ping
```

## Production Deployment

### Security Checklist

- [ ] Change `SECRET_KEY` to a strong random value
- [ ] Set `DEBUG=False`
- [ ] Update `POSTGRES_PASSWORD` to a strong password
- [ ] Configure proper CORS origins
- [ ] Enable HTTPS
- [ ] Set up proper firewall rules
- [ ] Use environment-specific `.env` files
- [ ] Enable Redis authentication
- [ ] Set up database backups

### Recommended Setup

1. Use a reverse proxy (nginx/traefik)
2. Run services in separate containers
3. Use managed database services (AWS RDS, etc.)
4. Set up monitoring and logging
5. Configure auto-scaling for high traffic
6. Use CDN for frontend assets

## License

[Your License Here]

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and questions, please open an issue on GitHub.
