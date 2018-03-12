from followback import app, db, lm, celery, celery_logger
from flask import render_template, flash, redirect, g, session, url_for, request
from flask_login import login_user, current_user, logout_user 
from .forms import LoginForm, RegisterForm, BotForm, CheckpointForm, UnfollowForm, AddWhitelistForm, RegisterInstaForm, ChangeUsernameForm, ChangePasswordForm, ForgotCredentialForm, ResetPasswordForm
from .models import User, InstaUser, PaypalTransaction, Whitelist
from .decorators import login_required
from .token import generate_confirmation_token, confirm_token
from .emails import  send_email
from config import PAYPAL_LOG_FILE, INSTABOT_LOG_FILE, UNFOLLOWBOT_LOG_FILE
import logging
from datetime import datetime, date, timedelta
from InstagramBot import InstagramBot, Getter
from werkzeug.datastructures import ImmutableOrderedMultiDict
import requests
import logging

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
        user = User(username=form.username.data,email=form.email.data,confirmed=False) 
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        token = generate_confirmation_token(user.email)
        confirm_url = url_for('confirm_email',token=token, _external=True)
        html = render_template('activate_email.html',confirm_url=confirm_url)
        subject = "Followback: Please confirm your email"
        send_email(subject,app.config['ADMINS'][0],[user.email],html)
        login_user(user)
        flash('A confirmation email has been sent to your email', 'success')
        return redirect(url_for('account',username=user.username))
    return render_template('register.html',
                           form=form)

@app.route('/<username>/account',methods=['GET','POST'])
@login_required(confirmed=False)
def account(username):
    if request.method == "POST":
        resend = request.form.get("resend","N/A")
        if resend != "N/A":
            token = generate_confirmation_token(g.user.email)
            confirm_url = url_for('confirm_email',token=token, _external=True)
            html = render_template('activate_email.html',confirm_url=confirm_url)
            subject = "Followback: Please confirm your email"
            send_email(subject,app.config['ADMINS'][0],[g.user.email],html)
            flash("Confirmation email resent", "success")
    return render_template('account.html')

@app.route('/support')
def support():
    return render_template('support.html')

@app.route('/<username>/change_username',methods=['GET','POST'])
@login_required()
def change_username(username):
    form = ChangeUsernameForm(g.user)
    if form.validate_on_submit():
        g.user.username = form.new_username.data
        db.session.add(g.user)
        db.session.commit()
        flash("Username Change Successful","success")
    return render_template('change_username.html',
                            form=form)

@app.route('/<username>/change_password',methods=['GET','POST'])
@login_required()
def change_password(username):
    form = ChangePasswordForm(g.user)
    if form.validate_on_submit():
        g.user.set_password(form.new_password.data)
        db.session.add(g.user)
        db.session.commit()
        flash("Password Change Successful","success")
    return render_template('change_password.html',
                            form=form)

@app.route('/forgot_password',methods=['GET','POST'])
def forgot_password():
    form = ForgotCredentialForm()
    if form.validate_on_submit():
        token = generate_confirmation_token(form.email.data)
        confirm_url = url_for('reset_password',token=token, _external=True)
        html = render_template('reset_password_email.html',confirm_url=confirm_url)
        subject = "FollowBack: Reset Password"
        send_email(subject,app.config['ADMINS'][0],[form.email.data],html)
        flash("Email sent to %s with further instructions" % (form.email.data),"success")
    return render_template('forgot_password.html',
                            form=form)

@app.route('/forgot_username',methods=['GET','POST'])
def forgot_username():
    form = ForgotCredentialForm()
    if form.validate_on_submit():
        html = render_template('forgot_username_email.html',username=form.user.username)
        subject = "FollowBack: Username"
        send_email(subject,app.config['ADMINS'][0],[form.email.data],html)
        flash("Email sent to %s with your username" % (form.email.data),"success")
        return redirect(url_for('login'))
    return render_template('forgot_username.html',
                            form=form)


@app.route('/reset_password/<token>',methods=['GET','POST'])
def reset_password(token):
    form = ResetPasswordForm()
    email = confirm_token(token)
    if email:
        user = User.query.filter_by(email=email).first()
        if user is not None:
            if form.validate_on_submit():
               user.set_password(form.new_password.data) 
               db.session.add(user)
               db.session.commit()
               flash("Password Reset Successful","success")
               return redirect(url_for('login'))
        else:
            flash("Email does not correspond to any registered users","danger")
            return redirect(url_for("index"))
    else:
        flash("The reset link is invalid or has expired", "danger")
        return redirect(url_for("index"))
    return render_template("reset_password.html",
                            form=form)

@app.route('/confirm/<token>')
def confirm_email(token):
    email = confirm_token(token)
    if not email:
        flash('The confirmation link is invalid or has expired.', 'danger')
        return redirect(url_for('index'))
    user = User.query.filter_by(email=email).first()
    if user.confirmed:
        flash('Account already confirmed. Please login.', 'success')
    else:
        user.confirmed = True
        user.plan = "Trial"
        user.purchased = True
        user.datetime_created = date.today()
        db.session.add(user)
        db.session.commit()
        flash('You have confirmed your account. Thanks!', 'success')
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if g.user is not None and g.user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        login_user(form.user,form.remember_me.data)
        return redirect(request.args.get('next') or url_for('dashboard',username=g.user.username))
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
        if g.user.paypal_transactions:
            last_payment = g.user.paypal_transactions[-1].unix
            last_payment = last_payment.date()
            from dateutil.relativedelta import relativedelta
            stop_date = last_payment + relativedelta(months=+1)
            stop_date += timedelta(days=1)
            g.stop_date = stop_date
            if date.today() > stop_date:
                g.user.purchased=False
                db.session.add(g.user)
                db.session.commit()
        elif g.user.confirmed:
            created_date = g.user.datetime_created.date()
            stop_date = created_date + timedelta(days=7)
            g.stop_date = stop_date
            if date.today() > stop_date:
                g.user.purchased=False
                db.session.add(g.user)
                db.session.commit()

@app.route('/ipn',methods=['POST'])
def ipn():
    class NotFullPayment(Exception):
        pass

    filename = PAYPAL_LOG_FILE % (date.today())
    handler = logging.handlers.RotatingFileHandler(filename,'a',1*1024*1024,10)
    handler.setLevel(logging.DEBUG)
    paypal_logger = logging.getLogger('paypal')
    paypal_logger.addHandler(handler)
    arg = ''
    request.parameter_storage_class = ImmutableOrderedMultiDict
    values = request.form
    for x, y in values.iteritems():
        arg += "&{x}={y}".format(x=x,y=y)
    validate_url = 'https://www.sandbox.paypal.com' \
                    '/cgi-bin/webscr?cmd=_notify-validate{arg}' \
                    .format(arg=arg)
    r = requests.get(validate_url)
    if r.text == 'VERIFIED':
        try:
            txn_type = request.form.get('txn_type','N/A')
            payer_email = request.form.get('payer_email','N/A')
            unix = date.today()
            username = request.form.get('custom','N/A')
            payment_date = request.form.get('payment_date','N/A')
            last_name = request.form.get('last_name','N/A')
            payment_gross = request.form.get('mc_gross',0)
            payment_fee = request.form.get('mc_fee',0)
            payment_net = float(payment_gross) - float(payment_fee)
            payment_status = request.form.get('payment_status','N/A')
            txn_id = request.form.get('txn_id','N/A')
            subscr_id = request.form.get('subscr_id','N/A')
            user = User.query.filter_by(username=username).first()
            if txn_type == 'subscr_payment':
                if float(payment_gross) < 5:
                    user.purchased = False
                    raise NotFullPayment
            
                payment = PaypalTransaction(payer_email=payer_email,
                                        unix=unix,payment_date=payment_date,
                                        last_name=last_name,
                                        payment_gross=payment_gross,
                                        payment_fee=payment_fee,
                                        payment_net=payment_net,
                                        payment_status=payment_status,
                                        txn_id=txn_id,
                                        subscr_id = subscr_id)
                user.purchased = True
                user.plan = "Classic"
                user.paypal_transactions.append(payment)
                db.session.add(user)
                db.session.commit()
        except Exception as e:
            paypal_logger.warning(e)
    paypal_logger.info(values)
    return r.text

@app.route('/<username>/purchase')
@login_required()
def purchase(username):
    return render_template('purchase.html')

@app.route('/<username>/success')
@login_required()
def success(username):
    return render_template('success.html')

@app.route('/<username>/<bot_id>/bot_status',methods=['GET','POST'])
@login_required()
def bot_status(username,bot_id):
    start_time = str()
    stopped = False
    insta_user = InstaUser.query.filter_by(bot_id=bot_id).first()
    insta_username = insta_user.username
    if request.method=='POST':
        celery.control.revoke(bot_id, terminate=True, signal='SIGINT')    
    status = instabot.AsyncResult(bot_id)
    if status.state == "PROGRESS":
        dt = datetime.strptime(status.info['start_time'], "%Y-%m-%dT%H:%M:%S.%f")
        start_time = dt.strftime("%A, %d. %B %Y \
                                %I:%M%p UTC")
    if status.state == "SUCCESS":
        start = status.result.get('start_time',0)
        end = status.result.get('end_time',0)
        start = datetime.strptime(start, "%Y-%m-%dT%H:%M:%S.%f")
        end = datetime.strptime(end, "%Y-%m-%dT%H:%M:%S.%f")
        run_time = end-start
        seconds = run_time.total_seconds()
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        status.result['start_time'] = start.strftime("%A, %d. %B %Y \
                                                    %I:%M%p UTC")
        status.result['end_time'] = end.strftime("%A, %d. %B %Y \
                                                %I:%M%p UTC")
        status.result['run_time'] = "%s hours, %s minutes, %s seconds" % (hours,minutes,seconds)
    return render_template('bot_status.html',
                            status=status,
                            bot_id=bot_id,
                            start_time=start_time,
                            insta_username=insta_username
                            )

@app.route('/<username>/dashboard')
@login_required()
def dashboard(username):
    return render_template('dashboard.html')

@celery.task(bind=True)
def instabot(self,**kwargs):
    args = kwargs.get('args')
    cookies = kwargs.get('cookies')
    headers = kwargs.get('headers')
    function = kwargs.get('function')
    bot = InstagramBot(args)
    bot.set_up()
    bot.login_poster(cookies,headers)
    if function == "bot":
        logfile = INSTABOT_LOG_FILE % args['username']
        handler = logging.handlers.RotatingFileHandler(logfile,'a',1*1024*1024, 10)
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        celery_logger.addHandler(handler)
        celery_logger.setLevel(logging.DEBUG)
        status = bot.login_getter()
        if not status:
            result = dict()
            celery_logger.error("Getter login failed")
            return result
        start_time = datetime.utcnow()
        followers_count = bot.get_followers()
        following_count = bot.get_followings()
        self.update_state(state="PROGRESS",
                            meta={"type":"bot",
                                "likes":0,
                                "follows":0,
                                "initial_followers":followers_count,
                                "followers_count":followers_count,
                                "following_count":following_count,
                                "start_time":start_time,
                                "end_time":0})
        result = bot.loop(self,start_time)
        return result
    elif function == "unfollow":
        logfile = UNFOLLOWBOT_LOG_FILE % args['username']
        handler = logging.handlers.RotatingFileHandler(logfile,'a',1*1024*1024,10)
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        celery_logger.addHandler(handler)
        celery_logger.setLevel(logging.DEBUG)
        status = bot.login_getter()
        if not status:
            result = dict()
            celery_logger.error("Getter login failed")
            return result
        start_time = datetime.utcnow()
        followings = bot.get_followings()
        self.update_state(state="PROGRESS",
                        meta={"type":"unfollow",
                            "unfollows":0,
                            "followings":followings,
                            "start_time":start_time,
                            "end_time":0})
        result = bot.unfollow(state=self,start_time=start_time)
        return result

@app.route('/<username>/checkpoint',methods=['GET','POST'])
@login_required(purchased=True)
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
        function = session['function']
        args['password'] = form.password.data 
        bot = InstagramBot(args)
        (status,req_session) = bot.handle_checkpoint_poster(form.code.data,
                                                            cookies,headers,
                                                            response)
        if status == 0:
            insta_user = InstaUser.query.filter_by(pk=session['pk']).first()
            cookies = requests.utils.dict_from_cookiejar(req_session.cookies)
            headers = req_session.headers
            headers = dict(headers)
            kwargs = {'args':args,'cookies':cookies,'headers':headers,'function':function}
            bot_instance = instabot.delay(**kwargs)
            insta_user.bot_id = bot_instance.id
            db.session.add(insta_user)
            db.session.commit()
            session['args'] = None
            session['cookies'] = None
            session['headers'] = None
            session['response'] = None
            session['pk'] = None
            session['function']=None
            return redirect(url_for('bot_status',username=username,
                                    bot_id=bot_instance.id))
        elif status == 1:
            message = 'Incorrect password, try again'
            form.password.errors.append(message)
            return render_template('checkpoint.html', 
                                    form=form, 
                                    )
        elif status == 3:
            message = 'Incorrect checkpoint code'
            form.code.errors.append(message)
            return render_template('checkpoint.html', 
                                    form=form, 
                                    )
    flash(checkpoint_msg,"info")
    return render_template('checkpoint.html', 
                            form=form, 
                            )

@app.route('/<username>/start_bot',methods=['GET','POST'])
@login_required(purchased=True)
def start_bot(username):
    insta_user_list = [ (x.username,x.username) for x in g.user.insta_users]
    form = BotForm(insta_user_list)
    if form.validate_on_submit():
        user_info_string = "https://www.instagram.com/%s/?__a=1"
        req = requests.get(user_info_string % (form.insta_username.data))
        json = req.json()
        pk = json['user']['id']
        insta_user = InstaUser.query.filter_by(pk=pk).first()
        if insta_user is not None:
            if insta_user not in g.user.insta_users:
                form.insta_username.errors.append('Instagram Account %s already registered with another account' % (form.insta_username.data))
                return render_template('start_bot.html',
                                    form=form)
            else:
                if insta_user.bot_id is not None:
                    bot_id = insta_user.bot_id
                    status = instabot.AsyncResult(bot_id)
                    if status.state == "PROGRESS":
                        message = "This user is already running a bot!"
                        form.insta_username.errors.append(message)
                        return render_template('start_bot.html',
                                                form=form)
        else:
            form.insta_username.errors.append("Instagram Account not yet registered with this account. <a href='" + {{ url_for('register_insta',username=g.user.username) }} + "'>Register here</a>")
            return render_template('start_bot.html',
                                        form=form)
        args = dict()
        args['username']=form.insta_username.data
        args['password']=form.insta_password.data
        args['pages']=form.pages.data
        args['likes_per_day']=form.likes_per_day.data
        args['follows_per_day']=form.follows_per_day.data
        args['use_whitelist']=form.use_whitelist.data
        bot = InstagramBot(args)
        (status,req_session,response) = bot.try_login_poster()
        cookies = requests.utils.dict_from_cookiejar(req_session.cookies)
        headers = req_session.headers
        headers = dict(headers)
        if status == 0:
            kwargs = {'args':args,'cookies':cookies,'headers':headers,'function':'bot'}
            bot_instance = instabot.delay(**kwargs)
            insta_user.bot_id = bot_instance.id
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
            session['pk'] = pk
            session['function']= 'bot'
            return redirect(url_for('checkpoint',
                                    username=username,
                                    ))
        elif status == 4:
            app.logger.error('Unknown login error with response %s' % (response))
            flash('Unknown Login Error; Our team has been notified', 'danger')
            return render_template('start_bot.html',
                                    form=form
                                    )
    return render_template('start_bot.html',
                            form = form
                            )

@app.route('/<username>/unfollowbot',methods=['GET','POST'])
@login_required(purchased=True)
def unfollowbot(username):
    insta_user_list = [ (x.username,x.username) for x in g.user.insta_users]
    form = UnfollowForm(insta_user_list)
    if form.validate_on_submit():
        user_info_string = "https://www.instagram.com/%s/?__a=1"
        req = requests.get(user_info_string % (form.insta_username.data))
        json = req.json()
        pk = json['user']['id']
        insta_user = InstaUser.query.filter_by(pk=pk).first()
        if insta_user is not None:
            if insta_user not in g.user.insta_users:
                form.insta_username.errors.append("Instagram Account %s already registered with another account" % (form.insta_username.data))
                return render_template('unfollowbot.html',
                                    form=form)
            else:
                bot_id = insta_user.bot_id
                status = instabot.AsyncResult(bot_id)
                if status.state == "PROGRESS":
                    message = "This user is already running a bot!"
                    form.insta_username.errors.append(message)
                    return render_template('unfollowbot.html',
                                        form=form)
        else:
            form.insta_username.errors.append("Instagram Account not yet registered with this account. <a href='" + {{ url_for('register_insta',username=g.user.username) }} + "'>Register here</a>")
            return render_template('unfollowbot.html',
                                        form=form)
        args = dict()
        args['username']=form.insta_username.data
        args['password']=form.insta_password.data
        args['follows_per_day']=form.follows_per_day.data
        args['use_whitelist']=form.use_whitelist.data
        bot = InstagramBot(args)
        (status,req_session,response) = bot.try_login_poster()
        cookies = requests.utils.dict_from_cookiejar(req_session.cookies)
        headers = req_session.headers
        headers = dict(headers)
        if status == 0:
            kwargs = {'args':args,'cookies':cookies,'headers':headers,'function':'unfollow'}
            bot_instance = instabot.delay(**kwargs)
            insta_user.bot_id = bot_instance.id
            db.session.add(insta_user)
            db.session.commit()
            return redirect(url_for('bot_status',username=username,bot_id=bot_instance.id))
        elif status == 1:
            message = 'Login Error! Instagram username or password are incorrect'
            form.insta_username.errors.append(message)
            return render_template('unfollowbot.html',
                                    form=form,
                                    )
        elif status == 2:
            args['password'] = ''
            session['args'] = args
            session['cookies'] = cookies
            session['headers'] = headers
            session['response'] = response
            session['pk'] = pk
            session['function'] = 'unfollow'
            return redirect(url_for('checkpoint',
                                    username=username,
                                    ))
        elif status == 4:
            app.logger.error('Unknown login error with response %s' % (response))
            flash('Unknown Login Error; Our team has been notified', 'danger')
            return render_template('unfollowbot.html',
                                        form=form)
    return render_template('unfollowbot.html',
                            form = form
                            )

@app.route('/<username>/add_whitelist',methods=['GET','POST'])
@login_required(purchased=True)
def add_whitelist(username):
    insta_user_list = [ (x.username,x.username) for x in g.user.insta_users]
    form = AddWhitelistForm(insta_user_list)
    if form.validate_on_submit():
        user_info_string = "https://www.instagram.com/%s/?__a=1"
        req = requests.get(user_info_string % (form.insta_username.data))
        json = req.json()
        pk = json['user']['id']
        insta_user = InstaUser.query.filter_by(pk=pk).first()
        if insta_user is not None:
            if insta_user not in g.user.insta_users:
                form.insta_username.errors.append('Instagram Account %s already registered with another account' % (form.insta_username.data))
                return render_template('add_whitelist.html',
                                        form=form)
        else:
            form.insta_username.errors.append("Instagram Account not yet registered with this account. <a href='" + {{ url_for('register_insta',username=g.user.username) }} + "'>Register here</a>")
            return render_template('add_whitelist.html',
                                        form=form)
        users = form.users.data
        if form.make.data:
            getter = Getter(form.insta_username.data,form.insta_password.data)
            status = getter.login()
            if status:
                followings = getter.getTotalSelfFollowings()
                for user in followings:
                    pk = Whitelist(pk=user['pk'])
                    insta_user.whitelist.append(pk)  
            else:
                flash("Error logging in with provided credentials", 'danger')
                return render_template('add_whitelist.html',
                                        form=form)

        for user in users:
            req = requests.get(user_info_string % (user))
            if req.status_code !=200:
                flash("Error with adding user %s" % user, 'danger')
                return render_template('add_whitelist.html',
                                        form=form)
            json = req.json()
            pk = json['user']['id']
            pk = Whitelist(pk=pk)
            insta_user.whitelist.append(pk)
        db.session.add(insta_user)
        db.session.commit()
        flash("Successfully added users to whitelist",'success')
    return render_template('add_whitelist.html',
                            form=form)

@app.route('/<username>/register_insta',methods=['GET','POST'])
@login_required(purchased=True)
def register_insta(username):
    form = RegisterInstaForm()
    if form.validate_on_submit():
        getter = Getter(form.insta_username.data,form.insta_password.data)
        status = getter.login()
        if status:
            user_info_string = "https://www.instagram.com/%s/?__a=1"
            req = requests.get(user_info_string % (form.insta_username.data))
            json = req.json()
            pk = json['user']['id']
            insta_user = InstaUser.query.filter_by(pk=pk).first()
            if insta_user is not None:
                if insta_user not in g.user.insta_users:
                    form.insta_username.errors.append('Instagram Account %s already registered ' % (form.insta_username.data))
                else:
                    insta_user.username=form.insta_username.data
                    db.session.add(insta_user)
                    db.session.commit()
                    flash("Name change successful",'success')
                    return redirect(url_for('dashboard',username=g.user.username))
            else:
                if len(g.user.insta_users) > 0:
                    flash('You can only register one account with the Classic payment plan','danger')
                else:
                    insta_user = InstaUser(username=form.insta_username.data,pk=pk)
                    g.user.insta_users.append(insta_user)
                    db.session.add(g.user)
                    db.session.commit()
                    flash("Registration successful",'success')
                    return redirect(url_for('dashboard',username=g.user.username))
        else:
            flash("Error logging in with these credentials", 'danger')
    return render_template('register_insta.html',
                            form=form)

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500
