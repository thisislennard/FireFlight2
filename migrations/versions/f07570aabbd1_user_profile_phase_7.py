"""user profile phase 7

Revision ID: f07570aabbd1
Revises: c610af27d089
Create Date: 2026-07-23 19:57:09.891374

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f07570aabbd1'
down_revision = 'c610af27d089'
branch_labels = None
depends_on = None


def upgrade():
    # Autogenerate schlug hier zusätzlich vor, integration_configs/external_references/
    # integration_sync_runs zu droppen (Altlast aus der entfernten DJI-FlightHub-2-Integration, s.
    # docs/roadmap.md "Zwischenschritt"). Bewusst NICHT übernommen -- konsistent mit derselben
    # Entscheidung in ad2f3b109171 (Notifications-Kern).
    op.add_column('users', sa.Column('is_pilot', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('users', sa.Column('is_camera_operator', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('users', sa.Column('phone_number', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('profile_image_filename', sa.String(length=255), nullable=True))


def downgrade():
    op.drop_column('users', 'profile_image_filename')
    op.drop_column('users', 'phone_number')
    op.drop_column('users', 'is_camera_operator')
    op.drop_column('users', 'is_pilot')
