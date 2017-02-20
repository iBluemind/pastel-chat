# -*- coding: utf-8 -*-

import datetime, httplib2
from dateutil.relativedelta import relativedelta
from flask import make_response, redirect, render_template, request, url_for, json, \
    session
from flask_login import current_user, login_required, login_user, logout_user
from googleapiclient.discovery import build
from oauth2client.client import OAuth2Credentials
from werkzeug.exceptions import Unauthorized, BadRequest
from config import RSA_PUBLIC_KEY_BASE64
from pastel_chat import app, db, response_template
from pastel_chat.forms import LoginForm
from pastel_chat.login import PastelLoginHelper
from pastel_chat.models import CalendarPlatformSync, Schedule, DateTimeWithTimeZone, Person, \
    CalendarPlatformSyncHistory, PlatformSyncBy, CalendarListPlatformSync, Calendar
from pastel_chat.oauth.models import User
from pastel_chat.oauth.provider import GoogleOAuth2Provider
from pastel_chat.tasks import sync_google_calendar
from pastel_chat.utils import get_or_create, KAKAOTALK_USER_AGENT


@app.route('/login', methods=['GET'])
@login_required
def login():
    session['messenger'] = current_user.messenger
    session['messenger_uid'] = current_user.messenger_uid
    return render_template('login.html')


@app.route('/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/auth/icloud', methods=['GET'])
def icloud_login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()
    rsa_public_key = RSA_PUBLIC_KEY_BASE64

    if form.validate_on_submit():
        encoded_email = form.email.data
        encoded_password = form.password.data
        encoded_aes_key = request.form['decryptKey']
        encoded_aes_iv = request.form['iv']

        pastel_login_helper = PastelLoginHelper(encoded_email, encoded_password,
                                                    encoded_aes_key, encoded_aes_iv)
        try:
            decrypted_email, decrypted_password = pastel_login_helper.decrypt()
            query = db.session.query(User).filter(User.email == decrypted_email)
            user = query.first()

            if user.check_password(decrypted_password):
                login_user(user)
                return redirect(request.args.get('next') or url_for('index'))
            else:
                raise Unauthorized()
        except:
            form.email.errors.append('이메일 주소 또는 비밀번호를 다시 확인해주세요.')

    form.email.data = ''
    response = make_response(render_template('icloud_login.html', form=form))
    response.set_cookie('JSESSIONID', rsa_public_key)
    return response


@app.route('/', methods=['GET'])
def index():
    if current_user.is_authenticated:
        return redirect(url_for('settings'))
    return render_template('index.html')


@app.route('/about', methods=['GET'])
def about():
    return render_template('index.html')


@app.route('/settings', methods=['GET'])
@login_required
def settings():
    user_platform_sessions = current_user.platform_sessions
    if len(user_platform_sessions) == 0:
        return redirect(url_for('login'))
    return render_template('settings.html')


@app.route('/api/calendars', methods=['GET'])
@login_required
def fetch_calendars():
    calendars = current_user.calendars
    primary_calendar_id = current_user.primary_calendar_id
    fetched_calendars = []
    for calendar in calendars:
        is_primary = True if calendar.id == primary_calendar_id else False
        fetched_calendars.append({
            'id': calendar.id,
            'name': calendar.name,
            'is_primary': is_primary
        })
    return response_template('정상처리되었습니다.', data={
        'calendars': fetched_calendars
    })


@app.route('/api/users', methods=['PATCH'])
@login_required
def modify_user():
    if request.form.get('primary_calendar_id'):
        calendar_id = request.form['primary_calendar_id']
        user = User.query.filter(User.uid==current_user.uid).first()
        user.primary_calendar_id = calendar_id
        db.session.commit()
        calendar_name = Calendar.query.get(calendar_id).name
        return response_template('기본 캘린더가 %s로 변경되었습니다.' % calendar_name)
    return response_template('정상처리되었습니다.')


@app.route('/api/sync/calendar_list', methods=['POST'])
@login_required
def calendars_sync():
    def google_calendar_list_sync():
        credentials = list(filter(lambda x: x.platform_id == GoogleOAuth2Provider.__platform_id__,
                                  current_user.platform_sessions))[0].tokens

        credentials = OAuth2Credentials.from_json(credentials)
        http = credentials.authorize(httplib2.Http())
        service = build('calendar', 'v3', http=http)

        sync_request = service.calendarList().list()
        sync_manager = CalendarListPlatformSync.query.filter(
            CalendarListPlatformSync.user_uid == current_user.uid
        ).first()

        sync_tokens = {}
        if sync_manager is not None:
            sync_tokens = sync_manager.tokens

        if sync_tokens.get('sync_token'):
            sync_request.syncToken = sync_tokens['sync_token']
            page_token = sync_tokens.get('page_token')
            if page_token:
                sync_request.pageToken = page_token

        calendar_count = 0
        while True:
            calendars_result = sync_request.execute()
            calendars = calendars_result.get('items', [])
            if len(calendars) == 0:
                break

            calendar_count += len(calendars)
            for calendar in calendars:
                fetched_calendar = get_or_create(
                    db.session,
                    Calendar,
                    platform_uuid=calendar.get('id'),
                    platform_id=GoogleOAuth2Provider.__platform_id__
                )

                calendar_obj_properties = {
                    'platform_uuid': calendar.get('id'),
                    'name': calendar.get('summary'),
                    'timezone': calendar.get('timeZone')
                }

                if calendar.get('primary'):
                    current_user.primary_calendar_id = fetched_calendar.id

                for k, v in calendar_obj_properties.items():
                    setattr(fetched_calendar, k, v)

                users = fetched_calendar.users
                is_in_current_user = True if \
                    len(list(filter(lambda x:
                                    x.uid == current_user.uid, users))) == 1 \
                    else False
                if not is_in_current_user:
                    fetched_calendar.users.append(current_user)
            if calendars_result.get('nextPageToken') is None:
                break
            else:
                sync_tokens['page_token'] = calendars_result.get('nextPageToken')
                sync_request.pageToken = sync_tokens['page_token']
        new_sync_token = calendars_result.get('nextSyncToken')
        if new_sync_token:
            sync_tokens['sync_token'] = new_sync_token
            if sync_tokens.get('page_token'):
                del sync_tokens['page_token']
        if sync_manager:
            sync_manager.tokens = sync_tokens
        else:
            new_platform_sync = CalendarListPlatformSync(
                sync_tokens, current_user.uid, GoogleOAuth2Provider.__platform_id__
            )
            db.session.add(new_platform_sync)
        db.session.commit()
    google_calendar_list_sync()
    return response_template('정상처리되었습니다.')


@app.route('/api/sync/primary_calendar', methods=['POST'])
@login_required
def primary_calendar_sync():
    user_primary_calendar = current_user.primary_calendar
    if user_primary_calendar is None:
        raise BadRequest('기본 캘린더가 설정되지 않았습니다.')
    if user_primary_calendar.platform_id != GoogleOAuth2Provider.__platform_id__:
        raise BadRequest('현재는 구글 캘린더만 지원하고 있습니다.')

    credentials = list(filter(lambda x: x.platform_id == GoogleOAuth2Provider.__platform_id__,
                              current_user.platform_sessions))[0].tokens
    sync_google_calendar.apply_async((credentials, current_user.uid))
    return response_template('정상처리되었습니다.')


@app.route('/users/<uuid>', methods=['GET'])
def redirect_settings(uuid):
    user = User.query.filter(User.uuid==uuid).first()
    if user:
        login_user(user)
        return redirect(url_for('settings'))
    return redirect(url_for('index'))


@app.route('/faq', methods=['GET'])
def faq():
    return render_template('faq.html')


@app.route('/privacy', methods=['GET'])
def privacy():
    return render_template('privacy.html')


@app.route('/terms', methods=['GET'])
def terms():
    return render_template('terms.html')
