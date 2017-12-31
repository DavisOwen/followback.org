from sqlalchemy import *
from migrate import *


from migrate.changeset import schema
pre_meta = MetaData()
post_meta = MetaData()
roles = Table('roles', pre_meta,
    Column('id', INTEGER(display_width=11), primary_key=True, nullable=False),
    Column('name', VARCHAR(length=50)),
    Column('user_id', INTEGER(display_width=11)),
)

users = Table('users', post_meta,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('username', String(length=64)),
    Column('password', String(length=120)),
    Column('email', String(length=120)),
    Column('datetime_created', DateTime),
    Column('role', String(length=120)),
)


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    pre_meta.tables['roles'].drop()
    post_meta.tables['users'].columns['role'].create()


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    pre_meta.tables['roles'].create()
    post_meta.tables['users'].columns['role'].drop()
