# -*- coding: utf-8 -*-

import httplib2
import requests
import six
import abc
from abc import abstractmethod
from flask import url_for, session, redirect
from flask_login import login_user
from googleapiclient.discovery import build
from oauth2client.client import OAuth2WebServerFlow, OAuth2Credentials
from sqlalchemy.exc import IntegrityError
from config import NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
from pastel_chat import db
from pastel_chat.oauth.models import User, Platform, PlatformSession, UserSignupStep
from pastel_chat.utils import random_generate_token


def platform_name2id(platform_name):
    selected_platform = Platform.query.filter(Platform.name==platform_name).first()
    return selected_platform.id


@six.add_metaclass(abc.ABCMeta)
class PlatformOAuth2Provider(object):
    def __init__(self):
        self.current_user = User.query\
            .filter(User.messenger_uid==self.messenger_uid).first()

    @abstractmethod
    def get_authorize_url(self):
        raise NotImplementedError('Please implement this method!')

    @abstractmethod
    def exchange_code_token(self, code):
        raise NotImplementedError('Please implement this method!')

    @abstractmethod
    def get_me(self):
        raise NotImplementedError('Please implement this method!')

    @property
    def access_token(self):
        return session['access_token'] \
            if session.get('access_token') else None

    @access_token.setter
    def access_token(self, access_token):
        session['access_token'] = access_token

    @property
    def refresh_token(self):
        return session['refresh_token'] \
            if session.get('refresh_token') else None

    @refresh_token.setter
    def refresh_token(self, refresh_token):
        session['refresh_token'] = refresh_token

    @property
    def messenger_uid(self):
        return session['messenger_uid']

    @property
    def messenger(self):
        return session['messenger']

    def platform_session_model(self):
        return {
            'platform_uid': None,
            'tokens': {
                'access_token': None,
                'refresh_token': None
            },
            'user_uid': None,
            'platform_id': None
        }

    def user_model(self):
        return {
            'username': None,
            'first_name': None,
            'last_name': None,
            'email': None,
            'gender': None,
            'age': None
        }

    def is_logged_in(self):
        return self.access_token is not None

    def get_oauth_callback_url(self, platform_id):
        selected_platform = Platform.query.filter(Platform.id == platform_id).first()
        platform_name = selected_platform.name
        return url_for('oauth.oauth_callback', _external=True,
                       platform_name=platform_name)


class GoogleOAuth2Provider(PlatformOAuth2Provider):

    __platform_id__ = 1

    def get_authorize_url(self):
        flow = self.get_google_oauth_flow(self.get_oauth_callback_url(self.__platform_id__))
        return flow.step1_get_authorize_url()

    def exchange_code_token(self, code):
        flow = self.get_google_oauth_flow(self.get_oauth_callback_url(self.__platform_id__))
        credentials = flow.step2_exchange(code)
        self.access_token = credentials.access_token
        self.refresh_token = credentials.refresh_token
        self.credentials = credentials.to_json()

    def get_me(self):
        credentials = OAuth2Credentials.from_json(self.credentials)
        http = credentials.authorize(httplib2.Http())
        oauth2 = build('oauth2', 'v2', http=http)
        profile = oauth2.userinfo().get()
        response = profile.execute()
        new_userinfo = self.user_model()
        new_userinfo['first_name'] = response.get('given_name', None)
        new_userinfo['last_name'] = response.get('family_name', None)
        new_userinfo['email'] = response.get('email', None)
        new_userinfo['gender'] = response.get('gender', None)

        user_platform_session = self.platform_session_model()
        user_platform_session['platform_uid'] = response.get('id', None)
        user_platform_session['tokens'] = self.credentials
        user_platform_session['user_uid'] = self.current_user.uid
        user_platform_session['platform_id'] = self.__platform_id__
        return new_userinfo, user_platform_session

    def get_google_oauth_flow(self, callback_url):
        return OAuth2WebServerFlow(
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            scope=('https://www.googleapis.com/auth/calendar',
                   'https://www.googleapis.com/auth/userinfo.email',
                   'https://www.googleapis.com/auth/userinfo.profile'),
            redirect_uri=callback_url,
            prompt='consent'
        )


class NaverOAuth2Provider(PlatformOAuth2Provider):

    __platform_id__ = 2

    def get_authorize_url(self):
        state_token = random_generate_token()
        auth_uri = 'https://nid.naver.com/oauth2.0/authorize?response_type=code' \
                   '&client_id=%s&redirect_uri=%s&state=%s' % \
                   (NAVER_CLIENT_ID, self.get_oauth_callback_url(self.__platform_id__),
                    state_token)
        session['state_token'] = state_token
        return auth_uri

    def exchange_code_token(self, code):
        code = code['code']
        get_token_uri = 'https://nid.naver.com/oauth2.0/token?grant_type=' \
                        'authorization_code&client_id=%s&client_secret=%s' \
                        '&code=%s&state=%s&redirect_uri=%s' % (NAVER_CLIENT_ID, NAVER_CLIENT_SECRET,
                                                   code, session['state_token'],
                                                   self.get_oauth_callback_url(self.__platform_id__))
        exchange_response = requests.get(get_token_uri).json()
        self.access_token = exchange_response['access_token']
        self.refresh_token = exchange_response['refresh_token']

    def get_me(self):
        get_userinfo = 'https://openapi.naver.com/v1/nid/me'
        profile = requests.get(get_userinfo,
                               headers={'Authorization': 'Bearer %s' % (session['access_token'])}).json()
        response = profile['response']
        new_userinfo = self.user_model()
        new_userinfo['username'] = response['name']
        new_userinfo['email'] = response['email']
        new_userinfo['age'] = response['age']
        new_userinfo['gender'] = response['gender']

        user_platform_session = self.platform_session_model()
        user_platform_session['platform_uid'] = response.get('id', None)
        user_platform_session['tokens']['access_token'] = self.access_token
        user_platform_session['tokens']['refresh_token'] = self.refresh_token
        user_platform_session['user_uid'] = self.current_user.uid
        user_platform_session['platform_id'] = self.__platform_id__
        return new_userinfo, user_platform_session


class PlatformOAuth2ProviderFactory(object):

    oauth2_platforms = [
        GoogleOAuth2Provider,
        NaverOAuth2Provider
    ]

    @classmethod
    def get_provider(cls, platform_id):
        for platform in PlatformOAuth2ProviderFactory.oauth2_platforms:
            if platform.__platform_id__ == platform_id:
                return platform()


class PlatformOAuth2Manager(object):
    def __init__(self, platform_id):
        self.provider = PlatformOAuth2ProviderFactory.get_provider(platform_id)

    def process(self, step, **kwargs):
        steps = {
            'step1': self._step1,
            'step2': self._step2
        }
        return steps[step](kwargs) if len(kwargs) > 0 else steps[step]()

    def is_logged_in(self):
        return self.provider.is_logged_in()

    def _step1(self):
        return redirect(self.provider.get_authorize_url())

    def _step2(self, code):
        self.provider.exchange_code_token(code)
        if self.is_logged_in():
            user = self.provider.current_user
            new_userinfo, user_platform_session = self.provider.get_me()

            old_user = User.query.filter(User.email == new_userinfo['email']).first()
            if old_user:
                old_user.email = None

            for k, v in new_userinfo.items():
                if v is not None:
                    setattr(user, k, v)
            if user.signup_step_status is None or \
                            user.signup_step_status < UserSignupStep.COMPLETE_ADD_FIRST_OAUTH:
                user.signup_step_status = UserSignupStep.COMPLETE_ADD_FIRST_OAUTH
            new_user_platform_session = PlatformSession(**user_platform_session)
            db.session.add(new_user_platform_session)

            try:
                db.session.commit()
            except IntegrityError as e:
                db.session.rollback()
                if e.orig.args[0] == 1062:
                    old_user_platform_session = \
                        PlatformSession.query.filter(
                            PlatformSession.platform_uid==
                            user_platform_session['platform_uid']
                        ).first()
                    old_user_platform_session.tokens = user_platform_session['tokens']
                    db.session.commit()
        return redirect(url_for('settings'))
