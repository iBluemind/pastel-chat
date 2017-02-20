FROM ubuntu:16.04

MAINTAINER han@manjong.org

ENV PASTEL_CHAT_APP_PATH /var/www/pastel_chat

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y \
    build-essential gcc git curl libpq-dev make pkg-config python3 python3-dev \
    # for PyCrypto
    libssl-dev libffi-dev \
    # for uWSGI
    libpcre3 libpcre3-dev \
    # for Mecab-ko-dic
    automake autoconf

RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3

RUN curl -sL https://deb.nodesource.com/setup_6.x | bash -
RUN apt-get install -y nodejs
RUN npm install -g bower

# for Mecab, ...
RUN apt-get -y install language-pack-ko-base software-properties-common python-software-properties
RUN add-apt-repository ppa:webupd8team/java
RUN apt-get update
RUN echo debconf shared/accepted-oracle-license-v1-1 select true | \
  debconf-set-selections
RUN echo debconf shared/accepted-oracle-license-v1-1 seen true | \
  debconf-set-selections
RUN apt-get -y install oracle-java7-installer oracle-java7-set-default

WORKDIR /tmp
RUN wget https://bitbucket.org/eunjeon/mecab-ko/downloads/mecab-0.996-ko-0.9.2.tar.gz
RUN tar -xzvf mecab-0.996-ko-0.9.2.tar.gz
WORKDIR /tmp/mecab-0.996-ko-0.9.2
RUN ./configure
RUN make
RUN make install
RUN echo "/usr/local/lib" > /etc/ld.so.conf
RUN ldconfig

WORKDIR /tmp
RUN wget https://bitbucket.org/eunjeon/mecab-ko-dic/downloads/mecab-ko-dic-2.0.1-20150920.tar.gz
RUN tar -xzvf mecab-ko-dic-2.0.1-20150920.tar.gz
WORKDIR /tmp/mecab-ko-dic-2.0.1-20150920
RUN ./autogen.sh
RUN ./configure
RUN make
RUN make install

WORKDIR /tmp
RUN git clone https://bitbucket.org/eunjeon/mecab-python-0.996.git
WORKDIR /tmp/mecab-python-0.996
RUN python3 setup.py build
RUN python3 setup.py install

RUN mkdir -p ${PASTEL_CHAT_APP_PATH}
WORKDIR ${PASTEL_CHAT_APP_PATH}
COPY requirements.txt ${PASTEL_CHAT_APP_PATH}/

RUN pip install -r requirements.txt
RUN pip install uwsgi -I

VOLUME ${PASTEL_CHAT_APP_PATH}
COPY ./ ${PASTEL_CHAT_APP_PATH}/

RUN apt-get autoremove -y && apt-get clean

ENTRYPOINT /var/www/pastel_chat/scripts/start.sh
