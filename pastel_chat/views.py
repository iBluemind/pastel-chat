# -*- coding: utf-8 -*-

import datetime
import httplib2
from dateutil.relativedelta import relativedelta
from flask import make_response, redirect, render_template, request, url_for, json
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
from pastel_chat.utils import get_or_create


@app.route('/login', methods=['GET'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
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
    return render_template('settings.html')


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
                    'user_uid': current_user.uid,
                    'timezone': calendar.get('timeZone')
                }

                if calendar.get('primary'):
                    current_user.primary_calendar_id = fetched_calendar.id

                for k, v in calendar_obj_properties.items():
                    setattr(fetched_calendar, k, v)
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
    def google_calendar_sync():
        credentials = list(filter(lambda x: x.platform_id == GoogleOAuth2Provider.__platform_id__,
                                  current_user.platform_sessions))[0].tokens
        credentials = OAuth2Credentials.from_json(credentials)
        http = credentials.authorize(httplib2.Http())
        service = build('calendar', 'v3', http=http)

        sync_tokens = None
        sync_request = service.events().list(calendarId=user_primary_calendar.platform_uuid)
        sync_manager = CalendarPlatformSync.query.filter(
            CalendarPlatformSync.calendar_id==user_primary_calendar.id
        ).first()

        sync_tokens = {}
        if sync_manager is not None:
            sync_tokens = sync_manager.tokens

        if sync_tokens.get('sync_token'):
            sync_request.syncToken = sync_tokens['sync_token']
            page_token = sync_tokens.get('page_token')
            if page_token:
                sync_request.pageToken = page_token
        else:
            now = datetime.datetime.now()
            one_year_ago = now - relativedelta(years=1)
            sync_request.timeMin = one_year_ago

        schedules_count = 0
        while True:
            events_result = sync_request.execute()
            events = events_result.get('items', [])
            if len(events) == 0:
                break

            schedules_count += len(events)
            for event in events:
                is_all_day = True if event['start'].get('date') else False
                started_at = DateTimeWithTimeZone(
                    event['start'].get('date') or \
                    event['start'].get('dateTime'),
                    event['start'].get('timeZone')
                )
                ended_at = DateTimeWithTimeZone(
                    event['end'].get('date') or \
                    event['end'].get('dateTime'),
                    event['end'].get('timeZone')
                )
                organizer = Person(
                    event['organizer'].get('displayName'),
                    event['organizer'].get('email'),
                    event['organizer'].get('id')
                )
                attendees = []
                if event.get('attendees'):
                    for attendee in event['attendees']:
                        fetched_attendee = Person(
                            attendee.get('displayName'),
                            attendee.get('email'),
                            attendee.get('id')
                        )
                        attendees.append(fetched_attendee.__dict__)
                reminders = []
                if event.get('reminder'):
                    for reminder in event['reminder']['overrides']:
                        reminders.append(reminder['minutes'])

                sensitivity = 0
                if event.get('visibility'):
                    sensitivities = {
                        'normal': 0,
                        'personal': 1,
                        'private': 2,
                        'confidential': 3,
                    }
                    sensitivity = sensitivities[event['visibility']]

                fetched_schedule = get_or_create(
                    db.session,
                    Schedule,
                    platform_uuid=event.get('id')
                )

                schedule_obj_properties = {
                    'title': event.get('summary'),
                    'platform_uuid': event.get('id'),
                    'description': event.get('description'),
                    'location': event.get('location'),
                    'is_all_day': 1 if is_all_day else 0,
                    'started_at': started_at.__dict__,
                    'ended_at': ended_at.__dict__,
                    'url': event.get('htmlLink'),
                    'online_meeting_url': event.get('hangoutLink'),
                    'organizer': organizer.__dict__,
                    'attendees': attendees,
                    'ical_uid': event.get('iCalUID'),
                    'is_cancelled': 1 if event.get('status') == 'cancelled' else 0,
                    'sensitivity': sensitivity,
                    'reminders': reminders
                }

                for k, v in schedule_obj_properties.items():
                    setattr(fetched_schedule, k, v)
            if events_result.get('nextPageToken') is None:
                break
            else:
                sync_tokens['page_token'] = events_result.get('nextPageToken')
                sync_request.pageToken = sync_tokens['page_token']
        new_sync_token = events_result.get('nextSyncToken')
        if new_sync_token:
            sync_tokens['sync_token'] = new_sync_token
            if sync_tokens.get('page_token'):
                del sync_tokens['page_token']
        if sync_manager:
            sync_manager.tokens = sync_tokens
        else:
            new_platform_sync = CalendarPlatformSync(
                sync_tokens, user_primary_calendar.id,
                GoogleOAuth2Provider.__platform_id__
            )
            db.session.add(new_platform_sync)
        history = CalendarPlatformSyncHistory(
            used_token=json.dumps(sync_tokens),
            calendar_id=user_primary_calendar.id,
            schedule_count=schedules_count,
            sync_by=PlatformSyncBy.USER,
            platform_id=GoogleOAuth2Provider.__platform_id__
        )
        db.session.add(history)
        db.session.commit()
    google_calendar_sync()
    return response_template('정상처리되었습니다.')


@app.route('/users/<uuid>', methods=['GET'])
def redirected_settings(uuid):
    user = User.query.filter(User.uuid==uuid).first()
    if user is not None:
        login_user(user)
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
