# 자원 요청, 제한, 배치와 확장

> 상태: 검토됨 · 적용 범위: 일반 CPU·메모리 요청/제한과 HPA 원리 · 원천 확인일: 2026-10-06 · 실습 여부: 원천·가상 예시 중심; 연결 실습의 범위는 본문

## 먼저 이해할 것

request는 배치와 자원 판단에 쓰이는 요구량이고 limit은 실행 중 제어와 연결되는 한도입니다. 실제 사용량은 또 다른 값입니다. 이 셋을 구분하면 사용량이 낮은 Node에 Pod가 배치되지 않는 경우나, request보다 많이 쓰지만 정상인 경우를 이해할 수 있습니다. 제품은 배치용 요청량·사용량·실행 한도를 각각 표시해야 합니다.

## request, limit, usage

CPU request는 배치 판단에 사용되고 Linux의 경쟁 상황에서는 CPU 가중치 설정에도 관련됩니다. CPU limit은 실행 시간의 상한 제어와 관련되고, 메모리 limit은 메모리 부족 처리로 이어질 수 있습니다. request를 넘었다고 즉시 컨테이너를 종료하는 일반 규칙은 없습니다. CPU 단위 `1`은 한 CPU 단위이며 `1000m`과 같습니다. 메모리의 `Mi`와 `M`은 각각 이진·십진 단위입니다. [Resource Management](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)

Linux 제한의 실제 동작과 throttling 계산은 [cgroup 자원 제어](../containers/resource-control.md)를 참고합니다. Pod 단위 자원 설정, 런타임과 Windows 노드의 적용 방식은 버전·기능 설정을 함께 확인합니다.

가상의 컨테이너가 request `500m`, limit `2`, 측정 사용량 `750m`이라고 가정합니다.

```text
실제 사용량 = 0.75 CPU
request 대비 = 0.75 / 0.5 = 150%
limit 대비   = 0.75 / 2 = 37.5%
```

두 비율은 모두 올바를 수 있습니다. “CPU 150%”만 보여 주면 어떤 분모인지 알 수 없습니다.

## 설정이 Linux cgroup으로 이어지는 경로

다음은 일반적인 Linux cgroup v2 구성의 대응입니다. CPU 관리 정책·kubelet 설정·feature gate에 따라 실제 제어값은 달라질 수 있으므로 API 설정에서 추측하는 데 그치지 않고 적용값을 확인합니다.

| Kubernetes 설정 | Linux cgroup v2 제어와의 대응 | 주의 |
| --- | --- | --- |
| memory limit | `memory.max` | 사용량 계정과 별도이며 부모 제한도 확인 |
| CPU limit | `cpu.max`의 quota/period | CPU 개수 고정 배정과 다름 |
| CPU request | 상대 가중치 `cpu.weight`와 연결 | request 수치를 그대로 파일에 복사하는 뜻이 아님 |

kubelet 1.37.0의 QoS cgroup 구성에서 **Guaranteed Pod는 kubepods 루트 바로 아래**에 놓이고, Burstable·BestEffort는 각 QoS 하위 그룹 아래에 놓입니다. 실제 경로 표기는 cgroup driver·설정에 따라 다릅니다. Node Allocatable을 강제하는 상위 cgroup 제한도 자식에 영향을 주므로 컨테이너 leaf의 limit 미만이라는 사실만으로 memcg OOM을 배제하지 않습니다. [QoS 계층](https://github.com/kubernetes/kubernetes/blob/v1.37.0/pkg/kubelet/cm/qos_container_manager_linux.go), [Node Allocatable 강제](https://github.com/kubernetes/kubernetes/blob/v1.37.0/pkg/kubelet/cm/node_container_manager_linux.go), [Kubernetes 자원 관리](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/), [계층적 cgroup v2 제한](https://docs.kernel.org/admin-guide/cgroup-v2.html)

```text
Node의 cgroup 계층 → kubepods
  ├─ Guaranteed Pod 그룹 → 컨테이너 그룹
  ├─ Burstable QoS 그룹 → Pod 그룹 → 컨테이너 그룹
  └─ BestEffort QoS 그룹 → Pod 그룹 → 컨테이너 그룹
```

**sandbox**는 런타임이 Pod 컨테이너들의 공유 실행 환경을 준비·관리하는 경계입니다. 애플리케이션 컨테이너 하나와 같은 뜻이 아닙니다. Linux에서 공유 네트워크 namespace 등의 수명과 연결되며 구현은 런타임에 따릅니다. [CRI PodSandbox](https://github.com/kubernetes/cri-api/blob/v0.37.0/pkg/apis/runtime/v1/api.proto)

## capacity와 allocatable

Node의 capacity와 Pod에 배정 가능한 allocatable은 다릅니다. 시스템용 예약과 축출을 위한 여유 등이 영향을 줍니다. 스케줄러는 allocatable을 사용 가능한 자원으로 다룹니다. [Node Allocatable](https://kubernetes.io/docs/tasks/administer-cluster/reserve-compute-resources/)

가상 예시로 CPU capacity가 8, allocatable이 7, 기존 Pod 요청 합이 6.5라면 새 Pod request 1을 수용할 요청 여유는 부족합니다. 현재 실사용량이 2 CPU라는 사실만으로 배치할 수 있다고 결론 내리지 않습니다. 실제 배치에는 메모리, taint, affinity, 저장소 등의 조건도 추가됩니다.

## Pod 요청량은 단순 합이 아닌 경우가 있다

계속 실행되는 sidecar와 Pod overhead가 없고 일반 init 컨테이너만 있는 단순 경우, 자원별 유효 요청은 애플리케이션 컨테이너 요청 합과 init 컨테이너 요청의 최댓값 중 큰 값으로 생각할 수 있습니다. init 실행 단계와 앱 실행 단계가 다르기 때문입니다. [Init Containers: Resource sharing](https://kubernetes.io/docs/concepts/workloads/pods/init-containers/#resource-sharing-within-containers)

```text
앱 CPU 요청: 0.4 + 0.3 = 0.7
일반 init CPU 요청: 1.5, 0.2 → 최댓값 1.5
이 제한된 예의 유효 CPU 요청: max(0.7, 1.5) = 1.5
```

실제 제품에서는 이 단순식을 모든 Pod에 적용하지 않고 해당 버전의 sidecar, overhead, Pod 단위 자원 설정까지 포함하는 계산을 사용해야 합니다. 원천 API 값과 제품의 파생 계산을 구분해 저장합니다.

## OOM과 축출은 구별한다

메모리 관련 종료는 **① 컨테이너·Pod·kubepods 등 cgroup 한도(memcg) OOM ② 노드 전체 커널 OOM ③ kubelet 축출(eviction)**로 나누어 조사합니다. 축출에는 디스크·PID 압박도 있습니다. 종료 reason 하나로 세 경로를 확정하지 않으며 [종료 원인 증거 표](pressure-and-termination.md#oomkilled와-evicted를-증거로-나눈다)를 따릅니다.

## HPA를 계산으로 이해하기

HPA의 기본 비례 계산은 다음과 같습니다. 실제 결정에는 누락 지표, 준비 상태, 허용 오차, 최소·최대 복제본, 안정화와 변경 정책 등이 추가됩니다. 자원 사용률 목표를 쓸 때 request가 분모에 관여합니다. [Horizontal Pod Autoscaling](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/)

```text
기본 권고 복제본 = ceil(현재 복제본 × 현재 지표 / 목표 지표)
```

가상의 동일 요청량을 가진 Pod 3개에서 유효한 평균 CPU 사용률이 request 대비 80%, 목표가 50%라고 하면 `ceil(3 × 80/50) = 5`입니다. 이는 제어 조건을 생략한 기본 계산 예이지, 모든 상황에서 즉시 5개가 된다는 예측이 아닙니다.

제품에서는 지표 값, 분모인 request, HPA 목표, 권고 수, 실제 수와 제한 조건을 나란히 보여 주는 방식을 제안합니다. 부하가 높은데 확장하지 않는 현상을 “HPA 고장”으로 표시하기 전에 누락 지표나 최대 복제본 제한을 확인할 수 있어야 합니다.

## 이해 확인

1. request 대비 150%는 CPU limit 초과인가? **아닙니다. 분모가 다릅니다.**
2. 실사용 여유가 충분하면 반드시 새 Pod를 배치할 수 있는가? **요청량과 다른 배치 제약도 확인해야 합니다.**
3. HPA 기본 계산의 5는 반드시 즉시 생성되는 Pod 수인가? **추가 제어 조건이 적용됩니다.**

이전: [Pod 수명, 컨테이너 상태와 건강 검사](pod-lifecycle.md) · 다음: [Kubernetes 자원 압박과 종료 원인](pressure-and-termination.md) · [분야 목차](README.md)
