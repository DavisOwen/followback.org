from flask import Flask
from flask_mail import Mail
from celery import Celery
from celery.utils.log import get_task_logger
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import ADMINS, MAIL_SERVER, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD, MAIL_USE_TLS

app = Flask(__name__)
app.config.from_object('config')
db = SQLAlchemy(app)
lm = LoginManager()
lm.init_app(app)
lm.login_view = 'login'
celery = Celery(app.name, backend=app.config['CELERY_RESULT_BACKEND'], broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)
celery_logger = get_task_logger(__name__)
mail = Mail(app)
if not app.debug:
    import logging
    from logging.handlers import SMTPHandler
    credentials=None
    secure=None
    if MAIL_USERNAME or MAIL_PASSWORD:
        credentials = (MAIL_USERNAME, MAIL_PASSWORD)
    if MAIL_USE_TLS:
        secure = ()
    mail_handler = SMTPHandler(mailhost=(MAIL_SERVER, MAIL_PORT), fromaddr=ADMINS[0], toaddrs=ADMINS, subject='followback error',credentials=credentials,secure=secure)
    mail_handler.setLevel(logging.ERROR)
    app.logger.addHandler(mail_handler)

from followback import views, models
