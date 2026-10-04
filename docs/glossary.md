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

용어의 짧은 정의는 학습을 돕는 요약입니다. 실제 판정과 계산은 연결된 원천·버전·조건을 따릅니다.
