# -*- coding: utf-8 -*-

from flask import request
from flask.json import jsonify
from pastel_chat.connectors.redis import RedisType
from pastel_chat import db, response_template, sentry, get_redis
from pastel_chat.core.analyzer import UserRequestAnalyzer
from pastel_chat.core.conversation import log_conversation, \
    end_conversation, get_last_message_in_conversation
from pastel_chat.core.exceptions import AlreadyBegunConversationError
from pastel_chat.core.messages import BAD_REQUEST, TERMS_DENY, PLEASE_AGREE_TERMS, TERMS_AGREE, PLEASE_ADD_OAUTH
from pastel_chat.core.response import ConversationMode, ResponseGenerator, RandomResponseMaker
from pastel_chat.core.utils import serialize_message_additional, PositiveOrNegativeDetector
from pastel_chat.models import MessageType, Message
from pastel_chat.oauth.models import User, UserStatus
from pastel_chat.plusfriend import plusfriend
from pastel_chat.utils import get_or_create


@plusfriend.route('/message', methods=['POST'])
def receive_user_message():
    body = request.get_json()
    messenger_uid = body['user_key']
    request_message_type = body['type']
    request_message = body['content']

    if request_message_type != 'text':
        return jsonify({
            "message": {
                "text": BAD_REQUEST
            }
        })

    if request_message == TERMS_DENY:
        return jsonify({
            "message":{
                "text": PLEASE_AGREE_TERMS
            },
            "keyboard": {
                "type": "buttons",
                "buttons": [TERMS_AGREE, TERMS_DENY]
            }
        })

    request_user = get_or_create(
        db.session,
        User,
        messenger_uid=messenger_uid
    )

    user_platform_sessions = request_user.platform_sessions
    if request_message == TERMS_AGREE or \
                    len(user_platform_sessions) == 0:
        return jsonify({
            "message":{
                "text": PLEASE_ADD_OAUTH % (request_user.uuid)
            }
        })

    conversation_redis = get_redis(RedisType.CONVERSATIONS)
    def log_conversations(request_user, user_request, response):
        pipe = conversation_redis.pipeline()
        # 요청 기록
        log_conversation(pipe, request_user.uid, user_request.command_type,
                         user_request.message,
                         MessageType.REQUEST,
                         serialize_message_additional(user_request.request_type, request=user_request))
        # 응답 기록
        log_conversation(pipe, request_user.uid, user_request.command_type,
                         response.content,
                         MessageType.RESPONSE,
                         serialize_message_additional(response.content_type, response=response))
        pipe.execute()

    def question_again():
        last_message_in_conversation = \
            get_last_message_in_conversation(conversation_redis, request_user.uid)
        return jsonify({
            "message": {
                "text": last_message_in_conversation['content']
            }
        })

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

        return jsonify({
            "message": {
                "text": response.content
            }
        })
    except AlreadyBegunConversationError:
        response = question_again()
        log_conversations(request_user, user_request, response)
        return response
    except:
        sentry.captureException()
        user_request.is_positive = PositiveOrNegativeDetector.detect(user_request.message)

        random_response_maker = RandomResponseMaker(user_request)
        response = random_response_maker.make_response()

        if user_request.is_in_conversation:
            log_conversations(request_user, user_request, response)
        else:
            log_messages(request_user, user_request, response)

        return jsonify({
            "message": {
                "text": response.content
            }
        })


@plusfriend.route('/friend', methods=['POST'])
def registered_as_friend():
    body = request.get_json()
    user_key = body['user_key']

    joined_user = User.query.filter(User.messenger_uid==user_key).first()
    if joined_user:
        joined_user.status = UserStatus.NORMAL
    else:
        new_user = User(messenger_uid=user_key)  # 새로운 회원 가입
        db.session.add(new_user)
    db.session.commit()
    return response_template('정상처리되었습니다.')


@plusfriend.route('/friend/<user_key>', methods=['DELETE'])
def removed_from_friend(user_key):
    joined_user = User.query.filter(User.messenger_uid==user_key).first()
    joined_user.status = UserStatus.DEACTIVATED
    db.session.commit()
    return response_template('정상처리되었습니다.')


@plusfriend.route('/keyboard', methods=['GET'])
def initial_keyboard():
    return jsonify(
        {
            "type": "buttons",
            "buttons": [TERMS_AGREE, TERMS_DENY]
        }
    )
