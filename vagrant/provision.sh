#!/bin/bash


read -r -d '' MY_PIP_CFG <<'EOF'
[global]
download_cache = ~/.pip/cache
EOF


apt-get update
apt-get install -y vim python-virtualenv nginx php5-cgi spawn-fcgi curl


if [ ! -d /home/vagrant/.pip ]; then
    mkdir /home/vagrant/.pip
    mkdir /home/vagrant/.pip/cache
    chown -R vagrant: /home/vagrant/.pip
fi
echo "$MY_PIP_CFG" > /home/vagrant/.pip/pip.conf
chown vagrant: /home/vagrant/.pip/pip.conf

/etc/init.d/nginx start
