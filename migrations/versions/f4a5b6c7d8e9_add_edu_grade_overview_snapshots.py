"""add edu grade overview snapshots

Revision ID: f4a5b6c7d8e9
Revises: f3c4d5e6a7b8
Create Date: 2026-07-15 13:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f4a5b6c7d8e9"
down_revision = "f3c4d5e6a7b8"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("edu_grade_snapshots") as batch_op:
        batch_op.add_column(sa.Column("refresh_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("jwxt_account_key", sa.String(length=64), nullable=True))
        batch_op.create_index(
            "ix_edu_grade_snapshots_user_refresh",
            ["user_id", "refresh_id"],
            unique=False,
        )
        batch_op.create_index(
            "ix_edu_grade_snapshots_user_account_fetched",
            ["user_id", "jwxt_account_key", "fetched_at"],
            unique=False,
        )

    op.create_table(
        "edu_grade_overview_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("refresh_id", sa.String(length=64), nullable=False),
        sa.Column("jwxt_account_key", sa.String(length=64), nullable=False),
        sa.Column("official_gpa", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("calculated_gpa", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "source IN ('official', 'calculated', 'unavailable')",
            name="ck_edu_grade_overview_source",
        ),
        sa.CheckConstraint(
            "official_gpa IS NULL OR (official_gpa >= 0 AND official_gpa <= 5)",
            name="ck_edu_grade_overview_official_range",
        ),
        sa.CheckConstraint(
            "calculated_gpa IS NULL OR (calculated_gpa >= 0 AND calculated_gpa <= 5)",
            name="ck_edu_grade_overview_calculated_range",
        ),
        sa.CheckConstraint(
            "(source = 'official' AND official_gpa IS NOT NULL) "
            "OR (source = 'calculated' AND calculated_gpa IS NOT NULL) "
            "OR (source = 'unavailable' AND official_gpa IS NULL AND calculated_gpa IS NULL)",
            name="ck_edu_grade_overview_source_value",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "refresh_id", name="uq_edu_grade_overview_user_refresh"),
    )
    op.create_index(
        "ix_edu_grade_overview_user_account_fetched",
        "edu_grade_overview_snapshots",
        ["user_id", "jwxt_account_key", "fetched_at"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_edu_grade_overview_user_account_fetched",
        table_name="edu_grade_overview_snapshots",
    )
    op.drop_table("edu_grade_overview_snapshots")
    with op.batch_alter_table("edu_grade_snapshots") as batch_op:
        batch_op.drop_index("ix_edu_grade_snapshots_user_account_fetched")
        batch_op.drop_index("ix_edu_grade_snapshots_user_refresh")
        batch_op.drop_column("jwxt_account_key")
        batch_op.drop_column("refresh_id")
