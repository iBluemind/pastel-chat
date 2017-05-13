# -*- coding: utf-8 -*-

from flask import request
from flask.json import jsonify
from pastel_chat import db, response_template
from pastel_chat.core.messages import BAD_REQUEST
from pastel_chat.line.luis import generate_response
from pastel_chat.oauth.models import User, UserStatus
from pastel_chat.plusfriend import plusfriend
from pastel_chat.utils import get_or_create


@plusfriend.route('/message', methods=['POST'])
def receive_user_message():
    body = request.get_json()
    messenger_uid = body['user_key']
    request_message_type = body['type']
    request_message = body['content']

    def make_response(message):
        return jsonify({
            "message": {
                "text": message
            }
        })

    if request_message_type != 'text':
        return make_response(BAD_REQUEST)

    request_user = get_or_create(
        db.session,
        User,
        messenger_uid=messenger_uid
    )

    response_message = generate_response(request_user, request_message)
    return make_response(response_message)


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
