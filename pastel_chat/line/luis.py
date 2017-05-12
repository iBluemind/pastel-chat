# -*- coding: utf-8 -*-

import abc
import datetime
import httplib2
import six
from flask import json
from googleapiclient.discovery import build
from oauth2client.client import OAuth2Credentials
from sqlalchemy.dialects import mysql

from pastel_chat.oauth.models import User
from pastel_chat.models import Calendar, Schedule
from pastel_chat.oauth.provider import GoogleOAuth2Provider
from pastel_chat.core.utils import PositiveOrNegativeDetector
from pastel_chat import luis, get_redis
from pastel_chat.core.dialog import _is_user_in_signup_steps, _process_user_signup_steps
from pastel_chat.core.messages import HELP_LINDER, README, CHECK_NEW_SCHEDULE, CANCEL_ADD_SCHEDULE, CONFIRM_ADD_SCHEDULE, \
    NO_CALENDAR_FOUND, CHECK_ADD_CALENDAR, CANCEL_ADD_CALENDAR, CONFIRM_ADD_CALENDAR
from pastel_chat.connectors.redis import RedisType
import dateutil.parser as dparser
from pastel_chat.tasks import insert_events_google_calendar
from pastel_chat.utils import Match

INTENT_ADD_NEW_SCHEDULE = 'Add New Schedule'
INTENT_FIND_SCHEDULE = 'Find Schedule'
INTENT_RECOMMENDATION = 'Recommendation'


def generate_conversation_id(uid):
    return 'conversation:%s' % uid


def is_user_in_conversation(conversation_redis, uid):
    conversation = conversation_redis.exists(generate_conversation_id(uid))
    return conversation


def get_last_message_in_conversation(conversation_redis, uid):
    last_message = conversation_redis.lindex(generate_conversation_id(uid), -1)
    if last_message:
        return json.loads(last_message.decode())


def end_conversation(uid):
    conversation_redis = get_redis(RedisType.LUIS_CONVERSATIONS)
    current_conversation = is_user_in_conversation(conversation_redis, uid)
    if current_conversation:
        while True:
            fetched_message = conversation_redis.lpop(generate_conversation_id(uid))
            if fetched_message is None:
                break


def log_conversation(redis_conn, uid, command_type, content, parsed):
    message = {
        'command_type': command_type,
        'content': content,
        'parsed': parsed,
        'created_at': datetime.datetime.now().isoformat()
    }
    redis_conn.rpush(generate_conversation_id(uid), json.dumps(message, ensure_ascii=False))


@six.add_metaclass(abc.ABCMeta)
class LuisIntentManager(object):
    def __init__(self, request_user, luis_response):
        self.user = request_user
        self.response = luis_response

    @abc.abstractmethod
    def parse(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def question(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def answer(self):
        raise NotImplementedError()


class AddNewScheduleManager(LuisIntentManager):

    __command_type__ = 'add_schedule'

    entities = {
        'Memo': '',
        'Hour': '12',
        'Month': '',
        'Day': '',
        'Daylight': 'AM',
        'Minute': '00',
        'Year': '2017',
        'DayIdiom': '',
        'Day of the Week': '',
        'WeekIdiom': '',
    }

    def parse(self):
        for entity in self.response.get_entities():
            if entity.get_type() == 'Daylight':
                if entity.get_name() == '오후' or '낮' or '저녁':
                    self.entities[entity.get_type()] = 'PM'
            else:
                self.entities[entity.get_type()] = entity.get_name()
        self.extracted_datetime = self._convert_datetime(
            self.entities['Year'],
            self.entities['Month'],
            self.entities['Day'],
            self.entities['Daylight'],
            self.entities['Hour'],
            self.entities['Minute'],
        )

    def _convert_datetime(self, year, month, day, daylight, hour, minute):
        return dparser.parse('%s-%s-%s %s:%s %s' % (
            year, month, day, hour, minute, daylight,
        ))

    def question(self):
        conversation_redis = get_redis(RedisType.LUIS_CONVERSATIONS)
        log_conversation(conversation_redis,
                         self.user.uid,
                         AddNewScheduleManager.__command_type__,
                         self.response.get_query(),
                         json.dumps(self.entities))
        extracted_title = self.entities['Memo']
        return CHECK_NEW_SCHEDULE % (
                self.user.username,
                ' '.join(extracted_title) if len(extracted_title) > 0 else '<인식불가>',
                self.extracted_datetime.strftime('%Y년 %m월 %d일 %H시 %M분'),
                '<인식불가>',
            )

    def answer(self):
        if PositiveOrNegativeDetector.detect(self.response.get_query()):
            def get_first_message_in_conversation():
                conversation_redis = get_redis(RedisType.LUIS_CONVERSATIONS)
                uid = self.user.uid
                message = conversation_redis.lindex(generate_conversation_id(uid), 0)
                return json.loads(message.decode())

            first = get_first_message_in_conversation()
            parsed = first['parsed']
            extracted_datetime = self._convert_datetime(
                parsed['Year'],
                parsed['Month'],
                parsed['Day'],
                parsed['Daylight'],
                parsed['Hour'],
                parsed['Minute'],
            )

            def datetime_format(extracted):
                korean_utctime = '+09:00'
                formatted = extracted.strftime('%Y-%m-%dT%H:%M:%S')
                return {
                    'dateTime': '%s%s' % (formatted, korean_utctime),
                    'timeZone': 'Asia/Seoul',
                }

            def date_format(extracted):
                formatted = extracted.strftime('%Y-%m-%d')
                return {
                    'date': '%s' % formatted,
                    'timeZone': 'Asia/Seoul',
                }

            if extracted_datetime.strftime('%H:%M:%S') == '12:00:00':
                start = date_format(extracted_datetime)
                end = date_format(extracted_datetime)
            else:
                start = datetime_format(extracted_datetime)
                after_one_hour = extracted_datetime + datetime.timedelta(hours=1)
                end = datetime_format(after_one_hour)

            new_event = {
                'summary': parsed['Memo'],
                'description': first['content'],
                'start': start,
                'end': end
            }
            self._add_to_google_calendar(new_event)
            return CONFIRM_ADD_SCHEDULE
        return CANCEL_ADD_SCHEDULE

    def _add_to_google_calendar(self, new_event):
        credential = list(filter(lambda x: x.platform_id ==
                              GoogleOAuth2Provider.__platform_id__,
                              self.user.platform_sessions))[0].tokens
        credentials = OAuth2Credentials.from_json(credential)
        http = credentials.authorize(httplib2.Http())
        service = build('calendar', 'v3', http=http)
        service.events().insert(calendarId='primary', body=new_event).execute()


class FindScheduleManager(LuisIntentManager):

    __command_type__ = 'find_schedule'

    entities = {
        'Title': ''
    }

    def parse(self):
        for entity in self.response.get_entities():
            self.entities[entity.get_type()] = entity.get_name()

    def question(self):
        conversation_redis = get_redis(RedisType.LUIS_CONVERSATIONS)

        calendar_title = self.entities['Title']
        calendar_title = calendar_title.replace(' ', '')
        q = Calendar.query.filter(Match([Calendar.name], calendar_title))
        found_calendar = q.first()

        if found_calendar is None:
            return NO_CALENDAR_FOUND % self.user.username

        log_conversation(conversation_redis,
                         self.user.uid,
                         FindScheduleManager.__command_type__,
                         self.response.get_query(),
                         json.dumps({'found_calendar_id': found_calendar.id}))

        schedules_count = Schedule.query.filter(Schedule.calendars.any(id=found_calendar.id)).count()
        return CHECK_ADD_CALENDAR % (self.user.username, found_calendar.name, schedules_count)

    def answer(self):
        if PositiveOrNegativeDetector.detect(self.response.get_query()):
            def get_first_message_in_conversation():
                conversation_redis = get_redis(RedisType.LUIS_CONVERSATIONS)
                uid = self.user.uid
                message = conversation_redis.lindex(generate_conversation_id(uid), 0)
                return json.loads(message.decode())

            first = get_first_message_in_conversation()
            calendar_id = first['found_calendar_id']
            schedules = Schedule.query.filter(Schedule.calendars.any(id=calendar_id)).all()

            current_user = User.query.filter(User.uid==self.user.uid).first()
            credentials = list(filter(lambda x: x.platform_id == GoogleOAuth2Provider.__platform_id__,
                                      current_user.platform_sessions))[0].tokens

            insert_events_google_calendar.apply_async((credentials, current_user.uid, schedules))

            return CONFIRM_ADD_CALENDAR
        return CANCEL_ADD_CALENDAR


class RecommendationManager(LuisIntentManager):

    __command_type__ = 'recommendation'

    entities = {
        'Keyword': '',
        'MonthIdiom': '',
        'Month': '',
        'Day': '',
        'Daylight': '',
    }

    def parse(self):
        for entity in self.response.get_entities():
            self.entities[entity.get_type()] = entity.get_name()

    def question(self):
        pass

    def answer(self):
        pass


class LuisParserFactory(object):
    managers = {
        INTENT_ADD_NEW_SCHEDULE: AddNewScheduleManager,
        INTENT_FIND_SCHEDULE: FindScheduleManager,
        INTENT_RECOMMENDATION: RecommendationManager
    }

    @staticmethod
    def get_parser(intent):
        return LuisParserFactory.managers[intent]


def _process_dialog(request_user, request_message):
    res = luis.predict(request_message)
    intent = res.get_top_intent().get_name()

    manager_cls = LuisParserFactory.get_parser(intent)
    manager = manager_cls(request_user, res)
    manager.parse()

    conversation_redis = get_redis(RedisType.LUIS_CONVERSATIONS)
    if is_user_in_conversation(conversation_redis, request_user.uid):
        end_conversation(request_user.uid)
        return manager.answer()
    return manager.question()


def generate_response(request_user, request_message):
    if _is_user_in_signup_steps(request_user):
        return _process_user_signup_steps(request_user, request_message)
    if request_message == HELP_LINDER:
        return README % request_user.uuid
    return _process_dialog(request_user, request_message)
