"""optional user phone"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
revision='0002'
down_revision='0001'
branch_labels=None
depends_on=None
def upgrade():
    bind=op.get_bind()
    columns={c['name'] for c in inspect(bind).get_columns('telegram_users')}
    if 'phone_number' not in columns:
        op.add_column('telegram_users',sa.Column('phone_number',sa.String(32),nullable=True))
    indexes={i['name'] for i in inspect(bind).get_indexes('telegram_users')}
    if 'ix_telegram_users_phone_number' not in indexes:
        op.create_index('ix_telegram_users_phone_number','telegram_users',['phone_number'])
def downgrade():
    bind=op.get_bind()
    indexes={i['name'] for i in inspect(bind).get_indexes('telegram_users')}
    if 'ix_telegram_users_phone_number' in indexes:
        op.drop_index('ix_telegram_users_phone_number',table_name='telegram_users')
    columns={c['name'] for c in inspect(bind).get_columns('telegram_users')}
    if 'phone_number' in columns:
        op.drop_column('telegram_users','phone_number')
