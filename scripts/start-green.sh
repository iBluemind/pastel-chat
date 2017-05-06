#!/bin/bash

ROOT_DIR=/var/www/pastel_chat

function get_train_datas {
    local train_datas="$ROOT_DIR/train_datas"
    if [ -d "$train_datas" ]
    then
        echo "train_datas is existed."
    else
        mkdir -p $train_datas
        wget -P $train_datas/ https://s3.ap-northeast-2.amazonaws.com/hiddentrackpastel/train_datas/doc2vec.model
        wget -P $train_datas/ https://s3.ap-northeast-2.amazonaws.com/hiddentrackpastel/train_datas/doc2vec.model.syn0.npy
        wget -P $train_datas/ https://s3.ap-northeast-2.amazonaws.com/hiddentrackpastel/train_datas/doc2vec.model.syn1.npy
        wget -P $train_datas/ https://s3.ap-northeast-2.amazonaws.com/hiddentrackpastel/train_datas/train_x
        wget -P $train_datas/ https://s3.ap-northeast-2.amazonaws.com/hiddentrackpastel/train_datas/train_y
    fi
}

cd $ROOT_DIR
get_train_datas

cd $ROOT_DIR
pip install -r requirements.txt
chown -R www-data:www-data $ROOT_DIR

echo "Sleep for memory releasing..."
sleep 30

uwsgi --ini /var/www/pastel_chat/uwsgi_config_green.ini
