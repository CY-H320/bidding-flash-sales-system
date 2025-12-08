"""Add performance indexes for bidding

Revision ID: add_performance_indexes
Revises:
Create Date: 2025-12-08

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'add_performance_indexes'
down_revision = None  # Update this if you have existing migrations
branch_labels = None
depends_on = None


def upgrade():
    """Add indexes to optimize bidding performance under high load"""

    # Index for finding user's bid in a session
    # Used in: SELECT ... WHERE session_id = X AND user_id = Y
    # Frequency: Every bid (1000+ times/sec during load test)
    op.create_index(
        'idx_bids_session_user',
        'bidding_session_bids',
        ['session_id', 'user_id'],
        unique=False
    )

    # Index for leaderboard queries (ordered by score)
    # Used in: SELECT ... WHERE session_id = X ORDER BY bid_score DESC
    # Frequency: Every leaderboard request
    op.create_index(
        'idx_bids_session_score',
        'bidding_session_bids',
        ['session_id', 'bid_score'],
        unique=False,
        postgresql_ops={'bid_score': 'DESC'}
    )

    # Index for active session lookups
    # Used in: SELECT ... WHERE is_active = true AND start_time < now < end_time
    # Frequency: Every bid (session validation)
    op.create_index(
        'idx_sessions_active_time',
        'bidding_sessions',
        ['is_active', 'start_time', 'end_time'],
        unique=False
    )

    # Index for session results/rankings
    # Used in: SELECT ... WHERE session_id = X ORDER BY ranking
    op.create_index(
        'idx_rankings_session',
        'bidding_session_rankings',
        ['session_id', 'ranking'],
        unique=False
    )


def downgrade():
    """Remove performance indexes"""
    op.drop_index('idx_rankings_session', table_name='bidding_session_rankings')
    op.drop_index('idx_sessions_active_time', table_name='bidding_sessions')
    op.drop_index('idx_bids_session_score', table_name='bidding_session_bids')
    op.drop_index('idx_bids_session_user', table_name='bidding_session_bids')
