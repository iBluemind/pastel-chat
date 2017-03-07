#!/bin/bash

DOCKER_APP_NAME=pastel-chat
TARGET_DEPLOY_TCP=tcp://172.31.27.217:2375
EXIST_BLUE=$(DOCKER_HOST=${TARGET_DEPLOY_TCP} docker-compose -p ${DOCKER_APP_NAME}-blue -f docker-compose.blue.yml ps | grep Up)

docker build -t registry.hiddentrack.co/${DOCKER_APP_NAME} .
docker push registry.hiddentrack.co/${DOCKER_APP_NAME}

if [ -z "$EXIST_BLUE" ]; then
    DOCKER_HOST=${TARGET_DEPLOY_TCP} docker-compose -p ${DOCKER_APP_NAME}-blue -f docker-compose.blue.yml pull
    DOCKER_HOST=${TARGET_DEPLOY_TCP} docker-compose -p ${DOCKER_APP_NAME}-blue -f docker-compose.blue.yml up -d

    sleep 10

    DOCKER_HOST=${TARGET_DEPLOY_TCP} docker-compose -p ${DOCKER_APP_NAME}-green -f docker-compose.green.yml down
else
    DOCKER_HOST=${TARGET_DEPLOY_TCP} docker-compose -p ${DOCKER_APP_NAME}-green -f docker-compose.green.yml pull
    DOCKER_HOST=${TARGET_DEPLOY_TCP} docker-compose -p ${DOCKER_APP_NAME}-green -f docker-compose.green.yml up -d

    sleep 10

    DOCKER_HOST=${TARGET_DEPLOY_TCP} docker-compose -p ${DOCKER_APP_NAME}-blue -f docker-compose.blue.yml down
fi

#curl -X POST --data-urlencode \
#    'payload={"channel": "#dev", "username": "배포하는애", "text": "린더봇을 성공적으로 배포했습니다. 하핳 확인해보셈: http://linder.kr", "icon_emoji": ":fire:"}' \
#    https://hooks.slack.com/services/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
