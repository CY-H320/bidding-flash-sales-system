"""add_unique_constraint_on_bids

Revision ID: add_unique_constraint_bids
Revises: add_performance_indexes
Create Date: 2025-12-10

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_unique_constraint_bids"
down_revision: Union[str, None] = "add_performance_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add unique constraint on (session_id, user_id) for bidding_session_bids
    op.create_unique_constraint(
        "uq_bidding_session_bids_session_user",
        "bidding_session_bids",
        ["session_id", "user_id"],
    )


def downgrade() -> None:
    # Drop the unique constraint
    op.drop_constraint(
        "uq_bidding_session_bids_session_user", "bidding_session_bids", type_="unique"
    )
