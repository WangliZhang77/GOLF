"""add notifications

Revision ID: a9b3c2d1e4f5
Revises: f8a2c1d4e5b6
Create Date: 2026-07-06 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a9b3c2d1e4f5"
down_revision: Union[str, None] = "f8a2c1d4e5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("recipient_user_id", sa.Integer(), nullable=False),
        sa.Column(
            "message_type",
            sa.Enum(
                "activity_registered",
                "dues_reminder",
                "activity_reminder",
                "system",
                "score_published",
                name="message_type",
                native_enum=False,
                length=24,
            ),
            nullable=False,
        ),
        sa.Column("title_zh", sa.String(length=128), nullable=False),
        sa.Column("title_en", sa.String(length=128), nullable=False),
        sa.Column("body_zh", sa.Text(), nullable=False),
        sa.Column("body_en", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("related_member_id", sa.Integer(), nullable=True),
        sa.Column("related_activity_id", sa.Integer(), nullable=True),
        sa.Column("related_ledger_id", sa.Integer(), nullable=True),
        sa.Column("sent_by", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["related_activity_id"], ["activities.id"]),
        sa.ForeignKeyConstraint(["related_ledger_id"], ["finance_ledger.id"]),
        sa.ForeignKeyConstraint(["related_member_id"], ["members.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notifications_is_deleted"), "notifications", ["is_deleted"], unique=False)
    op.create_index(op.f("ix_notifications_message_type"), "notifications", ["message_type"], unique=False)
    op.create_index(op.f("ix_notifications_recipient_user_id"), "notifications", ["recipient_user_id"], unique=False)
    op.create_index(op.f("ix_notifications_related_activity_id"), "notifications", ["related_activity_id"], unique=False)
    op.create_index(op.f("ix_notifications_related_ledger_id"), "notifications", ["related_ledger_id"], unique=False)
    op.create_index(op.f("ix_notifications_related_member_id"), "notifications", ["related_member_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_notifications_related_member_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_related_ledger_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_related_activity_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_recipient_user_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_message_type"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_is_deleted"), table_name="notifications")
    op.drop_table("notifications")
