import redis
from pastel_chat.connectors.access import AccessRedis


class RedisType(object):
    AUTH_SESSION = 0
    FORMATTED_TEXT = 1
    CONVERSATIONS = 2
    BROCKER = 3


class RedisConnector(object):
    REDIS_TYPES = {
        RedisType.AUTH_SESSION: AccessRedis(db=0),
        RedisType.FORMATTED_TEXT: AccessRedis(db=1),
        RedisType.CONVERSATIONS: AccessRedis(db=2),
        RedisType.BROCKER: AccessRedis(db=3)
    }

    def __init__(self, redis_type):
        access_redis = RedisConnector.REDIS_TYPES[redis_type]
        self.pool = self._get_connection_pool(
            access_redis.host,
            access_redis.port,
            access_redis.password,
            access_redis.db
        )

    def _get_connection_pool(self, host, port, password, db):
        return redis.ConnectionPool(host=host, port=port, password=password,
                                    db=db, encoding='utf-8')

    def get_redis(self):
        return redis.StrictRedis(connection_pool=self.pool)
