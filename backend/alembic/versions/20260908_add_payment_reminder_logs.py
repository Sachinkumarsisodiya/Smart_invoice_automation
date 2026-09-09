"""add payment reminder logs table

Revision ID: 2b8f9e0a1234
Revises: 11ff6c16e59c
Create Date: 2026-09-08 06:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import app.database.base


# revision identifiers, used by Alembic.
revision: str = '2b8f9e0a1234'
down_revision: Union[str, None] = '11ff6c16e59c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'payment_reminder_logs',
        sa.Column('id', app.database.base.GUID(length=36), nullable=False),
        sa.Column('invoice_id', app.database.base.GUID(length=36), nullable=False),
        sa.Column('reminder_type', sa.String(length=50), nullable=False),
        sa.Column('reminder_date', sa.Date(), nullable=False),
        sa.Column('recipient_email', sa.String(length=255), nullable=False),
        sa.Column('channel', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('invoice_id', 'reminder_type', 'reminder_date', name='uq_invoice_reminder_type_date')
    )
    op.create_index('idx_reminder_invoice_date', 'payment_reminder_logs', ['invoice_id', 'reminder_date'], unique=False)
    op.create_index(op.f('ix_payment_reminder_logs_invoice_id'), 'payment_reminder_logs', ['invoice_id'], unique=False)
    op.create_index(op.f('ix_payment_reminder_logs_reminder_date'), 'payment_reminder_logs', ['reminder_date'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_payment_reminder_logs_reminder_date'), table_name='payment_reminder_logs')
    op.drop_index(op.f('ix_payment_reminder_logs_invoice_id'), table_name='payment_reminder_logs')
    op.drop_index('idx_reminder_invoice_date', table_name='payment_reminder_logs')
    op.drop_table('payment_reminder_logs')
