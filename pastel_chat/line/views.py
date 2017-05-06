# -*- coding: utf-8 -*-

from flask import abort
from flask import request
from flask.json import jsonify
from linebot.exceptions import InvalidSignatureError
from linebot.models import FollowEvent
from linebot.models import MessageEvent
from linebot.models import TextMessage
from linebot.models import TextSendMessage
from linebot.models import UnfollowEvent
from pastel_chat.connectors.redis import RedisType
from pastel_chat import db, response_template, sentry, get_redis, handler, line_bot_api
from pastel_chat.core.analyzer import UserRequestAnalyzer
from pastel_chat.core.conversation import log_conversation, \
    end_conversation, get_last_message_in_conversation
from pastel_chat.core.exceptions import AlreadyBegunConversationError
from pastel_chat.core.messages import BAD_REQUEST, PLEASE_ADD_OAUTH, PLEASE_INPUT_INVITATION_CODE, HELP_LINDER, README, \
    NOT_YET_ADD_OAUTH, COMPLETE_ADD_OAUTH, INTRODUCE_LINDER, COMPLETE_SIGNUP
from pastel_chat.core.response import ConversationMode, ResponseGenerator, RandomResponseMaker
from pastel_chat.core.utils import serialize_message_additional, PositiveOrNegativeDetector
from pastel_chat.models import MessageType, Message, InvitationCode
from pastel_chat.oauth.models import User, UserStatus, UserSignupStep
from pastel_chat.line import line
from pastel_chat.utils import get_or_create


@line.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return response_template('정상처리되었습니다.')


@handler.default()
def default(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=BAD_REQUEST))


@handler.add(MessageEvent, message=TextMessage)
def receive_user_message(event):
    messenger_uid = event.source.user_id
    request_message = event.message.text

    request_user = get_or_create(
        db.session,
        User,
        messenger_uid=messenger_uid
    )

    if request_user.signup_step_status is None or \
                    request_user.signup_step_status < UserSignupStep.AFTER_READ_INTRODUCE:
        if request_user.invitation_code_id is None:
            input_code = InvitationCode.query.filter(InvitationCode.code == request_message).first()
            if input_code:
                request_user.invitation_code_id = input_code.id
                db.session.commit()

                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=PLEASE_ADD_OAUTH % (request_user.uuid)))
                return

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=PLEASE_INPUT_INVITATION_CODE))
            return

        if len(request_user.platform_sessions) == 0:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=NOT_YET_ADD_OAUTH))
            return

        if request_user.signup_step_status == UserSignupStep.COMPLETE_ADD_FIRST_OAUTH:
            request_user.signup_step_status = UserSignupStep.BEFORE_READ_INTRODUCE
            db.session.commit()

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=COMPLETE_ADD_OAUTH))
            return

        if request_user.signup_step_status == UserSignupStep.BEFORE_READ_INTRODUCE:
            request_user.signup_step_status = UserSignupStep.AFTER_READ_INTRODUCE
            db.session.commit()
            is_positive = PositiveOrNegativeDetector.detect(request_message)
            if is_positive:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=INTRODUCE_LINDER))
                return

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=COMPLETE_SIGNUP))
            return

    if request_message == HELP_LINDER:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=README % request_user.uuid))
        return

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

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=response.content))
        return

    except AlreadyBegunConversationError:
        response = question_again()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=response))
        return
    except Exception as e:
        sentry.captureException()
        user_request.is_positive = PositiveOrNegativeDetector.detect(user_request.message)

        random_response_maker = RandomResponseMaker(user_request)
        response = random_response_maker.make_response()

        if user_request.is_in_conversation:
            log_conversations(request_user, user_request, response)
        else:
            log_messages(request_user, user_request, response)

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=response.content))
        return


@handler.add(FollowEvent)
def registered_as_friend(event):
    joined_user = User.query.filter(User.messenger_uid == event.source.user_id).first()
    new_user = None
    if joined_user:
        joined_user.status = UserStatus.NORMAL
    else:
        new_user = User(messenger_uid=event.source.user_id)  # 새로운 회원 가입
        db.session.add(new_user)
    db.session.commit()

    user = new_user or joined_user
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=PLEASE_ADD_OAUTH % (user.uuid)))


@handler.add(UnfollowEvent)
def removed_from_friend(event):
    joined_user = User.query.filter(User.messenger_uid == event.source.user_id).first()
    joined_user.status = UserStatus.DEACTIVATED
    db.session.commit()
