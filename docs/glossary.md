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
| RPO / RTO | 허용 가능한 데이터 손실의 시간 범위 목표 / 복구 시간의 목표 | [복구](database/replication-and-recovery.md) |
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

## 시스템을 처음 배울 때

| 용어 | 의미 | 상세 |
| --- | --- | --- |
| Kernel | OS에서 실행·메모리·장치 등 자원을 관리하는 핵심 부분 | [시스템 지도](foundations/system-map.md) |
| Process / Thread | 실행 중인 프로그램의 자원 단위 / 그 안의 실행 흐름 | [프로세스](host/processes.md) |
| Logical CPU | OS가 실행을 배치할 수 있는 CPU 단위 | [CPU](host/cpu.md) |
| NUMA | CPU·메모리 위치에 따라 접근 특성이 달라지는 구조 | [NUMA](host/numa-and-pressure.md) |
| Affinity | 작업이 실행될 수 있는 CPU 집합을 제한하는 설정 | [NUMA](host/numa-and-pressure.md) |
| SMT | 한 코어에서 여러 논리 CPU 실행 문맥을 제공하는 기술 | [NUMA](host/numa-and-pressure.md) |
| IPC, Instructions per cycle | 관측 cycles당 instructions; 프로세스 간 통신이라는 다른 약어 뜻과 구분 | [NUMA](host/numa-and-pressure.md) |
| Cache miss | 요청 자료를 해당 캐시 계층에서 찾지 못한 사건 | [NUMA](host/numa-and-pressure.md) |
| Heap | 관리 runtime에서 객체를 할당하는 메모리 영역의 문맥 | [런타임](application/managed-runtimes.md) |
| Instrumentation | 실행의 의미 있는 경계에 관측 지점을 넣는 작업 | [계측](application/instrumentation-and-profiling.md) |
| eBPF | Linux BPF를 활용한 실행·관측 기법의 문맥; 모든 업무 의미를 자동 수집한다는 뜻 아님 | [계측](application/instrumentation-and-profiling.md) |

## 네트워크와 저장 계층

| 용어 | 의미 | 상세 |
| --- | --- | --- |
| Packet / Frame | 해당 네트워크 계층에서 다루는 전달 단위; 계층별 크기 경계 확인 필요 | [링크](network/layers-and-routing.md) |
| CIDR | 주소와 prefix 길이로 네트워크 범위를 표현하는 방식 | [주소](network/addressing-routing-dns.md) |
| ARP / ND | IPv4 링크 주소 해석 / IPv6 이웃 발견의 문맥 | [링크](network/layers-and-routing.md) |
| VTEP / VNI | VXLAN 터널 종단 / 가상 네트워크 식별 값 | [VXLAN](network/layers-and-routing.md) |
| Control / Data plane | 경로·정책을 결정하는 제어 / 실제 packet 전달 | [라우팅](network/routing-convergence-and-qos.md) |
| OSPF / BGP | 내부 링크 상태 라우팅 / 정책 기반 경로 교환 프로토콜 | [라우팅](network/routing-convergence-and-qos.md) |
| EVPN | BGP를 사용해 가상 네트워크 도달성 정보를 교환하는 제어 평면 | [EVPN](network/routing-convergence-and-qos.md) |
| QoS / DSCP | 트래픽 처리 정책 / DiffServ 분류에 사용하는 codepoint | [QoS](network/routing-convergence-and-qos.md) |
| SNMP / MIB / OID | 관리 질의 프로토콜 / 정보 정의 모음 / 객체 식별자 | [SNMP](network/snmp-and-device-models.md) |
| RAID | 여러 저장장치에 데이터를 배치·중복하는 방식 | [RAID](storage/raid-lvm-and-paths.md) |
| LVM PV / VG / LV | 물리 볼륨 / 볼륨 그룹 / 논리 볼륨; Kubernetes PV와 구분 | [LVM](storage/raid-lvm-and-paths.md) |
| Thin provisioning | 논리 제공량과 실제 backing 공간 할당을 분리하는 방식 | [LVM](storage/raid-lvm-and-paths.md) |
| SAN / NAS | 네트워크 블록 저장 환경 / 네트워크 파일 제공 환경 | [저장 경로](storage/raid-lvm-and-paths.md) |
| LUN | SCSI의 논리 장치를 구분하는 번호의 문맥 | [저장 경로](storage/raid-lvm-and-paths.md) |

## 제어·복구·데이터 진행

| 용어 | 의미 | 상세 |
| --- | --- | --- |
| CNI / IPAM | 컨테이너 네트워크 인터페이스 / IP 주소 할당 관리 | [CNI](kubernetes/cni-csi-and-data-paths.md) |
| CSI | container orchestration과 storage plugin 사이의 인터페이스 | [CSI](kubernetes/cni-csi-and-data-paths.md) |
| CRD / Operator | 새 API 종류의 정의 / 앱 운영 지식을 담은 controller 패턴 | [Operator](kubernetes/operators-and-api-lifecycle.md) |
| Admission | API 요청의 허용·변경을 결정하는 처리 경계 | [API](kubernetes/operators-and-api-lifecycle.md) |
| Fencing | 예전 writer가 더 이상 쓰지 못하게 하는 차단 경계 | [HA](database/high-availability.md) |
| Split brain | 서로 다른 구성원이 동시에 자신을 유효 writer 등으로 여기는 상태 | [HA](database/high-availability.md) |
| Linearizability | 연산이 실시간 순서를 존중하는 단일 순서로 설명 가능한 성질 | [분산 시스템](foundations/distributed-systems.md) |
| Serializability | 동시 transaction 결과가 어떤 직렬 실행과 동등한 성질 | [분산 시스템](foundations/distributed-systems.md) |
| Event / Processing time | 사건에 붙은 발생 시각 / 처리 시스템의 처리 시각 기준 | [스트림](middleware/stream-processing.md) |
| Watermark | event time 진행을 나타내는 신호 | [스트림](middleware/stream-processing.md) |
| Checkpoint | 복구할 상태와 진행을 정한 방식으로 보존하는 지점 | [스트림](middleware/stream-processing.md) |
| Compaction | 저장 구조를 병합·정리하는 배경 작업; 엔진별 의미 확인 | [DB 모델](database/specialized-data-models.md) |
| Quota | 자원 또는 작업에 적용되는 사용 한도와 그 범위 | [클라우드](cloud/quotas-cost-and-capacity.md) |
| Churn | 관측 대상·series가 생성·교체되는 빈도 또는 현상 | [제품 용량](product/capacity-and-loss-budgets.md) |

## 측정·동시성·전송을 읽는 용어

| 용어 | 쉬운 뜻과 구분 | 상세 |
| --- | --- | --- |
| 측정 경계 | 어디부터 어디까지, 누구의 작업을 셌는지 정한 범위 | [측정과 비교](foundations/measurement-and-comparability.md) |
| 해상도 / 정확도 | 구분할 수 있는 눈금 / 실제 값과의 일치 정도; 소수점 자릿수와 혼동하지 않음 | [시계와 오차](foundations/measurement-and-comparability.md) |
| RSS / PSS | 상주 페이지 계정 / 공유 페이지를 비례 배분한 계정 | [Linux 실습](host/linux-observation-lab.md) |
| Working set | 도구의 정의에 따른 메모리 관측값; cAdvisor의 계산을 실제로 회수 불가능한 총량과 동일시하지 않음 | [메모리 계정](containers/memory-accounting-and-oom.md) |
| SQLSTATE | SQL 처리 결과의 표준화된 코드 체계; 엔진·문맥과 함께 해석 | [PostgreSQL 실습](database/postgresql-concurrency-lab.md) |
| SAVEPOINT | 트랜잭션 안에서 그 지점 이후 작업을 되돌릴 수 있게 둔 저장점 | [실패와 저장점](database/postgresql-concurrency-lab.md) |
| 조회 snapshot | 한 조회·트랜잭션이 보는 기준 상태; DB 읽기·통계·스토리지 snapshot의 규약은 각각 다름 | [DB 실습](database/postgresql-concurrency-lab.md) |
| Selector | 관측할 객체 집합을 고르는 조건; 집합 이탈과 객체 삭제는 다를 수 있음 | [Kubernetes 인벤토리](kubernetes/inventory-consistency.md) |
| Partial success | 요청의 일부 항목은 수용하고 일부는 거절한 응답 | [전송 계약](product/telemetry-delivery-contracts.md) |
| Head / Tail sampling | 생성 시점 정보 / 모은 span 정보로 기록 대상을 선택하는 방식 | [Sampling](application/trace-sampling-and-context.md) |
| Negative caching | 이름 부재 등 부정 응답을 정해진 규약에 따라 보관하는 것 | [DNS와 연결](network/dns-and-connection-lifecycle.md) |
| Backfill / 재조회 | 과거 구간의 자료를 뒤늦게 확보·보완하는 처리; 중복 집계 정책 필요 | [Cloud 재조회](cloud/late-data-and-reconciliation.md) |
| Capability | 버전·설정·권한 등을 고려해 실제 사용할 수 있는 기능 | [필드 수용 기준](product/compatibility-and-acceptance.md) |

## 원천 통계와 제어 정책을 구분하는 용어

| 용어 | 의미·구분 | 상세 |
| --- | --- | --- |
| Exemplar | 집계 지표에서 선택한 개별 관측 사건과 trace 등의 연결 정보 | [지표 문맥](foundations/metric-context-and-start-time.md) |
| Counter start time | counter 집계가 시작된 시각; 최초 수집 시각과 다름 | [시작 시각](foundations/metric-context-and-start-time.md) |
| Adjusted count | 알려진 포함 확률의 역수인 추정 가중치; 실제 건수의 확정값 아님 | [Sampling 확률](application/trace-sampling-and-context.md) |
| Semantic conventions | 지표·속성 등의 이름·단위·의미를 공유하는 규약 | [안정 이름](application/semantic-conventions.md) |
| CurrEstab / RetransSegs | 현재 TCP 연결 gauge / namespace의 누적 재전송 세그먼트 계정 | [Linux 스택](network/linux-stack-counters.md) |
| RTO / cwnd | TCP 재전송 timeout / 혼잡 윈도; 복구 목표 RTO와 다른 문맥 | [소켓 통계](network/linux-stack-counters.md) |
| Pod QoS class | 자원 명세에 따른 Guaranteed·Burstable·BestEffort 분류; 네트워크 QoS와 구분 | [압박과 종료](kubernetes/pressure-and-termination.md) |
| WatchList | watch에서 초기 상태를 합성 이벤트로 전달하는 Kubernetes 기능 | [수집](kubernetes/collection.md) |
| Freeze / XID age | 오래된 행 XID를 정리하는 처리 / ID 공간의 거리; 경과 초와 다름 | [PostgreSQL 운영](database/postgresql-operations.md) |
| MultiXact | 여러 transaction의 행 잠금 구성원을 가리키는 별도 ID 체계 | [PostgreSQL 운영](database/postgresql-operations.md) |
| xmin horizon | 아직 필요한 행 버전의 회수를 막는 기준점; slot의 WAL 위치와 구분 | [회수 기준점](database/postgresql-operations.md) |
| Prepared transaction | 2단계 commit의 준비 상태로 남은 transaction; prepared statement와 다름 | [PostgreSQL 운영](database/postgresql-operations.md) |
| Share group | Kafka 레코드를 획득·확인·재전달하는 소비 모델; consumer group offset과 다른 진행 모델 | [Kafka](middleware/kafka.md) |
| FLUSH / FUA | 장치 캐시의 선행 쓰기 반영 / 해당 쓰기의 지속성 완료를 요청하는 동작 | [쓰기 경로](storage/write-path-and-durability.md) |
| PMTUD / DPLPMTUD | 경로 MTU 탐색 / datagram packetization layer의 MTU 탐색 | [MTU](network/layers-and-routing.md) |
| Time grain / Ingestion delay | 집계 구간 크기 / 측정 후 조회 가능해지기까지의 지연 | [Cloud 시간 축](cloud/provider-metrics.md) |

## 회수·분포 저장·엔진 내부를 읽는 용어

| 용어 | 의미·구분 | 상세 |
| --- | --- | --- |
| Reclaim / Refault | 페이지 회수 / 밀려났던 페이지의 재참조; 회수량·재읽기와 지연 시간을 구분 | [회수·OOM](host/reclaim-and-oom.md) |
| Direct reclaim / kswapd | 할당 경로의 직접 회수 / 백그라운드 회수 | [회수·OOM](host/reclaim-and-oom.md) |
| Memcg OOM | memory cgroup의 제약 범위에서 발생한 OOM; kubelet eviction과 별개 | [회수·OOM](host/reclaim-and-oom.md) |
| PSI trigger | window 안의 stall 조건을 fd로 감시하는 커널 모니터 등록 | [PSI](host/numa-and-pressure.md) |
| RssAnon / RssFile / RssShmem | 익명·파일·공유 메모리의 상주량 분류; 정밀도·포함 범위 확인 | [프로세스](host/processes.md) |
| Next-key / Gap lock | 인덱스 레코드와 앞 구간의 잠금 / 삽입할 빈 구간을 보호하는 잠금 | [MySQL 운영](database/mysql-operations.md) |
| GTID | 복제 트랜잭션 식별자; wall clock 또는 모든 source의 단일 순번이 아님 | [MySQL 운영](database/mysql-operations.md) |
| ExponentialHistogram scale | 지수 경계의 해상도 매개변수; 낮추면 버킷이 더 거칠어짐 | [분포 저장](foundations/histogram-storage.md) |
| NHCB | custom bucket 경계를 담는 native histogram; exponential 형식과 구분 | [분포 저장](foundations/histogram-storage.md) |
| Sketch / Centroid | 작은 통계 요약 자료구조 / t-digest가 표본들을 묶은 가중 대표점 | [분포 저장](foundations/histogram-storage.md) |
| Offset / Frequency / Skew | 시각 차이 / 진행 속도 차이 / chrony 주파수 추정의 불확실성 | [시계](foundations/time-and-data-quality.md) |
| PHC / Leap smear | PTP 하드웨어 시계 / 윤초를 일정 구간에 분산하는 정책 | [시계](foundations/time-and-data-quality.md) |
| RCSI / PVS | row versioning 기반 READ COMMITTED / ADR의 persistent version store | [SQL Server](database/sqlserver-oracle.md) |
| ASH / AWR | Oracle 활성 세션 표본 이력 / 성능 통계 이력; 사용 권리 확인 필요 | [Oracle](database/sqlserver-oracle.md) |
| JFR / EventPipe | JVM 이벤트 기록 / .NET 진단 이벤트 전달 경로 | [런타임](application/managed-runtimes.md) |
| ELU | 이벤트 루프 active/idle 기준의 사용 비율; OS CPU 사용률과 다름 | [Node](application/async-runtimes.md) |
| Chunk / Record | 로그 전송·재시도의 묶음 / 개별 기록; 줄 수와도 구분 | [로그 전달](product/collection-pipelines.md) |
| SM / Warp / Occupancy | GPU 실행 단위 / 실행 스레드 묶음 / 최대 대비 resident warp 점유 | [GPU](host/gpu.md) |
| Xid / Row remapping | NVIDIA driver 오류 보고 / 불량 메모리 행을 예비 행으로 대체 | [GPU](host/gpu.md) |

용어의 짧은 정의는 학습을 돕는 요약입니다. 실제 판정과 계산은 연결된 원천·버전·조건을 따릅니다.
