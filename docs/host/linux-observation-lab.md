# Linux 원천 관측 실습: CPU, 가상 메모리와 실제 I/O

> 상태: 검토됨 · 적용 범위: Ubuntu 24.04, WSL2 Linux 6.18.33.2, Python 3.12.3의 로컬 실행 · 검토일: 2026-10-04 · 실제 관측과 해석의 한계를 분리

## 먼저 이해할 것

운영체제가 보여 주는 메모리와 I/O는 한 가지 숫자가 아닙니다. 주소 공간을 확보한 양, 실제 RAM에 올라온 양, 프로그램이 읽은 양, 저장 계층에서 가져온 양은 서로 다른 질문입니다. 이 장은 작고 통제된 작업을 실행하면서 그 차이를 직접 확인합니다.

제1.1판 최초 실행 입력은 [보존한 실행기](../../labs/archive/run_linux_lab_1_1.py), 원시 결과는 [기존 Linux 실습 기록](../../labs/results/1.1-linux.json)입니다. 시계 진단을 추가한 [현재 실행기](../../scripts/run_linux_lab.py)로 Claude가 2026-10-04 04:10:49 UTC에 재실행한 결과는 [Linux 시계 진단 기록](../../labs/results/1.1-linux-clock-r1.json)에 별도로 보존했습니다. Codex는 전달받은 JSON의 실행기 hash·계산·품질 표시를 확인했습니다. 원본과 복사본의 SHA256은 같으며 [근거 보존 기록](../../review/evidence-provenance.json)에서 연결합니다. CPU 절은 두 실행을 구분해서 설명하고, 나머지 실습 표는 최초 기록을 유지합니다. 이 결과를 Windows 전체 호스트나 모든 Linux 배포판의 성능 측정으로 일반화하지 않습니다.

## 실행 범위와 준비

자기 프로세스의 `/proc` 자료를 읽고, 32MiB 익명 매핑과 1MiB 임시 파일을 사용했습니다. root 권한, 캐시 강제 비우기, 메모리 한도 변경, OOM 유발을 사용하지 않았습니다. 작업은 끝난 뒤 매핑과 임시 파일을 해제합니다.

저장소 루트에 대응하는 Linux 디렉터리에서 실행합니다. WSL에서는 저장소의 실제 Linux 경로로 이동한 뒤 같은 명령을 사용합니다.

```bash
python3 -B scripts/run_linux_lab.py --clock-observation-seconds 60 --output .lab-runs/linux-clock-r1.json
```

위 명령은 `.lab-runs/linux-clock-r1.json`에 결과를 저장합니다. 기본 출력도 `.lab-runs/linux.json`이며 출판 기록을 덮지 않습니다. 임시 I/O 파일도 `.lab-runs/`에 만듭니다. 이 장은 procfs가 존재하는 Linux용이며, `adjtimex` 구조체 호출은 확인한 glibc x86_64 ABI에서만 수행합니다. 다른 ABI에서는 미지원 사유를 기록합니다.

## 실습 1: 프로세스 이름에도 공백과 괄호가 있다

`/proc/PID/stat`의 두 번째 필드는 괄호로 감싼 comm입니다. CPU 시간은 utime·stime, 실행 수명은 starttime을 통해 해석합니다. 공백으로 전체 문자열을 나누면 이름 안의 공백 때문에 뒤 필드 위치가 어긋날 수 있습니다. [proc_pid_stat](https://man7.org/linux/man-pages/man5/proc_pid_stat.5.html)

실습에서는 자기 프로세스 이름을 잠시 `dk ) worker`로 바꾸고 다음을 확인한 뒤 원래 이름으로 복원했습니다.

| 확인 항목 | 실제 결과 |
| --- | --- |
| 읽은 comm | `dk ) worker` |
| 읽은 PID | 실행 중인 실습 프로세스 PID와 일치 |
| CPU·시작 시각 필드 | 괄호 경계를 처리한 뒤 원래 필드 위치로 읽음 |

문법을 정확히 파싱하는 것과 대상 수명을 확인하는 것은 별도입니다. 같은 PID가 나중에 재사용될 수 있으므로 저장 키에는 프로세스 시작 정보도 필요합니다. 이 실습은 PID 재사용 경쟁 상황을 직접 유발하지 않았습니다.

## 실습 2: 누적 CPU 시간을 초로 바꾸기

`sysconf(_SC_CLK_TCK)`에서 이 환경의 값 100을 읽었습니다. 원천의 utime와 stime 증가를 합하고 이 값으로 나누어 CPU초를 계산했습니다. `CLK_TCK=100`을 모든 플랫폼의 고정 상수로 구현하지 않습니다.

```text
제1.1판 최초 실행의 2초 목표 구간:
누적 CPU 계정 증가 = 212 ticks
CPU 시간 = 212 / 100 = 2.12초
monotonic wall 시간 ≈ 2.000005초
계산 비율 ≈ 1.06 CPU초/초
```

**최초 실행의 추가 확인:** 짧은 첫 표본의 비율이 예상보다 커서 1초·2초 구간을 추가했습니다. 이 구간에도 약 1.06이 나타났습니다. 프로세스 CPU clock과 monotonic clock의 구현 이름도 기록했습니다.

**교차 검토에서 확인한 설명:** Linux의 `CLOCK_MONOTONIC`은 역행하지 않는 성질과 별개로 주파수 조정을 받습니다. `CLOCK_MONOTONIC_RAW`는 그 조정을 받지 않습니다. 분모 시계가 CPU 계정에 비해 느리게 흐르면 단일 스레드에서도 CPU초/MONOTONIC초가 1을 넘을 수 있습니다. 이 비율을 물리적인 106% 처리 능력으로 읽으면 안 됩니다. [clock_gettime](https://man7.org/linux/man-pages/man2/clock_gettime.2.html)

**저장소 실행기로 재현한 관측:** 같은 WSL 환경(Linux 6.18.33.2-microsoft-standard-WSL2, Python 3.12.3)에서 busy 3개 구간과 sleep 1개 구간을 기록했습니다. 아래 시간은 같은 관측 구간에서 읽은 각 시계의 증가량이며, 소수 여섯 자리로 반올림했습니다. CPU는 프로세스 CPU clock입니다. 모든 구간의 시작·끝 스레드 수는 `[1, 1]`입니다.

| 작업·MONOTONIC 목표 | MONOTONIC(초) | RAW(초) | 프로세스 CPU(초) | CPU/MONOTONIC | CPU/RAW | MONOTONIC/RAW |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| busy 0.2초 | 0.200007 | 0.213378 | 0.213361 | 1.06676 | 0.99992 | 0.93734 |
| busy 1초 | 1.000002 | 1.066986 | 1.066906 | 1.06690 | 0.99992 | 0.93722 |
| busy 2초 | 2.000001 | 2.134155 | 2.134058 | 1.06703 | 0.99995 | 0.93714 |
| sleep 2초 | 2.000107 | 2.134267 | 0.000057 | 0.00003 | 0.00003 | 0.93714 |

CPU를 거의 쓰지 않은 sleep에서도 MONOTONIC/RAW가 약 0.937이었습니다. 따라서 두 시계의 차이는 이 실험에서 CPU 부하를 주는 동안에만 생긴 현상이 아닙니다. busy 구간에는 `single_thread_cpu_over_monotonic`, `monotonic_raw_rate_difference`, `clock_slew_suspected`가 기록됐고, sleep 구간에는 시계 비율 차이 표시만 남았습니다.

이어 MONOTONIC 기준 60초를 목표로 idle 시계열 61개 표본을 수집했습니다. 두 끝점의 증가량은 MONOTONIC **60.011948727초**, RAW **64.089720449초**이며 비율은 **0.93637401**입니다. 같은 표본에서 읽기 전용 `adjtimex(modes=0)`의 tick은 9,353–9,371µs 사이의 서로 다른 7개 값이었습니다. 이 환경의 명목 tick 10,000µs를 기준으로 61개 tick의 단순 산술평균을 나눈 값은 **0.93637541**입니다. `freq_ppm` 범위는 **-49.82660~+40.45189ppm**, `status` 비트 값은 모두 8192였습니다. 이 값들은 JSON에서 다시 계산할 수 있습니다.

두 비율의 근접성은 시계 조정 설명과 부합합니다. 다만 tick의 단순 표본 평균은 연속 시간에 대한 정확한 적분이 아닙니다. 시계와 adjtimex는 순차로 읽었고 표본 사이의 변경 시점은 알 수 없으며, freq도 시계 속도에 기여합니다. tick/10,000 하나를 MONOTONIC/RAW와 항상 같은 공식으로 사용하지 않습니다. `tick`의 단위와 freq 조정의 의미는 [adjtimex 규약](https://man7.org/linux/man-pages/man2/adjtimex.2.html), 명목 tick과 조정값의 결합은 [Linux 6.12 코드](https://github.com/torvalds/linux/blob/v6.12/kernel/time/ntp.c)에서 확인했습니다. 이 코드 대조가 실행한 WSL 6.18 커널 전체를 감사했다는 뜻은 아닙니다.

**이 재실행의 결론:** 같은 WSL 환경의 재실행에서 단일 스레드 busy 구간의 프로세스 CPU clock/RAW는 약 0.99992–0.99995였고, MONOTONIC/RAW는 약 0.937로 MONOTONIC이 RAW보다 약 6.3% 느리게 진행했습니다. sleep·idle 구간에서도 같은 방향의 시계 속도 차이가 관측되었고 adjtimex 조정값과 부합하므로, 이 재실행에서 CPU/MONOTONIC이 1을 넘은 현상은 분모 시계의 주파수 조정으로 설명됩니다. 원래 제1.1판의 약 1.06 표본은 같은 환경에서 재현된 동일 패턴으로만 연결하며, RAW·tick 기록이 없어 그 표본의 원인을 소급 확정하지 않습니다. tick을 설정한 주체와 RAW의 외부 정확도는 확인하지 않았습니다.

기존 `passed`는 `/proc` CPU ticks와 process CPU clock의 근접성을 검사한 결과입니다. 두 값은 같은 커널 CPU 계정을 반영할 수 있으므로 독립적인 경과 시간 교정 검사가 아닙니다. 원시 JSON의 `independently sampled` 표현도 이 의미에서는 부정확하며, 역사 기록을 바꾸는 대신 여기서 정정합니다.

수정 실행기는 busy·sleep 각각에서 MONOTONIC·RAW·process CPU 시간, 읽기 시각의 폭, 시작·끝 스레드 수, 읽기 전용 `adjtimex(modes=0)`의 tick·freq·status를 기록합니다. 단일 스레드의 CPU/MONOTONIC > 1은 품질 표시로 남기고, RAW와의 차이가 함께 나타나면 `clock_slew_suspected`를 표시합니다. 1%는 이 실습의 진단 구분값이며 보편적인 허용 오차가 아닙니다. RAW 역시 가상화·하드웨어 시계의 정확도를 자동 보증하지 않습니다. `adjtimex`의 freq는 65536으로 나누어 ppm으로 해석하며, 반환 상태 `TIME_ERROR`와 호출 실패 -1을 구분합니다. [adjtimex](https://man7.org/linux/man-pages/man2/adjtimex.2.html), [Linux 6.12 NTP 시간 조정 코드](https://github.com/torvalds/linux/blob/v6.12/kernel/time/ntp.c)

**근거 검증:** `verify_review_r1.py`와 `verify_revision.py`는 출판한 새 JSON의 SHA256, 실행기 SHA256, 구간별 원시 시계 증가량·CPU 계정·품질 표시, idle 표본과 위 본문 수치를 대조합니다. 실제 Linux 실행은 Claude가 수행했고 이 검증 명령은 저장된 결과를 검사합니다. 원천값을 임의로 100%로 잘라 저장하지 않는 이유는 [측정과 비교](../foundations/measurement-and-comparability.md)에 있습니다.

## 실습 3: 주소 공간 확보와 물리 페이지 사용

익명 private 매핑은 파일을 읽어 오는 대신 프로세스가 사용할 주소 영역을 확보하는 예입니다. 실습은 매핑을 만든 뒤 각 페이지에 한 바이트를 써 보고 해당 매핑의 `smaps`를 읽었습니다. `smaps`의 Size·Rss·Pss·Private_Dirty는 서로 다른 계정입니다. [proc_pid_smaps](https://man7.org/linux/man-pages/man5/proc_pid_smaps.5.html), [mmap](https://man7.org/linux/man-pages/man2/mmap.2.html)

| 해당 매핑 | 만든 직후 | 페이지를 쓴 뒤 |
| --- | ---: | ---: |
| Size | 32,768KiB | 32,768KiB |
| Rss | 0KiB | 32,768KiB |
| Pss | 0KiB | 32,768KiB |
| Private_Dirty | 0KiB | 32,768KiB |

이번 매핑에서는 주소 공간 크기가 같아도 상주 페이지가 달라졌습니다. 이 숫자는 전체 프로세스 메모리가 아니라 선택한 매핑의 값입니다. 다른 환경에서는 인접 매핑 병합이나 큰 페이지 등도 확인해야 하므로 항상 동일한 표가 나온다고 보장하지 않습니다.

이 결과로 메모리 누수를 입증할 수는 없습니다. 누수 판단에는 작업 종료·참조 해제·회수 후에도 메모리가 불필요하게 유지되는지와 시간에 따른 추세가 필요합니다.

## 실습 4: 읽기 호출의 byte와 저장 계층의 byte

`/proc/PID/io`에서 `rchar`·`wchar`는 읽기·쓰기 호출에 귀속되는 byte 계정을, `read_bytes`·`write_bytes`는 저장 계층에 대한 I/O 계정을 다룹니다. 파일의 논리적 읽기량과 실제 저장소에서 가져온 양을 같은 값으로 취급하지 않습니다. [proc_pid_io](https://man7.org/linux/man-pages/man5/proc_pid_io.5.html)

실습은 1MiB 파일을 쓰고 `flush()`와 `fsync()`를 호출한 뒤 같은 파일을 두 번 읽었습니다. 기록에서는 `wchar`가 1,048,576B 증가했고, 두 번 읽는 동안 `rchar`는 증가했지만 `read_bytes`는 증가하지 않았습니다.

파일 내용도 두 번 모두 원본과 일치했습니다. 따라서 “저장 계층의 읽기 증가가 0이면 프로그램은 아무것도 읽지 않았다”는 해석은 이 실행에서 성립하지 않습니다. `/proc/self/io`를 읽는 동작 자체도 `rchar`에 기여하므로 차분 전체를 파일 본문 두 번의 정확한 합으로 표시하지 않습니다.

캐시를 비우거나 실제 전원 장애를 일으키지는 않았습니다. `fsync()` 호출 성공만으로 스토리지의 모든 고장 조건을 실험했다고 표시하지 않습니다. [쓰기 완료와 지속성](../storage/write-path-and-durability.md)을 함께 읽습니다.

## cgroup 관측은 별도 범위다

기존 `/init.scope`의 `memory.current`, `memory.max`, `cpu.stat` 등을 읽었습니다. 이 그룹에는 다른 프로세스가 포함될 수 있어 자기 프로세스의 메모리와 직접 일치할 이유가 없습니다. 읽지 못한 `cpuset.cpus.effective`는 `FileNotFoundError`로 기록하고 CPU 수 0으로 바꾸지 않았습니다.

이 부분은 기존 그룹의 읽기 관측입니다. 격리된 컨테이너를 만들거나 limit·throttling·OOM을 재현한 실험은 아닙니다. 계층의 계정 의미는 [cgroup v2 규약](https://docs.kernel.org/admin-guide/cgroup-v2.html)을 따릅니다.

## 제품 적용 제안

수집 결과에는 원천값, 실행 수명, 실제 시간 구간, 단위, 관측 계층, 오류 상태를 함께 저장합니다. 숫자 하나를 “CPU”, “메모리”, “디스크”라는 이름으로만 보관하면 위 실험에서 확인한 차이를 나중에 복원하기 어렵습니다.

## 이해 확인

1. 32MiB를 매핑했으면 즉시 RSS가 32MiB 늘어나는가? **이번 익명 매핑에서는 쓰기 전 Rss가 0이었습니다. 주소 공간과 상주량을 구분합니다.**
2. `read_bytes` 차분 0은 파일을 읽지 않았다는 뜻인가? **캐시에서 읽은 경우처럼 논리 읽기는 있을 수 있습니다.**
3. 프로세스 CPU 비율이 예상 범위를 벗어나면 성능이 좋아졌다고 결론 내리는가? **시계·계정·표본 범위부터 확인합니다.**
4. 이번 결과가 cgroup OOM 동작을 검증했는가? **기존 필드를 읽었으며 OOM을 유발하지 않았습니다.**
