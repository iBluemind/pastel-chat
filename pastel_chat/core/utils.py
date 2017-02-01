# -*- coding: utf-8 -*-

import jpype
import nltk
import os
from sklearn.linear_model import LogisticRegression
from gensim.models import doc2vec
import pickle, konlpy


class CommandType(object):
    ADD_NEW_SCHEDULE = 'add_new_schedule'


class UserRequestType(object):
    COMMAND = 'command'
    UNKNOWN = 'unknown'


def serialize_message_additional(message_detail_type, **kwargs):
    from pastel_chat.core.analyzer import UserRequestType
    from pastel_chat.core.response import GeneratedResponseType

    if message_detail_type == UserRequestType.UNKNOWN:
        return {
            'is_positive': kwargs['request'].is_positive
        }
    if message_detail_type == GeneratedResponseType.FORMATTED:
        return {
            'formatted_text_id': kwargs['response'].formatted_text_id
        }


class PlaceWordsDatabase(object):
    def __init__(self, connector):
        self.connector = connector

    def search(self, place_name):
        res = self.connector.search(index='pastel_chat',
                                    body={'query':
                                        {'term':
                                            {
                                               'name': place_name
                                            }
                                        }
                                    })
        results = []
        total = res['hits']['total']
        if total > 0:
            results = res['hits']['hits']
        return total, results


class PositiveOrNegative(object):
    POSITIVE = 1
    NEGATIVE = 0


class PositiveOrNegativeDetector(object):
    result_type = {
        PositiveOrNegative.POSITIVE: True,
        PositiveOrNegative.NEGATIVE: False
    }

    pre_defined_positives = ('응', 'ㅇㅇ', 'ㅇㅋ', '그래', '오냐', '알았어', '확인', '오키',
                             '오케이', '굿', '좋아', '네')
    pre_defined_negatives = ('아니', 'ㄴㄴ', '싫어', '안좋아', '나빠', '노노')

    @classmethod
    def warmup(cls):
        from pastel_chat import logger
        import time
        logger.info('Warming PositiveOrNegativeDetector up...')
        start_time = time.time()
        current_dir_path = os.path.dirname(os.path.realpath(__file__))
        root_dir_path = '%s/../..' % current_dir_path

        cls.doc_vectorizer = doc2vec.Doc2Vec.load('%s/train_datas/doc2vec.model' % root_dir_path)
        with open('%s/train_datas/train_x' % root_dir_path, 'rb') as train_x_file:
            train_x = pickle.load(train_x_file)
        with open('%s/train_datas/train_y' % root_dir_path, 'rb') as train_y_file:
            train_y = pickle.load(train_y_file)

        cls.classifier = LogisticRegression()
        cls.classifier.fit(train_x, train_y)
        elapsed_time = time.time() - start_time
        logger.info('Completed! The elapsed time is %ds' % elapsed_time)

    @staticmethod
    def _tokenize(twitter_tagger, message):
        tokens = twitter_tagger.jki.tokenize(
            message,
            jpype.java.lang.Boolean(True),
            jpype.java.lang.Boolean(True)).toArray()
        return list(tokens)

    @classmethod
    def detect(cls, message):
        tagger = konlpy.tag.Twitter()

        morphs = tagger.morphs(message)
        for morph in morphs:
            if morph in cls.pre_defined_positives:
                return cls.result_type[PositiveOrNegative.POSITIVE]
            if morph in cls.pre_defined_negatives:
                return cls.result_type[PositiveOrNegative.NEGATIVE]

        tokenized = cls._tokenize(tagger, message)
        shaped = cls.doc_vectorizer.infer_vector(tokenized).reshape(1, -1)
        result = cls.classifier.predict(shaped)
        return cls.result_type[int(result[0])]


class NLPHelper(object):
    def __init__(self, message, **kwargs):
        self.message = message
        self.tagger_selector = kwargs['tagger_selector']
        self.grammer = kwargs.get('grammer')

    @property
    def tagger(self):
        if getattr(self, '_tagger', None) is None:
            if self.tagger_selector == 'mecab':
                self._tagger = konlpy.tag.Mecab()
            elif self.tagger_selector == 'twitter':
                self._tagger = konlpy.tag.Twitter()
        return self._tagger

    @property
    def parsed_chunks(self):
        if getattr(self, '_parsed_chunks', None) is None:
            self._parsed_chunks = list(self._parse().subtrees())
        return self._parsed_chunks

    def tokenize(self):
        if self.message is None:
            raise ValueError('You must set message first!')
        return self.tagger.morphs(self.message)

    def _parse(self):
        if self.message is None:
            raise ValueError('You must set message first!')
        if self.grammer is None:
            raise ValueError('You must set grammer first!')
        words = self.tagger.pos(self.message)
        parser = nltk.RegexpParser(self.grammer)
        return parser.parse(words)

    def extract_chunks(self, filter_func):
        return filter(filter_func, self.parsed_chunks)


class HanguelNumberConverter(object):
    numbers = {
        "영": 0,
        "일": 1,
        "이": 2,
        "삼": 3,
        "사": 4,
        "오": 5,
        "육": 6,
        "칠": 7,
        "팔": 8,
        "구": 9
    }

    digits = {
        "십": 1,
        "백": 2,
        "천": 3,
        "만": 4,
        "억": 8,
        "조": 12,
        "경": 16,
        "해": 20
    }

    def converter(self, hanguel):
        current = 0
        result = 0
        tmp = 0
        num = 0
        while True:
            is_unit = False
            if self.digits.get(hanguel[current]):
                is_unit = True
            if is_unit:
                if self.digits[hanguel[current]] in [1, 2, 3]:
                    tmp += (num if num != 0 else 1) * (pow(10, self.digits[hanguel[current]]))
                else:
                    tmp += num
                    result += (tmp if tmp != 0 else 1) * (pow(10, self.digits[hanguel[current]]))
                    tmp = 0
            else:
                num = self.numbers[hanguel[current]]
            current += 1
            if current == len(hanguel) - 1:
                break
        return result + tmp + num
