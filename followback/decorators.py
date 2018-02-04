from threading import Thread
from flask_login import login_required
from flask import redirect, url_for, flash
from functools import wraps
from .views import g 

def async(f):
    def wrapper(*args, **kwargs):
        thr = Thread(target=f, args=args, kwargs=kwargs)
        thr.start()
    return wrapper

def login_required(plan="ANY",confirmed=True,purchased=False):
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if not g.user.is_authenticated:
                return lm.unauthorized()
            uplan = g.user.get_plan()
            uconfirmed = g.user.get_confirmed()
            upurchased = g.user.get_purchased()
            if purchased and (upurchased != purchased):
                flash("This is a paid feature","warning")
                return redirect(url_for('purchase',username=g.user.username))
            elif confirmed and (uconfirmed != confirmed):
                flash("Confirm email first","warning")
                return redirect(url_for('account',username=g.user.username))
            return fn(*args,**kwargs)
        return decorated_view
    return wrapper
