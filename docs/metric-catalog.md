# 단위와 대표 지표의 해석 참조표

이 표는 실제 exporter의 완전한 필드 목록이 아닙니다. 도메인별 원천 지표를 제품에 연결할 때 검토할 계산·분모·집계의 출발점입니다. 수집기별 정확한 필드명과 권한·버전은 연결된 본문 및 공식 자료를 따릅니다.

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

## 시스템과 실행 환경

| 지표 개념 | 원천·형태 | 계산·집계 시 핵심 | 상세 |
| --- | --- | --- | --- |
| 호스트 CPU 사용 비율 | CPU 상태별 누적 시간 | 포함 상태·CPU 수·구간, guest 중복 확인 | [CPU](host/cpu.md) |
| 프로세스 CPU 사용 | 누적 user·system 시간 | CPU 초/경과 초, 실행 수명별 rate | [CPU](host/cpu.md) |
| 메모리 가용량 | Linux MemAvailable 추정값 | MemFree·heap·commit과 구분 | [메모리](host/memory.md) |
| 프로세스 메모리 | RSS·PSS·private 등 | 공유 페이지 중복과 포함 범위 | [메모리](host/memory.md) |
| Windows 시스템 CPU | 누적 Idle·Kernel·User 시간 | Kernel에 Idle 포함, processor group 범위 | [Windows](host/windows.md) |
| 파일시스템 사용률 | total·free·available | reserved 포함 여부와 분모 정의 | [I/O](host/disk-io.md) |
| IOPS | 완료 I/O 누적 횟수 | read·write·discard 구분, 경계별 split·merge | [I/O](host/disk-io.md) |
| 평균 I/O 지연 | 작업별 시간 누적과 횟수 | 같은 작업 집합의 시간 합/횟수; p99 아님 | [I/O](host/disk-io.md) |
| 인터페이스 전송률 | 누적 byte | 차분/초, reset·wrap, 계층 중복 | [네트워크 지표](network/network-metrics.md) |
| 컨테이너 CPU 한도 대비 | usage 시간과 quota/period | 실제 유효 제한과 호스트 용량을 구분 | [cgroup](containers/resource-control.md) |
| Throttled period 비율 | periods·throttled periods | 제한이 있었던 period 비율; 실패 요청률 아님 | [cgroup](containers/resource-control.md) |
| GPU 활동률 | 원천 정의의 시간 비율 | VRAM 용량·FLOPS 사용률과 구분 | [GPU](host/gpu.md) |
| Pod 재시작 횟수 | 컨테이너별 상태 값 | Pod UID·container 수명·초기화·수집 누락 | [Pod](kubernetes/pod-lifecycle.md) |
| Workload Available | 컨트롤러 상태 | desired·Ready와 구분, minReady 조건 | [객체](kubernetes/objects-and-control-loops.md) |

## 업무 요청과 데이터 시스템

| 지표 개념 | 원천·형태 | 계산·집계 시 핵심 | 상세 |
| --- | --- | --- | --- |
| 요청률 | 정의한 경계의 요청 Counter | 논리 요청·재시도·도착·완료 구분 | [요청](application/requests-and-concurrency.md) |
| 오류율 | 같은 모집단의 실패/전체 | 분자·분모 일치, 0건일 때 미정 처리 | [분포](foundations/distributions.md) |
| 요청 지연 | 개별 시간·Histogram | 측정 경계·sampling·bucket 호환성 | [분포](foundations/distributions.md) |
| 풀 대기 | 획득 전 시간·대기자 수 | DB 내부 실행 시간과 분리 | [요청](application/requests-and-concurrency.md) |
| JVM heap 사용 비율 | used·committed·max | 어느 분모인지 표시, max 미정 가능 | [런타임](application/managed-runtimes.md) |
| GC 시간 | 수집기별 계수·이벤트 | pause wall time과 병렬 worker CPU 구분 | [런타임](application/managed-runtimes.md) |
| DB 쿼리 평균 | 같은 수명의 시간 합/완료 수 | 단위·reset·캐시 퇴거·병렬 실행 포함 | [엔진 통계](database/sqlserver-oracle.md) |
| PostgreSQL 활동 | pg_stat_activity snapshot | active와 wait는 독립; 대기 시간 분율 아님 | [PostgreSQL](database/postgresql.md) |
| MySQL digest 시간 | Performance Schema timer | picosecond 단위, 실제 정밀도와 구분 | [MySQL](database/mysql-mariadb.md) |
| 복제 진척 | 위치 차이·시간·상태 | 송신·수신·flush·apply의 기준 구분 | [복제](database/replication-and-recovery.md) |
| 캐시 적중률 | lookup hits/(hits+misses) | lookup과 사용자 요청 수의 차이 | [Redis](middleware/cache-redis.md) |
| Kafka lag | end와 current·commit 차이 | 기준 위치·격리·partition별 집계 | [Kafka](middleware/kafka.md) |
| RabbitMQ 대기 | ready·unacked | 브로커에서 대기/소비자에게 전달 후 미확인 구분 | [메시지 큐](middleware/message-queues.md) |
| 검색 건강 상태 | shard 배치 상태 | 사용자 쿼리 SLO와 다른 기준 | [검색](middleware/search-engines.md) |
| 클라우드 기간 Sum | API가 집계한 구간 양 | 기간으로 나누기; 다음 Sum과 차분하지 않음 | [공급자 지표](cloud/provider-metrics.md) |
| Lambda 오류율 | Errors/Invocations | throttle로 호출되지 않은 요청의 별도 집계 | [서버리스](cloud/managed-and-serverless.md) |

## 제품 자체와 집계 계약

| 지표 개념 | 계산 또는 보존할 문맥 | 상세 |
| --- | --- | --- |
| 수집 완전성 | 대상 수명을 반영한 기대 관측 대비 확인한 관측 | [자체 관측](product/self-observation-and-access.md) |
| 조회 가능 지연 | 발생·수신·조회 가능 시각, clock 오차 | [데이터 품질](foundations/time-and-data-quality.md) |
| 버퍼 여유 시간 | 남은 byte / 양의 순유입 byte/s | [파이프라인](product/collection-pipelines.md) |
| 적체 해소 예상 | backlog / 양의 순감소율; 일정 조건 명시 | [적체 사례](cross-domain/backlogs-and-retries.md) |
| SLO burn rate | 관측 실패 비율 / 허용 실패 비율 | [SLO](foundations/service-level-objectives.md) |

비율을 여러 대상으로 합칠 때는 분자·분모의 합으로 다시 계산합니다. 누적값은 같은 실행 수명에서 rate를 구한 뒤 합치고, 분포는 원천 분포의 호환성을 확인합니다. 0 분모, reset, 미지원, 누락, 늦은 도착은 모두 정상 숫자와 구분해서 처리해야 합니다.

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
