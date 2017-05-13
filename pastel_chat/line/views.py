# -*- coding: utf-8 -*-

from flask import abort
from flask import request
from linebot.exceptions import InvalidSignatureError
from linebot.models import FollowEvent
from linebot.models import MessageEvent
from linebot.models import TextMessage
from linebot.models import TextSendMessage
from linebot.models import UnfollowEvent
from pastel_chat import db, response_template, handler, line_bot_api
from pastel_chat.core.dialog import generate_response
from pastel_chat.core.messages import BAD_REQUEST, PLEASE_ADD_OAUTH
from pastel_chat.oauth.models import User, UserStatus, Messenger
from pastel_chat.line import line
from pastel_chat.utils import get_or_create


@line.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

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

    response_message = generate_response(request_user, request_message)
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=response_message))


@handler.add(FollowEvent)
def registered_as_friend(event):
    joined_user = User.query.filter(User.messenger_uid == event.source.user_id).first()
    new_user = None
    if joined_user:
        joined_user.status = UserStatus.NORMAL
    else:
        new_user = User(messenger_uid=event.source.user_id, messenger=Messenger.LINE)  # 새로운 회원 가입
        db.session.add(new_user)
    user = new_user or joined_user
    user.invitation_code_id = 1
    db.session.commit()

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=PLEASE_ADD_OAUTH % (user.uuid)))


@handler.add(UnfollowEvent)
def removed_from_friend(event):
    joined_user = User.query.filter(User.messenger_uid == event.source.user_id).first()
    joined_user.status = UserStatus.DEACTIVATED
    db.session.commit()
