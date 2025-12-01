from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import bid
from app.core import close_db, init_db, redis_client, settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Backend lifespan management"""
    print("Starting application...")
    await redis_client.connect()
    print("Redis connected")
    await init_db()
    print("Database initialized")
    yield

    print("Shutting down application...")
    await redis_client.disconnect()
    print("Redis disconnected")
    await close_db()
    print("Database closed")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(bid.router, prefix="/api/v1")


@app.get("/")
async def read_root():
    """Root endpoint"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    redis_status = await redis_client.ping()

    return {
        "status": "healthy",
        "database": "connected",
        "redis": "connected" if redis_status else "disconnected",
    }
