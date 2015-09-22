"""add version column to case table

Revision ID: 4751d750080d
Revises: 22ca179a7eb6
Create Date: 2015-07-20 17:43:16.325283

"""

# revision identifiers, used by Alembic.
revision = '4751d750080d'
down_revision = '22ca179a7eb6'

from alembic import op
import sqlalchemy as sa


def upgrade(engine_name):
    _upgrade()


def downgrade(engine_name):
    _downgrade()


def _upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('case_data', sa.Column('version', sa.Integer(), nullable=True))
    ### end Alembic commands ###


def _downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('case_data', 'version')
    ### end Alembic commands ###
