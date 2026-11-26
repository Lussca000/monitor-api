"""Create monitors and monitor_checks tables with user_id relationship

Revision ID: 2_create_monitors_and_checks_tables
Revises: 1_create_users_table
Create Date: 2026-11-26 10:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2_create_monitors_and_checks_tables"
down_revision = "1_create_users_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create monitors table with user_id FK
    op.create_table(
        "monitors",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("interval_seconds", sa.Integer(), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("expected_status_code", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_monitors_user_id"), "monitors", ["user_id"], unique=False)
    
    # Create monitor_checks table
    op.create_table(
        "monitor_checks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("monitor_id", sa.Integer(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("response_time_ms", sa.Float(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_type", sa.String(50), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["monitor_id"], ["monitors.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_monitor_checks_monitor_id"), "monitor_checks", ["monitor_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_monitor_checks_monitor_id"), table_name="monitor_checks")
    op.drop_table("monitor_checks")
    op.drop_index(op.f("ix_monitors_user_id"), table_name="monitors")
    op.drop_table("monitors")
