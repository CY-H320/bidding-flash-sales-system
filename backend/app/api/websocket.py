# app/api/websocket.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Set
from uuid import UUID
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json

from app.core.redis import get_redis
from app.core.database import get_async_db
from app.models.user import User
from app.models.bid import BiddingSession

router = APIRouter()

# Store active WebSocket connections per session
# Format: {session_id: {websocket1, websocket2, ...}}
active_connections: Dict[str, Set[WebSocket]] = {}


class ConnectionManager:
    """Manage WebSocket connections for real-time updates"""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept a new WebSocket connection for a session"""
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        self.active_connections[session_id].add(websocket)
        print(f"✓ WebSocket connected to session {session_id}. Total connections: {len(self.active_connections[session_id])}")

    def disconnect(self, websocket: WebSocket, session_id: str):
        """Remove a WebSocket connection"""
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        print(f"✓ WebSocket disconnected from session {session_id}")

    async def broadcast_to_session(self, session_id: str, message: dict):
        """Broadcast a message to all connections in a session"""
        if session_id not in self.active_connections:
            return

        disconnected = set()
        for connection in self.active_connections[session_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error sending to WebSocket: {e}")
                disconnected.add(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.active_connections[session_id].discard(connection)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_async_db),
):
    """
    WebSocket endpoint for real-time leaderboard updates.

    Clients connect to this endpoint with a session_id and receive
    real-time updates whenever the leaderboard changes.
    """
    await manager.connect(websocket, session_id)

    try:
        # Send initial leaderboard data
        leaderboard = await get_leaderboard_data(session_id, redis, db)
        await websocket.send_json({
            "type": "leaderboard_update",
            "data": leaderboard
        })

        # Keep connection alive and listen for messages
        while True:
            # Receive messages from client (e.g., ping/pong for keepalive)
            data = await websocket.receive_text()

            # Handle ping/pong
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket, session_id)


async def get_leaderboard_data(session_id: str, redis: Redis, db: AsyncSession, limit: int = 10):
    """Fetch leaderboard data from Redis and database"""
    try:
        session_uuid = UUID(session_id)
    except ValueError:
        return {"session_id": session_id, "leaderboard": []}

    ranking_key = f"ranking:{session_id}"

    # Get top bidders from Redis
    top_bidders = await redis.zrevrange(
        ranking_key,
        0,
        limit - 1,
        withscores=True
    )

    if not top_bidders:
        return {"session_id": session_id, "leaderboard": []}

    # Get inventory to determine winners
    result = await db.execute(
        select(BiddingSession.inventory).where(
            BiddingSession.id == session_uuid
        )
    )
    inventory = result.scalar_one_or_none()

    if inventory is None:
        return {"session_id": session_id, "leaderboard": []}

    leaderboard = []

    for rank, (user_id_str, score) in enumerate(top_bidders, start=1):
        user_id = UUID(user_id_str)

        # Get username
        user_result = await db.execute(
            select(User.username).where(User.id == user_id)
        )
        username = user_result.scalar_one_or_none()

        # Get bid data from Redis
        bid_key = f"bid:{session_id}:{user_id}"
        bid_data = await redis.hgetall(bid_key)

        price = float(bid_data.get("price", 0)) if bid_data else 0

        leaderboard.append({
            "user_id": str(user_id),
            "username": username or f"User {user_id}",
            "price": price,
            "score": round(score, 2),
            "rank": rank,
            "is_winner": (rank <= inventory)
        })

    return {"session_id": session_id, "leaderboard": leaderboard}


async def broadcast_leaderboard_update(session_id: str, redis: Redis, db: AsyncSession):
    """
    Broadcast leaderboard update to all connected clients for a session.
    Call this function after a bid is placed.
    """
    leaderboard = await get_leaderboard_data(session_id, redis, db)
    await manager.broadcast_to_session(session_id, {
        "type": "leaderboard_update",
        "data": leaderboard
    })
