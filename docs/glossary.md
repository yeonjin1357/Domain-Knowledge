# 통합 모니터링 용어집

이 표는 본문을 찾아가기 위한 짧은 정의입니다. 같은 용어의 엔진별 차이와 계산 조건은 연결된 상세 장을 따릅니다.

## 관측과 통계

| 용어 | 이 책에서의 의미 | 상세 |
| --- | --- | --- |
| Telemetry | 시스템에서 관측해 전달하는 측정·사건 자료 | [공통 관측](foundations/README.md) |
| Time series | 같은 식별 범위의 값을 시간에 따라 기록한 자료 | [시계열](foundations/time-series.md) |
| Counter | 재시작·reset을 고려해야 하는 누적 증가값 | [시계열](foundations/time-series.md) |
| Gauge | 증가·감소할 수 있는 상태값 | [시계열](foundations/time-series.md) |
| Delta / Cumulative | 구간의 양 / 같은 시작점부터의 누적량 | [시계열](foundations/time-series.md) |
| Rate | 단위 시간당 증가·발생량; 원천 유형과 구간 명시 필요 | [시계열](foundations/time-series.md) |
| Cardinality | 여기서는 서로 다른 시계열 조합의 수 | [시계열](foundations/time-series.md) |
| Histogram | 값의 구간별 개수로 나타낸 분포 | [분포](foundations/distributions.md) |
| Percentile | 순서 지어진 분포에서 특정 비율의 위치를 나타내는 값 | [분포](foundations/distributions.md) |
| Sampling | 전체 중 일부를 선택해 관측·보존하는 과정 | [추적](foundations/traces-logs-profiles.md) |
| Trace / Span | 요청의 연결된 작업 구조 / 그 구조의 개별 작업 구간 | [추적](foundations/traces-logs-profiles.md) |
| Context propagation | 호출 사이에 trace 등 관련 문맥을 전달하는 것 | [추적](foundations/traces-logs-profiles.md) |
| Profile | 코드 stack과 자원 소비·대기 등을 연결한 관측 | [추적](foundations/traces-logs-profiles.md) |
| SLI / SLO | 서비스 수준의 측정 지표 / 그 지표의 목표 | [서비스 수준](foundations/service-level-objectives.md) |
| Error budget | SLO에서 허용한 실패의 양 | [서비스 수준](foundations/service-level-objectives.md) |
| Burn rate | 허용 실패 비율에 대비한 관측 실패 비율의 배수 | [서비스 수준](foundations/service-level-objectives.md) |
| Freshness / Staleness | 자료의 최신성 / 더 이상 현재를 충분히 설명하지 못하는 상태 | [데이터 품질](foundations/time-and-data-quality.md) |
| Monotonic clock | 지속 시간 측정에 쓰는, 뒤로 가지 않는 시계 | [데이터 품질](foundations/time-and-data-quality.md) |

## 실행과 자원

| 용어 | 의미 | 상세 |
| --- | --- | --- |
| CPU time | 정한 대상이 CPU에서 실행한 시간의 합 | [CPU](host/cpu.md) |
| Wall time | 정한 시작·종료 사이에 경과한 시간 | [CPU](host/cpu.md) |
| Load average | Linux에서는 실행 가능·특정 대기 상태 작업 수를 반영한 평균 | [CPU](host/cpu.md) |
| PSI | 자원 압력으로 작업 진행이 막힌 시간을 관측하는 Linux 인터페이스 | [CPU](host/cpu.md) |
| RSS / PSS | 상주 메모리 / 공유 페이지를 비례 배분한 상주 메모리 | [메모리](host/memory.md) |
| Commit | 메모리 제공 약속의 문맥; OS·API별 의미 확인 필요 | [Windows](host/windows.md) |
| Swap | 메모리 페이지를 보조 저장 공간과 주고받는 문맥 | [메모리](host/memory.md) |
| FD | 프로세스에서 열린 파일 등 객체를 참조하는 정수 식별자 | [프로세스](host/processes.md) |
| IOPS / Throughput | 초당 I/O 작업 수 / 단위 시간당 처리한 데이터량 | [I/O](host/disk-io.md) |
| cgroup | Linux에서 프로세스 집합의 자원을 계층적으로 관측·제어하는 기능 | [자원 제어](containers/resource-control.md) |
| Namespace | Linux에서는 프로세스가 보는 특정 시스템 자원의 범위를 격리하는 기능 | [격리](containers/isolation-and-lifecycle.md) |
| Throttling | 정해진 자원·호출 한도로 작업을 제한하는 것; 원천별 동작은 다름 | [cgroup](containers/resource-control.md) |
| Copy-on-write | 공유된 내용을 변경할 때 별도 쓰기 대상으로 분리하는 방식 | [파일시스템](containers/filesystems.md) |
| Hypervisor | VM의 실행과 가상 자원을 관리하는 계층 | [가상화](host/virtualization.md) |
| MIG | 지원 NVIDIA GPU를 격리된 GPU 인스턴스 등으로 분할하는 기능 | [GPU](host/gpu.md) |

## Kubernetes와 애플리케이션

| 용어 | 의미 | 상세 |
| --- | --- | --- |
| Reconciliation | 관측한 상태를 원하는 상태에 맞추려는 제어 과정 | [객체](kubernetes/objects-and-control-loops.md) |
| UID | Kubernetes 객체의 고유 식별자; 이름과 구분 | [객체](kubernetes/objects-and-control-loops.md) |
| Readiness / Liveness | 트래픽을 받을 준비 판단 / 재시작 판단에 쓰는 건강 검사 문맥 | [Pod](kubernetes/pod-lifecycle.md) |
| Request / Limit | 배치 등에 사용하는 요청 자원 / 실행 자원 제어 한도 | [배치](kubernetes/resources-and-scheduling.md) |
| Eviction | 특정 사유로 Pod 실행을 종료·제거하는 동작; OOM과 구분 | [배치](kubernetes/resources-and-scheduling.md) |
| PV / PVC | Kubernetes 저장 자원 / 저장 자원 사용 요청 | [저장 연결](kubernetes/network-and-storage.md) |
| Concurrency | 같은 관측 경계 안에서 동시에 진행 중인 작업 수 | [요청](application/requests-and-concurrency.md) |
| Pool | 재사용 가능한 연결·실행 자원 등을 대여·반환하는 구조 | [요청](application/requests-and-concurrency.md) |
| Deadline / Timeout | 완료 기한 / 정한 단계에 허용한 대기 시간 | [재시도](application/timeouts-and-retries.md) |
| Idempotence | 같은 작업을 반복 적용해도 의도한 효과가 한 번과 같은 성질 | [재시도](application/timeouts-and-retries.md) |
| GC | 더 이상 필요하지 않은 관리 메모리를 회수하는 런타임 기능 | [관리 런타임](application/managed-runtimes.md) |
| Event loop | 이벤트와 callback·작업을 실행하는 반복 처리 구조 | [비동기 런타임](application/async-runtimes.md) |
| RUM | 실제 사용자 환경에서 얻는 사용자 경험 관측 | [사용자 경험](application/user-experience.md) |

## 데이터와 통신

| 용어 | 의미 | 상세 |
| --- | --- | --- |
| Transaction | 정한 원자성·격리·지속성 조건으로 묶인 DB 작업 단위 | [트랜잭션](database/transactions-and-locks.md) |
| MVCC | 여러 버전의 데이터를 이용해 읽기와 변경의 동시성을 다루는 방식 | [트랜잭션](database/transactions-and-locks.md) |
| Deadlock | 작업들이 서로가 보유한 자원을 기다리는 순환 대기 | [트랜잭션](database/transactions-and-locks.md) |
| Execution plan | DB가 선택한 연산과 접근 경로의 구조 | [실행 계획](database/queries-and-indexes.md) |
| WAL | 데이터 페이지의 영속 반영보다 복구 로그를 먼저 기록하는 원리 | [복구](database/replication-and-recovery.md) |
| Replication lag | 복제 진척의 차이; 시간·바이트·위치 등 기준을 명시해야 함 | [복구](database/replication-and-recovery.md) |
| Quorum | 정한 합의·읽기·쓰기 규칙이 요구하는 참여 수; 의미는 시스템마다 다름 | [분산 DB](database/distributed-and-analytical.md) |
| RPO / RTO | 허용 손실 시점의 목표 / 복구 시간의 목표 | [복구](database/replication-and-recovery.md) |
| Cache eviction | 정책이나 한도에 따라 캐시 항목을 제거하는 것 | [Redis](middleware/cache-redis.md) |
| Offset | Kafka partition 로그의 위치 식별; 업무 완료와 같은 뜻 아님 | [Kafka](middleware/kafka.md) |
| Acknowledgement | 정한 단계의 수신·처리 확인; 누가 무엇을 확인했는지 명시 필요 | [메시지 큐](middleware/message-queues.md) |
| Shard | 데이터·검색 등의 작업을 나누는 단위; 엔진별 구조는 다름 | [검색](middleware/search-engines.md) |
| RTT | 특정 관측의 왕복 시간 | [TCP](network/tcp-and-udp.md) |
| Retransmission | 데이터를 다시 전송하는 동작; 손실률과 바로 같지는 않음 | [TCP](network/tcp-and-udp.md) |
| NAT | 관측 경계에서 네트워크 주소 등을 변환하는 기능 | [주소](network/addressing-routing-dns.md) |
| MTU | 해당 링크·계층에서 운반 가능한 패킷 크기의 제한 | [MTU](network/layers-and-routing.md) |
| TLS | 전송 구간의 암호화·인증 등을 제공하는 프로토콜 | [TLS](network/tls-http.md) |
| Backpressure | 처리 가능한 속도에 맞춰 상류 유입을 제어하는 동작 | [파이프라인](product/collection-pipelines.md) |
| Downsampling | 시간 해상도 등을 줄이도록 원천 자료를 집계·축약하는 과정 | [저장](product/storage-and-query.md) |

같은 `namespace`라도 Kubernetes namespace, Linux namespace, CloudWatch namespace는 서로 다른 개념입니다. `active`, `used`, `lag`, `commit`처럼 여러 시스템이 공유하는 단어는 이름만으로 공통 지표에 매핑하지 않습니다.
