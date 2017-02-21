# -*- coding: utf-8 -*-

import datetime, json, httplib2
from celery import Celery
from dateutil.relativedelta import relativedelta
from googleapiclient.discovery import build
from oauth2client.client import OAuth2Credentials
from pastel_chat.oauth.provider import GoogleOAuth2Provider
from pastel_chat.utils import get_or_create
from pastel_chat.connectors.redis import RedisType, RedisConnector
from pastel_chat.models import PlatformSyncBy, CalendarPlatformSync, db, CalendarPlatformSyncHistory, \
    DateTimeWithTimeZone, Person, Schedule
from pastel_chat.oauth.models import User


def make_celery():
    from pastel_chat import app
    celery = Celery(broker=RedisConnector.REDIS_TYPES[RedisType.BROCKER].uri)
    celery.conf.update(app.config)
    TaskBase = celery.Task
    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
    return celery


tasks = make_celery()


@tasks.task
def sync_google_calendar(credentials, current_user_uid):
    current_user = User.query.get(current_user_uid)

    credentials = OAuth2Credentials.from_json(credentials)
    http = credentials.authorize(httplib2.Http())
    service = build('calendar', 'v3', http=http)

    sync_tokens = None
    user_primary_calendar = current_user.primary_calendar
    sync_request = service.events().list(calendarId=user_primary_calendar.platform_uuid)
    sync_manager = CalendarPlatformSync.query.filter(
        CalendarPlatformSync.calendar_id==user_primary_calendar.id,
        CalendarPlatformSync.user_uid==current_user.uid
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
                    'default': 0,
                    'public': 1,
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

            calendars = fetched_schedule.calendars
            is_in_this_calendar = True if \
                len(list(filter(lambda x:
                                x.platform_uuid==user_primary_calendar.platform_uuid,
                                                          calendars))) == 1 \
                            else False
            if not is_in_this_calendar:
                fetched_schedule.calendars.append(user_primary_calendar)

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
            GoogleOAuth2Provider.__platform_id__,
            current_user.uid
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
