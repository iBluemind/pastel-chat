#!/bin/sh

TARGET_DEPLOY_TCP=tcp://

DOCKER_APP_NAME=pastel-chat
EXIST_BLUE=$(DOCKER_HOST=${TARGET_DEPLOY_TCP} docker-compose -p ${DOCKER_APP_NAME}-blue -f docker-compose.blue.yml ps | grep Up)

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
