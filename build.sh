#!/bin/bash

BOWER_PATH=/usr/bin/bower
GIT_PATH=/usr/bin/git
ROOT_DIR=/var/www/pastel_chat
DOCKER_PATH=/usr/bin/docker
DOCKER_COMPOSE_PATH=/usr/local/bin/docker-compose

function build_forge_min_js {
    local forge_min_js="$ROOT_DIR/pastel_chat/static/libs/forge/js/forge.min.js"
    if [ -f "$forge_min_js" ]
    then
        echo "forge_min_js is existed."
    else
        cd "$ROOT_DIR/pastel_chat/static/libs/forge"
        npm install
        npm run minify
    fi
}


cd $ROOT_DIR
$GIT_PATH pull origin master
/bin/chown -R www-data:www-data $ROOT_DIR

$BOWER_PATH install --allow-root
build_forge_min_js

$DOCKER_PATH build -t pastel/pastel-chat .

$DOCKER_COMPOSE_PATH up -d
