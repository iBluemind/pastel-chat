import elasticsearch
from pastel_chat.connectors.access import AccessElasticSearch


class ElasticSearchType(object):
    PRODUCTION = 0
    DEV = 1


class ElasticSearchConnector(object):
    ES_TYPES = {
        ElasticSearchType.PRODUCTION: AccessElasticSearch(host=''),
        ElasticSearchType.DEV: AccessElasticSearch()
    }

    def __init__(self, es_type):
        access_es = ElasticSearchConnector.ES_TYPES[es_type]
        self.connection = self._create_connection(access_es.uri)

    def _create_connection(self, uri):
        return elasticsearch.Elasticsearch([uri])

    def get_es(self):
        return self.connection
