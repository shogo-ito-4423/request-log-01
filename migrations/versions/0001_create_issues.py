"""Create the initial issues schema."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "issues",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("priority", sa.String(10), nullable=False),
        sa.Column("assignee", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("status IN ('open', 'in_progress', 'done')", name="valid_status"),
        sa.CheckConstraint("priority IN ('low', 'medium', 'high')", name="valid_priority"),
        sa.CheckConstraint("length(trim(title)) BETWEEN 1 AND 200", name="valid_title"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("issues")
