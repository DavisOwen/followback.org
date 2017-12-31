from flask_wtf import Form
from wtforms import StringField, BooleanField, PasswordField, TextAreaField, IntegerField
from wtforms.validators import DataRequired, EqualTo, Length
from wtforms.widgets import TextInput
from wtforms.fields import Field
from .models import User, InstaUser
from .views import current_user

class TagListField(Field):
    widget = TextInput()
    
    def _value(self):
        if self.data:
            return u', '.join(self.data)
        else:
            return u''

    def process_formdata(self, valuelist):
        if valuelist:
            self.data = [x.strip() for x in valuelist[0].split(',')]
        else:
            self.data = []

class LoginForm(Form):
    username = StringField('username', 
                        validators=[DataRequired()])
    password = PasswordField('password', 
                            validators=[DataRequired()])
    remember_me = BooleanField('remember_me',
                                default=False)

    def validate(self):
        rv = Form.validate(self)
        if not rv:
            return False
        user = User.query.filter_by(
            username=self.username.data).first()
        if user is None:
            self.username.errors.append('Unknown username')
            return False
        if not user.check_password(self.password.data):
            self.password.errors.append('Invalid password')
            return False
        self.user = user
        return True

class BotForm(Form):
  insta_username = StringField('insta_username',
                                validators=[DataRequired()])
  insta_password = PasswordField('insta_password',
                                validators=[DataRequired()])
  pages = TagListField('pages',validators=[DataRequired()])

  likes_per_day = IntegerField('likes_per_day',
                                validators=[DataRequired()],
                                default=600)

  follows_per_day = IntegerField('follows_per_day',
                                validators=[DataRequired()],
                                default=400)

  make = BooleanField('make', default=False)

  new_user =  BooleanField('new_user',default=False)

  pk = StringField('pk')

  def validate(self):
    rv = Form.validate(self)
    if not rv:
        return False
    import requests
    req_string = "https://www.instagram.com/%s"
    user_info_string = "https://www.instagram.com/%s/?__a=1"
    req = requests.get(req_string % (self.insta_username.data))
    if req.status_code != 200:
        self.insta_username.errors.append('User %s does not exist' % self.insta_username.data)
        return False
    for page in self.pages.data:
       req = requests.get(req_string % (page))
       if req.status_code != 200:
           self.pages.errors.append('Page %s does not exist' % page) 
           return False
    req = requests.get(user_info_string % (self.insta_username.data))
    json = req.json()
    pk = json['user']['id']
    insta_user = InstaUser.query.filter_by(pk=pk).first()
    if insta_user is not None:
        if insta_user not in current_user.insta_users:
            self.insta_username.errors.append('Instagram Account %s already registered with another account' % (self.insta_username.data))
            return False
    else:
        self.new_user.data = True
    self.pk.data = pk
    return True

class CheckpointForm(Form):
    code = StringField('code',validators=[DataRequired()])
    password = PasswordField('password',validators=[DataRequired()])
    
class RegisterForm(Form):
    username = StringField('username', 
                            validators=[DataRequired()])
    password = PasswordField('password', 
                            validators=[DataRequired(), 
                            EqualTo('confirm_password', 
                            message='Passwords must match')])
    confirm_password = PasswordField('confirm_password', 
                                    validators=[DataRequired()])

    def validate(self):
        rv = Form.validate(self)
        if not rv:
            return False
        user = User.query.filter_by(
                username=self.username.data).first()
        if user is not None:
            self.username.errors.append('Username already in use. \
                                        Please choose another one.')
            return False
        return True

