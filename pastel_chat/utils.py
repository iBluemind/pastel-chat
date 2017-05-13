# -*- coding: utf-8 -*-

import re
from sqlalchemy.sql import ClauseElement


def is_none(attribute):
    return True if attribute is None or attribute == '' else False


def convert2escape_character(str):
    str = re.sub(r"([=\(\)|\-!@~\"&/\\\^\$\=])", r"\\\1", str)
    return re.escape(str)


def random_generate_token(length=32):
    import random
    import string
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))


def add_months(src_date, months):
    import calendar
    import datetime

    month = src_date.month - 1 + months
    year = int(src_date.year + month / 12)
    month = month % 12 + 1
    day = min(src_date.day, calendar.monthrange(year, month)[1])
    return datetime.date(year, month, day)


def get_or_create(session, model, defaults=None, **kwargs):
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    else:
        params = dict((k, v) for k, v in kwargs.items() if not isinstance(v, ClauseElement))
        if defaults:
            params.update(defaults)
        instance = model(**params)
        session.add(instance)
        return instance


KAKAOTALK_USER_AGENT = 'KAKAOTALK'


import json, requests


def slack_notification(to, icon, body, botname, attachments=None):
        api_endpoint = ''
        payload = {
                'channel': '%s' % to,
                'text': body,
                'icon_emoji': icon,
                'mrkdwn': True,
                'username': botname
            }
        if attachments:
            payload['attachments'] = attachments
        requests.post(api_endpoint, data={
            'payload': json.dumps(payload, ensure_ascii=False)
        })


class JSONSerializable(object):
    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]


from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import ClauseElement
from sqlalchemy import literal

class Match(ClauseElement):
    def __init__(self, columns, value):
        self.columns = columns
        self.value = literal(value)

@compiles(Match)
def _match(element, compiler, **kw):
    return "MATCH (%s) AGAINST (\"%s*\" IN BOOLEAN MODE)" % (
        ", ".join(compiler.process(c, **kw) for c in element.columns),
        compiler.process(element.value)
    )
