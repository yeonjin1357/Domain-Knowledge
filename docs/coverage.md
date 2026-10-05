# 제1.1판의 분야별 범위

2026-10-04 기준 **12개 분야, 상세 본문 92장**을 통합했습니다. 표는 읽을 수 있는 본문의 범위이며 사용자 제품의 지원 여부를 뜻하지 않습니다.

| 분야 | 상세 장 | 이번 판에서 다루는 내용 |
| --- | ---: | --- |
| [공통 관측](foundations/README.md) | 9 | 시스템 지도, 시계열·단위·분포·SLO·시간·trace·sampling, 성능 실험, 분산 시스템 |
| [호스트](host/README.md) | 10 | Linux CPU·메모리·블록 I/O·프로세스, Windows API, VM·GPU, NUMA·압력·원천 필드 |
| [네트워크](network/README.md) | 8 | IP·DNS·TCP·UDP·QUIC·TLS·HTTP, 링크·MTU·BGP, SNMP·OSPF·EVPN·QoS |
| [스토리지](storage/README.md) | 4 | 블록·파일·객체, 처리량·IOPS·지속성, 복제·snapshot·복구, RAID·LVM·SAN·NAS |
| [컨테이너](containers/README.md) | 5 | namespace·OCI 수명·image·COW·volume, cgroup v1/v2, Windows 격리 차이 |
| [Kubernetes](kubernetes/README.md) | 9 | API·Pod·request/limit·HPA·수집·Service·PV/PVC·workload·etcd, CNI·CSI·CRD·Operator |
| [앱](application/README.md) | 8 | 요청·queue·pool·deadline·retry, JVM·.NET·Go·Node.js·Python, RUM·계측·프로파일 |
| [DB](database/README.md) | 11 | transaction·MVCC·lock·index·plan·WAL·HA, 주요 엔진·분산·분석·시계열·그래프, 수집 SQL |
| [미들웨어](middleware/README.md) | 6 | Redis·Memcached·Kafka·RabbitMQ·Pulsar·검색·프록시·mesh, Flink·Spark 처리 경계 |
| [클라우드](cloud/README.md) | 6 | AWS·Azure·Google Cloud 식별·API·기간 집계, 관리형·서버리스·VPC, quota·비용 |
| [도메인 간 분석](cross-domain/README.md) | 7 | 지연·자원·적체·관측 중단 사례, 실제 로컬 실습, 종합 연습과 해설 |
| [제품 설계](product/README.md) | 9 | 정체성·관계·수집·저장·질의·알림·tenant 접근·자체 관측, adapter 계약·용량 |

추가한 장은 [측정과 비교](foundations/measurement-and-comparability.md), [Linux 실습](host/linux-observation-lab.md), [연결 수명](network/dns-and-connection-lifecycle.md), [쓰기 지속성](storage/write-path-and-durability.md), [메모리 계정](containers/memory-accounting-and-oom.md), [인벤토리](kubernetes/inventory-consistency.md), [sampling](application/trace-sampling-and-context.md), [PostgreSQL 실습](database/postgresql-concurrency-lab.md), [cloud 재조회](cloud/late-data-and-reconciliation.md), [분석 연습](cross-domain/investigation-workbook.md), [전송 계약](product/telemetry-delivery-contracts.md), [필드 수용 기준](product/compatibility-and-acceptance.md)입니다.

## 대표 적용 범위

| 원천 | 이 책에서의 적용 |
| --- | --- |
| PostgreSQL 18, MySQL 8.4, Oracle 19c | 해당 버전의 동작·통계·단위 설명 |
| SQL Server, MariaDB, MongoDB, Cassandra, DynamoDB, ClickHouse | 장에 표시한 공식 원천과 구체적인 사례의 범위 |
| JDK 25, CPython 3.14, .NET·Go·Node.js 문서 | runtime 메모리·실행·관측 의미; 모든 배포 옵션 인증 아님 |
| Linux 6.12 코드·NUMA 문서, cgroup·procfs | 명시한 원천 필드의 의미와 차분·계층 처리 |
| OCI 1.2.1, CNI 1.1.0, CSI 1.11.0 | 명세의 경계와 capability; 제품 plugin 버전과 구분 |
| etcd 3.6, Kafka 4.3, RabbitMQ 4.3, Flink 1.20, Pulsar 4.0 | 해당 장의 적용 버전; 최신·유일 지원 버전 주장 아님 |
| Kubernetes 1.35 이상과 이전 버전 | 비교 규약을 구분; API server 1.34.1·etcd 3.6.4 실제 실행, workload 실행은 제외 |
| PostgreSQL 18.6 | 임시 인스턴스의 동시성·권한·수집 SQL 11개 시나리오 실행 |
| Linux 6.18.33.2·Python 3.12.3 | WSL2의 자기 프로세스와 기존 cgroup 읽기, HTTP/1.1 실습 |
| OTLP 1.11.0·Collector 0.137.0 | 규약 검토와 HTTP JSON 전송 실험; gRPC·영속 큐 검증은 제외 |
| Windows·SQLite 3.45.1·promtool 3.5.0 | 실제 실행 결과는 로컬 실습의 기록 범위 |
| 버전을 고정하지 않은 공식 웹 문서 | 확인 날짜 기준; 구현 시 실제 버전과 대조 |

개별 장의 범위가 이 요약보다 우선합니다. 다른 버전과 이름이 같더라도 필드·설정·수명·권한을 확인합니다.

## 교차 검토 시점의 버전 상태

확인일은 **2026-10-04**입니다. “고정”은 문서·실습을 해석할 기준이며 현재 권장 설치 버전을 뜻하지 않습니다. 최신 릴리스 확인과 실제 재실행은 별개입니다. 종료일이 확인되지 않은 항목은 임의로 날짜를 만들지 않았습니다.

| 대상 | 책의 고정 기준 | 검토 시점 현재 | 지원·종료와 해석 |
| --- | --- | --- | --- |
| Kubernetes | API server 1.34.1, 전 시나리오 watch cache 비활성화 | 최신 1.37.1, 최신 3개 브랜치 1.35–1.37; 1.34 계열 패치 1.34.12 | 1.34는 2026-10-27 종료 전 유지보수 중. 최신 3개에서 제외됐다고 이미 지원 종료된 것은 아님. [릴리스](https://kubernetes.io/releases/), [일정](https://kubernetes.io/releases/patch-releases/) |
| etcd | 3.6.4, Kubernetes 실습의 전용 인스턴스 | 최신 릴리스 3.7.2 | 이 검토에서는 3.6 계열의 종료일을 확정하지 않음. 새 버전으로 재실행하지 않음. [릴리스](https://github.com/etcd-io/etcd/releases/tag/v3.7.2) |
| OTel Collector | 0.137.0 HTTP JSON 실험 | 0.162.0; core 9월 28일, 배포판 9월 29일 UTC 게시 | 고정 버전은 최신 아님. 해당 태그의 정해진 LTS 종료일은 확인하지 못함. [core](https://github.com/open-telemetry/opentelemetry-collector/releases/tag/v0.162.0), [배포판](https://github.com/open-telemetry/opentelemetry-collector-releases/releases/tag/v0.162.0) |
| Prometheus/promtool | 3.5.0 | 최신 3.15.0, 현재 LTS 3.13.4 | 3.5 LTS는 2026-07-31 종료. 3.13 LTS 종료 예정일 2027-07-31. [다운로드](https://prometheus.io/download/), [지원 주기](https://prometheus.io/docs/introduction/release-cycle/) |
| MySQL | 8.4 LTS 문서, 서버 실습 없음 | 최신 LTS 계열 9.7; 9.7.2 일반 릴리스, 9.7.3 Docker image 전용 패치. 이후 YY.M 체계 | 새 LTS 등장만으로 8.4 지원 종료를 의미하지 않음. LTS는 Oracle 정책의 premier 5년·extended 3년 구분을 따르며 계약·배포판의 적용 조건 확인 필요. [정책](https://dev.mysql.com/doc/refman/9.7/en/mysql-releases.html), [9.7.2](https://dev.mysql.com/doc/relnotes/mysql/9.7/en/news-9-7-2.html), [9.7.3 범위](https://dev.mysql.com/doc/relnotes/mysql/9.7/en/news-9-7-3.html) |
| Ceph | Squid 문서 | Tentacle 20.2.4, Squid 19.2.6 | 공식 표는 Squid 2026-10-31을 **예상** 종료일로 표시. Tentacle의 예상일은 2027-06-01. [릴리스 표](https://docs.ceph.com/en/latest/releases/) |
| cAdvisor | 0.52.1 코드 | Kubernetes 1.37.1 의존성은 lib 0.60.5 | 해당 의존성의 working set 식을 코드 대조. cAdvisor 전체 최신 릴리스·고정 버전 종료일을 이 정보만으로 판정하지 않음. [의존성](https://github.com/kubernetes/kubernetes/blob/v1.37.1/go.mod), [계산 코드](https://github.com/google/cadvisor/blob/lib/v0.60.5/lib/container/libcontainer/handler.go) |
| OCI runtime spec | 1.2.1 | 1.3.0 | 명세 판본이며 런타임 제품의 지원 종료일과 다름. [릴리스](https://github.com/opencontainers/runtime-spec/releases/tag/v1.3.0) |
| CSI spec | 1.11.0 | 1.13.0 | 명세 판본이며 driver의 지원·capability는 별도 확인. [릴리스](https://github.com/container-storage-interface/spec/releases/tag/v1.13.0) |
| Flink | 1.20 문서 | 최신 안정 2.3.0, 1.20 LTS 패치 1.20.5 | 1.20을 단순히 지원 종료로 표시하지 않음. 종료일은 이 검토에서 확정하지 않음. [공식 다운로드](https://flink.apache.org/downloads/) |
| Tomcat | 10.1 connector 문서 | 10.1.60·11.0.26 지원 계열; Spring Boot 4의 내장 Tomcat은 11.0.x | Tomcat 10.1 지원과 Spring Boot의 기본 의존성은 다른 기준. [Tomcat 지원 표](https://tomcat.apache.org/whichversion.html), [Spring Boot 요구 사항](https://docs.spring.io/spring-boot/system-requirements.html) |
| PostgreSQL | 18 규약·18.6 실제 실험 | 18.6 | 18 계열 지원 종료 예정일 2030-11-14. [정책](https://www.postgresql.org/support/versioning/) |
| OTLP 원천 저장소 | 1.11.0 문서 | 원천 릴리스 1.11.1, 2026-09-29 게시; 공식 웹 문서 표시는 1.11.0 | 웹 문서의 판 표시와 원천 저장소의 최신 태그를 구분. 고정 규약의 전체 재검증이나 Collector의 지원 범위를 대신하지 않음. [릴리스](https://github.com/open-telemetry/opentelemetry-proto/releases/tag/v1.11.1), [웹 규약](https://opentelemetry.io/docs/specs/otlp/) |

Linux 커널·WSL 배포판, Python·SQLite·브라우저·문서 renderer 버전은 [검증 기록](validation.md)의 실행 환경 식별자입니다. 이 표의 소프트웨어 릴리스와 동일한 지원 체계로 취급하지 않으며, 이번 라운드에서 그 환경을 최신 버전으로 교체하지 않았습니다. 현재 릴리스 실습의 범위·예상 비용은 [교차 검토 응답](../review/claude-codex-r1.md)에 제안합니다.

## 이 판을 사용하는 경계

학습과 설계에 필요한 주요 원리를 상세히 연결했습니다. 장비 모델별 MIB·센서 전수, 모든 DB view의 전체 컬럼, 모든 cloud 서비스의 가격·quota, 모든 Unix·하이퍼바이저의 counter 전수는 포함하지 않습니다. 그러한 항목은 해당 대상의 어댑터 명세로 별도 구체화해야 합니다.

실제 실행 증거가 있는 범위는 [실습](cross-domain/reproducible-labs.md)과 [검증 기록](validation.md)에 한정합니다. 본문에 기술을 설명했다는 이유로 해당 제품을 설치하거나 운영 장애를 재현한 것으로 해석하지 않습니다.

## 함께 읽는 부록

[학습 안내](reading-guide.md) · [용어집](glossary.md) · [지표 참조표](metric-catalog.md) · [검토 기록](review.md) · [통합본](../BOOK.md)
