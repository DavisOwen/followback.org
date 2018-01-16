from threading import Thread
from flask_login import login_required
from flask import redirect, url_for
from functools import wraps
from .views import g 

def async(f):
    def wrapper(*args, **kwargs):
        thr = Thread(target=f, args=args, kwargs=kwargs)
        thr.start()
    return wrapper

def login_required(role="ANY"):
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if not g.user.is_authenticated:
                return lm.unauthorized()
            urole = g.user.get_role()
            if role == "Customer" and (urole != role):
                return redirect(url_for('purchase',username=g.user.username))
            elif role == "Confirmed" and (urole != role):
                return redirect(url_for('confirm_email',username=g.user.username))
            return fn(*args,**kwargs)
        return decorated_view
    return wrapper
