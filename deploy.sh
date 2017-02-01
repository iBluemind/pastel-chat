#!/bin/bash

BOWER_PATH=/usr/local/bin/bower
GIT_PATH=/usr/bin/git
PKILL_PATH=/usr/bin/pkill
ROOT_DIR=/var/www/pastel_chat
VENV_PATH=$ROOT_DIR/venv
UWSGI_PATH=$VENV_PATH/bin/uwsgi
ACTIVATE_PATH=$VENV_PATH/bin/activate
PIP_PATH=$VENV_PATH/bin/pip

cd $ROOT_DIR/app
$GIT_PATH pull origin master
$PIP_PATH install -r requirements.txt

/bin/chown -R www-data:www-data $ROOT_DIR

$PKILL_PATH -f -INT uwsgi
source $ACTIVATE_PATH
$UWSGI_PATH $ROOT_DIR/app/uwsgi_config.ini

