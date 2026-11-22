#!/bin/sh
# 랩 초기화 (멱등). compose의 one-shot 서비스로 실행된다.
#   bootstrap.sh opensearch  -> 인덱스 템플릿 + Alerting 모니터
#   bootstrap.sh dashboards  -> Dashboards 인덱스 패턴
set -eu

OS_URL="${OS_URL:-https://opensearch:9200}"
OSD_URL="${OSD_URL:-http://dashboards:5601}"
AUTH="admin:${OPENSEARCH_INITIAL_ADMIN_PASSWORD:?OPENSEARCH_INITIAL_ADMIN_PASSWORD 가 필요합니다}"
DIR="$(dirname "$0")"

os() { # os METHOD PATH [BODY_FILE]
  method="$1"; path="$2"; body="${3:-}"
  if [ -n "$body" ]; then
    curl -sS -k --fail-with-body -u "$AUTH" -X "$method" "$OS_URL$path" \
      -H 'Content-Type: application/json' --data-binary "@$body"
  else
    curl -sS -k --fail-with-body -u "$AUTH" -X "$method" "$OS_URL$path"
  fi
}

put_template() {
  echo "[+] index template: $1"
  os PUT "/_index_template/$1" "$DIR/templates/$1.json" >/dev/null
}

ensure_monitor() { # ensure_monitor NAME FILE
  query="{\"size\":0,\"query\":{\"term\":{\"monitor.name.keyword\":\"$1\"}}}"
  found=$(curl -sS -k -u "$AUTH" -X POST "$OS_URL/_plugins/_alerting/monitors/_search" \
            -H 'Content-Type: application/json' -d "$query" || true)
  case "$found" in
    *'"value":0'*|*index_not_found*)
      echo "[+] monitor 생성: $1"
      os POST "/_plugins/_alerting/monitors" "$2" >/dev/null ;;
    *'"value":'*)
      echo "[=] monitor 이미 있음: $1" ;;
    *)
      echo "[!] monitor 조회 실패: $found" >&2; exit 1 ;;
  esac
}

ensure_index_pattern() { # ensure_index_pattern ID TITLE
  code=$(curl -sS -o /dev/null -w '%{http_code}' -u "$AUTH" "$OSD_URL/api/saved_objects/index-pattern/$1")
  if [ "$code" = "200" ]; then
    echo "[=] index pattern 이미 있음: $2"; return
  fi
  echo "[+] index pattern 생성: $2"
  curl -sS --fail-with-body -u "$AUTH" -X POST "$OSD_URL/api/saved_objects/index-pattern/$1" \
    -H 'osd-xsrf: true' -H 'Content-Type: application/json' \
    -d "{\"attributes\":{\"title\":\"$2\",\"timeFieldName\":\"@timestamp\"}}" >/dev/null
}

import_saved_objects() { # import_saved_objects NDJSON_FILE
  echo "[+] saved objects import: $(basename "$1")"
  result=$(curl -sS --fail-with-body -u "$AUTH" -X POST \
    "$OSD_URL/api/saved_objects/_import?overwrite=true" -H 'osd-xsrf: true' -F "file=@$1")
  case "$result" in
    *'"success":true'*) ;;
    *) echo "[!] import 실패: $result" >&2; exit 1 ;;
  esac
}

wait_dashboards() {
  i=0
  until [ "$(curl -s -o /dev/null -w '%{http_code}' -u "$AUTH" "$OSD_URL/api/status")" = "200" ]; do
    i=$((i + 1))
    [ "$i" -gt 60 ] && { echo "[!] Dashboards 가 준비되지 않았습니다" >&2; exit 1; }
    sleep 5
  done
}

case "${1:-}" in
  opensearch)
    put_template siem-linux-auth
    put_template siem-web-access
    ensure_monitor "SSH brute force (source_ip별 실패 5회 이상/5분)" "$DIR/monitors/ssh-brute-force.json"
    ensure_monitor "SSH brute force 후 로그인 성공" "$DIR/monitors/ssh-success-after-failures.json"
    ensure_monitor "웹 스캔 (source_ip별 4xx 10회 이상/5분)" "$DIR/monitors/web-scan.json"
    ;;
  dashboards)
    wait_dashboards
    ensure_index_pattern siem-linux-auth 'siem-linux-auth-*'
    ensure_index_pattern siem-web-access 'siem-web-access-*'
    for file in "$DIR"/dashboards/*.ndjson; do
      import_saved_objects "$file"
    done
    ;;
  *) echo "usage: bootstrap.sh opensearch|dashboards" >&2; exit 2 ;;
esac
echo "[ok] bootstrap $1 완료"
