"""Add immutable ownership; historical records remain admin-managed."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("issues", sa.Column("owner_id", sa.String(100), nullable=True))


def downgrade():
    with op.batch_alter_table("issues") as batch:
        batch.drop_column("owner_id")
