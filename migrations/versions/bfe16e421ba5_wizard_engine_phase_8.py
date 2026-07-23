"""wizard engine phase 8

Revision ID: bfe16e421ba5
Revises: f07570aabbd1
Create Date: 2026-07-23 20:33:31.086983

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'bfe16e421ba5'
down_revision = 'f07570aabbd1'
branch_labels = None
depends_on = None


def upgrade():
    # Autogenerate schlug hier wieder das Droppen der DJI-Alttabellen vor -- bewusst nicht
    # übernommen, konsistent mit ad2f3b109171/f07570aabbd1.
    op.create_table('wizards',
    sa.Column('organization_id', sa.UUID(), nullable=False),
    sa.Column('key', sa.String(length=100), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('description', sa.String(length=500), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('key')
    )
    op.create_table('wizard_steps',
    sa.Column('wizard_id', sa.UUID(), nullable=False),
    sa.Column('step_type', sa.String(length=100), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['wizard_id'], ['wizards.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('wizard_steps')
    op.drop_table('wizards')
