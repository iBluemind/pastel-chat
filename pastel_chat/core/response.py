# -*- coding: utf-8 -*-

import abc, re, six, \
        dateutil.parser as dparser
import json
from datetime import timedelta
import httplib2, random
from googleapiclient.discovery import build
from oauth2client.client import OAuth2Credentials
from pastel_chat.connectors.redis import RedisType
from pastel_chat.core.conversation import generate_conversation_id
from pastel_chat.core.utils import PlaceWordsDatabase, NLPHelper, UserRequestType, \
    CommandType, PositiveOrNegativeDetector
from pastel_chat import get_es, get_redis
from pastel_chat.oauth.provider import GoogleOAuth2Provider
from pastel_chat.core.messages import formatted_response


class ConversationMode(object):
    BEGIN = 0
    END = 1
    INHERIT = 2


class GeneratedResponseType(object):
    FORMATTED = 'formatted'
    RANDOM = 'random'


class GeneratedResponse(object):
    def __init__(self, conversation_mode, content, **kwargs):
        self.conversation_mode = conversation_mode
        self.content = content
        if kwargs.get('formatted_text_id'):
            self.content_type = GeneratedResponseType.FORMATTED
            self.formatted_text_id = kwargs['formatted_text_id']
        else:
            self.content_type = GeneratedResponseType.RANDOM


@six.add_metaclass(abc.ABCMeta)
class ResponseMaker(object):
    def __init__(self, user_request):
        self.user_request = user_request

    @abc.abstractmethod
    def make_response(self):
        raise NotImplementedError('Please implement this method!')


class RandomResponseMaker(ResponseMaker):

    positive_messages = (
        '감사합니다. 일정 관리에 최선을 다하겠습니다.',
        '계속해서 발전하고 있는 노력파 봇입니다.',
        '제가 천사 유저를 만났군요, 저는 행복한 봇입니다.',
        '넓은 아량을 베풀어 주셔서 감사드립니다.',
        '항상 감사합니다.'
    )

    negative_messages = (
        '죄송합니다. 요청하신 사항은 도움 드리기 어렵습니다.',
        "아직 부족한 '봇' 입니다, 아량을 베풀어 주세요.",
        '아직 배우지 못한 단어 입니다.',
        '더 노력하는 봇이 되겠습니다',
        '못 들은 걸로 하겠습니다.',
    )

    @property
    def message(self):
        return self.user_request.message

    def make_response(self):
        if self.user_request.is_positive:
            message = random.choice(self.positive_messages)
        else:
            message = random.choice(self.negative_messages)
        return GeneratedResponse(
            ConversationMode.INHERIT,
            message
        )


class NewScheduleResponseMaker(ResponseMaker):

    __command_type__ = CommandType.ADD_NEW_SCHEDULE

    def __init__(self, user_request):
        super().__init__(user_request)
        self.place_searcher = PlaceWordsDatabase(get_es())

    @property
    def user(self):
        return self.user_request.user

    @property
    def parsed_chunks(self):
        return self.helper.parsed_chunks

    def create_nlp_helper(self, message):
        grammer = '''
                    X: {(<SN><SC|SY>)?<SN><SC|SY><SN>}
                    Y1: {<NNG>?<SN><NNBC>}
                    Y2: {<NR>*<NNBC>}
                    Z: {<Y><SY><Y>}
                    VP: {<NNG><XSV\+E.*>+<VX\+EC>?}            # 동사구
                    NP: {<N.*>*<XSN|XSV|XSA>?}                 # 명사구
                '''
        self.helper = NLPHelper(message,
                                tagger_selector='mecab', grammer=grammer)

    def make_response(self):
        if self.user_request.is_in_conversation:
            return self._answer()
        else:
            return self._question()

    def _question(self):
        self.create_nlp_helper(self.user_request.message)
        extracted_datetime, extracted_places, extracted_title = self.extract()
        response = formatted_response['check_new_schedule']
        username = self.user.first_name or self.user.username
        return GeneratedResponse(
            ConversationMode.BEGIN,
            str(response) % (
                username,
                ' '.join(extracted_title) if len(extracted_title) > 0 else '<인식불가>',
                extracted_datetime.strftime('%Y년 %m월 %d일 %H시 %M분'),
                ' '.join(extracted_places) if len(extracted_places) > 0 else '<인식불가>',
            ),
            formatted_text_id=response.id
        )

    def _answer(self):
        if PositiveOrNegativeDetector.detect(self.user_request.message):
            response = formatted_response['confirm_add_schedule']

            def get_first_message_in_conversation():
                conversation_redis = get_redis(RedisType.CONVERSATIONS)
                uid = self.user.uid
                message = conversation_redis.lindex(generate_conversation_id(uid), 0)
                return json.loads(message.decode())['content']

            first_message = get_first_message_in_conversation()
            self.create_nlp_helper(first_message)
            extracted_datetime, extracted_places, extracted_title = self.extract()

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
                after_one_hour = extracted_datetime + timedelta(hours=1)
                end = datetime_format(after_one_hour)

            new_event = {
                'summary': extracted_title,
                'location': extracted_places,
                'description': first_message,
                'start': start,
                'end': end
            }
            self._add_to_google_calendar(new_event)
        else:
            response = formatted_response['cancel_add_schedule']
        return GeneratedResponse(
            ConversationMode.END,
            str(response),
            formatted_text_id=response.id
        )

    def _extract_datetime(self):
        def convert(converted_date):
            # return datetime.datetime.strptime(converted_date, '%Y-%m-%d %p %I:%M')
            return dparser.parse(converted_date)

        def _case1(expression, user_message=None):
            return re.sub(r'[\.\-\/]', '-', expression)

        def _case2(expression, user_message=None):
            # TODO: 체이닝되도록(파이프라이닝하도록)
            converted_date = re.sub(r'\b[\s]\b(?=(\d+)(년|월|일))', '-', expression)
            converted_date = re.sub(r'[년월일분]', '', converted_date)
            converted_date = re.sub(r'[시]$', ':00', converted_date)
            converted_date = re.sub(r'[시]\s', ':', converted_date)
            converted_date = re.sub(r'(오전|아침)(?P<time>\d+:\d+)', r'\g<time>AM', converted_date)
            return re.sub(r'(오후|낮|저녁)(?P<time>\d+:\d+)', r'\g<time>PM ', converted_date)

        def _case3(expression, user_message=None):
            matched = re.findall(r'([가-힣]+)(년|월|일|시|분)(?=\s)', user_message)
            converted_date = expression
            # 월 디텍션
            if len(re.findall(r'([가-힣]+)(월)', converted_date)) == 0:
                month_expression = list(filter(lambda x: x[1] == '월', matched))
                if month_expression:
                    month_expression = '%s \g<day>' % ''.join(''.join(m) for m in month_expression)
                    converted_date = re.sub(r'(?P<day>[가-힣]+일)', month_expression, converted_date)
            # 시 디텍션
            if len(re.findall(r'([가-힣]+)(시)', converted_date)) == 0:
                time_expression = list(filter(lambda x: x[1] == '시', matched))
                if time_expression:
                    time_expression = '\g<day> %s' % ''.join(''.join(t) for t in time_expression)
                    converted_date = re.sub(r'(\s시)', '', converted_date)
                    converted_date = re.sub(r'(?P<day>[가-힣]+일)', time_expression, converted_date)
            # TODO: 한글문자열을 숫자로 바꿔야함
            return converted_date

        def process(user_message=None):
            cases = {
                'X': _case1,
                'Y1': _case2,
                'Y2': _case3,
            }
            for case in cases.keys():
                chunks = self.helper.extract_chunks(lambda subtree: subtree.label() == case)
                extracted = ' '.join(''.join((e[0] for e in list(chunk))) for chunk in chunks)
                if len(extracted) > 0:
                    if case == 'Y2':
                        return cases[case](extracted, user_message)
                    return cases[case](extracted)
            raise ValueError('Can\'t recognize case!')

        converted_date = process(self.helper.message)
        if converted_date:
            calc_time = convert(converted_date)
            return calc_time

    def _extract_places(self):
        places = []
        def search(chunk):
            return self.place_searcher.search(chunk)
        chunks = self.helper.extract_chunks(lambda subtree: re.match(r'^N.*', subtree.label()))
        if chunks:
            chunks = [''.join((e[0] for e in list(chunk))) for chunk in chunks]
            for chunk in chunks:
                results = search(chunk)
                count = results[0]
                # TODO: 정확도 개선 필요..보다도 사실 걍 디비 많이 쌓으면 댐..;;
                if count > 0:
                    places.append(chunk)
            return places

    def _extract_title(self):
        ignore_words = ['린더', '린더야', '야']
        words = []
        chunks = self.helper.extract_chunks(lambda subtree: re.match(r'^NP', subtree.label()))
        if chunks:
            chunks = [''.join((e[0] for e in list(chunk))) for chunk in chunks]
            for chunk in chunks:
                # TODO: 글로벌 제외 키워드 설정할 수 있도록 해야
                if chunk not in ignore_words:
                    words.append(chunk)
            return words

    def extract(self):
        # TODO: 이미 사용한 청크들은 제거하도록 해야함

        # 시간추출
        extracted_datetime = self._extract_datetime()
        # 장소추출
        extracted_places = self._extract_places()
        # 내용추출
        extracted_title = self._extract_title()
        return extracted_datetime, extracted_places, extracted_title

    def _add_to_google_calendar(self, new_event):
        credential = list(filter(lambda x: x.platform_id ==
                              GoogleOAuth2Provider.__platform_id__,
                              self.user.platform_sessions))[0].tokens
        credentials = OAuth2Credentials.from_json(credential)
        http = credentials.authorize(httplib2.Http())
        service = build('calendar', 'v3', http=http)
        service.events().insert(calendarId='primary', body=new_event).execute()


class ResponseGenerator(object):

    command_type_response_makers = {
        CommandType.ADD_NEW_SCHEDULE: NewScheduleResponseMaker
    }

    def __init__(self, user_request):
        self.user_request = user_request

    def make_response(self):
        if self.user_request.request_type == UserRequestType.COMMAND:
            maker_cls = self.command_type_response_makers[self.user_request.command_type]
            maker = maker_cls(self.user_request)
        else:
            maker = RandomResponseMaker(self.user_request)
        return maker.make_response()
