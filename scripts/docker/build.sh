#!/bin/sh

ROOT_PATH=`pwd`
DOCKER_APP_NAME=pastel-chat

docker build -t registry.hiddentrack.co/${DOCKER_APP_NAME} ${ROOT_PATH}
docker push registry.hiddentrack.co/${DOCKER_APP_NAME}
