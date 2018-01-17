from sqlalchemy import *
from migrate import *


from migrate.changeset import schema
pre_meta = MetaData()
post_meta = MetaData()
paypal_transaction = Table('paypal_transaction', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('user_id', Integer),
    Column('payer_email', String(length=254)),
    Column('unix', DateTime),
    Column('last_name', String(length=30)),
    Column('payment_date', String(length=64)),
    Column('payment_gross', Float),
    Column('payment_fee', Float),
    Column('payment_net', Float),
    Column('payment_status', String(length=30)),
    Column('txn_id', String(length=64)),
    Column('subscr_id', String(length=64)),
)


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    post_meta.tables['paypal_transaction'].columns['subscr_id'].create()


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    post_meta.tables['paypal_transaction'].columns['subscr_id'].drop()
