"""add origin and destination cities

Revision ID: 2a4432ffebc2
Revises: 
Create Date: 2026-10-20 06:47:46.589044

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2a4432ffebc2'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('loads', schema=None) as batch_op:
        batch_op.add_column(sa.Column('origin_city', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('origin_state', sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column('destination_city', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('destination_state', sa.String(length=10), nullable=True))
        batch_op.create_index(batch_op.f('ix_loads_extracted_at'), ['extracted_at'], unique=False)



def downgrade():
    with op.batch_alter_table('loads', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_loads_extracted_at'))
        batch_op.drop_column('destination_state')
        batch_op.drop_column('destination_city')
        batch_op.drop_column('origin_state')
        batch_op.drop_column('origin_city')
