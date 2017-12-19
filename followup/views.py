from followup import app, db, lm
from flask import render_template, flash, redirect, g, session, url_for, request
from flask_login import login_user, current_user, login_required, logout_user
from .forms import LoginForm, RegisterForm, EditForm
from .models import User
from datetime import datetime

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

@app.route('/edit',methods=['GET', 'POST'])
@login_required
def edit():
    form = EditForm(g.user.username)
    if form.validate_on_submit():
        g.user.username = form.username.data
        g.user.about_me = form.about_me.data
        db.session.add(g.user)
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('edit'))
    else:
        form.username.data = g.user.username
        form.about_me.data = g.user.about_me
    return render_template('edit.html', form=form)

@app.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first()
    if user == None:
        flash('User %s not found.' % username)
        return redirect(url_for('index'))
    form = BotForm()
    if form.validate_on_submit():
        from subprocess import Popen, PIPE
        process = Popen(['bot.py', form.insta_username.data, form.insta_password.data, form.pages.data, form.likes_per_day.data, form.follows_per_day.data], stdout=PIPE, stderr=PIPE)
        stdout,stderr = process.communicate()
    return render_template('user.html',
                            user = user,
                            form = form,
                            )

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500
