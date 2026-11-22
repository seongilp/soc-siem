#!/bin/sh
set -eu

mkdir -p /var/log/lab/nginx
ssh-keygen -A >/dev/null

rm -f /run/rsyslogd.pid
rsyslogd
nginx

# -D: 포그라운드, 로그는 syslog(AUTH) -> rsyslog -> /var/log/lab/auth.log
exec /usr/sbin/sshd -D
