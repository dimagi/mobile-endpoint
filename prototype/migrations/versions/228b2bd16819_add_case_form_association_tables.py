"""Add case/form association tables

Revision ID: 228b2bd16819
Revises: 57e4ec05c2c2
Create Date: 2015-10-01 10:47:12.130605

"""

# revision identifiers, used by Alembic.
revision = '228b2bd16819'
down_revision = '57e4ec05c2c2'

from alembic.migration import MigrationContext
from alembic.operations import Operations
from flask import current_app
from sqlalchemy.dialects import postgresql
from sqlalchemy import create_engine
import sqlalchemy as sa


# TODO: Share this function with other migrations!
def get_shard_db_operations():
    """
    Return an Operations instance for each db that hosts sharded models
    :return:
    """
    for db_name, uri in current_app.config.get('SHARDED_DATABASE_URIS').iteritems():
        engine = create_engine(uri)
        connection = engine.connect()
        context = MigrationContext.configure(connection)
        yield Operations(context)


def upgrade():
    for op in get_shard_db_operations():
        op.create_table(
            'case_form_association',
            sa.Column('case_id', postgresql.UUID(), autoincrement=False, nullable=False),
            sa.Column('shard_id', sa.SMALLINT(), autoincrement=False, nullable=False),
            sa.Column('form_id', postgresql.UUID(), autoincrement=False, nullable=False),
            postgresql_ignore_search_path=False
        )


def downgrade():
    for op in get_shard_db_operations():
        op.drop_table('case_form_association')
