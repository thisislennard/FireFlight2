"""rc wizard flow phase 12

Revision ID: 49286e4006a0
Revises: 31acde4e81fe
Create Date: 2026-07-23 22:20:33.324780

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '49286e4006a0'
down_revision = '31acde4e81fe'
branch_labels = None
depends_on = None


def upgrade():
    # Autogenerate schlug hier wieder das Droppen der DJI-Alttabellen vor -- bewusst nicht
    # übernommen, konsistent mit ad2f3b109171/f07570aabbd1/bfe16e421ba5/6fedb0635366/31acde4e81fe.
    with op.batch_alter_table('flights', schema=None) as batch_op:
        batch_op.add_column(sa.Column('flight_status', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('start_requested_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('start_approved_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('start_approved_by_id', sa.UUID(), nullable=True))
        batch_op.create_foreign_key(None, 'users', ['start_approved_by_id'], ['id'])

    with op.batch_alter_table('wizard_steps', schema=None) as batch_op:
        batch_op.add_column(sa.Column('field_key', sa.String(length=100), nullable=True))


def downgrade():
    with op.batch_alter_table('wizard_steps', schema=None) as batch_op:
        batch_op.drop_column('field_key')

    with op.batch_alter_table('flights', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('start_approved_by_id')
        batch_op.drop_column('start_approved_at')
        batch_op.drop_column('start_requested_at')
        batch_op.drop_column('flight_status')
