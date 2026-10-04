# 제1판의 분야별 범위

2026-10-04 기준 **12개 분야, 상세 본문 80장**을 통합했습니다. 표는 읽을 수 있는 본문의 범위이며 사용자 제품의 지원 여부를 뜻하지 않습니다.

| 분야 | 상세 장 | 이번 판에서 다루는 내용 |
| --- | ---: | --- |
| [공통 관측](foundations/README.md) | 8 | 시스템 지도, 시계열·단위·분포·SLO·시간·trace·sampling, 성능 실험, 분산 시스템 |
| [호스트](host/README.md) | 9 | Linux CPU·메모리·블록 I/O·프로세스, Windows API, VM·GPU, NUMA·압력·원천 필드 |
| [네트워크](network/README.md) | 7 | IP·DNS·TCP·UDP·QUIC·TLS·HTTP, 링크·MTU·BGP, SNMP·OSPF·EVPN·QoS |
| [스토리지](storage/README.md) | 3 | 블록·파일·객체, 처리량·IOPS·지속성, 복제·snapshot·복구, RAID·LVM·SAN·NAS |
| [컨테이너](containers/README.md) | 4 | namespace·OCI 수명·image·COW·volume, cgroup v1/v2, Windows 격리 차이 |
| [Kubernetes](kubernetes/README.md) | 8 | API·Pod·request/limit·HPA·수집·Service·PV/PVC·workload·etcd, CNI·CSI·CRD·Operator |
| [앱](application/README.md) | 7 | 요청·queue·pool·deadline·retry, JVM·.NET·Go·Node.js·Python, RUM·계측·프로파일 |
| [DB](database/README.md) | 10 | transaction·MVCC·lock·index·plan·WAL·HA, 주요 엔진·분산·분석·시계열·그래프, 수집 SQL |
| [미들웨어](middleware/README.md) | 6 | Redis·Memcached·Kafka·RabbitMQ·Pulsar·검색·프록시·mesh, Flink·Spark 처리 경계 |
| [클라우드](cloud/README.md) | 5 | AWS·Azure·Google Cloud 식별·API·기간 집계, 관리형·서버리스·VPC, quota·비용 |
| [도메인 간 분석](cross-domain/README.md) | 6 | 지연·자원·적체·관측 중단 사례, 실제 로컬 실습, 종합 연습과 해설 |
| [제품 설계](product/README.md) | 7 | 정체성·관계·수집·저장·질의·알림·tenant 접근·자체 관측, adapter 계약·용량 |

## 대표 적용 범위

| 원천 | 이 책에서의 적용 |
| --- | --- |
| PostgreSQL 18, MySQL 8.4, Oracle 19c | 해당 버전의 동작·통계·단위 설명 |
| SQL Server, MariaDB, MongoDB, Cassandra, DynamoDB, ClickHouse | 장에 표시한 공식 원천과 구체적인 사례의 범위 |
| JDK 25, CPython 3.14, .NET·Go·Node.js 문서 | runtime 메모리·실행·관측 의미; 모든 배포 옵션 인증 아님 |
| Linux 6.12 코드·NUMA 문서, cgroup·procfs | 명시한 원천 필드의 의미와 차분·계층 처리 |
| OCI 1.2.1, CNI 1.1.0, CSI 1.11.0 | 명세의 경계와 capability; 제품 plugin 버전과 구분 |
| etcd 3.6, Kafka 4.3, RabbitMQ 4.3, Flink 1.20, Pulsar 4.0 | 해당 장의 적용 버전; 최신·유일 지원 버전 주장 아님 |
| Windows·SQLite 3.45.1·promtool 3.5.0 | 실제 실행 결과는 로컬 실습의 기록 범위 |
| 버전을 고정하지 않은 공식 웹 문서 | 확인 날짜 기준; 구현 시 실제 버전과 대조 |

개별 장의 범위가 이 요약보다 우선합니다. 다른 버전과 이름이 같더라도 필드·설정·수명·권한을 확인합니다.

## 이 판을 사용하는 경계

학습과 설계에 필요한 주요 원리를 상세히 연결했습니다. 장비 모델별 MIB·센서 전수, 모든 DB view의 전체 컬럼, 모든 cloud 서비스의 가격·quota, 모든 Unix·하이퍼바이저의 counter 전수는 포함하지 않습니다. 그러한 항목은 해당 대상의 어댑터 명세로 별도 구체화해야 합니다.

실제 실행 증거가 있는 범위는 [실습](cross-domain/reproducible-labs.md)과 [검증 기록](validation.md)에 한정합니다. 본문에 기술을 설명했다는 이유로 해당 제품을 설치하거나 운영 장애를 재현한 것으로 해석하지 않습니다.

## 함께 읽는 부록

[학습 안내](reading-guide.md) · [용어집](glossary.md) · [지표 참조표](metric-catalog.md) · [검토 기록](review.md) · [통합본](../BOOK.md)
