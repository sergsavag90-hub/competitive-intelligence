"""add performance indexes

Revision ID: 004_add_indexes
Revises: 003_add_token_version
Create Date: 2025-02-01
"""

from alembic import op
import sqlalchemy as sa

revision = '004_add_indexes'
down_revision = '003_add_token_version'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable trigram for GIN indexes if available
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Competitors
    op.create_index(
        'idx_competitors_url',
        'competitors',
        ['url'],
        unique=True,
    )
    op.create_index(
        'idx_competitors_enabled',
        'competitors',
        ['enabled'],
    )

    # Products
    op.create_index(
        'idx_products_competitor_active',
        'products',
        ['competitor_id', 'is_active'],
        postgresql_where=sa.text('in_stock = true'),
    )
    op.create_index(
        'idx_products_name_trgm',
        'products',
        ['name'],
        postgresql_using='gin',
        postgresql_ops={'name': 'gin_trgm_ops'},
    )

    # Price history
    op.create_index(
        'idx_price_history_product_time',
        'price_history',
        ['product_id', 'recorded_at'],
    )

    # SEO data
    op.create_index(
        'idx_seo_data_competitor_date',
        'seo_data',
        ['competitor_id', 'collected_at'],
    )

    # Promotions
    op.create_index(
        'idx_promotions_competitor_active',
        'promotions',
        ['competitor_id', 'is_active'],
    )

    # Audit logs
    op.create_index(
        'idx_audit_logs_user_action',
        'audit_logs',
        ['user_id', 'action', 'created_at'],
    )


def downgrade() -> None:
    op.drop_index('idx_audit_logs_user_action', table_name='audit_logs')
    op.drop_index('idx_promotions_competitor_active', table_name='promotions')
    op.drop_index('idx_seo_data_competitor_date', table_name='seo_data')
    op.drop_index('idx_price_history_product_time', table_name='price_history')
    op.drop_index('idx_products_name_trgm', table_name='products')
    op.drop_index('idx_products_competitor_active', table_name='products')
    op.drop_index('idx_competitors_enabled', table_name='competitors')
    op.drop_index('idx_competitors_url', table_name='competitors')
