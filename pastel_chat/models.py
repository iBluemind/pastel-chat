# -*- coding: utf-8 -*-

import datetime
from sqlalchemy import func
from pastel_chat import db
from pastel_chat.utils import random_generate_token

user_hashtag = db.Table(
                        'user_hashtag',
                            db.Column('user_uid', db.Integer, db.ForeignKey('user.uid')),
                            db.Column('hashtag_id', db.Integer, db.ForeignKey('hashtag.id'))
                    )


schedule_schedule_recurrence = db.Table(
                        'schedule_schedule_recurrence',
                            db.Column('schedule_id', db.Integer, db.ForeignKey('schedule.id')),
                            db.Column('schedule_rid', db.Integer,
                                            db.ForeignKey('schedule_recurrence.id'))
                    )


calendar_schedule = db.Table(
                        'calendar_schedule',
                            db.Column('calendar_id', db.Integer, db.ForeignKey('calendar.id')),
                            db.Column('schedule_id', db.Integer,
                                            db.ForeignKey('schedule.id'))
                    )


class Conversation(db.Model):

    __tablename__ = 'conversation'

    gid = db.Column(db.String(32), primary_key=True)
    uid = db.Column(db.Integer, db.ForeignKey('user.uid'), nullable=True)
    command_type = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, onupdate=func.current_timestamp())
    messages = db.relationship('Message', backref='conversation', lazy='dynamic')

    def __init__(self, uid, command_type):
        self.gid = self._generate_gid()
        self.uid = uid
        self.command_type = command_type
        self.created_at = datetime.datetime.now()

    def _generate_gid(self):
        return random_generate_token()


class MessageType(object):
    REQUEST = 0
    RESPONSE = 1


class Message(db.Model):

    __tablename__ = 'message'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    content = db.Column(db.Text, nullable=True)
    uid = db.Column(db.Integer,
                                  db.ForeignKey('user.uid'), nullable=False)
    message_gid = db.Column(db.String(32),
                          db.ForeignKey('conversation.gid'), nullable=True)
    message_type = db.Column(db.SmallInteger, nullable=True)
    additional = db.Column(db.JSON)
    created_at = db.Column(db.DateTime)

    def __init__(self, content, uid, message_type, additional, message_gid=None):
        self.content = content
        self.uid = uid
        self.message_type = message_type
        self.additional = additional
        self.message_gid = message_gid
        self.created_at = datetime.datetime.now()


class PlatformSyncBy(object):
    USER = 'user'
    PASTEL = 'pastel'
    ADMIN = 'admin'


class CalendarPlatformSyncHistory(db.Model):

    __tablename__ = 'calendar_platform_sync_history'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    used_token = db.Column(db.Text, nullable=True)
    calendar_id = db.Column(db.Integer,
                                  db.ForeignKey('calendar.id'), nullable=True)
    platform_id = db.Column(db.Integer,
                                  db.ForeignKey('platform.id'), nullable=False)
    schedule_count = db.Column(db.Integer, default=0)
    sync_by = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime)

    def __init__(self, used_token, calendar_id, platform_id, schedule_count, sync_by):
        self.used_token = used_token
        self.calendar_id = calendar_id
        self.platform_id = platform_id
        self.schedule_count = schedule_count
        self.sync_by = sync_by
        self.created_at = datetime.datetime.now()


class CalendarPlatformSync(db.Model):

    __tablename__ = 'calendar_platform_sync'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tokens = db.Column(db.JSON, nullable=True)
    calendar_id = db.Column(db.Integer,
                               db.ForeignKey('calendar.id'), nullable=True)
    platform_id = db.Column(db.Integer,
                                  db.ForeignKey('platform.id'), nullable=False)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, onupdate=func.current_timestamp())

    def __init__(self, tokens, calendar_id, platform_id):
        self.tokens = tokens
        self.calendar_id = calendar_id
        self.platform_id = platform_id
        self.created_at = datetime.datetime.now()


class CalendarListPlatformSync(db.Model):

    __tablename__ = 'calendar_list_platform_sync'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tokens = db.Column(db.JSON, nullable=True)
    user_uid = db.Column(db.Integer,
                               db.ForeignKey('user.uid'), nullable=False)
    platform_id = db.Column(db.Integer,
                                  db.ForeignKey('platform.id'), nullable=False)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, onupdate=func.current_timestamp())

    def __init__(self, tokens, user_uid, platform_id):
        self.tokens = tokens
        self.user_uid = user_uid
        self.platform_id = platform_id
        self.created_at = datetime.datetime.now()


class HashTag(db.Model):

    __tablename__ = 'hashtag'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, onupdate=func.current_timestamp())

    def __init__(self, name):
        self.name = name
        self.created_at = datetime.datetime.now()


class Region(db.Model):

    __tablename__ = 'region'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(10), nullable=True)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, onupdate=func.current_timestamp())

    def __init__(self, name):
        self.name = name
        self.created_at = datetime.datetime.now()


class AttachedFile(db.Model):

    __tablename__ = 'attached_file'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(256), nullable=True)
    path = db.Column(db.Text, nullable=True)
    mime_type = db.Column(db.Text, nullable=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedule.id'), nullable=False)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, onupdate=func.current_timestamp())

    def __init__(self, name, path, mime_type, schedule_id):
        self.name = name
        self.path = path
        self.mime_type = mime_type
        self.schedule_id = schedule_id
        self.created_at = datetime.datetime.now()


class ScheduleRecurrence(db.Model):

    __tablename__ = 'schedule_recurrence'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, onupdate=func.current_timestamp())

    def __init__(self, name):
        self.name = name
        self.created_at = datetime.datetime.now()


class ScheduleSenstivity(object):
    NORMAL = 0
    PERSONAL = 1
    PRIVATE = 2
    CONFIDENTIAL = 3


class DateTimeWithTimeZone(object):
    def __init__(self, datetime, timezone):
        self.datetime = datetime
        self.timezone = timezone


class Person(object):
    def __init__(self, name, email, platform_uid):
        self.name = name
        self.email = email
        self.platform_uid = platform_uid


class Schedule(db.Model):

    __tablename__ = 'schedule'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    platform_uuid = db.Column(db.String(256), unique=True, nullable=False)
    title = db.Column(db.Text, nullable=True)
    description = db.Column(db.Text, nullable=True)
    location = db.Column(db.Text, nullable=True)
    is_all_day = db.Column(db.SmallInteger)
    started_at = db.Column(db.JSON, nullable=True)
    ended_at = db.Column(db.JSON, nullable=True)
    url = db.Column(db.Text, nullable=True)
    online_meeting_url = db.Column(db.Text, nullable=True)
    organizer = db.Column(db.JSON, nullable=True)
    attendees = db.Column(db.JSON, nullable=True)
    ical_uid = db.Column(db.String(256), nullable=True)
    is_cancelled = db.Column(db.SmallInteger)
    reminders = db.Column(db.JSON, nullable=True)
    sensitivity = db.Column(db.SmallInteger)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, onupdate=func.current_timestamp())
    attached_files = db.relationship('AttachedFile', backref='schedule', lazy='dynamic')
    schedule_recurrences = db.relationship('ScheduleRecurrence', secondary=schedule_schedule_recurrence,
                                  backref=db.backref('schedules', lazy='dynamic'))

    def __init__(self, platform_uuid, title=None, description=None, location=None, is_all_day=None, scheduled_at=None,
                 started_at=None, ended_at=None, url=None, online_meeting_url=None, organizer=None, attendees=None,
                 ical_uid=None, is_cancelled=None, sensitivity=None, reminders=None):
        self.title = title
        self.platform_uuid = platform_uuid
        self.description = description
        self.location = location
        self.is_all_day = is_all_day
        self.scheduled_at = scheduled_at
        self.started_at = started_at
        self.ended_at = ended_at
        self.url = url
        self.online_meeting_url = online_meeting_url
        self.organizer = organizer
        self.attendees = attendees
        self.ical_uid = ical_uid
        self.is_cancelled = is_cancelled
        self.sensitivity = sensitivity
        self.reminders = reminders
        self.created_at = datetime.datetime.now()


class Calendar(db.Model):

    __tablename__ = 'calendar'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    platform_uuid = db.Column(db.String(256), unique=True, nullable=False)
    name = db.Column(db.String(50), nullable=True)
    platform_id = db.Column(db.Integer, db.ForeignKey('platform.id'), nullable=False)
    user_uid = db.Column(db.Integer,
                                    db.ForeignKey('user.uid'), nullable=True)
    timezone = db.Column(db.Text, nullable=True)
    schedules = db.relationship('Schedule', secondary=calendar_schedule,
                                                 backref=db.backref('calendars', lazy='dynamic'))
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, onupdate=func.current_timestamp())

    def __init__(self, platform_uuid, platform_id, name=None, user_uid=None, timezone=None):
        self.platform_uuid = platform_uuid
        self.name = name
        self.platform_id = platform_id
        self.user_uid = user_uid
        self.timezone = timezone
        self.created_at = datetime.datetime.now()
