# Claude–Codex 2a: 최신 버전 실습 준비

준비 기준일: **2026-10-05**. 기준 커밋 `7e1360f2e2d69ea354f24176037c1241bb54cfb6`, 브랜치 `review/claude-codex-r2`. 이 단계는 실행기·공식 자산·판정 기준 준비입니다. Linux 바이너리와 WSL은 실행하지 않았습니다. `docs/`, 기존 실행기·실습 결과·hash·판 번호·통합본을 수정하지 않았고 commit·push·브랜치 전환도 하지 않았습니다.

## 준비한 파일

| 파일 | 역할 |
| --- | --- |
| [assets.json](../labs/review-r2/assets.json) | 공식 release API·checksum과 대조한 SHA256, exact envtest 자산 부재, 기존 PostgreSQL 파일 hash |
| [get_review_r2_assets.py](../scripts/get_review_r2_assets.py) | 고정 자산만 다운로드·해시 검증 후 필요한 regular file을 `.tools/r2/`에 추출. Linux 바이너리는 실행하지 않음 |
| [lab_r2_common.py](../scripts/lab_r2_common.py) | 경로 제한, 실행기·입력 hash, 관측 시각, 실패 결과, 소유한 프로세스·임시 디렉터리 정리 |
| [run_kubernetes_r2_lab.py](../scripts/run_kubernetes_r2_lab.py) | 두 버전 × watch cache on/off의 4개 시나리오; 현재 exact envtest 부재로 16개 판정은 blocked 대상 |
| [run_otel_r2_lab.py](../scripts/run_otel_r2_lab.py) | Collector 0.162.0의 8개 전송 조건과 4개 queue 응답 경계, 2개 구성요소 이름 검사 |
| [run_prometheus_r2_lab.py](../scripts/run_prometheus_r2_lab.py) | 두 promtool 버전으로 기존 규칙·테스트 파일을 byte 단위로 복사해 평가 |
| [run_postgres_r2_lab.py](../scripts/run_postgres_r2_lab.py), [postgresql-observe.sql](../labs/review-r2/postgresql-observe.sql) | prepared transaction·logical catalog_xmin·standby feedback·physical slot xmin의 네 조건과 해제 전후 관측 |
| [verify_review_r2.py](../scripts/verify_review_r2.py) | 순수 로직·경로·자산 검증, 이후 전달되는 실제 JSON의 입력 hash·산술·관측 수치 검사 |

출력은 저장소 `.lab-runs/` 아래로 제한합니다. 기본 결과 경로는 `.lab-runs/r2/`이며 같은 결과 파일을 덮어쓰지 않습니다. 재실행은 `--output .lab-runs/r2/otel-run2.json`처럼 새 이름을 사용합니다. 임시 데이터·설정·로그는 `.lab-runs/r2/work/` 아래에 생성합니다. 종료 시 로그·SQL 관측을 결과 JSON에 담고 소유한 프로세스와 작업 디렉터리를 정리합니다. 정리가 실패하면 해당 경로와 오류를 남기고 실패로 끝냅니다.

새 결과는 `supported`, `refuted`, `inconclusive`, `blocked`, `error`를 구분합니다. `RECORDED`와 검증기의 무결성 `PASS`는 모든 가설의 성립이나 제품 전체의 지원 인증을 뜻하지 않습니다. 결과 JSON에는 각 가설·성공 조건·반증 조건·원시 관측·판정 이유가 함께 들어갑니다. 실제 값은 2b 실행 뒤에만 생기며, 2a에서 수치를 만들어 출판하지 않습니다.

## 버전과 공식 자산

**Kubernetes 1.34 최신 패치는 1.34.12**로 확인했습니다. [공식 패치 일정](https://kubernetes.io/releases/patch-releases/), [v1.34.12 릴리스](https://github.com/kubernetes/kubernetes/releases/tag/v1.34.12)

그러나 controller-tools 공식 envtest의 [1.34.12 release API](https://api.github.com/repos/kubernetes-sigs/controller-tools/releases/tags/envtest-v1.34.12)와 [1.37.1 release API](https://api.github.com/repos/kubernetes-sigs/controller-tools/releases/tags/envtest-v1.37.1)는 모두 **404**였습니다. 검토 시점 공식 목록에는 [envtest 1.34.1](https://github.com/kubernetes-sigs/controller-tools/releases/tag/envtest-v1.34.1)과 [envtest 1.37.0](https://github.com/kubernetes-sigs/controller-tools/releases/tag/envtest-v1.37.0)의 Linux amd64 자산이 있습니다. 이들은 요청 버전과 다르므로 대체 다운로드·실행 대상으로 넣지 않았습니다. 없는 자산의 SHA256을 추측하지 않았습니다.

| 자산 | 공식 다운로드 | SHA256 |
| --- | --- | --- |
| Collector 0.162.0 core, Linux amd64 | [tar.gz](https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v0.162.0/otelcol_0.162.0_linux_amd64.tar.gz), [checksum](https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v0.162.0/otelcol_0.162.0_linux_amd64.tar.gz.sha256) | `f99929987a915d3c6b2c9b15bc4938c5cea903a37a3f49e478024a0fa0772339` |
| Prometheus 3.13.4 Linux amd64, promtool만 추출 | [tar.gz](https://github.com/prometheus/prometheus/releases/download/v3.13.4/prometheus-3.13.4.linux-amd64.tar.gz), [checksum](https://github.com/prometheus/prometheus/releases/download/v3.13.4/sha256sums.txt) | `87f21a66f96c597a189cef8d640e8921b621fc17a9feff707c332c4f3b3ddd56` |
| Prometheus 3.15.0 Linux amd64, promtool만 추출 | [tar.gz](https://github.com/prometheus/prometheus/releases/download/v3.15.0/prometheus-3.15.0.linux-amd64.tar.gz), [checksum](https://github.com/prometheus/prometheus/releases/download/v3.15.0/sha256sums.txt) | `2a542df32eac02ee17b9d844fb2aa1de00dafa5476579ba8a3ba862e9d572ea0` |

위 세 자산은 **Windows Python에서 다운로드·검증·추출 완료**했습니다. release API의 asset digest와 공식 checksum 항목이 일치함을 확인했고, 압축 해제 전에 실제 파일의 SHA256·크기를 검증했습니다. 압축 파일은 합계 **253,435,941B**, 추출한 세 실행 파일은 합계 **359,378,273B**입니다. 합계 약 584.4MiB이며 실행 시 임시 데이터 공간은 별도입니다. release 서명 검증을 수행한 것으로 표시하지 않습니다.

PostgreSQL은 기존 `.tools/pg18`의 18.6 패키지 추출물을 재사용합니다. [기존 공식 패키지 manifest](../labs/postgresql/packages.json)의 SHA256으로 보관된 `.deb`를 검증하고, 그 내부의 `postgres`, `initdb`, `pg_basebackup`, `pgoutput.so`, `libpq.so.5.18`, `libpqwalreceiver.so`를 현재 추출 파일과 byte 단위로 대조했습니다. 새 설치·다운로드는 하지 않았습니다. 각 실행 파일·라이브러리의 hash와 대응 패키지는 새 manifest의 `postgresql.file_sha256`에 있습니다.

## 실습별 판정과 한계

### Kubernetes

- selector 이탈: DELETED 이벤트, 직접 GET 200, 동일 UID, 변경된 label을 함께 요구합니다. 정상 watch 구간에서 해당 관측이 다르면 반증으로 기록합니다.
- pagination: 첫 페이지 뒤에 생성한 항목이 continue 페이지에 끼지 않고 기존 3개 이름과 collection RV가 유지되는지 확인합니다. fresh LIST의 4개와 대조합니다.
- 410: 전용 etcd의 physical compaction 뒤 Exact RV=1 조회와 최초 continue를 각각 요청합니다. 410과 fresh LIST 200이면 이 만료 유발 조건을 지지합니다. cache on에서 200이면 이 조건이 만료를 유발한다는 가설의 반증으로 기록하며 Kubernetes 규약 위반으로 일반화하지 않습니다.
- resourceVersion: 같은 클러스터·API group·resource type의 순차 갱신 값을 보존하고 십진 문자열을 임의 정밀도 정수로 비교합니다. 1.34에서 증가가 보이더라도 순서 비교 규약으로 승격하지 않습니다. [현재 API 규약](https://kubernetes.io/docs/reference/using-api/api-concepts/#resource-versions)

`/metrics`의 `kubernetes_feature_enabled` 원시 행과 `ListFromCacheSnapshot` 항목을 보존합니다. 지표가 없으면 상태 미관측으로 표시하며 비활성으로 단정하지 않습니다. feature gate를 임의로 켜거나 끄지 않습니다. 서버가 요청한 patch와 일치하지 않으면 중단합니다. 현재 두 exact envtest 자산이 없으므로 이 로직의 실제 서버 검사는 대기 상태입니다.

### OTel Collector

각 queue on/off에서 정상 대조군, 부분 거절, 503 후 성공, 503 재시도 소진을 실행합니다. 내부 로그는 JSON/debug, metric은 detailed 수준의 loopback Prometheus endpoint입니다. `sending_queue.wait_for_result=false`, consumer 1개, queue 10 requests, 내부 batch 설정 없음, bounded retry 3초를 명시합니다. [0.162.0 exporterhelper 구성](https://github.com/open-telemetry/opentelemetry-collector/blob/v0.162.0/exporter/exporterhelper/README.md), [내부 telemetry](https://opentelemetry.io/docs/collector/internal-telemetry/)

각 새 Collector에 별도 primer 2개 span을 보내 의도적인 영구 400으로 실패 counter를 먼저 생성합니다. primer와 본 실험의 trace ID·요청·계수 기준점을 구분합니다. counter가 없으면 0으로 간주하지 않습니다. 본 실험의 두 번째 backend 요청을 약 0.6초 보류하고 그 동안 metric을 관측한 뒤 해제합니다. 재시도 중 증가나 최종 증가량 불일치는 반증, 누락된 metric·보류 구간은 관측 불충분으로 처리합니다. 목적지 요청·응답, upstream 반환, scrape 시작·끝에 MONOTONIC·RAW·UTC 관측 시각을 남깁니다. 표본 사이의 정확한 계수 명령 실행 시각까지 안다고 주장하지 않습니다.

부분 거절은 `rejectedSpans=1`과 고유 거절 문구에 대응하는 내부 로그 또는 계수 변화를 확인합니다. `send_failed`를 곧바로 거절 span 수로 이름 붙이지 않습니다. queue를 켰을 때 목적지의 보류 해제보다 upstream 200이 앞서는지도 별도 판정합니다. 목적지의 수용과 영속 저장은 이 실험에서 같은 뜻이 아닙니다.

이름 변경은 **v0.144.0**에 도입됐습니다. `otlphttp`→`otlp_http`, `otlp` exporter→`otlp_grpc`이며 기존 이름은 deprecated alias입니다. `otlp` receiver는 별개로 유지됩니다. [고정 버전 CHANGELOG](https://github.com/open-telemetry/opentelemetry-collector/blob/v0.162.0/CHANGELOG.md#v1500v01440), [0.162.0 metadata 코드](https://github.com/open-telemetry/opentelemetry-collector/blob/v0.162.0/exporter/otlphttpexporter/internal/metadata/generated_status.go), [exporter 설명](https://github.com/open-telemetry/opentelemetry-collector/blob/v0.162.0/exporter/otlphttpexporter/README.md)

실행기는 `otlp_http/lab`을 사용하며 `otlphttp/lab`의 `validate` 결과도 별도 기록합니다. `components` 출력만으로 alias 수용 여부를 추정하지 않습니다. 이번 단계에서 실제 Collector `validate`를 실행한 것은 아닙니다.

### promtool

기존 `labs/prometheus/rules.yml`과 `tests.yml`을 작업 디렉터리에 그대로 복사해 `check rules`, `test rules`를 두 버전으로 실행합니다. 모두 exit 0이면 지지, 실제 규칙·표현식·alert 불일치이면 반증, 실행 오류는 별도로 기록합니다. stdout·stderr·종료 코드·버전·실행 파일과 fixture hash를 보존합니다. 새 Prometheus 서버는 띄우지 않습니다.

### PostgreSQL 18

| 조건 | 붙잡는 원천과 대조 |
| --- | --- |
| prepared transaction | XID를 할당한 트랜잭션을 PREPARE한 뒤 다른 연결에서 128행 DELETE. VACUUM의 제거 불가 행과 `pg_prepared_xacts`를 관측하고 ROLLBACK PREPARED 뒤 재관측 |
| logical slot | 내장 pgoutput으로 logical slot 생성. `catalog_xmin`과 비활성을 확인하고 24개 테이블 생성·삭제 뒤 pg_class VACUUM. slot 삭제 후 제거 불가 행이 사라지는지 확인 |
| standby feedback | slot 없는 standby의 REPEATABLE READ snapshot과 primary walsender `backend_xmin`을 확인한 뒤 DELETE/VACUUM. 질의 종료 후 feedback 전진을 기다려 다시 VACUUM |
| physical slot | 같은 standby에 physical slot을 연결해 xmin을 받은 뒤 **그 실습의 standby 프로세스 그룹만** 강제 종료. 비활성 slot의 xmin과 제거 불가 행을 확인하고 slot 삭제 뒤 재관측 |

각 단계에서 `n_dead_tup`, `age(datfrozenxid)`, `pg_stat_activity.backend_xmin`, `pg_prepared_xacts`, `pg_replication_slots`, `pg_stat_replication.backend_xmin`을 수집합니다. VACUUM VERBOSE의 제거·잔존·제거 불가 수와 원문 notice를 함께 보존합니다. 이 출력 형식은 [PostgreSQL 18.6 vacuumlazy.c](https://github.com/postgres/postgres/blob/REL_18_6/src/backend/access/heap/vacuumlazy.c#L956-L970)와 대조했습니다.

`n_dead_tup`은 추정치이고 단일 테이블 VACUUM이 DB 전체의 `datfrozenxid`를 반드시 전진시키지는 않습니다. logical slot의 일반 `xmin`이 NULL이어도 `catalog_xmin` 실험의 실패로 처리하지 않습니다. [slot 필드](https://www.postgresql.org/docs/18/view-pg-replication-slots.html), [feedback 설정](https://www.postgresql.org/docs/18/runtime-config-replication.html#GUC-HOT-STANDBY-FEEDBACK), [회수 기준점](https://www.postgresql.org/docs/18/routine-vacuuming.html)

primary와 standby는 새로운 로컬 포트·데이터 디렉터리를 사용합니다. autovacuum을 끄는 설정은 이 임시 cluster에만 적용합니다. root·sudo·시스템 서비스·기존 DB·XID wraparound 가속을 사용하지 않습니다. standby 준비가 불가능하면 원래 오류 JSON을 보존한 뒤 `--skip-standby`와 새 출력 파일명으로 축소 실행할 수 있습니다. 이 경우 두 복제 시나리오는 blocked이며 성공으로 세지 않습니다. 저장소 파일시스템에서 initdb가 실패해도 저장소 밖으로 우회하지 않습니다.

## Claude가 실행할 명령

Windows PowerShell의 현재 디렉터리를 `C:\project\Domain-Knowledge`로 둡니다. Ubuntu의 `/mnt/c/project/Domain-Knowledge` 매핑과 일반 Linux 사용자를 전제로 합니다. 아래 시간·메모리는 **계획용 예상치**입니다. 다운로드와 실제 서버 동작 시간은 보장하지 않습니다. 서로 순차로 실행합니다.

| 순서 | PowerShell 명령 | 예상 소요·메모리 | 출력 |
| --- | --- | --- | --- |
| 1 | `wsl -d Ubuntu --cd /mnt/c/project/Domain-Knowledge -- python3 -B scripts/get_review_r2_assets.py` | 캐시 사용 시 약 5–20초, 0.1–0.3GiB | `.tools/r2/` 검증·추출, Linux 실행 권한 설정. 서비스 실행 없음 |
| 2 | `python -X utf8 -B scripts/verify_review_r2.py` | 약 5–20초, 0.1–0.3GiB | stdout; 정적 로직·자산 확인 |
| 3 | `wsl -d Ubuntu --cd /mnt/c/project/Domain-Knowledge -- python3 -B scripts/run_prometheus_r2_lab.py --output .lab-runs/r2/prometheus.json` | 약 1분 이내, 여유 0.5–1GiB | `.lab-runs/r2/prometheus.json` |
| 4 | `wsl -d Ubuntu --cd /mnt/c/project/Domain-Knowledge -- python3 -B scripts/run_otel_r2_lab.py --output .lab-runs/r2/otel.json` | 약 1–3분, 여유 0.5–1GiB | `.lab-runs/r2/otel.json` |
| 5 | `wsl -d Ubuntu --cd /mnt/c/project/Domain-Knowledge -- python3 -B scripts/run_postgres_r2_lab.py --output .lab-runs/r2/postgresql.json` | 약 2–5분, 여유 1–2GiB·임시 디스크 1–2GiB | `.lab-runs/r2/postgresql.json` |
| 6 | `python -X utf8 -B scripts/verify_review_r2.py --result .lab-runs/r2/prometheus.json --result .lab-runs/r2/otel.json --result .lab-runs/r2/postgresql.json` | 약 5–30초, 결과 크기에 따라 0.1–0.5GiB | stdout; 저장 근거 무결성·판정 분포 |

1번은 이미 내려받은 archive를 다시 검증하고 Linux에서 실행 권한을 설정하기 위한 단계입니다. cache hash가 맞으면 네트워크로 다시 받지 않습니다. archive가 없거나 다르면 고정된 공식 URL에서 다시 받아 검증합니다.

Kubernetes는 exact 자산 부재로 실제 matrix 명령에 넣지 않았습니다. 준비된 가설과 부재를 확인하는 명령은 `python -X utf8 -B scripts/run_kubernetes_r2_lab.py --plan`입니다. 부재 상태를 실행 결과 형식으로 남겨야 한다면 `wsl -d Ubuntu --cd /mnt/c/project/Domain-Knowledge -- python3 -B scripts/run_kubernetes_r2_lab.py --output .lab-runs/r2/kubernetes.json`을 사용할 수 있습니다. 약 1초·0.1GiB 이내이며 **서버 실행 없이 16개 blocked 판정만 기록**합니다. 실제 cache 비교나 RV 관측의 대체 결과가 아닙니다.

## 검증 범위와 남은 판단

준비용 검증은 구문·경로·판정 분기·자산의 무결성을 확인합니다. Linux 서버, Collector 구성 수용, SQL 실행, 실제 재시도·회수·cache 동작은 2b에서 확인합니다. 기존 여섯 검증과 원본 보존 대조의 정확한 출력은 [구조화된 준비 기록](claude-codex-r2a.json)에 있습니다.

남은 질문은 Kubernetes 버전 선택 하나입니다. **공식 envtest가 있는 1.34.1·1.37.0으로 비교 범위를 바꿀지, 요청한 1.34.12·1.37.1의 envtest가 나올 때까지 보류할지** 결정이 필요합니다. 현재 준비물은 부재 상태를 기록합니다. 대체 버전은 사용자 판단 후 manifest와 자산을 별도로 고정합니다.
