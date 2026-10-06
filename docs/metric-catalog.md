# 단위와 대표 지표의 해석 참조표

이 표는 실제 exporter의 완전한 필드 목록이 아닙니다. 도메인별 원천 지표를 제품에 연결할 때 검토할 계산·분모·집계의 출발점입니다. 수집기별 정확한 필드명과 권한·버전은 연결된 본문 및 공식 자료를 따릅니다.

필드의 기계 판독 계약은 [필드 카탈로그](../catalog/field-catalog.json), 선택·검증 방법은 [어댑터 계약](product/adapter-contracts.md)에 있습니다. 아래 표는 빠른 탐색용이며 상세 원천·버전·NULL 규약은 각 장을 따릅니다.

## 단위를 먼저 맞춘다

`B`는 byte이고 1 B는 8 bit입니다. 이진 접두어 Ki·Mi·Gi는 각각 2의 10·20·30승을, SI 접두어 k·M·G는 각각 10의 3·6·9승을 나타냅니다. API가 과거 관례의 `KB`를 쓰는 경우 원천 정의를 확인하고 정규화합니다. [NIST binary prefixes](https://physics.nist.gov/cuu/Units/binary.html)

| 표현 | 환산 |
| --- | --- |
| 1 KiB / MiB / GiB | 1,024 B / 1,048,576 B / 1,073,741,824 B |
| 1 MB / GB | 1,000,000 B / 1,000,000,000 B |
| 1 s | 1,000 ms = 1,000,000 µs = 1,000,000,000 ns |
| ratio → percent | 0.25 → 25%; 이미 percent인 25에 다시 100을 곱하지 않음 |
| 100 Mbit/s | 12.5 MB/s; 애플리케이션의 실효 처리량 보장은 아님 |
| CPU-second / second | 평균 사용 CPU 수; 전체 용량 대비 비율에는 CPU 수 분모 필요 |

## 관측과 분포

| 지표·필드 | 단위·종류 | 해석할 경계 | 상세 |
| --- | --- | --- | --- |
| 오류율 | 같은 모집단의 실패/전체 | 분자·분모 일치, 0건일 때 미정 처리 | [분포](foundations/distributions.md) |
| 요청 지연 | 개별 시간·Histogram | 측정 경계·sampling·bucket 호환성 | [분포](foundations/distributions.md) |
| histogram scale/schema·zero threshold | 해상도·원천 단위 경계 | 표본 population·temporality와 함께 보존 | [분포 저장](foundations/histogram-storage.md) |
| chrony System time / Frequency / Skew | s / ppm / ppm | 시각 차이·속도·추정 오차의 다른 축 | [시계](foundations/time-and-data-quality.md) |
| 조회 가능 지연 | 제품별 정의 | 발생·수신·조회 가능 시각, clock 오차 | [데이터 품질](foundations/time-and-data-quality.md) |
| SLO burn rate | 제품별 정의 | 관측 실패 비율 / 허용 실패 비율 | [SLO](foundations/service-level-objectives.md) |
| exemplar | 개별 관측 값·시각·문맥 | 일반 metric label이나 모든 사건의 목록 아님 | [지표 문맥](foundations/metric-context-and-start-time.md) |
| `StartTimeUnixNano` / `_created` | epoch ns / epoch s | 원천 시작·수명 정보; 첫 수집 시각과 다름 | [시작 시각](foundations/metric-context-and-start-time.md) |

## 호스트

| 지표·필드 | 단위·종류 | 해석할 경계 | 상세 |
| --- | --- | --- | --- |
| 호스트 CPU 사용 비율 | CPU 상태별 누적 시간 | 포함 상태·CPU 수·구간, guest 중복 확인 | [CPU](host/cpu.md) |
| 프로세스 CPU 사용 | 누적 user·system 시간 | CPU 초/경과 초, 실행 수명별 rate | [CPU](host/cpu.md) |
| 메모리 가용량 | Linux MemAvailable 추정값 | MemFree·heap·commit과 구분 | [메모리](host/memory.md) |
| 프로세스 메모리 | RSS·PSS·private 등 | 공유 페이지 중복과 포함 범위 | [메모리](host/memory.md) |
| Windows 시스템 CPU | 누적 Idle·Kernel·User 시간 | Kernel에 Idle 포함, processor group 범위 | [Windows](host/windows.md) |
| 파일시스템 사용률 | total·free·available | reserved 포함 여부와 분모 정의 | [I/O](host/disk-io.md) |
| IOPS | 완료 I/O 누적 횟수 | read·write·discard 구분, 경계별 split·merge | [I/O](host/disk-io.md) |
| 평균 I/O 지연 | 작업별 시간 누적과 횟수 | 같은 작업 집합의 시간 합/횟수; p99 아님 | [I/O](host/disk-io.md) |
| GPU 활동률 | 원천 정의의 시간 비율 | VRAM 용량·FLOPS 사용률과 구분 | [GPU](host/gpu.md) |
| vmstat `pgscan_*`, `pgsteal_*` | 누적 페이지 | 회수 경로별 비교; anon/file 분류와 중복 합산 금지 | [회수](host/reclaim-and-oom.md) |
| `allocstall_*`, `oom_kill` | 누적 사건 계수 | 대기 초·전역 OOM 사건 수로 변환 금지 | [OOM](host/reclaim-and-oom.md) |
| `workingset_refault_*`, `pswpin/out` | 누적 페이지 | refault·swap 활동, 현재 점유량과 다름 | [회수](host/reclaim-and-oom.md) |
| PSI total / avg10·60·300 | µs 누적 / % | 시스템·cgroup 범위, 시스템 CPU full의 무효 0 | [PSI](host/numa-and-pressure.md) |
| VmRSS·RssAnon/File/Shmem·VmSwap | kB(×1024) | 비동기 RSS 추정, VmSwap은 shmem swap 제외 | [프로세스](host/processes.md) |
| statm resident / shared | 페이지 | shared는 실제 공유자 수가 아닌 file+shmem 분류 | [프로세스](host/processes.md) |
| DCGM SM_ACTIVE·SM_OCCUPANCY·tensor·DRAM | ratio | 각 하드웨어 활동 분모; NVML utilization과 구분 | [GPU](host/gpu.md) |
| Clock event reason / duration | bitmask / API별 시간 | 활성 조건과 누적 시간 구분, nvidia-smi µs·NVML 필드 ns 확인 | [GPU](host/gpu.md) |
| Windows Processor Time / Utility | % | 점유 시간 / 성능 상태 보정; 100% 상한 가정 금지 | [Windows](host/windows.md) |

## 컨테이너

| 지표·필드 | 단위·종류 | 해석할 경계 | 상세 |
| --- | --- | --- | --- |
| 컨테이너 CPU 한도 대비 | usage 시간과 quota/period | 실제 유효 제한과 호스트 용량을 구분 | [cgroup](containers/resource-control.md) |
| Throttled period 비율 | periods·throttled periods | 제한이 있었던 period 비율; 실패 요청률 아님 | [cgroup](containers/resource-control.md) |

## Kubernetes

| 지표·필드 | 단위·종류 | 해석할 경계 | 상세 |
| --- | --- | --- | --- |
| Pod 재시작 횟수 | 컨테이너별 상태 값 | Pod UID·container 수명·초기화·수집 누락 | [Pod](kubernetes/pod-lifecycle.md) |
| Workload Available | 컨트롤러 상태 | desired·Ready와 구분, minReady 조건 | [객체](kubernetes/objects-and-control-loops.md) |
| eviction `memory.available` | byte·capacity 비율 | capacity−node working set; MemAvailable과 구분; 1.37 HugepageAwareEviction 적용 Summary의 hugepage 보정값을 다시 차감하지 않음 | [Kubernetes 압박](kubernetes/pressure-and-termination.md) |
| `memory.events.oom_group_kill` | group OOM 횟수 | 종료 프로세스 수·재시작 수와 다름 | [memory.events](containers/memory-accounting-and-oom.md) |
| `containerStatuses[].resources` | CPU·memory 자원 명세 | spec 희망값과 실제 적용 분모 구분 | [resize](kubernetes/pressure-and-termination.md) |

## 네트워크

| 지표·필드 | 단위·종류 | 해석할 경계 | 상세 |
| --- | --- | --- | --- |
| 인터페이스 전송률 | 누적 byte | 차분/초, reset·wrap, 계층 중복 | [네트워크 지표](network/network-metrics.md) |
| `Tcp.CurrEstab` | 연결 수 gauge | ESTABLISHED·CLOSE-WAIT, namespace 단위; CLOSE-WAIT 포함은 Linux 6.10 변경·backport 적용 여부 확인 | [Linux 스택](network/linux-stack-counters.md) |
| `Tcp.RetransSegs / Tcp.OutSegs`의 구간 차분 비 | ratio 또는 % | 제어·반복 전송 포함 범위; 손실률 아님 | [Linux 스택](network/linux-stack-counters.md) |
| `Udp.InErrors`, `Udp.RcvbufErrors` | 누적 횟수 | 겹치는 실패를 합산하지 않음 | [Linux 스택](network/linux-stack-counters.md) |
| `TcpExt.ListenOverflows/ListenDrops` | 누적 횟수 | 대기열·LISTEN 경로; 같은 drop이 겹칠 수 있음 | [Linux 스택](network/linux-stack-counters.md) |
| 인증서 `notAfter−현재 시각` | 남은 초·일 | 발급일별 BR 한도·갱신·배포 상태 확인 | [TLS](network/tls-http.md) |
| SNMP `ifSpeed` / `ifHighSpeed` | bit/s / 백만 bit/s | Gauge32 포화와 속도 분모 | [SNMP](network/snmp-and-device-models.md) |

## 애플리케이션

| 지표·필드 | 단위·종류 | 해석할 경계 | 상세 |
| --- | --- | --- | --- |
| 요청률 | 정의한 경계의 요청 Counter | 논리 요청·재시도·도착·완료 구분 | [요청](application/requests-and-concurrency.md) |
| 풀 대기 | 획득 전 시간·대기자 수 | DB 내부 실행 시간과 분리 | [요청](application/requests-and-concurrency.md) |
| JVM heap 사용 비율 | used·committed·max | 어느 분모인지 표시, max 미정 가능 | [런타임](application/managed-runtimes.md) |
| GC 시간 | 수집기별 계수·이벤트 | pause wall time과 병렬 worker CPU 구분 | [런타임](application/managed-runtimes.md) |
| BufferPool MemoryUsed / TotalCapacity | byte 추정 | capacity·상주량·실제 할당량 구분, −1 처리 | [JVM](application/managed-runtimes.md) |
| ELU active·idle / loop delay | ms / ns | CPU 사용률 아님, Node 표본 모드 보존 | [Node](application/async-runtimes.md) |
| `http.server.request.duration` | Histogram, s, Stable | 구 ms 규약과 변환·중복 제거 | [안정 이름](application/semantic-conventions.md) |
| `jvm.memory.used/committed/limit` | UpDownCounter, By, Stable | used·확보·최대·미정 분모 | [JVM 규약](application/semantic-conventions.md) |
| `jvm.gc.duration` / `dotnet.gc.pause.time` | Histogram s / Counter s, Stable | GC action 분포 / 누적 정지 시간 | [런타임 규약](application/semantic-conventions.md) |

## 데이터베이스

| 지표·필드 | 단위·종류 | 해석할 경계 | 상세 |
| --- | --- | --- | --- |
| DB 쿼리 평균 | 같은 수명의 시간 합/완료 수 | 단위·reset·캐시 퇴거·병렬 실행 포함 | [엔진 통계](database/sqlserver-oracle.md) |
| PostgreSQL 활동 | pg_stat_activity snapshot | active와 wait는 독립; 대기 시간 분율 아님 | [PostgreSQL](database/postgresql.md) |
| MySQL digest 시간 | Performance Schema timer | picosecond 단위, 실제 정밀도와 구분 | [MySQL](database/mysql-mariadb.md) |
| 복제 진척 | 위치 차이·시간·상태 | 송신·수신·flush·apply의 기준 구분 | [복제](database/replication-and-recovery.md) |
| `Seconds_Behind_Source` | 초 또는 NULL | receiver/applier 상태와 NULL 조건; 0도 freshness 보장 아님 | [MySQL](database/mysql-operations.md) |
| worker·receiver commit/queue/apply timestamp | µs 정밀도 시각 | 서버별 시계와 원본/직전 source·단계 구분 | [MySQL](database/mysql-operations.md) |
| AG send/redo queue | KB gauge | 아직 미전송 / 수신했지만 미redo; 지연 초와 다름 | [SQL Server](database/sqlserver-oracle.md) |
| version store reserved_space_kb | KB gauge | tempdb 집계이며 ADR PVS 전체를 대체하지 않음 | [SQL Server](database/sqlserver-oracle.md) |
| `age(datfrozenxid)`, `mxid_age(datminmxid)` | 각각 XID·MultiXact 거리 | 초·실행 SQL 수 아님; 별도 한도 | [PostgreSQL 운영](database/postgresql-operations.md) |
| slot `xmin`·`catalog_xmin`, sender `backend_xmin` | ID·age | 행 보존·catalog 보존·feedback; LSN과 구분 | [회수 기준점](database/postgresql-operations.md) |
| `pg_stat_io.read_bytes/write_bytes` | PostgreSQL 18 누적 byte | 16–17 reads×op_bytes와 분기; 18 reads는 블록 수가 아닌 요청 수 | [통계 호환성](database/postgresql-operations.md) |

## 미들웨어

| 지표·필드 | 단위·종류 | 해석할 경계 | 상세 |
| --- | --- | --- | --- |
| 캐시 적중률 | lookup hits/(hits+misses) | lookup과 사용자 요청 수의 차이 | [Redis](middleware/cache-redis.md) |
| Kafka lag | end와 current·commit 차이 | 기준 위치·격리·partition별 집계 | [Kafka](middleware/kafka.md) |
| RabbitMQ 대기 | ready·unacked | 브로커에서 대기/소비자에게 전달 후 미확인 구분 | [메시지 큐](middleware/message-queues.md) |
| 검색 건강 상태 | shard 배치 상태 | 사용자 쿼리 SLO와 다른 기준 | [검색](middleware/search-engines.md) |
| HAProxy qcur·scur / ereq·econ·eresp·hrsp_5xx | 현재 수 / 누적 수 | 요청·세션·처리 오류·HTTP 응답 분류 | [프록시](middleware/proxies-and-mesh.md) |
| Kafka UnderReplicated·UnderMinIsr | partition 수 gauge | RF 대비 / min ISR 미만을 구분 | [Kafka](middleware/kafka.md) |

## 클라우드

| 지표·필드 | 단위·종류 | 해석할 경계 | 상세 |
| --- | --- | --- | --- |
| 클라우드 기간 Sum | API가 집계한 구간 양 | 기간으로 나누기; 다음 Sum과 차분하지 않음 | [공급자 지표](cloud/provider-metrics.md) |
| Lambda 오류율 | Errors/Invocations | throttle로 호출되지 않은 요청의 별도 집계 | [서버리스](cloud/managed-and-serverless.md) |
| CloudWatch `Errors` (Lambda) | 기간별 오류 수 | 호출 시작 시각 귀속, 완료 시각 아님 | [서버리스](cloud/managed-and-serverless.md) |

## 수집 제품

| 지표·필드 | 단위·종류 | 해석할 경계 | 상세 |
| --- | --- | --- | --- |
| Fluent Bit retries_failed / dropped_records | chunk / record 누적 | retry 횟수·버린 record 수·fan-out 구분 | [로그](product/collection-pipelines.md) |
| 수집 완전성 | 제품별 정의 | 대상 수명을 반영한 기대 관측 대비 확인한 관측 | [자체 관측](product/self-observation-and-access.md) |
| 버퍼 여유 시간 | 제품별 정의 | 남은 byte / 양의 순유입 byte/s | [파이프라인](product/collection-pipelines.md) |
| 적체 해소 예상 | 제품별 정의 | backlog / 양의 순감소율; 일정 조건 명시 | [적체 사례](cross-domain/backlogs-and-retries.md) |
| Collector `otelcol_exporter_send_failed_spans_total` 등 | 실패한 signal 항목 수 | 기본 Prometheus counter 접미사 `_total`; 실습은 접미사 비활성. exporter 최종 실패 계정이며 retry 시도·부분 거절 수와 다름 | [전송 계약](product/telemetry-delivery-contracts.md) |

## 비슷한 이름이 다른 값을 뜻하는 경우

| 비교 대상 | 구분해야 하는 경계 | 상세 |
| --- | --- | --- |
| 5초 CPU 평균 / 1분 CPU 평균 | 같은 작업도 시간 창이 다르면 값이 다름 | [측정과 비교](foundations/measurement-and-comparability.md) |
| rchar / read_bytes | 프로그램의 논리 읽기 / 저장 계층의 읽기 계정 | [실제 I/O 관측](host/linux-observation-lab.md) |
| Heap / RSS / memory.current / WorkingSet | 런타임·프로세스·cgroup·도구 계산의 포함 범위 | [메모리 계정](containers/memory-accounting-and-oom.md) |
| DB active / CPU 실행 | active인 SQL이 잠금을 기다릴 수 있음 | [실제 잠금 대기](database/postgresql-concurrency-lab.md) |
| 요청 오류율 / 보존한 trace의 오류 비율 | sampling 전후 모집단 | [Sampling](application/trace-sampling-and-context.md) |
| HTTP 요청 수 / TCP 연결 수 | 재사용·다중화 여부 | [연결 실습](network/dns-and-connection-lifecycle.md) |
| HTTP 200 수 / 본문 완료 수 | 헤더 도착과 본문 전송 완료 | [불완전 응답](network/dns-and-connection-lifecycle.md) |
| Span 전송 항목 수 / 고유 수신 항목 수 | 응답 유실 후 중복 재시도 | [OTLP 전송](product/telemetry-delivery-contracts.md) |
| 같은 구간의 첫 Sum / 재조회 Sum | 같은 집계의 갱신인지 독립된 증가량인지 | [Cloud 재조회](cloud/late-data-and-reconciliation.md) |
| Write 지연 / fsync 지연 / commit 지연 | 반환·동기화·트랜잭션 정책의 완료 경계 | [쓰기 지속성](storage/write-path-and-durability.md) |

실제 필드별 명세는 [지표 템플릿](../templates/metric.md)에 원천 URL·버전·단위·수집 권한·검증 결과를 채워 작성합니다. [필드 계약과 수용 기준](product/compatibility-and-acceptance.md)의 19개 항목은 원천 값에서 제품 지표까지 연결하는 구체적인 예입니다.

이전: [통합 모니터링 용어집](glossary.md) · 다음: [제1.2판의 분야별 범위](coverage.md)
