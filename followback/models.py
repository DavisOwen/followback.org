from followback import db
from hashlib import md5
from flask_user import UserMixin

class User(db.Model,UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer(), primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    password = db.Column(db.String(120), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    datetime_created = db.Column(db.DateTime())
    insta_users = db.relationship('InstaUser')
    roles = db.relationship('Role')

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return unicode(self.id)

    def check_password(self,password):
        if self.password == password:
            return True
        else:
            return False
        
    def __repr__(self):
        return '<User %r>' % (self.username)

class Role(db.Model):
    __tablename__= 'roles'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(50), unique=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'))

class Followed(db.Model):
    __tablename__ = 'followed'
    id = db.Column(db.Integer(),primary_key=True)
    insta_user_id = db.Column(db.Integer(), db.ForeignKey('insta_users.id', ondelete='CASCADE'))
    pk = db.Column(db.String(120))

class MaxID(db.Model):
    __tablename__ = 'max_id'
    id = db.Column(db.Integer(), primary_key=True)
    insta_user_id = db.Column(db.Integer(), db.ForeignKey('insta_users.id', ondelete='CASCADE'))
    page = db.Column(db.String(120))
    max_id = db.Column(db.String(120))

class Whitelist(db.Model):
    __tablename__ = 'whitelists'
    id = db.Column(db.Integer(),primary_key=True)
    insta_user_id = db.Column(db.Integer(), db.ForeignKey('insta_users.id', ondelete='CASCADE'))
    pk = db.Column(db.String(120))

class InstaUser(db.Model):
    __tablename__ = 'insta_users'
    id = db.Column(db.Integer(),primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'))
    username = db.Column(db.String(120), index=True, unique=True)
    followed = db.relationship('Followed')
    max_id = db.relationship('MaxID')
    whitelist = db.relationship('Whitelist')
    bot_id = db.Column(db.String(120), index=True, unique=True)
