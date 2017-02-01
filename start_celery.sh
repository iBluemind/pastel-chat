#!/bin/bash

celery -A tasks worker --app=pastel_chat.tasks --loglevel=info