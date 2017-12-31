from sqlalchemy import *
from migrate import *


from migrate.changeset import schema
pre_meta = MetaData()
post_meta = MetaData()
insta_users = Table('insta_users', pre_meta,
    Column('id', BIGINT(display_width=20), primary_key=True, nullable=False),
    Column('user_id', BIGINT(display_width=20)),
    Column('username', VARCHAR(length=120)),
    Column('bot_id', VARCHAR(length=120)),
    Column('state', VARCHAR(length=120)),
    Column('likes', BIGINT(display_width=20)),
    Column('follows', BIGINT(display_width=20)),
    Column('start_time', DATETIME),
    Column('end_time', DATETIME),
    Column('pk', VARCHAR(length=120)),
)


def upgrade(migrate_engine):
    # Upgrade operations go here. Don't create your own engine; bind
    # migrate_engine to your metadata
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    pre_meta.tables['insta_users'].columns['end_time'].drop()
    pre_meta.tables['insta_users'].columns['follows'].drop()
    pre_meta.tables['insta_users'].columns['likes'].drop()
    pre_meta.tables['insta_users'].columns['start_time'].drop()
    pre_meta.tables['insta_users'].columns['state'].drop()


def downgrade(migrate_engine):
    # Operations to reverse the above upgrade go here.
    pre_meta.bind = migrate_engine
    post_meta.bind = migrate_engine
    pre_meta.tables['insta_users'].columns['end_time'].create()
    pre_meta.tables['insta_users'].columns['follows'].create()
    pre_meta.tables['insta_users'].columns['likes'].create()
    pre_meta.tables['insta_users'].columns['start_time'].create()
    pre_meta.tables['insta_users'].columns['state'].create()
