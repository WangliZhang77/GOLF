"""add finance_ledger

Revision ID: f8a2c1d4e5b6
Revises: e42909fa4cfc
Create Date: 2026-07-06 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f8a2c1d4e5b6"
down_revision: Union[str, None] = "e42909fa4cfc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "finance_ledger",
        sa.Column(
            "direction",
            sa.Enum("income", "expense", name="ledger_direction", native_enum=False, length=16),
            nullable=False,
        ),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=True),
        sa.Column("branch_id", sa.Integer(), nullable=True),
        sa.Column("activity_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("confirmed", "voided", "refunded", name="ledger_status", native_enum=False, length=16),
            nullable=False,
        ),
        sa.Column("is_paid", sa.Boolean(), nullable=False),
        sa.Column(
            "payment_method",
            sa.Enum("manual", "cash", "bank_transfer", name="payment_method", native_enum=False, length=16),
            nullable=False,
        ),
        sa.Column("void_reason", sa.String(length=512), nullable=True),
        sa.Column("voided_by", sa.Integer(), nullable=True),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reconciled", sa.Boolean(), nullable=False),
        sa.Column("reconciled_by", sa.Integer(), nullable=True),
        sa.Column("reconciled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refund_of_id", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["activity_id"], ["activities.id"]),
        sa.ForeignKeyConstraint(["branch_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"]),
        sa.ForeignKeyConstraint(["refund_of_id"], ["finance_ledger.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_finance_ledger_activity_id"), "finance_ledger", ["activity_id"], unique=False)
    op.create_index(op.f("ix_finance_ledger_branch_id"), "finance_ledger", ["branch_id"], unique=False)
    op.create_index(op.f("ix_finance_ledger_category"), "finance_ledger", ["category"], unique=False)
    op.create_index(op.f("ix_finance_ledger_direction"), "finance_ledger", ["direction"], unique=False)
    op.create_index(op.f("ix_finance_ledger_is_deleted"), "finance_ledger", ["is_deleted"], unique=False)
    op.create_index(op.f("ix_finance_ledger_member_id"), "finance_ledger", ["member_id"], unique=False)
    op.create_index(op.f("ix_finance_ledger_refund_of_id"), "finance_ledger", ["refund_of_id"], unique=False)
    op.create_index(op.f("ix_finance_ledger_status"), "finance_ledger", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_finance_ledger_status"), table_name="finance_ledger")
    op.drop_index(op.f("ix_finance_ledger_refund_of_id"), table_name="finance_ledger")
    op.drop_index(op.f("ix_finance_ledger_member_id"), table_name="finance_ledger")
    op.drop_index(op.f("ix_finance_ledger_is_deleted"), table_name="finance_ledger")
    op.drop_index(op.f("ix_finance_ledger_direction"), table_name="finance_ledger")
    op.drop_index(op.f("ix_finance_ledger_category"), table_name="finance_ledger")
    op.drop_index(op.f("ix_finance_ledger_branch_id"), table_name="finance_ledger")
    op.drop_index(op.f("ix_finance_ledger_activity_id"), table_name="finance_ledger")
    op.drop_table("finance_ledger")
