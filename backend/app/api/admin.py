# app/api/admin.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Optional

from app.core.database import get_async_db
from app.models.user import User
from app.models.product import BiddingProduct
from app.models.bid import BiddingSession
from app.api.auth import get_current_user
from app.schemas.admin import ProductCreate, SessionCreate, CombinedCreate

router = APIRouter()


async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to ensure current user is admin"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


@router.post("/products")
async def create_product(
    product_data: ProductCreate,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
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
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(new_product)
    await db.commit()
    await db.refresh(new_product)
    
    return {
        "product_id": str(new_product.id),
        "name": new_product.name,
        "description": new_product.description,
        "message": "Product created successfully"
    }


@router.post("/sessions")
async def create_session(
    session_data: SessionCreate,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Create session
    start_time = datetime.utcnow()
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
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    
    return {
        "session_id": str(new_session.id),
        "product_id": str(new_session.product_id),
        "upset_price": new_session.upset_price,
        "inventory": new_session.inventory,
        "start_time": new_session.start_time.isoformat(),
        "end_time": new_session.end_time.isoformat(),
        "message": "Session created successfully"
    }


@router.post("/sessions/combined")
async def create_product_and_session(
    combined_data: CombinedCreate,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
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
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(new_product)
    await db.flush()  # Get the product ID
    
    # Create session
    start_time = datetime.utcnow()
    end_time = start_time + timedelta(minutes=combined_data.duration_minutes)

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
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(new_session)
    await db.commit()
    
    return {
        "product_id": str(new_product.id),
        "session_id": str(new_session.id),
        "name": new_product.name,
        "upset_price": new_session.upset_price,
        "inventory": new_session.inventory,
        "message": "Product and session created successfully"
    }


@router.put("/sessions/{session_id}/activate")
async def activate_session(
    session_id: str,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
):
    """Activate a bidding session (Admin only)"""
    
    result = await db.execute(
        select(BiddingSession).where(BiddingSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    session.is_active = True
    session.updated_at = datetime.utcnow()
    
    await db.commit()
    
    return {"message": "Session activated", "session_id": str(session.id)}


@router.put("/sessions/{session_id}/deactivate")
async def deactivate_session(
    session_id: str,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
):
    """Deactivate a bidding session (Admin only)"""
    
    result = await db.execute(
        select(BiddingSession).where(BiddingSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    session.is_active = False
    session.updated_at = datetime.utcnow()
    
    await db.commit()
    
    return {"message": "Session deactivated", "session_id": str(session.id)}


@router.get("/stats")
async def get_admin_stats(
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
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
        select(func.count(BiddingSession.id)).where(BiddingSession.is_active == True)
    )
    active_sessions = sessions_result.scalar()
    
    # Count total bids
    bids_result = await db.execute(select(func.count(BiddingSessionBid.id)))
    total_bids = bids_result.scalar()
    
    return {
        "total_users": total_users,
        "total_products": total_products,
        "active_sessions": active_sessions,
        "total_bids": total_bids
    }