FROM ubuntu:16.04

MAINTAINER han@manjong.org

ENV PYTHONUNBUFFERED 1
ENV PASTEL_CHAT_APP_PATH /var/www/pastel_chat

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y \
    build-essential \
    gcc \
    git \
    curl \
    libpq-dev \
    make \
    pkg-config \
    python3 \
    python3-dev \
    libssl-dev \
    libffi-dev \
    libpcre3 \
    libpcre3-dev \
    && apt-get autoremove -y \
    && apt-get clean

RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3

RUN mkdir -p ${PASTEL_CHAT_APP_PATH}
WORKDIR ${PASTEL_CHAT_APP_PATH}

ADD requirements.txt ${PASTEL_CHAT_APP_PATH}/

VOLUME ${PASTEL_CHAT_APP_PATH}
RUN pip install -r requirements.txt
RUN pip install uwsgi -I

ENTRYPOINT bash
