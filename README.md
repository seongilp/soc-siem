# soc-siem — OpenSearch SIEM 테스트랩

OpenSearch 기반 SIEM을 실험하기 위한 단일 노드 랩. Docker 엔진은 **Kiri**(`docker context use kiri`)를 쓴다.

```
attacker ──(ssh brute force / web scan)──▶ target (sshd + nginx)
                                             │  /var/log/lab (공유 볼륨)
                                             ▼
                                         fluent-bit ──▶ opensearch ◀── dashboards (:5601)
                                                            ▲
                                             opensearch-init (템플릿 · Alerting 모니터)
```

| 서비스 | 역할 | 접속 |
|---|---|---|
| `opensearch` | 3.10 단일 노드, 보안 플러그인(데모 인증서) 활성 | https://localhost:9200 |
| `dashboards` | OpenSearch Dashboards | http://localhost:5601 |
| `fluent-bit` | target 로그 tail → 파싱 → 색인 | - |
| `target` | 로그 소스(sshd, nginx). 약한 계정 `labuser` | 랩 네트워크 내부 전용 |
| `attacker` | 공격 시뮬레이터(`attack` 프로필, 요청 시 실행) | - |
| `sysctl-init` | 엔진 VM에 `vm.max_map_count=262144` 설정 | one-shot |
| `opensearch-init` / `dashboards-init` | `scripts/bootstrap.sh` 실행(멱등) | one-shot |

계정은 `admin` / `.env`의 `OPENSEARCH_INITIAL_ADMIN_PASSWORD`. 포트는 127.0.0.1에만 바인딩된다.

## 사용

```sh
cp .env.example .env      # 최초 1회, 비밀번호 수정
make up                   # 기동
make attack               # 웹 스캔 → SSH brute force → 로그인 성공
make attack S=ssh-brute   # 시나리오 개별 실행: ssh-brute | ssh-login | web-scan
make alerts               # 1~2분 뒤 알림 확인 (Dashboards > Alerting 에서도 보임)
make reset                # 볼륨까지 삭제하고 초기화
```

## 데이터

| 인덱스 | 원본 | 주요 필드 |
|---|---|---|
| `siem-linux-auth-YYYY.MM.DD` | `/var/log/lab/auth.log` (rsyslog) | `event_action`(Failed/Accepted), `user_name`, `source_ip`, `source_port`, `process`, `message` |
| `siem-web-access-YYYY.MM.DD` | nginx JSON access log | `source_ip`, `http_method`, `url_original`, `url_path`, `url_query`, `http_status`, `user_agent` |

Dashboards에는 두 인덱스 패턴(`siem-linux-auth-*`, `siem-web-access-*`)이 미리 등록된다.

## 대시보드

**SIEM 개요** — http://localhost:5601/app/dashboards#/view/siem-overview (기본 최근 24시간, 30초 자동 새로고침)

SSH 로그인 실패/성공 수, 인증 추이, 실패 출발지 IP·대상 계정 Top 10, 웹 요청 추이와 상태 코드 분포,
오류 응답 경로 Top 10, 최근 SSH 인증 이벤트를 한 화면에 보여 준다.

정의는 `scripts/dashboards/build.py`가 만든 `siem-overview.ndjson`이고 `dashboards-init`이 매번 덮어쓰기로 import한다.
패널을 바꾸려면 `build.py`를 고친 뒤 아래를 실행한다. UI에서 직접 고친 내용은 다음 기동 때 덮어써진다.

```sh
python3 scripts/dashboards/build.py > scripts/dashboards/siem-overview.ndjson
docker compose run --rm dashboards-init
```

Dashboards 멀티테넌시는 꺼 두었다(`dashboards/opensearch_dashboards.yml`). 모든 saved objects는 하나의 공용 공간에 있다.

## 탐지 (Alerting bucket-level 모니터, 1분 주기)

| 모니터 | 조건 | 심각도 |
|---|---|---|
| SSH brute force | `source_ip`별 로그인 실패 ≥ 5회 / 5분 | 2 |
| SSH brute force 후 로그인 성공 | 같은 `source_ip`에서 실패 ≥ 5회 + 성공 ≥ 1회 / 10분 | 1 |
| 웹 스캔 | `source_ip`별 4xx ≥ 10회 / 5분 | 3 |

정의는 `scripts/monitors/*.json`. 알림 채널(action)은 비어 있어 알림은 OpenSearch 안에만 쌓인다.

## 구조

```
docker-compose.yml
dashboards/   Dashboards 설정 (멀티테넌시 비활성)
fluent-bit/   수집 파이프라인, 파서
target/       로그 소스 이미지 (sshd, rsyslog, nginx)
attacker/     공격 시나리오 (hydra, curl)
scripts/      bootstrap.sh, 인덱스 템플릿, 모니터 정의, 대시보드 정의
```

## 주의

- 랩 전용이다. 데모 인증서, admin 계정으로 색인, 고의로 약한 target 계정을 쓴다.
- `vm.max_map_count`는 Kiri VM이 재시작되면 초기화되지만 `make up` 때마다 다시 설정된다.
- Kiri VM 기본 자원(2 CPU / 8GB) 기준으로 OpenSearch 힙을 1g로 잡았다(`.env`의 `OPENSEARCH_HEAP`).
