#!/bin/bash

BOWER_PATH=/usr/local/bin/bower
GIT_PATH=/usr/bin/git
PKILL_PATH=/usr/bin/pkill
ROOT_DIR=/var/www/pastel_chat
VENV_PATH=$ROOT_DIR/venv
UWSGI_PATH=$VENV_PATH/bin/uwsgi
ACTIVATE_PATH=$VENV_PATH/bin/activate
PIP_PATH=$VENV_PATH/bin/pip


function build_forge_min_js {
    local forge_min_js="$ROOT_DIR/app/pastel_chat/static/libs/forge/js/forge.min.js"
    if [ -f "$forge_min_js" ]
    then
        echo "forge_min_js is existed."
    else
        cd "$ROOT_DIR/app/pastel_chat/static/libs/forge"
        npm install
        npm run minify
    fi
}


cd $ROOT_DIR/app
$GIT_PATH pull origin master

$BOWER_PATH install
$PIP_PATH install -r requirements.txt
build_forge_min_js

/bin/chown -R www-data:www-data $ROOT_DIR


