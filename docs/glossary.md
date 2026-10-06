# 통합 모니터링 용어집

이 표는 본문을 찾아가기 위한 짧은 정의입니다. 같은 용어의 엔진별 차이와 계산 조건은 연결된 상세 장을 따릅니다.

## 관측과 통계

| 용어 | 의미와 구분 | 상세 |
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
| 측정 경계 | 어디부터 어디까지, 누구의 작업을 셌는지 정한 범위 | [측정과 비교](foundations/measurement-and-comparability.md) |
| 해상도 / 정확도 | 구분할 수 있는 눈금 / 실제 값과의 일치 정도; 소수점 자릿수와 혼동하지 않음 | [시계와 오차](foundations/measurement-and-comparability.md) |
| Exemplar | 집계 지표에서 선택한 개별 관측 사건과 trace 등의 연결 정보 | [지표 문맥](foundations/metric-context-and-start-time.md) |
| Counter start time | counter 집계가 시작된 시각; 최초 수집 시각과 다름 | [시작 시각](foundations/metric-context-and-start-time.md) |
| ExponentialHistogram scale | 지수 경계의 해상도 매개변수; 낮추면 버킷이 더 거칠어짐 | [분포 저장](foundations/histogram-storage.md) |
| NHCB | custom bucket 경계를 담는 native histogram; exponential 형식과 구분 | [분포 저장](foundations/histogram-storage.md) |
| Sketch / Centroid | 작은 통계 요약 자료구조 / t-digest가 표본들을 묶은 가중 대표점 | [분포 저장](foundations/histogram-storage.md) |
| PHC / Leap smear | PTP 하드웨어 시계 / 윤초를 일정 구간에 분산하는 정책 | [시계](foundations/time-and-data-quality.md) |
| Monotonic clock | 지속 시간용 단조 시계. Linux CLOCK_MONOTONIC은 주파수 조정을 받으며 RAW와 진행 속도가 다를 수 있음 | [Monotonic clock](foundations/time-and-data-quality.md) |
| Temporality | 집계값이 구간 증가량인지 누적량인지 정하는 시간 의미 | [Temporality](foundations/time-series.md) |
| Classic / Native histogram | 버킷별 시계열 / 한 복합 표본 안에 버킷 등을 담는 Prometheus 분포 형식 | [Classic / Native histogram](foundations/histogram-storage.md) |
| Schema (histogram) | 버킷 경계 배치를 정하는 식별 값; 일반적인 데이터 schema와 문맥을 구분 | [Schema (histogram)](foundations/histogram-storage.md) |
| Zero bucket | 지수 버킷과 별도로 0 주변의 관측을 모으는 구간 | [Zero bucket](foundations/histogram-storage.md) |
| 보간 / 외삽 | 알려진 구간 안을 가정으로 채움 / 알려진 범위 밖으로 추정함 | [보간 / 외삽](foundations/distributions.md) |
| DDSketch | 상대 값 오차를 제어하는 병합 가능한 분포 요약 | [DDSketch](foundations/histogram-storage.md) |
| 상대 오차 / 순위 오차 | 값의 크기에 대한 오차 / 정렬된 분포에서 위치의 오차 | [상대 오차 / 순위 오차](foundations/histogram-storage.md) |
| _created | OpenMetrics counter 등의 생성 시각; 첫 scrape 시각과 다름 | [_created](foundations/metric-context-and-start-time.md) |
| Reservoir | exemplar 후보 중 제한된 표본을 보유하는 저장 구조 | [Reservoir](foundations/metric-context-and-start-time.md) |
| NTP / PTP | 네트워크 시각 동기화 프로토콜 / 정밀 시각 동기화 프로토콜 | [NTP / PTP](foundations/time-and-data-quality.md) |
| ppm | 백만분율. 시계 속도 오차 1 ppm은 초당 1 μs의 차이에 해당 | [ppm](foundations/time-and-data-quality.md) |
| Step / Slew | 시각을 한 번에 이동 / 진행 속도를 조절해 보정 | [Step / Slew](foundations/time-and-data-quality.md) |
| Offset (시계) | 기준 시계와의 시각 차이. 도구별 부호 정의 확인 | [Offset (시계)](foundations/time-and-data-quality.md) |
| Frequency / Skew | 시계 진행 속도 차이 / chrony 주파수 추정의 불확실성 | [Frequency / Skew](foundations/time-and-data-quality.md) |
| Offset (버킷) | 연속된 버킷 배열의 시작 index; 시각 차이나 Kafka 위치와 다름 | [Offset (버킷)](foundations/histogram-storage.md) |
| Lookback | 질의가 현재 표본을 찾을 때 거슬러 보는 구간의 규약 | [Lookback](foundations/time-and-data-quality.md) |
| UpDownCounter | 증가량과 감소량을 함께 기록하는 OTel 계측 유형 | [UpDownCounter](application/semantic-conventions.md) |
| Little의 법칙 | 안정 상태에서 평균 진행 중 수 = 도착률 × 평균 체류 시간 | [Little의 법칙](foundations/performance-and-statistics.md) |
| 가상 예시 / 합성 검사 | 설명을 위한 임의 수치·상황 / 실제 사용자 대신 요청을 보내는 synthetic monitoring | [가상 예시 / 합성 검사](application/user-experience.md) |
| OTLP | OpenTelemetry Protocol. 관측 자료를 전송하는 규약 | [OTLP](product/telemetry-delivery-contracts.md) |
| Collector | 관측 자료를 받아 처리하고 내보내는 OpenTelemetry 구성 요소 | [Collector](product/collection-pipelines.md) |
| Receiver / Exporter | Collector의 입력 / 출력 구성 요소. Prometheus exporter는 scrape용 endpoint 제공 역할 | [Receiver / Exporter](foundations/README.md) |

## 실행과 자원

| 용어 | 의미와 구분 | 상세 |
| --- | --- | --- |
| CPU time | 정한 대상이 CPU에서 실행한 시간의 합 | [CPU](host/cpu.md) |
| Wall time | 정한 시작·종료 사이에 경과한 시간 | [CPU](host/cpu.md) |
| Load average | Linux에서는 실행 가능·특정 대기 상태 작업 수를 반영한 평균 | [CPU](host/cpu.md) |
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
| RSS / PSS | 상주 페이지 계정 / 공유 페이지를 비례 배분한 계정; 기본 수집과 상세 조사 원천을 구분 | [RSS / PSS](host/processes.md) |
| PSI | 자원 압력으로 작업 진행이 막힌 시간의 Linux 인터페이스 | [PSI](host/numa-and-pressure.md) |
| 페이지 | 메모리를 관리·매핑하는 단위. 크기는 환경에서 확인 | [페이지](host/memory.md) |
| 익명 / 파일 메모리 | 일반 파일의 내용과 직접 연결되지 않은 메모리 / 파일에 대응하는 페이지 | [익명 / 파일 메모리](host/memory.md) |
| Page cache | 파일 데이터를 메모리에 보관하는 캐시 | [Page cache](host/memory.md) |
| Inactive file / LRU | 비활성 파일 페이지 계정 / 최근 사용 정보를 회수 선택에 활용하는 구조 | [Inactive file / LRU](host/memory.md) |
| MGLRU | 여러 세대로 사용 이력을 관리하는 Linux 페이지 회수 방식 | [MGLRU](host/reclaim-and-oom.md) |
| OOM killer | 메모리 부족 상황에서 작업을 선택해 종료하는 커널 경로; kubelet 축출과 다름 | [OOM killer](host/reclaim-and-oom.md) |
| MemAvailable | swap 없이 새 작업에 제공할 수 있는 Linux 메모리의 추정치 | [MemAvailable](host/memory.md) |
| Iowait / Steal | I/O 대기 계정 / 가상 CPU가 hypervisor에 의해 실행하지 못한 시간 계정 | [Iowait / Steal](host/cpu.md) |
| D 상태 | Linux의 중단 불가능한 대기 상태; 디스크 대기만 뜻하지 않음 | [D 상태](host/processes.md) |
| Zswap / Zram | swap 앞의 압축 캐시 / 압축 RAM 블록 장치; pswpout 포함 범위가 다름 | [Zswap / Zram](host/reclaim-and-oom.md) |
| Working set (Windows) | 프로세스의 물리 메모리 상주 페이지 집합 | [Working set (Windows)](host/windows.md) |
| Working set (cAdvisor) | usage에서 inactive_file을 뺀 계산값; 회수 불가능량과 동일하지 않음 | [Working set (cAdvisor)](containers/memory-accounting-and-oom.md) |
| Working set (개념) | 정한 관측 구간에 작업이 필요로 하는 페이지 집합의 문맥 | [Working set (개념)](containers/memory-accounting-and-oom.md) |
| Kernel (OS / GPU) | OS의 자원 관리 핵심 / GPU에서 실행하는 함수·작업; 서로 다른 뜻 | [Kernel (OS / GPU)](host/gpu.md) |
| NVML / DCGM | NVIDIA 장치 관리 API / GPU 관리·건강·프로파일 관측 도구 | [NVML / DCGM](host/gpu.md) |
| Xid (NVIDIA) / Row remapping | driver 오류 보고 / 불량 메모리 행을 예비 행으로 대체 | [Xid (NVIDIA) / Row remapping](host/gpu.md) |

## Kubernetes와 애플리케이션

| 용어 | 의미와 구분 | 상세 |
| --- | --- | --- |
| Reconciliation | 관측한 상태를 원하는 상태에 맞추려는 제어 과정 | [객체](kubernetes/objects-and-control-loops.md) |
| UID | Kubernetes 객체의 고유 식별자; 이름과 구분 | [객체](kubernetes/objects-and-control-loops.md) |
| Readiness / Liveness | 트래픽을 받을 준비 판단 / 재시작 판단에 쓰는 건강 검사 문맥 | [Pod](kubernetes/pod-lifecycle.md) |
| Request / Limit | 배치 등에 사용하는 요청 자원 / 실행 자원 제어 한도 | [배치](kubernetes/resources-and-scheduling.md) |
| PV / PVC | Kubernetes 저장 자원 / 저장 자원 사용 요청 | [저장 연결](kubernetes/network-and-storage.md) |
| Concurrency | 같은 관측 경계 안에서 동시에 진행 중인 작업 수 | [요청](application/requests-and-concurrency.md) |
| Pool | 재사용 가능한 연결·실행 자원 등을 대여·반환하는 구조 | [요청](application/requests-and-concurrency.md) |
| Deadline / Timeout | 완료 기한 / 정한 단계에 허용한 대기 시간 | [재시도](application/timeouts-and-retries.md) |
| Idempotence | 같은 작업을 반복 적용해도 의도한 효과가 한 번과 같은 성질 | [재시도](application/timeouts-and-retries.md) |
| GC | 더 이상 필요하지 않은 관리 메모리를 회수하는 런타임 기능 | [관리 런타임](application/managed-runtimes.md) |
| Event loop | 이벤트와 callback·작업을 실행하는 반복 처리 구조 | [비동기 런타임](application/async-runtimes.md) |
| RUM | 실제 사용자 환경에서 얻는 사용자 경험 관측 | [사용자 경험](application/user-experience.md) |
| Eviction | 축출. kubelet 노드 압박 축출과 PDB가 적용되는 API 축출을 구분 | [Eviction](kubernetes/pressure-and-termination.md) |
| ResourceVersion | API 객체·목록의 버전 값. 응답 API server의 버전·종류·규약을 확인하며 순서 비교도 같은 cluster·resource type 안으로 한정 | [ResourceVersion](kubernetes/inventory-consistency.md) |
| Watch / Bookmark | 변경 스트림 / watch 진행 위치를 알리는 사건 | [Watch / Bookmark](kubernetes/inventory-consistency.md) |
| WatchList / Streaming list | sendInitialEvents로 초기 객체를 watch 사건으로 전달. 응답 encoding의 streaming과 다름 | [WatchList / Streaming list](kubernetes/inventory-consistency.md) |
| Eviction 신호 | memory.available·파일시스템·PID 등의 노드 압박 판단 입력 | [Eviction 신호](kubernetes/pressure-and-termination.md) |
| OOMKilled / Evicted | 컨테이너 종료 원인 / 축출된 Pod의 사유. 증거와 수명 단위를 구분 | [OOMKilled / Evicted](kubernetes/pressure-and-termination.md) |
| Kubelet / cAdvisor | 노드에서 Pod 실행을 관리하는 agent / 컨테이너 자원 통계 제공 구성 요소 | [Kubelet / cAdvisor](kubernetes/collection.md) |
| Summary API | kubelet이 노드·Pod·컨테이너 통계를 묶어 제공하는 API | [Summary API](kubernetes/collection.md) |
| Metrics-server | kubelet 자료로 Resource Metrics API를 제공하는 구성 요소 | [Metrics-server](kubernetes/collection.md) |
| Kube-state-metrics | Kubernetes API 객체 상태를 지표로 노출하는 구성 요소 | [Kube-state-metrics](kubernetes/collection.md) |
| PDB | PodDisruptionBudget. 자발적 중단 시 허용할 가용 Pod 감소를 정하는 정책 | [PDB](kubernetes/pressure-and-termination.md) |
| Feature gate | 특정 기능의 사용 여부를 제어하는 버전별 설정 | [Feature gate](kubernetes/pressure-and-termination.md) |
| Allocatable | 노드 용량에서 예약 등을 고려한 Pod 배치용 자원량 | [Allocatable](kubernetes/resources-and-scheduling.md) |
| Finalizer | 객체 삭제 완료 전에 정리 작업을 요구하는 API 표식 | [Finalizer](kubernetes/operators-and-api-lifecycle.md) |
| Watch cache | API server가 watch와 조회에 활용하는 객체·변경의 캐시 | [Watch cache](kubernetes/inventory-consistency.md) |
| GIL | CPython에서 Python 코드 실행을 조정하는 전역 잠금의 문맥; 빌드별 차이 확인 | [GIL](application/async-runtimes.md) |
| JMX / MBean | Java 관리 인터페이스 / 그 인터페이스로 노출하는 관리 객체 | [JMX / MBean](application/managed-runtimes.md) |
| Stop-the-world | 런타임이 일부 작업을 위해 애플리케이션 실행을 멈추는 구간 | [Stop-the-world](application/managed-runtimes.md) |
| Traceparent / Tracestate | W3C trace 식별 문맥 / vendor별 추가 trace 문맥 전달 필드 | [Traceparent / Tracestate](application/trace-sampling-and-context.md) |

## 데이터와 통신

| 용어 | 의미와 구분 | 상세 |
| --- | --- | --- |
| Transaction | 정한 원자성·격리·지속성 조건으로 묶인 DB 작업 단위 | [트랜잭션](database/transactions-and-locks.md) |
| MVCC | 여러 버전의 데이터를 이용해 읽기와 변경의 동시성을 다루는 방식 | [트랜잭션](database/transactions-and-locks.md) |
| Deadlock | 작업들이 서로가 보유한 자원을 기다리는 순환 대기 | [트랜잭션](database/transactions-and-locks.md) |
| Execution plan | DB가 선택한 연산과 접근 경로의 구조 | [실행 계획](database/queries-and-indexes.md) |
| WAL | 데이터 페이지의 영속 반영보다 복구 로그를 먼저 기록하는 원리 | [복구](database/replication-and-recovery.md) |
| Quorum | 정한 합의·읽기·쓰기 규칙이 요구하는 참여 수; 의미는 시스템마다 다름 | [분산 DB](database/distributed-and-analytical.md) |
| RPO / RTO | 허용 가능한 데이터 손실의 시간 범위 목표 / 복구 시간의 목표 | [복구](database/replication-and-recovery.md) |
| Acknowledgement | 정한 단계의 수신·처리 확인; 누가 무엇을 확인했는지 명시 필요 | [메시지 큐](middleware/message-queues.md) |
| Shard | 데이터·검색 등의 작업을 나누는 단위; 엔진별 구조는 다름 | [검색](middleware/search-engines.md) |
| RTT | 특정 관측의 왕복 시간 | [TCP](network/tcp-and-udp.md) |
| Retransmission | 데이터를 다시 전송하는 동작; 손실률과 바로 같지는 않음 | [TCP](network/tcp-and-udp.md) |
| NAT | 관측 경계에서 네트워크 주소 등을 변환하는 기능 | [주소](network/addressing-routing-dns.md) |
| MTU | 해당 링크·계층에서 운반 가능한 패킷 크기의 제한 | [MTU](network/layers-and-routing.md) |
| TLS | 전송 구간의 암호화·인증 등을 제공하는 프로토콜 | [TLS](network/tls-http.md) |
| Downsampling | 시간 해상도 등을 줄이도록 원천 자료를 집계·축약하는 과정 | [저장](product/storage-and-query.md) |
| Backpressure | 역압. 처리 가능한 속도에 맞춰 상류 유입을 제어하는 동작 | [Backpressure](middleware/stream-processing.md) |
| Replication lag | 복제 진척 차이. 시간·바이트·위치를 명시하며 NULL은 PG와 MySQL에서 뜻이 다름 | [Replication lag](database/replication-and-recovery.md) |
| Cache eviction | Redis 등에서 한도·정책에 따라 캐시 항목을 제거하는 퇴거 | [Cache eviction](middleware/cache-redis.md) |
| Offset (Kafka) | partition 로그의 위치 식별. 업무 완료와 같은 뜻 아님 | [Offset (Kafka)](middleware/kafka.md) |
| Partition / Consumer group | Kafka 로그의 분할 단위 / partition 소비를 나눠 맡는 구독 집합 | [Partition / Consumer group](middleware/kafka.md) |
| ISR | leader 자신도 포함하는 Kafka 동기 상태 replica 집합 | [ISR](middleware/kafka.md) |
| Prefetch / Dead letter | 확인 전 전달량 제한 / 정한 실패·만료 조건의 메시지를 다른 경로로 보내는 처리 | [Prefetch / Dead letter](middleware/message-queues.md) |
| VACUUM / Dead tuple | 불필요한 행 버전을 정리하는 PG 작업 / UPDATE·DELETE로 대체·삭제된 이전 버전; 아직 볼 snapshot이 있으면 회수 불가 | [VACUUM / Dead tuple](database/postgresql-operations.md) |
| Replication slot | 복제 소비자가 필요로 하는 WAL·회수 기준점 등을 유지하는 PG 상태 | [Replication slot](database/postgresql-operations.md) |
| LSN | WAL 안의 로그 위치를 나타내는 값 | [LSN](database/replication-and-recovery.md) |
| Standby feedback | standby의 `hot_standby_feedback`(기본 off)을 켜 필요한 행 버전의 기준을 primary 또는 upstream standby에 알리는 PG 기능 | [Standby feedback](database/postgresql-operations.md) |
| 격리 수준 | 동시 트랜잭션 사이에 보이는 변경과 허용되는 현상을 정하는 규약 | [격리 수준](database/transactions-and-locks.md) |
| 일관 읽기 / 잠금 읽기 | snapshot의 버전을 보는 읽기 / 필요한 잠금을 함께 획득하는 읽기; 엔진별 확인 | [일관 읽기 / 잠금 읽기](database/transactions-and-locks.md) |
| Relay log | MySQL receiver가 받은 source 로그를 replica에 보관하는 중간 로그 | [Relay log](database/mysql-operations.md) |
| Receiver / Applier | 복제 변경을 수신 / 적용하는 역할. 병렬 applier는 coordinator와 worker로 나뉨 | [Receiver / Applier](database/mysql-operations.md) |
| Redo log / Binary log | InnoDB 복구 로그 / MySQL 서버의 변경 기록; 목적과 완료 경계가 다름 | [Redo log / Binary log](database/mysql-operations.md) |
| Group commit | 여러 트랜잭션의 로그 동기화 등을 묶어 수행하는 처리 | [Group commit](database/mysql-operations.md) |
| Seconds_Behind_Source | MySQL의 복제 지연 추정값; NULL과 0·실제 진척을 구분 | [Seconds_Behind_Source](database/mysql-operations.md) |
| XID (PostgreSQL) | 트랜잭션 ID. age는 시각이 아니라 ID 공간의 거리 | [XID (PostgreSQL)](database/postgresql-operations.md) |
| ADR / DMV / AG | SQL Server 빠른 복구 기능 / 동적 관리 view / 가용성 그룹 | [ADR / DMV / AG](database/sqlserver-oracle.md) |
| Checkpoint (DB) | 복구의 기준이 되는 상태를 정리·기록하는 과정; 모든 DB에서 같은 저장 장벽은 아님 | [Checkpoint (DB)](storage/write-path-and-durability.md) |
| Checkpoint (스트림) | 복구할 처리 상태와 진행 위치를 정한 방식으로 보존하는 지점 | [Checkpoint (스트림)](middleware/stream-processing.md) |
| Compaction (DB 엔진) | 저장 구조를 병합·정리하는 작업; 엔진별 의미 확인 | [Compaction (DB 엔진)](database/specialized-data-models.md) |
| Compaction (etcd) | 오래된 revision 이력을 정리하는 작업; 최신 객체 삭제와 다름 | [Compaction (etcd)](kubernetes/inventory-consistency.md) |
| Raft / etcd | 복제 로그의 합의 알고리즘 / Kubernetes 등이 사용하는 분산 key-value 저장소 | [Raft / etcd](foundations/distributed-systems.md) |

## 시스템을 처음 배울 때

| 용어 | 의미와 구분 | 상세 |
| --- | --- | --- |
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

| 용어 | 의미와 구분 | 상세 |
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
| Fsync | 파일 변경을 저장 장치에 동기화하도록 요청하는 시스템 호출 | [Fsync](storage/write-path-and-durability.md) |
| Flow / IPFIX | 정한 키·시간 경계로 묶은 통신 흐름 / 흐름 정보를 내보내는 규약 | [Flow / IPFIX](network/network-metrics.md) |
| TTFB | 첫 응답 byte까지의 시간. 이 책 curl 예시에서는 time_starttransfer | [TTFB](network/tls-http.md) |
| SNI | TLS 연결에서 접속하려는 서버 이름을 전달하는 확장 | [SNI](network/tls-http.md) |
| DR / BDR | OSPF의 지정 라우터 / 예비 지정 라우터 | [DR / BDR](network/routing-convergence-and-qos.md) |
| 2-Way / Full | OSPF 양방향 이웃 확인 / 인접 라우터와 DB 동기화를 마친 상태 | [2-Way / Full](network/routing-convergence-and-qos.md) |
| OSD / PG (Ceph) | 객체 저장 daemon / 객체 배치·복구를 관리하는 묶음 | [OSD / PG (Ceph)](storage/capacity-and-protection.md) |
| WWID | 여러 경로가 같은 저장 장치를 가리키는지 식별하는 값 | [WWID](storage/raid-lvm-and-paths.md) |
| MSS | TCP 세그먼트의 데이터 부분 최대 크기. IP·TCP header를 제외 | [MSS](network/layers-and-routing.md) |

## 제어·복구·데이터 진행

| 용어 | 의미와 구분 | 상세 |
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
| Quota | 자원 또는 작업에 적용되는 사용 한도와 그 범위 | [클라우드](cloud/quotas-cost-and-capacity.md) |
| Churn | 관측 대상·series가 생성·교체되는 빈도 또는 현상 | [제품 용량](product/capacity-and-loss-budgets.md) |
| Tenant | 제품에서 접근·데이터 소유 범위를 나누는 구획 | [Tenant](product/self-observation-and-access.md) |
| Pending / Firing | 알림 조건이 성립해 유지 시간을 기다림 / 유지 조건을 충족한 알림 상태 | [Pending / Firing](product/alerts-and-incidents.md) |
| Silence | 정한 matcher·시간 범위에서 알림 통지를 억제하는 설정 | [Silence](product/alerts-and-incidents.md) |

## 측정·동시성·전송을 읽는 용어

| 용어 | 의미와 구분 | 상세 |
| --- | --- | --- |
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

| 용어 | 의미와 구분 | 상세 |
| --- | --- | --- |
| Adjusted count | 알려진 포함 확률의 역수인 추정 가중치; 실제 건수의 확정값 아님 | [Sampling 확률](application/trace-sampling-and-context.md) |
| Semantic conventions | 지표·속성 등의 이름·단위·의미를 공유하는 규약 | [안정 이름](application/semantic-conventions.md) |
| CurrEstab / RetransSegs | 현재 TCP 연결 gauge / namespace의 누적 재전송 세그먼트 계정 | [Linux 스택](network/linux-stack-counters.md) |
| RTO / cwnd | TCP 재전송 timeout / 혼잡 윈도; 복구 목표 RTO와 다른 문맥 | [소켓 통계](network/linux-stack-counters.md) |
| Pod QoS class | 자원 명세에 따른 Guaranteed·Burstable·BestEffort 분류; 네트워크 QoS와 구분 | [압박과 종료](kubernetes/pressure-and-termination.md) |
| Freeze / XID age | 오래된 행 XID를 정리하는 처리 / ID 공간의 거리; 경과 초와 다름 | [PostgreSQL 운영](database/postgresql-operations.md) |
| MultiXact | 여러 transaction의 행 잠금 구성원을 가리키는 별도 ID 체계 | [PostgreSQL 운영](database/postgresql-operations.md) |
| xmin horizon | 아직 필요한 행 버전의 회수를 막는 기준점; slot의 WAL 위치와 구분 | [회수 기준점](database/postgresql-operations.md) |
| Prepared transaction | 2단계 commit의 준비 상태로 남은 transaction; prepared statement와 다름 | [PostgreSQL 운영](database/postgresql-operations.md) |
| Share group | Kafka 레코드를 획득·확인·재전달하는 소비 모델; consumer group offset과 다른 진행 모델 | [Kafka](middleware/kafka.md) |
| FLUSH / FUA | 장치 캐시의 선행 쓰기 반영 / 해당 쓰기의 지속성 완료를 요청하는 동작 | [쓰기 경로](storage/write-path-and-durability.md) |
| PMTUD / DPLPMTUD | 경로 MTU 탐색 / datagram packetization layer의 MTU 탐색 | [MTU](network/layers-and-routing.md) |
| Time grain / Ingestion delay | 집계 구간 크기 / 측정 후 조회 가능해지기까지의 지연 | [Cloud 시간 축](cloud/provider-metrics.md) |

## 회수·분포 저장·엔진 내부를 읽는 용어

| 용어 | 의미와 구분 | 상세 |
| --- | --- | --- |
| Reclaim / Refault | 페이지 회수 / 밀려났던 페이지의 재참조; 회수량·재읽기와 지연 시간을 구분 | [회수·OOM](host/reclaim-and-oom.md) |
| Direct reclaim / kswapd | 할당 경로의 직접 회수 / 백그라운드 회수 | [회수·OOM](host/reclaim-and-oom.md) |
| Memcg OOM | memory cgroup의 제약 범위에서 발생한 OOM; kubelet eviction과 별개 | [회수·OOM](host/reclaim-and-oom.md) |
| PSI trigger | window 안의 stall 조건을 fd로 감시하는 커널 모니터 등록 | [PSI](host/numa-and-pressure.md) |
| RssAnon / RssFile / RssShmem | 익명·파일·공유 메모리의 상주량 분류; 정밀도·포함 범위 확인 | [프로세스](host/processes.md) |
| Next-key / Gap lock | 인덱스 레코드와 앞 구간의 잠금 / 삽입할 빈 구간을 보호하는 잠금 | [MySQL 운영](database/mysql-operations.md) |
| GTID | 복제 트랜잭션 식별자; wall clock 또는 모든 source의 단일 순번이 아님 | [MySQL 운영](database/mysql-operations.md) |
| RCSI / PVS | row versioning 기반 READ COMMITTED / ADR의 persistent version store | [SQL Server](database/sqlserver-oracle.md) |
| ASH / AWR | Oracle 활성 세션 표본 이력 / 성능 통계 이력; 사용 권리 확인 필요 | [Oracle](database/sqlserver-oracle.md) |
| JFR / EventPipe | JVM 이벤트 기록 / .NET 진단 이벤트 전달 경로 | [런타임](application/managed-runtimes.md) |
| ELU | 이벤트 루프 active/idle 기준의 사용 비율; OS CPU 사용률과 다름 | [Node](application/async-runtimes.md) |
| Chunk / Record | 로그 전송·재시도의 묶음 / 개별 기록; 줄 수와도 구분 | [로그 전달](product/collection-pipelines.md) |
| SM / Warp / Occupancy | GPU 실행 단위 / 실행 스레드 묶음 / 최대 대비 resident warp 점유 | [GPU](host/gpu.md) |

**동음이의 주의:** `namespace`는 [Linux 격리](containers/isolation-and-lifecycle.md), [Kubernetes 객체 범위](kubernetes/objects-and-control-loops.md), [CloudWatch 지표 이름 공간](cloud/provider-metrics.md)에서 뜻이 다릅니다. `commit`도 [Windows 메모리 제공 약속](host/windows.md), [DB transaction 완료](database/transactions-and-locks.md), [Kafka 소비 위치 저장](middleware/kafka.md)을 구분합니다. `active`, `used`, `lag` 역시 원천·대상·단위·완료 경계를 붙여 읽습니다.

같은 이름도 원천에 따라 뜻이 다릅니다. 용어 정의는 학습용 요약이며 실제 판정은 연결된 장의 버전·조건·원천을 따릅니다.

이전: [모니터링 제품의 용량과 손실 예산](product/capacity-and-loss-budgets.md) · 다음: [단위와 대표 지표의 해석 참조표](metric-catalog.md)
