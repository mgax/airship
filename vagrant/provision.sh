#!/bin/bash

read -r -d '' MY_SQUID_CFG <<'EOF'
acl manager proto cache_object
acl localhost src 127.0.0.1/32
acl to_localhost dst 127.0.0.0/8 0.0.0.0/32
acl SSL_ports port 443
acl Safe_ports port 80         # http
acl Safe_ports port 21         # ftp
acl Safe_ports port 443        # https
acl Safe_ports port 1025-65535 # unregistered ports
acl CONNECT method CONNECT
http_access allow manager localhost
http_access deny manager
http_access deny !Safe_ports
http_access deny CONNECT !SSL_ports
http_access allow localhost
http_access deny all
icp_access deny all
htcp_access deny all
http_port 3128
maximum_object_size 65536 KB
access_log /var/log/squid3/access.log squid
refresh_pattern . 518400 100% 518400 override-expire override-lastmod ignore-reload ignore-no-cache ignore-no-store ignore-private ignore-auth
icp_port 3130
coredump_dir /var/spool/squid3
EOF


read -r -d '' MY_PIP_CFG <<'EOF'
[global]
proxy = localhost:3128
EOF


apt-get update
apt-get install -y vim python-virtualenv squid3

if [ ! -f /etc/squid3/squid.conf.orig ]; then
    mv /etc/squid3/squid.conf /etc/squid3/squid.conf.orig
fi
echo "$MY_SQUID_CFG" > /etc/squid3/squid.conf
service squid3 reload

if [ ! -d /home/vagrant/.pip ]; then
    mkdir /home/vagrant/.pip
    chown vagrant: /home/vagrant/.pip
fi
echo "$MY_PIP_CFG" > /home/vagrant/.pip/pip.conf
chown vagrant: /home/vagrant/.pip/pip.conf
