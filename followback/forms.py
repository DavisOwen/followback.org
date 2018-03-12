from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, PasswordField, TextAreaField, IntegerField, SelectField
from wtforms.validators import DataRequired, EqualTo, Length, Email
from wtforms.widgets import TextInput
from wtforms.fields import Field
from wtforms.fields.html5 import EmailField
from .models import User 
import string

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

class LoginForm(FlaskForm):
    username = StringField('username', 
                        validators=[DataRequired()])
    password = PasswordField('password', 
                            validators=[DataRequired()])
    remember_me = BooleanField('remember_me',
                                default=False)

    def validate(self):
        rv = FlaskForm.validate(self)
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

class RegisterInstaForm(FlaskForm):
    insta_username = StringField('insta_username',
                                validators=[DataRequired()])
    insta_password = PasswordField('insta_password',
                                validators=[DataRequired()])

    def validate(self):
        rv = FlaskForm.validate(self)
        if not rv:
            return False
        import requests
        req_string = "https://www.instagram.com/%s"
        req = requests.get(req_string % (self.insta_username.data))
        if req.status_code != 200:
            self.insta_username.errors.append('User %s does not exist' % self.insta_username.data)
            return False
        return True

class ChangeUsernameForm(FlaskForm):
    new_username = StringField('new_username',
                                validators=[DataRequired()])
    password = PasswordField('password',
                            validators=[DataRequired()])

    def __init__(self, user, *args, **kwargs):
        super(ChangeUsernameForm, self).__init__(*args, **kwargs)
        self.user = user

    def validate(self):
        rv = FlaskForm.validate(self)
        if not rv:
            return False
        new_user = User.query.filter_by(username=
                                        self.new_username.data).first()
        if new_user is not None:
            self.new_username.errors.append('Username %s already in use. \
                                            Please choose another one' % (self.new_username.data))
            return False
        if not self.user.check_password(self.password.data):
            self.password.errors.append('Invalid password')
            return False
        return True

class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('old_password',
                                validators=[DataRequired()])
    new_password = PasswordField('new_password',
                            validators=[DataRequired(),
                            EqualTo('new_password_confirm', 
                            message='Passwords must match')])
    new_password_confirm = PasswordField('new_password_confirm',
                            validators=[DataRequired()])

    def __init__(self, user, *args, **kwargs):
        super(ChangePasswordForm, self).__init__(*args, **kwargs)
        self.user = user

    def validate(self):
        rv = FlaskForm.validate(self)
        if not rv:
            return False
        if not self.user.check_password(self.old_password.data):
            self.password.errors.append('Invalid password')
            return False
        pw = self.new_password.data
        if len(pw) < 6:
            self.new_password.errors.append('Password must be\
                                        at least 6 characters,\
                                        contain upper and lower\
                                        case letters, and at least,\
                                        one number')
            return False
        elif len(set(string.ascii_lowercase).intersection(pw)) == 0:
            self.new_password.errors.append('Password must be\
                                        at least 6 characters,\
                                        contain upper and lower\
                                        case letters, and at least,\
                                        one number')
            return False
        elif len(set(string.ascii_uppercase).intersection(pw)) == 0:
            self.new_password.errors.append('Password must be\
                                        at least 6 characters,\
                                        contain upper and lower\
                                        case letters, and at least,\
                                        one number')
            return False
        elif len(set(string.digits).intersection(pw)) == 0:
            self.new_password.errors.append('Password must be\
                                        at least 6 characters,\
                                        contain upper and lower\
                                        case letters, and at least,\
                                        one number')
            return False
        return True

class ResetPasswordForm(FlaskForm):
    new_password = PasswordField('new_password',
                            validators=[DataRequired(),
                            EqualTo('new_password_confirm', 
                            message='Passwords must match')])
    new_password_confirm = PasswordField('new_password_confirm',
                            validators=[DataRequired()])

    def validate(self):
        rv = FlaskForm.validate(self)
        if not rv:
            return False
        pw = self.new_password.data
        if len(pw) < 6:
            self.new_password.errors.append('Password must be\
                                        at least 6 characters,\
                                        contain upper and lower\
                                        case letters, and at least,\
                                        one number')
            return False
        elif len(set(string.ascii_lowercase).intersection(pw)) == 0:
            self.new_password.errors.append('Password must be\
                                        at least 6 characters,\
                                        contain upper and lower\
                                        case letters, and at least,\
                                        one number')
            return False
        elif len(set(string.ascii_uppercase).intersection(pw)) == 0:
            self.new_password.errors.append('Password must be\
                                        at least 6 characters,\
                                        contain upper and lower\
                                        case letters, and at least,\
                                        one number')
            return False
        elif len(set(string.digits).intersection(pw)) == 0:
            self.new_password.errors.append('Password must be\
                                        at least 6 characters,\
                                        contain upper and lower\
                                        case letters, and at least,\
                                        one number')
            return False
        return True

class ForgotCredentialForm(FlaskForm):
    email = EmailField('email',
                        validators=[DataRequired(),Email()])

    def validate(self):
        rv = FlaskForm.validate(self)
        if not rv:
            return False
        email = User.query.filter_by(email=self.email.data).first()
        if email is None:
            self.email.errors.append("Email not associated with\
                                        any accounts")
            return False
        self.user = email
        return True

class AddWhitelistForm(FlaskForm):
    insta_username = SelectField('insta_username',
                                choices=list(),
                                validators=[DataRequired()])
    insta_password = PasswordField('insta_password',
                                    validators=[DataRequired()])

    users = TagListField('users')

    make = BooleanField('make', default=False)

    def __init__(self, insta_user_list, *args, **kwargs):
        super(AddWhitelistForm, self).__init__(*args, **kwargs)
        self.insta_username.choices = insta_user_list
    
    def validate(self):
        rv = FlaskForm.validate(self)
        if not rv:
            return False
        if self.users.data[0] == u'':
            self.users.errors.append('This field is required')
            return False
        import requests
        req_string = "https://www.instagram.com/%s"
        req = requests.get(req_string % (self.insta_username.data))
        if req.status_code != 200:
            self.insta_username.errors.append('User %s does not exist' % self.insta_username.data)
            return False
        for user in self.users.data:
           req = requests.get(req_string % (user))
           if req.status_code != 200:
               self.users.errors.append('User %s does not exist' % user) 
               return False
        return True

class UnfollowForm(FlaskForm):
    insta_username = SelectField('insta_username',
                                choices=list(),
                                validators=[DataRequired()])
    insta_password = PasswordField('insta_password',
                                validators=[DataRequired()])

    follows_per_day = IntegerField('follows_per_day',
                                validators=[DataRequired()],
                                default=400)

    use_whitelist = BooleanField('use_whitelist', default=True)

    def __init__(self, insta_user_list, *args, **kwargs):
        super(UnfollowForm, self).__init__(*args, **kwargs)
        self.insta_username.choices = insta_user_list

    def validate(self):
        rv = FlaskForm.validate(self)
        if not rv:
            return False
        import requests
        req_string = "https://www.instagram.com/%s"
        req = requests.get(req_string % (self.insta_username.data))
        if req.status_code != 200:
            self.insta_username.errors.append('User %s does not exist' % self.insta_username.data)
            return False
        return True

class BotForm(FlaskForm):
    insta_username = SelectField('insta_username',
                                choices=list(),
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

    use_whitelist = BooleanField('use_whitelist', default=True)

    def __init__(self, insta_user_list, *args, **kwargs):
        super(BotForm, self).__init__(*args, **kwargs)
        self.insta_username.choices=insta_user_list

    def validate(self):
        rv = FlaskForm.validate(self)
        if not rv:
            return False
        import requests
        req_string = "https://www.instagram.com/%s"
        req = requests.get(req_string % (self.insta_username.data))
        if req.status_code != 200:
            self.insta_username.errors.append('User %s does not exist' % self.insta_username.data)
            return False
        for page in self.pages.data:
           req = requests.get(req_string % (page))
           if req.status_code != 200:
               self.pages.errors.append('Page %s does not exist' % page) 
               return False
        return True

class CheckpointForm(FlaskForm):
    code = StringField('code',validators=[DataRequired()])
    password = PasswordField('password',validators=[DataRequired()])
    
class RegisterForm(FlaskForm):
    username = StringField('username', 
                            validators=[DataRequired()])
    password = PasswordField('password', 
                            validators=[DataRequired(), 
                            EqualTo('confirm_password', 
                            message='Passwords must match')])
    confirm_password = PasswordField('confirm_password', 
                                    validators=[DataRequired()])
    email = EmailField('email',
                        validators=[DataRequired(),Email()])

    def validate(self):
        rv = FlaskForm.validate(self)
        if not rv:
            return False
        pw = self.password.data
        if len(pw) < 6:
            self.password.errors.append('Password must be\
                                        at least 6 characters,\
                                        contain upper and lower\
                                        case letters, and at least,\
                                        one number')
            return False
        elif len(set(string.ascii_lowercase).intersection(pw)) == 0:
            self.password.errors.append('Password must be\
                                        at least 6 characters,\
                                        contain upper and lower\
                                        case letters, and at least,\
                                        one number')
            return False
        elif len(set(string.ascii_uppercase).intersection(pw)) == 0:
            self.password.errors.append('Password must be\
                                        at least 6 characters,\
                                        contain upper and lower\
                                        case letters, and at least,\
                                        one number')
            return False
        elif len(set(string.digits).intersection(pw)) == 0:
            self.password.errors.append('Password must be\
                                        at least 6 characters,\
                                        contain upper and lower\
                                        case letters, and at least,\
                                        one number')
            return False
        user = User.query.filter_by(
                username=self.username.data).first()
        if user is not None:
            self.username.errors.append('Username already in use. \
                                        Please choose another one')
            return False
        email = User.query.filter_by(
                email=self.email.data).first()
        if email is not None:
            self.email.errors.append('Email already in use')
            return False
        return True
