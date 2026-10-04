# 컨테이너 메모리: 사용량, working set과 OOM을 구분하기

> 상태: 검토됨 · 적용 범위: Linux cgroup v2, cAdvisor 0.52.1 계산, Kubernetes의 메모리 관측 · 검토일: 2026-10-04 · OOM·eviction은 문서 검토이며 직접 유발하지 않음

## 먼저 이해할 것

집의 전체 면적, 실제 짐이 차지하는 면적, 당장 치울 수 없는 짐의 면적은 다릅니다. 프로세스 heap, RSS, cgroup 사용량, working set도 각각 세는 범위가 다릅니다. 메모리 화면에서 숫자가 다르다고 바로 수집 오류라고 판단하지 말고 “무엇이 포함됐는가”를 먼저 확인합니다.

선수 내용은 [호스트 메모리](../host/memory.md)와 [컨테이너 자원 제어](resource-control.md)입니다.

## 관측 계층을 나란히 놓기

| 관측 | 주로 설명하는 것 | 같은 뜻으로 바꾸면 안 되는 값 |
| --- | --- | --- |
| 런타임 heap | 런타임이 관리하는 객체 메모리 | 프로세스 전체 RSS |
| 프로세스 RSS/PSS | 매핑된 상주 페이지와 공유 계정 | cgroup 전체 사용량 |
| `memory.current` | cgroup과 하위 계층의 메모리 계정 | 앱 heap 합계 |
| cAdvisor WorkingSet | 해당 구현의 사용량 보정값 | 회수 불가능한 메모리의 정확한 총량 |
| `memory.max` | cgroup의 설정된 한도 | 현재 사용량 또는 물리 RAM 총량 |

RSS와 PSS의 계정은 [smaps 정의](https://man7.org/linux/man-pages/man5/proc_pid_smaps.5.html)를 따릅니다. 여러 프로세스의 RSS를 더하면 공유 페이지가 중복될 수 있습니다. cgroup 부모와 자식의 계정을 모두 더하는 것도 포함 범위 중복을 확인해야 합니다.

## working set은 구현의 계산식을 확인한다

cAdvisor 0.52.1의 해당 코드에서는 메모리 Usage에서 inactive file 값을 빼고, 뺄 값이 더 크면 0으로 처리합니다. cgroup v2에는 `inactive_file`, v1 경로에는 `total_inactive_file` 키를 사용합니다. 이는 이 구현의 정의이며 모든 도구의 working set이 같은 계산이라는 뜻은 아닙니다. [cAdvisor 0.52.1 원천 코드](https://github.com/google/cadvisor/blob/v0.52.1/container/libcontainer/handler.go)

**가상 예시:** Usage=600MiB, inactive_file=200MiB, limit=768MiB라면 다음과 같습니다.

```text
WorkingSet = 600 - 200 = 400MiB
Usage / limit = 600 / 768 = 78.125%
WorkingSet / limit = 400 / 768 ≈ 52.08%
```

두 비율의 분자는 다릅니다. 둘 중 하나만 “메모리 사용률”이라고 표시하면 오해하기 쉽습니다. working set이 낮다는 사실만으로 OOM까지 충분한 여유가 남았다고 확정하지 않습니다. 표본 사이 급증과 다른 계정 항목도 있습니다.

## high와 max의 역할

`memory.high` 초과는 reclaim과 throttling을 통해 사용량을 제어하는 경계이며, 그 경계 자체의 초과가 OOM killer를 직접 호출하는 것은 아닙니다. `memory.max`는 회수가 되지 않을 때 cgroup OOM으로 이어질 수 있는 한도입니다. 사용량이 순간적으로 한도를 넘는 예외와 모든 할당이 같은 방식으로 실패하지 않는 조건도 있습니다. [cgroup v2 memory 규약](https://docs.kernel.org/admin-guide/cgroup-v2.html#memory)

따라서 high 관련 사건과 지연이 늘어도 컨테이너 재시작이 반드시 함께 증가하지는 않습니다. 반대로 노드 전체의 메모리 압박은 특정 컨테이너의 limit만으로 설명되지 않을 수 있습니다.

Kubernetes request는 스케줄링 등에서 사용하는 자원 요구량입니다. limit, 현재 계정, 런타임 heap과 각각 구분합니다. request 값을 보고 동일한 크기의 물리 메모리가 즉시 점유됐다고 해석하지 않습니다. [Kubernetes 자원 관리](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)

## 사건 카운터에서 확인할 구분

| 원천 항목 | 확인할 의미 |
| --- | --- |
| `memory.events: high` | high 경계로 인한 throttling·직접 reclaim 사건 |
| `memory.events: max` | max 경계를 넘으려던 사건 |
| `memory.events: oom` | 정의된 OOM 조건의 사건; 모든 할당 실패와 동일하지 않음 |
| `memory.events: oom_kill` | 해당 cgroup 프로세스가 OOM killer에 의해 죽은 수 |
| `memory.events.local` | 하위 계층을 합치지 않는 local 사건 |

`memory.events`는 기본적으로 하위 계층을 포함하며 관련 mount 옵션도 확인합니다. 특히 `oom_kill`은 **어떤 종류의 OOM killer에 의한 종료도** 셀 수 있으므로 증가 하나만으로 이 cgroup의 `memory.max`가 유일한 원인이라고 확정하지 않습니다. [사건 필드 정의](https://docs.kernel.org/admin-guide/cgroup-v2.html#memory)

사건 수는 누적 counter입니다. 재생성된 cgroup의 새 값을 이전 수명과 그대로 차분하지 않습니다. 표본 사이 증가를 확인해도 개별 종료의 정확한 시각·원인은 로그와 런타임 상태 등 추가 증거가 필요합니다.

## OOM kill과 kubelet eviction

노드 메모리 압박에 대한 kubelet eviction은 Pod를 종료해 자원을 회수하는 관리 동작입니다. 커널 OOM과 작동 주체·조건·관측 경로가 다릅니다. eviction의 threshold·grace period·우선순위·request 대비 사용 등은 해당 Kubernetes 규약을 따릅니다. [Node-pressure eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/)

조사할 때는 Pod 상태·종료 reason·container 이전 상태, 노드 상태, kernel 기록, cgroup 사건의 시간 순서를 함께 봅니다. 재시작 횟수만으로 어떤 경로인지 확정하지 않습니다. 같은 Pod 이름이 유지돼도 컨테이너 실행 수명은 달라질 수 있습니다. [Pod와 컨테이너 상태](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)

## 흔한 조사 질문을 순서로 바꾸기

다음은 **제품 분석 흐름의 제안**입니다.

1. 사건 시점의 Pod UID·container ID·cgroup 수명을 맞춥니다.
2. 종료·재시작·eviction·수집 단절 중 무엇을 실제 관측했는지 구분합니다.
3. 적용된 limit과 부모 계층의 제한, 노드 압박을 확인합니다.
4. heap·RSS·cgroup current·working set의 범위를 나란히 보여 줍니다.
5. 사건 증가와 직전 추세를 확인하고, 수집 간격 사이의 peak 가능성을 남깁니다.
6. 다음 재현에는 필요한 시간 해상도·사건 기록·원천 상태를 먼저 확보합니다.

`memory.max=max` 같은 문자열을 파싱 오류나 0B 한도로 바꾸지 않도록 제안합니다. 자체 한도가 없다는 사실과 부모·호스트 자원이 무한하다는 주장은 다릅니다.

## 실제 확인한 범위

[Linux 실습](../host/linux-observation-lab.md)에서 기존 cgroup 필드와 자기 프로세스의 매핑을 읽었습니다. private 익명 매핑은 쓰기 전 Rss 0에서 페이지 접근 후 32MiB가 되었습니다. 그러나 cgroup 한도나 OOM을 유발하지 않았으므로 이 결과로 high/max의 제어 효과를 실행 검증했다고 표시하지 않습니다.

## 이해 확인

1. WorkingSet 400MiB이면 heap도 400MiB인가? **계산과 포함 범위가 다릅니다.**
2. high 사건이 늘면 반드시 OOM kill인가? **high 경계는 reclaim·throttling과 관련됩니다.**
3. oom_kill 하나로 cgroup limit 초과를 확정하는가? **global OOM 등 가능한 경로를 추가 증거로 구분합니다.**
4. cgroup max가 무제한이면 메모리 장애가 불가능한가? **부모 계층과 노드 전체 자원도 유한합니다.**
