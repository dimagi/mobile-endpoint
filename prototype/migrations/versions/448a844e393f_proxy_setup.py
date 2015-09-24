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

NUM_CLUSTERS = 2**7
SHARDS_PER_SERVER = 2**7

def upgrade(engine_name):
    globals()["upgrade_%s" % engine_name]()


def downgrade(engine_name):
    globals()["downgrade_%s" % engine_name]()


def upgrade_():
    op.execute('CREATE EXTENSION IF NOT EXISTS plproxy')

    def get_db(server, shard):
        return '01' if server < (NUM_CLUSTERS /2) else '02'

    for server_id in range(NUM_CLUSTERS):
        partitions = [
            "p{shard} 'dbname=receiver_{db} host=127.0.0.1'".format(shard=shard, db=get_db(server_id, shard))
            for shard in range(SHARDS_PER_SERVER)
        ]
        sql = """
        CREATE SERVER cluster_{id} FOREIGN DATA WRAPPER plproxy
        OPTIONS (connection_lifetime '1800',
             {partitions}
        )
         """.format(id=server_id, partitions=',\n'.join(partitions))
        op.execute(sql)
        op.execute("CREATE USER MAPPING FOR PUBLIC SERVER cluster_{}".format(server_id))


def downgrade_():
    for server_id in range(NUM_CLUSTERS):
        op.execute("DROP USER MAPPING IF EXISTS FOR PUBLIC SERVER cluster_{}".format(server_id))
        op.execute("DROP SERVER IF EXISTS cluster_{}".format(server_id))
    op.execute('DROP EXTENSION IF EXISTS plproxy CASCADE')


def upgrade_db02():
    pass


def downgrade_db02():
    pass


def upgrade_db01():
    pass


def downgrade_db01():
    pass

