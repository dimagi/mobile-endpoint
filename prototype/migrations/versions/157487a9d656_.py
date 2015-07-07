"""empty message

Revision ID: 157487a9d656
Revises: 1ab2e4176494
Create Date: 2015-07-03 14:54:02.241632

"""

# revision identifiers, used by Alembic.
revision = '157487a9d656'
down_revision = '1ab2e4176494'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('form_data', sa.Column('type', sa.Text(), nullable=True))
    op.drop_column('form_data', 'duplicate')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('form_data', sa.Column('duplicate', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.drop_column('form_data', 'type')
    ### end Alembic commands ###