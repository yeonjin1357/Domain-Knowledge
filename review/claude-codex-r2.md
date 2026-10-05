# Claude–Codex 2라운드: 원고 보강·교차 검토·실습 결과

확인일: **2026-10-05**. 판 번호와 `book.json.as_of`는 제1.1판·2026-10-04로 유지한다. G1–G5와 G6–G12를 원고에 반영했고, 2d에서 Claude가 전달한 최종 실습 결과와 2c 지적을 다시 대조했다. **0–3절은 2b 당시 기록**, 4절 이후는 2d의 출판·수정·판정 기록이다. 과거의 계획·미실행 문구를 현재 실행 상태와 구분한다. AI 간 교차 검토이며 외부 전문가 인증이 아니다.

## 0. Kubernetes 실행 버전과 입력 보존

사용자가 승인한 공식 envtest **1.34.1·1.37.0**을 사용한다. 각 minor의 최신 patch가 아니다(검토 시 1.34.12·1.37.1). 목적은 minor API 규약과 watch cache 경로 비교이며 최신 patch의 회귀 인증이 아니다. [공식 patch 일정](https://kubernetes.io/releases/patch-releases/)

진행 중인 다른 실습의 입력 hash를 보존하기 위해 [전용 manifest](../labs/review-r2/kubernetes-assets.json)를 추가하고 [Kubernetes 실행기](../scripts/run_kubernetes_r2_lab.py)만 연결했다. 공통 [assets.json](../labs/review-r2/assets.json)의 2a 당시 미제공 항목과 [공통 다운로드 코드](../scripts/get_review_r2_assets.py)는 유지한다. 따라서 공통 준비 검사의 옛 `UNAVAILABLE` 목록은 2a 요청 버전의 상태이며 이번 두 버전의 실패를 뜻하지 않는다.

| 실행 버전 | 공식 릴리스·자산 | 공식 release API asset digest에서 고정한 SHA256 |
| --- | --- | --- |
| 1.34.1 | [릴리스](https://github.com/kubernetes-sigs/controller-tools/releases/tag/envtest-v1.34.1), [linux-amd64 tar.gz](https://github.com/kubernetes-sigs/controller-tools/releases/download/envtest-v1.34.1/envtest-v1.34.1-linux-amd64.tar.gz) | `c8500090806ed5ce4064eeeb2a5666476a5168c1f4ff0eadd54fe59b22c4baa7` |
| 1.37.0 | [릴리스](https://github.com/kubernetes-sigs/controller-tools/releases/tag/envtest-v1.37.0), [linux-amd64 tar.gz](https://github.com/kubernetes-sigs/controller-tools/releases/download/envtest-v1.37.0/envtest-v1.37.0-linux-amd64.tar.gz) | `f03faedfc68d2a78cee5cb02618bb44e7f67044f4c5fc957f72d3307fda61a9c` |

Windows Python으로 공식 자산을 `.tools/r2/`에 내려받아 압축 해제 전 검증했다. 이후 receipt·실행 파일 hash·ELF Linux amd64 header를 읽기 전용으로 재확인했다. API server·etcd를 이 환경에서 실행하지 않았다. 결과 JSON에는 `patch_scope`와 전용 manifest·실행기 입력 hash가 들어간다.

| 시나리오 | 지지 조건 | 반증·미확정 조건 |
| --- | --- | --- |
| selector 이탈 | DELETED 수신 + 직접 GET 200 + 같은 UID·바뀐 label | 완료된 watch의 해당 이벤트 부재 또는 객체 상태 불일치 |
| pagination | 동일 collection RV·원래 항목만 3개, 중간 생성 항목은 fresh LIST에만 존재 | 누락·중복·중간 생성 혼입·RV 변경 |
| 410 | 실험 compaction 후 Exact RV=1은 410, fresh LIST는 200 | Exact 200이면 이 조건에서 만료를 유발하지 못한 반증; API 위반으로 단정하지 않음 |
| resourceVersion | 같은 core/v1 ConfigMap 순차 변경에서 십진수 RV 증가 | 역전이면 반증; 1.34의 비수치 RV는 opaque 규약상 허용되므로 미확정 |

각각 cache true/false와 두 버전으로 총 16개를 기록한다. 서버의 `kubernetes_feature_enabled`에서 ListFromCacheSnapshot 값을 찾되, 지표가 없으면 disabled가 아니라 미관측이다. continue token 자체의 시간 만료, 업무 Pod·OOM·eviction은 이번 API 행렬의 실행 대상이 아니다.

### Claude가 실행할 명령

PowerShell에서 순서대로 실행한다. 아래 시간·메모리는 **계획 추정치**이며 실측값이 아니다. 이미 받은 자산이 있으므로 첫 명령은 검증·재사용 경로가 된다. 출력 파일이 이미 있으면 덮어쓰지 않으므로 새 이름을 정하고 다음 검증 명령에도 같은 이름을 쓴다.

```powershell
wsl -d Ubuntu --cd /mnt/c/project/Domain-Knowledge -- python3 -B scripts/run_kubernetes_r2_lab.py --prepare-assets
wsl -d Ubuntu --cd /mnt/c/project/Domain-Knowledge -- python3 -B scripts/run_kubernetes_r2_lab.py --output .lab-runs/r2/kubernetes.json
python -X utf8 -B scripts/verify_review_r2.py --result .lab-runs/r2/kubernetes.json
```

| 명령 | 예상 시간·메모리 | 출력 |
| --- | --- | --- |
| 자산 준비 | 재사용 수초–1분, 새 다운로드 시 연결 속도에 따름; 256 MiB 이내 계획 | `.tools/r2/envtest-1.34.1`, `.tools/r2/envtest-1.37.0`와 receipt |
| API 행렬 | 약 3–8분; API server+etcd 한 쌍씩 순차 실행, 1–2 GiB 여유 계획 | `.lab-runs/r2/kubernetes.json`; 로그·사건·gate 관측 포함 |
| 결과 검증 | 수초–1분; 256 MiB 이내 계획 | 터미널 PASS/판정별 집계; `.lab-runs/` 안의 준비 검사 임시 fixture |

검증기의 PASS는 JSON·입력·정리 상태의 일치이며 모든 시나리오의 supported를 뜻하지 않는다. refuted·inconclusive도 원시값과 함께 반환해야 한다. 2b Codex 작업에서는 이 검증기가 `.lab-runs/`에 fixture를 쓰므로 실행하지 않았다.

## 1. 주제별 원천 대조 기록

아래 원천은 2026-10-05에 직접 확인했다. 버전이 고정된 코드·문서와 갱신되는 웹 문서를 구분했고, 실제 설치·측정으로 확인하지 않은 기능은 본문에 그렇게 표시했다.

### G1. Linux 네트워크 스택

- 쓴 위치: [새 장](../docs/network/linux-stack-counters.md), 네트워크 목차·용어집·지표 참조표.
- 확인한 원천: [Linux SNMP counter 설명](https://docs.kernel.org/networking/snmp_counter.html), [TCP-MIB RFC 4022](https://www.rfc-editor.org/rfc/rfc4022.html), [network namespace procfs](https://man7.org/linux/man-pages/man5/proc_pid_net.5.html), Linux 6.12 [송신](https://github.com/torvalds/linux/blob/v6.12/net/ipv4/tcp_output.c)·[UDP](https://github.com/torvalds/linux/blob/v6.12/net/ipv4/udp.c)·[proc 출력](https://github.com/torvalds/linux/blob/v6.12/net/ipv4/proc.c), [ss](https://man7.org/linux/man-pages/man8/ss.8.html)·[v6.12.0 코드](https://raw.githubusercontent.com/iproute2/iproute2/v6.12.0/misc/ss.c).
- 채택: Tcp·Udp·TcpExt의 단위/중복, CurrEstab gauge, namespace 수명, 헤더 기반 파싱, `ss`의 ms·segment·현재/누적 구분.
- 쓰지 않은 해석: RetransSegs/OutSegs를 실제 손실 확률로 변환, OutSegs를 모든 경로에서 순수 원본 data packet으로 단정, RFC Counter32를 Linux proc 저장 폭으로 대입. 60초 합성 계산만 검사했고 명령은 실행하지 않았다.

### G2. Kubernetes 압박·종료·수집

- 쓴 위치: [새 장](../docs/kubernetes/pressure-and-termination.md), [collection](../docs/kubernetes/collection.md), 기존 인벤토리 장의 후속 실습 범위.
- 확인한 원천: [QoS](https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/), [eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/), [kubelet config](https://kubernetes.io/docs/reference/config-api/kubelet-config.v1beta1/), [cgroup v2](https://docs.kernel.org/admin-guide/cgroup-v2.html), [1.35 resize](https://v1-35.docs.kubernetes.io/docs/tasks/configure-pod-container/resize-container-resources/), [PSI GA](https://kubernetes.io/blog/2026/05/12/kubernetes-v1-36-psi-metrics-ga/), [1.37 릴리스](https://kubernetes.io/blog/2026/08/26/kubernetes-v1-37-release/), [node metrics](https://kubernetes.io/docs/reference/instrumentation/node-metrics/), [feature gate 이력](https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/), [API concepts](https://kubernetes.io/docs/reference/using-api/api-concepts/), [client-go v1.37 기본값](https://github.com/kubernetes/kubernetes/blob/v1.37.0/staging/src/k8s.io/client-go/features/known_features.go).
- 채택: QoS와 Pod-level 자원 예외, request·priority·usage ranking, oom_score_adj, OOMKilled/Evicted 증거, resize actual/spec 차이. 컨테이너 resize 1.35 Stable, PSI 1.36 GA, cgroup v1은 1.35부터 기본 거부하지만 1.37에도 override 존재. WatchList의 1.33 default false 구간과 1.34 이후 true, client 1.35 true를 구분했다.
- 쓰지 않은 해석: OOMKilled=limit 초과 확정, 137=OOM 확정, QoS 순서로 모든 eviction 정렬, memory.events oom=모든 할당 실패/kill, cgroup v1 코드 삭제, API-only envtest가 노드 압박 동작까지 검증했다는 주장. continue 만료와 watch history 만료의 보존 시간을 동일시하지 않았다.

### G3. PostgreSQL 운영 관측

- 쓴 위치: [새 장](../docs/database/postgresql-operations.md), DB 목차·참조표.
- 확인한 원천: 18의 [routine vacuuming](https://www.postgresql.org/docs/18/routine-vacuuming.html), [vacuum 설정](https://www.postgresql.org/docs/18/runtime-config-vacuum.html), [통계 설정](https://www.postgresql.org/docs/18/runtime-config-statistics.html), [통계 view](https://www.postgresql.org/docs/18/monitoring-stats.html), [역할](https://www.postgresql.org/docs/18/predefined-roles.html), [slot](https://www.postgresql.org/docs/18/view-pg-replication-slots.html), [prepared](https://www.postgresql.org/docs/18/view-pg-prepared-xacts.html); [16](https://www.postgresql.org/docs/16/release-16.html)·[17](https://www.postgresql.org/docs/17/release-17.html)·[18](https://www.postgresql.org/docs/18/release-18.html) 릴리스; pg_stat_statements [12](https://www.postgresql.org/docs/12/pgstatstatements.html)·[13](https://www.postgresql.org/docs/13/pgstatstatements.html)·[14](https://www.postgresql.org/docs/14/pgstatstatements.html)·[17](https://www.postgresql.org/docs/17/pgstatstatements.html)·[18](https://www.postgresql.org/docs/18/pgstatstatements.html).
- 채택: XID와 MultiXact 거리·별도 설정, backend/prepared/slot/feedback의 horizon, `cache` 기본값과 `none` 모니터링 용도, view·컬럼·단위 버전 표. 제시된 버전 단서를 확인했고 progress vacuum의 17 단위 변경도 추가했다.
- 제한: SQL은 PostgreSQL 18용 미실행 읽기 예시. 서버 major뿐 아니라 extension version·실제 컬럼도 검사한다. `n_dead_tup` 감소를 freeze 전진으로, `dealloc`을 사라진 개별 쿼리 수로, age를 경과 초로 쓰지 않았다. 새 실습 수치는 2d에 연결한다.

### G4. Exemplar·counter 시작·sampling 확률

- 쓴 위치: [새 지표 문맥 장](../docs/foundations/metric-context-and-start-time.md), [sampling 장](../docs/application/trace-sampling-and-context.md).
- 확인한 원천: [OTel data model](https://opentelemetry.io/docs/specs/otel/metrics/data-model/), [SDK exemplar](https://opentelemetry.io/docs/specs/otel/metrics/sdk/#exemplar), [OpenMetrics 1.0](https://prometheus.io/docs/specs/om/open_metrics_spec/), [Prometheus 3.15.0 flags](https://github.com/prometheus/prometheus/blob/v3.15.0/docs/feature_flags.md), [probability sampling](https://opentelemetry.io/docs/specs/otel/trace/tracestate-probability-sampling/), [tracestate](https://opentelemetry.io/docs/specs/otel/trace/tracestate-handling/), [Tracing SDK](https://opentelemetry.io/docs/specs/otel/trace/sdk/), [W3C 2024-03-28 CRD](https://www.w3.org/TR/2024/CRD-trace-context-2-20240328/).
- 채택: exemplar는 선택 사건 연결, start와 scrape 시각 구분, 첫 증가분의 정보 한계. th/rv는 Development이며 56bit threshold·역확률 가중과 추정 전제를 명시했다. TraceIdRatioBased의 deprecated와 최소 2027-01-01까지 기존 동작 유지 규칙을 함께 썼다.
- 쓰지 않은 해석: W3C Level 2를 최종 Recommendation으로 소개, sampled bit를 확률로 변환, 불명확한 tail·유실 후 단일 10배 보정, Prometheus `_created` 존재만으로 질의에서 자동 사용한다고 주장. promtool만으로 exemplar/start 저장 동작을 검증했다는 주장도 제외했다.

### G5. OTel 안정 이름

- 쓴 위치: [새 semantic conventions 장](../docs/application/semantic-conventions.md), [런타임 장 연결](../docs/application/managed-runtimes.md).
- 확인한 원천: SemConv 웹 1.44.0의 [HTTP metrics](https://opentelemetry.io/docs/specs/semconv/http/http-metrics/), [HTTP attributes](https://opentelemetry.io/docs/specs/semconv/registry/attributes/http/), [HTTP migration](https://opentelemetry.io/docs/specs/semconv/non-normative/http-migration/), [JVM](https://opentelemetry.io/docs/specs/semconv/runtime/jvm-metrics/), [.NET](https://opentelemetry.io/docs/specs/semconv/runtime/dotnet-metrics/), [Microsoft runtime metrics](https://learn.microsoft.com/en-us/dotnet/core/diagnostics/built-in-metrics-runtime).
- 채택: 명시한 HTTP/JVM/.NET 이름·단위·형태의 Stable 상태, http/http/dup 전환, ms→s 예시, 현재 JVM memory와 .NET last_collection 값의 차이.
- 쓰지 않은 해석: Stable metric의 모든 부속 attribute도 Stable, 모든 SDK가 이미 출력, 환경변수 하나가 모든 major에 필수, JVM GC action과 .NET 누적 pause가 같은 지표. `jvm.gc.cause`는 Development로 구분했다.

### G6. Kafka broker·share group

- 쓴 위치: [Kafka](../docs/middleware/kafka.md).
- 확인한 원천: [4.3 monitoring](https://kafka.apache.org/43/operations/monitoring/), [4.0 upgrade](https://kafka.apache.org/40/getting-started/upgrade/), [4.2 릴리스](https://kafka.apache.org/blog/2026/01/14/apache-kafka-4.2.0-release-announcement/), [4.3 ShareConsumer](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/KafkaShareConsumer.html), [KIP-1226](https://cwiki.apache.org/confluence/spaces/KAFKA/pages/390761228/KIP-1226%2BIntroducing%2BShare%2BPartition%2BLag%2BPersistence%2Band%2BRetrieval).
- 채택: 4개 gauge의 broker/controller 범위, 4.0 ZooKeeper 제거, share group의 4.2 production-ready 상태와 획득·확인·재전달 모델.
- 제한: 해당 4개 gauge 모두가 KRaft 전용이라는 해석을 쓰지 않았다. lag 설계의 terminal 제외와 offset 간극을 설명하되 실제 broker 값·정확한 업무 잔량으로 단정하지 않았다. JMX·broker 실행 없음.

### G7. Windows 카운터

- 쓴 위치: [Windows](../docs/host/windows.md).
- 확인한 원천: [Microsoft 카운터 설명](https://learn.microsoft.com/en-us/exchange/exchange-2013-performance-counters-exchange-2013-help), [PERFORMANCE_INFORMATION](https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-performance_information), [Utility와 100%](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/cpu-usage-exceeds-100), [KB5064081](https://support.microsoft.com/en-au/servicing/os/windows-11/2025/08/august-29-2025-kb5064081-os-build-26100-5074-preview), [PDH 수집](https://learn.microsoft.com/en-us/windows/win32/perfctrs/collecting-performance-data).
- 채택: Time·Utility·물리 가용·commit·ready queue의 실명과 단위, rate 카운터의 두 표본·CStatus.
- 수정한 단서: “작업 관리자가 쓰는 값”을 전 Windows 빌드에서 Utility로 확정하지 않았다. Windows 11 업데이트는 CPU 계산 변경과 선택적 CPU Utility 열을 설명한다. 이 공지만으로 새 계산을 특정 PDH 카운터와 일대일 매핑하지 않는다. Exchange 2013 페이지의 운영 임계값은 전용 범위이므로 가져오지 않았다.

### G8. Cloud 시간 축

- 쓴 위치: [공급자 지표](../docs/cloud/provider-metrics.md), [서버리스](../docs/cloud/managed-and-serverless.md), [네트워크](../docs/cloud/networking.md).
- 확인한 원천: [GetMetricData](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_GetMetricData.html), [EC2 monitoring](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/manage-detailed-monitoring.html), [Lambda 지표](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-metrics-types.html), [runtime 환경](https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtime-environment.html), [Telemetry schema](https://docs.aws.amazon.com/lambda/latest/dg/telemetry-schema-reference.html), [INIT 과금 공지](https://aws.amazon.com/blogs/compute/aws-lambda-standardizes-billing-for-init-phase/), [flow record](https://docs.aws.amazon.com/vpc/latest/userguide/flow-log-records.html)·[예외](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs-limitations.html), [Azure 집계](https://learn.microsoft.com/en-us/azure/azure-monitor/metrics/metrics-aggregation-explained), [GCP metrics](https://docs.cloud.google.com/monitoring/api/metrics)·[지연](https://docs.cloud.google.com/monitoring/api/v3/latency-n-retention).
- 채택: 3h/15d/63d/455d 보존, query 500·기본 datapoints 100800·pagination, sampling/게시/귀속 시각, NULL/0, flow 집계·예외.
- 수정한 단서: EC2 basic은 **상태 검사 1분 예외**가 있다. INIT 과금 변경은 2025-08-01의 managed ZIP on-demand 범위이며 Duration metric 재정의가 아니다. Errors는 표준 Lambda metric의 호출 시작 시각. Nitro의 1분 이하 집계와 공급자별 가용성도 구분했다. Azure 최소 grain을 모든 로그·관측 체계로, GCP 지연을 하나의 상수로 일반화하지 않았다. cloud 호출·유료 설정 변경 없음.

### G9. 알림 지연

- 쓴 위치: [알림](../docs/product/alerts-and-incidents.md).
- 확인한 원천: [Alertmanager 설정](https://prometheus.io/docs/alerting/latest/configuration/), [Prometheus alert rule](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/).
- 채택: route 기본값 30s/5m/4h, 새 그룹/기존 그룹의 구분, resolved·receiver별 send_resolved, 합성 180초 계산.
- 수정한 단서: `수집+평가 간격+for+group_wait`를 정확한 모든 경우의 등식으로 쓰지 않았다. 발생 위상·평가 정렬·게시·window·억제·기존 그룹·전송 지연을 분리했다. 서버나 외부 통지 수신처 호출 없음.

### G10. 저장 쓰기 경로

- 쓴 위치: [쓰기 지속성](../docs/storage/write-path-and-durability.md), [Ceph](../docs/storage/capacity-and-protection.md), [multipath](../docs/storage/raid-lvm-and-paths.md).
- 확인한 원천: [Linux write cache](https://docs.kernel.org/block/writeback_cache_control.html), [open(2)](https://man7.org/linux/man-pages/man2/open.2.html), [PG18 data_sync_retry](https://www.postgresql.org/docs/18/runtime-config-error-handling.html), [Ceph Squid pool](https://docs.ceph.com/en/squid/rados/operations/pools/), [PG states](https://docs.ceph.com/en/squid/rados/operations/pg-states/), [RHEL9 DM Multipath](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html-single/configuring_device_mapper_multipath/index).
- 채택: PREFLUSH/FUA 범위, O_DIRECT와 동기화 차이, fsync 오류 재시도의 정보 한계, data_sync_retry 기본 off, min_size와 PG, queue_if_no_path의 장기 대기.
- 쓰지 않은 해석: direct I/O=지속성, 후속 fsync 성공=앞선 유실 복원, min_size 단독으로 모든 inactive 원인 설명, queue 중 오류 없음=정상. 설정 변경·장애 주입 없음.

### G11. HTTP·TLS

- 쓴 위치: [TLS·HTTP](../docs/network/tls-http.md).
- 확인한 원천: [RFC 9112 §6](https://www.rfc-editor.org/rfc/rfc9112.html#section-6), [RFC 5246 §7.3](https://www.rfc-editor.org/rfc/rfc5246.html#section-7.3), [RFC 8446 §2](https://www.rfc-editor.org/rfc/rfc8446.html#section-2), [curl timer](https://curl.se/libcurl/c/CURLINFO_APPCONNECT_TIME.html), [CA/B Forum BR 2.3.1](https://cabforum.org/working-groups/server/baseline-requirements/requirements/).
- 채택: TE/CL 이전의 HEAD·상태·CONNECT 우선 조건, sender 금지·recipient 처리·연결 종료, 일반 TLS full handshake 2/1 RTT 모델, 발급일별 공개 신뢰 TLS 인증서 398/200/100/47일 최대값.
- 쓰지 않은 해석: 두 헤더 동시 송신을 정상으로 허용, appconnect=순수 TLS RTT, 모든 연결의 고정 왕복 보장, 사설 PKI 포함 모든 인증서에 BR 적용, 변경일의 소급 만료. 실제 endpoint 검사·인증서 발급 없음.

### G12. SNMP·MTU

- 쓴 위치: [SNMP](../docs/network/snmp-and-device-models.md), [링크·MTU](../docs/network/layers-and-routing.md).
- 확인한 원천: [RFC 3584 §4.2.2.1](https://www.rfc-editor.org/rfc/rfc3584.html#section-4.2.2.1), [RFC 2863](https://www.rfc-editor.org/rfc/rfc2863.html), [RFC 1191](https://www.rfc-editor.org/rfc/rfc1191.html), [RFC 4821](https://www.rfc-editor.org/rfc/rfc4821.html), [RFC 8899](https://www.rfc-editor.org/rfc/rfc8899.html).
- 채택: v1 Counter64 불가와 v2c/v3 가능, 속도별 카운터 요구, ifSpeed 포화·ifHighSpeed 단위, IPv4 ICMP 기반 PMTUD와 probe 기반 방법.
- 수정한 단서: RFC 2863 §3.1.6은 650 Mbit/s 이상, MIB conformance는 초과로 표현해 정확한 경계를 무조건 통일하지 않았다. RFC 8899는 datagram DPLPMTUD이며 TCP 전반의 규약으로 인용하지 않았다. 실제 장비 질의·SET·probe·캡처 없음.

## 2. 자체 피드백과 출판 연결

새 5장을 `book.json`·분야 README·학습 안내·용어집·지표 참조표·coverage에 연결했다. 범위를 상세 97장으로 갱신하되 과거 92장 당시의 실행·검증 기록은 역사적 범위로 남겼다. 새 예시 20개의 본문 결과 문자열과 산술, 확률·resize 해석 3개를 기존 `verify_examples.py`에 연결했다.

자체 재검토에서 `memory.events.oom`을 모든 실제 할당 실패와 같게 쓰지 않도록 수정했다. OpenMetrics bucket 경계는 canonical `1.0`으로 고쳤다. WatchList 기본값 근거는 정의 이름만 있는 코드 대신 공식 gate 이력과 실제 client 기본값 코드로 연결했다. 실습 예정·문서 대조·합성 산술을 실행 완료로 읽을 수 있는 문장은 분리했다.

장별 hash와 검토 초점은 [chapter-review.json](chapter-review.json)에 기록한다. 이는 검토한 본문과의 일치 검사이며 hash 생성만으로 사실 검토를 대신하지 않는다. 최종 명령 결과와 HTML 화면 검사의 적용 범위는 [검증 기록](../docs/validation.md)에 남긴다.

### 검증 명령과 결과

| 명령 | 결과 |
| --- | --- |
| `python -X utf8 -B scripts/check_docs.py` | PASS: Markdown 121개·상세 97장·목차·로컬 연결·검토 hash |
| `python -X utf8 -B scripts/verify_examples.py` | PASS: 57개 원문·169개 산술/해석 |
| `python -X utf8 -B scripts/verify_contracts.py` | PASS: 어댑터 경계 22개·계산 28개·기존 실행 근거 |
| `python -X utf8 -B scripts/verify_revision.py` | PASS: 31개 보존 시나리오·입력 hash·12개 계산·Linux 시계 추가 근거 |
| `python -X utf8 -B scripts/build_book.py --check` | PASS: 119개 원문과 생성 일치 |
| `python -X utf8 -B scripts/build_html.py --check` | PASS: 원문·고정 renderer와 생성 일치 |
| `git diff --check` | PASS: 변경 내용의 공백 검사 |

두 통합본은 각 build script로 재생성했다. 초회 구조 검사에서 검토 디렉터리를 대상으로 한 fragment 링크가 검사 범위 밖임을 확인해 파일 링크로 바꾼 뒤 재검사했다. 저장소의 `eol=lf` 규칙에 맞춰 이번 수정 파일의 줄바꿈을 정규화하고 장별 hash를 연결했다. HTML 화면·새 Linux 실험·전체 외부 URL 재조회는 위 PASS의 범위에 포함하지 않는다.

## 3. 2c·2d와 3라운드 제안

2c에서는 특히 G2의 버전 경계, G3의 view 변화·권한, G4/G5의 stability·단위, G7 Task Manager 빌드 범위, G12 RFC 내부 경계 문구를 재대조한다. 2d에서는 전달된 결과의 입력 hash·원시 로그·반증 조건부터 확인하고 출판 경로로 승격한다. 기존 1.1 결과를 덮어쓰지 않는다.

다음은 **3라운드 계획만**이며 이번에 사실 본문을 작성하거나 실험하지 않았다.

| 우선순위 | 주제 | 계획상 작업·비용 |
| --- | --- | --- |
| 1 | OOM·reclaim vmstat, PSI 활성 조건·irq, 프로세스 RSS 세부·I 상태 | 커널 버전별 원천·읽기 계약 대조. 실측이 필요하면 격리된 노드의 별도 승인 범위·자원 한도 설계 |
| 1 | MySQL 잠금·지속성·GTID·lag NULL, SQL Server version store·AG·권한 | 엔진별 버전·권한 표부터 작성. 실행은 별도 설치 자산·라이선스·메모리 계획 후 제안 |
| 1 | Exponential/native histogram·sketch, NTP/PTP 오프셋 | 수학 예시·정보 손실 비교부터 작성. 시계 정확도 실험은 외부 기준이 있어야 별도 판정 |
| 2 | JFR·JMX·EventPipe·Node ELU, HAProxy stats·로그 파이프라인 손실 | 공식 계측 API·부하·권한·누락 카운터 연결; agent 전수 실행 인증은 분리 |
| 2 | Oracle ASH/AWR와 Diagnostics Pack | 공식 계약·기능별 라이선스 범위를 확인한 문서 작성; 미확인 사용 권한을 추정하지 않음 |
| 2 | GPU DCGM profiling·XID·ECC·throttle | GPU 모델·driver·가상화 capability 표. 지원 GPU 없는 환경에서 실행 검증을 주장하지 않음 |

이 표의 비용은 자산·권한·실험 경계의 종류를 나타낸다. 아직 정하지 않은 대상의 실행 시간이나 메모리 수치를 임의로 확정하지 않았다.

## 4. 2d: native 데이터 디렉터리 수정 검토

Claude의 DrvFs 예외 설계에 동의한다. PostgreSQL의 데이터 디렉터리만 `mkdtemp`가 만든 Linux native 경로로 옮기고 mode 0700을 확인하며, 결과·로그·일반 workspace는 저장소 `.lab-runs/`에 둔다. [PostgreSQL 18 initdb](https://www.postgresql.org/docs/18/app-initdb.html), [WSL 파일 권한](https://learn.microsoft.com/en-us/windows/wsl/file-permissions)의 구분과 실행 실패 로그에 부합한다. `.tools/pg18`의 기존 공식 도구를 재사용하고 설치·sudo·서비스 등록·외부 DB 접속은 추가하지 않았다.

성공한 `postgresql-3.json`의 primary·standby 경로와 `Connection`의 `SHOW data_directory` 대조가 모두 같은 native root를 사용한다. 결과의 mode는 `0700`, `native_directories_removed=true`, `cleanup.completed=true`이다. 코드 변경은 성공 경로와 별도로 다음 실패 경로를 보완할 필요가 있었다.

| 확인한 결함 | 이번 수정 | 확인 범위 |
| --- | --- | --- |
| 원래는 resolve/chmod/stat 검사가 끝난 뒤 소유 경로를 등록하여 검사 실패 시 정리 대상에서 빠질 수 있음 | mkdtemp 직후 등록, 검증 전 mode/verified 상태도 기록 | 합성 resolve 실패·chmod 실패·잘못된 mode에서 디렉터리 제거 확인 |
| native rmtree 실패를 cleanup에 적어도 status/exit code가 성공으로 남을 수 있음 | 실패를 status=error·exit=1에 반영 | 합성 삭제 실패에서 retained 경로와 실패 상태 확인 |
| 로그 close/read 실패가 이후 정리까지 중단시킬 수 있음 | 로그 오류를 모아 기록하면서 native 정리 계속 시도 | 합성 로그 읽기 실패에서 native 제거 확인 |
| 소유 프로세스 종료 실패 뒤 데이터 삭제 위험 | 종료 실패 시 native/workspace를 보존하고 정리 실패 기록 | 합성 stop 실패에서 데이터 보존 확인 |
| native 예외의 실행 범위 | Linux amd64·일반 사용자 제한과 단순 prefix 검사 | Windows에서 native 경로를 실제 생성하지 않음 |

[공통 모듈](../scripts/lab_r2_common.py), [실패 검사·native smoke](../scripts/verify_lab_r2_cleanup.py)를 수정·추가했다. 출력 `open('x')`의 덮어쓰기 방지도 여섯 합성 경우에서 확인했다. 실제 PostgreSQL 실행기는 추가 수정하지 않았다.

성공한 네 실험에 사용된 공통 모듈은 [보존 파일](../labs/archive/lab_r2_common_2026_10_05.py)에 byte 단위로 복사했다. SHA256은 `260f654988729f0119f17e50a6c9b8fe2cf89f7edf697170ffe45338e8af8518`이다. 새 helper를 옛 실험에서 실행한 것처럼 hash를 덮지 않았다. **수치 출판을 위한 네 서버 실험 재실행은 필요하지 않다.** 수정 helper의 Linux native 성공 경로만 아래 smoke로 Claude가 확인한다. 이 Codex 턴에는 저장소 밖 파일을 만들거나 수정하지 않았다.

## 5. 2d: 최종 실행 결과 출판과 해석

원시 파일은 아래 경로로 byte 단위 복사했다. 입력 hash가 현재 파일과 맞는지 먼저 확인한 다음 공통 모듈만 보존 경로로 연결했다. [provenance](../review/evidence-provenance.json)의 파일 hash가 맞는 기존 출판 결과에만 보존 입력 대체를 허용하며, 새로운 실행 결과는 실제 현재 입력 hash를 검사한다. [verify_review_r2](../scripts/verify_review_r2.py)의 `--published`는 `.tools/`·비공개 임시 결과 없이 실행되고 [verify_revision](../scripts/verify_revision.py)에서도 호출된다.

| 원본 | 출판 위치 | SHA256 | 판정 |
| --- | --- | --- | --- |
| `.lab-runs/r2/kubernetes.json` | [Kubernetes](../labs/results/1.1-r2-kubernetes.json) | `f97eb0a3b048f1b023aca532e72d62118c5e67b971b97feeeb35af12ab445341` | supported 14·refuted 2 |
| `.lab-runs/r2/prometheus-3.json` | [promtool](../labs/results/1.1-r2-prometheus.json) | `424ee8a03016848ef16f2f6ec061357f11912055b7466116f02bb4dd9d03ce06` | supported 2 |
| `.lab-runs/r2/otel-3.json` | [Collector](../labs/results/1.1-r2-otel.json) | `0f451a5e25da770c27ca812aaeaa3974fde9f84217bdc32b03dd6cf99717d64f` | supported 14 |
| `.lab-runs/r2/postgresql-3.json` | [PostgreSQL](../labs/results/1.1-r2-postgresql.json) | `3409ea201ab70cc27ee895a1d531f2cb38937d613eef87743003f39c4cf06873` | supported 4 |

실행은 Claude, 원시 입력·결과 대조와 원고 반영은 Codex가 담당했다. 환경은 전달된 Ubuntu 24.04 WSL·커널 6.18.33.2이며 결과가 Python 3.12.3과 Linux 식별자를 기록한다. 36개 중 지지 34개·반증 2개라는 사실을 보편적 제품 보장으로 바꾸지 않았다. `postgresql.json`의 initdb 실패와 공통 입력 변경 때문에 대체된 `prometheus.json`·`otel.json`·`postgresql-2.json`·`prometheus-2.json`·`otel-2.json`은 존재 이력만 남기고 출판하지 않는다.

### Kubernetes: cache-on 200은 별도 보존된 새 증거다

1.34.1·1.37.0은 최신 patch 1.34.12·1.37.1이 아니다. 네 구성은 새 etcd 데이터 디렉터리를 각각 사용했고 `feature_gate_overrides={}`이다. 모든 구성의 metric은 `ListFromCacheSnapshot` Beta=1을 기록한다. cache-on 두 구성은 compaction 뒤 Exact RV=1 LIST에서 HTTP 200·`ConfigMapList`·RV 문자열 `"1"`·빈 items를 반환했다. cache-off 두 구성은 410이다. 첫 continue 요청도 이 조건에서 각각 200/410이었다. 이는 token을 일정 시간 기다려 만료시킨 실험이 아니다.

“compaction만으로 Exact LIST의 410을 얻는다”라는 가설은 두 cache-on 구성에서 반증됐다. 1라운드의 미보존 예비 200을 근거로 되살리지 않았으며 새 결과만 인용한다. gate를 on/off로 분리하지 않아 `ListFromCacheSnapshot`을 단독 원인으로 확정하지 않는다.

etcd [3.6.4](https://github.com/etcd-io/etcd/blob/v3.6.4/server/storage/mvcc/kvstore.go#L103)·[3.7.0](https://github.com/etcd-io/etcd/blob/v3.7.0/server/storage/mvcc/kvstore.go#L104)의 새 MVCC store는 currentRev=1로 시작한다. 실행기는 새 store의 API 준비 후 namespace와 ConfigMap을 생성한다. 따라서 RV=1의 빈 목록은 초기 상태와 **부합한다는 추론**이다. namespace 생성 응답이나 RV=1의 별도 etcd dump는 저장하지 않았으므로 그 snapshot의 상태를 독립 검증했다고 쓰지 않았다. 이 경계는 [본문](../docs/kubernetes/inventory-consistency.md)에 그대로 반영했다.

pagination·selector 이탈은 네 구성에서 지지됐다. RV 관측은 1.34.1 두 구성 205/206/207, 1.37.0 cache-on 218/219/220·cache-off 217/218/219였다. 같은 객체의 순서 증가 관측이 규약 전체의 증명은 아니다. 1.34의 숫자 증가를 정렬 권한으로 바꾸지 않고, 1.35 이상 규약의 자원·클러스터 범위를 유지했다.

### Collector: 내부 최종 실패와 queue 수락 경계

0.162.0 core, HTTP JSON, debug 로그·detailed 내부 지표, queue true/false·`wait_for_result=false`를 대조했다. 각 실험은 metric을 생성하는 primer 때문에 `send_failed_spans`가 이미 2인 상태로 probe를 시작한다. 재시도 진행 중 관측값은 2였고, 소진 후 4가 됐다. probe span 2개의 실패 증가이며 최초 0→4의 네 probe 실패가 아니다. 표본 간 정확한 증가 시각이나 다른 exporter의 구현까지 보장하지 않는다.

부분 거절은 `Partial success response` 로그의 `dropped_spans=1`·목적지 오류 메시지, probe 전송 1회, upstream 200·빈 partialSuccess, send_failed 증가 0으로 확인했다. queue-on이면 목적지 차단 해제보다 upstream 완료가 앞서고, queue-off이면 뒤였다. 실제 영속 저장은 실험하지 않았다. [본문](../docs/product/telemetry-delivery-contracts.md)

`otlp_http`와 `otlphttp`는 둘 다 구성 검사가 exit 0이었으며 실제 전송은 `otlp_http/lab`로 실행했다. 이름 변경을 0.150 도입으로 쓰지 않았다. [0.144.0 core 릴리스](https://github.com/open-telemetry/opentelemetry-collector/releases/tag/v0.144.0)가 새 이름과 deprecated alias를 명시한다.

### PostgreSQL과 promtool

PostgreSQL 18.6의 네 원천을 유지하는 동안 VACUUM이 대상 128행 또는 catalog 24행을 제거하지 못했고, 원천 해제 뒤 제거했다. 물리 slot 사용 시 sender xmin NULL·slot xmin 815, 연결 강제 종료 후 inactive slot의 xmin 유지도 확인했다. slot 없는 standby에서는 sender xmin 813을 관측했다. `n_dead_tup`은 각 대상에서 0이 됐지만 `datfrozenxid`는 모든 표본에서 744였다. 회수와 freeze를 같은 성공 판정으로 합치지 않는다. 실행기의 activity 필터는 walsender 중복 행을 수집하지 않았으므로 view 사이 중복 가능성은 소스 검토로만 설명한다. [본문·수치](../docs/database/postgresql-operations.md)

promtool 3.13.4·3.15.0 모두 기존 `labs/prometheus` 규칙 검사와 테스트(표현식 8개·alert 5개)를 통과했다. 새 서버 scrape·exemplar·시작 timestamp·WAL 실행 근거로 확장하지 않았다. [재현 방법](../docs/cross-domain/reproducible-labs.md)에 실제 명령과 후속 재현 예시의 범위를 구분했다.

## 6. 2c 지적의 항목별 판정

모든 판정은 2026-10-05에 공식 문서·고정 버전 소스 또는 전달된 원시 결과를 직접 대조한 범위다. “수용”은 지적의 방향을 수용한다는 뜻이며 제시된 문장을 그대로 전재했다는 뜻은 아니다. 해당 환경을 실행하지 않은 설명은 본문에 원천 검토로 표시한다.

| ID | 판정 | 직접 확인한 근거·수정 범위 | 바꾼 파일 |
| --- | --- | --- | --- |
| N1 | 수용 | 6.12 [`tcp_create_openreq_child`](https://github.com/torvalds/linux/blob/v6.12/net/ipv4/tcp_minisocks.c#L629)의 PassiveOpens 증가, [accept queue 검사](https://github.com/torvalds/linux/blob/v6.12/net/ipv4/tcp_ipv4.c#L1757)가 child 생성보다 앞섬. SYN 도착률과 accept 완료 수 모두 배제, TFO 경계 명시 | [Linux 스택](../docs/network/linux-stack-counters.md) |
| N2 | 수용 | [수정 commit](https://github.com/torvalds/linux/commit/a46d0ea5c94205f40ecf912d1bb7806a8a64704f), v6.9/v6.10 `tcp_set_state` 차이와 현재 6.6.y·6.1.y·5.15.y 코드를 대조. 최초 backport patch 번호는 확정하지 않음; 표·Q1에 수정 포함 조건 | [Linux 스택](../docs/network/linux-stack-counters.md) |
| N3 | 부분 수용 | [udp.c 주 수신 경로](https://github.com/torvalds/linux/blob/v6.12/net/ipv4/udp.c#L2065)의 ENOMEM/ENOBUFS와 MemErrors 수용. 다만 [multicast skb_clone 실패](https://github.com/torvalds/linux/blob/v6.12/net/ipv4/udp.c#L2284)도 RcvbufErrors 증가. [송신 ENOBUFS 은폐](https://github.com/torvalds/linux/blob/v6.12/net/ipv4/udp.c#L983)·SOCK_NOSPACE 경로도 확인하여 전용 원인 지표로 단정하지 않음 | [Linux 스택](../docs/network/linux-stack-counters.md) |
| N4 | 수용 | [RFC 3584 §4.2.2.1](https://www.rfc-editor.org/rfc/rfc3584.html#section-4.2.2.1)은 multi-lingual responder의 v1 요청 처리. GET의 noSuchName과 GETNEXT의 Counter64 건너뛰기 구분 | [SNMP](../docs/network/snmp-and-device-models.md) |
| N5 | 수용 | PMTUD 자체는 RFC 1191, ICMP가 막힌 black hole은 [RFC 2923 §2.1](https://www.rfc-editor.org/rfc/rfc2923.html#section-2.1)로 분리 | [계층·경로](../docs/network/layers-and-routing.md) |
| K1 | 수용 | v1.37.0 [`GetContainerOOMScoreAdjust`](https://github.com/kubernetes/kubernetes/blob/v1.37.0/pkg/kubelet/qos/policy.go#L45)의 `1000 + (-997) = 3`, 상한 999·정수 계산·Pod-level request·sidecar 보정 확인. 단순 식의 적용 조건 명시 | [자원 압박](../docs/kubernetes/pressure-and-termination.md) |
| K2 | 수용 | [node-pressure 문서](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/#memory-signals)와 [v1.37 gate 정의](https://github.com/kubernetes/kubernetes/blob/v1.37.0/pkg/features/kube_features.go#L1672): HugepageAwareEviction Beta·기본 true·hugepage 총용량 차감. Summary API와의 실제 값 차이는 미확인으로 채택하지 않음 | [자원 압박](../docs/kubernetes/pressure-and-termination.md) |
| K3 | 수용 | [cgroups 페이지](https://kubernetes.io/docs/concepts/architecture/cgroups/)의 Deprecated since v1.35·failCgroupV1 기본 true를 [1.31 유지보수 전환](https://kubernetes.io/blog/2024/08/14/kubernetes-1-31-moving-cgroup-v1-support-maintenance-mode/)과 구분 | [자원 압박](../docs/kubernetes/pressure-and-termination.md) |
| K4 | 수용 | [v1.37 ComputePodQOS](https://github.com/kubernetes/kubernetes/blob/v1.37.0/pkg/apis/core/helper/qos/qos.go): 해당 gate·설정 분기에서 Pod-level 값이 컨테이너별 값 대신 결정. nil/비어 있는 값까지 무조건 대체한다고 확대하지 않음 | [자원 압박](../docs/kubernetes/pressure-and-termination.md) |
| K5 | 수용 | [Pod container state](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#container-states)의 현재 terminated와 이전 lastState를 모두 읽도록 보강. restartPolicy Never의 현재 종료도 포함 | [자원 압박](../docs/kubernetes/pressure-and-termination.md) |
| K6 | 수용 | [System Metrics](https://kubernetes.io/docs/concepts/cluster-administration/system-metrics/)로 `/metrics/cadvisor`, `/metrics/resource`, `/metrics/probes` 근거 교체. Node Metrics Data는 Summary/resource 경로에 한정 | [자원 압박](../docs/kubernetes/pressure-and-termination.md) |
| K7 | 수용 | [v0.37.0 ListOptions.Continue 주석](https://github.com/kubernetes/apimachinery/blob/v0.37.0/pkg/apis/meta/v1/types.go#L426)에 새 continue token의 최신 snapshot·불일관성. 정확한 주석 위치는 ListMeta가 아닌 ListOptions. [API concepts](https://kubernetes.io/docs/reference/using-api/api-concepts/)의 기본 5분 설명과 별개로 “같다고 가정하지 않음”을 설계 제안으로 표시 | [수집](../docs/kubernetes/collection.md) |
| K8 | 부분 수용 | [MemoryQoS gate](https://github.com/kubernetes/kubernetes/blob/v1.37.0/pkg/features/kube_features.go#L1845), [설정](https://github.com/kubernetes/kubernetes/blob/v1.37.0/staging/src/k8s.io/kubelet/config/v1beta1/types.go#L899), [memory.high 구현](https://github.com/kubernetes/kubernetes/blob/v1.37.0/pkg/kubelet/kuberuntime/kuberuntime_container_linux.go#L203): 기본 nil이면 high 설정 없음. [커널](https://docs.kernel.org/admin-guide/cgroup-v2.html#memory)상 high는 강한 reclaim·task throttling이며 “회수가 지연”으로 쓰지 않음. 직접 OOM 발동과 구분하되 max OOM 가능성은 유지 | [자원 압박](../docs/kubernetes/pressure-and-termination.md) |

| ID | 판정 | 직접 확인한 근거·수정 범위 | 바꾼 파일 |
| --- | --- | --- | --- |
| P1 | 수용·오류 정정 | [13 release notes](https://www.postgresql.org/docs/13/release-13.html): 이전에도 execution time만 수집. 12 total_time→13 total_exec_time은 실행 시간 의미를 연속 매핑; 계획 시간은 별도 선택 항목, [track_planning 기본 off](https://www.postgresql.org/docs/13/pgstatstatements.html). 버전 업그레이드/reset을 넘어 누적값 자체를 이어 붙인다는 뜻은 아님 | [PG 운영](../docs/database/postgresql-operations.md) |
| P2 | 수용 | [18.6 walsender](https://github.com/postgres/postgres/blob/REL_18_6/src/backend/replication/walsender.c#L2553)의 slot 사용 시 PGPROC xmin 비우기, slot 없을 때 sender xmin. 새 [실측](../labs/results/1.1-r2-postgresql.json)의 slot xmin=815·sender NULL과 slot 없는 sender 813 부합. activity SQL은 backend_type으로 walsender 분리 | [PG 운영](../docs/database/postgresql-operations.md) |
| P3 | 수용·구체화 | [Squid PG states](https://docs.ceph.com/en/squid/rados/operations/pg-states/)의 peered 상태는 client I/O 불가. 이미 있던 설명에 읽기도 포함함을 명시. [19.2.3 OSDMonitor](https://github.com/ceph/ceph/blob/v19.2.3/src/mon/OSDMonitor.cc#L7773)의 EC 기본 k+min(1,m−1), 4+2→5 예시를 산술 검사에 연결 | [용량·보호](../docs/storage/capacity-and-protection.md), [산술 검사](../scripts/verify_examples.py) |
| P4 | 수용 | [18 datetime](https://www.postgresql.org/docs/18/functions-datetime.html#FUNCTIONS-DATETIME-CURRENT)의 가장 최근 command message. 하나의 simple Query에 여러 SELECT가 있으면 같은 값 가능; 원자적 통계 snapshot 아님. 과거 실행 SQL·hash는 유지 | [PG 운영](../docs/database/postgresql-operations.md), [DB 수집 계약](../docs/database/collection-contracts.md) |
| P5 | 수용 | [17 릴리스](https://www.postgresql.org/docs/17/release-17.html), [17 진행 view](https://www.postgresql.org/docs/17/progress-reporting.html), [18 통계 view](https://www.postgresql.org/docs/18/monitoring-stats.html), [18 진행 view](https://www.postgresql.org/docs/18/progress-reporting.html), [17 slot](https://www.postgresql.org/docs/17/view-pg-replication-slots.html), [18 wraparound](https://www.postgresql.org/docs/18/routine-vacuuming.html#VACUUM-FOR-WRAPAROUND), [failsafe](https://www.postgresql.org/docs/18/runtime-config-vacuum.html#GUC-VACUUM-FAILSAFE-AGE). 제거·이동·rename·신규 컬럼을 분리, warning/거부/failsafe를 다른 경계로 설명 | [PG 운영](../docs/database/postgresql-operations.md) |
| T1 | 수용 | [SDK ProbabilitySampler](https://opentelemetry.io/docs/specs/otel/trace/sdk/#probabilitysampler)는 Development·non-composable. [ComposableProbability](https://opentelemetry.io/docs/specs/otel/trace/sdk/#composableprobability)와 구분. TraceIdRatioBased 절 자체의 Stable 상태와 deprecation은 별개 | [sampling](../docs/application/trace-sampling-and-context.md) |
| T2 | 수용 | [SDK Presumption of TraceID randomness](https://opentelemetry.io/docs/specs/otel/trace/sdk/#presumption-of-traceid-randomness): rv는 선택 explicit randomness, 없으면 R은 TraceID 하위 56bit. 무작위성 전제·th 전달 손실·미상 확률을 여전히 조건으로 둠 | [sampling](../docs/application/trace-sampling-and-context.md) |
| T3 | 수용 | counter 차분 12−7=5는 그 사이 reset/교체가 없을 때만 유효. [OTel reset 모델](https://opentelemetry.io/docs/specs/otel/metrics/data-model/#resets-and-gaps)과 식을 대조하고 전제를 표에 명시 | [지표 문맥](../docs/foundations/metric-context-and-start-time.md) |
| T4 | 부분 수용 | [HTTP 경계 advice](https://opentelemetry.io/docs/specs/semconv/http/http-metrics/#metric-httpserverrequestduration)와 [SDK Explicit Bucket](https://opentelemetry.io/docs/specs/otel/metrics/sdk/#explicit-bucket-histogram-aggregation)의 배열 추가. SDK 기본은 SHOULD 권고이며 모든 SDK가 반드시 같은 경계를 쓴다고 단정하지 않음 | [semconv](../docs/application/semantic-conventions.md) |
| T5 | 부분 수용 | [Prometheus 3.15 flag](https://github.com/prometheus/prometheus/blob/v3.15.0/docs/feature_flags.md#exemplars-storage)의 기본 off·메모리 원형 버퍼·WAL 기록 및 [exemplar.go](https://github.com/prometheus/prometheus/blob/v3.15.0/tsdb/exemplar.go) 확인. WAL 지속성과 개수 제한 조회 버퍼를 분리해 “항상 WAL 기간 동안 조회”로 해석하지 않음. [text 0.0.4/OM 형식](https://prometheus.io/docs/instrumenting/exposition_formats/) 차이 반영 | [지표 문맥](../docs/foundations/metric-context-and-start-time.md) |
| T6 | 수용 | [3.15 flag](https://github.com/prometheus/prometheus/blob/v3.15.0/docs/feature_flags.md)의 created-timestamp-zero-ingestion은 전역 기본 scrape_protocols를 PrometheusProto 우선으로 변경. 명시 설정과 `_created` 시계열 비용 구분 | [지표 문맥](../docs/foundations/metric-context-and-start-time.md) |
| .NET 추가 | 수용 | [CLR semconv](https://opentelemetry.io/docs/specs/semconv/runtime/dotnet-metrics/)의 generation Required와 collections의 중복 방지 정의. 마지막 heap의 세대별 합산 범위와 GC.CollectionCount 원시값 합산의 차이를 설명 | [semconv](../docs/application/semantic-conventions.md) |

| ID | 판정 | 직접 확인한 근거·수정 범위 | 바꾼 파일 |
| --- | --- | --- | --- |
| M1 | 부분 수용 | Kafka 4.3 [ControllerServer](https://github.com/apache/kafka/blob/4.3.0/core/src/main/scala/kafka/server/ControllerServer.scala), [ControllerMetadataMetricsPublisher](https://github.com/apache/kafka/blob/4.3.0/metadata/src/main/java/org/apache/kafka/controller/metrics/ControllerMetadataMetricsPublisher.java)에서 각 controller에 publisher·전체 offline partition 집계 확인. 합산 금지 수용; 비동기 metadata 적용 때문에 모든 시각의 값 동일성까지 보장하지 않음 | [Kafka](../docs/middleware/kafka.md) |
| M2 | 부분 수용 | [Lambda runtime environment](https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtime-environment.html)의 suppressed init은 별도 INIT 줄 없이 REPORT Duration에 INIT+INVOKE 포함. CloudWatch Duration까지 같은 숫자라는 추론은 채택하지 않음. on-demand 초기 Init의 10초 제한과 invoke 실패 뒤 suppressed init을 동일 사건으로 합치지 않음 | [관리형·서버리스](../docs/cloud/managed-and-serverless.md) |
| M3 | 수용 | [Azure aggregation](https://learn.microsoft.com/en-us/azure/azure-monitor/metrics/metrics-aggregation-explained): 플랫폼의 무수신 0/NULL은 provider 결정, custom metrics는 NULL. 0을 항상 실제 무활동으로 해석하지 않음 | [cloud 지표](../docs/cloud/provider-metrics.md) |
| M4 | 수용 | [Windows Time/Utility](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/cpu-usage-exceeds-100), [Windows 성능](https://learn.microsoft.com/en-us/troubleshoot/windows-server/performance/troubleshoot-performance-problems-in-windows), [commit/pagefile](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/introduction-to-the-page-file) 등으로 행별 근거 연결. Exchange 문서는 실제로 정의한 System Queue Length 행에만 사용하고 서비스별 임계값은 채택하지 않음 | [Windows](../docs/host/windows.md) |
| M5 | 수용 | 공식 [2026-02-17 Kafka 4.2 발표](https://kafka.apache.org/blog/2026/02/17/apache-kafka-4.2.0-release-announcement/)의 canonical 경로 확인·교체 | [Kafka](../docs/middleware/kafka.md) |

### 미검증으로 전달받은 네트워크 단서

- **AttemptFails:** 6.12 IPv4 request socket의 일반 SYN/ACK 재시도 만료 경로를 직접 따라 확인했다. [`reqsk_timer_handler`](https://github.com/torvalds/linux/blob/v6.12/net/ipv4/inet_connection_sock.c#L1149) → [`tcp_syn_ack_timeout`](https://github.com/torvalds/linux/blob/v6.12/net/ipv4/tcp_timer.c#L732)는 TCPTimeouts를 증가시키고 request 제거는 AttemptFails를 올리지 않는다. [`tcp_v4_reqsk_destructor`](https://github.com/torvalds/linux/blob/v6.12/net/ipv4/tcp_ipv4.c#L1218)도 메모리 해제 경로다. 일반 timer 경로에 한정해 [본문](../docs/network/linux-stack-counters.md)에 넣었으며 실제 손실 주입·모든 TFO/IPv6 경로를 실행했다고 쓰지 않았다.
- **TLS 1.2 False Start:** [RFC 7918 §4](https://www.rfc-editor.org/rfc/rfc7918.html#section-4)의 선택 기능으로, handshake 전체 검증 완료 전에 첫 application data를 보낼 수 있음을 [본문](../docs/network/tls-http.md)에 추가했다. 따라서 기본 handshake RTT와 첫 데이터 전송 지연을 구분한다. curl backend별 `time_appconnect` 기록 시각을 직접 확인한 것은 아니므로 그 값이 자동으로 1 RTT 감소한다고 쓰지 않았다.

## 7. 채택하지 않은 확대 해석과 남은 확인

N3의 RcvbufErrors를 항상 소켓 한도 하나로 귀속하지 않았고, K8의 high 동작을 “회수가 지연”으로 쓰지 않았다. T4의 SDK 권고는 모든 구현의 강제 기본값이 아니며, T5의 WAL 지속성은 조회 가능한 메모리 버퍼의 고정 시간 보장이 아니다. M1의 controller 값은 같은 정의를 복제하지만 항상 같은 시각에 일치하지는 않는다. M2의 CloudWatch Duration에 suppressed init이 얼마나 포함되는지는 REPORT 설명만으로 확정하지 않았다.

K7의 정확한 continue 주석 위치는 **ListOptions.Continue**이다. K2의 Summary API와 eviction manager 사이 수치 차이는 이번 원고에서 확정하지 않았다. gate만 바꾸는 Kubernetes 대조 실험과 Lambda 지표·로그 비교는 이번 결과 출판의 선행 조건이 아니며, 수행하려면 별도 후속 범위로 계획한다. 실습 수치나 판정이 추가 답변을 기다리는 상태는 아니다.

Claude에게 필요한 후속 실행은 아래 두 가지다. 첫 명령은 DB·서버를 띄우지 않고 수정 helper가 Linux native 임시 경로에 작은 파일을 만든 뒤 제거하는지만 검사한다. 결과 JSON은 `.lab-runs/`에 남긴다. 두 번째는 이번 생성본의 화면 검사다. 기존 출력 파일이 있으면 첫 명령의 출력 이름을 새로 정한다.

```powershell
wsl -d Ubuntu --cd /mnt/c/project/Domain-Knowledge -- python3 -B scripts/verify_lab_r2_cleanup.py --native-output .lab-runs/r2/native-cleanup-r2d.json
python -X utf8 -B scripts/check_html.py
```

native 성공 경로와 화면 검사 결과는 이 기록에서 아직 PASS로 표시하지 않는다. 네 실습 묶음 전체를 다시 실행할 필요는 없으며, 재현을 원할 경우 본문의 별도 출력 명령을 사용한다.

## 8. 2d 검증 결과

Windows Python에서 다음을 실행했다. 두 build script를 먼저 실행해 통합본을 갱신했다. Linux 서버 실행·화면 검사는 포함하지 않는다.

| 명령 | 결과 |
| --- | --- |
| `python -X utf8 -B scripts/check_docs.py` | PASS: Markdown 121개·상세 97장·로컬 링크 2043개·고유 외부 URL 459개 목록화, 장별 hash |
| `python -X utf8 -B scripts/verify_examples.py` | PASS: 57개 원문·산술/해석 170개 |
| `python -X utf8 -B scripts/verify_contracts.py` | PASS: 어댑터 22개·본문 계산 28개·기존 실행 hash |
| `python -X utf8 -B scripts/verify_revision.py` | PASS: 기존 31개·12개 계산·Linux 시계 추가 근거와 새 출판 판정 36개 |
| `python -X utf8 -B scripts/build_book.py --check` | PASS: 원문 119개와 일치 |
| `python -X utf8 -B scripts/build_html.py --check` | PASS: 원문·고정 renderer와 일치 |
| `python -X utf8 -B scripts/verify_review_r2.py --published` | PASS: 네 결과·입력 hash·34 supported/2 refuted 및 핵심 관측값 |
| `python -X utf8 -B scripts/verify_lab_r2_cleanup.py` | PASS: 저장소 안 fixture의 실패 경로 6개·덮어쓰기 방지 |
| `git -c safe.directory=C:/project/Domain-Knowledge diff --check` | PASS: 공백 검사 |

추가로 HEAD의 과거 결과·archive 8개, 기존 실행기와 Prometheus fixture의 byte 보존을 대조했고, 새 네 결과가 전달된 최종 파일과 byte 단위로 같음을 확인했다. 판 번호 `1.1`·기준일 `2026-10-04`를 유지했다. 새 원고·링크·수치의 검토 초점을 확인한 **상세 20장**의 hash와 이해 확인 문장을 갱신했다. 다른 장의 과거 원천을 이번에 전수 사실 검토했다고 표시하지 않는다. commit·push·브랜치 전환은 수행하지 않았다.
