"""add token_version to users

Revision ID: 003_add_token_version
Revises: 002_add_auth_tables.py
Create Date: 2025-02-01
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003_add_token_version'
down_revision = '002_add_auth_tables'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('users', sa.Column('token_version', sa.Integer(), nullable=False, server_default='0'))
    op.execute("UPDATE users SET token_version = 0")
    op.alter_column('users', 'token_version', server_default=None)


def downgrade() -> None:
    op.drop_column('users', 'token_version')
