# -*- coding: utf-8 -*-

from flask import request
from flask_login import login_required
from pastel_chat.oauth import oauth
from pastel_chat.oauth.provider import PlatformOAuth2Manager, platform_name2id


@oauth.route('/<platform_name>/authorize', methods=['GET'])
@login_required
def request_oauth(platform_name):
    platform_id = platform_name2id(platform_name)
    manager = PlatformOAuth2Manager(platform_id)
    return manager.process('step1')


@oauth.route('/<platform_name>/callback', methods=['GET'])
def oauth_callback(platform_name):
    auth_code = request.args.get('code')
    platform_id = platform_name2id(platform_name)
    manager = PlatformOAuth2Manager(platform_id)
    return manager.process('step2', code=auth_code)
