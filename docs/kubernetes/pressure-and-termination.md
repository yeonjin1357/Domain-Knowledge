# Kubernetes 자원 압박과 종료 원인

> 상태: 검토됨 · 적용 범위: Kubernetes 1.34–1.37, Linux cgroup v2와 명시한 v1 차이 · 원천 확인일: 2026-10-05 · workload 실행 미검증 · 3b 원천 검토: 2026-10-05 (새 실습 결과 미반영)

## 먼저 이해할 상황

“Pod가 메모리 때문에 죽었다”는 설명만으로는 제품의 원인 분류를 정하기 어렵습니다. 컨테이너의 한도에 도달해 커널이 프로세스를 종료했는지, 노드 전체의 부족을 감지한 kubelet이 Pod를 축출했는지에 따라 증거와 복구가 다릅니다. [request와 limit](resources-and-scheduling.md), [cgroup 메모리 계정](../containers/memory-accounting-and-oom.md)을 먼저 구분합니다.

## QoS는 자원 명세의 분류다

컨테이너 수준 CPU·메모리 자원 설정을 사용하는 경우 아래 규칙을 적용합니다. init container도 고려하며, 사용자가 보낸 원본 YAML이 아닌 admission과 defaulting 이후의 객체를 봅니다. 실제 분류는 `status.qosClass`로 확인합니다. [QoS 정의](https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/), [QoS 계산 코드 v1.37.0](https://github.com/kubernetes/kubernetes/blob/v1.37.0/pkg/apis/core/v1/helper/qos/qos.go)

| QoS | 분류 기준 | 보장하지 않는 것 |
| --- | --- | --- |
| Guaranteed | 모든 컨테이너에 양수 CPU·메모리 request와 limit이 있고, 각 자원에서 request=limit | 노드 장애·디스크 압박·자기 한도 OOM에 대한 생존 보장 |
| BestEffort | CPU·메모리 request/limit이 없음 | 유휴 자원의 장기 확보 |
| Burstable | 위 두 조건 사이 | 실제 사용량이 항상 request 이하라는 보장 |

1.34부터 기본 활성 Beta인 Pod-level resources를 사용하는 1.37의 해당 분기에서는 **컨테이너별 값 대신 `.spec.resources`로 QoS를 결정**합니다. 두 자원의 request=limit인 Pod-level Guaranteed 조건이 있으므로 컨테이너 필드만 재계산하면 오분류할 수 있습니다. 실제 코드는 gate와 Pod-level 자원 설정 여부를 검사하므로 비어 있는 `.spec.resources`의 존재만으로 분기를 단정하지 않습니다. Pod-level resize와 컨테이너 resize의 단계도 구분합니다. [Pod-level 규칙](https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/#guaranteed), [1.37 ComputePodQOS](https://github.com/kubernetes/kubernetes/blob/v1.37.0/pkg/apis/core/v1/helper/qos/qos.go)

## 노드 압박을 감지하는 신호와 축출 순서

Linux의 kubelet eviction 신호 `memory.available`은 `node capacity − node memory working set`으로 산출합니다. `/proc/meminfo`의 `MemAvailable`을 그대로 읽은 값이 아닙니다. kubelet의 working set 계산에서는 `inactive_file`을 회수 가능하다고 보고 제외하는 점도 유의합니다. [eviction 신호](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/#eviction-signals)

**1.37의 예외:** `HugepageAwareEviction`은 Beta·기본 활성입니다. hugepage를 구성한 노드에서는 eviction manager가 쓰는 `memory.available`에서 노드의 hugepage 총용량을 추가로 뺍니다. memory cgroup working set이 hugetlb 할당을 계정하지 않아 여유가 부풀려지는 것을 보정합니다. 사용 중인 hugepage만 빼는 식이 아니므로 제품은 보정 여부를 함께 보존합니다. [hugepage 보정](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/#memory-signals), [gate 이력](https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/)

**3라운드 코드 확인(2026-10-05): 이 보정은 Summary API에도 반영됩니다.** v1.37.0 `summaryProviderImpl.Get`과 `GetCPUAndMemoryStats`는 gate가 켜져 있으면 `adjustForHugePages`를 호출한 MemoryStats를 `summary.node.memory`에 넣습니다. `availableBytes`에서 Node의 hugepage Capacity 합계를 빼고 0을 하한으로 사용합니다. workingSetBytes 자체를 바꾸는 함수는 아니며, 값·Node가 없거나 hugepage 총용량이 0이면 보정하지 않습니다. 그러므로 gate가 적용된 Summary의 availableBytes에 제품이 hugepage 용량을 다시 빼면 이중 차감입니다. [v1.37.0 summary.go](https://github.com/kubernetes/kubernetes/blob/v1.37.0/pkg/kubelet/server/stats/summary.go)

| 신호 | 단위·범위 | 추가로 확인할 것 |
| --- | --- | --- |
| `memory.available` | byte 또는 capacity 대비 비율 | 노드 working set·시스템 daemon 사용량·cgroup OOM |
| `nodefs.available`, `nodefs.inodesFree` | 파일시스템 여유 byte / inode 수 | 로그·emptyDir·쓰기 계층, 실제 mount |
| `imagefs.available`, `imagefs.inodesFree` | 이미지 전용 파일시스템이 있는 경우의 여유 | runtime이 보고한 분리 구성 |
| `containerfs.*` | 지원 구성의 컨테이너 쓰기 계층 파일시스템 | Kubernetes·runtime·feature gate 지원 여부 |
| `pid.available` | PID 여유 수 | 프로세스·스레드 소비, 노드 PID 제한 |

soft 임계는 지정한 grace 기간 동안 부족이 지속되어야 하며, hard 임계는 이 유예 없이 반응합니다. soft eviction의 Pod 종료 유예도 별도 설정을 봅니다. node-pressure eviction은 Eviction API를 통한 자발적 중단과 달라 PDB를 존중한다고 가정할 수 없습니다. 먼저 노드 자원을 회수한 뒤 Pod 축출이 필요하면 **request 초과 여부 → Pod Priority → request 대비 사용량**을 고려합니다. 디스크·PID는 자원별 ranking 조건이 달라 “항상 BestEffort → Burstable → Guaranteed”라는 고정 정렬로 구현하지 않습니다. [축출과 순위](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/#pod-selection-for-kubelet-eviction), [ranking 코드](https://github.com/kubernetes/kubernetes/blob/v1.37.0/pkg/kubelet/eviction/helpers.go)

## 커널 OOM 선택과 컨테이너의 종료 범위

Linux kubelet **1.37.0 구현**의 `oom_score_adj`는 Guaranteed `−997`, BestEffort `1000`입니다. 일반 Burstable 컨테이너는 `1000 − (1000 × memoryRequestBytes / machineMemoryCapacityBytes)`를 정수 나눗셈으로 계산하고 하한 **3**, 상한 999로 제한합니다. 설명 문서의 하한 2보다 고정 버전 코드의 `1000 + guaranteedOOMScoreAdj = 3`을 우선합니다. Pod-level request를 나누는 보정과 재시작 가능한 init container(sidecar) 보정이 있어 이 기본 식 하나로 모든 컨테이너 값을 재계산하지 않습니다. `system-node-critical`에도 별도 규칙이 있습니다. 이 값은 kernel OOM 선택을 조정하며 kubelet eviction 순위 자체가 아닙니다. [1.37 정책·정수 계산](https://github.com/kubernetes/kubernetes/blob/v1.37.0/pkg/kubelet/qos/policy.go), [회귀 테스트](https://github.com/kubernetes/kubernetes/blob/v1.37.0/pkg/kubelet/qos/policy_test.go)

cgroup v2 Linux의 kubelet 설정 `singleProcessOOMKill`은 기본값이 `false`입니다. 이 경우 컨테이너 cgroup에 `memory.oom.group`을 설정하는 동작을 사용합니다. `true`이면 이 flag 설정을 막아 프로세스를 개별 종료하는 v1 방식에 가깝게 합니다. kernel의 `memory.events`에서 `oom`은 한도에 도달해 할당이 실패할 상황에 이른 횟수입니다. 모든 할당 실패가 이 계정에 들어가거나 모두 kill로 이어지는 것은 아닙니다. `oom_kill`은 OOM killer가 종료한 프로세스 수, `oom_group_kill`은 group OOM 발생 수를 읽습니다. `memory.events`는 하위 계층 사건도 포함할 수 있으므로 `memory.events.local`과 범위를 구분합니다. [kubelet 설정](https://kubernetes.io/docs/reference/config-api/kubelet-config.v1beta1/), [cgroup v2](https://docs.kernel.org/admin-guide/cgroup-v2.html#memory-interface-files)

group kill에도 커널의 예외가 있으므로 “모든 프로세스가 반드시 함께 종료된다”로 일반화하지 않습니다. 특히 `oom_score_adj=-1000`인 task는 제외됩니다. OOM 사건 횟수, 종료 프로세스 수, 컨테이너 재시작 수는 서로 다른 단위입니다. [memory.oom.group 정의](https://docs.kernel.org/admin-guide/cgroup-v2.html#memory-interface-files)

## OOMKilled와 Evicted를 증거로 나눈다

| 관측 | 지지하는 설명 | 추가 증거·확정하지 못하는 점 |
| --- | --- | --- |
| `containerStatuses[].state.terminated.reason=OOMKilled` 또는 `lastState.terminated.reason=OOMKilled` | runtime이 현재 또는 직전 컨테이너 종료를 OOM으로 보고 | `restartPolicy: Never`로 재시작하지 않은 경우 현재 `state`도 확인; cgroup·kernel 로그로 한도 OOM과 노드 OOM 구분 |
| Pod `phase=Failed`, `reason=Evicted`와 압박 관련 message | kubelet의 Pod 축출 | node condition, eviction 신호, kubelet event/log의 시간순서 |
| exit code 137만 존재 | SIGKILL과 일치하는 종료 코드일 수 있음 | OOM의 단독 증거 아님; 다른 강제 종료도 가능 |
| `memory.events.oom_kill` 증가, 재시작 없음 | 일부 프로세스 OOM 가능 | PID 1 생존·group 설정·runtime 보고 확인 |
| `memory.events.high` 증가, 종료 없음 | `memory.high` 초과로 task가 직접 회수·throttling 경로에 들어감 | OOM kill 횟수가 아님; 한도·PSI·처리 지연을 함께 확인 |

`lastState`는 모든 과거 종료를 보존하는 원장이 아닙니다. Pod UID·container ID·시각·restartCount와 event를 연계해 이력을 수집합니다. `OOMKilled`를 곧바로 “메모리 limit 초과 확정”으로 표기하지 않고, `Evicted`도 모든 원인이 메모리라고 가정하지 않습니다. [Pod 상태](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/), [eviction 동작](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/)

**MemoryQoS는 1.37에서 Beta·기본 활성**이지만 `memoryThrottlingFactor` 기본값은 `nil`이어서 kubelet이 이 기능으로 `memory.high`를 설정하지 않습니다. 값을 지정한 지원 구성에서는 OOM 없이도 `high` 계정과 처리 지연이 늘 수 있습니다. 이는 회수 작업과 throttling으로 task가 지연되는 상황이며 회수 자체가 늦춰진다는 뜻은 아닙니다. `memory.high`는 OOM kill을 직접 일으키는 한도가 아니지만 같은 시스템의 `memory.max` 도달 등 다른 OOM 가능성을 없애지도 않습니다. [gate 기본값](https://github.com/kubernetes/kubernetes/blob/v1.37.0/pkg/features/kube_features.go#L1845), [kubelet 설정 정의](https://github.com/kubernetes/kubernetes/blob/v1.37.0/staging/src/k8s.io/kubelet/config/v1beta1/types.go#L899), [적용 코드](https://github.com/kubernetes/kubernetes/blob/v1.37.0/pkg/kubelet/kuberuntime/kuberuntime_container_linux.go), [kernel memory.high·events](https://docs.kernel.org/admin-guide/cgroup-v2.html#memory-interface-files)

## 한도와 수집 경로도 수명 중 바뀐다

컨테이너 CPU·메모리 in-place resize는 **1.35에서 Stable**입니다. `.spec.containers[].resources`는 원하는 값, `.status.containerStatuses[].resources`는 실행 중 컨테이너에 설정된 값입니다. 시작 전이나 재시작 시에는 다음 시작에 할당된 자원을 나타내는 의미도 있습니다. `allocatedResources`와 `PodResizePending`·`PodResizeInProgress`를 함께 보면 적용 대기와 완료를 구분할 수 있습니다. [resize 문서](https://v1-35.docs.kubernetes.io/docs/tasks/configure-pod-container/resize-container-resources/)

**예시:** 같은 컨테이너의 메모리 사용량이 400 MiB인 채 실제 한도가 512 MiB에서 1024 MiB로 바뀌면 사용률은 `78.125% → 39.0625%`입니다. 사용량이 절반으로 줄어든 것이 아닙니다. 분모의 적용 시각을 저장하고 request 기준 비율과 limit 기준 비율을 구분합니다. spec 변경 시각을 실제 한도 적용 시각으로 대체하지 않습니다.

| kubelet 경로 | 관측 목적 | 호환성 경계 |
| --- | --- | --- |
| `/stats/summary` | node·Pod·container 자원 통계 JSON | runtime/CRI 통계와 cAdvisor 경로, OS에 따라 제공 범위 확인 |
| `/metrics/resource` | CPU·메모리 등 resource metrics용 제한된 지표 | 전체 cAdvisor 지표의 별칭 아님; metrics-server 0.6+의 사용 경로 |
| `/metrics/cadvisor` | cAdvisor의 자세한 컨테이너 지표 | 지표 수명·label·OS·runtime 범위 별도 확인 |
| `/metrics/probes` | kubelet probe 관련 지표 | 자원 사용량 endpoint와 구분 |

Prometheus endpoint 구분은 [System Metrics](https://kubernetes.io/docs/concepts/cluster-administration/system-metrics/), Summary API와 metrics-server 경로는 [Node Metrics Data](https://kubernetes.io/docs/reference/instrumentation/node-metrics/)를 따릅니다. PSI는 `KubeletPSI`가 1.34 Beta 기본 활성, **1.36 GA**이며 Linux PSI·cgroup v2 전제가 필요합니다. Summary API와 `/metrics/cadvisor`에 노출되며 Windows에는 제공되지 않습니다. 1.36에서는 OS가 지원하지 않을 때 거짓 0 대신 생략하도록 개선됐습니다. endpoint 존재만으로 PSI 지원을 인정하지 않습니다. [PSI GA 설명](https://kubernetes.io/blog/2026/05/12/kubernetes-v1-36-psi-metrics-ga/)

cgroup v1은 [1.31부터 유지보수 상태](https://kubernetes.io/blog/2024/08/14/kubernetes-1-31-moving-cgroup-v1-support-maintenance-mode/)이며 **1.35부터 Deprecated**입니다. kubelet의 `failCgroupV1` 기본값도 **1.35부터 true**입니다. 1.37에서도 `false` override가 남아 있으므로 “v1 코드가 이미 제거됐다”와 “기본 설정으로 시작을 거부한다”를 구분합니다. [cgroup v1 상태](https://kubernetes.io/docs/concepts/architecture/cgroups/), [1.37 릴리스 설명](https://kubernetes.io/blog/2026/08/26/kubernetes-v1-37-release/)

## 제품 적용 제안

종료 화면을 `관측한 reason`, `추정 원인`, `뒷받침하는 증거`, `누락된 증거`로 구성합니다. 노드 압박·cgroup 사건·실제 자원 한도·Pod UID를 같은 시간 축에서 비교합니다. workload를 실행하지 않는 envtest API 실습으로 OOM이나 eviction 동작을 검증했다고 표시하지 않습니다.

API 객체 조회에는 해당 namespace/리소스의 `get/list/watch`, kubelet endpoint 조회에는 별도의 인증·인가가 필요합니다. API proxy 권한을 읽기 전용 지표 수집 권한과 동일하게 취급하지 않습니다. cgroup·kernel 로그 접근은 노드 정책을 따릅니다. 높은 빈도의 전체 Pod/컨테이너 수집은 노드와 API server에 부하를 줄 수 있습니다. 이 장에서는 조회·설정 명령이나 압박 주입을 실행하지 않았습니다.

## 이해 확인

1. Guaranteed이면 eviction이 불가능한가? **아니다. 자원 명세의 QoS 분류이며 모든 종료 원인에 대한 면제가 아니다.**
2. OOMKilled이면 컨테이너 limit 초과가 확정되는가? **노드 OOM 등과 구분할 추가 증거가 필요하다.**
3. resize 후 사용률이 절반이면 사용량도 절반인가? **분모 한도가 바뀌었을 수 있다.**
4. PSI 필드가 없으면 압력이 0인가? **OS·버전·수집 경로·지원 여부를 먼저 확인한다.**

## 함께 읽기

[자원과 배치](resources-and-scheduling.md) · [수집 경로](collection.md) · [메모리와 OOM](../containers/memory-accounting-and-oom.md) · [자원 장애 분석](../cross-domain/resource-failures.md)
