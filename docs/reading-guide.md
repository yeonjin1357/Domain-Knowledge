# 이 지식서를 읽는 방법

이 책은 통합 모니터링 제품을 만드는 개발자가 도메인 지식을 처음부터 익히도록 구성한 제1.2판입니다. 낯선 용어가 나와도 외부 문서를 모두 읽어야 다음으로 넘어가도록 구성하지 않았습니다. 핵심 설명은 본문에 두고 출처는 그 설명을 확인할 근거로 연결했습니다.

## 한 파일로 읽기

**[BOOK.html](../BOOK.html)을 브라우저에서 열면** 목차 검색·표·그림을 포함한 전체를 읽을 수 있습니다. 본문 검색은 Ctrl+F를 사용합니다. Markdown을 선호하면 [BOOK.md](../BOOK.md), 작은 파일별 탐색은 [분야별 목차](../README.md)를 사용합니다. 내용의 원본은 `docs/`이며 두 통합본은 같은 원문에서 생성됩니다.

## 처음 읽는 순서

처음에는 [시스템 지도](foundations/system-map.md)부터 읽습니다. 호스트·프로세스·서비스·컨테이너·Pod가 어떻게 다른지 이해한 뒤 개별 지표로 들어가면 용어를 외우는 부담이 줄어듭니다.

| 단계 | 읽을 내용 | 스스로 설명해 볼 질문 |
| --- | --- | --- |
| 1 | 시스템 지도 → 시계열 → 분포 → 성능과 통계 | 현재값·누적값·평균·p95는 어떤 질문에 답하는가? |
| 2 | CPU → 메모리 → I/O → 주소·DNS → TCP → TLS·HTTP | 실행과 대기는 어떻게 다르고 어느 경계에서 시간이 걸리는가? |
| 3 | 컨테이너 격리 → cgroup → Pod 수명 → 배치 → CNI·CSI | 호스트가 한가한데 컨테이너가 제한되거나 Pod가 준비되지 않을 수 있는가? |
| 4 | 요청 → 연결 풀 → transaction·잠금 → 쿼리 → 복제·HA | 요청이 어떤 자원을 기다리고 언제 성공했다고 말할 수 있는가? |
| 5 | 캐시·Kafka·메시지·검색·스트림 → 클라우드 | 처리 진행과 실제 업무 완료를 어떻게 구분하는가? |
| 6 | 따라 하기 실습 → 어댑터 계약 → 종합 분석 연습 → 나머지 제품 설계 | 원천의 뜻과 불확실성을 수집·저장·화면까지 보존할 수 있는가? |

모든 분야를 한 번에 암기할 필요는 없습니다. 첫 번째로 읽을 때는 개념과 계산 예시를 따라가고, 두 번째에는 자신의 제품에서 사용할 원천 필드·권한·수명·결측 처리를 확인합니다. Windows·GPU·특정 DB처럼 당장 필요하지 않은 구현 사례도 공통 개념을 익힌 뒤 찾아볼 수 있습니다.

## 각 장을 읽는 방법

각 장은 선수 개념이나 구체적인 상황을 먼저 설명합니다. 실제 실습 장은 작업 순서, 관측값, 해석, 그 결과만으로 알 수 없는 것의 순서로 읽습니다. 이어서 동작·원천·예시·한계·제품 적용·이해 확인을 읽습니다. 예시의 숫자를 한 번 직접 계산하면 어떤 분모와 시간 범위를 사용하는지 확인할 수 있습니다.

낯선 약어는 [용어집](glossary.md)에서 짧은 정의를 보고 연결된 장으로 돌아옵니다. 표에 있는 수치가 임계값인지, 가상의 계산 입력인지, 실제 측정값인지도 확인합니다.

## 목적별 찾아보기

| 목적 | 경로 |
| --- | --- |
| 새 수집기 구현 | [시계열](foundations/time-series.md) → [호스트 계약](host/collection-contracts.md) / [SNMP](network/snmp-and-device-models.md) / [DB 계약](database/collection-contracts.md) → [어댑터 계약](product/adapter-contracts.md) |
| 느린 요청 조사 | [trace](foundations/traces-logs-profiles.md) → [연결 풀](application/servers-and-pools.md) → [잠금](database/transactions-and-locks.md) → [사례](cross-domain/slow-requests.md) |
| 실행·자원 장애 조사 | CPU·메모리 → cgroup·Pod → [자원 장애](cross-domain/resource-failures.md) |
| 대상·관계 설계 | 프로세스·Pod·cloud ID → [entity와 topology](product/entities-and-topology.md) |
| 알림 구현 | [데이터 품질](foundations/time-and-data-quality.md) → [SLO](foundations/service-level-objectives.md) → [알림](product/alerts-and-incidents.md) → [PromQL 실습](cross-domain/reproducible-labs.md) |
| 용량 계획 | [성능과 통계](foundations/performance-and-statistics.md) → [보존과 질의](product/storage-and-query.md) → [용량과 손실 예산](product/capacity-and-loss-budgets.md) |

## 원천 필드까지 이해하려는 두 번째 읽기

다음 경로는 **같은 이름으로 합치면 틀리는 원천의 경계**를 확인하는 학습입니다. 실습은 [따라 하기와 실행 근거](cross-domain/reproducible-labs.md)에서 선택합니다. kubelet 자원 압박·새 PDH 조회·cloud 호출처럼 실행하지 않은 항목은 원천 검토 범위입니다.

| 출발 상황 | 읽을 장 | 스스로 확인할 것 |
| --- | --- | --- |
| NIC는 정상인데 연결을 놓침 | [Linux 스택 카운터](network/linux-stack-counters.md) | namespace·소켓 범위, 재전송 비율과 손실률의 차이 |
| Pod 종료·사용률 급변 | [자원 압박과 종료](kubernetes/pressure-and-termination.md) → [수집](kubernetes/collection.md) | OOM/eviction 증거, resize의 실제 분모, 수집 endpoint |
| DB 정리가 안 되거나 업그레이드 후 지표 누락 | [PostgreSQL 운영 관측](database/postgresql-operations.md) | ID 나이·회수 기준점·통계 view 버전·권한 |
| 지표에서 trace로 이동하거나 첫 counter 해석 | [exemplar와 시작 시각](foundations/metric-context-and-start-time.md) → [sampling](application/trace-sampling-and-context.md) | 사건 연결과 모집단 추정은 어떻게 다른가 |
| 계측기 교체 뒤 이름·단위가 변함 | [Semantic conventions](application/semantic-conventions.md) | Stable 상태, s/ms, 현재값/마지막 GC, 누적/분포 |
| 화면과 알림이 늦거나 다르게 보임 | [cloud 시간 축](cloud/provider-metrics.md) → [알림 지연](product/alerts-and-incidents.md) | 측정·게시·평가·발송의 각 시간 |

Kafka broker·share group은 [Kafka](middleware/kafka.md), Windows의 PDH와 CPU 표시는 [Windows](host/windows.md), 저장 완료는 [쓰기 경로](storage/write-path-and-durability.md), 프로토콜의 세부 경계는 [TLS·HTTP](network/tls-http.md)와 [SNMP](network/snmp-and-device-models.md)를 찾아봅니다.

## 원천을 구분하는 세 번째 읽기

회수·잠금·저장 형식·시계·런타임 내부를 더 깊게 살펴보는 경로입니다. 기본 개념을 익힌 뒤 필요한 주제부터 읽고, 각 장의 실습 여부를 확인합니다.

| 질문 | 읽을 순서 | 이해 확인 |
| --- | --- | --- |
| 메모리는 비슷한데 왜 느려지고 죽는가 | [회수와 OOM](host/reclaim-and-oom.md) → [PSI](host/numa-and-pressure.md) → [프로세스](host/processes.md) | 사용량·회수 페이지·대기 시간·종료 사건을 구분하는가? |
| 없는 키를 넣는데 왜 기다리는가 | [MySQL 운영](database/mysql-operations.md) | gap lock과 deadlock, timeout의 롤백 범위를 설명하는가? |
| 커밋과 복제 완료는 같은가 | [MySQL 운영](database/mysql-operations.md) → [SQL Server·Oracle](database/sqlserver-oracle.md) | 수신·적용·redo·저장 설정, NULL·0의 차이를 보존하는가? |
| histogram 형식을 바꿔도 p99는 같은가 | [분포](foundations/distributions.md) → [분포 저장 형식](foundations/histogram-storage.md) | 경계·scale·보간·상대 오차를 구분하는가? |
| 로그 시각을 신뢰할 수 있는가 | [시계 동기화](foundations/time-and-data-quality.md) | offset·frequency·불확실성·smear와 MONOTONIC/RAW를 구분하는가? |
| 런타임·GPU 내부에서 무엇이 막히는가 | [JMX·JFR·EventPipe](application/managed-runtimes.md) → [Node ELU](application/async-runtimes.md) → [GPU](host/gpu.md) | pool·이벤트·루프·SM·메모리의 관측 범위를 구분하는가? |
| 로그가 없다는 것은 오류가 없다는 뜻인가 | [로그 전달](product/collection-pipelines.md) → [HAProxy](middleware/proxies-and-mesh.md) | record·chunk·세션·요청·응답 코드의 단위를 보존하는가? |

## 개념을 배운 뒤 실제 결과와 연결하기

| 읽은 개념 | 다음에 읽을 실습·해설 | 집중할 질문 |
| --- | --- | --- |
| CPU·메모리·I/O | [Linux 실습](host/linux-observation-lab.md) → [측정과 비교](foundations/measurement-and-comparability.md) | 숫자의 차이가 오류인가, 다른 계정인가, 아직 모르는가? |
| transaction·잠금 | [PostgreSQL 실습](database/postgresql-concurrency-lab.md) | 같은 연결에서 오류 이후 무엇이 달라지는가? |
| API 객체·watch | [인벤토리 실습](kubernetes/inventory-consistency.md) | 대상이 실제로 삭제됐는가, 수집 범위에서 빠졌는가? |
| trace·sampling·전송 | [sampling 해설](application/trace-sampling-and-context.md) → [Collector 실습](product/telemetry-delivery-contracts.md) | 보이지 않는 자료가 선택되지 않은 것인가, 거절된 것인가? |
| 요청·연결 풀 | [HTTP/1.1 실습](network/dns-and-connection-lifecycle.md) | 성공 상태 코드와 응답 본문 완료가 같은가? |
| 제품의 저장·집계 | [cloud 재조회](cloud/late-data-and-reconciliation.md) → [필드 수용 기준](product/compatibility-and-acceptance.md) | 같은 자료를 다시 받았을 때 더할 것인가, 대체할 것인가? |

실습 프로그램을 실행하지 않아도 본문의 표와 [해설이 있는 분석 연습](cross-domain/investigation-workbook.md)으로 학습할 수 있습니다. 실행하려면 각 장의 환경 조건을 따릅니다.

## 문장의 종류

| 표시 | 읽는 방법 |
| --- | --- |
| 공식 출처·적용 버전 | 그 범위의 정의와 동작 |
| 가상 예시 | 학습을 위한 입력과 상황; 실제 성능 수치 아님 |
| 실제 실행·실습 | 기록한 버전과 설정에서 얻은 결과 |
| 제품 적용 제안 | 사용자의 현재 구현을 확인한 사실이 아닌 설계 제안 |
| 가설·가능성 | 더 확인할 설명 후보 |
| 실행 미검증 | 공식 설명은 있지만 이 환경에서 실행하지 않은 예제 |

장의 `검토됨`을 모든 환경의 실행 인증으로 읽지 않습니다. [검토 기록](review.md)과 [검증 기록](validation.md)에 범위를 분리했습니다.

## 끝까지 유지할 질문

어떤 수치에도 **누구의 값인지, 어디서 쟀는지, 단위와 분모가 무엇인지, 어느 시간의 값인지, 어떻게 집계했는지, 수집이 성공했는지**를 묻습니다. 이 질문들을 설명할 수 있으면 기술 이름이 바뀌어도 원천을 읽고 새 도메인을 제품에 연결할 출발점을 갖게 됩니다.

다음: [제1.2판의 범위와 사실 확인 원칙](scope.md)
