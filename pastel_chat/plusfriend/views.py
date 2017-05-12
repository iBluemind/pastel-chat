# -*- coding: utf-8 -*-

from flask import request
from flask.json import jsonify
from pastel_chat.connectors.redis import RedisType
from pastel_chat import db, response_template, sentry, get_redis
from pastel_chat.core.analyzer import UserRequestAnalyzer
from pastel_chat.core.conversation import log_conversation, \
    end_conversation, get_last_message_in_conversation
from pastel_chat.core.dialog import _receive_user_message
from pastel_chat.core.exceptions import AlreadyBegunConversationError
from pastel_chat.core.messages import BAD_REQUEST, PLEASE_ADD_OAUTH, PLEASE_INPUT_INVITATION_CODE, HELP_LINDER, README, \
    NOT_YET_ADD_OAUTH, COMPLETE_ADD_OAUTH, INTRODUCE_LINDER, COMPLETE_SIGNUP
from pastel_chat.core.response import ConversationMode, ResponseGenerator, RandomResponseMaker
from pastel_chat.core.utils import serialize_message_additional, PositiveOrNegativeDetector
from pastel_chat.models import MessageType, Message, InvitationCode
from pastel_chat.oauth.models import User, UserStatus, UserSignupStep
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

    request_user = get_or_create(
        db.session,
        User,
        messenger_uid=messenger_uid
    )

    response_message = _receive_user_message(request_user, request_message)
    return jsonify({
        'message': {
            'text': response_message
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
            "type": "text"
        }
    )
