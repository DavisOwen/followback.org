from followback import db

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.BigInteger(), primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    password = db.Column(db.String(120), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    datetime_created = db.Column(db.DateTime())
    insta_users = db.relationship('InstaUser')
    role = db.Column(db.String(120))

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

    def get_role(self):
        return self.role

    def __repr__(self):
        return '<User %r>' % (self.username)

class Followed(db.Model):
    __tablename__ = 'followed'
    id = db.Column(db.BigInteger(),primary_key=True)
    insta_user_id = db.Column(db.BigInteger(), db.ForeignKey('insta_users.id', ondelete='CASCADE'))
    pk = db.Column(db.String(120))

class MaxID(db.Model):
    __tablename__ = 'max_id'
    id = db.Column(db.BigInteger(), primary_key=True)
    insta_user_id = db.Column(db.BigInteger(), db.ForeignKey('insta_users.id', ondelete='CASCADE'))
    page = db.Column(db.String(120))
    max_id = db.Column(db.String(120))

class Whitelist(db.Model):
    __tablename__ = 'whitelists'
    id = db.Column(db.BigInteger(),primary_key=True)
    insta_user_id = db.Column(db.BigInteger(), db.ForeignKey('insta_users.id', ondelete='CASCADE'))
    pk = db.Column(db.String(120))

class InstaUser(db.Model):
    __tablename__ = 'insta_users'
    id = db.Column(db.BigInteger(),primary_key=True)
    user_id = db.Column(db.BigInteger(), db.ForeignKey('users.id', ondelete='CASCADE'))
    username = db.Column(db.String(120), index=True, unique=True)
    pk = db.Column(db.String(120), index=True, unique=True)
    followed = db.relationship('Followed')
    max_id = db.relationship('MaxID')
    whitelist = db.relationship('Whitelist')
    bot_id = db.Column(db.String(120), index=True, unique=True)
    state = db.Column(db.String(120))
    likes = db.Column(db.BigInteger()) 
    follows = db.Column(db.BigInteger()) 
    start_time = db.Column(db.DateTime())
    end_time = db.Column(db.DateTime())
