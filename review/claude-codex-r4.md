# Claude–Codex 4라운드 기록

## 4a — 수집 스키마와 저장 실측 기반 계약

작성·검증일: 2026-10-06. 기준 HEAD `15fef0b`(제1.2판), 브랜치 `review/claude-codex-r4`. 기존 `docs/`, book.json, BOOK.md/BOOK.html, 1–3라운드 실행기·원시 결과·provenance는 수정하지 않습니다. commit·push·브랜치 전환과 새 Linux/DB/cloud 실행은 수행하지 않습니다.

사용자 제품의 구현이 아니라 **필드 정의와 수용 경계를 표현한 참조 산출물**입니다. 새 파일은 [카탈로그 안내](../catalog/README.md), [데이터](../catalog/field-catalog.json), [schema](../catalog/field-catalog.schema.json), [fixture](../labs/fixtures/adapter-r4.json)에 있습니다.

### 설계 결정

1. JSON을 선택했습니다. 표준 라이브러리로 파싱·정규화·hash·검증할 수 있고 저장소의 기존 증거 형식과 같습니다. YAML parser를 추가하지 않습니다.
2. 숫자 지표 종류와 temporality를 분리했습니다. UID/resourceVersion/token은 identifier, 상태는 state, 시각은 timestamp입니다. 조회 정의가 필요한 CloudWatch 값은 dynamic으로 남겼습니다.
3. min/max 검토 범위와 실제 도입·제거·안정화 시점을 분리했습니다. PG 19 미검토 경계를 제거로, Kubernetes 1.35 GA를 필드 최초 도입으로 잘못 해석하지 않게 했습니다. capability·backport·extension 확인을 함께 요구합니다.
4. 정확히 표현할 수 있는 86개만 선택했습니다. Linux 29, cgroup v2 10, Kubernetes 9, PostgreSQL 19, MySQL 8, OTLP 6, CloudWatch 5입니다. 상용 DB·GPU, 실제 cloud/SNMP, 전체 버전 조합은 제외합니다.
5. field evidence는 파일을 읽은 증거와 동작 실험을 구분합니다. 메모리/PSI 파일에서 0을 읽었다는 사실을 OOM·압박 실험으로 표시하지 않습니다.
6. 새 fixture는 증거 21개 파일에서 필요한 내용만 추출합니다. 압축/비압축 SHA256, 원래 manifest, JSON pointer/metric 행 선택, 추출 값 hash를 남깁니다. 원본은 수정하지 않습니다.
7. `transform()`과 기존 22개 경계 사례는 보존했습니다. 새 56개는 `verify_contracts.py`가 추가 실행하며 본문 산술 28개와 별도 집계합니다. 기대 결과는 어댑터 출력으로 생성하지 않습니다.

### 원천과 확인 범위

1.2판 원고·1–3라운드 증거를 읽고 다음 1차 원천의 필드 의미를 대조했습니다. 개별 행의 정확한 URL은 카탈로그에 있습니다.

| 영역 | 확인한 원천 | 주로 보존한 경계 |
| --- | --- | --- |
| Linux/cgroup | [diskstats](https://docs.kernel.org/admin-guide/iostats.html), [cgroup v2 6.12](https://docs.kernel.org/6.12/admin-guide/cgroup-v2.html), [PSI](https://docs.kernel.org/accounting/psi.html), proc man-pages와 원고의 고정 Linux 소스 | 단위/폭/모집단, cgroup 수명, 6.13/6.15 가용성 |
| Kubernetes | [v1.37 Summary types](https://raw.githubusercontent.com/kubernetes/kubernetes/v1.37.0/staging/src/k8s.io/kubelet/pkg/apis/stats/v1alpha1/types.go), [summary 보정](https://raw.githubusercontent.com/kubernetes/kubernetes/v1.37.0/pkg/kubelet/server/stats/summary.go), [core types](https://raw.githubusercontent.com/kubernetes/kubernetes/v1.37.0/staging/src/k8s.io/api/core/v1/types.go), [API 개념](https://kubernetes.io/docs/reference/using-api/api-concepts/) | optional 통계, 적용 자원, UID/집합/RV 비교 경계 |
| PostgreSQL | [18 통계](https://www.postgresql.org/docs/18/monitoring-stats.html), [16](https://www.postgresql.org/docs/16/monitoring-stats.html)·[17](https://www.postgresql.org/docs/17/monitoring-stats.html), [12 statement](https://www.postgresql.org/docs/12/pgstatstatements.html)·[18 statement](https://www.postgresql.org/docs/18/pgstatstatements.html) | cache/reset, 권한 NULL, I/O와 statement 버전 분기 |
| MySQL | [8.4 status](https://dev.mysql.com/doc/refman/8.4/en/show-replica-status.html)·[9.7 status](https://dev.mysql.com/doc/refman/9.7/en/show-replica-status.html), Performance Schema 잠금·worker·connection·statement 표 | NULL/0, 수신/적용/위치, 원래 lock 문자열과 ID |
| OTLP/분포 | [OTLP](https://opentelemetry.io/docs/specs/otlp/), [metric data model](https://opentelemetry.io/docs/specs/otel/metrics/data-model/), 저장된 promtool debug | hop 성공과 최종 저장, 시작 시각/temporality, 실제 보간 값 |
| Cloud | [GetMetricData](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_GetMetricData.html), [MetricDataResult](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_MetricDataResult.html), [Azure 집계](https://learn.microsoft.com/en-us/azure/azure-monitor/metrics/metrics-aggregation-explained) | 결과별 부분 상태, 요청 token, timestamp-value pairing, 원천별 NULL/0 |

[HTTP 접근 기록](field-catalog-source-links.json): 39개 중 Python 직접 GET 32개 200·MySQL 7개 403. MySQL 공식 페이지는 웹 도구에서 별도로 열어 내용을 확인했고 직접 GET의 실패를 그대로 남겼습니다. URL 접근 성공과 문장별 사실 확인을 구분합니다. 전체 원천의 최신 지원 정책을 재조사하거나 새 판 기준일로 올린 작업은 아닙니다.

### 새 계약 테스트 56개

| 계약 묶음 | 사례 | 입력 종류 | 직접 출처 |
| --- | ---: | --- | --- |
| CPU clock 분모 품질 | 4 | 실측 | `1.1-linux-clock-r1.json`의 before/after ns·스레드 수 |
| 폭/연속성/reset·diskstats 형식 | 9 | 합성 | host 수집 계약의 32bit 조건; SNMP 64bit 경계 1개 포함 |
| Linux `/proc/net/snmp` 이름/값 파싱 | 2 | 합성 | Linux 스택의 이름/값 짝 형식; SNMP 장비 프로토콜 parser 아님 |
| MySQL 두 버전 × 네 복제 단계 | 8 | 실측 | `1.1-r3/mysql-8.4.11-r2.json`, `mysql-9.7.2-r2.json`에 연결한 gzip XML 8개 |
| PG 가려진 state·feedback NULL·lag | 6 | 실측 4·합성 2 | `1.1-postgresql.json`, `1.1-r2-postgresql.json`; replay_lag는 합성 |
| Kubernetes 집합 이탈·UID·404·늦은 삭제 | 4 | 실측 2·합성 2 | `1.1-kubernetes.json` selector_exit/name_reuse |
| CloudWatch partial/token/pairing/Forbidden | 4 | 합성 | 원고의 가상 응답·API 계약 |
| Azure null/0/absent | 3 | 합성 | 공식 집계 문서; cloud 호출 없음 |
| OTLP 부분 거절·upstream hop 성공·HTTP 분류 | 6 | 실측 4·합성 2 | `1.1-r2-otel.json`의 목적지/상류 원래 응답 |
| Collector retry 진행/소진, queue off/on | 4 | 실측 | 같은 결과의 기준/held/최종 metric 원문 행 |
| 중복 수신·다른 trace의 같은 span ID | 2 | mixed 1·합성 1 | `1.1-otel.json`; 이전 결과에 trace ID 미보존이므로 고정 실습 문맥 명시 |
| classic/native/custom 보간 | 2 | 실측 실행 출력 | `1.1-r3/histograms.json`의 promtool 3.13.4·3.15.0 gzip debug; 입력 분포 자체는 합성 |
| PSI 형식과 실제 0 | 1 | 실측 | `1.1-r3/linux-memory.raw/psi-memory.gz` |
| NaN을 정상 숫자로 거부 | 1 | 합성 | 참조의 유한 숫자 계약 |

실측 29·합성 26·mixed 1입니다. 옛 입력 hash를 현재 스크립트에 맞춰 덮어쓰지 않습니다. 새 fixture를 다시 추출해 비교하고 원시 자료의 gzip/JSON과 현재 참조 구현의 책임을 분리합니다.

구현 도중 MySQL XML이 하나의 XML 문서가 아니라 `SHOW REPLICA STATUS` 뒤 별도 완료-marker SELECT를 포함하는 것을 확인했습니다. 원시 자료를 잘라 고치지 않고 명령별 resultset을 선택하도록 parser를 수정했습니다. SQL NULL은 `xsi:nil`에서 읽으며 빈 문자열과도 구분합니다.

### 본문에서 발견한 4b 수정 후보 — 4a에서는 미수정

| ID | 위치 | 판정과 수정 제안 |
| --- | --- | --- |
| C1 | [지표 참조표](../docs/metric-catalog.md)의 `Tcp.CurrEstab` | 요약 표의 ESTABLISHED·CLOSE-WAIT에 버전 경계가 생략됨. 상세 [Linux 스택](../docs/network/linux-stack-counters.md)의 6.10 수정/이전 구현/backport 조건을 표에도 짧게 표시. 전 버전 오류로 단정하지 않음 |
| C2 | 같은 표의 eviction `memory.available` | capacity−working set만 적으면 1.37 hugepage 보정을 재계산할 때 놓치거나 이중 차감할 수 있음. [상세 장](../docs/kubernetes/pressure-and-termination.md)의 gate 적용 Summary availableBytes와 보정 전 식을 구분 |
| C3 | [어댑터 계약](../docs/product/adapter-contracts.md)의 “이 참조 구현은 wrap 복원을 수행하지 않음” | 기존 `transform()` 설명으로는 여전히 맞지만 이제 파일 전체에는 조건부 `bounded_counter_delta()`가 있음. 함수별 전제/출력을 나누고 감소만으로 확정하지 않는 원칙 유지 |
| C4 | 같은 장의 “22가지 사례”, [검증 기록](../docs/validation.md) | 기존 22개와 1.2판 발행 결과는 역사로 보존. 4라운드 절에 추가 56개·스키마 86개/본문 연결 35개/거부 16개를 별도로 기록 |
| C5 | [복제/회수 원천 설명](../docs/database/postgresql-operations.md)과 향후 수용 표 | 기존 실측에는 replay_lag 열이 없음. `backend_xmin NULL` 실측과 `replay_lag NULL` 합성 계약을 명시적으로 나눠 증거 범위를 표시 |

카탈로그에서 새로 표현한 PG 버전 범위 끝과 `introduced_in/removed_in`, CloudWatch `kind=dynamic`, K8s 적용 자원·reset marker는 원고 오류 판정이 아니라 기계 계약으로 옮기면서 드러난 명세 필요 사항입니다.

### 검증과 4b 계획

Windows Python에서 아래 명령을 `python -X utf8 -B scripts/<파일명>`으로 실행했습니다. 기본 여섯 검사와 새 검사가 모두 PASS입니다. 기존 원고를 변경하지 않아 BOOK은 `--check`로 일치를 확인했습니다. 새 Linux/DB/cloud 실행·HTML 화면 검사는 하지 않았습니다.

| 명령 | 결과 |
| --- | --- |
| `check_docs.py` | PASS: Markdown 124개, 상세 100장, 로컬 링크 2,413개; 외부 URL 582개는 목록화 |
| `verify_examples.py` | PASS: 원문 60개에 연결한 산술·해석 185개 |
| `verify_contracts.py` | PASS: 기존 22개 + 새 56개 어댑터 사례, 본문 계산 28개, 기존 실습 hash |
| `verify_revision.py` | PASS: 원래 31개 시나리오, 1라운드 시계, 2라운드 36판정, 3라운드 27판정/525 gzip |
| `build_book.py --check` | PASS: BOOK.md와 원문 122개 일치 |
| `build_html.py --check` | PASS: BOOK.html과 원문·고정 renderer 일치 |
| `verify_field_catalog.py` | PASS: 86개 필드, 본문 연결 35개, 거부 사례 16개, 보조 문서 링크 20개 |
| `build_adapter_fixtures.py --check` | PASS: 56개 fixture·출처 파일 21개 재추출 일치 |
| `verify_adapter_fixtures.py` | PASS: 실측 29·합성 26·mixed 1; 동일 검사가 verify_contracts에서도 실행됨 |

원시 증거의 verdict를 바꾸거나 실패한 관측을 합성 기대값으로 대체하지 않았습니다. 검사 성공은 이 참조 코드와 저장된 입력의 수용 조건에 한정됩니다.

4b에서는 새 장 수를 늘리기보다 `product/adapter-contracts.md`에 **카탈로그 한 행 → 원시 입력 → 정규화 값/품질 → 수용 테스트** 흐름을 보강합니다. `compatibility-and-acceptance.md`에는 버전/권한/capability 선택 절차를 연결하고 `metric-catalog.md`에 데이터 파일 링크와 C1·C2를 반영할 예정입니다. 원고 수정 시 장별 hash·검증 기록·BOOK을 함께 갱신하되 역사적 1.2판 실행 결과는 보존합니다.

## 4b — 일관성과 초보자 가독성, 계약 산출물의 본문 연결

검토·편집일: 2026-10-06. 제1.2판·100장·기준일을 유지했습니다. 원시 실습 JSON/gzip·provenance·역사 입력은 수정하지 않았고 서버·cloud 실습도 재실행하지 않았습니다. 검토 초점은 **독자가 처음 만나는 개념·수집 경계·정본·탐색 순서**입니다. 100장을 다시 모든 원천과 사실 대조했다는 의미가 아닙니다.

### 정본 배정

| 개념 | 정본 | 다른 장의 역할 |
| --- | --- | --- |
| PSI | [NUMA·PSI](../docs/host/numa-and-pressure.md) | CPU·memory는 신호 요약 |
| 프로세스 메모리 원천 | [프로세스](../docs/host/processes.md) | memory는 개념·누수 판단 |
| memory.events·working set | [컨테이너 메모리](../docs/containers/memory-accounting-and-oom.md) | host/Kubernetes는 범위·원인 연결 |
| OOM·축출 증거 | [압박·종료](../docs/kubernetes/pressure-and-termination.md) | 호스트의 커널 로그 상세는 reclaim 장 유지 |
| RV·410·초기완료·BOOKMARK | [인벤토리](../docs/kubernetes/inventory-consistency.md) | collection는 수집 경로 |
| DNS 실패 / IF-MIB·Counter64 | [주소·DNS](../docs/network/addressing-routing-dns.md) / [SNMP](../docs/network/snmp-and-device-models.md) | lifecycle는 연결 실습, metrics는 링크 요약 |
| 복제 단계 대응 | [복제·복구](../docs/database/replication-and-recovery.md) | 저장·사례는 그 경계로 연결 |
| PG 회수·버전 / MySQL SBS·잠금 | [PG 운영](../docs/database/postgresql-operations.md) / [MySQL 운영](../docs/database/mysql-operations.md) | 엔진 기초는 개요 |
| sampling 추정 | [sampling·문맥](../docs/application/trace-sampling-and-context.md) | 통계·trace 개요는 링크 |
| OTLP 응답→행동 | [전송 계약](../docs/product/telemetry-delivery-contracts.md) | 파이프라인·용량은 규칙 요약 |
| 버퍼·용량 | [용량·손실 예산](../docs/product/capacity-and-loss-budgets.md) | pipeline는 책임·역압 |
| 상태 이름·카탈로그→fixture | [어댑터 계약](../docs/product/adapter-contracts.md) | 독립 품질 축과 제안한 전달 단계 구분 |

### 항목별 판정

총 102항목: 수용 88 · 부분 수용 14 · 반박 0 · 보류 0. 원칙으로 해결한 분야 항목도 별도 행으로 기록합니다.

| ID | 판정 | 바꾼 파일 | 비고 |
| --- | --- | --- | --- |
| P1 | 수용 | [host/linux-observation-lab.md](../docs/host/linux-observation-lab.md), [foundations/distributed-systems.md](../docs/foundations/distributed-systems.md), [database/mysql-operations.md](../docs/database/mysql-operations.md), [cross-domain/reproducible-labs.md](../docs/cross-domain/reproducible-labs.md) | 라운드·작업자·검사 이력은 검증 노트/검토 기록으로 이동. 파일명·실행 당시 label은 근거에서 보존 |
| P2 | 부분 수용 | [product/adapter-contracts.md](../docs/product/adapter-contracts.md), [product/telemetry-delivery-contracts.md](../docs/product/telemetry-delivery-contracts.md), [foundations/README.md](../docs/foundations/README.md) | 아래 정본 배정 적용. 각 장의 질문·이해 확인에 필요한 짧은 요약과 실제 실습의 고유 관측은 남김 |
| P3 | 부분 수용 | [host/reclaim-and-oom.md](../docs/host/reclaim-and-oom.md), [network/linux-stack-counters.md](../docs/network/linux-stack-counters.md), [kubernetes/pressure-and-termination.md](../docs/kubernetes/pressure-and-termination.md), [database/mysql-operations.md](../docs/database/mysql-operations.md) | 결론을 먼저 쓰고 복잡한 코드 근거를 심화로 분리. 오독을 막는 버전 조건·출처는 해당 표 곁에도 유지 |
| P4 | 수용 | [kubernetes/resources-and-scheduling.md](../docs/kubernetes/resources-and-scheduling.md), [containers/resource-control.md](../docs/containers/resource-control.md), [application/requests-and-concurrency.md](../docs/application/requests-and-concurrency.md), [product/collection-pipelines.md](../docs/product/collection-pipelines.md) | 반복 도입 21곳을 병합하고 제품에서 필요한 이유 추가. 서로 다른 선수 개념은 억지로 삭제하지 않음 |
| P5 | 수용 | [reading-guide.md](../docs/reading-guide.md), [network/README.md](../docs/network/README.md), [database/README.md](../docs/database/README.md) | book.json 기준 본문·개요의 이전/다음 생성. foundations 심화 3장은 이동 대신 건너뛰기·선수 안내 선택 |
| P6 | 수용 | [glossary.md](../docs/glossary.md) | 중복 RSS/PSS 통합, 동음이의 의미별 행, 누락 용어와 정본 링크, 관측·통계 용어 묶음 |
| P7 | 부분 수용 | [foundations/README.md](../docs/foundations/README.md), [host/memory.md](../docs/host/memory.md), [network/tcp-and-udp.md](../docs/network/tcp-and-udp.md), [kubernetes/resources-and-scheduling.md](../docs/kubernetes/resources-and-scheduling.md), [database/transactions-and-locks.md](../docs/database/transactions-and-locks.md), [storage/write-path-and-durability.md](../docs/storage/write-path-and-durability.md) | 요청한 기초 흐름·표 추가. cgroup 대응은 실제 설정 조건을 붙이고 freeze 그림은 행 상태 기계가 아닌 학습 순서로 한정 |
| P8 | 수용 | [glossary.md](../docs/glossary.md), [storage/write-path-and-durability.md](../docs/storage/write-path-and-durability.md), [database/replication-and-recovery.md](../docs/database/replication-and-recovery.md) | 축출/캐시 퇴거, 지속성 완료, 역압, HTTP 410(reason Expired), 가상 예시 구분 |
| P9 | 수용 | [README.md](../README.md), [cross-domain/reproducible-labs.md](../docs/cross-domain/reproducible-labs.md), [review.md](../docs/review.md) | README 요약 4줄, 따라 하기 실습 우선, 과거 판정·hash는 실습 장 끝 검증 노트로 이동 |
| F1 | 수용 | [foundations/time-and-data-quality.md](../docs/foundations/time-and-data-quality.md), [glossary.md](../docs/glossary.md) | 날짜·tick 조건이 다른 두 시계 비율을 명시. monotonic도 주파수 조정 받음 |
| F2 | 수용 | [foundations/time-and-data-quality.md](../docs/foundations/time-and-data-quality.md), [foundations/measurement-and-comparability.md](../docs/foundations/measurement-and-comparability.md) | 동기화 진단 심화 이동, CPU 상세 실측은 Linux 실습 정본으로, 이해 확인 형식 통일 |
| F3 | 수용 | [foundations/service-level-objectives.md](../docs/foundations/service-level-objectives.md) | 28÷4=7일의 가정과 이동 창·요청률 한계, 본문 연결 산술 검사 |
| F4 | 수용 | [foundations/service-level-objectives.md](../docs/foundations/service-level-objectives.md) | 300 ms bucket 경계 또는 원표본 필요, 없으면 보간 추정임을 설명 |
| F5 | 수용 | [foundations/metric-context-and-start-time.md](../docs/foundations/metric-context-and-start-time.md), [foundations/histogram-storage.md](../docs/foundations/histogram-storage.md) | 기능 수용·문맥 보존 결론을 flag 표 앞에 두고 구현자 참고 표시 |
| F6 | 수용 | [foundations/distributions.md](../docs/foundations/distributions.md), [foundations/histogram-storage.md](../docs/foundations/histogram-storage.md) | nearest-rank 명명, 4표본 p25=1.25초 추가와 검사 |
| F7 | 수용 | [foundations/performance-and-statistics.md](../docs/foundations/performance-and-statistics.md) | λ를 도착률(안정 상태에서 완료율과 같음)로 명시 |
| F8 | 수용 | [foundations/performance-and-statistics.md](../docs/foundations/performance-and-statistics.md), [foundations/traces-logs-profiles.md](../docs/foundations/traces-logs-profiles.md), [foundations/README.md](../docs/foundations/README.md) | sampling 계산 정본으로 연결, Stable/Development 범례와 별도 deprecated 축 구분 |
| F9 | 수용 | [foundations/distributed-systems.md](../docs/foundations/distributed-systems.md), [glossary.md](../docs/glossary.md) | CAP 가용성·분류표 오용 결론 선행. 옛 링크 정정은 검증 노트, Raft·etcd·fsync 용어 추가 |
| F10 | 수용 | [glossary.md](../docs/glossary.md) | 분포 형식·문맥·시계·오차·lookback 용어 추가 |
| H1 | 수용 | [host/memory.md](../docs/host/memory.md) | 비가용 비율 명칭·식 통일, 4종 메모리 의미·원천·정본 비교 |
| H2 | 수용 | [host/reclaim-and-oom.md](../docs/host/reclaim-and-oom.md), [host/README.md](../docs/host/README.md) | 심화 표시와 선수 링크, 커널 계수 지점을 심화로 이동 |
| H3 | 수용 | [host/processes.md](../docs/host/processes.md) | 좀비 문단을 상태 절 뒤로, 누수 링크를 memory로. cat 명령 자체와 자기 PID 의미·미실행 상태 명시 |
| H4 | 수용 | [host/memory.md](../docs/host/memory.md), [host/processes.md](../docs/host/processes.md) | 기본 status/statm, 상세 smaps 계열로 권고 통일. 비원자성·비용 한계 유지 |
| H5 | 수용 | [host/cpu.md](../docs/host/cpu.md), [host/linux-observation-lab.md](../docs/host/linux-observation-lab.md), [host/collection-contracts.md](../docs/host/collection-contracts.md) | 분모 시계 경고, CPU 실습 결론 선행, 호스트 계약은 요약+링크 |
| H6 | 수용 | [host/cpu.md](../docs/host/cpu.md) | D 상태 정의와 비 idle 식의 iowait·steal 포함 명시 |
| H7 | 수용 | [host/gpu.md](../docs/host/gpu.md), [glossary.md](../docs/glossary.md) | GPU kernel과 OS kernel, NVML·DCGM 정의 |
| H8 | 수용 | [host/windows.md](../docs/host/windows.md), [host/memory.md](../docs/host/memory.md) | API·PDH 메모리 대응표 통합. 시간 다른 표본의 값 동일성까지 보장하지 않음 |
| H9 | 수용 | [host/disk-io.md](../docs/host/disk-io.md), [host/collection-contracts.md](../docs/host/collection-contracts.md), [host/memory.md](../docs/host/memory.md) | diskstats wrap의 정본 지정, meminfo kB=1024 B |
| H10 | 수용 | [glossary.md](../docs/glossary.md) | 메모리·회수·CPU 상태·GPU 원천 용어 추가 |
| N1 | 수용 | [network/network-metrics.md](../docs/network/network-metrics.md), [network/snmp-and-device-models.md](../docs/network/snmp-and-device-models.md) | 10 Gbit/s 3.44초와 1 Gbit/s 34.4초 병기, 독립 산술 검사 |
| N2 | 부분 수용 | [network/snmp-and-device-models.md](../docs/network/snmp-and-device-models.md), [network/linux-stack-counters.md](../docs/network/linux-stack-counters.md) | marker 유지·속도 추정만으로 연속성/실제 상한 입증 불가. uptime 역행과 정상 증가를 구분하고 조건부 wrap만 허용 |
| N3 | 수용 | [storage/write-path-and-durability.md](../docs/storage/write-path-and-durability.md), [database/replication-and-recovery.md](../docs/database/replication-and-recovery.md), [cross-domain/resource-failures.md](../docs/cross-domain/resource-failures.md) | 수신·기록·적용과 write/flush/replay의 정본 표로 연결 |
| N4 | 수용 | [storage/write-path-and-durability.md](../docs/storage/write-path-and-durability.md), [glossary.md](../docs/glossary.md) | 언어·장치·복제 flush 표, DB/스트림 checkpoint 분리 |
| N5 | 수용 | [network/layers-and-routing.md](../docs/network/layers-and-routing.md), [glossary.md](../docs/glossary.md) | L2/L3/L4·frame/packet/segment와 전달 4단계·MTU 설명 |
| N6 | 수용 | [network/tcp-and-udp.md](../docs/network/tcp-and-udp.md), [network/linux-stack-counters.md](../docs/network/linux-stack-counters.md) | TCP 상태와 두 대기열 선행, code/backport 심화 이동 |
| N7 | 수용 | [storage/write-path-and-durability.md](../docs/storage/write-path-and-durability.md) | WAL이 데이터보다 먼저 지속돼야 하는 이유와 async commit/fsync 차이의 결론 추가 |
| N8 | 수용 | [network/dns-and-connection-lifecycle.md](../docs/network/dns-and-connection-lifecycle.md), [network/addressing-routing-dns.md](../docs/network/addressing-routing-dns.md) | 실패 분류는 addressing, lifecycle는 TTL·연결·실측의 고유 질문 유지 |
| N9 | 수용 | [network/network-metrics.md](../docs/network/network-metrics.md), [network/tcp-and-udp.md](../docs/network/tcp-and-udp.md) | IF-MIB 요약과 정본 링크, Linux stack/SNMP 관련 목록 |
| N10 | 수용 | [glossary.md](../docs/glossary.md), [network/routing-convergence-and-qos.md](../docs/network/routing-convergence-and-qos.md), [network/dns-and-connection-lifecycle.md](../docs/network/dns-and-connection-lifecycle.md), [storage/raid-lvm-and-paths.md](../docs/storage/raid-lvm-and-paths.md) | 요청한 용어 추가와 첫 사용의 짧은 정의 |
| N11 | 수용 | [network/layers-and-routing.md](../docs/network/layers-and-routing.md) | 옵션 없는 내부 IPv4/TCP 등 가정 아래 1450−20−20=1410 B, PMTUD 심화 표시 |
| N12 | 수용 | [storage/capacity-and-protection.md](../docs/storage/capacity-and-protection.md) | Ceph 소개와 OSD/acting set/peering 정의, 버전 문단 뒤로 |
| N13 | 수용 | [network/snmp-and-device-models.md](../docs/network/snmp-and-device-models.md) | GET/순회 절을 Counter64 상세보다 먼저, v1/v2c/v3 비교 |
| N14 | 수용 | [network/tls-http.md](../docs/network/tls-http.md) | TLS 1.3·30 ms RTT 가정과 잔여 20 ms의 가상 성격 명시 |
| N15 | 수용 | [storage/models-and-performance.md](../docs/storage/models-and-performance.md), [host/disk-io.md](../docs/host/disk-io.md), [database/replication-and-recovery.md](../docs/database/replication-and-recovery.md) | 쓰기 경로 상호 링크와 전체 탐색 순서 일치 |
| K1 | 부분 수용 | [kubernetes/resources-and-scheduling.md](../docs/kubernetes/resources-and-scheduling.md), [containers/platform-differences.md](../docs/containers/platform-differences.md), [kubernetes/cni-csi-and-data-paths.md](../docs/kubernetes/cni-csi-and-data-paths.md) | 일반 cgroup v2 대응·계층과 sandbox. 설정/API 값이 실제 cgroup 값의 무조건 보장은 아님 |
| K2 | 수용 | [kubernetes/pressure-and-termination.md](../docs/kubernetes/pressure-and-termination.md), [kubernetes/resources-and-scheduling.md](../docs/kubernetes/resources-and-scheduling.md), [containers/memory-accounting-and-oom.md](../docs/containers/memory-accounting-and-oom.md), [host/reclaim-and-oom.md](../docs/host/reclaim-and-oom.md) | 세 종료 경로 통일, oom_score_adj는 커널 OOM 선택의 조정임을 명시 |
| K3 | 부분 수용 | [kubernetes/pressure-and-termination.md](../docs/kubernetes/pressure-and-termination.md) | OOMKilled 재시작은 정책에 의존, Evicted 대체는 controller 동작에 의존. 무조건 restartCount/새 UID 증가로 단정하지 않음 |
| K4 | 수용 | [containers/memory-accounting-and-oom.md](../docs/containers/memory-accounting-and-oom.md), [kubernetes/pressure-and-termination.md](../docs/kubernetes/pressure-and-termination.md), [host/reclaim-and-oom.md](../docs/host/reclaim-and-oom.md) | events 정의와 종료 증거 정본 분리·연결 |
| K5 | 수용 | [glossary.md](../docs/glossary.md), [kubernetes/collection.md](../docs/kubernetes/collection.md), [containers/resource-control.md](../docs/containers/resource-control.md) | Windows/cAdvisor/개념의 working set 구분과 정본 링크 |
| K6 | 수용 | [kubernetes/pressure-and-termination.md](../docs/kubernetes/pressure-and-termination.md), [glossary.md](../docs/glossary.md) | 축출 용어와 PDB·자발적 중단/API 축출 구분 |
| K7 | 수용 | [containers/resource-control.md](../docs/containers/resource-control.md), [kubernetes/README.md](../docs/kubernetes/README.md) | manifest에 따른 3→4→5→6→7 및 메모리 장 연결 |
| K8 | 부분 수용 | [kubernetes/collection.md](../docs/kubernetes/collection.md), [containers/platform-differences.md](../docs/containers/platform-differences.md) | endpoint/PSI와 v1 상태 이동. 제안 그림은 그대로 채택하지 않음: metrics-server 0.6+는 /metrics/resource 사용 |
| K9 | 수용 | [kubernetes/inventory-consistency.md](../docs/kubernetes/inventory-consistency.md), [kubernetes/collection.md](../docs/kubernetes/collection.md) | 페이지 LIST·streaming 초기완료·일반 BOOKMARK의 다른 규칙을 표로 정리 |
| K10 | 수용 | [kubernetes/inventory-consistency.md](../docs/kubernetes/inventory-consistency.md), [kubernetes/collection.md](../docs/kubernetes/collection.md) | 410 명칭, cache true 200·빈 목록 관측과 전체 삭제 금지 원칙 |
| K11 | 수용 | [kubernetes/inventory-consistency.md](../docs/kubernetes/inventory-consistency.md), [kubernetes/objects-and-control-loops.md](../docs/kubernetes/objects-and-control-loops.md), [kubernetes/operators-and-api-lifecycle.md](../docs/kubernetes/operators-and-api-lifecycle.md) | 응답한 서버의 버전·종류가 기준. LIST RV 옵션 4종 표, GET/watch에 무조건 적용 금지 |
| K12 | 수용 | [kubernetes/pressure-and-termination.md](../docs/kubernetes/pressure-and-termination.md) | 상황→증거→QoS→신호→심화, 용어 선행 정의 |
| K13 | 수용 | [kubernetes/pressure-and-termination.md](../docs/kubernetes/pressure-and-termination.md), [kubernetes/inventory-consistency.md](../docs/kubernetes/inventory-consistency.md), [kubernetes/collection.md](../docs/kubernetes/collection.md), [containers/memory-accounting-and-oom.md](../docs/containers/memory-accounting-and-oom.md) | P1 적용; 코드/문서 비교 이력 대신 버전별 규칙을 본문에 유지 |
| K14 | 수용 | [glossary.md](../docs/glossary.md) | streaming list/encoding, etcd compaction과 요청한 Kubernetes 용어 |
| A1 | 수용 | [application/trace-sampling-and-context.md](../docs/application/trace-sampling-and-context.md) | th/rv/1/p 조건부 요약, rv 선택성, W3C 별도 절·안정성 범례 |
| A2 | 수용 | [middleware/kafka.md](../docs/middleware/kafka.md), [middleware/README.md](../docs/middleware/README.md) | 기본 용어 표와 offset 차이로서 lag |
| A3 | 수용 | [middleware/README.md](../docs/middleware/README.md) | Kafka/RabbitMQ/Pulsar의 세는 단위·범위 비교 |
| A4 | 수용 | [application/semantic-conventions.md](../docs/application/semantic-conventions.md) | 순서 이동 대신 계측 선수 안내, By·collection·UpDownCounter와 구 이름 예 |
| A5 | 부분 수용 | [application/managed-runtimes.md](../docs/application/managed-runtimes.md), [application/semantic-conventions.md](../docs/application/semantic-conventions.md) | JVM→.NET 재배열, GC 축 정본, 임의 100 ms 질문 제거. API MBean 표와 별개인 OTel 이름/단위 표는 각 목적에 맞춰 보존 |
| A6 | 수용 | [foundations/traces-logs-profiles.md](../docs/foundations/traces-logs-profiles.md), [foundations/performance-and-statistics.md](../docs/foundations/performance-and-statistics.md), [application/trace-sampling-and-context.md](../docs/application/trace-sampling-and-context.md) | 표본 오류 계산 정본화, 제거한 50.25% 예의 자동 계산도 제거 |
| A7 | 수용 | [middleware/stream-processing.md](../docs/middleware/stream-processing.md), [middleware/message-queues.md](../docs/middleware/message-queues.md), [middleware/cache-redis.md](../docs/middleware/cache-redis.md), [application/README.md](../docs/application/README.md), [middleware/README.md](../docs/middleware/README.md) | Pulsar/Memcached 문단 이동·README 범위와 관측 표 갱신 |
| A8 | 수용 | [application/user-experience.md](../docs/application/user-experience.md), [reading-guide.md](../docs/reading-guide.md), [glossary.md](../docs/glossary.md) | 가상 수치와 synthetic monitoring을 분리 |
| A9 | 수용 | [glossary.md](../docs/glossary.md), [middleware/stream-processing.md](../docs/middleware/stream-processing.md), [product/collection-pipelines.md](../docs/product/collection-pipelines.md) | Backpressure 정본 링크, 역압 통일 |
| A10 | 수용 | [glossary.md](../docs/glossary.md) | 계측 유형·Kafka·런타임·문맥·메시징·Little 용어 추가 |
| A11 | 부분 수용 | [application/managed-runtimes.md](../docs/application/managed-runtimes.md), [application/async-runtimes.md](../docs/application/async-runtimes.md), [middleware/kafka.md](../docs/middleware/kafka.md) | 버전 메모 표시. 해당 지표의 집계 오류를 막는 controller 범위는 그 절에 남김 |
| A12 | 수용 | [application/README.md](../docs/application/README.md) | 전체 본문 이전/다음 생성으로 해결 |
| A13 | 수용 | [application/requests-and-concurrency.md](../docs/application/requests-and-concurrency.md), [application/timeouts-and-retries.md](../docs/application/timeouts-and-retries.md), [middleware/kafka.md](../docs/middleware/kafka.md) | P4로 해결 |
| A14 | 부분 수용 | [application/instrumentation-and-profiling.md](../docs/application/instrumentation-and-profiling.md) | 추가 문맥 없는 경우 server 4xx MUST unset, client 4xx SHOULD Error; 5xx SHOULD. 모든 404를 무조건 오류로 확정하지 않음 |
| A15 | 수용 | [application/README.md](../docs/application/README.md) | P1 머리말 공통 형식 적용, 실제 확인일과 실행 범위 유지 |
| D1 | 수용 | [database/transactions-and-locks.md](../docs/database/transactions-and-locks.md), [database/postgresql-operations.md](../docs/database/postgresql-operations.md), [database/postgresql.md](../docs/database/postgresql.md) | MVCC→회수·freeze 학습 흐름과 회수 기준점/동결 진행점 용어. 상태 기계 아님 |
| D2 | 부분 수용 | [database/replication-and-recovery.md](../docs/database/replication-and-recovery.md), [database/mysql-operations.md](../docs/database/mysql-operations.md), [glossary.md](../docs/glossary.md) | NULL의 복수 원인 표. PG NULL이 '대개' 어떤 원인이라는 빈도 주장·정상 단정은 채택하지 않음 |
| D3 | 부분 수용 | [database/transactions-and-locks.md](../docs/database/transactions-and-locks.md) | RR 시간표와 엔진별 표. SQL Server에 FOR UPDATE가 없어 UPDLOCK 등 별도 규칙 명시 |
| D4 | 수용 | [database/mysql-operations.md](../docs/database/mysql-operations.md) | receiver(IO)/applier(SQL) 라벨·복제 흐름·relay/coordinator/worker 정의 |
| D5 | 수용 | [database/README.md](../docs/database/README.md), [database/transactions-and-locks.md](../docs/database/transactions-and-locks.md), [database/postgresql-operations.md](../docs/database/postgresql-operations.md) | 실제 book 순서를 기초→엔진→복제/HA→운영→수집/실습으로 변경, 선수와 실습 링크 |
| D6 | 수용 | [database/postgresql-operations.md](../docs/database/postgresql-operations.md) | 기본값 나이와 남은 거리를 한 축에 표시; 2^31 부근 경계는 근사·설정 조건 명시 |
| D7 | 수용 | [database/mysql-operations.md](../docs/database/mysql-operations.md), [database/postgresql-operations.md](../docs/database/postgresql-operations.md), [database/mysql-mariadb.md](../docs/database/mysql-mariadb.md), [database/transactions-and-locks.md](../docs/database/transactions-and-locks.md) | 구현식/코드는 검증 노트, 실행 코드명은 의미 있는 표현으로, 버전 상태는 근거 절로 |
| D8 | 수용 | [database/postgresql.md](../docs/database/postgresql.md) | 개요의 VACUUM·통계·버전 요약에서 운영 정본·상세 표로 연결 |
| D9 | 수용 | [database/mysql-mariadb.md](../docs/database/mysql-mariadb.md), [database/mysql-operations.md](../docs/database/mysql-operations.md) | 개요와 잠금/SBS 정본 역할 분리 |
| D10 | 부분 수용 | [database/transactions-and-locks.md](../docs/database/transactions-and-locks.md) | 엔진별 오류 후 표 추가. PG savepoint 복구 가능, SQLite 오류별 롤백 차이도 함께 명시 |
| D11 | 수용 | [database/collection-contracts.md](../docs/database/collection-contracts.md) | 권장 statement_timestamp AS sampled_at 선행, 보존 SQL은 고정 실습 입력임을 표시. 입력 파일은 그대로 |
| D12 | 수용 | [glossary.md](../docs/glossary.md), [database/distributed-and-analytical.md](../docs/database/distributed-and-analytical.md), [database/sqlserver-oracle.md](../docs/database/sqlserver-oracle.md), [database/replication-and-recovery.md](../docs/database/replication-and-recovery.md) | 약어 첫 정의와 XID/Xid 등 용어 분리 |
| D13 | 수용 | [database/mysql-operations.md](../docs/database/mysql-operations.md) | GTID 적용 직후와 위치 일치 후를 분리. 검증기 대조 token만 새 라벨에 맞춤, 근거 불변 |
| D14 | 수용 | [database/sqlserver-oracle.md](../docs/database/sqlserver-oracle.md) | PG MVCC와 row versioning의 개념 연결·ADR 정의, 엔진별 구현 차이 유지 |
| C1 | 수용 | [cross-domain/reproducible-labs.md](../docs/cross-domain/reproducible-labs.md), [reading-guide.md](../docs/reading-guide.md), [README.md](../README.md) | P9로 해결 |
| C2 | 수용 | [foundations/README.md](../docs/foundations/README.md), [product/collection-pipelines.md](../docs/product/collection-pipelines.md), [product/telemetry-delivery-contracts.md](../docs/product/telemetry-delivery-contracts.md), [glossary.md](../docs/glossary.md) | OTLP 소개, protobuf snake_case/JSON camelCase 구분, 제품·알림 용어 |
| C3 | 수용 | [product/telemetry-delivery-contracts.md](../docs/product/telemetry-delivery-contracts.md), [product/self-observation-and-access.md](../docs/product/self-observation-and-access.md), [metric-catalog.md](../docs/metric-catalog.md) | send_failed 세 줄 요약·정본 링크·참조표 행 |
| C4 | 수용 | [product/telemetry-delivery-contracts.md](../docs/product/telemetry-delivery-contracts.md), [product/collection-pipelines.md](../docs/product/collection-pipelines.md), [product/capacity-and-loss-budgets.md](../docs/product/capacity-and-loss-budgets.md) | 응답→행동 정본, partial success MUST NOT와 429/502/503/504 통일 |
| C5 | 수용 | [cross-domain/missing-observations.md](../docs/cross-domain/missing-observations.md), [cross-domain/investigation-workbook.md](../docs/cross-domain/investigation-workbook.md), [reading-guide.md](../docs/reading-guide.md) | 먼저 읽을 제품 계약 안내와 학습 경로 |
| C6 | 부분 수용 | [product/adapter-contracts.md](../docs/product/adapter-contracts.md), [product/entities-and-topology.md](../docs/product/entities-and-topology.md), [product/README.md](../docs/product/README.md), [cloud/resources-and-apis.md](../docs/cloud/resources-and-apis.md) | 4a 참조의 상태 축을 정확히 구분. 제안 Accepted 등은 스키마 wire enum으로 가장하지 않음. scheduled_on 목록 추가 |
| C7 | 수용 | [cloud/managed-and-serverless.md](../docs/cloud/managed-and-serverless.md) | CloudWatch/REPORT/Telemetry/SnapStart별 Duration 표, 미확인 설명은 검증 노트 |
| C8 | 수용 | [product/collection-pipelines.md](../docs/product/collection-pipelines.md) | Fluent Bit 사례 하위 절로 단위별 읽기 순서와 세부 표 분리 |
| C9 | 수용 | [metric-catalog.md](../docs/metric-catalog.md) | 필드 참조표를 영역별로 재배열, Lambda/PG 항목을 각 영역에 모음 |
| C10 | 수용 | [README.md](../README.md), [reading-guide.md](../docs/reading-guide.md), [review.md](../docs/review.md) | 학습 경로는 주제명, 자세한 이력은 검토 기록/검증 노트 |
| C11 | 수용 | [cross-domain/resource-failures.md](../docs/cross-domain/resource-failures.md) | 세 종료 경로 정본과 MemAvailable/eviction 신호 차이 연결 |
| C12 | 수용 | [cross-domain/README.md](../docs/cross-domain/README.md) | 중복 4개 목록 삭제, manifest의 7개 상세 목록 하나로 통합 |
| C13 | 수용 | [product/collection-pipelines.md](../docs/product/collection-pipelines.md), [product/capacity-and-loss-budgets.md](../docs/product/capacity-and-loss-budgets.md), [product/storage-and-query.md](../docs/product/storage-and-query.md) | 버퍼 계산 정본은 capacity, 4B/16B는 별개의 가상 가정임을 명시 |
| C14 | 수용 | [cross-domain/capstone-investigation.md](../docs/cross-domain/capstone-investigation.md) | Node 8 vCPU를 최초 증거 표에 추가 |
| C15 | 수용 | [cloud/provider-metrics.md](../docs/cloud/provider-metrics.md), [cloud/late-data-and-reconciliation.md](../docs/cloud/late-data-and-reconciliation.md) | manifest 순서의 다음 링크로 해결 |

### 4a에서 발견한 후보의 처리

4a의 C1–C5는 이번 사용자 C1–C15와 별개입니다.

| 4a ID | 처리 | 반영 |
| --- | --- | --- |
| C1 | 수용 | metric-catalog의 CurrEstab에 6.10/backport 조건 |
| C2 | 수용 | 같은 표의 memory.available에 1.37 gate·Summary 보정·이중 차감 금지 |
| C3 | 수용 | adapter-contracts에서 transform과 bounded_counter_delta의 범위 분리 |
| C4 | 수용 | 검증 기록에 기존 22개·추가 56개를 구분, 예전 1.2 발행 수치는 역사로 유지 |
| C5 | 수용 | 실제 backend_xmin NULL과 가상 replay_lag NULL의 증거 범위를 구분 |

### 새로 명시·계산한 문장과 직접 확인 근거

원고 이동은 기존 출처를 함께 옮겼습니다. 아래는 4c에서 새 문장으로 우선 볼 대상입니다. 확인일은 2026-10-06입니다.

| 새 문장·경계 | 직접 확인 근거 | 위치 |
| --- | --- | --- |
| 추가 문맥 없는 HTTP 4xx는 SERVER MUST unset / CLIENT SHOULD Error, 5xx SHOULD Error | [OTel HTTP status](https://opentelemetry.io/docs/specs/semconv/http/http-spans/#status) | instrumentation-and-profiling |
| metrics-server 0.6+는 /stats/summary 대신 /metrics/resource | [Node Metrics Data](https://kubernetes.io/docs/reference/instrumentation/node-metrics/) | collection 그림 |
| 137=128+9는 SIGKILL과 일치하는 관례이고 OOM 단독 증거 아님 | [Bash Exit Status](https://www.gnu.org/software/bash/manual/html_node/Exit-Status.html), [Pod lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/) | pressure 증거 표 |
| 내부 MTU 1450, 옵션 없는 IPv4/TCP 등 가정에서 1450−20−20=1410 B | [RFC 9293 §3.7.1](https://www.rfc-editor.org/rfc/rfc9293.html#section-3.7.1), 기존 VXLAN 가상 입력·산술 검사 | layers |
| 원표본 p25는 이 책의 nearest-rank로 ceil(0.25×4)=1번째, 1.25초 | 기존 [분포 규칙](../docs/foundations/distributions.md), [저장된 가상 입력](../labs/review-r3/histograms/fixture.json), verify_examples 독립 계산 | histogram-storage |
| burn 4의 7일은 28÷4의 단순 모델이며 실제 소진 일시 보장 아님 | 기존 SLO의 28일·4배 입력, verify_examples 계산 | SLO |
| 10/1 Gbit/s의 32bit octet wrap은 약 3.44/34.4초 | [RFC 2863 카운터 폭](https://www.rfc-editor.org/rfc/rfc2863.html), 2^32×8/bit-rate 독립 계산 | SNMP·network-metrics |
| XID 축의 기본 2억/16억과 wrap까지 남은 4000만/300만은 다른 기준 | [PG18 vacuum](https://www.postgresql.org/docs/18/routine-vacuuming.html#VACUUM-FOR-WRAPAROUND), [failsafe](https://www.postgresql.org/docs/18/runtime-config-vacuum.html#GUC-VACUUM-FAILSAFE-AGE), [REL_18_6 varsup.c](https://github.com/postgres/postgres/blob/REL_18_6/src/backend/access/transam/varsup.c) | PG 운영 |
| PG/MySQL/SQL Server의 일반 읽기·잠금 읽기와 오류 뒤 복구는 서로 다름 | [PG 격리](https://www.postgresql.org/docs/18/transaction-iso.html), [InnoDB 격리](https://dev.mysql.com/doc/refman/8.4/en/innodb-transaction-isolation-levels.html), [SQL Server](https://learn.microsoft.com/en-us/sql/t-sql/statements/set-transaction-isolation-level-transact-sql?view=sql-server-ver17), [MySQL 오류](https://dev.mysql.com/doc/refman/8.4/en/innodb-error-handling.html), [SQLite 오류](https://www.sqlite.org/lang_transaction.html#response_to_errors_within_a_transaction) | transactions |
| Node→QoS/Pod→container의 일반 cgroup 대응은 실제 설정으로 확인 | [자원 관리](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/), [cgroup v2](https://docs.kernel.org/admin-guide/cgroup-v2.html), 기존 원고 계약 | resources |
| 값 품질·가시성·차분·시계 flag·제품 전달 단계는 독립 축 | [현재 참조 코드](../scripts/adapter_contract.py), [카탈로그](../catalog/field-catalog.json), fixture 재검사 | adapter-contracts |

기초 용어집은 각 정본의 정의를 짧게 옮겼습니다. 새로운 지원 버전·기본값·실행 성능을 추가한 표가 아닙니다. 특히 freeze 흐름은 학습 순서, cgroup 계층은 일반 구조, 메모리 API/PDH 대응은 의미 대응이며 원자적 등가값이라는 주장을 피했습니다.

### 구조·검사 변경과 남겨 둔 한계

- book.json은 network의 layers를 상세 2번으로, DB는 기초→엔진→복제·HA→운영 심화→수집·실습 순으로 바꿨습니다. 파일 이동·새 장·판 변경은 없습니다.
- Pulsar/Memcached 절과 kubelet endpoint/PSI·cgroup v1 절은 각각 정본으로 옮겼습니다. 이전/다음과 분야 목록은 manifest에 맞췄습니다.
- verify_examples는 제거한 trace 50.25% 중복 계산 2개를 빼고 버퍼 계산의 원문 경로를 정본으로 변경했습니다. 새 산술 7개를 본문의 실제 표기와 대조합니다(190개/62개 원문).
- verify_review_r3는 MySQL baseline의 표시 문구만 '위치 일치 후(baseline)'로 맞췄습니다. 데이터·판정·hash·입력 검사를 약화시키지 않았습니다.
- chapter-review의 과거 검토 항목은 이전 hash와 함께 남기고, 이번 검토 초점은 문장 이동·의미 보존·선수 개념·탐색으로 표시합니다. hash 갱신을 전수 사실 재검토로 표현하지 않습니다.
- 원시 결과·provenance와 이전 라운드 기록은 수정하지 않았습니다. 서버·cloud 재실행, 외부 URL 전수 검사, 새 BOOK의 브라우저 화면 검사는 수행하지 않았습니다.
- Lambda suppressed init의 CloudWatch Duration 포함 여부, tick 설정 주체·RAW 외부 정확도 등 기존 미확인은 유지했습니다. 이 편집으로 해소됐다고 표시하지 않습니다.

### 4c 우선 검토 대상

pressure의 세 종료 경로·수명 흔적, collection의 metrics-server 경로, transactions의 MVCC/격리/오류 복구 표, MySQL의 GTID 직후/위치 일치 후 구분, adapter의 상태 축을 우선 대조합니다. glossary의 짧은 정의가 정본의 조건을 확대하지 않는지, README·심화 안내·이전/다음으로 초보자가 학습 경로를 따라갈 수 있는지도 봅니다.

### 4b 최종 실행 결과 — 2026-10-06

Windows Python에서 `build_book.py`와 `build_html.py`를 순서대로 실행한 뒤 아래 검사를 모두 통과했습니다. 표의 명령에는 `python -X utf8 -B scripts/` 접두사를 붙입니다.

| 명령 | 결과 |
| --- | --- |
| `check_docs.py` | PASS: Markdown 124개, 상세 100장, 로컬 링크 3,324개; 외부 URL 605개는 목록 검사 |
| `verify_examples.py` | PASS: 원문 62개의 산술·해석 190개 |
| `verify_contracts.py` | PASS: 기존 경계 22개·계산 28개, 추가 계약 56개 |
| `verify_revision.py` | PASS: 보존된 실행·입력 hash·시나리오·525 gzip·본문 수치 |
| `build_book.py --check` | PASS: 원문 122개와 BOOK.md 일치 |
| `build_html.py --check` | PASS: 원문·고정 renderer와 BOOK.html 일치 |
| `verify_field_catalog.py` | PASS: 86개 필드·35개 본문 연결·거부 사례 16개·지원 문서 링크 260개 |
| `build_adapter_fixtures.py --check` | PASS: 출처 21개와 fixture 56개 재추출 일치 |
| `verify_adapter_fixtures.py` | PASS: 실측 입력 29개·가상 입력 26개·혼합 입력 1개 |

추가 확인: `git diff --check` 통과. 브랜치·판·기준일, 장 파일 집합, 보존 실행·provenance·과거 라운드 기록이 그대로임을 대조했습니다. manifest 기반 탐색 119곳과 이 검토 기록의 로컬 링크 249개도 확인했습니다. chapter-review의 이전 내용 검토 metadata를 보존했고 현재 critical excerpt가 모두 해당 원고에 있는지 확인했습니다. 새 HTML 브라우저 화면 검사는 Claude가 `python -X utf8 -B scripts/check_html.py`로 수행합니다.


## 4d — 카탈로그 사실 확인과 재배치 무결성 보완

확인일: 2026-10-06. 번호가 있는 **45개 항목은 수용 41·부분 수용 4·반박 0·보류 0**입니다. 별도로 제시된 미검증 단서 5개는 아래 U1–U5로 기록하며 수용 4·부분 수용 1입니다. 문서·소스·보존 입력을 대조한 검토이고 새 Linux·DB·cloud 실측은 수행하지 않았습니다. 판 번호·판 기준일·장 순서와 원시 실습 결과·hash는 유지했습니다.

### 항목별 판정

표의 카탈로그는 [field-catalog.json](../catalog/field-catalog.json), 참조 구현은 [adapter_contract.py](../scripts/adapter_contract.py), fixture는 [adapter-r4.json](../labs/fixtures/adapter-r4.json)를 뜻합니다. 원고 링크는 변경 위치이며, 근거 링크는 직접 대조한 원천입니다.

| ID | 판정 | 바꾼 파일 | 직접 확인한 근거·수정 범위 |
| --- | --- | --- | --- |
| I1 | 수용 | [PG 운영](../docs/database/postgresql-operations.md), [용어집](../docs/glossary.md) | `hot_standby_feedback` 설정명을 복원. [PG18 GUC](https://www.postgresql.org/docs/18/runtime-config-replication.html#GUC-HOT-STANDBY-FEEDBACK); R17과 함께 설정 위치·기본값 명시 |
| I2 | 수용 | [coverage](../docs/coverage.md), [재현](../docs/cross-domain/reproducible-labs.md), [Linux 실습](../docs/host/linux-observation-lab.md), [전송](../docs/product/telemetry-delivery-contracts.md) | 원문 대조: 작업자·회차를 날짜·주제로 정리. 증거 경로·재현 명령의 고유 이름은 보존하고 상세 이력은 review·validation으로 연결 |
| CL1 | 수용 | 카탈로그, [PG 운영](../docs/database/postgresql-operations.md), [지표표](../docs/metric-catalog.md), fixture | [PG16 reads](https://www.postgresql.org/docs/16/monitoring-stats.html#MONITORING-PG-STAT-IO-VIEW), [18 reads](https://www.postgresql.org/docs/18/monitoring-stats.html#MONITORING-PG-STAT-IO-VIEW), [f92c854c](https://github.com/postgres/postgres/commit/f92c854c). 16–17 fixed-block과 18 request 정의를 별도 ID로 분리; 업그레이드 `definition_changed` 가상 사례 |
| CL2 | 수용 | 카탈로그, 참조 구현·fixture, [전송](../docs/product/telemetry-delivery-contracts.md), [지표표](../docs/metric-catalog.md) | [기본 `_total` 이름](https://opentelemetry.io/docs/collector/internal-telemetry/), [0.162.0 config·snapshot](../labs/results/1.1-r2-otel.json). 기본 이름과 suffix-off 실측을 구분; exporter·instance·error 속성 보존. 0.137.0을 이 필드의 실측 검토 목록에서 제외 |
| CL3 | 부분 수용 | 카탈로그, 참조 구현·fixture, [전송](../docs/product/telemetry-delivery-contracts.md), [어댑터](../docs/product/adapter-contracts.md) | [OTLP](https://opentelemetry.io/docs/specs/otlp/), [ProtoJSON](https://protobuf.dev/programming-guides/json/). 생략 0·거절 0과 메시지의 경고·int64 문자열을 반영. 단 임의 2xx가 아니라 **HTTP 200의 유효 성공 응답**에 적용 |
| CL4 | 수용 | 카탈로그 | [v6.12 ipv4 proc](https://github.com/torvalds/linux/blob/v6.12/net/ipv4/proc.c), [UDP IPv6 계정](https://github.com/torvalds/linux/blob/v6.12/include/net/udp.h). UDP IPv4/IPv6 scope 분리, TCP는 양 address family를 합산하는 namespace 계정 |
| CL5 | 부분 수용 | 카탈로그, [PG 운영](../docs/database/postgresql-operations.md), [복제](../docs/database/replication-and-recovery.md) | [REL_18_6 view 조인](https://github.com/postgres/postgres/blob/REL_18_6/src/backend/catalog/system_views.sql#L906), [공개 backend_xmin](https://github.com/postgres/postgres/blob/REL_18_6/src/backend/utils/adt/pgstatfuncs.c#L361), [W 함수 권한](https://github.com/postgres/postgres/blob/REL_18_6/src/backend/replication/walsender.c#L4018). replay_lag는 권한 NULL 추가; backend_xmin은 이 권한 마스킹 대상이 아님 |
| CL6 | 수용 | 카탈로그, [PG 운영](../docs/database/postgresql-operations.md) | [17 num_timed](https://www.postgresql.org/docs/17/monitoring-stats.html#MONITORING-PG-STAT-CHECKPOINTER-VIEW)도 completed/skipped 포함. 18 num_done 추가와 구분 |
| CL7 | 수용 | 카탈로그, [MySQL 개요](../docs/database/mysql-mariadb.md) | [8.4 statement summary](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-statement-summary-tables.html). (SCHEMA_NAME,DIGEST), catch-all NULL, FIRST_SEEN 보조 수명 표식, TRUNCATE의 행 삭제 |
| CL8 | 부분 수용 | 카탈로그, [cloud 재조회](../docs/cloud/late-data-and-reconciliation.md) | [GetMetricData](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_GetMetricData.html), [MetricDataResult](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_MetricDataResult.html). 응답 Unit 부재·비변환 반영. Unit 지정은 direct metric의 **제품 제안**이며 API 필수 인자가 아님; math는 별도 |
| CL9 | 수용 | 카탈로그, [압박](../docs/kubernetes/pressure-and-termination.md) | [1.37 summary.go](https://github.com/kubernetes/kubernetes/blob/v1.37.0/pkg/kubelet/server/stats/summary.go). gate on·capacity 양수·관측값 존재 조건과 정의 문맥 기록 |
| CL10 | 수용 | 카탈로그 | [v6.12 swap_writepage](https://github.com/torvalds/linux/blob/v6.12/mm/page_io.c). zero-filled folio와 zswap 경로는 pswpout에 포함되지 않음; zram과 구분 |
| CL11 | 수용 | 카탈로그 | [v6.12 account_guest_time](https://github.com/torvalds/linux/blob/v6.12/kernel/sched/cputime.c). nice의 guest_nice 포함, 프로세스 utime의 guest 시간 포함과 이중 합산 금지 |
| CL12 | 수용 | 카탈로그 | [boot_id 원천](https://www.kernel.org/doc/html/latest/admin-guide/sysctl/kernel.html#random). vmstat 6개·memory PSI some.total의 같은 부팅 누적 수명 표식 추가 |
| CL13 | 수용 | 카탈로그 | [v6.12 do_task_stat](https://github.com/torvalds/linux/blob/v6.12/fs/proc/array.c). utime/stime 출력에는 ptrace 마스킹 없음. 실제 procfs hidepid·PID 가시성 제약으로 한정 |
| CL14 | 수용 | 카탈로그 | [TCP 수정](https://github.com/torvalds/linux/commit/a46d0ea5c942), [v6.9](https://github.com/torvalds/linux/blob/v6.9/net/ipv4/tcp.c)·[v6.10](https://github.com/torvalds/linux/blob/v6.10/net/ipv4/tcp.c), [memcontrol 6.13](https://github.com/torvalds/linux/blob/v6.13/mm/memcontrol.c)·[6.15](https://github.com/torvalds/linux/blob/v6.15/mm/memcontrol.c), [vmscan 6.15 reclaimer_offset](https://github.com/torvalds/linux/blob/v6.15/mm/vmscan.c) 연결 |
| CL15 | 수용 | 카탈로그, [PG 운영](../docs/database/postgresql-operations.md), fixture | [REL_18_6 STATE_UNDEFINED](https://github.com/postgres/postgres/blob/REL_18_6/src/backend/utils/adt/pgstatfuncs.c#L412)는 NULL. backend_type도 권한으로 가려질 수 있어 보조 문맥만으로 원인 확정하지 않음 |
| R1 | 수용 | [자원 제어](../docs/containers/resource-control.md) | 연결 대상 원문 대조. cAdvisor와 Windows working set 링크를 각각 실제 설명 장으로 분리 |
| R2 | 수용 | [쓰기 지속성](../docs/storage/write-path-and-durability.md) | [PG18 async commit](https://www.postgresql.org/docs/18/wal-async-commit.html). fsync-off 손상은 hardware/OS crash, async commit의 유실은 DB crash/immediate shutdown까지 구분 |
| R3 | 수용 | [압박](../docs/kubernetes/pressure-and-termination.md), [자원 설정](../docs/kubernetes/resources-and-scheduling.md), [메모리 계정](../docs/containers/memory-accounting-and-oom.md), [회수](../docs/host/reclaim-and-oom.md) | [1.37 Node Allocatable cgroup](https://github.com/kubernetes/kubernetes/blob/v1.37.0/pkg/kubelet/cm/node_container_manager_linux.go), [계층 한도](https://docs.kernel.org/admin-guide/cgroup-v2.html). 컨테이너·Pod·kubepods 등 cgroup 한도 OOM으로 확장 |
| R4 | 수용 | [자원 설정](../docs/kubernetes/resources-and-scheduling.md) | [1.37 qos_container_manager](https://github.com/kubernetes/kubernetes/blob/v1.37.0/pkg/kubelet/cm/qos_container_manager_linux.go). Guaranteed는 rootContainer, Burstable/BestEffort만 QoS 하위 그룹; 그림 수정 |
| R5 | 수용 | [Windows](../docs/host/windows.md) | [PhysicalTotal](https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-performance_information), [설치 RAM](https://learn.microsoft.com/en-us/windows/win32/api/sysinfoapi/nf-sysinfoapi-getphysicallyinstalledsystemmemory). 실제 OS 가용 물리량과 SMBIOS 설치량 분리 |
| R6 | 수용 | [메모리 계정](../docs/containers/memory-accounting-and-oom.md) | 문단 이동 위치 대조. 아래→위 working set 식 |
| R7 | 수용 | [압박](../docs/kubernetes/pressure-and-termination.md) | [설명 문서](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/#node-out-of-memory-behavior) 하한 2와 [고정 1.37 코드](https://github.com/kubernetes/kubernetes/blob/v1.37.0/pkg/kubelet/qos/policy.go) 하한 3 대조 복원. gate 의존 DRA 보정도 명시 |
| R8 | 수용 | [SNMP](../docs/network/snmp-and-device-models.md), [계산 연결](../scripts/verify_contracts.py) | 2^32×8 / link-bit-rate 직접 계산. 10 Gbit/s 약 3.44초·1 Gbit/s 약 34.4초로 통일; 정확한 기대값 유지 |
| R9 | 수용 | [쓰기 지속성](../docs/storage/write-path-and-durability.md) | 복제 단계 대응표와 그림 대조. 수신→write→flush→replay를 분리하고 조사 오타 수정 |
| R10 | 수용 | [회수](../docs/host/reclaim-and-oom.md) | [페이지 할당 API](https://docs.kernel.org/core-api/mm-api.html). 2^order개의 연속 페이지로 정의 |
| R11 | 수용 | [메모리](../docs/host/memory.md) | [v6.12 show_val_kb](https://github.com/torvalds/linux/blob/v6.12/fs/proc/meminfo.c#L30)의 PAGE_SHIFT−10 환산으로 1024 B 근거 교체 |
| R12 | 수용 | [인벤토리](../docs/kubernetes/inventory-consistency.md) | [apimachinery ListOptions](https://github.com/kubernetes/apimachinery/blob/v0.37.0/pkg/apis/meta/v1/types.go#L448), [상수](https://github.com/kubernetes/apimachinery/blob/v0.37.0/pkg/apis/meta/v1/types.go#L508)로 initial-events-end 근거 추가 |
| R13 | 수용 | [저장 용량](../docs/storage/capacity-and-protection.md) | [Squid PG concepts](https://docs.ceph.com/en/squid/rados/operations/pg-concepts/). Acting Set·Peering 근거 추가; OSD glossary 링크 유지 |
| R14 | 수용 | [플랫폼](../docs/containers/platform-differences.md) | [1.37 kubelet config](https://github.com/kubernetes/kubernetes/blob/v1.37.0/staging/src/k8s.io/kubelet/config/v1beta1/types.go#L957)에서 failCgroupV1 false override 확인 |
| R15 | 수용 | [네트워크 계층](../docs/network/layers-and-routing.md) | [RFC1122 §1.3.3](https://www.rfc-editor.org/rfc/rfc1122.html#section-1.3.3)으로 용어 근거 절 수정 |
| R16 | 수용 | [트랜잭션](../docs/database/transactions-and-locks.md), [용어집](../docs/glossary.md) | [REL_18_6 recently_dead 집계](https://github.com/postgres/postgres/blob/REL_18_6/src/backend/access/heap/vacuumlazy.c#L941), [기존 실습](../labs/results/1.1-r2-postgresql.json). 이전 버전 중 아직 제거할 수 없는 것을 제외한 정의로 쓰지 않음 |
| R17 | 수용 | [PG 운영](../docs/database/postgresql-operations.md), [용어집](../docs/glossary.md) | [PG18 GUC](https://www.postgresql.org/docs/18/runtime-config-replication.html#GUC-HOT-STANDBY-FEEDBACK), [고정 실행기](../scripts/run_postgres_r2_lab.py). standby에서 on·기본 off·upstream standby, 실습 interval 1s 복원 |
| R18 | 수용 | [미들웨어 목차](../docs/middleware/README.md), [메시지 큐](../docs/middleware/message-queues.md) | [Pulsar4.1 batching](https://pulsar.apache.org/docs/4.1.x/concepts-messaging/#batching). backlog size의 batch(entry) 단위 명시; 모든 Pulsar metric의 공통 단위로 확대하지 않음 |
| R19 | 수용 | [미들웨어 목차](../docs/middleware/README.md) | 표 중간 빈 줄을 없애 프록시·스트림 두 행을 같은 GFM 표로 복원 |
| R20 | 수용 | [용어집](../docs/glossary.md) | offset의 위치와 업무 완료를 구분. 잘못 추가된 시각 비교 제거 |
| R21 | 수용 | [용어집](../docs/glossary.md) | Linux/Kubernetes/CloudWatch namespace, 메모리/DB/Kafka commit, active·used·lag의 원천별 문맥 경고와 정본 링크 복원 |
| R22 | 수용 | [MySQL 운영](../docs/database/mysql-operations.md), [재현](../docs/cross-domain/reproducible-labs.md) | [8.4.11 전후 표본](../labs/results/1.1-r3/mysql-8.4.11-r2.json), [9.7.2](../labs/results/1.1-r3/mysql-9.7.2-r2.json). GTID 적용 직후와 위치 일치 후 baseline 구분; 보완 실행으로 표기 |
| R23 | 부분 수용 | [어댑터](../docs/product/adapter-contracts.md) | 참조 함수 반환값 직접 대조. OTLP 3 outcome, watch·UID·CloudWatch 상태와 cpu_clock_quality 이름 추가. `retryable`은 outcome이 아니라 별도 boolean |
| R24 | 수용 | [트랜잭션](../docs/database/transactions-and-locks.md) | [SQLite transaction 오류](https://www.sqlite.org/lang_transaction.html#response_to_errors_within_a_transaction). FULL/IOERR/INTERRUPT/NOMEM의 자동 롤백 가능성과 명시적 정리 권고; COMMIT BUSY는 transaction 유지·재시도 가능 |
| R25 | 수용 | [용어집](../docs/glossary.md), [쓰기 지속성](../docs/storage/write-path-and-durability.md) | Raft/etcd 링크를 분산 시스템으로 수정. Checkpoint 정의를 대상 장에 [PG18 WAL configuration](https://www.postgresql.org/docs/18/wal-configuration.html) 근거로 추가 |
| R26 | 수용 | [용어집](../docs/glossary.md), [Kafka](../docs/middleware/kafka.md) | [Kafka4.3 min.insync.replicas](https://kafka.apache.org/43/configuration/topic-configs/#min.insync.replicas): ISR에 leader 포함 |
| R27 | 수용 | [Sampling](../docs/application/trace-sampling-and-context.md) | [OTel probability sampling](https://opentelemetry.io/docs/specs/otel/trace/tracestate-probability-sampling/). th를 거절 임계값(rejection threshold)으로 통일 |
| R28 | 수용 | [어댑터](../docs/product/adapter-contracts.md), [용량](../docs/product/capacity-and-loss-budgets.md) | 원래 설계 의도와 4상태 표 대조. agent 읽기·gateway 인증/schema 검증을 수용 전 관측 경계로 복원. 새 wire enum을 만들거나 검증 성공으로 Accepted를 추정하지 않음 |

### 부분 수용의 이유

- **CL3:** OTLP 성공을 임의 2xx로 넓히지 않았습니다. HTTP 200의 해석된 ExportTraceServiceResponse에서만 protobuf 기본값을 적용합니다. 거절 0+메시지는 `warning=true`; 음수·비정수·int64 초과·bool·잘못된 메시지 자료형은 거부합니다. 큰 숫자를 이미 binary64로 정밀도 손실해 받은 경우에는 복구를 가장하지 않고 거부하는 좁은 참조입니다. 전체 wire decoder는 아닙니다.
- **CL5:** “pid 외 전부 NULL”은 walsender 함수의 `W.*`에 관한 설명입니다. `pg_stat_replication`은 activity의 `S.*`와 조인하며, `S.backend_xmin`은 권한 검사 앞에서 공개됩니다. 따라서 replay_lag에는 권한 NULL을 추가하되 backend_xmin에 같은 제한을 복사하지 않았습니다. 이 반론의 직접 확인 범위는 REL_18_6 소스이며 새로운 비권한 세션 실측이 아닙니다.
- **CL8:** 요청 Unit 생략과 미변환 문제는 수용하지만 Unit이 API의 필수 인자는 아닙니다. 직접 metric의 수집 계약에서 명시하자는 제품 제안으로 기록했고 metric math의 단위는 별도 계약으로 남겼습니다.
- **R23:** 함수의 실제 자료형을 보존했습니다. `retryable`·`remove_current`·`complete`는 boolean이고 outcome·identity·status enum과 섞지 않았습니다.

### 번호 없는 미검증 단서

| ID | 판정 | 반영·남은 범위 | 근거 |
| --- | --- | --- | --- |
| U1 양의 RV + match 생략 | 수용 | 인벤토리 표에 limit 없는 NotOlderThan, 양수 limit·continue 없는 Exact 추가. continue+양의 RV는 유효하지 않음 | [API GET/LIST 표](https://kubernetes.io/docs/reference/using-api/api-concepts/#semantics-for-get-and-list) |
| U2 static Pod UID | 부분 수용 | controller의 새 API Pod UID 규칙을 static Pod 재실행까지 일반화하지 않음. 로컬 명세 hash UID와 mirror Pod를 구분; 축출·재실행 실측은 미수행 | [1.37 applyDefaults](https://github.com/kubernetes/kubernetes/blob/v1.37.0/pkg/kubelet/config/common.go#L67), [static Pod](https://kubernetes.io/docs/tasks/configure-pod-container/static-pod/) |
| U3 ResourceVersion 용어집 | 수용 | 응답 서버 규약 확인에 더해 같은 cluster·resource type 안의 순서 비교로 범위 표시 | [resourceVersion](https://kubernetes.io/docs/reference/using-api/api-concepts/#resource-versions) |
| U4 Kafka HW 출처 | 수용 | 용어표에 성공적으로 복제된 마지막 offset+1 정의와 현재 Consumer API 링크 사용 | [4.3 endOffsets](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html) |
| U5 SQL Server cursor | 수용 | 일반 SELECT FOR UPDATE와 DECLARE CURSOR의 FOR UPDATE 절을 구분하는 문장 추가 | [DECLARE CURSOR](https://learn.microsoft.com/en-us/sql/t-sql/language-elements/declare-cursor-transact-sql?view=sql-server-ver17) |

### 산출물·검사 범위

- 카탈로그 **87개**: Linux29·cgroup10·Kubernetes9·PostgreSQL20·MySQL8·OTLP6·CloudWatch5. 검토 범위와 실제 도입 시점을 분리하고 `pg.io.reads` ID는 16–17 의미로 좁혔습니다. 소비자가 정의를 저장한 경우 업그레이드 때 정의 경계를 적용해야 합니다.
- 추가 fixture **74개**: 실측29·가상44·mixed1. 기존56개에서 가상18개를 보강했습니다. OTLP 정상/경고/생략/null/문자열·숫자/int64 범위/오류, 기본 Collector 접미사, PG I/O 정의 변화와 미확정 state NULL입니다. 기존22개·본문 계산28개는 별도 유지합니다.
- 입력 출처 **21개 파일**을 유지했고 원시 JSON·gzip·verdict·provenance를 변경하지 않았습니다. fixture의 기대 출력은 함수 실행값을 복사해서 생성하지 않았습니다.
- 카탈로그 검증은 본문 연결38개·거부16개를 확인합니다. 원천 URL21개를 추가 GET해 모두 HTTP200을 받았고 기존39개의 실제 상태·MySQL403 기록은 그대로 보존합니다. 합계60개 URL의 접근 기록은 사실성 인증이 아닙니다.
- 장·파일 이동과 book.json 변경 없음. 상세100장·원문122개를 유지합니다. 새 사실 설명 옆의 1차 근거와 변경 장 검토 hash를 갱신하되 앞선 검토 기록도 보존합니다.

최종 검증 명령은 [현재 검증 기록](../docs/validation.md#수집-계약재배치-후속-검토의-검사--2026-10-06)에 모았습니다. 9개 검사와 BOOK 재생성 결과는 아래 완료 기록에 남깁니다. 이번 HTML의 브라우저 화면 검사는 실행하지 않았고, 전달받은 수정 전 `html-check.json`은 그대로 두었습니다.

### 남은 확인 범위

static Pod 축출·재실행의 실제 수명 표본, Lambda suppressed init의 CloudWatch Duration 포함 여부, WSL tick 설정 주체·RAW의 외부 정확도, 최초 MySQL 표본의 내부 clock_diff 산술은 이번 근거만으로 확정하지 않습니다. 카탈로그·참조 구현은 운영 parser나 제품의 모든 버전·권한 조합에 대한 지원 인증이 아닙니다. 이전 라운드 원시 증거를 새 구현의 실행 결과로 바꾸지 않습니다.

### 4d 완료 검사

2026-10-06, Windows Python에서 아래 **9개 모두 PASS(exit code 0)**를 확인했습니다. 먼저 `python -X utf8 -B scripts/build_book.py`, 이어서 `python -X utf8 -B scripts/build_html.py`로 두 통합본을 재생성했습니다.

| 실행 명령 | 결과 |
| --- | --- |
| `python -X utf8 -B scripts/check_docs.py` | PASS: Markdown 124개, 상세100장, 로컬 링크·앵커·검토 hash |
| `python -X utf8 -B scripts/verify_examples.py` | PASS: 62개 원문 산술·해석190개 |
| `python -X utf8 -B scripts/verify_contracts.py` | PASS: 기존22개·본문 계산28개·확장 fixture74개 |
| `python -X utf8 -B scripts/verify_revision.py` | PASS: 기존 실행과 시계, API·DB·Collector36조건, 메모리·분포·MySQL27판정·gzip525개, 입력·원시 hash |
| `python -X utf8 -B scripts/build_book.py --check` | PASS: 원문122개와 BOOK.md 일치 |
| `python -X utf8 -B scripts/build_html.py --check` | PASS: 원문·고정 renderer와 BOOK.html 일치 |
| `python -X utf8 -B scripts/verify_field_catalog.py` | PASS: 필드87개·본문 연결38개·거부16개·근거/링크 |
| `python -X utf8 -B scripts/build_adapter_fixtures.py --check` | PASS: fixture74개·원본21개 재추출 일치 |
| `python -X utf8 -B scripts/verify_adapter_fixtures.py` | PASS: 실측29·가상44·mixed1 |

`git diff --check`도 통과했습니다. `book.json`과 전달받은 `review/html-check.json`의 작업 전후 SHA256이 같습니다. `labs/results/`, `labs/archive/`, `review/evidence-provenance.json`에는 변경이 없습니다. commit·push·브랜치 전환을 수행하지 않았습니다.

Claude의 남은 화면 확인 명령은 `python -X utf8 -B scripts/check_html.py`입니다. 앞선 화면 PASS를 이번 새 BOOK의 화면 검사로 재사용하지 않습니다.
