from followback import db
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), index=True, unique=True)
    password = db.Column(db.String(93))
    email = db.Column(db.String(254), index=True, unique=True)
    confirmed = db.Column(db.SmallInteger, default=False)
    datetime_created = db.Column(db.DateTime)
    insta_users = db.relationship('InstaUser')
    paypal_transactions = db.relationship('PaypalTransaction')
    role = db.Column(db.String(30))

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

    def set_password(self,password):
        self.password = generate_password_hash(password)

    def check_password(self,password):
        return check_password_hash(self.password,password)

    def get_role(self):
        return self.role

    def __repr__(self):
        return '<User %r>' % (self.username)

class Followed(db.Model):
    __tablename__ = 'followed'
    id = db.Column(db.Integer,primary_key=True)
    insta_user_id = db.Column(db.Integer, db.ForeignKey('insta_users.id', ondelete='CASCADE'))
    pk = db.Column(db.String(64))

class MaxID(db.Model):
    __tablename__ = 'max_id'
    id = db.Column(db.Integer, primary_key=True)
    insta_user_id = db.Column(db.Integer, db.ForeignKey('insta_users.id', ondelete='CASCADE'))
    page = db.Column(db.String(30))
    max_id = db.Column(db.String(64))

class Whitelist(db.Model):
    __tablename__ = 'whitelists'
    id = db.Column(db.Integer,primary_key=True)
    insta_user_id = db.Column(db.Integer, db.ForeignKey('insta_users.id', ondelete='CASCADE'))
    pk = db.Column(db.String(64))

class InstaUser(db.Model):
    __tablename__ = 'insta_users'
    id = db.Column(db.Integer,primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    username = db.Column(db.String(30), index=True, unique=True)
    pk = db.Column(db.String(64), index=True, unique=True)
    followed = db.relationship('Followed')
    max_id = db.relationship('MaxID')
    whitelist = db.relationship('Whitelist')
    bot_id = db.Column(db.String(64), index=True, unique=True)

class PaypalTransaction(db.Model):
    __tablename__ = 'paypal_transaction'
    id = db.Column(db.Integer,primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id',ondelete='CASCADE'))
    payer_email = db.Column(db.String(254))
    unix = db.Column(db.DateTime)
    last_name = db.Column(db.String(30))
    payment_date = db.Column(db.String(64))
    payment_gross = db.Column(db.Float)
    payment_fee = db.Column(db.Float)
    payment_net = db.Column(db.Float)
    payment_status = db.Column(db.String(30))
    txn_id = db.Column(db.String(64))
