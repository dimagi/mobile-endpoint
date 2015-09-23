"""proxy setup

Revision ID: 448a844e393f
Revises: e0fe5591b30
Create Date: 2015-09-22 14:58:18.621661

"""

# revision identifiers, used by Alembic.
import os

revision = '448a844e393f'
down_revision = 'e0fe5591b30'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

def upgrade(engine_name):
    globals()["upgrade_%s" % engine_name]()


def downgrade(engine_name):
    globals()["downgrade_%s" % engine_name]()


def upgrade_():
    op.execute('CREATE EXTENSION IF NOT EXISTS plproxy')
    # op.execute("DROP FOREIGN DATA WRAPPER IF EXISTS plproxy")
    # op.execute("CREATE FOREIGN DATA WRAPPER plproxy")
    op.execute("""
    CREATE SERVER hqcluster FOREIGN DATA WRAPPER plproxy
    OPTIONS (connection_lifetime '1800',
         p0 'dbname=receiver_01 host=127.0.0.1',
         p1 'dbname=receiver_02 host=127.0.0.1')
     """)
    op.execute("CREATE USER MAPPING FOR PUBLIC SERVER hqcluster")


def downgrade_():
    op.execute("DROP USER MAPPING IF EXISTS FOR PUBLIC SERVER hqcluster")
    op.execute("DROP SERVER IF EXISTS hqcluster")
    op.execute('DROP EXTENSION IF EXISTS plproxy CASCADE')


def upgrade_db02():
    pass


def downgrade_db02():
    pass


def upgrade_db01():
    pass


def downgrade_db01():
    pass

