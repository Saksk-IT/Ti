"""add grade refresh order

Revision ID: f5b6c7d8e9f0
Revises: f4a5b6c7d8e9
Create Date: 2026-07-15 15:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f5b6c7d8e9f0"
down_revision = "f4a5b6c7d8e9"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("edu_grade_snapshots") as batch_op:
        batch_op.drop_index("ix_edu_grade_snapshots_user_account_fetched")
        batch_op.add_column(
            sa.Column(
                "refresh_order",
                sa.BigInteger(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.create_unique_constraint(
            "uq_edu_grade_snapshots_user_refresh_term",
            ["user_id", "refresh_id", "xnm", "xqm"],
        )
        batch_op.create_index(
            "ix_edu_grade_snapshots_user_account_fetched",
            ["user_id", "jwxt_account_key", "refresh_order", "fetched_at"],
            unique=False,
        )

    with op.batch_alter_table("edu_grade_overview_snapshots") as batch_op:
        batch_op.drop_index("ix_edu_grade_overview_user_account_fetched")
        batch_op.add_column(
            sa.Column(
                "refresh_order",
                sa.BigInteger(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.create_index(
            "ix_edu_grade_overview_user_account_fetched",
            ["user_id", "jwxt_account_key", "refresh_order", "fetched_at"],
            unique=False,
        )


def downgrade():
    with op.batch_alter_table("edu_grade_overview_snapshots") as batch_op:
        batch_op.drop_index("ix_edu_grade_overview_user_account_fetched")
        batch_op.drop_column("refresh_order")
        batch_op.create_index(
            "ix_edu_grade_overview_user_account_fetched",
            ["user_id", "jwxt_account_key", "fetched_at"],
            unique=False,
        )

    with op.batch_alter_table("edu_grade_snapshots") as batch_op:
        batch_op.drop_index("ix_edu_grade_snapshots_user_account_fetched")
        batch_op.drop_constraint(
            "uq_edu_grade_snapshots_user_refresh_term",
            type_="unique",
        )
        batch_op.drop_column("refresh_order")
        batch_op.create_index(
            "ix_edu_grade_snapshots_user_account_fetched",
            ["user_id", "jwxt_account_key", "fetched_at"],
            unique=False,
        )
