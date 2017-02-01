# -*- coding: utf-8 -*-

import datetime, json
from pastel_chat.connectors.redis import RedisType
from pastel_chat import db, get_redis
from pastel_chat.models import Message, Conversation


def generate_conversation_id(uid):
    return 'conversation:%s' % uid


def is_user_in_conversation(conversation_redis, uid):
    conversation = conversation_redis.exists(generate_conversation_id(uid))
    return conversation


def get_last_message_in_conversation(conversation_redis, uid):
    last_message = conversation_redis.lindex(generate_conversation_id(uid), -1)
    if last_message:
        return json.loads(last_message.decode())


def end_conversation(uid):
    conversation_redis = get_redis(RedisType.CONVERSATIONS)
    current_conversation = is_user_in_conversation(conversation_redis, uid)
    if current_conversation:
        last_message = get_last_message_in_conversation(conversation_redis,
                                                        uid)
        new_conversation = Conversation(uid=uid,
                                command_type=last_message['command_type'])
        db.session.add(new_conversation)
        while True:
            fetched_message = conversation_redis.lpop(generate_conversation_id(uid))
            if fetched_message is None:
                break
            else:
                fetched_message = json.loads(fetched_message.decode())
            new_message = Message(fetched_message['content'], uid,
                                  fetched_message['message_type'],
                                  fetched_message['additional'],
                                  new_conversation.gid)
            db.session.add(new_message)
        db.session.commit()


def log_conversation(redis_pipe, uid, command_type,
                     content, message_type, additional):
    message = {
        'command_type': command_type,
        'content': content,
        'message_type': message_type,
        'additional': additional,
        'created_at': datetime.datetime.now().isoformat()
    }
    redis_pipe.rpush(generate_conversation_id(uid), json.dumps(message, ensure_ascii=False))
