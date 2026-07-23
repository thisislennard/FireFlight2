"""incidents flugbuch phase 9

Revision ID: 6fedb0635366
Revises: bfe16e421ba5
Create Date: 2026-07-23 20:59:39.745189

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '6fedb0635366'
down_revision = 'bfe16e421ba5'
branch_labels = None
depends_on = None


def upgrade():
    # Autogenerate schlug hier wieder das Droppen der DJI-Alttabellen vor -- bewusst nicht
    # übernommen, konsistent mit ad2f3b109171/f07570aabbd1/bfe16e421ba5.
    op.create_table('incidents',
    sa.Column('organization_id', sa.UUID(), nullable=False),
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('description', sa.String(length=2000), nullable=True),
    sa.Column('is_closed', sa.Boolean(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('flights',
    sa.Column('incident_id', sa.UUID(), nullable=False),
    sa.Column('pilot_id', sa.UUID(), nullable=True),
    sa.Column('camera_operator_id', sa.UUID(), nullable=True),
    sa.Column('drone_label', sa.String(length=150), nullable=True),
    sa.Column('battery_label', sa.String(length=150), nullable=True),
    sa.Column('purpose', sa.String(length=1000), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('start_lat', sa.Float(), nullable=True),
    sa.Column('start_lon', sa.Float(), nullable=True),
    sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('end_lat', sa.Float(), nullable=True),
    sa.Column('end_lon', sa.Float(), nullable=True),
    sa.Column('synced', sa.Boolean(), nullable=False),
    sa.Column('had_issues', sa.Boolean(), nullable=False),
    sa.Column('notes', sa.String(length=2000), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['camera_operator_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['incident_id'], ['incidents.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['pilot_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('flights')
    op.drop_table('incidents')
