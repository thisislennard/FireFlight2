"""pin login migration

Revision ID: eb781f84828e
Revises: b087a1bfd48f
Create Date: 2026-07-23 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'eb781f84828e'
down_revision = 'b087a1bfd48f'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('users', 'password_hash', new_column_name='pin_hash')
    op.add_column('users', sa.Column('must_change_pin', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('users', sa.Column('pin_set_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('lockout_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('last_lockout_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('requires_admin_unlock', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    op.drop_column('users', 'requires_admin_unlock')
    op.drop_column('users', 'last_lockout_at')
    op.drop_column('users', 'lockout_count')
    op.drop_column('users', 'pin_set_at')
    op.drop_column('users', 'must_change_pin')
    op.alter_column('users', 'pin_hash', new_column_name='password_hash')
