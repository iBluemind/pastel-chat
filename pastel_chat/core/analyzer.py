# -*- coding: utf-8 -*-

import re
from pastel_chat.connectors.redis import RedisType
from pastel_chat.core.response import CommandType
from pastel_chat.core.utils import NLPHelper, UserRequestType, PositiveOrNegativeDetector
from pastel_chat import get_redis
from pastel_chat.core.conversation import is_user_in_conversation, \
    get_last_message_in_conversation


class UserRequest(object):
    def __init__(self, message, user):
        self.message = message
        self.user = user
        self.is_in_conversation = False

    @property
    def is_positive(self):
        return self._is_positive

    @is_positive.setter
    def is_positive(self, is_positive):
        self._is_positive = is_positive

    @property
    def request_type(self):
        return self._request_type

    @request_type.setter
    def request_type(self, request_type):
        self._request_type = request_type

    @property
    def last_conversation_message(self):
        return self._last_conversation_message

    @last_conversation_message.setter
    def last_conversation_message(self, last_conversation_message):
        self._last_conversation_message = last_conversation_message


class UserRequestAnalyzer(object):

    command_types = {
        ('등록해', '추가해', '저장해'): CommandType.ADD_NEW_SCHEDULE
    }

    def __init__(self, message, user):
        self.message = message
        self.user = user
        self.conversation_redis = get_redis(RedisType.CONVERSATIONS)
        grammer = '''
            VP: {<NNG><XSV\+E.*>+<VX\+EC>?}            # 동사구
            NP: {<N.*>*<XSN|XSV|XSA>?}                 # 명사구
        '''
        self.helper = NLPHelper(message, tagger_selector='mecab',
                                grammer=grammer)

    def analyze(self):
        self.user_request = user_request = UserRequest(self.message, self.user)
        command_type = self._extract_command_type()
        if command_type:
            user_request.request_type = UserRequestType.COMMAND
            user_request.command_type = command_type
        else:
            user_request.request_type = UserRequestType.UNKNOWN
            user_request.is_positive = PositiveOrNegativeDetector.detect(self.message)

        if self.is_in_conversation:
            user_request.is_in_conversation = True
            user_request.last_conversation_message = self._get_last_message_in_conversation()
        return user_request

    @property
    def is_in_conversation(self):
        if getattr(self, '_is_in_conversation', None) is None:
            self._is_in_conversation = \
                is_user_in_conversation(self.conversation_redis, self.user.uid)
        return self._is_in_conversation

    def _get_last_message_in_conversation(self):
        return get_last_message_in_conversation(self.conversation_redis, self.user.uid)

    def _extract_verb_phrases(self):
        chunks = self.helper.extract_chunks(lambda subtree:
                                            re.match(r'^VP', subtree.label()))
        if chunks:
            return [''.join((e[0] for e in list(chunk))) for chunk in chunks]

    def _extract_command_type(self):
        extracted_verb_phrases = self._extract_verb_phrases()
        for verb_keywords, command_type in self.command_types.items():
            for verb_keyword in verb_keywords:
                for pre_defined_verb_phrases in extracted_verb_phrases:
                    if verb_keyword in pre_defined_verb_phrases:
                        return command_type
