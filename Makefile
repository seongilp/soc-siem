.PHONY: up down reset ps logs attack alerts

up:      ## 랩 기동 (빌드 포함)
	docker compose up -d --build

down:    ## 중지 (데이터 유지)
	docker compose down

reset:   ## 중지 + 볼륨 삭제 (인덱스·수집 상태 초기화)
	docker compose down -v

ps:
	docker compose ps -a

logs:
	docker compose logs -f --tail=50

attack:  ## 공격 시나리오 실행. 예: make attack S=ssh-brute (기본 all)
	docker compose --profile attack run --rm --build attacker $(or $(S),all)

alerts:  ## 현재 Alerting 알림 조회
	@set -a; . ./.env; set +a; \
	curl -sk -u "admin:$$OPENSEARCH_INITIAL_ADMIN_PASSWORD" \
	  'https://localhost:9200/_plugins/_alerting/monitors/alerts?size=50&sortString=start_time&sortOrder=desc' \
	| python3 -c "import json,sys; [print(a['state'], 'sev'+a['severity'], a['monitor_name'], a.get('agg_alert_content',{}).get('bucket_keys')) for a in json.load(sys.stdin)['alerts']]"
