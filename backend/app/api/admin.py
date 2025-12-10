# app/api/admin.py
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.database import get_async_db
from app.models.bid import BiddingSession
from app.models.product import BiddingProduct
from app.models.user import User
from app.schemas.admin import CombinedCreate, ProductCreate, SessionCreate

router = APIRouter()


async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to ensure current user is admin"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return current_user


@router.post("/products")
async def create_product(
    product_data: ProductCreate,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Create a new product (Admin only).

    Request body:
    {
        "name": "Limited Edition Sneakers",
        "description": "Nike Air Jordan 1 Retro High"
    }
    """

    # Create new product
    new_product = BiddingProduct(
        id=uuid4(),
        name=product_data.name,
        description=product_data.description,
        admin_id=current_user.id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(new_product)
    await db.commit()
    await db.refresh(new_product)

    return {
        "product_id": str(new_product.id),
        "name": new_product.name,
        "description": new_product.description,
        "message": "Product created successfully",
    }


@router.get("/products")
async def get_products(
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """
    List products created by the current admin.
    """
    result = await db.execute(
        select(BiddingProduct)
        .where(BiddingProduct.admin_id == current_user.id)
        .order_by(BiddingProduct.created_at.desc())
    )
    products = result.scalars().all()

    return [
        {
            "id": str(p.id),
            "name": p.name,
            "description": p.description,
            "created_at": p.created_at.isoformat(),
        }
        for p in products
    ]


@router.post("/sessions")
async def create_session(
    session_data: SessionCreate,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Create a new bidding session (Admin only).

    Request body:
    {
        "product_id": "uuid-here",
        "upset_price": 200.0,
        "inventory": 5,
        "alpha": 0.5,
        "beta": 1000.0,
        "gamma": 2.0,
        "duration_minutes": 60
    }
    """

    # Verify product exists
    result = await db.execute(
        select(BiddingProduct).where(BiddingProduct.id == session_data.product_id)
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    # Create session using UTC time
    # Start 1 minute in the past to avoid timezone conversion issues with PostgreSQL
    start_time = datetime.now(timezone.utc) - timedelta(minutes=1)
    end_time = start_time + timedelta(minutes=session_data.duration_minutes)

    new_session = BiddingSession(
        id=uuid4(),
        admin_id=current_user.id,
        product_id=session_data.product_id,
        upset_price=session_data.upset_price,
        inventory=session_data.inventory,
        alpha=session_data.alpha,
        beta=session_data.beta,
        gamma=session_data.gamma,
        start_time=start_time,
        end_time=end_time,
        duration=timedelta(minutes=session_data.duration_minutes),
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)

    # Broadcast session list update
    try:
        from app.api.websocket import broadcast_session_list_update

        print(f"🔔 Broadcasting new session creation: {new_session.id}")
        await broadcast_session_list_update()
        print(f"✓ Broadcast completed for session: {new_session.id}")
    except Exception as e:
        print(f"❌ WebSocket broadcast error: {e}")
        import traceback

        traceback.print_exc()

    return {
        "session_id": str(new_session.id),
        "product_id": str(new_session.product_id),
        "upset_price": new_session.upset_price,
        "inventory": new_session.inventory,
        "start_time": new_session.start_time.isoformat(),
        "end_time": new_session.end_time.isoformat(),
        "message": "Session created successfully",
    }


@router.post("/sessions/combined")
async def create_product_and_session(
    combined_data: CombinedCreate,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Create both product and session in one request (Admin only).
    This is what your frontend uses.

    Request body:
    {
        "name": "Limited Edition Sneakers",
        "description": "Nike Air Jordan 1",
        "upset_price": 200.0,
        "inventory": 5,
        "alpha": 0.5,
        "beta": 1000.0,
        "gamma": 2.0,
        "duration_minutes": 60
    }
    """

    # Create product
    new_product = BiddingProduct(
        id=uuid4(),
        name=combined_data.name,
        description=combined_data.description,
        admin_id=current_user.id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(new_product)
    await db.flush()  # Get the product ID

    # Create session using UTC time
    # Start 1 minute in the past to avoid timezone conversion issues with PostgreSQL
    start_time = datetime.now(timezone.utc) - timedelta(minutes=1)
    end_time = start_time + timedelta(minutes=combined_data.duration_minutes)

    print("🕒 Creating session with times:")
    print(f"   start_time: {start_time} (UTC)")
    print(f"   end_time: {end_time} (UTC)")
    print(f"   duration: {combined_data.duration_minutes} minutes")

    new_session = BiddingSession(
        id=uuid4(),
        admin_id=current_user.id,
        product_id=new_product.id,
        upset_price=combined_data.upset_price,
        inventory=combined_data.inventory,
        alpha=combined_data.alpha,
        beta=combined_data.beta,
        gamma=combined_data.gamma,
        start_time=start_time,
        end_time=end_time,
        duration=timedelta(minutes=combined_data.duration_minutes),
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(new_session)
    await db.commit()

    # Broadcast session list update
    try:
        from app.api.websocket import broadcast_session_list_update

        print(f"🔔 Broadcasting new product+session creation: {new_session.id}")
        await broadcast_session_list_update()
        print(f"✓ Broadcast completed for product+session: {new_session.id}")
    except Exception as e:
        print(f"❌ WebSocket broadcast error: {e}")
        import traceback

        traceback.print_exc()

    return {
        "product_id": str(new_product.id),
        "session_id": str(new_session.id),
        "name": new_product.name,
        "upset_price": new_session.upset_price,
        "inventory": new_session.inventory,
        "message": "Product and session created successfully",
    }


@router.put("/sessions/{session_id}/activate")
async def activate_session(
    session_id: str,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """Activate a bidding session (Admin only)"""

    result = await db.execute(
        select(BiddingSession).where(BiddingSession.id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    session.is_active = True
    session.updated_at = datetime.now(timezone.utc)

    await db.commit()

    # Broadcast session list update
    try:
        from app.api.websocket import broadcast_session_list_update

        await broadcast_session_list_update()
    except Exception as e:
        print(f"WebSocket broadcast error: {e}")

    return {"message": "Session activated", "session_id": str(session.id)}


@router.put("/sessions/{session_id}/deactivate")
async def deactivate_session(
    session_id: str,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """Deactivate a bidding session (Admin only)"""

    result = await db.execute(
        select(BiddingSession).where(BiddingSession.id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    session.is_active = False
    session.updated_at = datetime.now(timezone.utc)

    await db.commit()

    # Broadcast session list update
    try:
        from app.api.websocket import broadcast_session_list_update

        await broadcast_session_list_update()
    except Exception as e:
        print(f"WebSocket broadcast error: {e}")

    return {"message": "Session deactivated", "session_id": str(session.id)}


@router.get("/stats")
async def get_admin_stats(
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db),
):
    """Get system statistics (Admin only)"""

    from sqlalchemy import func

    from app.models.bid import BiddingSessionBid

    # Count users
    users_result = await db.execute(select(func.count(User.id)))
    total_users = users_result.scalar()

    # Count products
    products_result = await db.execute(select(func.count(BiddingProduct.id)))
    total_products = products_result.scalar()

    # Count active sessions
    sessions_result = await db.execute(
        select(func.count(BiddingSession.id)).where(BiddingSession.is_active)
    )
    active_sessions = sessions_result.scalar()

    # Count total bids
    bids_result = await db.execute(select(func.count(BiddingSessionBid.id)))
    total_bids = bids_result.scalar()

    return {
        "total_users": total_users,
        "total_products": total_products,
        "active_sessions": active_sessions,
        "total_bids": total_bids,
    }


@router.get("/pool-status")
async def get_pool_status(
    current_user: User = Depends(get_current_admin),
):
    """
    Get database connection pool status (Admin only).

    Useful for monitoring and diagnosing connection issues.
    """
    from app.core.pool_monitor import get_pool_status

    status = get_pool_status()

    # Calculate health score (0-100)
    utilization = (
        status["checked_out"] / status["total_capacity"]
        if status["total_capacity"] > 0
        else 0
    )
    health_score = 100 - (utilization * 100)

    # Determine health status
    if utilization < 0.5:
        health_status = "healthy"
    elif utilization < 0.75:
        health_status = "moderate"
    elif utilization < 0.9:
        health_status = "high"
    else:
        health_status = "critical"

    return {
        **status,
        "utilization_percent": round(utilization * 100, 1),
        "health_score": round(health_score, 1),
        "health_status": health_status,
    }
