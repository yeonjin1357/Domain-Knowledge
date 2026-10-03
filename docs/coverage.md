# 분야별 집필 현황

2026-10-03 기준으로 **12개 분야의 개요와 상세 본문 58장**을 작성했습니다. 본문은 공식 자료를 확인해 작성한 학습용 초안입니다. 표의 추가 범위는 현재 책으로 충분히 다루지 못한 영역이며 실제 제품의 지원 여부와 다릅니다.

## 현재 본문과 추가 범위

| 분야 | 상세 장 수 | 현재 다루는 내용 | 추가로 깊게 다룰 범위 |
| --- | ---: | --- | --- |
| [공통 관측](foundations/README.md) | 5 | 시계열·분포·SLO·시간·품질·추적·로그·프로파일 | 통계 추론·시계열 이상 탐지, 계측 SDK별 실험 |
| [호스트](host/README.md) | 7 | Linux 자원·프로세스, Windows API, 가상화, GPU | 다른 Unix, NUMA·마이크로아키텍처 심화, 하이퍼바이저별 전체 카운터 |
| [네트워크](network/README.md) | 5 | IP·DNS·TCP·UDP·QUIC·TLS·HTTP, 인터페이스·흐름, 링크·MTU·BGP | 장비 OS별 MIB, OSPF·EVPN·QoS·무선·광 링크 심화 |
| [스토리지](storage/README.md) | 2 | 블록·파일·객체, IOPS·처리량·지속성, 용량·복제·snapshot·복구 | RAID·SAN·NAS 제품별 내부 구조·카운터와 복구 실험 |
| [컨테이너](containers/README.md) | 3 | namespace·OCI 수명, cgroup v2, 이미지·쓰기 계층·볼륨 | cgroup v1 전체 대응, Windows 컨테이너, 런타임별 검증 |
| [Kubernetes](kubernetes/README.md) | 6 | 객체·Pod·자원·HPA·수집·네트워크·저장, 주요 workload·etcd | CNI·CSI 구현 비교, CRD·operator별 로직, 버전별 feature gate |
| [애플리케이션](application/README.md) | 5 | 요청·풀·동시성·재시도, JVM·.NET·Go·Node.js·Python, 웹 사용자 경험 | WAS·프레임워크별 계측, native allocator, 모바일 native |
| [DB](database/README.md) | 7 | 트랜잭션·계획·복제, PostgreSQL·MySQL·MariaDB·SQL Server·Oracle, MongoDB·Cassandra·DynamoDB·ClickHouse | 엔진별 전체 관리 뷰·HA 구성, 시계열·그래프 DB, 추가 상용 엔진 |
| [미들웨어](middleware/README.md) | 5 | Redis·Kafka·RabbitMQ·Elasticsearch·OpenSearch·NGINX·Envoy·Istio | Memcached·Pulsar·Spark·Flink와 제품별 관리 API 전체 대응 |
| [클라우드](cloud/README.md) | 4 | AWS·Azure·Google Cloud 자원·API·집계, 관리형·서버리스, VPC 사례 | 공급자별 전체 서비스·할당량·비용, 프라이빗 클라우드별 연동 |
| [도메인 간 분석](cross-domain/README.md) | 4 | 요청·DB 잠금, OOM·볼륨, 캐시·적체·재시도, 관측 중단 | 실제 운영 사례와 재현 실험, 변경 전후 비교 자료 |
| [제품 설계](product/README.md) | 5 | 식별·관계, 수집·변환·전송, 저장·조회, 알림, 자체 관측·접근 경계 | 실제 제품 스키마·어댑터·SLO·용량 벤치마크의 확정 명세 |

스토리지·네트워크·복제처럼 여러 분야에 걸친 주제는 관련 장을 연결했습니다. 한 분야의 장 수만으로 깊이를 비교하기보다 연결된 본문까지 읽습니다.

## 부록과 학습 지원

- [학습 안내](reading-guide.md): 순서와 목적별 경로
- [용어집](glossary.md): 본문으로 연결되는 짧은 정의
- [지표 참조표](metric-catalog.md): 단위·분모·집계의 대표 규칙
- [검증 기록](validation.md): 자동 점검과 실제 실행 검증의 구분
- [통합본](../BOOK.md): 위 내용과 도메인 원문을 한 파일로 생성

## 검토한 기술 범위의 읽는 법

| 명시한 기준의 예 | 의미 |
| --- | --- |
| PostgreSQL 18, MySQL 8.4, Oracle 19c | 해당 공식 문서로 확인한 설명; 다른 버전 전체 검증 아님 |
| JDK 25, CPython 3.14 | 해당 API·런타임 문맥; 모든 배포판·옵션에 같은 결과 보장 아님 |
| OCI Runtime 1.2.1, etcd 3.6, Kafka 4.3, RabbitMQ 4.3 | 특정 명세·문서 기준; 적용 환경과 대조 필요 |
| Linux 6.12 회계 코드, man-pages 6.19, NVML R550 | 세부 의미를 확인한 원천; 최신 또는 유일 지원 버전이라는 뜻 아님 |
| 버전이 고정되지 않은 공식 웹 문서 | 장 상단의 확인일 기준; 구현할 버전에서 재확인 필요 |

개별 장의 범위 표시가 이 요약보다 우선합니다. 자료 확인일과 제품 출시일을 같은 의미로 사용하지 않습니다.

## 정확성 유지 기준

본문이 있다는 이유로 해당 분야의 모든 지식이나 모든 수집 명령이 완성되었다고 표시하지 않습니다. 변경되는 기술은 근거·버전·검증 상태를 함께 갱신합니다. 특히 실제 자료가 없는 성능 수치, 범용 임계값, 무손실·정확히 한 번 처리 같은 보장을 만들어 넣지 않습니다.
