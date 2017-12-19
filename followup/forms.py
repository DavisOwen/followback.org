from flask_wtf import Form, Field
from wtforms import StringField, BooleanField, PasswordField, TextAreaField, IntegerField
from wtforms.validators import DataRequired, EqualTo, Length
from wtforms.widgets import TextInput
from .models import User

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

class EditForm(Form):
    username = StringField('username', 
                            validators=[DataRequired()])
    about_me = TextAreaField('about_me', 
                            validators=[Length(min=0, max=140)])

    def __init__(self, original_username, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)
        self.original_username = original_username

    def validate(self):
        rv = Form.validate(self)
        if not rv:
            return False
        if self.username.data == self.original_username:
            return True
        user = User.query.filter_by(username=self.username.data).first()
        if user is not None:
            self.username.errors.append('This username is already in use.\
                                        Please choose another one.')
            return False
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

  def validate(self):
    rv = Form.validate(self)
    if not rv:
        return False
    import requests
    req_string = "http://www.instagram.com/%s"
    for page in self.pages.data:
       req = requests.get(req_string % (page))
       if req.status_code != 200:
           self.pages.errors.append('Page %s does not exist' % page) 
           return False
    return True
    
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

