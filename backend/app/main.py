# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Import API routers
from app.api import bid
# Import new auth and admin routers
try:
    from app.api import auth
    has_auth = True
except ImportError:
    has_auth = False
    print("Warning: auth router not found")

try:
    from app.api import admin
    has_admin = True
except ImportError:
    has_admin = False
    print("Warning: admin router not found")

try:
    from app.api import websocket
    has_websocket = True
except ImportError:
    has_websocket = False
    print("Warning: websocket router not found")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown events for FastAPI application.
    """
    from app.core.redis import redis_client

    # Connect to Redis on startup
    try:
        await redis_client.connect()
        print("✓ Redis connected")
    except Exception as e:
        print(f"⚠ Redis connection failed: {e}")

    print("✓ Application started")
    yield

    # Disconnect from Redis on shutdown
    try:
        await redis_client.disconnect()
        print("✓ Redis disconnected")
    except Exception as e:
        print(f"⚠ Redis disconnect failed: {e}")

    print("✓ Application shutdown")


# Create FastAPI app
app = FastAPI(
    title="Bidding Flash Sale System API",
    description="Real-time bidding system with WebSocket support",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware (allow frontend to connect)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React development server
        "http://localhost:3001",  # Alternative port
        "http://127.0.0.1:3000",
        "*"  # Allow all origins for development (remove in production)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include API routers
app.include_router(bid.router, prefix="/api", tags=["Bidding"])

if has_auth:
    app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])

if has_admin:
    app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])

if has_websocket:
    app.include_router(websocket.router, tags=["WebSocket"])


@app.get("/")
async def root():
    """Root endpoint - health check"""
    return {
        "message": "Bidding Flash Sale System API",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )