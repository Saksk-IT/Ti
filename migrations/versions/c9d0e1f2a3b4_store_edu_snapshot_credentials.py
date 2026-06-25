"""store edu snapshot credentials

Revision ID: c9d0e1f2a3b4
Revises: c8d9e0f1a2b3
Create Date: 2026-06-25 16:45:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c9d0e1f2a3b4"
down_revision = "c8d9e0f1a2b3"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("edu_schedule_snapshots") as batch_op:
        batch_op.drop_constraint("uq_edu_schedule_snapshots_user_term", type_="unique")
        batch_op.add_column(sa.Column("jwxt_username_ciphertext", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("jwxt_password_ciphertext", sa.Text(), nullable=True))

    with op.batch_alter_table("edu_grade_snapshots") as batch_op:
        batch_op.drop_constraint("uq_edu_grade_snapshots_user_term", type_="unique")
        batch_op.add_column(sa.Column("jwxt_username_ciphertext", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("jwxt_password_ciphertext", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("edu_grade_snapshots") as batch_op:
        batch_op.drop_column("jwxt_password_ciphertext")
        batch_op.drop_column("jwxt_username_ciphertext")
        batch_op.create_unique_constraint(
            "uq_edu_grade_snapshots_user_term",
            ["user_id", "xnm", "xqm"],
        )

    with op.batch_alter_table("edu_schedule_snapshots") as batch_op:
        batch_op.drop_column("jwxt_password_ciphertext")
        batch_op.drop_column("jwxt_username_ciphertext")
        batch_op.create_unique_constraint(
            "uq_edu_schedule_snapshots_user_term",
            ["user_id", "xnm", "xqm"],
        )
