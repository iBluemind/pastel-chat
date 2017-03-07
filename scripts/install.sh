#!/bin/sh

function build_forge_min_js {
    local forge_min_js="$ROOT_PATH/pastel_chat/static/libs/forge/js/forge.min.js"
    if [ -f "$forge_min_js" ]
    then
        echo "forge_min_js is existed."
    else
        cd "$ROOT_PATH/pastel_chat/static/libs/forge"
        npm install
        npm run minify
    fi
}

bower install
build_forge_min_js
pip install -r requirements.txt
