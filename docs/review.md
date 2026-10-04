# 제1.1판의 검토와 수정 기록

2026-10-04에 작성·자체 검토·공식 원천 대조·실제 실행을 반복한 보강판입니다. 제1.0판의 80장에서 **92장**으로 확장했습니다. 이번 검토는 작성자의 자체 검토이며 외부 전문가 감수를 의미하지 않습니다. 실행 환경과 자동 검사 결과는 [검증 기록](validation.md)에 있습니다.

## 보강을 결정한 이유

기존 판에는 주요 개념과 원천 필드가 있었지만, 그 의미가 실제 실패·부분 결과·재조회에서 어떻게 달라지는지 확인할 자료가 더 필요했습니다. “값을 읽었다”에서 “제품에서 어떤 뜻으로 저장해야 하는가”까지 이어지도록 12개 장, 5개 실습 묶음의 31개 실제 시나리오, 해설이 있는 합성 연습을 추가했습니다.

실습은 원문 설명을 대신하는 데모가 아닙니다. 원천 규약을 먼저 확인하고 작은 실험에서 무엇을 관측했는지 기록했습니다. 그 결과가 규약 전체나 다른 환경의 보장까지 증명하지 않는다는 경계도 각 장에서 설명합니다.

## 새로 작성한 장과 핵심 질문

| 장 | 답하는 질문 |
| --- | --- |
| [측정과 비교](foundations/measurement-and-comparability.md) | 이름이 같은 값이 다를 때 무엇부터 맞춰야 하는가? |
| [Linux 실제 관측](host/linux-observation-lab.md) | CPU 시간·상주 메모리·논리 I/O의 원천은 무엇인가? |
| [DNS와 연결 수명](network/dns-and-connection-lifecycle.md) | 이름 조회·연결·헤더·본문의 완료는 어떻게 다른가? |
| [쓰기 지속성](storage/write-path-and-durability.md) | write·fsync·commit·복제 중 어디까지 완료됐는가? |
| [메모리 계정과 OOM](containers/memory-accounting-and-oom.md) | heap·RSS·working set·limit과 OOM 사건은 어떻게 연결되는가? |
| [Kubernetes 인벤토리](kubernetes/inventory-consistency.md) | 부분 목록·watch·선택 집합 이탈·실제 삭제를 어떻게 구분하는가? |
| [Trace sampling](application/trace-sampling-and-context.md) | 상세 trace의 오류 비율을 전체 요청에 적용할 수 있는가? |
| [PostgreSQL 동시성](database/postgresql-concurrency-lab.md) | 잠금·오류·권한·snapshot이 실제 조회에 무엇을 바꾸는가? |
| [Cloud 재조회](cloud/late-data-and-reconciliation.md) | 늦은 집계를 다시 받으면 더해야 하는가, 대체해야 하는가? |
| [분석 연습과 해설](cross-domain/investigation-workbook.md) | 주어진 증거로 어디까지 결론을 낼 수 있는가? |
| [관측 데이터 전송](product/telemetry-delivery-contracts.md) | 부분 성공과 응답 유실을 제품에서 어떻게 해석하는가? |
| [필드 계약과 수용 기준](product/compatibility-and-acceptance.md) | 어댑터 지원의 근거를 필드별로 어떻게 남기는가? |

## 검토에서 수정하거나 구체화한 사실

| 항목 | 확인한 근거와 반영 |
| --- | --- |
| Kubernetes resourceVersion | 1.34의 동일성 비교 규약과 1.35의 제한된 순서 비교 규약을 대조해 기존 세 장을 수정. 같은 클러스터의 API group·resource type, 십진수 형식·임의 정밀도 조건을 구분 |
| Kubernetes watch의 DELETED | selector에서 빠진 ConfigMap의 DELETED 뒤 직접 GET 200·동일 UID를 실제 확인. 수집 집합 이탈과 원천 삭제를 분리 |
| PostgreSQL active | active·Lock·transactionid와 blocker를 함께 관측. active를 CPU 실행과 같은 뜻으로 표시하지 않음 |
| PostgreSQL 오류 후 상태 | timeout·CHECK 위반 뒤 25P02, savepoint 복구를 실행. 기존 SQLite 결과와 엔진별 차이를 설명 |
| PostgreSQL 통계 | stats_reset NULL, 권한에 따른 NULL, 통계 snapshot의 4→4→10을 확인. 원래 수집 SQL도 18.6에서 실행 |
| OTLP/HTTP 재시도 | 공식 규약의 429·502·503·504와 실제 500 1회 전송을 대조. 모든 5xx를 재시도한다는 일반화 배제 |
| OTLP 부분 성공 | 목적지의 1개 거절 선언이 이 Collector 구성의 upstream 응답에 그대로 전달되지 않음. upstream 200을 종단 간 수용률로 사용하지 않음 |
| OTLP 응답 유실 | 같은 span 2개가 두 요청에 반복되어 4개 항목·고유 ID 2개 수신. 영속 저장의 중복을 실험한 것으로 표현하지 않음 |
| Linux 메모리·I/O | 32MiB 매핑 전후 Rss와 논리 읽기·저장 계층 읽기를 관측. 주소 공간·상주량·캐시를 구분 |
| cAdvisor working set | 0.52.1 코드의 Usage−inactive file 계산과 0 하한 확인. 회수 불가능한 메모리의 정확한 총량이라는 해석 배제 |
| HTTP 완료 | 200·Content-Length 10 뒤 본문 5B만 와 IncompleteRead. 헤더 성공과 메시지 완료 구분 |
| CloudWatch 결과 | 결과별 StatusCode, timestamp-value 대응, StartTime 포함·EndTime 제외를 확인. HTTP 성공과 완전성, 재조회와 중복 합산 분리 |

위 표의 공식 원천·주장·범위는 [주요 사실 대조 기록](../review/fact-review-1.1.json)에 연결했습니다. 실제 결과는 각 실습의 JSON에 있으며 실행 코드·입력의 SHA256도 함께 보존했습니다.

## 예상과 달랐던 결과를 처리한 방식

**Linux CPU 계정과 시계:** 짧은 측정에서 1을 넘는 CPU초/경과초 비율이 나와 1초·2초 목표 구간으로 다시 관측했습니다. 두 구간에서도 약 1.06이었습니다. 원천 tick을 초로 바꾸는 계산은 확인했지만 서로 다른 시계·계정 사이 차이의 근본 원인은 규명하지 못했습니다. 이를 짧은 구간 반올림만의 문제로 단정하거나 100%로 잘라 숨기지 않았습니다. 해당 WSL 환경의 관측이며 장비 성능 기준으로 쓰지 않습니다.

**Kubernetes 과거 버전 조회:** 예비 시도에서 오래된 조회가 200을 반환해, 단순한 etcd compaction만으로 원하는 만료 응답을 보장할 수 없음을 확인했습니다. 최종 실험에서는 전용 서버의 watch cache를 끄고 physical compaction 완료를 요청해 410을 재현했습니다. 두 설정을 동시에 바꾸었으므로 cache 하나의 인과 효과를 분리 입증한 것은 아닙니다. 성공 기록의 설정과 초기 시도의 해석 한계를 구분했습니다.

## 읽기 쉽게 바꾼 부분

새 장은 쉬운 상황 설명 뒤에 원천의 정의를 두고, 실습은 **작업 순서 → 실제 관측값 → 해석 → 추가로 확인할 것**으로 구성했습니다. 해설 연습에서는 실제 고객 장애로 꾸민 숫자를 사용하지 않고 가정과 입력을 먼저 적었습니다. 용어집·지표 참조표·학습 안내에도 새 장의 경로를 연결했습니다.

자동 검사는 원시 결과의 주요 값, 입력 hash, 실행한 SQL과 본문의 일치, 대표 계산을 다시 대조합니다. 자동 통과를 모든 문장의 사실 인증으로 표현하지 않습니다.

## 제1.0판에서 유지한 근거

기존 판의 SQLite·HTTP/1.0·Windows API·promtool 3.5.0 실행 기록, 146개 대표 예시 검사, 22개 어댑터 입력 사례와 28개 계산 검사를 유지했습니다. guest CPU 중복 합산, Windows kernel의 idle 포함, sector 단위, SNMP 불연속, DB 지속성 조건 등의 기존 설명도 유지했습니다. 이번 판에서 바꾸지 않은 모든 출처를 새로 사실 대조했다고 표시하지 않습니다.

## 검토 기록과 개정 기준

[장별 기록](../review/chapter-review.json)은 상세 장의 내용 hash·범위·검토 초점을 보존합니다. [URL 조회 기록](../review/source-status.json)은 주소의 접근 상태이며 사실 대조 기록과 역할이 다릅니다. 기존 장의 출처 확인일과 이번 편집·추가 검토일도 구분합니다.

실제 cloud 계정·상용 SNMP 장비·여러 DB 엔진·Kubernetes workload·분산 HA·전원 장애·OOM은 이번에 실행하지 않았습니다. 새로운 버전의 보장이나 반례, 실제 배포 증거가 생기면 해당 장과 결과를 다시 검토합니다. 제1.1판은 보강된 학습·설계 지식서이며 모든 제조사·모든 버전의 지식을 영구히 망라했다는 선언으로 사용하지 않습니다.
