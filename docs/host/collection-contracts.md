# 호스트 수집 명세: 원천 필드에서 지표까지

> 상태: 검토됨 · 적용 범위: Linux procfs·cgroup v2와 Windows API · 검토일: 2026-10-04 · 원천 규약 검토, Linux 자기 프로세스·기존 cgroup과 Windows API 일부는 로컬 실험

수집기는 숫자를 읽는 프로그램이면서 그 숫자의 뜻을 보존하는 프로그램입니다. 예를 들어 원천에 `1024`가 있어도 단위가 kB인지 page인지 byte인지 모르면 정확한 지표를 만들 수 없습니다. 이 장은 모니터링 제품의 첫 어댑터를 구현할 때 사용할 최소 계약을 제안합니다. 표의 정규화 이름은 이 책의 설계 예시이며 특정 exporter의 공식 이름이 아닙니다.

## 원천별 계약

| 원천·필드 | 원천 단위·유형 | 정규화와 범위 | 연속성·누락 처리 |
| --- | --- | --- | --- |
| `/proc/stat`의 cpu user 등 | USER_HZ 단위 누적 시간 | `sysconf(_SC_CLK_TCK)`로 초 변환, CPU별 또는 전체 | boot 식별 변화·감소·CPU 집합 변경을 확인 |
| `/proc/PID/stat` utime, stime | clock ticks 누적 | 해당 프로세스의 CPU 초, 자식 시간은 별도 | PID와 starttime으로 실행 수명 구분 |
| `/proc/meminfo` MemTotal, MemAvailable | 표시된 kB, 현재량 | 해당 인터페이스에서 1kB=1024B로 변환 | 없는 필드는 지원 불가; MemFree로 몰래 대체하지 않음 |
| `/proc/diskstats` sectors read/written | 512B 섹터 누적 수 | 완료된 장치 I/O byte 수 | 장치 재생성·리셋을 구분; 계층 합산 금지 |
| `/proc/diskstats` read/write milliseconds | 32bit unsigned 누적 ms | wrap 조건을 판정한 차분을 완료 작업 증가량으로 나누면 평균 시간 | 64bit 커널에서도 wrap 가능; 완료 수 증가 0이면 평균 없음 |
| `cpu.stat` usage_usec | 누적 µs | cgroup CPU 초로 변환 | cgroup 재생성과 counter 감소 확인 |
| `memory.current` | byte 현재량 | cgroup과 자식의 현재 계정 | 프로세스 RSS와 동일시하지 않음 |
| `GetSystemTimes` | 100ns 누적 시간 | kernel에는 idle 포함; API의 CPU group 범위 | 두 표본의 차분, 총시간 0은 결측 |

Linux 정의는 [proc stat](https://man7.org/linux/man-pages/man5/proc_stat.5.html), [PID stat](https://man7.org/linux/man-pages/man5/proc_pid_stat.5.html), [meminfo](https://man7.org/linux/man-pages/man5/proc_meminfo.5.html), [디스크 통계](https://docs.kernel.org/admin-guide/iostats.html), [cgroup v2](https://docs.kernel.org/admin-guide/cgroup-v2.html)에 근거합니다. Windows는 [GetSystemTimes](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getsystemtimes)를 사용합니다. 다른 API의 단위를 이 표에서 추측하지 않습니다.

[Linux 실습](linux-observation-lab.md)은 자기 프로세스의 stat·smaps·io와 기존 cgroup 읽기를 확인했습니다. 이 표의 모든 호스트 필드나 제한 동작을 실행 검증한 것은 아닙니다. 최초 CPU 표본과 별도로 [시계 진단 재실행](../../labs/results/1.1-linux-clock-r1.json)을 보존했습니다. 단일 스레드 busy 구간의 프로세스 CPU clock은 RAW와 거의 같은 증가량을 보였지만 MONOTONIC보다 빨랐고, sleep·idle의 시계 차이와 adjtimex 값도 분모의 주파수 조정 설명에 부합했습니다. 수집기는 CPU/MONOTONIC > 1을 100%로 자르기보다 분모 시계·RAW 비교·조정 상태·스레드 수를 품질 정보로 남기도록 제안합니다. 이 재실행으로 RAW·tick이 없는 과거 1.06 표본의 원인이나 시계 조정 주체까지 확정하지 않습니다.

## 읽기 한 번이 하나의 원자적 스냅샷은 아니다

파일 A를 읽고 B를 읽는 사이에도 프로세스가 종료되고 장치가 변경될 수 있습니다. 값마다 실제 수집 시간 또는 배치의 시작·종료 구간을 기록합니다. “목록에는 있었는데 상세 파일이 없다”는 것은 수집 중 종료일 수 있으므로 파일 파싱 오류와 같은 상태로 처리하지 않습니다.

`/proc/PID/stat`는 공백만으로 필드 분리를 끝내면 안 됩니다. 괄호로 둘러싸인 comm에 공백 등이 있을 수 있기 때문입니다. starttime 검증을 포함해 상세를 읽는 중 PID가 재사용되었는지도 확인합니다. `/proc`의 다른 사용자 프로세스 가시성은 권한·마운트 옵션 등에 따라 제한될 수 있습니다. [procfs](https://man7.org/linux/man-pages/man5/proc.5.html)

## 차분 변환의 상태 기계

다음은 두 표본 차분을 사용하는 이 책의 **단순 어댑터 정책**입니다. Prometheus의 외삽을 포함하는 `rate()` 알고리즘과 동일한 구현이라고 부르지 않습니다.

```text
첫 표본 / 새 실행 수명       → 기준만 저장, 증가율은 없음
같은 수명 + 시각 증가 + 값 증가 → (현재값 - 이전값) / 경과시간
같은 시각                   → 중복 판단; 분모 0으로 나누지 않음
역순 도착                   → 시계열 순서 정책으로 처리; 음수 경과시간 금지
값 감소, 원인 미상          → decrease 기록, rate 보류; wrap·reset 증거 확인
실행·리셋 표식 변경         → 확인한 수명 변경 기록, 기준 재설정
수집 실패                   → 실패 사건 기록, 값 0을 합성하지 않음
```

가상 입력 `100→160`을 15초 간격으로 읽으면 4/초입니다. 다음 표본이 같은 시각에 다시 오면 0/초를 추가하지 않습니다. 새 실행 수명의 첫 값이 12라면 `12−160`을 음수 처리량으로 저장하지 않습니다. 특히 diskstats의 시간 필드 4·8·10·11·15·17은 64bit 커널에서도 32bit unsigned 값으로 노출됩니다. `2^32 ms`는 약 49.71일분의 **누적 계정 시간**이며, 병렬 I/O를 합하는 필드는 그보다 짧은 실제 경과 시간에도 wrap할 수 있습니다. 값 감소만으로 장치 재시작을 확정하지 않습니다. 같은 장치 수명과 구간 최대 증가량이 `2^32` 미만임을 별도 근거로 보장할 때에만 `(현재−이전) mod 2^32`를 복원 후보로 사용합니다. 그 조건을 모르면 wrap 횟수와 reset을 구분할 수 없어 rate를 보류합니다. [필드 유형](https://docs.kernel.org/admin-guide/iostats.html), [Linux 6.12 출력 코드](https://github.com/torvalds/linux/blob/v6.12/block/genhd.c#L1239-L1300)

## 평균과 비율의 입력을 보존하기

장치의 읽기 시간 증가가 9,000ms이고 완료 읽기 수 증가가 3,000이라면 평균은 3ms입니다. 총 9초를 관측 경과 10초로 나눈 90%는 이 평균과 다른 계산이며 장치 포화율로 이름 붙일 근거가 없습니다. 여러 작업의 시간이 중첩될 수 있습니다.

제품에는 평균만 저장하기보다 시간 합과 작업 수를 함께 저장하는 편이 이후 집계에 유리합니다. 반대로 gauge는 순간 관측이므로 서로 다른 시각의 메모리 값을 단순 합해 사용량이라고 부르지 않습니다.

## 권한과 실행 비용

| 수집 방법 | 권한·범위 | 비용 관리 |
| --- | --- | --- |
| procfs·sysfs 읽기 | 파일별 권한, namespace, hidepid 등에 의존 | 고빈도 전체 PID 열거와 상세 수집을 분리 |
| `smaps` 계열 | 프로세스 접근 제약; 매핑 규모 영향 | 모든 프로세스의 고빈도 기본 수집으로 단정하지 않음 |
| 네트워크 통계 netlink | namespace별 인터페이스, API 권한 확인 | 동일 namespace의 목록과 통계 연결 |
| Windows API/PDH | API별 접근권, counter 정의·언어 차이 | 필요한 counter 묶음과 실제 샘플 간격 유지 |

수집기가 root 또는 관리자 권한이면 의미가 더 정확해지는 것은 아닙니다. 권한은 접근 가능 범위의 문제입니다. 얻은 값의 단위·계정 범위는 동일하게 확인해야 합니다.

## 받아들이기 전의 사례 검사

어댑터에는 정상 증가뿐 아니라 재부팅, 프로세스 교체, 수집 실패, 같은 시각 재전송, clock 이동, 지원하지 않는 필드, 분모 0을 넣어 봅니다. 입력과 기대 상태는 [수집 계약 검사](../product/adapter-contracts.md)에서 구체화합니다.

Windows CPU의 실제 원천 표본과 산식은 [실습](../cross-domain/reproducible-labs.md)에 기록했습니다. 그 실행으로 Linux 계정 규칙이나 모든 Windows processor group 조합을 검증했다고 표시하지 않습니다.

## 이해 확인

1. 장치 논리 sector 크기가 4096B면 diskstats sector도 4096B인가? **해당 통계는 512B 단위이므로 별도로 해석합니다.**
2. 첫 표본으로 초당 CPU 사용량을 만들 수 있는가? **이 차분 정책에서는 이전 표본이 필요합니다.**
3. permission denied를 값 0으로 저장해도 되는가? **접근 실패와 0 사용량을 구분해야 합니다.**
