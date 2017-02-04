# -*- coding: utf-8 -*-

import datetime
from flask import render_template
from flask_login import UserMixin
from sqlalchemy import func
from sqlalchemy.orm import relationship, backref
from werkzeug.security import generate_password_hash, check_password_hash
from pastel_chat import db, login_manager
from pastel_chat.models import Calendar
from pastel_chat.utils import random_generate_token


class Platform(db.Model):

    __tablename__ = 'platform'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(20), nullable=True)
    client_id = db.Column(db.Text, nullable=True)
    client_secret = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, onupdate=func.current_timestamp())

    def __init__(self, name, client_id=None, client_secret=None):
        self.name = name
        self.client_id = client_id
        self.client_secret = client_secret
        self.created_at = datetime.datetime.now()


class PlatformSession(db.Model):

    __tablename__ = 'platform_session'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    platform_uid = db.Column(db.String(100), unique=True)
    tokens = db.Column(db.JSON, nullable=False)
    user_uid = db.Column(db.Integer, db.ForeignKey('user.uid'), nullable=True)
    platform_id = db.Column(db.Integer, db.ForeignKey('platform.id'), nullable=False)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, onupdate=func.current_timestamp())

    def __init__(self, platform_uid, tokens, user_uid, platform_id):
        self.platform_uid = platform_uid
        self.tokens = tokens
        self.user_uid = user_uid
        self.platform_id = platform_id
        self.created_at = datetime.datetime.now()


class UserStatus(object):
    DEACTIVATED = 0      # 비활성화(탈퇴)
    BLOCKED = 1          # 차단
    NORMAL = 2           # 정상


class UserPrivilege(object):
    NORMAL = 0           # 일반
    STAFF = 1            # 직원
    ADMIN = 2            # 관리자


class Messenger(object):
    KAKAOTALK = 0               # 카카오톡
    FACEBOOK_MESSENGER = 1      # 페이스북 메신저
    LINE = 2                    # 라인


class User(db.Model, UserMixin):

    __tablename__ = 'user'

    uid = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uuid = db.Column(db.String(32), unique=True, nullable=False)
    username = db.Column(db.String(20), nullable=True)
    first_name = db.Column(db.String(20), nullable=True)
    last_name = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(30), unique=True, nullable=True)
    age = db.Column(db.String(10), nullable=True)
    gender = db.Column(db.String(10), nullable=True)
    status = db.Column(db.SmallInteger, nullable=False)
    privilege = db.Column(db.SmallInteger, nullable=False)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, onupdate=func.current_timestamp())
    messenger = db.Column(db.SmallInteger, nullable=True)
    messenger_uid = db.Column(db.String(100), unique=True)
    region_id = db.Column(db.Integer, db.ForeignKey('region.id'), nullable=True)
    region = relationship('Region', backref=backref('user', uselist=False))
    timezone = db.Column(db.String(50), nullable=True)      # TZ db의 TZ값
    calendars = db.relationship('Calendar', backref='user', lazy='dynamic', primaryjoin=
                                            uid==Calendar.user_uid)
    primary_calendar_id = db.Column(db.Integer, db.ForeignKey('calendar.id'), nullable=True)
    primary_calendar = relationship('Calendar', backref=backref('primary_user', uselist=False),
                                            primaryjoin=primary_calendar_id==Calendar.id)
    platform_sessions = db.relationship('PlatformSession', backref='user')

    def __init__(self, username=None, first_name=None, last_name=None,
                 email=None, status=UserStatus.NORMAL, privilege=UserPrivilege.NORMAL,
                 age=None, gender=None, messenger=Messenger.KAKAOTALK,
                 messenger_uid=None, region_id=None,
                 timezone='Asia/Seoul', primary_calendar_id=None):
        self.uuid = random_generate_token()
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.age = age
        self.gender = gender
        self.email = email
        self.status = status
        self.privilege = privilege
        self.messenger = messenger
        self.messenger_uid = messenger_uid
        self.region_id = region_id
        self.timezone = timezone
        self.primary_calendar_id = primary_calendar_id
        self.created_at = datetime.datetime.now()

    @staticmethod
    def encrypt_password(password):
        return generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def get_id(self):
        return self.messenger_uid

    @property
    def is_active(self):
        return True if self.status > UserStatus.DEACTIVATED else False

    @property
    def is_anonymous(self):
        return False


@login_manager.user_loader
def load_user(user_id):
    login_user = db.session.query(User).filter(User.messenger_uid==user_id).first()
    return login_user


@login_manager.unauthorized_handler
def unauthorized_login():
    return render_template('error.html', title='카카오톡에서 사용해주세요!',
                           description='카카오톡 옐로아이디 친구 추가 후 접속해주세요.')
