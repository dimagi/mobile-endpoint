"""Add sharded model tables

Revision ID: 57e4ec05c2c2
Revises: 260e1f55c70
Create Date: 2015-09-24 14:49:54.422504

"""

# revision identifiers, used by Alembic.
from alembic.migration import MigrationContext
from alembic.operations import Operations
from flask import current_app
from sqlalchemy.dialects import postgresql

revision = '57e4ec05c2c2'
down_revision = '260e1f55c70'

from alembic import op
import sqlalchemy as sa
from sqlalchemy import engine_from_config, create_engine


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
            'case_data',
            sa.Column('id', postgresql.UUID(), autoincrement=False, nullable=False),
            sa.Column('shard_id', sa.SMALLINT(), autoincrement=False, nullable=False),
            sa.Column('domain', sa.TEXT(), autoincrement=False, nullable=False),
            sa.Column('closed', sa.BOOLEAN(), autoincrement=False, nullable=False),
            sa.Column('owner_id', postgresql.UUID(), autoincrement=False, nullable=False),
            sa.Column('server_modified_on', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
            sa.Column('case_json', postgresql.JSONB(), autoincrement=False, nullable=False),
            sa.Column('version', sa.INTEGER(), autoincrement=False, nullable=True),
            sa.Column('attachments', postgresql.JSONB(), autoincrement=False, nullable=True),
            sa.PrimaryKeyConstraint('id', name=u'case_data_pkey'),
            postgresql_ignore_search_path=False
        )
        op.create_table('case_index',
            sa.Column('case_id', postgresql.UUID(), autoincrement=False, nullable=False),
            sa.Column('shard_id', sa.SMALLINT(), autoincrement=False, nullable=False),
            sa.Column('domain', sa.TEXT(), autoincrement=False, nullable=False),
            sa.Column('identifier', sa.TEXT(), autoincrement=False, nullable=False),
            sa.Column('referenced_id', postgresql.UUID(), autoincrement=False, nullable=True),
            sa.Column('referenced_type', sa.TEXT(), autoincrement=False, nullable=False),
            # TODO: We should probably actually have foreign key on case_id, but haven't implemented that relationship yet.
            #sa.ForeignKeyConstraint(['case_id'], [u'case_data.id'], name=u'case_index_case_id_fkey'),
            #sa.ForeignKeyConstraint(['referenced_id'], [u'case_data.id'], name=u'case_index_referenced_id_fkey'),
            sa.PrimaryKeyConstraint('case_id', 'identifier', name=u'case_index_pkey')
        )


def downgrade():
    for op in get_shard_db_operations():
        op.drop_table('case_data')
        op.drop_table('case_index')

