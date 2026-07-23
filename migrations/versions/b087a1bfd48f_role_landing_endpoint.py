"""role landing endpoint

Revision ID: b087a1bfd48f
Revises: aef813582552
Create Date: 2026-07-23 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b087a1bfd48f'
down_revision = 'aef813582552'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'roles',
        sa.Column('landing_endpoint', sa.String(length=150), nullable=False, server_default='dashboards.view'),
    )


def downgrade():
    op.drop_column('roles', 'landing_endpoint')
