"""pl_proxy_functions

Revision ID: 2413d6dd74a6
Revises: 448a844e393f
Create Date: 2015-09-23 11:35:39.125325

"""

# revision identifiers, used by Alembic.
import os

revision = '2413d6dd74a6'
down_revision = '448a844e393f'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


PROXY_FILES = [
    'proxy_fn_get_case_by_id.sql',
    'proxy_fn_create_or_update_case.sql',
    'proxy_fn_insert_form.sql',
    'proxy_fn_get_form_by_id.sql',
    'proxy_fn_get_form_by_id.sql',
    'proxy_fn_create_or_update_case_indices.sql',
]

SHARD_FILES = [
    'fn_create_or_update_case.sql',
    'fn_insert_form.sql',
    'fn_create_or_update_case_indices.sql',
]


def upgrade(engine_name):
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
