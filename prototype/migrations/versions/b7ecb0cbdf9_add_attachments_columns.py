"""add attachments columns

Revision ID: b7ecb0cbdf9
Revises: 4751d750080d
Create Date: 2015-07-22 09:50:23.190603

"""

# revision identifiers, used by Alembic.
revision = 'b7ecb0cbdf9'
down_revision = '4751d750080d'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('case_data', sa.Column('attachments', postgresql.JSONB(), nullable=True))
    op.add_column('form_data', sa.Column('attachments', postgresql.JSONB(), nullable=True))
    op.add_column('form_error', sa.Column('attachments', postgresql.JSONB(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('form_error', 'attachments')
    op.drop_column('form_data', 'attachments')
    op.drop_column('case_data', 'attachments')
    ### end Alembic commands ###
