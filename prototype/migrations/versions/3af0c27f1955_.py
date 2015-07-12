"""empty message

Revision ID: 3af0c27f1955
Revises: None
Create Date: 2015-07-09 14:51:16.000495

"""

# revision identifiers, used by Alembic.
revision = '3af0c27f1955'
down_revision = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('case_data',
    sa.Column('id', postgresql.UUID(), nullable=False),
    sa.Column('domain', sa.Text(), nullable=False),
    sa.Column('closed', sa.Boolean(), nullable=False),
    sa.Column('owner_id', postgresql.UUID(), nullable=False),
    sa.Column('server_modified_on', sa.DateTime(), nullable=False),
    sa.Column('case_json', postgresql.JSONB(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_case_data_domain_closed_modified', 'case_data', ['domain', 'closed', 'server_modified_on'], unique=False)
    op.create_index('ix_case_data_domain_owner', 'case_data', ['domain', 'owner_id'], unique=False)
    op.create_table('form_data',
    sa.Column('id', postgresql.UUID(), nullable=False),
    sa.Column('domain', sa.Text(), nullable=False),
    sa.Column('received_on', sa.DateTime(), nullable=False),
    sa.Column('user_id', postgresql.UUID(), nullable=False),
    sa.Column('md5', sa.LargeBinary(), nullable=False),
    sa.Column('form_json', postgresql.JSONB(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_form_data_domain'), 'form_data', ['domain'], unique=False)
    op.create_table('synclog',
    sa.Column('id', postgresql.UUID(), nullable=False),
    sa.Column('user_id', postgresql.UUID(), nullable=False),
    sa.Column('previous_log_id', postgresql.UUID(), nullable=True),
    sa.Column('hash', sa.Text(), nullable=False),
    sa.Column('owner_ids_on_phone', postgresql.ARRAY(postgresql.UUID()), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('case_form',
    sa.Column('case_id', postgresql.UUID(), nullable=False),
    sa.Column('form_id', postgresql.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['case_id'], ['case_data.id'], ),
    sa.ForeignKeyConstraint(['form_id'], ['form_data.id'], ),
    sa.PrimaryKeyConstraint('case_id', 'form_id')
    )
    op.create_table('case_index',
    sa.Column('case_id', postgresql.UUID(), nullable=False),
    sa.Column('domain', sa.Text(), nullable=False),
    sa.Column('identifier', sa.Text(), nullable=False),
    sa.Column('referenced_id', postgresql.UUID(), nullable=True),
    sa.Column('referenced_type', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['case_id'], ['case_data.id'], ),
    sa.ForeignKeyConstraint(['referenced_id'], ['case_data.id'], ),
    sa.PrimaryKeyConstraint('case_id', 'identifier')
    )
    op.create_index('ix_case_index_referenced_id', 'case_index', ['domain', 'referenced_id'], unique=False)
    op.create_table('form_error',
    sa.Column('id', postgresql.UUID(), nullable=False),
    sa.Column('domain', sa.Text(), nullable=False),
    sa.Column('received_on', sa.DateTime(), nullable=False),
    sa.Column('user_id', postgresql.UUID(), nullable=False),
    sa.Column('md5', sa.LargeBinary(), nullable=False),
    sa.Column('type', sa.Integer(), nullable=False),
    sa.Column('duplicate_id', postgresql.UUID(), nullable=True),
    sa.Column('form_json', postgresql.JSONB(), nullable=False),
    sa.ForeignKeyConstraint(['duplicate_id'], ['form_data.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_form_error_domain'), 'form_error', ['domain'], unique=False)
    op.create_table('synclog_cases',
    sa.Column('synclog_id', postgresql.UUID(), nullable=False),
    sa.Column('case_id', postgresql.UUID(), nullable=False),
    sa.Column('is_dependent', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['synclog_id'], ['synclog.id'], ),
    sa.PrimaryKeyConstraint('synclog_id')
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('synclog_cases')
    op.drop_index(op.f('ix_form_error_domain'), table_name='form_error')
    op.drop_table('form_error')
    op.drop_index('ix_case_index_referenced_id', table_name='case_index')
    op.drop_table('case_index')
    op.drop_table('case_form')
    op.drop_table('synclog')
    op.drop_index(op.f('ix_form_data_domain'), table_name='form_data')
    op.drop_table('form_data')
    op.drop_index('ix_case_data_domain_owner', table_name='case_data')
    op.drop_index('ix_case_data_domain_closed_modified', table_name='case_data')
    op.drop_table('case_data')
    ### end Alembic commands ###
