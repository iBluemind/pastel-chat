import pymysql
from contextlib import contextmanager
from sqlalchemy import event, create_engine
from sqlalchemy.exc import DisconnectionError
from sqlalchemy.orm import sessionmaker
from pastel_chat.connectors.access import AccessDAO


class DaoType(object):
    PRODUCTION = 0
    DEV = 1
    LOCAL = 2


class RawPyMySQL(object):
    def __init__(self, access_dao):
        self.access_dao = access_dao

    def _create_connection(self, access_dao):
        return pymysql.connect(
            db=access_dao.db, host=access_dao.host, user=access_dao.user, password=access_dao.password,
            port=access_dao.port, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor,
            use_unicode=True
        )

    @property
    def connection(self):
        if not self._connection:
            self._connection = self._create_connection(self.access_dao)
        return self._connection

    def close(self):
        if self._connection:
            self._connection.close()


class RawSQLAlchemy(object):
    def __init__(self, access_dao, **kwargs):
        self.access_dao = access_dao
        self.pool_size = kwargs.get('POOL_SIZE') or 10
        self.pool_recycle = kwargs.get('POOL_RECYCLE') or 7200

    def _create_engine(self, access_dao, pool_size=None, pool_recycle=None):
        return create_engine(access_dao.uri,
                                    pool_size=pool_size,
                                    pool_recycle=pool_recycle)

    def _sessionmaker(self, engine):
        return sessionmaker(bind=engine)

    @property
    def engine(self):
        if getattr(self, '_engine', None) is None:
            self._engine = self._create_engine(self.access_dao,
                                pool_size=self.pool_size,
                                pool_recycle=self.pool_recycle)

        return self._engine

    @property
    def Session(self):
        if getattr(self, '_Session', None) is None:
            self._Session = self._sessionmaker(self.engine)
        return self._Session

    @contextmanager
    def session(self):
        session = None
        try:
            Session = self.Session
            session = Session()
            yield session
        except:
            raise
        finally:
            if session:
                session.close()


class DAO(object):
    DAO_TYPES = {
        DaoType.PRODUCTION: AccessDAO(driver='pymysql', host='', port=3306, password=''),
        DaoType.DEV: AccessDAO(driver='pymysql'),
        DaoType.LOCAL: AccessDAO(driver='pymysql', host='', port='3306', user='', password='', db='')
    }

    def __init__(self, connector, dao_type, **kwargs):
        self.connector = connector
        self.access_dao = DAO.DAO_TYPES[dao_type]
        self.connector_args = kwargs

    def _create_connection(self, connector, access_dao):
        connection = connector(access_dao=access_dao, **self.connector_args) if len(self.connector_args) > 0 else \
                    connector(access_dao=access_dao)
        event.listen(connection.engine, 'checkout', self._checkout_listener)
        return connection

    @property
    def connection(self):
        if getattr(self, '_connection', None) is None:
            self._connection = \
                self._create_connection(self.connector,
                                        self.access_dao)
        return self._connection

    def close(self):
        if self.connection is not None and \
                hasattr(self.connection, 'close'):
            self.connection.close()

    def _checkout_listener(self, dbapi_con, con_record, con_proxy):
        try:
            try:
                dbapi_con.ping(False)
            except TypeError:
                dbapi_con.ping()
        except dbapi_con.OperationalError as exc:
            if exc.args[0] in (2006, 2013, 2014, 2045, 2055):
                raise DisconnectionError()
            else:
                raise
