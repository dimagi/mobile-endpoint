"""additional pl_proxy functions

Revision ID: 35c779ce5aa6
Revises: 2413d6dd74a6
Create Date: 2015-10-15 15:11:17.752700

"""

# revision identifiers, used by Alembic.

revision = '35c779ce5aa6'
down_revision = '2413d6dd74a6'
branch_labels = None
depends_on = None

from alembic import op
import os
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


PROXY_FILES = [
    'proxy_fn_get_case_ids_modified_with_owner_since.sql',
    'proxy_fn_get_last_modified_dates.sql',
    'proxy_fn_get_indexed_case_ids.sql',
]

SHARD_FILES = []


def upgrade(engine_name):
    # Proxy files are executed on the SINGLE Proxy DB.
    files = PROXY_FILES if not engine_name else SHARD_FILES
    _execute_files('upgrade', files)


def downgrade(engine_name):
    files = PROXY_FILES if not engine_name else SHARD_FILES
    _execute_files('downgrade', files)


def _execute_files(folder, files):
    for file in files:
        op.execute(_get_sql_from_file(folder, file))


def _get_sql_from_file(folder, file):
    with open(os.path.join('sql', folder, file)) as f:
        return f.read()
