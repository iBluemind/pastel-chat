from config import MYSQL_DATABASE, MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, \
                   REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_DEFAULT_DB_NUMBER, \
                   ELASTIC_SEARCH_PORT, ELASTIC_SEARCH_HOST, ELASTIC_SEARCH_INDEX


class AccessDAO(object):
    def __init__(self, driver, db=None, host=None,
                       user=None, password=None, port=None):
        self.driver = driver
        self._db = db
        self._host = host
        self._user = user
        self._password = password
        self._port = port

    @property
    def db(self):
        if getattr(self, '_db', None) is None:
            self._db = MYSQL_DATABASE
        return self._db

    @property
    def host(self):
        if getattr(self, '_host', None) is None:
            self._host = MYSQL_HOST
        return self._host

    @property
    def port(self):
        if getattr(self, '_port', None) is None:
            self._port = MYSQL_PORT
        return self._port

    @property
    def user(self):
        if getattr(self, '_user', None) is None:
            self._user = MYSQL_USER
        return self._user

    @property
    def password(self):
        if getattr(self, '_password', None) is None:
            self._password = MYSQL_PASSWORD
        return self._password

    @property
    def uri(self):
        return 'mysql+%s://%s:%s@%s:%s/%s?charset=utf8mb4&use_unicode=0' % (
            self.driver, self.user, self.password, self.host, self.port, self.db
        )


class AccessRedis(object):
    def __init__(self, host=None, port=None, password=None, db=None):
        self._host = host
        self._port = port
        self._password = password
        self._db = db

    @property
    def host(self):
        host = self._host
        if host is None:
            host = REDIS_HOST
        return host

    @property
    def port(self):
        port = self._port
        if port is None:
            port = REDIS_PORT
        return port

    @property
    def password(self):
        password = self._password
        if password is None:
            password = REDIS_PASSWORD
        return password

    @property
    def db(self):
        db = self._db
        if db is None:
            db = REDIS_DEFAULT_DB_NUMBER
        return db

    @property
    def uri(self):
        return 'redis://:%s@%s:%s/%s' % (
            self.password, self.host, self.port, self.db
        )


class AccessElasticSearch(object):
    def __init__(self, host=None, port=None):
        self._host = host
        self._port = port

    @property
    def host(self):
        if getattr(self, '_host', None) is None:
            self._host = ELASTIC_SEARCH_HOST
        return self._host

    @property
    def port(self):
        if getattr(self, '_port', None) is None:
            self._port = ELASTIC_SEARCH_PORT
        return self._port

    @property
    def uri(self):
        return 'http://%s:%s' % (
            self.host, self.port
        )
