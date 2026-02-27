"""add invoice manual source flags

Revision ID: 0002_invoice_field_sources
Revises: 0001_initial
Create Date: 2026-02-27 00:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = '0002_invoice_field_sources'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('invoices', sa.Column('vendor_source', sa.String(length=16), nullable=False, server_default='auto'))
    op.add_column('invoices', sa.Column('amount_source', sa.String(length=16), nullable=False, server_default='auto'))
    op.execute("UPDATE invoices SET vendor_source='auto' WHERE vendor_source IS NULL OR vendor_source = ''")
    op.execute("UPDATE invoices SET amount_source='auto' WHERE amount_source IS NULL OR amount_source = ''")


def downgrade() -> None:
    op.drop_column('invoices', 'amount_source')
    op.drop_column('invoices', 'vendor_source')
