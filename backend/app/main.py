# app/main.py
import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Import API routers
from app.api import bid

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

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
    import asyncio

    from app.core.redis import redis_client
    from app.tasks.batch_persist import start_batch_persist_background_task
    from app.tasks.session_monitor import session_monitor_task

    # Connect to Redis on startup
    try:
        await redis_client.connect()
        print("✓ Redis connected")
    except Exception as e:
        print(f"⚠ Redis connection failed: {e}")

    # Start session monitor background task
    monitor_task = asyncio.create_task(session_monitor_task())
    print("✓ Session monitor started")

    # Start batch persist background task (every 5 seconds)
    batch_persist_task = asyncio.create_task(
        start_batch_persist_background_task(batch_interval=5)
    )
    print("✓ Batch persist task started (interval: 5s)")

    print("✓ Application started")
    yield

    # Cancel background tasks
    monitor_task.cancel()
    batch_persist_task.cancel()
    try:
        await monitor_task
    except asyncio.CancelledError:
        print("✓ Session monitor stopped")
    try:
        await batch_persist_task
    except asyncio.CancelledError:
        print("✓ Batch persist task stopped")

    # Disconnect from Redis on shutdown
    try:
        await redis_client.disconnect()
        print("✓ Redis disconnected")
    except Exception as e:
        print(f"⚠ Redis disconnect failed: {e}")

    print("✓ Application shutdown")


# Create FastAPI app
import os

app = FastAPI(
    title="Bidding Flash Sale System API",
    description="Real-time bidding system with WebSocket support",
    version="1.0.0",
    lifespan=lifespan,
    debug=os.getenv("DEBUG", "False").lower() == "true",
)

# CORS middleware (allow frontend to connect)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React development server
        "http://localhost:3001",  # Alternative port
        "http://127.0.0.1:3000",
        "*",  # Allow all origins for development (remove in production)
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


# Global exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler to log and return detailed errors"""
    logger.error(f"Unhandled exception: {exc}")
    logger.error(f"Request: {request.method} {request.url}")
    logger.error(f"Traceback: {traceback.format_exc()}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": str(exc),
            "type": type(exc).__name__,
            "traceback": traceback.format_exc().split("\n") if app.debug else None,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors with detailed info"""
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "body": exc.body if hasattr(exc, "body") else None,
        },
    )


@app.get("/")
async def root():
    """Root endpoint - health check"""
    return {
        "message": "Bidding Flash Sale System API",
        "status": "running",
        "version": "1.0.0",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/metrics/pool")
async def pool_metrics():
    """
    Monitor connection pool status.
    Useful for debugging connection pool exhaustion during load tests.
    """
    from app.core.database import engine

    pool = engine.pool

    return {
        "pool_size": pool.size(),
        "checked_in_connections": pool.checkedin(),
        "checked_out_connections": pool.checkedout(),
        "overflow_connections": pool.overflow(),
        "total_connections": pool.size() + pool.overflow(),
        "queue_size": pool._queue.qsize() if hasattr(pool._queue, 'qsize') else 0,
        "status": "healthy" if pool.checkedout() < (pool.size() + pool.overflow()) else "exhausted"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
