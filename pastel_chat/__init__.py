# -*- coding: utf-8 -*-

from flask import Flask, g
from flask_assets import Environment, ManageAssets
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, MigrateCommand
from flask_login import LoginManager
# from flask_mail import Mail
from flask_s3 import FlaskS3
from flask_script import Manager
import logging
from linebot import LineBotApi
from linebot import WebhookHandler
from config import DEBUG, LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET, MS_COGNITIVE_SERVICE_APP_ID, \
    MS_COGNITIVE_SERVICE_APP_KEY
from luis_sdk import LUISClient
from pastel_chat.connectors.dao import DAO, DaoType
from pastel_chat.connectors.es import ElasticSearchType, ElasticSearchConnector
from pastel_chat.connectors.redis import RedisType, RedisConnector
from pastel_chat.core.utils import PositiveOrNegativeDetector
from pastel_chat.scripts import compress

app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
# app.session_interface = RedisSessionInterface()
assets = Environment(app)
s3 = FlaskS3(app)
# mail = Mail(app)
manager = Manager(app)

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

luis = LUISClient(MS_COGNITIVE_SERVICE_APP_ID, MS_COGNITIVE_SERVICE_APP_KEY, DEBUG)


def create_logger():
    logger = logging.getLogger('pastel_chat_logger')
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    logger.addHandler(ch)
    return logger


logger = create_logger()


# Sentry 설정
from raven.contrib.flask import Sentry
sentry = Sentry(app,
        dsn='')

if DEBUG:
    sentry.dsn = None

app.config['CSRF_ENABLED'] = True
app.config['SECRET_KEY'] = ''

db_type = DaoType.DEV if DEBUG else DaoType.PRODUCTION
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['SQLALCHEMY_POOL_RECYCLE'] = 7200
app.config['SQLALCHEMY_POOL_SIZE'] = 10
app.config['SQLALCHEMY_DATABASE_URI'] = DAO.DAO_TYPES[db_type].uri

db = SQLAlchemy(app)
migrate = Migrate(app, db)

manager.add_command('db', MigrateCommand)
manager.add_command('assets', ManageAssets(assets))


def get_redis(redis_type):
    with app.app_context():
        redis_connection_pool = getattr(g, '_redis_connection_pool', None)
        if redis_connection_pool is None:
            redis_connection_pool = g._redis_connection_pool = {}
        selected = redis_connection_pool.get(redis_type)
        if selected is None:
            selected = redis_connection_pool[redis_type] = RedisConnector(redis_type)
            g._redis_connection_pool = redis_connection_pool
        return selected.get_redis()


es_type = ElasticSearchType.DEV if DEBUG else ElasticSearchType.PRODUCTION


def get_es():
    with app.app_context():
        es_connection = getattr(g, '_es_connection', None)
        if es_connection is None:
            es_connection = g._es_connection = ElasticSearchConnector(es_type)
        return es_connection.get_es()


app.config['FLASKS3_BUCKET_NAME'] = ''
app.config['FLASKS3_REGION'] = ''
app.config['AWS_ACCESS_KEY_ID'] = ''
app.config['AWS_SECRET_ACCESS_KEY'] = ''
app.config['FLASKS3_FORCE_MIMETYPE'] = True
app.config['FLASK_ASSETS_USE_S3'] = True
app.config['FLASKS3_GZIP'] = True
app.config['FLASKS3_CDN_DOMAIN'] = ''
app.config['FLASKS3_USE_HTTPS'] = True


# 기본 응답 템플릿
def response_template(message, status=200, data=None):
    content = {'message': message}
    if data:
        content = {'message': message, 'data': data}
    import flask
    return flask.jsonify(content), status


# Status 400 응답
def bad_request(message='잘못된 형식으로 요청했습니다.', error=None):
    return response_template(message, 400)

# Status 401 응답
def unauthorized(message='로그인이 필요합니다.', error=None):
    return response_template(message, 401)

# Status 403 응답
def forbidden(message='권한이 없습니다.', error=None):
    return response_template(message, 403)

# Status 404 응답
def not_found(message='잘못된 요청입니다. 요청 API를 확인해주세요.', error=None):
    return response_template(message, 404)

# Status 500 응답
def internal_error(message='점검 중이거나 내부 문제가 발생했습니다. 나중에 다시 시도해주세요.', error=None):
    return response_template(message, 500)


@app.errorhandler(400)
def bad_request_template(error=None):
    sentry.captureException()
    return bad_request()

@app.errorhandler(404)
def not_found_template(error=None):
    sentry.captureException()
    return render_template('404.html')


@app.errorhandler(403)
def forbidden_template(error=None):
    return render_template('403.html')


@app.errorhandler(500)
def internal_error_template(error=None):
    sentry.captureException()
    return render_template('500.html')


from pastel_chat.oauth.views import oauth
app.register_blueprint(oauth)
from pastel_chat.plusfriend.views import plusfriend
app.register_blueprint(plusfriend)
from pastel_chat.line.views import line
app.register_blueprint(line)
from pastel_chat.views import *


compress()
PositiveOrNegativeDetector.warmup()
