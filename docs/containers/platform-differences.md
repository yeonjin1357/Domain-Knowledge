# 컨테이너 수집의 플랫폼 차이: cgroup v1·v2와 Windows

> 상태: 검토됨 · 적용 범위: Linux cgroup 인터페이스, Windows 격리 모드의 공식 정의 · 원천 확인일: 2026-10-06 · 실습 여부: 원천·가상 예시 중심; 연결 실습의 범위는 본문

선수 용어: **sandbox**는 Pod의 공유 실행 환경을 관리하는 런타임 경계입니다. [자원 설정·cgroup 계층](../kubernetes/resources-and-scheduling.md#설정이-linux-cgroup으로-이어지는-경로)에서 컨테이너와의 차이를 먼저 확인합니다.

컨테이너라는 이름이 같아도 원천 계정은 다를 수 있습니다. Linux의 파일 경로를 Windows에서도 찾거나 cgroup v1의 값을 v2 단위로 읽으면 수집기는 실행되어도 틀린 숫자를 만듭니다. 먼저 OS, runtime, 격리 모드, 자원 제어 인터페이스를 식별합니다.

## cgroup v1과 v2의 대표 차이

| 목적 | v1 원천 예 | v2 원천 예 | 변환 시 확인 |
| --- | --- | --- | --- |
| CPU 누적 사용 | `cpuacct.usage`, ns | `cpu.stat`의 `usage_usec`, µs | 각각 10⁹, 10⁶으로 나누어 초 |
| CPU 시간 quota | `cpu.cfs_quota_us`, `cpu.cfs_period_us` | `cpu.max` quota와 period | 무제한 표현과 상위 그룹 제약 |
| 메모리 계정 | `memory.usage_in_bytes` | `memory.current` | 포함 계정·계층·근사성 |
| 메모리 한도 | `memory.limit_in_bytes` | `memory.max` | 큰 sentinel 값과 `max` 문자열 |
| OOM·한도 사건 | v1 전용 파일 | `memory.events`, `memory.events.local` | 이벤트 의미·하위 그룹 포함 여부 |

v1 CPU 계정은 [cpuacct](https://docs.kernel.org/admin-guide/cgroup-v1/cpuacct.html), quota는 [CFS bandwidth control](https://docs.kernel.org/scheduler/sched-bwc.html), 메모리는 [v1 memory controller](https://docs.kernel.org/admin-guide/cgroup-v1/memory.html), v2는 [통합 hierarchy](https://docs.kernel.org/admin-guide/cgroup-v2.html)를 기준으로 합니다. 이름 대응은 완전한 의미 동등성을 보장하지 않습니다.

가상 원천 v1 `2,000,000,000ns`와 v2 `2,000,000µs`는 각각 CPU 시간 2초입니다. 숫자만 복사하면 1,000배 차이가 납니다. 이 값을 wall time 1초로 나누면 평균 2CPU이며, quota나 호스트 전체 비율은 별도 분모가 필요합니다.

## 메모리 사용량의 이름을 조심하기

v1 `memory.usage_in_bytes`는 효율을 위해 정확한 즉시 총합이 아닌 값일 수 있다고 문서가 설명합니다. v2 `memory.current`는 cgroup과 descendants의 사용을 다룹니다. 어느 쪽이든 모든 프로세스 RSS의 단순 합과 같다고 보장하지 않습니다.

working set을 캐시 일부를 빼서 계산하는 exporter도 있지만 “절대로 회수할 수 없는 메모리”라는 물리적 진실로 이름 붙이지 않습니다. 원천 계정, 뺀 필드, 음수 처리, 페이지 단위를 명세해야 합니다. 캐시 제거 정의가 다른 두 어댑터의 값을 같은 그래프에 조용히 이어 붙이지 않습니다.

## Windows의 격리 모드

Windows process isolation 컨테이너는 호스트와 커널을 공유하는 방식이고, Hyper-V isolation은 각 컨테이너를 최적화된 가상 머신 경계에서 실행합니다. 호스트·컨테이너 이미지 버전의 호환성 조건도 모드에 따라 달라집니다. [Windows isolation modes](https://learn.microsoft.com/en-us/virtualization/windowscontainers/manage-containers/hyperv-container)

따라서 Linux namespace·cgroup 경로가 Windows의 동일한 수집 계약이라고 쓰지 않습니다. CPU count·maximum·weight 등 자원 제어의 설정과 실제 계정은 Windows runtime과 격리 방식의 정의를 따릅니다. [Windows resource controls](https://learn.microsoft.com/en-us/virtualization/windowscontainers/manage-containers/resource-controls)

Hyper-V isolation을 사용한다고 해당 VM의 모든 보조 비용이 업무 프로세스 메모리와 동일하게 나타난다고 가정하지 않습니다. 호스트, utility VM, 컨테이너 내부 프로세스를 연결할 수 있는 원천 관계를 확인합니다.

## 컨테이너 정체성과 PID

runtime의 컨테이너 ID, sandbox ID, Pod UID, 호스트 PID는 서로 다른 종류의 식별자입니다. 호스트에서 보이는 PID와 컨테이너 안의 PID도 namespace에 따라 달라질 수 있습니다. 전체 ID와 그 적용 범위를 보존하고 화면에서만 줄여 표시하는 방식을 제안합니다. [Linux PID namespaces](https://man7.org/linux/man-pages/man7/pid_namespaces.7.html)

runtime 소켓 접근은 단순 지표 읽기 이상의 권한을 제공할 수 있어 실제 API 권한 범위를 확인합니다. 수집 실패를 우회하려고 광범위한 제어 API를 자동 활성화하는 방식으로 문서화하지 않습니다. 필요한 읽기 계약을 구체화하는 것이 우선입니다.

## cgroup v1의 버전 상태

cgroup v1은 [1.31부터 유지보수 상태](https://kubernetes.io/blog/2024/08/14/kubernetes-1-31-moving-cgroup-v1-support-maintenance-mode/)이며 **1.35부터 Deprecated**입니다. kubelet의 `failCgroupV1` 기본값도 **1.35부터 true**입니다. 1.37에서도 `false` override가 남아 있으므로 “v1 코드가 이미 제거됐다”와 “기본 설정으로 시작을 거부한다”를 구분합니다. [cgroup v1 상태](https://kubernetes.io/docs/concepts/architecture/cgroups/), [1.37 릴리스 설명](https://kubernetes.io/blog/2026/08/26/kubernetes-v1-37-release/), [1.37.0 failCgroupV1 기본값·override](https://github.com/kubernetes/kubernetes/blob/v1.37.0/staging/src/k8s.io/kubelet/config/v1beta1/types.go#L957)

## 제품 적용 제안과 이해 확인

어댑터 capability에 OS·runtime 버전·cgroup 버전·격리 모드·지원 필드·원천 단위를 기록합니다. 같은 정규화 이름을 제공할 때도 원래 필드와 계산 정의를 조회할 수 있도록 유지합니다.

1. cpuacct.usage를 10⁶으로 나누면 초인가? **v1 해당 필드는 ns이므로 10⁹으로 나눕니다.**
2. 컨테이너 메모리는 프로세스 RSS 합계와 같은가? **계정 범위가 달라질 수 있습니다.**
3. Windows Hyper-V isolation도 호스트 커널을 그대로 공유하는가? **별도 VM 격리 경계를 사용합니다.**

이전: [컨테이너 파일시스템, 쓰기 계층과 볼륨](filesystems.md) · 다음: [쿠버네티스 도메인](../kubernetes/README.md) · [분야 목차](README.md)
