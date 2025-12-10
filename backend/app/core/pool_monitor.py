# app/core/pool_monitor.py
"""Connection pool monitoring utilities"""

from app.core.database import engine


def get_pool_status() -> dict:
    """
    Get current connection pool status.

    Returns:
        Dictionary with pool statistics
    """
    pool = engine.pool

    return {
        "size": pool.size(),  # Current number of connections
        "checked_in": pool.checkedin(),  # Available connections
        "checked_out": pool.checkedout(),  # In-use connections
        "overflow": pool.overflow(),  # Overflow connections in use
        "total_capacity": pool.size() + getattr(pool, "_max_overflow", 0),
    }


def print_pool_status():
    """Print connection pool status to console"""
    status = get_pool_status()
    print(f"""
📊 Connection Pool Status:
   - Total connections: {status["size"]}
   - Available: {status["checked_in"]}
   - In use: {status["checked_out"]}
   - Overflow: {status["overflow"]}
   - Capacity: {status["total_capacity"]}
   - Utilization: {status["checked_out"]}/{status["total_capacity"]} ({status["checked_out"] / status["total_capacity"] * 100:.1f}%)
""")
