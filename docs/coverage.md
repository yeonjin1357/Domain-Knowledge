# 제1.2판의 분야별 범위

판 기준일은 **2026-10-06**이며, 교차 검토를 반영한 제1.2판은 **12개 분야, 상세 본문 100장**입니다. 표는 읽을 수 있는 본문의 범위이며 사용자 제품의 지원 여부를 뜻하지 않습니다.

| 분야 | 상세 장 | 이번 판에서 다루는 내용 |
| --- | ---: | --- |
| [공통 관측](foundations/README.md) | 11 | 시스템 지도, 시계열·단위·분포·SLO·시간·trace·sampling, 성능 실험, 분산 시스템 |
| [호스트](host/README.md) | 11 | Linux CPU·메모리·블록 I/O·프로세스, Windows API, VM·GPU, NUMA·압력·원천 필드 |
| [네트워크](network/README.md) | 9 | IP·DNS·TCP·UDP·QUIC·TLS·HTTP, 링크·MTU·BGP, SNMP·OSPF·EVPN·QoS |
| [스토리지](storage/README.md) | 4 | 블록·파일·객체, 처리량·IOPS·지속성, 복제·snapshot·복구, RAID·LVM·SAN·NAS |
| [컨테이너](containers/README.md) | 5 | namespace·OCI 수명·image·COW·volume, cgroup v1/v2, Windows 격리 차이 |
| [Kubernetes](kubernetes/README.md) | 10 | API·Pod·request/limit·HPA·수집·Service·PV/PVC·workload·etcd, CNI·CSI·CRD·Operator |
| [앱](application/README.md) | 9 | 요청·queue·pool·deadline·retry, JVM·.NET·Go·Node.js·Python, RUM·계측·프로파일 |
| [DB](database/README.md) | 13 | transaction·MVCC·lock·index·plan·WAL·HA, 주요 엔진·분산·분석·시계열·그래프, 수집 SQL |
| [미들웨어](middleware/README.md) | 6 | Redis·Memcached·Kafka·RabbitMQ·Pulsar·검색·프록시·mesh, Flink·Spark 처리 경계 |
| [클라우드](cloud/README.md) | 6 | AWS·Azure·Google Cloud 식별·API·기간 집계, 관리형·서버리스·VPC, quota·비용 |
| [도메인 간 분석](cross-domain/README.md) | 7 | 지연·자원·적체·관측 중단 사례, 실제 로컬 실습, 종합 연습과 해설 |
| [제품 설계](product/README.md) | 9 | 정체성·관계·수집·저장·질의·알림·tenant 접근·자체 관측, adapter 계약·용량 |

제1.1판에서 추가했던 12개 장은 [측정과 비교](foundations/measurement-and-comparability.md), [Linux 실습](host/linux-observation-lab.md), [연결 수명](network/dns-and-connection-lifecycle.md), [쓰기 지속성](storage/write-path-and-durability.md), [메모리 계정](containers/memory-accounting-and-oom.md), [인벤토리](kubernetes/inventory-consistency.md), [sampling](application/trace-sampling-and-context.md), [PostgreSQL 실습](database/postgresql-concurrency-lab.md), [cloud 재조회](cloud/late-data-and-reconciliation.md), [분석 연습](cross-domain/investigation-workbook.md), [전송 계약](product/telemetry-delivery-contracts.md), [필드 수용 기준](product/compatibility-and-acceptance.md)입니다.

제1.2판은 그 92장에 운영·수집 주제 **8장**을 더했습니다. [새 장과 변경 요약](review.md#제12판에서-달라진-내용)에 분야별 질문을 정리했고, 아래에는 주제별 범위와 실습 조건을 정리합니다. 상세 이력은 검토·검증 기록에 있습니다.

[필드 카탈로그](../catalog/field-catalog.json)는 87개 핵심 필드의 검토 범위를 기계 판독 형식으로 제공합니다. 전수 지원 목록이 아니며 버전 범위·미지원·NULL 의미와 [실측/가상 계약의 차이](product/adapter-contracts.md)를 함께 읽습니다. 학습용 정본·탐색 정리는 장 수를 바꾸지 않았습니다.

## 2026-10-05 원고 보강의 범위

제1.2판에서는 네트워크 스택, Kubernetes 압박, PostgreSQL 운영, 지표 문맥과 semantic conventions를 보강했습니다. 2026-10-05 실행한 Kubernetes·Collector·promtool·PostgreSQL의 36개 조건은 지지 34개·반증 2개입니다. 반증은 cache-on의 과거 Exact LIST가 compaction 뒤에도 200을 반환한 관측이며, 원시 판정을 보존했습니다. [실습 조건](cross-domain/reproducible-labs.md), [상세 검증 기록](validation.md)

| 요청 주제 | 읽을 본문 | 포함한 경계 |
| --- | --- | --- |
| Linux 네트워크 스택 | [새 장](network/linux-stack-counters.md) | namespace·TCP/UDP·TcpExt·ss·재전송 비율 |
| Kubernetes 자원·수집 | [새 장](kubernetes/pressure-and-termination.md), [수집](kubernetes/collection.md) | QoS·eviction·OOM·resize·PSI·v1 상태·WatchList |
| PostgreSQL 운영 | [새 장](database/postgresql-operations.md) | XID/MultiXact·horizon·권한·통계 일관성·12–18 분기 |
| 관측 데이터 문맥 | [새 장](foundations/metric-context-and-start-time.md), [sampling](application/trace-sampling-and-context.md) | exemplar·start time·created·th/rv·추정 조건 |
| OTel 이름 | [새 장](application/semantic-conventions.md) | SemConv 1.44.0의 명시한 Stable 항목, JVM/.NET 차이 |
| broker·Windows | [Kafka](middleware/kafka.md), [Windows](host/windows.md) | ISR·controller·share group, PDH 실명·빌드별 표시 |
| 시간과 알림 | [cloud 지표](cloud/provider-metrics.md), [Lambda](cloud/managed-and-serverless.md), [flow log](cloud/networking.md), [알림](product/alerts-and-incidents.md) | 보존·sampling·게시·귀속 시각·평가·발송 |
| 저장 경로 | [쓰기](storage/write-path-and-durability.md), [Ceph](storage/capacity-and-protection.md), [multipath](storage/raid-lvm-and-paths.md) | FLUSH/FUA·O_DIRECT·fsync 실패·min_size·경로 부재 |
| 프로토콜 | [HTTP/TLS](network/tls-http.md), [SNMP](network/snmp-and-device-models.md), [MTU](network/layers-and-routing.md) | framing·RTT·인증서 기간·Counter64·PMTUD |

Kubernetes 후속 API 실습은 공식 envtest가 제공되는 **1.34.1·1.37.0**을 선택했습니다. 각 minor의 최신 patch 실행이 아닙니다(2026-10-05 검토 시 최신 **1.34.12·1.37.1**). watch cache true/false의 minor 규약 비교이며 결과는 [인벤토리 본문](kubernetes/inventory-consistency.md)에 반영했습니다. 특정 feature gate의 인과나 최신 patch의 회귀 검증으로 확장하지 않습니다. [전용 자산 pin](../labs/review-r2/kubernetes-assets.json), [공식 patch 일정](https://kubernetes.io/releases/patch-releases/)

## 메모리·DB·분포 저장의 보강 범위

회수·OOM, MySQL 운영, 분포 저장의 세 장과 기존 원고를 보강했습니다. 메모리·분포·시계와 MySQL 두 버전의 최종 채택 실행은 17개 지지 조건입니다. MySQL의 관측 전제를 보완하기 전 반증 이력도 별도로 보존합니다. 결과 수치는 명시한 환경·입력에만 적용하며 상용 DB·GPU의 실측을 뜻하지 않습니다. [실습·원자료](cross-domain/reproducible-labs.md), [주제별 검토 이력](../review/claude-codex-r3.md), [검증 집계](validation.md)

| 주제 | 원고 | 보존한 해석 경계 |
| --- | --- | --- |
| 회수·OOM | [새 장](host/reclaim-and-oom.md) | 페이지·사건·시간, 전역/memcg OOM·eviction 증거 |
| PSI·프로세스 | [PSI](host/numa-and-pressure.md), [프로세스](host/processes.md) | 기능 가용성·trigger, RSS 정밀도·상세 조회 비용·I 상태 |
| MySQL | [새 장](database/mysql-operations.md) | 8.4·9.7 잠금·지속성 설정·복제 timestamp·NULL/0 |
| 분포 저장 | [새 장](foundations/histogram-storage.md) | OTel scale·Prometheus schema·보간·DDSketch·t-digest |
| 시계 | [시간 품질](foundations/time-and-data-quality.md) | offset·frequency·smear·PHC/시스템 시계 |
| 상용 DB | [SQL Server·Oracle](database/sqlserver-oracle.md) | ADR·version store·AG KB, 권한과 Diagnostics Pack 허용 범위 |
| 런타임 | [JVM/.NET](application/managed-runtimes.md), [Node](application/async-runtimes.md) | JMX pool·JFR 비용·EventPipe와 collect-linux preview·ELU·Node 26.5+/24.19+ 표본 모드 |
| 전송 | [로그](product/collection-pipelines.md), [HAProxy](middleware/proxies-and-mesh.md) | record/chunk, retry/drop·frontend/backend/server의 범위 |
| GPU | [GPU](host/gpu.md) | activity·occupancy·tensor·DRAM·Xid·ECC·clock reason |

이전에 미확인이었던 항목 중 Kubernetes 1.37 hugepage 보정은 Summary API의 node.memory.availableBytes에도 반영되는 것을 코드로 확인했습니다. Lambda suppressed init의 CloudWatch Duration 포함 여부는 명시적 공식 근거를 찾지 못해 미확인을 유지합니다. 런타임·GPU·상용 DB를 실제 환경에서 실행 검증한 것으로 표시하지 않습니다.

## 대표 적용 범위

| 원천 | 이 책에서의 적용 |
| --- | --- |
| PostgreSQL 18, MySQL 8.4·9.7, Oracle 19c | 해당 버전의 동작·통계·단위 설명; MySQL 초기 두 preflight는 blocked, 8.4.11·9.7.2의 잠금·교착·설정·복제의 최초·보완 실행, 보완 실행은 각 supported 5. 최초 반증도 보존 |
| SQL Server, MariaDB, MongoDB, Cassandra, DynamoDB, ClickHouse | 장에 표시한 공식 원천과 구체적인 사례의 범위 |
| JDK 25, CPython 3.14, .NET·Go·Node.js 문서 | runtime 메모리·실행·관측 의미; 모든 배포 옵션 인증 아님 |
| Linux 6.12·6.13·6.15·6.18 코드, cgroup·procfs | 회수·swap·proactive 항목의 버전·모집단 차이, 차분·계층 처리 |
| OCI 1.2.1, CNI 1.1.0, CSI 1.11.0 | 명세의 경계와 capability; 제품 plugin 버전과 구분 |
| etcd 3.6, Kafka 4.3, RabbitMQ 4.3, Flink 1.20, Pulsar 4.0 | 해당 장의 적용 버전; 최신·유일 지원 버전 주장 아님 |
| Kubernetes 1.35 이상과 이전 버전 | 비교 규약을 구분; API server 1.34.1·1.37.0에서 cache true/false 실행, workload 실행은 제외 |
| PostgreSQL 18.6 | 기존 동시성·권한·수집 SQL 11개와 prepared transaction·slot·standby 회수 기준점 4개 시나리오 실행 |
| Linux 6.18.33.2·Python 3.12.3 | WSL2의 자기 프로세스·기존 cgroup·HTTP/1.1에 RSS/PSS·조회 비용·PSI/vmstat·시계 상태 관측 추가; 강제 OOM 없음 |
| OTLP 1.11.0·Collector 0.137.0·0.162.0 | HTTP JSON 전송과 0.162.0 내부 로그·지표·메모리 queue 경계; gRPC·영속 큐 검증은 제외 |
| Windows·SQLite 3.45.1·promtool 3.5.0·3.13.4·3.15.0 | 실제 실행 결과는 로컬 실습의 기록 범위; 새 promtool 두 버전은 기존 규칙과 classic/native histogram의 합성 분포 평가 |
| chrony 4.9·Node 26.10.0/24.19.0·Fluent Bit 5.1.3·HAProxy 3.2 | 2026-10-06 확인한 원천 범위; 해당 런타임·수집기 실행 검증은 별도 |
| 버전을 고정하지 않은 공식 웹 문서 | 확인 날짜 기준; 구현 시 실제 버전과 대조 |

개별 장의 범위가 이 요약보다 우선합니다. 다른 버전과 이름이 같더라도 필드·설정·수명·권한을 확인합니다.

## 교차 검토 시점의 버전 상태

릴리스·지원 상태 확인일은 **2026-10-04**이며 Kubernetes patch 선택은 10월 5일에도 확인했습니다. MySQL 일반 릴리스 쌍과 보강 원고의 chrony·Node·Fluent Bit 기준은 **10월 6일** 추가 확인했습니다. 실행 열에는 각 기록의 후속 실행 결과를 구분해 적었습니다. MySQL 보완 실행의 실행일은 10월 6일 KST이며 원문 시각은 10월 5일 UTC입니다. “고정”은 문서·실습을 해석할 기준이며 현재 권장 설치 버전을 뜻하지 않습니다. 최신 릴리스 확인과 실제 재실행은 별개입니다. 종료일이 확인되지 않은 항목은 임의로 날짜를 만들지 않았습니다.

| 대상 | 책의 고정 기준 | 검토 시점 현재 | 지원·종료와 해석 |
| --- | --- | --- | --- |
| Kubernetes | 기존 1.34.1 cache 비활성화 기록 보존; 새 1.34.1·1.37.0 각각 cache true/false | 최신 1.37.1, 최신 3개 브랜치 1.35–1.37; 1.34 계열 패치 1.34.12 | 실행 버전은 최신 patch가 아님. 1.34는 2026-10-27 종료 전 유지보수 중. 최신 3개에서 제외됐다고 이미 지원 종료된 것은 아님. [릴리스](https://kubernetes.io/releases/), [일정](https://kubernetes.io/releases/patch-releases/) |
| etcd | 기존 3.6.4 보존; 새 envtest에 포함된 3.6.4·3.7.0 전용 인스턴스 | 최신 릴리스 3.7.2 | 최신 patch 3.7.2는 실행하지 않음. 이 검토에서는 3.6 계열의 종료일을 확정하지 않음. [릴리스](https://github.com/etcd-io/etcd/releases/tag/v3.7.2) |
| OTel Collector | 기존 0.137.0 보존; 새 0.162.0 HTTP JSON·내부 로그/지표·queue 경계 실행 | 0.162.0; core 9월 28일, 배포판 9월 29일 UTC 게시 | 새 실행은 검토 시점 현재 버전. 해당 태그의 정해진 LTS 종료일은 확인하지 못함. [core](https://github.com/open-telemetry/opentelemetry-collector/releases/tag/v0.162.0), [배포판](https://github.com/open-telemetry/opentelemetry-collector-releases/releases/tag/v0.162.0) |
| Prometheus/promtool | 기존 3.5.0 보존; 새 3.13.4·3.15.0에서 규칙·테스트와 합성 native histogram 평가 | 최신 3.15.0, 현재 LTS 3.13.4 | 3.5 LTS는 2026-07-31 종료. 3.13 LTS 종료 예정일 2027-07-31. 새 실행은 서버 수집·WAL·exemplar 실험을 포함하지 않음. [다운로드](https://prometheus.io/download/), [지원 주기](https://prometheus.io/docs/introduction/release-cycle/) |
| MySQL | 8.4·9.7 문서. 8.4.10·9.7.2 초기 preflight blocked; 8.4.11·9.7.2 보완 실행 각 supported 5; 최초 실행 각 supported 3·refuted 2도 보존. 복제 worker 수는 명시적으로 2 | 최신 LTS 계열 9.7. 일반 릴리스 8.4.11·9.7.2는 2026-07-28 쌍; 8.4.12·9.7.3은 Docker image 전용 | 새 LTS 등장만으로 8.4 지원 종료를 의미하지 않음. LTS는 Oracle 정책의 premier 5년·extended 3년 구분을 따르며 계약·배포판의 적용 조건 확인 필요. [정책](https://dev.mysql.com/doc/refman/9.7/en/mysql-releases.html), [8.4.11](https://dev.mysql.com/doc/relnotes/mysql/8.4/en/news-8-4-11.html), [8.4.12 범위](https://dev.mysql.com/doc/relnotes/mysql/8.4/en/news-8-4-12.html), [9.7.2](https://dev.mysql.com/doc/relnotes/mysql/9.7/en/news-9-7-2.html), [9.7.3 범위](https://dev.mysql.com/doc/relnotes/mysql/9.7/en/news-9-7-3.html) |
| Ceph | Squid 문서 | Tentacle 20.2.4, Squid 19.2.6 | 공식 표는 Squid 2026-10-31을 **예상** 종료일로 표시. Tentacle의 예상일은 2027-06-01. [릴리스 표](https://docs.ceph.com/en/latest/releases/) |
| cAdvisor | 0.52.1 코드 | Kubernetes 1.37.1 의존성은 lib 0.60.5 | 해당 의존성의 working set 식을 코드 대조. cAdvisor 전체 최신 릴리스·고정 버전 종료일을 이 정보만으로 판정하지 않음. [의존성](https://github.com/kubernetes/kubernetes/blob/v1.37.1/go.mod), [계산 코드](https://github.com/google/cadvisor/blob/lib/v0.60.5/lib/container/libcontainer/handler.go) |
| OCI runtime spec | 1.2.1 | 1.3.0 | 명세 판본이며 런타임 제품의 지원 종료일과 다름. [릴리스](https://github.com/opencontainers/runtime-spec/releases/tag/v1.3.0) |
| CSI spec | 1.11.0 | 1.13.0 | 명세 판본이며 driver의 지원·capability는 별도 확인. [릴리스](https://github.com/container-storage-interface/spec/releases/tag/v1.13.0) |
| Flink | 1.20 문서 | 최신 안정 2.3.0, 1.20 LTS 패치 1.20.5 | 1.20을 단순히 지원 종료로 표시하지 않음. 종료일은 이 검토에서 확정하지 않음. [공식 다운로드](https://flink.apache.org/downloads/) |
| Tomcat | 10.1 connector 문서 | 10.1.60·11.0.26 지원 계열; Spring Boot 4의 내장 Tomcat은 11.0.x | Tomcat 10.1 지원과 Spring Boot의 기본 의존성은 다른 기준. [Tomcat 지원 표](https://tomcat.apache.org/whichversion.html), [Spring Boot 요구 사항](https://docs.spring.io/spring-boot/system-requirements.html) |
| PostgreSQL | 18 규약·18.6 실제 실험 | 18.6 | 18 계열 지원 종료 예정일 2030-11-14. [정책](https://www.postgresql.org/support/versioning/) |
| OTLP 원천 저장소 | 1.11.0 문서 | 원천 릴리스 1.11.1, 2026-09-29 게시; 공식 웹 문서 표시는 1.11.0 | 웹 문서의 판 표시와 원천 저장소의 최신 태그를 구분. 고정 규약의 전체 재검증이나 Collector의 지원 범위를 대신하지 않음. [릴리스](https://github.com/open-telemetry/opentelemetry-proto/releases/tag/v1.11.1), [웹 규약](https://opentelemetry.io/docs/specs/otlp/) |

Linux 커널·WSL 배포판, Python·SQLite·브라우저·문서 renderer 버전은 [검증 기록](validation.md)의 실행 환경 식별자입니다. 이 표의 소프트웨어 릴리스와 동일한 지원 체계로 취급하지 않으며, 제1.2판 보강에서 그 환경을 최신 버전으로 교체하지 않았습니다. 새 실습의 관측과 한계는 [API·전송·DB 검토 기록](../review/claude-codex-r2.md)와 [메모리·MySQL 검토 기록](../review/claude-codex-r3.md)에 있습니다.

## 이 판을 사용하는 경계

학습과 설계에 필요한 주요 원리를 상세히 연결했습니다. 장비 모델별 MIB·센서 전수, 모든 DB view의 전체 컬럼, 모든 cloud 서비스의 가격·quota, 모든 Unix·하이퍼바이저의 counter 전수는 포함하지 않습니다. 그러한 항목은 해당 대상의 어댑터 명세로 별도 구체화해야 합니다.

실제 실행 증거가 있는 범위는 [실습](cross-domain/reproducible-labs.md)과 [검증 기록](validation.md)에 한정합니다. 본문에 기술을 설명했다는 이유로 해당 제품을 설치하거나 운영 장애를 재현한 것으로 해석하지 않습니다.

## 함께 읽는 부록

[학습 안내](reading-guide.md) · [용어집](glossary.md) · [지표 참조표](metric-catalog.md) · [검토 기록](review.md) · [통합본](../BOOK.md)

이전: [단위와 대표 지표의 해석 참조표](metric-catalog.md) · 다음: [제1.2판 검증 기록](validation.md)
