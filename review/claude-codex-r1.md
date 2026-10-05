# Claude–Codex 교차 검토 1차 판정과 수정

기준: 2026-10-04, `6aea2ed` 제1.1판. 작업 브랜치 `review/claude-codex-r1`. 판 번호·book.json 기준일·기존 실험 원시 JSON을 유지했습니다. commit·push·branch 전환은 수행하지 않았습니다. 1b에서는 Claude가 실행한 Linux 시계 진단 JSON을 별도 출판하고 원시값·실행기 hash·계산을 확인했습니다. 전달된 HTML 화면 검사는 당시 통합본과 hash가 일치했으며, 이후 재생성본의 화면 검사 적용 범위는 아래에 따로 기록합니다.

## 1. 항목별 판정

C의 세부 식별자는 이 응답에서 구분하기 위해 붙였습니다. 표의 파일 외에 BOOK.md·BOOK.html, 장별 검토 hash와 URL 조회 기록도 함께 갱신합니다.

| ID | 판정 | 직접 확인한 근거·결론 | 바꾼 파일 |
| --- | --- | --- | --- |
| A1 | 부분 수용 | 보존한 재실행 JSON에서 단일 스레드 busy의 프로세스 CPU clock/RAW는 약 0.99992–0.99995, MONOTONIC/RAW는 약 0.937. sleep·idle의 시계 차이와 adjtimex 값도 부합하므로 이 재실행의 CPU/MONOTONIC > 1은 분모의 주파수 조정으로 설명된다. RAW·tick이 없는 과거 1.06 표본의 원인, 조정 주체와 RAW의 외부 정확도는 확정하지 않는다. [보존한 재실행](../labs/results/1.1-linux-clock-r1.json). [시계 규약](https://man7.org/linux/man-pages/man2/clock_gettime.2.html) [adjtimex modes=0](https://man7.org/linux/man-pages/man2/adjtimex.2.html) [Linux 6.12 ntp_update_frequency·ADJ_TICK](https://github.com/torvalds/linux/blob/v6.12/kernel/time/ntp.c) [glibc x86_64 timex ABI](https://github.com/bminor/glibc/blob/glibc-2.39/sysdeps/unix/sysv/linux/bits/timex.h) | [scripts/run_linux_lab.py](../scripts/run_linux_lab.py)<br>[labs/archive/run_linux_lab_1_1.py](../labs/archive/run_linux_lab_1_1.py)<br>[scripts/verify_revision.py](../scripts/verify_revision.py)<br>[scripts/verify_review_r1.py](../scripts/verify_review_r1.py)<br>[review/evidence-provenance.json](../review/evidence-provenance.json)<br>[docs/host/linux-observation-lab.md](../docs/host/linux-observation-lab.md)<br>[docs/host/collection-contracts.md](../docs/host/collection-contracts.md)<br>[docs/foundations/time-and-data-quality.md](../docs/foundations/time-and-data-quality.md)<br>[docs/foundations/measurement-and-comparability.md](../docs/foundations/measurement-and-comparability.md)<br>[docs/review.md](../docs/review.md)<br>[docs/validation.md](../docs/validation.md)<br>[review/fact-review-1.1.json](../review/fact-review-1.1.json)<br>[README.md](../README.md)<br>[labs/results/1.1-linux-clock-r1.json](../labs/results/1.1-linux-clock-r1.json) |
| A2 | 수용 | 7개 시나리오 전체 watch cache off를 명시. selector 이탈은 etcd와 cache 경로 둘 다 Deleted 분기가 있음. cache on은 코드 대조만 했으며 미보존 예비 200·ListFromCacheSnapshot 인과는 근거에서 제외. [etcd watcher L617–634](https://github.com/kubernetes/kubernetes/blob/v1.34.1/staging/src/k8s.io/apiserver/pkg/storage/etcd3/watcher.go#L617-L634) [cache watcher L374–397](https://github.com/kubernetes/kubernetes/blob/v1.34.1/staging/src/k8s.io/apiserver/pkg/storage/cacher/cache_watcher.go#L374-L397) | [docs/kubernetes/inventory-consistency.md](../docs/kubernetes/inventory-consistency.md)<br>[docs/review.md](../docs/review.md)<br>[docs/validation.md](../docs/validation.md)<br>[review/fact-review-1.1.json](../review/fact-review-1.1.json) |
| A3 | 수용 | run_otel_lab.py의 logs:error·metrics:none 확인. 목적지 요청·receiver 응답만 근거이며 내부 거절 인지·계수는 관측되지 않음.  | [docs/product/telemetry-delivery-contracts.md](../docs/product/telemetry-delivery-contracts.md)<br>[docs/validation.md](../docs/validation.md)<br>[review/fact-review-1.1.json](../review/fact-review-1.1.json) |
| B1 | 수용 | db-0에는 앞 Pod가 없음. 기본 OrderedReady의 다음 신규 Pod는 앞 Pod Running·Ready까지 미생성. Pending과 구분. [StatefulSet 보장](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/#deployment-and-scaling-guarantees) | [docs/kubernetes/workloads-and-control-plane.md](../docs/kubernetes/workloads-and-control-plane.md) |
| B2 | 수용 | 0.137.0 base_exporter L66–102: queue→obs→retry→timeout→pusher. obs Send/endOp L86–138은 내부 retry 반환 뒤 failed 항목 수 계수. 같은 retry의 중간 실패 횟수가 아님. 일반 안내의 의도를 상류 재전송 하나로 한정하지 않음. [base_exporter](https://github.com/open-telemetry/opentelemetry-collector/blob/v0.137.0/exporter/exporterhelper/internal/base_exporter.go#L66-L102) [obs_report_sender](https://github.com/open-telemetry/opentelemetry-collector/blob/v0.137.0/exporter/exporterhelper/internal/obs_report_sender.go#L86-L138) [queue_sender L42](https://github.com/open-telemetry/opentelemetry-collector/blob/v0.137.0/exporter/exporterhelper/internal/queue_sender.go#L38-L49) | [docs/product/telemetry-delivery-contracts.md](../docs/product/telemetry-delivery-contracts.md) |
| B3 | 수용 | 6.12 diskstats_show의 4·8·10·11·15·17은 32bit unsigned ms. 2^32 ms≈49.71 누적 일이며 병렬 합계는 실제 시간이 더 짧을 수 있음. 감소를 reset이 아닌 decrease로 분리; 증거 없는 modulo 복원은 구현하지 않음. [필드 유형](https://docs.kernel.org/admin-guide/iostats.html) [diskstats_show L1239–1300](https://github.com/torvalds/linux/blob/v6.12/block/genhd.c#L1239-L1300) | [docs/host/collection-contracts.md](../docs/host/collection-contracts.md)<br>[docs/host/disk-io.md](../docs/host/disk-io.md)<br>[docs/product/adapter-contracts.md](../docs/product/adapter-contracts.md)<br>[scripts/adapter_contract.py](../scripts/adapter_contract.py)<br>[scripts/verify_contracts.py](../scripts/verify_contracts.py)<br>[scripts/verify_review_r1.py](../scripts/verify_review_r1.py) |
| B4 | 수용 | 회수 horizon에 일반 세션 외 prepared transaction, slot xmin/catalog_xmin, hot_standby_feedback을 포함. catalog_xmin의 catalog 범위 구분. [PostgreSQL 18 VACUUM](https://www.postgresql.org/docs/18/routine-vacuuming.html#VACUUM-FOR-WRAPAROUND) [feedback](https://www.postgresql.org/docs/18/runtime-config-replication.html#GUC-HOT-STANDBY-FEEDBACK) | [docs/database/transactions-and-locks.md](../docs/database/transactions-and-locks.md)<br>[docs/database/postgresql.md](../docs/database/postgresql.md) |
| B5 | 수용 | NextToken은 MetricDataResult가 아닌 GetMetricData 응답 최상위. 결과별 완전성과 요청 pagination을 분리. [GetMetricData](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_GetMetricData.html) [MetricDataResult](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_MetricDataResult.html) | [docs/cloud/late-data-and-reconciliation.md](../docs/cloud/late-data-and-reconciliation.md)<br>[review/fact-review-1.1.json](../review/fact-review-1.1.json) |
| B6 | 수용 | 동시성 모델의 평균 시간은 요청의 환경 점유 시간. 요청에 귀속되는 Init 포함, 미리 준비된 환경의 유휴 시간을 요청마다 더하지 않음. [Lambda concurrency](https://docs.aws.amazon.com/lambda/latest/dg/lambda-concurrency.html) | [docs/cloud/managed-and-serverless.md](../docs/cloud/managed-and-serverless.md) |
| B7 | 수용 | xNAME 체인의 RCODE는 최종 query cycle 기준. 최초 이름·체인·최종 이름을 함께 보존. [RFC 6604 §3](https://www.rfc-editor.org/rfc/rfc6604.html#section-3) | [docs/network/addressing-routing-dns.md](../docs/network/addressing-routing-dns.md)<br>[docs/network/dns-and-connection-lifecycle.md](../docs/network/dns-and-connection-lifecycle.md) |
| B8 | 수용 | account_user_time의 task_nice(p)>0 분기가 nice, 그 외 user. 음수 nice도 user. [Linux 6.12 account_user_time](https://github.com/torvalds/linux/blob/v6.12/kernel/sched/cputime.c#L119-L133) | [docs/host/cpu.md](../docs/host/cpu.md) |
| B9 | 수용 | Cached에 tmpfs/shmem 포함, SwapCached 제외. Shmem 별도 수집과 중복 주의. 살아 있는 내용은 깨끗한 파일 캐시처럼 그냥 버릴 수 없음. [Linux meminfo](https://docs.kernel.org/filesystems/proc.html#meminfo) | [docs/host/memory.md](../docs/host/memory.md) |
| B10 | 수용 | Executor가 연결된 connector의 maxThreads는 무시되고 JMX 등에 -1로 보고. [Tomcat 10.1 maxThreads](https://tomcat.apache.org/tomcat-10.1-doc/config/http.html) | [docs/application/servers-and-pools.md](../docs/application/servers-and-pools.md) |
| B11 | 수용 | quorum queue는 global QoS prefetch 미지원. 해당 channel의 consume은 channel error. [RabbitMQ global QoS](https://www.rabbitmq.com/docs/quorum-queues#global-qos) | [docs/middleware/message-queues.md](../docs/middleware/message-queues.md) |
| B12 | 부분 수용 | clock_timestamp는 문장 내에서도 달라지며 기존 결과 3행 시각도 다름. SQL·실행 hash는 유지하고 collected_at을 행별 평가 시각으로 명세. 문장 공통 시작 시각이 목적이면 statement_timestamp. [PostgreSQL 18 시각 함수](https://www.postgresql.org/docs/18/functions-datetime.html#FUNCTIONS-DATETIME-CURRENT) | [docs/database/collection-contracts.md](../docs/database/collection-contracts.md) |
| B13 | 수용 | Brewer2.pdf는 2012 회고. 2002 원 논문으로 연결하고 non-failing node의 모든 요청이라는 가용성 정의, Theorem 1·2 모델을 구분. [2002 원 논문 §2·Theorem 1–2](https://sites.cs.ucsb.edu/~rich/class/cs293b-cloud/papers/cap-proof.pdf) [2012 회고](https://groups.csail.mit.edu/tds/papers/Gilbert/Brewer2.pdf) | [docs/foundations/distributed-systems.md](../docs/foundations/distributed-systems.md) |
| B14 | 수용 | 가정은 Pod당 20, 세 Pod 전체 60. 0.1초 점유에서 각각 200/초·600/초, 1초이면 20/초·60/초. 직접 재계산.  | [docs/cross-domain/slow-requests.md](../docs/cross-domain/slow-requests.md) |
| B15 | 부분 수용 | 제조사 이름 자체가 아니라 제조사가 부여한 관리 하위 시스템·장비 종류 OID로 명확화. 물리 모델과 반드시 일대일 대응하는 식별자로 단정하지 않음. [RFC 3418 sysObjectID](https://www.rfc-editor.org/rfc/rfc3418.html) | [docs/network/snmp-and-device-models.md](../docs/network/snmp-and-device-models.md) |
| B16 | 수용 | 연결한 Neo4j Operations Manual의 metrics 기능은 Enterprise Edition 전용. [Neo4j metrics](https://neo4j.com/docs/operations-manual/current/monitoring/metrics/) | [docs/database/specialized-data-models.md](../docs/database/specialized-data-models.md) |
| B17 | 수용 | amdsmi_get_gpu_activity 문서에 VM guest 미지원 명시. 함수 heading의 실제 하이픈 anchor도 수정. [AMD SMI 함수](https://rocm.docs.amd.com/projects/amdsmi/en/latest/reference/amdsmi-py-api.html#amdsmi-get-gpu-activity) | [docs/host/gpu.md](../docs/host/gpu.md) |
| B18 | 수용 | primary 6 + replica 6 = shard 사본 총 12; replica 수는 6. 직접 재계산.  | [docs/middleware/search-engines.md](../docs/middleware/search-engines.md) |
| B19 | 수용 | 가중 추정·learner·Memcached stats·Spark fault tolerance·Hikari 설정을 직접 뒷받침하는 원천으로 연결. OTel 확률 명세는 Development 상태 표시. [OTel adjusted count](https://opentelemetry.io/docs/specs/otel/trace/tracestate-probability-sampling/) [etcd learner](https://etcd.io/docs/v3.6/learning/design-learner/) [Memcached stats](https://github.com/memcached/memcached/blob/master/doc/protocol.txt) [Spark 보장](https://spark.apache.org/docs/latest/streaming/getting-started.html#fault-tolerance-semantics) [Hikari 설정](https://github.com/brettwooldridge/HikariCP#gear-configuration-knobs-baby) | [docs/foundations/performance-and-statistics.md](../docs/foundations/performance-and-statistics.md)<br>[docs/foundations/traces-logs-profiles.md](../docs/foundations/traces-logs-profiles.md)<br>[docs/kubernetes/workloads-and-control-plane.md](../docs/kubernetes/workloads-and-control-plane.md)<br>[docs/middleware/stream-processing.md](../docs/middleware/stream-processing.md)<br>[docs/application/servers-and-pools.md](../docs/application/servers-and-pools.md) |
| B20 | 수용 | MetricDataResult 문서는 Forbidden을 유효 값으로 열거하지만 원인을 정의하지 않음. 권한은 조사 가설로 표시하고 Messages 보존. [MetricDataResult](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_MetricDataResult.html) | [docs/cloud/late-data-and-reconciliation.md](../docs/cloud/late-data-and-reconciliation.md)<br>[review/fact-review-1.1.json](../review/fact-review-1.1.json) |
| C-Kubernetes | 부분 수용 | 최신 1.37.1 및 1.35+ 비교 규약 수용. 최신 3개 브랜치는 1.35–1.37이나 1.34는 10월 27일까지 유지보수 중. 1.34.1 고정 실습과 1.34.12 패치 구분. [릴리스](https://kubernetes.io/releases/) [종료 일정](https://kubernetes.io/releases/patch-releases/) [현재 비교 규약](https://kubernetes.io/docs/reference/using-api/api-concepts/#resource-versions) | [docs/coverage.md](../docs/coverage.md)<br>[docs/kubernetes/inventory-consistency.md](../docs/kubernetes/inventory-consistency.md)<br>[docs/kubernetes/objects-and-control-loops.md](../docs/kubernetes/objects-and-control-loops.md)<br>[docs/kubernetes/operators-and-api-lifecycle.md](../docs/kubernetes/operators-and-api-lifecycle.md)<br>[docs/kubernetes/collection.md](../docs/kubernetes/collection.md)<br>[docs/product/compatibility-and-acceptance.md](../docs/product/compatibility-and-acceptance.md)<br>[docs/review.md](../docs/review.md)<br>[docs/validation.md](../docs/validation.md)<br>[review/fact-review-1.1.json](../review/fact-review-1.1.json)<br>[README.md](../README.md) |
| C-Collector | 수용 | 현재 0.162.0. core published_at=2026-09-28T14:09:31Z, 배포판=2026-09-29T12:34:07Z. 9월 29일은 배포판 기준으로 맞음. 0.137.0 실행 기록 유지. [core release](https://github.com/open-telemetry/opentelemetry-collector/releases/tag/v0.162.0) [distribution release](https://github.com/open-telemetry/opentelemetry-collector-releases/releases/tag/v0.162.0) | [docs/coverage.md](../docs/coverage.md)<br>[docs/application/trace-sampling-and-context.md](../docs/application/trace-sampling-and-context.md)<br>[docs/product/telemetry-delivery-contracts.md](../docs/product/telemetry-delivery-contracts.md)<br>[docs/product/compatibility-and-acceptance.md](../docs/product/compatibility-and-acceptance.md) |
| C-Prometheus | 수용 | 3.5 LTS 종료 2026-07-31, 현재 LTS 3.13.4·최신 3.15.0. 과거 promtool 3.5.0 결과는 그대로 둠. 공식 release 목록과 v3.5.5 태그도 대조: 검토 시점 3.5 계열의 마지막 게시 패치는 3.5.5. [3.5.5 릴리스](https://github.com/prometheus/prometheus/releases/tag/v3.5.5) [지원 주기](https://prometheus.io/docs/introduction/release-cycle/) [다운로드](https://prometheus.io/download/) | [docs/coverage.md](../docs/coverage.md)<br>[docs/cross-domain/reproducible-labs.md](../docs/cross-domain/reproducible-labs.md)<br>[docs/validation.md](../docs/validation.md) |
| C-MySQL | 부분 수용 | 9.7 LTS·YY.M 체계 수용. 9.7.3은 Docker image 전용 보안 패치로 범위 제한. 8.4 LTS 문서 기준을 유지하며 새 LTS 출시를 8.4 EOL로 해석하지 않음. [릴리스 정책](https://dev.mysql.com/doc/refman/9.7/en/mysql-releases.html) [9.7.2](https://dev.mysql.com/doc/relnotes/mysql/9.7/en/news-9-7-2.html) [9.7.3 Docker only](https://dev.mysql.com/doc/relnotes/mysql/9.7/en/news-9-7-3.html) | [docs/coverage.md](../docs/coverage.md)<br>[docs/database/mysql-mariadb.md](../docs/database/mysql-mariadb.md)<br>[docs/database/collection-contracts.md](../docs/database/collection-contracts.md)<br>[docs/database/transactions-and-locks.md](../docs/database/transactions-and-locks.md) |
| C-Ceph | 부분 수용 | 공식 표는 Squid 2026-10-31을 estimated EOL로 표시. 현재 Tentacle 20.2.4, Squid 19.2.6. 확정 보증일로 쓰지 않음. [Ceph 릴리스 표](https://docs.ceph.com/en/latest/releases/) | [docs/coverage.md](../docs/coverage.md)<br>[docs/storage/capacity-and-protection.md](../docs/storage/capacity-and-protection.md) |
| C-cAdvisor | 수용 | Kubernetes 1.37.1 go.mod의 github.com/google/cadvisor/lib v0.60.5 확인. lib/v0.60.5 handler.go에서도 Usage−inactive_file, 0 하한 식 확인. [go.mod](https://github.com/kubernetes/kubernetes/blob/v1.37.1/go.mod) [handler.go](https://github.com/google/cadvisor/blob/lib/v0.60.5/lib/container/libcontainer/handler.go) | [docs/coverage.md](../docs/coverage.md)<br>[docs/containers/memory-accounting-and-oom.md](../docs/containers/memory-accounting-and-oom.md)<br>[review/fact-review-1.1.json](../review/fact-review-1.1.json) |
| C-OCI-CSI | 수용 | 공식 latest release의 runtime-spec 1.3.0·CSI 1.13.0 확인. 책의 고정 판본 유지; 명세 판본과 제품 EOL 구분. [OCI 1.3.0](https://github.com/opencontainers/runtime-spec/releases/tag/v1.3.0) [CSI 1.13.0](https://github.com/container-storage-interface/spec/releases/tag/v1.13.0) | [docs/coverage.md](../docs/coverage.md) |
| C-Flink | 수용 | 공식 다운로드에 안정 2.3.0, 1.20 LTS 및 1.20.5 표기 확인. [Flink downloads](https://flink.apache.org/downloads/) | [docs/coverage.md](../docs/coverage.md) |
| C-Tomcat | 수용 | Spring Boot 4의 Tomcat 11 확인. Tomcat 10.1은 여전히 지원 계열이므로 EOL처럼 표시하지 않음. [Tomcat 지원 버전](https://tomcat.apache.org/whichversion.html) [Spring Boot requirements](https://docs.spring.io/spring-boot/system-requirements.html) | [docs/coverage.md](../docs/coverage.md) |
| C-PostgreSQL | 수용 | 공식 지원 표의 18.6 확인, 18 계열 종료 예정 2030-11-14. [PostgreSQL versioning](https://www.postgresql.org/support/versioning/) | [docs/coverage.md](../docs/coverage.md) |
| C-OTLP | 부분 수용 | 공식 웹 규약의 제목은 1.11.0이 맞다. 반면 원천 저장소 latest release는 1.11.1(2026-09-29T08:46:40Z). 문서 판 표시와 소스 릴리스의 최신성을 분리. [웹 규약 1.11.0](https://opentelemetry.io/docs/specs/otlp/) [원천 릴리스 1.11.1](https://github.com/open-telemetry/opentelemetry-proto/releases/tag/v1.11.1) | [docs/coverage.md](../docs/coverage.md)<br>[docs/product/telemetry-delivery-contracts.md](../docs/product/telemetry-delivery-contracts.md)<br>[docs/product/compatibility-and-acceptance.md](../docs/product/compatibility-and-acceptance.md) |
| C-etcd-보충 | 수용 | 고정 실습 의존성 3.6.4와 현재 latest release 3.7.2를 별도 표기. 3.6 종료일은 미확정; 이번 서버 실행 변경 없음. [etcd release](https://github.com/etcd-io/etcd/releases/tag/v3.7.2) | [docs/coverage.md](../docs/coverage.md) |

## 2. 수정 방식을 달리한 이유

**A1:** 1b의 저장소 실행 결과로 CPU/RAW≈1과 MONOTONIC/RAW≈0.937이 재현됐고 sleep·idle 및 adjtimex 값도 분모 주파수 조정 설명에 부합했습니다. 따라서 새 실행을 계속 “원인 미해결”로 표시하지 않습니다. 그러나 RAW·tick을 기록하지 않은 과거 약 1.06 표본은 같은 환경에서 재현된 동일 패턴으로만 연결합니다. tick을 누가 설정했는지와 RAW의 외부 정확도는 미확인입니다. 기존 `passed`와 `independently sampled`의 경과 시간 교정 해석은 정정하되 원시 JSON·보존 실행기는 그대로 둡니다. 새 결과도 원본과 byte 단위로 동일하게 출판하고 SHA256·실행기 hash·4개 CPU 구간·61개 idle 표본·본문 수치를 검증합니다. 품질 표시는 `observed`이며 정상 인증이나 >1 값의 clamp가 아닙니다.

**B2:** 해당 버전에서 내부 retry와 실패 계수의 호출 순서는 명확합니다. 다만 일반 웹 문서의 “재시도할 수 있다”는 문구가 모든 버전·exporter에서 반드시 상류 재전송만을 뜻한다고 해석하지 않았습니다. 내부 중간 실패 횟수, 최종 exporter 실패, 부분 거절, 고유 항목의 영구 유실을 나누었습니다. 이 설명은 코드 대조이며 A3 실험의 metric 관측이 아닙니다.

**B3:** 필드 폭만 알면 무조건 wrap 복원이 가능한 것은 아닙니다. 여러 번 wrap했을 수 있고 reset 표식이 없을 수도 있습니다. 참조 어댑터는 감소를 `decrease`로 남기며 rate를 보류합니다. 동일 수명과 구간 최대 증가량을 별도로 보장한 경우에만 modulo 복원을 검토하도록 설명했습니다. 49.71일은 누적 시간이며 모든 필드의 실제 경과 주기가 아닙니다.

**B12:** 기존 SQL은 실행 증거를 가진 행별 관측 예시로 유지했습니다. 수집 계약의 `collected_at`을 각 행 평가 시각으로 명시했으므로 잘못된 공통 표본 시각을 주장하지 않습니다. `statement_timestamp()`는 문장 공통 시작 시각을 원할 때의 대안이지 DB 전체 원자적 snapshot 시각을 보증하는 함수가 아닙니다. 따라서 이번에는 PostgreSQL 재실행과 hash 교체가 필요하지 않습니다.

**B15:** RFC는 제조사가 관리 하위 시스템을 식별하도록 할당한 OID를 설명합니다. 장비 종류를 나타낸다고 풀되 모든 제품에서 정확히 물리 모델과 일대일 대응하는 식별자로 제한하지 않았습니다.

**C:** 지원 기간·최신 버전·문서 판본은 다른 축입니다. Kubernetes 1.34는 최신 3개에는 없지만 유지보수 종료 전입니다. Ceph 날짜는 예상치이고 MySQL 9.7.3은 Docker image 전용입니다. OTLP 웹 제목 1.11.0과 원천 릴리스 1.11.1을 구분했습니다. Collector 날짜는 core와 배포판 양쪽을 확인해 어느 기준인지 적었습니다. 고정 버전의 설명을 최신 버전에서 실행한 것처럼 고치지 않았습니다.

## 3. Claude 1b 답변 반영과 계산 정정

1. A1의 원시 로그가 보존되지 않은 busy·timesyncd·Windows Stopwatch 보고는 본문과 사실 근거에서 제외했습니다. 별도 구두 보고의 수치를 새 실습 근거와 섞지 않습니다. 저장소 실행기가 만든 JSON으로 필요한 근거를 이어 받았으므로 추가 원시 기록 요청은 없습니다.
2. 61개 idle 표본의 tick 합계는 571,189µs입니다. `(571189 / 61) / 10000 = 0.9363754098360656`이므로 소수 다섯 자리로는 **0.93638**입니다. 전달 요약의 0.93639를 정정했습니다. 측정된 전체 MONOTONIC/RAW는 **0.9363740129706928**이며 두 값은 가깝지만, 단순 표본 평균을 시간 가중 적분과 동일시하지 않습니다. freq와 표본 사이의 변경 시점도 고려해야 합니다.
3. 같은 61개 표본의 `freq_ppm` 최댓값은 **+40.45188903808594**입니다. 전달 요약의 약 +10.9와 다릅니다. idle 배열의 인덱스 0–3에서 `freq_scaled_ppm=2651055`, `2651055/65536=40.45188903808594`를 확인했습니다. 최솟값 **-49.82659912109375**도 같은 변환으로 확인했습니다. 두 정정은 분모 시계 조정이라는 해석을 바꾸지 않습니다.
4. A2의 미보존 예비 200·`ListFromCacheSnapshot` 인과는 제외한 상태를 유지합니다. Kubernetes 최신 3개 브랜치와 1.34 유지보수, MySQL 9.7.3의 Docker 범위, Ceph 예상 EOL, OTLP 웹 문서·원천 릴리스 구분에 대한 Claude의 수용 답변도 기록했습니다.

## 4. 실행한 검증

1b의 필수 여섯 검증은 모두 통과했습니다. 명령 앞의 `python -X utf8 -B`는 모든 Python 검사에 동일하게 사용했습니다. 실제 Linux 실행은 Claude가 수행했으며 Codex는 저장된 결과를 검증했습니다. 1차 URL 조회와 WSL 접근 거부는 [구조화된 기록](claude-codex-r1.json)의 `round_1a_history`에 보존했습니다.

| 명령 | 1b 결과 |
| --- | --- |
| `scripts/build_book.py` / `scripts/build_html.py` | BOOK.md·BOOK.html 재생성 |
| `scripts/check_docs.py` | 통과: Markdown 116개·상세 장 92개·로컬 링크 1,725개·외부 URL 목록 348개 |
| `scripts/verify_examples.py` | 통과: 51개 원문·146개 검사 |
| `scripts/verify_contracts.py` | 통과: 어댑터 22개·계산 28개·기존 근거 hash |
| `scripts/verify_revision.py` | 통과: 기존 31개 시나리오·SQL·12개 계산과 새 Linux 4개 구간·idle 61개 표본·본문 수치·hash |
| `scripts/build_book.py --check` | 통과: 원문 114개와 일치 |
| `scripts/build_html.py --check` | 통과: 원문·고정 renderer와 일치 |
| `scripts/verify_review_r1.py --linux-result .lab-runs/linux-clock-r1.json` | 통과: 품질 합성 11개·ABI 2개·counter/wrap 5개·잘못된 근거 거절 3개·출판 및 전달 Linux JSON 정합성 |
| `scripts/check_html.py` | 미완료: 1회 시도에서 `Timeout: Page.enable`; 화면 단계 전 실패 |
| `git -c safe.directory=C:/project/Domain-Knowledge diff --check` | 통과: 공백 오류 없음 |

기존 출판 JSON 6개·보존 실행기·이번 Linux 결과를 만든 현재 실행기·PostgreSQL SQL·book.json은 1b 시작 시 SHA256과 일치합니다. 새 JSON은 전달받은 파일과 byte 단위로 같고, 입력 코드와 출판 파일의 hash는 [provenance](evidence-provenance.json)에 연결했습니다. 브랜치와 HEAD도 그대로입니다. 기존 URL 목록 348개를 이번 1b에 모두 HTTP 재조회한 것은 아닙니다. A1의 시계·adjtimex 원천을 다시 확인했습니다.

## 5. 후속 실행 상태

Linux 진단과 원시 결과 검증은 완료됐으므로 Claude에게 다시 실행을 요청하지 않습니다. 기존 JSON과 실행기를 보존하며 새 출판 근거는 [1.1-linux-clock-r1.json](../labs/results/1.1-linux-clock-r1.json)입니다.

Claude가 실행한 정확한 명령은 다음과 같습니다. 재현 안내이며 이미 받은 결과를 대체하라는 요청이 아닙니다.

```powershell
wsl -d Ubuntu --cd /mnt/c/project/Domain-Knowledge -- python3 -B scripts/run_linux_lab.py --clock-observation-seconds 60 --output .lab-runs/linux-clock-r1.json
python -X utf8 -B scripts/verify_review_r1.py --linux-result .lab-runs/linux-clock-r1.json
```

전달된 HTML 검사 통과 기록은 [당시 hash의 기록](html-check-r1b-incoming.json)으로 보존했습니다. A1 수정 뒤 생성한 HTML 검사는 `Page.enable` 시간 초과로 미완료입니다. [화면 검사 이력](html-check-r1.json)에 시도한 파일과 최종 파일의 hash를 구분했습니다. Claude에게 남은 실행 요청은 아래 현재 BOOK.html의 화면 검사 하나입니다. 성공한 뒤에는 새 `review/html-check.json`의 hash에 맞춰 화면 검사 상태를 갱신합니다.

```powershell
python -X utf8 -B scripts/check_html.py
```

## 6. 2라운드 제안

아래 시간·메모리·디스크는 **계획용 예상치이며 실측·보장치가 아닙니다.** 다운로드 속도와 설치 상태에 따라 늘어날 수 있습니다. 로컬 loopback 실험으로 진행하면 cloud 사용료는 없으며, 개발·검토 시간과 로컬 자원은 필요합니다. 최신 버전의 실행 파일·SHA256을 새로 고정한 뒤 기존 결과와 별도 경로에 기록합니다.

| 우선순위 | 작업과 완료 기준 | 예상 비용 |
| --- | --- | --- |
| 높음 | Kubernetes 1.34.12와 1.37.1 × watch cache on/off. pagination·selector 이탈·만료 이력과 feature gate 기록. compaction·cache 변경을 분리해 인과 확인 | 실행 15–30분, 동시 1개 서버 조합 기준 RAM 여유 2–4GiB·디스크 1–2GiB; 준비·분석 2–4시간 |
| 높음 | Collector 0.137.0과 0.162.0에 내부 로그·metric을 켜고 기존 7개 시나리오 반복. partial rejection 로그·계수, retry 중/종료 후 send_failed, queue on/off의 완료 경계 분리 | 실행 5–15분, RAM 여유 0.5–1GiB; 준비·분석 2–4시간 |
| 높음 | promtool 3.13.4 LTS·3.15.0에서 기존 식 8개·alert 5개와 경계 사례 재평가 | 실행 1–5분·도구 다운로드 수백 MB 범위의 여유; 준비·비교 30–60분 |
| 다음 | PostgreSQL xmin horizon에 prepared transaction·slot·standby feedback이 미치는 영향과 행별/문장별 시각을 별도 임시 DB에서 재현 | 2개 인스턴스 기준 실행 15–30분, RAM 여유 1–2GiB·디스크 1–2GiB; 준비·해석 반나절 |
| 다음 | 32bit counter wrap·reset·복수 wrap의 관측 가능성과 모호한 rate 처리 사례 보강. 합성 입력과 실제 필드 decoder를 구분 | 실행 1분 이내·개발/검토 1–2시간; 실제 49일 대기 실험은 계획하지 않음 |
| 이후 | namespace/cgroup 관측 범위와 OOM·throttling, 재시작 후 telemetry 복구·중복의 제품 계약 보강 | 격리 환경·실행 한도부터 설계; 상세 비용은 실험 범위 확정 뒤 산정 |

이번 라운드에서는 위 최신 버전 실험과 새 장 보강을 실행하지 않았습니다.
