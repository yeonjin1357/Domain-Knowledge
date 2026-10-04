# CPU와 메모리의 위치: NUMA, 캐시, 스케줄링과 압력

> 상태: 검토됨 · 적용 범위: Linux NUMA·CPU affinity·PSI 인터페이스 · 검토일: 2026-10-04 · 명령은 이 환경에서 실행하지 않음

서버 전체에 메모리가 남아 있어도 어떤 CPU가 가까이 접근할 수 있는 메모리는 부족할 수 있습니다. NUMA는 CPU와 메모리의 위치에 따라 접근 특성이 달라지는 구조입니다. 가까운 창고와 먼 창고를 떠올리면 쉽지만, 실제 비용은 장비 구조·배치·접근 패턴에 따라 달라지므로 “원격 메모리는 항상 몇 배 느리다”는 고정 배수를 사용하지 않습니다.

## 논리 CPU, 코어, 소켓과 노드

소켓은 CPU 패키지를 꽂는 하드웨어 위치이고, 코어는 실행 자원을 가진 처리 단위입니다. SMT를 지원하고 활성화한 코어는 여러 논리 CPU로 노출될 수 있습니다. 논리 CPU 개수가 두 배라고 모든 작업의 처리 성능이 두 배가 되지는 않습니다. NUMA node와 소켓의 대응 역시 장비별로 확인합니다. Linux는 CPU topology와 node 정보를 sysfs로 제공합니다. [Linux CPU topology](https://docs.kernel.org/admin-guide/cputopology.html)

이 책의 CPU 사용률 분모는 명시하지 않으면 모호합니다. 하이퍼스레드 16개인 서버의 8개 논리 CPU 사용을 “물리 코어 8개가 온전히 사용됨”으로 바꾸어 적지 않습니다. 명령 처리량은 캐시 적중, 메모리 대기, 실행 명령, 주파수 등에도 영향을 받습니다.

## 메모리 배치 정책

Linux 메모리 정책에는 기본 정책, 특정 노드 선호, 노드 집합으로 제한하는 bind, 노드 간 분산을 시도하는 interleave 등이 있습니다. CPU 배치와 메모리 배치는 같은 설정이 아닙니다. 프로세스가 실행될 수 있는 CPU를 제한했어도 모든 기존 페이지가 자동으로 그 CPU 근처로 옮겨졌다고 가정하지 않습니다. 정책의 범위와 기존 페이지에 대한 효과를 별도로 확인해야 합니다. [NUMA memory policy](https://docs.kernel.org/6.12/admin-guide/mm/numa_memory_policy.html)

가상의 2노드 장비에서 node 0은 사용 가능 1GiB, node 1은 63GiB인데 작업의 허용 메모리 집합이 node 0으로 제한되어 있다고 합시다. 전체 여유 64GiB라는 합계만 보면 배치 제한에 따른 압력을 놓칩니다. 실제 할당 결과는 정책, cpuset, 회수·스왑 상태에 달려 있으며 이 예시만으로 OOM 발생을 단정하지 않습니다.

## 캐시와 메모리 대기

CPU는 작은 캐시에 자주 사용하는 데이터를 유지합니다. cache miss는 요청한 데이터가 해당 캐시에 없어 다음 계층에서 가져와야 하는 사건입니다. 모든 miss가 디스크 I/O를 뜻하지 않습니다. 메모리 접근 대기 중에도 CPU 시간 계정과 명령 처리량은 서로 다른 모습을 보일 수 있습니다.

`perf stat`은 지원되는 성능 이벤트의 개수, 실행 시간 등을 관측하는 도구입니다. `cycles`, `instructions` 같은 이름이 있더라도 이벤트 지원과 가상화·권한·멀티플렉싱을 확인해야 합니다. 여러 이벤트를 동시에 요구해 번갈아 측정했다면 실제 측정 시간과 스케일링 여부가 해석에 영향을 줍니다. [perf stat](https://man7.org/linux/man-pages/man1/perf-stat.1.html)

합성 예로 2억 instructions / 1억 cycles = IPC 2입니다. 이것만으로 다른 CPU나 다른 업무보다 2배 빠르다고 비교할 수 없습니다. 같은 일을 끝냈는지, 같은 명령 구성이었는지, 경과 시간과 주파수는 어땠는지 함께 확인해야 합니다.

## affinity와 스케줄링

affinity는 실행할 수 있는 CPU 집합을 제한합니다. Linux 스레드별 affinity mask는 시스템에 실제 존재하는 CPU와 cpuset 등 추가 제한의 영향을 받습니다. 호스트 전체가 한가한데 특정 스레드의 실행 대기가 늘면 허용 CPU 집합도 조사합니다. [sched_setaffinity](https://man7.org/linux/man-pages/man2/sched_setaffinity.2.html)

`/proc/PID/status`의 `Cpus_allowed_list`와 `Mems_allowed_list`는 처음 조사할 단서입니다. CPU 시간 한도는 [cgroup 자원 제어](../containers/resource-control.md), 작업 상태는 [프로세스](processes.md)와 연결해서 읽습니다.

## PSI를 읽는 정확한 방법

PSI의 `some`은 적어도 일부 작업이 해당 자원을 기다린 구간을 나타내며, 메모리·I/O `full`은 모든 비유휴 작업이 동시에 멈춘 구간을 다룹니다. `avg10`, `avg60`, `avg300`과 누적 마이크로초인 `total`은 서로 다른 출력입니다. CPU `full`은 시스템 전체에서는 정의되지 않는다는 제한이 있습니다. [PSI 정의](https://docs.kernel.org/accounting/psi.html)

예시로 같은 범위의 `memory some total`이 10초 동안 2,000,000µs 늘었다면 그 구간의 정체 비중은 20%입니다. 작업 10개가 각각 20%씩 느려졌다는 뜻도, 메모리가 20% 사용되었다는 뜻도 아닙니다. 여러 작업의 대기가 겹칠 수 있습니다.

## 읽기 전용 조사와 제품 적용 제안

```bash
lscpu
cat /sys/devices/system/node/online
cat /proc/pressure/memory
cat /proc/self/status
```

위 명령은 구조와 상태 조회 예시입니다. `/proc/self`는 조회 프로세스 자신의 정보이므로 제품 대상 PID로 바꾸면 접근 권한과 프로세스 수명도 처리해야 합니다. `perf` 수집은 별도 권한·오버헤드 평가가 필요하며 기본 수집에 무조건 포함하지 않습니다.

제품 화면은 전체 CPU 평균, CPU별 편중, NUMA node별 메모리, 허용 CPU·메모리 집합, cgroup 한도, PSI를 연결합니다. 하드웨어 이벤트가 지원되지 않는 경우 0으로 채우지 않고 지원 불가 상태로 보존합니다.

## 이해 확인

1. 캐시 miss가 늘면 디스크가 느려진 것인가? **해당 캐시 계층과 다음 접근 대상을 확인해야 합니다.**
2. 메모리 여유 합계가 많으면 배치 문제를 배제할 수 있는가? **NUMA 정책과 허용 노드 제한을 봐야 합니다.**
3. PSI 20%와 메모리 사용률 20%는 같은가? **시간 비중과 용량 비중으로 서로 다릅니다.**
