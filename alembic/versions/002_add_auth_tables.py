"""add auth tables"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "002_add_auth_tables"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("admin", "analyst", "viewer", name="user_roles"),
            server_default="viewer",
        ),
        sa.Column("api_key_hash", sa.String(length=128), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("failed_attempts", sa.Integer(), default=0),
        sa.Column("lock_until", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column(
            "action",
            sa.Enum("login", "scan", "export", "delete", "access", name="audit_actions"),
            nullable=False,
        ),
        sa.Column("resource", sa.String(length=500)),
        sa.Column("ip_address", sa.String(length=45)),
        sa.Column("user_agent", sa.String(length=500)),
        sa.Column("metadata", sa.JSON()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("audit_logs")
    op.drop_table("users")
