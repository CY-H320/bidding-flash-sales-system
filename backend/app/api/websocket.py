# app/api/websocket.py
from datetime import datetime, timezone
from typing import Dict, Set
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.redis import get_redis
from app.models.bid import BiddingSession
from app.models.product import BiddingProduct
from app.models.user import User

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
        print(
            f"✓ WebSocket connected to session {session_id}. Total connections: {len(self.active_connections[session_id])}"
        )

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


# Global connection managers
manager = ConnectionManager()
session_list_manager = ConnectionManager()


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
        await websocket.send_json({"type": "leaderboard_update", "data": leaderboard})

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


@router.websocket("/ws/sessions")
async def session_list_websocket(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_async_db),
):
    """
    WebSocket endpoint for real-time session list updates.
    """
    channel_id = "session_list"

    try:
        await session_list_manager.connect(websocket, channel_id)
        print("✓ Session list WebSocket connected")

        # Send initial session list data
        try:
            sessions = await get_all_sessions(db)
            print(f"✓ Fetched {len(sessions)} sessions")
            await websocket.send_json({"type": "session_list_update", "data": sessions})
            print("✓ Sent initial session list")
        except Exception as e:
            print(f"❌ Error fetching/sending initial sessions: {e}")
            import traceback

            traceback.print_exc()
            raise

        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        print("✓ Session list WebSocket disconnected normally")
        session_list_manager.disconnect(websocket, channel_id)
    except Exception as e:
        print(f"❌ Session list WebSocket error: {e}")
        import traceback

        traceback.print_exc()
        session_list_manager.disconnect(websocket, channel_id)


async def get_leaderboard_data(
    session_id: str, redis: Redis, db: AsyncSession, limit: int = 10
):
    """Fetch leaderboard data from Redis and database"""
    try:
        session_uuid = UUID(session_id)
    except ValueError:
        return {"session_id": session_id, "leaderboard": []}

    ranking_key = f"ranking:{session_id}"

    # Get top bidders from Redis
    top_bidders = await redis.zrevrange(ranking_key, 0, limit - 1, withscores=True)

    if not top_bidders:
        return {"session_id": session_id, "leaderboard": []}

    # Get inventory to determine winners
    result = await db.execute(
        select(BiddingSession.inventory).where(BiddingSession.id == session_uuid)
    )
    inventory = result.scalar_one_or_none()

    if inventory is None:
        return {"session_id": session_id, "leaderboard": []}

    leaderboard = []

    for rank, (user_id_str, score) in enumerate(top_bidders, start=1):
        user_id = UUID(user_id_str)

        # Get username
        user_result = await db.execute(select(User.username).where(User.id == user_id))
        username = user_result.scalar_one_or_none()

        # Get bid data from Redis
        bid_key = f"bid:{session_id}:{user_id}"
        bid_data = await redis.hgetall(bid_key)

        price = float(bid_data.get("price", 0)) if bid_data else 0

        leaderboard.append(
            {
                "user_id": str(user_id),
                "username": username or f"User {user_id}",
                "price": price,
                "score": round(score, 2),
                "rank": rank,
                "is_winner": (rank <= inventory),
            }
        )

    return {"session_id": session_id, "leaderboard": leaderboard}


async def broadcast_leaderboard_update(session_id: str, redis: Redis, db: AsyncSession):
    """
    Broadcast leaderboard update to all connected clients for a session.
    Call this function after a bid is placed.
    """
    leaderboard = await get_leaderboard_data(session_id, redis, db)
    await manager.broadcast_to_session(
        session_id, {"type": "leaderboard_update", "data": leaderboard}
    )


async def get_all_sessions(db: AsyncSession):
    """Fetch all sessions with correct status"""
    try:
        # Use naive datetime to match what's in the database
        now = datetime.now()

        result = await db.execute(
            select(
                BiddingSession.id.label("session_id"),
                BiddingProduct.id.label("product_id"),
                BiddingProduct.name,
                BiddingProduct.description,
                BiddingSession.upset_price,
                BiddingSession.inventory,
                BiddingSession.alpha,
                BiddingSession.beta,
                BiddingSession.gamma,
                BiddingSession.start_time,
                BiddingSession.end_time,
                BiddingSession.is_active,
            ).join(BiddingProduct, BiddingSession.product_id == BiddingProduct.id)
        )

        sessions = []
        for row in result:
            # Determine status based on is_active flag and end_time
            # Strip timezone info if present to compare apples to apples
            end_time = row.end_time
            if end_time.tzinfo is not None:
                end_time = end_time.replace(tzinfo=None)
            is_ended = not row.is_active or now > end_time

            sessions.append(
                {
                    "session_id": str(row.session_id),
                    "product_id": str(row.product_id),
                    "name": row.name,
                    "description": row.description,
                    "base_price": row.upset_price,
                    "inventory": row.inventory,
                    "alpha": row.alpha,
                    "beta": row.beta,
                    "gamma": row.gamma,
                    "start_time": row.start_time.isoformat(),
                    "end_time": row.end_time.isoformat(),
                    "is_active": row.is_active,
                    "status": "ended" if is_ended else "active",
                }
            )

        return sessions
    except Exception as e:
        print(f"❌ Error in get_all_sessions: {e}")
        import traceback

        traceback.print_exc()
        return []


async def broadcast_session_list_update(db: AsyncSession = None):
    """
    Broadcast session list update to all connected clients.
    Creates its own DB session to ensure fresh data.
    """
    # Create a fresh database session to get the latest data
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as fresh_db:
        sessions = await get_all_sessions(fresh_db)
        print(
            f"✓ Broadcasting session list update: {len(sessions)} sessions to {len(session_list_manager.active_connections.get('session_list', []))} connections"
        )
        await session_list_manager.broadcast_to_session(
            "session_list", {"type": "session_list_update", "data": sessions}
        )
