#!/bin/bash

BOWER_PATH=/usr/local/bin/bower
GIT_PATH=/usr/bin/git
ROOT_DIR=/var/www/pastel_chat
DOCKER_PATH=/usr/bin/docker
DOCKER_COMPOSE_PATH=/usr/local/bin/docker-compose

cd $ROOT_DIR/app
$GIT_PATH pull origin master

/bin/chown -R www-data:www-data $ROOT_DIR

DOCKER_COMPOSE_PATH restart
