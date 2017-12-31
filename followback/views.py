from followback import app, db, lm, celery
from flask import render_template, flash, redirect, g, session, url_for, request
from flask_login import login_user, current_user, login_required, logout_user 
from .forms import LoginForm, RegisterForm, BotForm, CheckpointForm
from .models import User, InstaUser
from datetime import datetime
from instabot import Bot
from functools import wraps
import requests.utils

def login_required(role="ANY"):
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return lm.unauthorized()
            urole = current_user.get_role()
            if role == "Customer" and (urole != role):
                return redirect(url_for('purchase',username=current_user.username))
            return fn(*args,**kwargs)
        return decorated_view
    return wrapper

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html',
                            title='Home',
                            )
    
@app.route('/register', methods=['GET','POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
       user = User(username=form.username.data,password=form.password.data) 
       user.role = "Customer"
       db.session.add(user)
       db.session.commit()
       return redirect(url_for('login'))
    return render_template('register.html',
                           title='Register',
                           form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if g.user is not None and g.user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        login_user(form.user,form.remember_me.data)
        return redirect(request.args.get('next') or url_for('index'))
    return render_template('login.html',
                            title='Sign In',
                            form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@lm.user_loader
def load_user(id):
    return User.query.get(int(id))

@app.before_request
def before_request():
    g.user = current_user
    if g.user.is_authenticated:
        g.user.last_seen = datetime.utcnow()
        db.session.add(g.user)
        db.session.commit()

@app.route('/purchase')
def purchase():
    return render_template('purchase.html')

@app.route('/<username>/bot_status')
@login_required()
def all_bot_status(username):
    return render_template('all_bot_status.html')

@app.route('/<username>/<bot_id>/bot_status',methods=['GET','POST'])
@login_required()
def bot_status(username,bot_id):
    insta_user = InstaUser.query.filter_by(bot_id=bot_id).first()
    if request.method=='POST':
        celery.control.revoke(bot_id, terminate=True, signal='SIGINT')    
        insta_user.state = "STOPPED"
        db.session.add(insta_user)
        db.session.commit()
    #if insta_user.state != "STOPPED":
    status = instabot.AsyncResult(bot_id)
    #else:
    #    status = None
    return render_template('bot_status.html',
                            status=status,
                            bot_id=bot_id,
                            insta_user=insta_user)

@celery.task(bind=True)
def instabot(self,**kwargs):
    args = kwargs.get('args')
    cookies = kwargs.get('cookies')
    headers = kwargs.get('headers')
    bot = Bot(args)
    bot.set_up()
    bot.login_poster(cookies,headers)
    status = bot.login_getter()
    if not status:
        result = dict()
        return result
    start_time = datetime.utcnow()
    self.update_state(state="PROGRESS",
                        meta={"likes":0,
                            "follows":0,
                            "start_time":start_time,
                            "end_time":0})
    result = bot.loop(self,start_time)
    return result

@app.route('/<username>/checkpoint',methods=['GET','POST'])
@login_required(role='Customer')
def checkpoint(username):
    form = CheckpointForm()
    response = session['response']
    checkpoint_msg = 'Security code sent to email \
                        %s associated with this instagram account'\
                        % (response['fields']['contact_point'])
    if form.validate_on_submit():
        args = session['args']
        cookies = session['cookies']
        headers = session['headers']
        args['password'] = form.password.data 
        bot = Bot(args)
        (status,req_session) = bot.handle_checkpoint_poster(form.code.data,
                                                            cookies,headers,
                                                            response)
        if status == 0:
            cookies = requests.utils.dict_from_cookiejar(req_session.cookies)
            headers = req_session.headers
            headers = dict(headers)
            kwargs = {'args':args,'cookies':cookies,'headers':headers}
            if session['new_user']:
                insta_user = InstaUser(username=args['username'],pk=session['pk'])
                g.user.insta_users.append(insta_user)
                db.session.add(g.user)
                db.session.commit()
            else:
                insta_user = InstaUser.query.filter_by(username=args['username']).first()
                if insta_user is None:
                   insta_user = InstaUser.query.filter_by(pk=session['pk']).first()
                   insta_user.username=args['username']
                   db.session.add(insta_user)
                   db.session.commit()
            bot_instance = instabot.delay(**kwargs)
            insta_user = InstaUser.query.filter_by(username=args['username']).first()
            insta_user.bot_id = bot_instance.id
            insta_user.state = "RUNNING"
            insta_user.likes = None
            insta_user.follows = None
            insta_user.start_time = None
            insta_user.end_time = None
            db.session.add(insta_user)
            db.session.commit()
            session['args'] = None
            session['cookies'] = None
            session['headers'] = None
            session['response'] = None
            session['new_user'] = None
            session['pk'] = None
            return redirect(url_for('bot_status',username=username,
                                    bot_id=bot_instance.id))
        elif status == 1:
            message = 'Incorrect password, try again'
            form.password.errors.append(message)
            return render_template('checkpoint.html', 
                                    form=form, 
                                    checkpoint_msg=checkpoint_msg)
        elif status == 3:
            message = 'Incorrect checkpoint code'
            form.code.errors.append(message)
            return render_template('checkpoint.html', 
                                    form=form, 
                                    checkpoint_msg=checkpoint_msg)
    return render_template('checkpoint.html', 
                            form=form, 
                            checkpoint_msg=checkpoint_msg)

@app.route('/<username>/start_bot',methods=['GET','POST'])
@login_required(role='Customer')
def start_bot(username):
    form = BotForm()
    if form.validate_on_submit():
        args = dict()
        args['username']=form.insta_username.data
        args['password']=form.insta_password.data
        args['pages']=form.pages.data
        args['likes_per_day']=form.likes_per_day.data
        args['follows_per_day']=form.follows_per_day.data
        args['make']=form.make.data
        args['uploads_per_day']=None
        args['caption']=None
        args['pic_path']=None
        args['scrape_user']=None
        args['upload_file']=None
        bot = Bot(args)
        (status,req_session,response) = bot.try_login_poster()
        cookies = requests.utils.dict_from_cookiejar(req_session.cookies)
        headers = req_session.headers
        headers = dict(headers)
        if status == 0:
            kwargs = {'args':args,'cookies':cookies,'headers':headers}
            if form.new_user.data:
                insta_user = InstaUser(username=form.insta_username.data,pk=form.pk.data)
                g.user.insta_users.append(insta_user)
                db.session.add(g.user)
                db.session.commit()
            else:
                insta_user = InstaUser.query.filter_by(username=args['username']).first()
                if insta_user is None:
                   insta_user = InstaUser.query.filter_by(pk=form.pk.data).first()
                   insta_user.username=form.insta_username.data
                   db.session.add(insta_user)
                   db.session.commit()
            bot_instance = instabot.delay(**kwargs)
            insta_user.bot_id = bot_instance.id
            insta_user.state = "RUNNING"
            insta_user.likes = None
            insta_user.follows = None
            insta_user.start_time = None
            insta_user.end_time = None
            db.session.add(insta_user)
            db.session.commit()
            return redirect(url_for('bot_status',username=username,bot_id=bot_instance.id))
        elif status == 1:
            message = 'Login Error! Instagram username or password are incorrect'
            form.insta_username.errors.append(message)
            return render_template('start_bot.html',
                                    form=form,
                                    )
        elif status == 2:
            args['password'] = ''
            session['args'] = args
            session['cookies'] = cookies
            session['headers'] = headers
            session['response'] = response
            session['new_user'] = form.new_user.data
            session['pk'] = form.pk.data
            return redirect(url_for('checkpoint',
                                    username=username))
        elif status == 4:
            flash('Unknown Poster Login Error')
            return render_template('start_bot.html',
                                    form=form
                                    )
    return render_template('start_bot.html',
                            form = form
                            )

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500
