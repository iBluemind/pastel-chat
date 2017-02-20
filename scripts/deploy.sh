#!/bin/bash

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

bower install --allow-root
build_forge_min_js

$DOCKER_COMPOSE_PATH up -d

curl -X POST --data-urlencode \
    'payload={"channel": "#dev", "username": "배포하는애", "text": "린더봇을 성공적으로 배포했습니다. 하핳 확인해보셈: http://linder.kr", "icon_emoji": ":fire:"}' \
    https://hooks.slack.com/services/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
