"""proxy setup

Revision ID: 448a844e393f
Revises: e1935c99018
Create Date: 2015-09-22 14:58:18.621661

"""

# revision identifiers, used by Alembic.
import os

revision = '448a844e393f'
down_revision = 'e1935c99018'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

extension_plproxy = 'CREATE EXTENSION IF NOT EXISTS plproxy'

def upgrade(engine_name):
    globals()["upgrade_%s" % engine_name]()


def downgrade(engine_name):
    globals()["downgrade_%s" % engine_name]()


def get_sql_from_file(file):
    with open(os.path.join('sql', file)) as f:
        return f.read()


def upgrade_():
    op.execute(extension_plproxy)
    # op.execute("DROP FOREIGN DATA WRAPPER IF EXISTS plproxy")
    # op.execute("CREATE FOREIGN DATA WRAPPER plproxy")
    op.execute("""
    CREATE SERVER hqcluster FOREIGN DATA WRAPPER plproxy
    OPTIONS (connection_lifetime '1800',
         p0 'dbname=receiver_01 host=127.0.0.1',
         p1 'dbname=receiver_02 host=127.0.0.1')
     """)
    op.execute("CREATE USER MAPPING FOR PUBLIC SERVER hqcluster")
    op.execute(get_sql_from_file('proxy_fn_get_case_by_id.sql'))
    op.execute(get_sql_from_file('proxy_fn_insert_case.sql'))


def downgrade_():
    pass


def upgrade_db02():
    op.execute(get_sql_from_file('fn_insert_case.sql'))


def downgrade_db02():
    pass


def upgrade_db01():
    op.execute(get_sql_from_file('fn_insert_case.sql'))


def downgrade_db01():
    pass

