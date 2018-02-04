from sqlalchemy import *
from migrate import *


from migrate.changeset import schema
pre_meta = MetaData()
post_meta = MetaData()
users = Table('users', pre_meta,
    Column('id', INTEGER(display_width=11), primary_key=True, nullable=False),
    Column('username', VARCHAR(length=30)),
    Column('password', VARCHAR(length=93)),
    Column('email', VARCHAR(length=254)),
    Column('confirmed', SMALLINT(display_width=6)),
    Column('datetime_created', DATETIME),
    Column('role', VARCHAR(length=30)),
)

users = Table('users', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('username', String(length=30)),
    Column('password', String(length=93)),
    Column('email', String(length=254)),
    Column('confirmed', SmallInteger, default=ColumnDefault(False)),
    Column('datetime_created', DateTime),
    Column('plan', String(length=30)),
    Column('purchased', SmallInteger, default=ColumnDefault(False)),
)


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    pre_meta.tables['users'].columns['role'].drop()
    post_meta.tables['users'].columns['plan'].create()
    post_meta.tables['users'].columns['purchased'].create()


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    pre_meta.tables['users'].columns['role'].create()
    post_meta.tables['users'].columns['plan'].drop()
    post_meta.tables['users'].columns['purchased'].drop()
