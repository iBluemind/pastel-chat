#!/bin/bash

docker run -d -p 80:80 -p 443:443 \
    --name nginx-proxy-letsencrypt \
    -v `pwd`/certs:/etc/nginx/certs:ro \
    -v /etc/nginx/vhost.d \
    -v /usr/share/nginx/html \
    -v /var/run/docker.sock:/tmp/docker.sock:ro \
    --label com.github.jrcs.letsencrypt_nginx_proxy_companion.nginx_proxy=true \
    registry.hiddentrack.co/nginx-proxy

docker run -d \
    -v `pwd`/certs:/etc/nginx/certs:rw \
    -v /var/run/docker.sock:/var/run/docker.sock:ro \
    --volumes-from nginx-proxy-letsencrypt \
    jrcs/letsencrypt-nginx-proxy-companion
