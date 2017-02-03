#!/bin/bash

BOWER_PATH=/usr/bin/bower
GIT_PATH=/usr/bin/git
ROOT_DIR=/var/www/pastel_chat
DOCKER_PATH=/usr/bin/docker
DOCKER_COMPOSE_PATH=/usr/local/bin/docker-compose

cd $ROOT_DIR
$GIT_PATH pull origin master
$BOWER_PATH install --allow-root

/bin/chown -R www-data:www-data $ROOT_DIR
$DOCKER_COMPOSE_PATH up -d

curl -X POST --data-urlencode \
    'payload={"channel": "#dev", "username": "배포하는애", "text": "린더봇을 성공적으로 배포했습니다. 하핳 확인해보셈: http://linder.kr", "icon_emoji": ":fire:"}' \
    https://hooks.slack.com/services/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
