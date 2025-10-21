"""add hall field to users

Revision ID: add_hall_field_to_users
Revises: b8215c199082
Create Date: 2025-10-18 14:55:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_hall_field_to_users'
down_revision = 'b8215c199082'
branch_labels = None
depends_on = None

def upgrade():
    # Add hall column to users table
    op.add_column('users', sa.Column('hall', sa.String(20), nullable=True))

def downgrade():
    # Remove hall column from users table
    op.drop_column('users', 'hall')