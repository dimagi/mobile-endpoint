"""pl proxy config functions

Revision ID: 53abda089bce
Revises: 5914baed6ce7
Create Date: 2015-09-24 10:22:55.060471

"""

# revision identifiers, used by Alembic.
import os

revision = '53abda089bce'
down_revision = '5914baed6ce7'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


PROXY_FILES = [
    'proxy_fn_get_cluster_partitions.sql',
    'proxy_fn_get_cluster_version.sql',
]


def upgrade(engine_name):
    if not engine_name:
        _execute_files('upgrade', PROXY_FILES)

def downgrade(engine_name):
    if not engine_name:
        _execute_files('downgrade', PROXY_FILES)


def _execute_files(folder, files):
    for file in files:
        op.execute(_get_sql_from_file(folder, file))


def _get_sql_from_file(folder, file):
    with open(os.path.join('sql', folder, file)) as f:
        return f.read()
