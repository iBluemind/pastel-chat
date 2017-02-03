#!/bin/bash

pip install -r requirements.txt
uwsgi --ini /var/www/pastel_chat/uwsgi_config.ini
