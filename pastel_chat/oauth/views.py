# -*- coding: utf-8 -*-

from flask import request, redirect, url_for
from sqlalchemy.exc import IntegrityError
from pastel_chat import db
from pastel_chat.oauth.models import User
from pastel_chat.oauth import oauth
from pastel_chat.oauth.provider import PlatformOAuth2Manager, platform_name2id
from pastel_chat.utils import store_current_user


@oauth.route('/<platform_name>/authorize', methods=['GET'])
def request_oauth(platform_name):
    try:
        messenger, messenger_uid = store_current_user()
        new_user = User(messenger_uid=messenger_uid)    # 새로운 회원 가입
        db.session.add(new_user)
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        if e.orig.args[0] == 1062:      # 이미 가입이 되어 있는 경우
            pass
    except:
        return redirect(url_for('index'))
    platform_id = platform_name2id(platform_name)
    manager = PlatformOAuth2Manager(platform_id)
    return manager.process('step1')


@oauth.route('/<platform_name>/callback', methods=['GET'])
def oauth_callback(platform_name):
    auth_code = request.args.get('code')
    platform_id = platform_name2id(platform_name)
    manager = PlatformOAuth2Manager(platform_id)
    return manager.process('step2', code=auth_code)
