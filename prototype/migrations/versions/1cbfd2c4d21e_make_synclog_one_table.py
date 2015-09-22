"""Make synclog into a single table

Revision ID: 1cbfd2c4d21e
Revises: 3af0c27f1955
Create Date: 2015-07-09 19:01:51.236741

"""

# revision identifiers, used by Alembic.
revision = '1cbfd2c4d21e'
down_revision = '3af0c27f1955'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade(engine_name):
    _upgrade()


def downgrade(engine_name):
    _downgrade()


def _upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('synclog_cases')
    op.add_column('form_data', sa.Column('synclog_id', postgresql.UUID(), nullable=True))
    op.create_foreign_key(None, 'form_data', 'synclog', ['synclog_id'], ['id'])
    op.add_column('synclog', sa.Column('case_ids_on_phone', postgresql.ARRAY(postgresql.UUID()), nullable=True))
    op.add_column('synclog', sa.Column('date', sa.DateTime(), nullable=False))
    op.add_column('synclog', sa.Column('dependent_case_ids_on_phone', postgresql.ARRAY(postgresql.UUID()), nullable=True))
    op.add_column('synclog', sa.Column('domain', sa.Text(), nullable=False))
    op.add_column('synclog', sa.Column('index_tree', postgresql.JSONB(), nullable=True))
    op.create_foreign_key(None, 'synclog', 'synclog', ['previous_log_id'], ['id'])
    ### end Alembic commands ###


def _downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'synclog', type_='foreignkey')
    op.drop_column('synclog', 'index_tree')
    op.drop_column('synclog', 'domain')
    op.drop_column('synclog', 'dependent_case_ids_on_phone')
    op.drop_column('synclog', 'date')
    op.drop_column('synclog', 'case_ids_on_phone')
    op.drop_constraint(None, 'form_data', type_='foreignkey')
    op.drop_column('form_data', 'synclog_id')
    op.create_table('synclog_cases',
    sa.Column('synclog_id', postgresql.UUID(), autoincrement=False, nullable=False),
    sa.Column('case_id', postgresql.UUID(), autoincrement=False, nullable=False),
    sa.Column('is_dependent', sa.BOOLEAN(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['synclog_id'], [u'synclog.id'], name=u'synclog_cases_synclog_id_fkey'),
    sa.PrimaryKeyConstraint('synclog_id', name=u'synclog_cases_pkey')
    )
    ### end Alembic commands ###
