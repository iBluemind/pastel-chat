#!/bin/sh

# Install Docker
sudo apt-get install -y apt-transport-https \
                       ca-certificates

curl -fsSL https://yum.dockerproject.org/gpg | sudo apt-key add -

sudo apt-get install -y software-properties-common
sudo add-apt-repository \
       "deb https://apt.dockerproject.org/repo/ \
       ubuntu-$(lsb_release -cs) \
       main"

sudo apt-get update
sudo apt-get -y install docker-engine

# Install Git-LFS
curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | sudo bash
sudo apt-get install -y git-lfs

# Install Docker-Compose
sudo curl -L "https://github.com/docker/compose/releases/download/1.10.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Make execute Docker without su permission
sudo gpasswd -a ${USER} docker
sudo service docker restart
newgrp docker

# Install Bower
curl -sL https://deb.nodesource.com/setup_6.x | sudo -E bash -
sudo apt-get install -y nodejs
sudo npm install -g bower

# Build
sudo mkdir -p /var/www
sudo chown -R ${USER}:${USER} /var/www
git config --global credential.helper cache
git clone https://github.com/hiddentrackco/pastel-chat /var/www/pastel_chat
/var/www/pastel_chat/build.sh
