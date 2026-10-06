# 제1.2판의 검토와 수정 기록

제1.2판의 기준일은 **2026-10-06**입니다. 제1.1판의 **92장에 8장을 더해 100장**으로 확장하고 Claude–Codex 교차 검토 세 라운드의 정정·실행 근거를 반영했습니다. 두 AI의 교차 검토와 명시된 로컬 환경의 실행이며 **외부 전문가 감수나 모든 운영 환경의 지원 인증은 아닙니다.** 발행 검사는 [검증 기록](validation.md)에 있습니다.

## 제1.2판에서 달라진 내용

### 새로 추가한 8장

| 장 | 독자가 배울 내용 | 추가 라운드 |
| --- | --- | --- |
| [Linux 네트워크 스택 카운터](network/linux-stack-counters.md) | TCP·UDP·namespace 범위, 재전송 비율과 원천 필드의 한계 | 2 |
| [Kubernetes 자원 압박과 종료](kubernetes/pressure-and-termination.md) | QoS·eviction·OOM 증거와 실제 자원 한도의 변화 | 2 |
| [PostgreSQL 운영 관측](database/postgresql-operations.md) | 오래된 XID·회수 기준점·권한·버전별 통계 view | 2 |
| [지표 문맥과 카운터 시작 시각](foundations/metric-context-and-start-time.md) | exemplar의 trace 연결, 시작 시각과 첫 증가분 | 2 |
| [OpenTelemetry 이름·단위·안정성](application/semantic-conventions.md) | HTTP·JVM·.NET 지표 이름을 적용 버전과 함께 해석 | 2 |
| [메모리 회수와 OOM](host/reclaim-and-oom.md) | 회수·swap·OOM 원천의 모집단과 종료 증거 | 3 |
| [MySQL 잠금·커밋·복제](database/mysql-operations.md) | gap/next-key 잠금, 지속성 설정, GTID와 복제 표시의 완료 시점 | 3 |
| [분포 저장 형식](foundations/histogram-storage.md) | exponential/native histogram·sketch의 해상도·병합·보간 | 3 |

기존 장에도 PSI·프로세스 메모리·시계 동기화·SQL Server·Oracle·런타임·로그 손실·HAProxy·GPU를 보강했습니다. 새 장은 쉬운 상황 설명에서 시작해 원천 정의, 단위·계산, 해석 함정, 제품 적용 제안, 이해 확인으로 이어집니다.

### 세 라운드의 주요 정정

| 라운드 | 바로잡거나 범위를 명확히 한 내용 | 상세 판단·원천 |
| --- | --- | --- |
| 1 | CPU 계정과 MONOTONIC 분모를 구분하고 RAW·adjtimex 관측을 추가. diskstats wrap, StatefulSet 순서, DB 회수 기준점, DNS 응답 귀속 등을 정정. Kubernetes 비교 규약과 고정 실습 버전의 상태를 분리 | [1라운드 기록](../review/claude-codex-r1.md) |
| 2 | Collector의 재시도 중/소진 뒤 실패 계수와 queue 응답 경계를 실측. cache-on Kubernetes의 과거 Exact LIST 200을 반증으로 보존. PostgreSQL 12→13 실행 시간 매핑, Linux TCP·Kubernetes QoS/종료·지표 문맥의 버전 경계를 정정 | [2라운드 기록](../review/claude-codex-r2.md) |
| 3 | Linux 회수 계수의 모집단, zswap/zram 계정, OOM 작업·희생자를 구분. native histogram 안정화·변환 규약과 런타임·로그 지표의 도입 범위를 보완. MySQL sys 가시성과 GTID/coordinator/SBS 완료를 혼동한 실습 조건을 고치고 r2로 재확인 | [3라운드 기록](../review/claude-codex-r3.md) |

### 새로 보존한 실습과 판정

| 라운드 | 출판 묶음 | 원래 기록의 판정 | 무엇을 확인했는가 |
| --- | ---: | --- | --- |
| 1 | 1 | passed 3·observed 2 | [Linux 재관측](../labs/results/1.1-linux-clock-r1.json): 파싱·메모리·I/O 검사와 CPU/cgroup 관측. CPU 4구간·idle 61표본을 포함하며 외부 시간 교정 인증은 아님 |
| 2 | 4 | supported 34·refuted 2, 합계 36 | Kubernetes cache 두 구성·두 버전, Collector 내부 관측, PostgreSQL 회수 기준점, promtool 규칙 재평가 |
| 3 | 7 | supported 23·refuted 4, 합계 27 | 메모리·분포·시계와 MySQL 두 버전의 r1·r2. gzip 원자료 525개 보존 |

서로 다른 실행기의 판정 형식과 반복 실행을 구분합니다. 3라운드의 최종 채택 실행은 메모리·분포·시계·MySQL r2의 17개 supported 조건이며, 표의 27에는 설계 전제를 반증한 MySQL r1도 포함합니다. 이를 모두 독립적인 제품 기능 시험으로 합산하지 않습니다. 결과와 입력 hash는 [provenance](../review/evidence-provenance.json), 실행 조건은 [실습 해설](cross-domain/reproducible-labs.md)에 연결했습니다.

제1.1판에서 실행한 5묶음·31개 시나리오, `1.1-*` 결과 파일 이름, 실행 당시 verdict·버전·시각·hash는 그대로입니다. 이번 발행은 원고와 현재 판 안내를 1.2로 올리는 작업이며 새 Linux/DB 실습을 수행한 것이 아닙니다.

### 남은 미확인과 실행 범위

- Lambda suppressed init의 REPORT 설명을 CloudWatch Duration 포함 여부로 확장할 직접적인 공식 문장은 확인하지 못했습니다.
- WSL tick 설정 주체·RAW의 외부 정확도, MySQL r1의 내부 clock_diff와 SBS 13의 정확한 산술 원인은 미확인입니다. 최초 CPU 1.06 표본의 원인도 기록에 없던 RAW·tick으로 소급 확정하지 않습니다.
- Kubernetes cache-on의 Exact LIST 200은 관측했지만 특정 feature gate를 분리 변경하지 않아 그 기능의 인과까지 확정하지 않았습니다.

운영 클러스터·cloud 계정·상용 장비·전원 장애와 모든 버전 조합을 실행하지 않았습니다. 판 기준일 변경을 모든 원천의 재확인 날짜로 사용하지 않으며, 각 장의 확인일·고정 버전과 [범위 원칙](scope.md)을 따릅니다. 아래에는 판 번호를 유지하며 작업했던 교차 검토와 제1.1판의 작성 이력을 보존합니다.

## Claude–Codex 교차 검토 3차: 원고 보강과 3f 결과 확정

2026-10-05의 3b에서는 [회수·OOM](host/reclaim-and-oom.md), [MySQL 운영](database/mysql-operations.md), [분포 저장 형식](foundations/histogram-storage.md)을 새 장으로 추가해 상세 **100장**으로 확장했습니다. 기존 장에 PSI·프로세스 RSS·시계 동기화·SQL Server와 Oracle·런타임·로그와 HAProxy·GPU 원천을 보강했습니다. 10월 6일 3d에서는 Claude의 3c 지적 24개와 추가 단서를 원천에 다시 대조하고 실습 세 묶음을 출판했습니다. AI 간 교차 검토이며 모든 문장의 무오류 인증은 아닙니다. [항목별 판정과 근거](../review/claude-codex-r3.md)

Kubernetes v1.37.0 코드에서 hugepage 보정이 Summary API의 node.memory.availableBytes에도 적용되는 것을 확인했습니다. Lambda suppressed init이 CloudWatch Duration 지표에도 포함되는지는 직접적인 공식 문장을 확인하지 못해 미확인을 유지했습니다.

3d에서는 Linux reclaim counter의 서로 다른 모집단, zswap과 zram의 계정 차이, OOM 유발 작업·희생자의 score 구분을 명확히 했습니다. MySQL 1213의 탐색 한계와 table lock 감지 조건, SQL Server 최소 권한·redo_rate 기간, Oracle의 실제 pack 대상 목록, native histogram 안정화 단계와 변환 규약의 Development 상태도 보강했습니다. Fluent Bit의 memrb drop·files_rotated 지표는 4.1.0 코드에도 있어 “4.2 최초 추가”라는 단서를 채택하지 않았습니다.

메모리·histogram·시계 실습은 supported 4·2·1개의 요약 JSON과 **gzip 원자료 61개 전체**를 보존했습니다. 8 MiB 메모리 분류와 조회 비용, 보간 차이, MONO/RAW와 동기화 metadata를 제한된 관측으로 연결했습니다. MySQL의 두 최초 실행은 loader 실패로 DB 관측이 없었으므로 출판하지 않았습니다. 서명을 확인한 8.4.11·기존 9.7.2와 비공개 라이브러리의 후속 실행을 3e에서 출판했습니다. r1은 각 supported 3·refuted 2, gzip 100개로 보존하고, 3f에서 r2의 각 supported 5·gzip 132개를 추가했습니다. 반복 실행 이력을 포함한 3라운드 누계는 27개 판정(supported 23·refuted 4)·525개 gzip입니다. [실습 근거·한계](cross-domain/reproducible-labs.md), [검증 기록](validation.md)

3e에서는 next-key의 직접 대기 관계가 있었음에도 sys view가 비어 있던 표본을 INNODB_TRX cache·join 경로와 대조했습니다. GTID 적용 완료를 이미 기다린 복제에서도 coordinator 위치가 뒤처져 SBS가 0이 아닐 수 있음을 원자료·소스로 확인했습니다. 9.7.2의 재개 SBS는 0이 아닌 1입니다. 두 refuted를 성공으로 바꾸지 않았으며, 보완한 관측 조건을 Claude가 r2로 실행한 결과를 3f에서 확정했습니다. 두 버전 모두 sys 행은 재조회 뒤 나타났고, 위치 일치 뒤의 SBS와 SQL 중지 상태는 정의에 부합했습니다. GTID 직후와 위치 수렴 뒤 표본을 함께 남겨 실제 작업과 표시 갱신의 완료 시점 차이를 설명했습니다. 시계 보정 내부값과 WSL 시계 조정의 인과는 이번 기록만으로 확정하지 않았습니다. [분석 근거](../review/mysql-r3e-analysis.json), [MySQL 본문](database/mysql-operations.md)

## Claude–Codex 교차 검토 2차: 원고 보강과 실행 근거

2026-10-05에는 위 92장에 5장을 추가해 상세 97장으로 보강했습니다. G1–G5 필수 주제와 G6–G12를 공식 문서·명세·버전 소스에 대조했고, 2d에서는 Claude가 전달한 네 최종 실행 결과를 출판했습니다. 주제별 원천·위치·채택하지 않은 단서와 이유, 2c 지적 29개와 추가 단서의 판정은 [2라운드 기록](../review/claude-codex-r2.md)에 있습니다. 그 라운드 당시 과거 1.1 실행 결과·hash와 판 번호·판 기준일을 유지했습니다.

Windows Task Manager의 CPU를 모든 빌드에서 Utility로 단정하지 않고, EC2 basic의 상태 검사 1분 예외, datagram용 RFC 8899의 범위, SNMP RFC 내 650 Mbit/s 경계 표현 차이를 명시했습니다. 새 예시 산술을 기존 검사에 연결했으며 저장 근거 검사와 실제 서버 재실행을 계속 구분합니다.

2c 대조에서는 PostgreSQL 12의 `total_time`이 이미 실행 시간이었다는 오류를 바로잡아 13의 `total_exec_time`과 의미를 연결했습니다. Linux PassiveOpens의 실제 증가 위치, CLOSE-WAIT 수정 포함 여부, UDP MemErrors, Kubernetes Burstable의 하한 3과 Pod-level QoS, OOM의 현재·이전 종료 상태를 보강했습니다. exemplar의 메모리 조회 창과 WAL 보존을 구분하고, Lambda suppressed init의 REPORT 관측을 CloudWatch 지표로 무리하게 확장하지 않았습니다.

새 실행 36개 판정은 지지 34개·반증 2개입니다. Collector 0.162.0에서는 재시도 진행 중 유지되던 send_failed 값이 소진 뒤 증가했고, queue 활성화 시 upstream 수락이 목적지 해제보다 앞섰습니다. PostgreSQL 18.6에서는 네 회수 기준점의 유지·해제를 관측했으며 회수 성공을 freeze 전진으로 해석하지 않았습니다. [실습 원시 결과·한계](cross-domain/reproducible-labs.md)

## Claude–Codex 교차 검토 1차

동일한 제1.1판에 A·B·C 정정을 반영했습니다. [항목별 판정과 직접 확인한 원천](../review/claude-codex-r1.md)에 수용 범위, 다른 수정 방식을 택한 이유, 1b에서 이어 받은 Linux 재실행 근거를 기록했습니다. AI 간 교차 검토이며 외부 전문가 인증은 아닙니다. 판 번호와 기준일, 과거 실행 원시 결과는 유지했습니다. 최신 버전으로 실행하지 않은 항목은 [버전 상태 표](coverage.md#교차-검토-시점의-버전-상태)에서 구분합니다.

## 제1.1판 작성 당시의 기록

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
| Kubernetes resourceVersion | 1.35 이상의 제한된 순서 비교와 1.34 이하·확장 API의 경계를 현재 1.37 문서까지 대조. 같은 클러스터의 API group·resource type, 십진수 형식·임의 정밀도 조건을 구분 |
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

**Linux CPU 계정과 시계:** 최초 표본의 약 1.06은 MONOTONIC 분모를 사용한 관측입니다. 원시 기록과 원래 실행기를 보존하고 현재 실행기에 RAW·읽기 전용 adjtimex·스레드 수·품질 표시를 추가했습니다. Claude가 같은 WSL 환경에서 재실행한 [새 JSON](../labs/results/1.1-linux-clock-r1.json)을 그대로 보존하고 Codex가 실행기 hash와 계산을 확인했습니다. busy 3개 구간의 프로세스 CPU clock/RAW는 약 0.99992–0.99995, MONOTONIC/RAW는 약 0.937이었으며 sleep·idle에서도 시계 속도 차이가 나타났습니다. adjtimex 조정값과도 부합하므로 이 재실행의 CPU/MONOTONIC > 1은 분모 시계의 주파수 조정으로 설명됩니다. 원래 표본에는 RAW·tick이 없어 같은 원인을 소급 확정하지 않으며, 조정 주체와 RAW의 외부 정확도도 확인하지 않았습니다. 기존 두 CPU 계정의 일치 검사는 경과 시간의 정확도를 검증하지 못한다는 정정을 유지합니다. [관측값과 한계](host/linux-observation-lab.md)에 idle 61개 표본의 비율·tick·freq 재계산과 표본 평균의 한계를 함께 적었습니다.

**Kubernetes 과거 버전 조회:** 기존 7개 시나리오는 모두 `--watch-cache=false`였고, 당시 보존하지 않은 “예비 시도 200”은 계속 근거에서 제외합니다. 별도로 보존한 2d의 1.34.1·1.37.0 실행에서는 cache를 켜면 compaction 뒤 Exact RV=1 LIST가 200·빈 목록으로, 끄면 410으로 반환됐습니다. 따라서 compaction만으로 반드시 410을 얻는다는 가설은 두 cache-on 구성에서 반증됐습니다. `ListFromCacheSnapshot` 활성 상태는 기록했지만 gate를 분리 변경하지 않아 인과는 확정하지 않습니다. 빈 RV=1 목록과 새 etcd의 초기 상태가 부합한다는 것은 코드·실행 순서에 근거한 추론입니다. 네 구성의 selector 이탈도 DELETED 뒤 GET 200·동일 UID로 확인했습니다. [새 증거와 해석](kubernetes/inventory-consistency.md)

## 읽기 쉽게 바꾼 부분

새 장은 쉬운 상황 설명 뒤에 원천의 정의를 두고, 실습은 **작업 순서 → 실제 관측값 → 해석 → 추가로 확인할 것**으로 구성했습니다. 해설 연습에서는 실제 고객 장애로 꾸민 숫자를 사용하지 않고 가정과 입력을 먼저 적었습니다. 용어집·지표 참조표·학습 안내에도 새 장의 경로를 연결했습니다.

자동 검사는 원시 결과의 주요 값, 입력 hash, 실행한 SQL과 본문의 일치, 대표 계산을 다시 대조합니다. 자동 통과를 모든 문장의 사실 인증으로 표현하지 않습니다.

## 제1.0판에서 유지한 근거

기존 판의 SQLite·HTTP/1.0·Windows API·promtool 3.5.0 실행 기록, 146개 대표 예시 검사, 22개 어댑터 입력 사례와 28개 계산 검사를 유지했습니다. guest CPU 중복 합산, Windows kernel의 idle 포함, sector 단위, SNMP 불연속, DB 지속성 조건 등의 기존 설명도 유지했습니다. 이번 판에서 바꾸지 않은 모든 출처를 새로 사실 대조했다고 표시하지 않습니다.

## 검토 기록과 개정 기준

[장별 기록](../review/chapter-review.json)은 상세 장의 내용 hash·범위·검토 초점을 보존합니다. [URL 조회 기록](../review/source-status.json)은 주소의 접근 상태이며 사실 대조 기록과 역할이 다릅니다. 기존 장의 출처 확인일과 이번 편집·추가 검토일도 구분합니다.

실제 cloud 계정·상용 SNMP 장비·여러 DB 엔진·Kubernetes workload·분산 HA·전원 장애·OOM은 이번에 실행하지 않았습니다. 새로운 버전의 보장이나 반례, 실제 배포 증거가 생기면 해당 장과 결과를 다시 검토합니다. 제1.1판은 보강된 학습·설계 지식서이며 모든 제조사·모든 버전의 지식을 영구히 망라했다는 선언으로 사용하지 않습니다.
