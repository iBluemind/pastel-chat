# -*- coding: utf-8 -*-

from pastel_chat import get_redis, sentry, db
from pastel_chat.connectors.redis import RedisType
from pastel_chat.core.utils import PositiveOrNegativeDetector
from pastel_chat.core.analyzer import UserRequestAnalyzer
from pastel_chat.core.conversation import log_conversation, get_last_message_in_conversation, end_conversation
from pastel_chat.core.exceptions import AlreadyBegunConversationError
from pastel_chat.core.messages import NOT_YET_ADD_OAUTH, PLEASE_INPUT_INVITATION_CODE, PLEASE_ADD_OAUTH, \
    COMPLETE_ADD_OAUTH, INTRODUCE_LINDER, COMPLETE_SIGNUP, HELP_LINDER, README
from pastel_chat.core.response import ResponseGenerator, ConversationMode, RandomResponseMaker
from pastel_chat.core.utils import serialize_message_additional
from pastel_chat.models import InvitationCode, MessageType, Message
from pastel_chat.oauth.models import UserSignupStep


def _is_user_in_signup_steps(request_user):
    return request_user.signup_step_status is None or \
                request_user.signup_step_status < UserSignupStep.AFTER_READ_INTRODUCE


def _process_user_signup_steps(request_user, request_message):
    if request_user.invitation_code_id is None:
        input_code = InvitationCode.query.filter(InvitationCode.code == request_message).first()
        if input_code:
            request_user.invitation_code_id = input_code.id
            db.session.commit()
            return PLEASE_ADD_OAUTH % (request_user.uuid)
        return PLEASE_INPUT_INVITATION_CODE

    if len(request_user.platform_sessions) == 0:
        return NOT_YET_ADD_OAUTH

    if request_user.signup_step_status == UserSignupStep.COMPLETE_ADD_FIRST_OAUTH:
        request_user.signup_step_status = UserSignupStep.BEFORE_READ_INTRODUCE
        db.session.commit()
        return COMPLETE_ADD_OAUTH

    before_status = request_user.signup_step_status
    request_user.signup_step_status = UserSignupStep.AFTER_READ_INTRODUCE
    db.session.commit()

    if before_status == UserSignupStep.BEFORE_READ_INTRODUCE:
        is_positive = PositiveOrNegativeDetector.detect(request_message)
        if is_positive:
            return INTRODUCE_LINDER
        return COMPLETE_SIGNUP
    return README


def _process_dialog(request_user, request_message):
    conversation_redis = get_redis(RedisType.CONVERSATIONS)

    def log_conversations(request_user, user_request, response):
        pipe = conversation_redis.pipeline()
        command_type = getattr(user_request, 'command_type', None)
        # 요청 기록
        log_conversation(pipe, request_user.uid, command_type,
                         user_request.message,
                         MessageType.REQUEST,
                         serialize_message_additional(user_request.request_type, request=user_request))
        # 응답 기록
        log_conversation(pipe, request_user.uid, command_type,
                         response.content,
                         MessageType.RESPONSE,
                         serialize_message_additional(response.content_type, response=response))
        pipe.execute()

    def question_again():
        last_message_in_conversation = \
            get_last_message_in_conversation(conversation_redis, request_user.uid)
        return last_message_in_conversation['content']

    def log_messages(request_user, user_request, response):
        log_request = Message(
            user_request.message, request_user.uid, MessageType.REQUEST,
            serialize_message_additional(user_request.request_type, request=user_request)
        )
        db.session.add(log_request)
        log_response = Message(
            response.content, request_user.uid, MessageType.RESPONSE,
            serialize_message_additional(response.content_type, response=response)
        )
        db.session.add(log_response)
        db.session.commit()

    message_analyzer = UserRequestAnalyzer(request_message, request_user)
    user_request = message_analyzer.analyze()
    try:
        response_generator = ResponseGenerator(user_request)
        response = response_generator.make_response()

        if user_request.is_in_conversation:
            log_conversations(request_user, user_request, response)

        if response.conversation_mode == ConversationMode.BEGIN:
            if user_request.is_in_conversation:
                raise AlreadyBegunConversationError()
            log_conversations(request_user, user_request, response)

        if response.conversation_mode == ConversationMode.END:
            end_conversation(request_user.uid)

        if (not user_request.is_in_conversation) and \
                        response.conversation_mode != ConversationMode.BEGIN:
            log_messages(request_user, user_request, response)

        return response.content
    except AlreadyBegunConversationError:
        return question_again()
    except Exception as e:
        sentry.captureException()
        user_request.is_positive = PositiveOrNegativeDetector.detect(user_request.message)

        random_response_maker = RandomResponseMaker(user_request)
        response = random_response_maker.make_response()

        if user_request.is_in_conversation:
            log_conversations(request_user, user_request, response)
        else:
            log_messages(request_user, user_request, response)
        return response.content


def generate_response(request_user, request_message):
    if _is_user_in_signup_steps(request_user):
        return _process_user_signup_steps(request_user, request_message)
    if request_message == HELP_LINDER:
        return README % request_user.uuid
    return _process_dialog(request_user, request_message)
