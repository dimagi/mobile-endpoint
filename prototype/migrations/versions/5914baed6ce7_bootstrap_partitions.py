"""bootstrap partitions

Revision ID: 5914baed6ce7
Revises: 13687c89f352
Create Date: 2015-09-23 18:52:06.101172

"""

# revision identifiers, used by Alembic.
revision = '5914baed6ce7'
down_revision = '13687c89f352'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

from sqlalchemy.sql import table, column
from sqlalchemy import String, Integer, Text

# Create an ad-hoc table to use for the insert statement.
cluster = table(
    'cluster',
    column('name', Text),
    column('version', Integer)
)

physical_partition = table(
    'physical_partition',
    column('name', Text),
    column('cluster_name', Text),
    column('host', Text),
    column('port', Text),
    column('dbname', Text),
    # column('remote_user', Text),
    # column('password', Text),
)

logical_partition = table(
    'logical_partition',
    column('id', Integer),
    column('group', Integer),
    column('physical_partition', Text),
)


def upgrade(engine_name):
    if not engine_name:
        op.bulk_insert(cluster, [{'name': 'hqcluster', 'version': 1}])
        op.bulk_insert(physical_partition, [
            {'name': 'db01', 'cluster_name': 'hqcluster', 'host': 'localhost', 'port': '5432', 'dbname': 'receiver_01'},
            {'name': 'db02', 'cluster_name': 'hqcluster', 'host': 'localhost', 'port': '5432', 'dbname': 'receiver_02'}
        ])

        def group_id(partition):
            return partition % 100

        def physical_id(partition):
            return ['db01', 'db02'][partition % 2]

        partitions = [
            {'id': part_id, 'group': group_id(part_id), 'physical_partition': physical_id(part_id)}
            for part_id in range(2**10)
        ]
        op.bulk_insert(logical_partition, partitions)


def downgrade(engine_name):
    if not engine_name:
        op.execute('TRUNCATE TABLE logical_partition CASCADE')
        op.execute('TRUNCATE TABLE physical_partition CASCADE')
        op.execute('TRUNCATE TABLE cluster CASCADE')
