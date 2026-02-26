"""initial schema

Revision ID: 0001_initial
Revises: None
Create Date: 2026-02-26 00:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'invoices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(length=32), nullable=False),
        sa.Column('paperless_doc_id', sa.Integer(), nullable=False),
        sa.Column('paperless_created', sa.DateTime(), nullable=True),
        sa.Column('title', sa.Text(), nullable=True),
        sa.Column('vendor', sa.String(length=255), nullable=True),
        sa.Column('amount', sa.Numeric(12, 2), nullable=True),
        sa.Column('currency', sa.String(length=8), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('needs_review', sa.Boolean(), nullable=False),
        sa.Column('extracted_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('debug_json', sa.Text(), nullable=True),
        sa.Column('correspondent', sa.String(length=255), nullable=True),
        sa.Column('document_type', sa.String(length=255), nullable=True),
        sa.Column('ocr_text', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('paperless_doc_id', name='uq_invoices_paperless_doc_id'),
    )
    op.create_index(op.f('ix_invoices_paperless_doc_id'), 'invoices', ['paperless_doc_id'], unique=False)

    op.create_table(
        'manual_costs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(length=32), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('vendor', sa.String(length=255), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('currency', sa.String(length=8), nullable=False),
        sa.Column('category', sa.String(length=120), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('manual_costs')
    op.drop_index(op.f('ix_invoices_paperless_doc_id'), table_name='invoices')
    op.drop_table('invoices')
