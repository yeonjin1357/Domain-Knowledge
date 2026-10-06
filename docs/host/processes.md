# 프로세스와 스레드 및 파일 디스크립터

> 상태: 검토됨 · 범위: Linux procfs와 프로세스 인터페이스 · 공식 자료 확인: 2026-10-03 · 편집 검토일: 2026-10-04 · 3d 원천·저장 증거 확인: 2026-10-06

> 3라운드 보강: Linux 6.12 상태·메모리 원천 확인, 2026-10-05

## 먼저 이해할 것

프로세스는 실행 중인 프로그램을 관측하는 기본 단위입니다. 프로세스가 존재한다고 계속 CPU에서 실행되는 것은 아니며, 스레드가 I/O나 다른 자원을 기다릴 수 있습니다. PID는 재사용될 수 있으므로 이름과 번호만으로 장기간 같은 실행이라고 판단하지 않습니다. 열린 파일과 소켓도 프로세스가 사용하는 자원입니다.

호스트 지표를 원인 조사로 연결하려면 어떤 실행 대상이 자원을 사용했는지 알아야 합니다. 프로세스 수명과 스레드, 파일 디스크립터, I/O 범위를 구분하면 수집기의 대상 모델을 정확하게 만들 수 있습니다.

## 이름과 PID만으로 수명을 구분하기 어렵다

`/proc/PID/stat`에는 시작 시각 `starttime`이 부팅 이후 clock tick 단위로 제공됩니다. 프로세스 이름에는 공백 등 구분자를 해석할 때 주의할 문자가 있을 수 있어 이 파일을 단순 공백 분리만으로 처리하지 않습니다. [Linux proc_pid_stat](https://man7.org/linux/man-pages/man5/proc_pid_stat.5.html)

**제품 적용 제안:** 호스트와 부팅 수명, PID namespace, PID, 시작 시각을 조합해 실행을 구분합니다. 관측 중 실행이 바뀌었는지 재확인하는 절차를 둡니다. 이 조합은 설계안이며 모든 환경에서 완전한 고유성을 자동 보장한다고 주장하지 않습니다.

프로세스의 표시 이름은 변경되거나 잘릴 수 있습니다. 전체 실행 파일 경로, 명령행, 서비스 소속도 각각의 가시성과 의미가 있으므로 이름 하나를 업무 서비스 식별자로 사용하지 않습니다.

## 프로세스와 스레드의 상태

Linux `status`에는 스레드 그룹·스레드 ID, 부모 ID, 상태와 스레드 수 등이 있습니다. `FDSize`는 할당된 디스크립터 슬롯의 크기이며 현재 열린 파일 수와 같은 의미가 아닙니다. [Linux proc_pid_status](https://man7.org/linux/man-pages/man5/proc_pid_status.5.html)

| 상태 | 해석의 출발점 |
| --- | --- |
| R | 실행 중이거나 실행 가능한 상태 |
| S | 인터럽트 가능한 대기 |
| D | 인터럽트 불가능한 대기 상태로 표시되는 범주 |
| I | 유휴 kernel thread로 표시되는 TASK_IDLE; 일반 D와 구분 |
| T·t | 중지 또는 추적에 따른 중지 |
| Z | 종료했지만 상태 회수가 남은 좀비 |

대기 상태만으로 특정 디스크나 잠금이 원인이라고 단정하지 않습니다. 스레드 스택, 대기 지점, I/O와 런타임 정보를 더 확인합니다.

Linux 6.12의 `TASK_IDLE`은 `TASK_UNINTERRUPTIBLE`과 `TASK_NOLOAD`를 결합하고 `I`로 노출합니다. 이 상태의 대기는 load average의 uninterruptible 기여에서 제외됩니다. 따라서 I를 D에 합쳐 load를 역산하지 않습니다. load average는 시간 평균이며 순간 상태 목록과도 같지 않습니다. [상태 정의](https://github.com/torvalds/linux/blob/v6.12/include/linux/sched.h), [sched_contributes_to_load](https://github.com/torvalds/linux/blob/v6.12/kernel/sched/core.c), [load 평균 계정](https://github.com/torvalds/linux/blob/v6.12/kernel/sched/loadavg.c)

## 먼저 저비용 메모리 원천을 읽고 상세 매핑으로 좁힌다

수천 개 프로세스의 메모리를 매번 자세히 조사하면 수집기 자체가 부담을 만들 수 있습니다. 먼저 status/statm으로 변화한 대상을 찾고 필요할 때 smaps_rollup·smaps으로 내려가는 방식을 고려합니다. 이것은 비용을 제한하는 제품 제안이며 모든 프로세스에서 일정한 배수만큼 빠르다는 뜻은 아닙니다.

| 원천 | 단위·계산 | 관측 범위와 한계 |
| --- | --- | --- |
| `status: VmRSS` | 원천 kB, bytes로는 ×1024 | `RssAnon + RssFile + RssShmem`; 빠른 계정이므로 정밀 snapshot으로 취급하지 않음 |
| `RssAnon` | kB | 상주 익명 페이지 |
| `RssFile` | kB | 상주 파일 매핑 페이지 |
| `RssShmem` | kB | 상주 shared memory·tmpfs·shared anonymous 계열 |
| `VmSwap` | kB | private anonymous swap 사용량; shmem swap은 포함하지 않음 |
| `statm: resident` | 페이지 수 × 실제 page size | VmRSS에 대응하는 근사 resident 계정 |
| `statm: shared` | 페이지 수 × 실제 page size | RssFile+RssShmem에 대응; 현재 둘 이상이 실제 공유한 페이지 수라는 뜻은 아님 |
| `smaps` | 매핑별 kB | page table을 조사해 RSS·PSS 등 상세 분류 제공 |
| `smaps_rollup` | 합산 kB | 매핑별 텍스트 대신 프로세스 전체 합산; 여전히 페이지 조사 비용이 있음 |

status/statm의 RSS 계정은 비동기 처리 등의 이유로 부정확할 수 있습니다. smaps는 더 정밀한 조사 수단이지만 읽는 동안 대상이 계속 변하므로 서로 다른 파일을 연속해서 읽은 값을 하나의 원자적 snapshot처럼 등식 검증하지 않습니다. [커널 proc 메모리 설명](https://docs.kernel.org/6.12/filesystems/proc.html), [statm의 정확도 제한](https://man7.org/linux/man-pages/man5/proc_pid_statm.5.html), [status 필드](https://man7.org/linux/man-pages/man5/proc_pid_status.5.html)

PSS는 공유 페이지의 비용을 공유자에게 나눠 귀속합니다. RSS와 PSS가 어떤 질문에 답하는지는 [메모리 장의 공유 페이지 예시](memory.md)를 봅니다. smaps_rollup은 smaps의 내용을 먼저 모두 출력해 사용자 공간에서 합산하는 비용을 줄이지만, 모든 메모리 변화의 무비용 계수기는 아닙니다. 페이지·매핑 수, 권한, 커널 구현과 읽기 빈도에 따라 비용을 평가합니다. [smaps·rollup 정의](https://docs.kernel.org/6.12/filesystems/proc.html#smaps)

수집 시에는 PID·starttime을 전후 확인해 PID 재사용을 구분합니다. 대상 procfs를 읽을 권한과 ptrace 접근 검사·hidepid 같은 제한을 확인하고, 프로세스 종료·권한 부족·미지원은 0으로 채우지 않습니다. 명령 예시 `cat /proc/self/status`는 **cat 자신의 정보**를 읽습니다. 제품 대상 PID의 상태를 읽는 것과 구분하며, 상세 매핑 조회는 읽기 전용이어도 비용이 있습니다. 이 cat 명령은 별도로 실행하지 않았습니다. 아래 실습의 procfs 읽기와 구분합니다. [procfs 접근](https://man7.org/linux/man-pages/man5/proc.5.html), [smaps](https://man7.org/linux/man-pages/man5/proc_pid_smaps.5.html)

**저장된 실습 결과(Claude 실행 2026-10-05, WSL2 Linux 6.18.33.2):** 각각 8 MiB를 매핑하고 페이지를 만진 뒤, 익명·파일·memfd는 해당 `Pss_Anon`·`Pss_File`·`Pss_Shmem`이 각각 8,388,608 bytes 증가했습니다. 서로 다른 자식 프로세스의 전후 차이이며 일반적인 메모리 누수 판정 기준이 아닙니다. [요약과 모든 gzip 원자료의 hash](../../labs/results/1.1-r3/linux-memory.json)

같은 실행의 익명 매핑 단계에서 statm resident는 7,320페이지였고, 페이지 크기 4 KiB를 곱한 29,280 KiB가 status의 `VmRSS`와 같았습니다. memfd 단계의 shared는 `4,709 × 4 = 18,836 KiB`로 `RssFile 10,644 + RssShmem 8,192 KiB`와 같았습니다. **이 표본에서의 일치**이며 status/statm의 근사성이나 순차 조회의 한계를 없애지는 않습니다. [resident 원자료](../../labs/results/1.1-r3/linux-memory.raw/anonymous-allocated-statm.gz), [memfd status](../../labs/results/1.1-r3/linux-memory.raw/memfd-allocated-status.gz)

각 원천을 30회 읽은 경과 시간의 중앙값은 다음과 같습니다. `CLOCK_MONOTONIC_RAW`로 측정한 로컬 호출 비용이며 커널·매핑 수·캐시·스케줄링이 달라지면 결과도 달라집니다. 원천 간 고정 비용 배율로 사용하지 않습니다. 파싱된 값과 원자료, 표본의 중앙값 계산은 `verify_review_r3 --published`가 검사합니다.

| 매핑 단계 | status | smaps_rollup | smaps |
| --- | --- | --- | --- |
| 익명 | 14.9515 µs | 90.647 µs | 172.609 µs |
| 파일 | 19.06 µs | 105.816 µs | 195.4055 µs |
| memfd | 17.5295 µs | 105.3905 µs | 200.052 µs |

메모리 분류의 이동을 누수라고 단정하기 전에 [회수와 OOM](reclaim-and-oom.md)을 연결해 봅니다.

좀비는 계속 애플리케이션 코드를 실행하는 상태가 아닙니다. 부모가 종료 상태를 회수하지 않으면 필요한 프로세스 정보가 남을 수 있으므로, 좀비 증가에서는 부모의 회수 동작을 조사합니다. [Linux wait](https://man7.org/linux/man-pages/man2/wait.2.html)

## 파일 디스크립터는 파일만 가리키지 않는다

파일 디스크립터 FD는 프로세스가 연 객체에 접근하는 번호입니다. `/proc/PID/fd`에는 디스크립터별 링크가 있으며 일반 파일뿐 아니라 소켓·파이프 등도 나타납니다. 링크 조회와 상세 정보 접근에는 권한 조건이 있습니다. [Linux proc_pid_fd](https://man7.org/linux/man-pages/man5/proc_pid_fd.5.html)

`RLIMIT_NOFILE`은 열 수 있는 최대 디스크립터 번호보다 1 큰 경계이며 soft·hard limit의 의미를 구분합니다. 제한을 넘는 관련 호출은 `EMFILE`로 실패할 수 있습니다. [Linux getrlimit](https://man7.org/linux/man-pages/man2/getrlimit.2.html)

**분석 예:** 서비스의 신규 연결이 실패하고 FD 사용이 증가한다면 연결·파일을 닫는 동작, 풀의 수명, 제한값을 조사합니다. FD 수가 많다는 사실만으로 누수라고 판단하지 않고 업무 동시성과 해제 이후의 변화를 비교합니다.

## 프로세스 I/O의 두 관점

`/proc/PID/io`는 프로세스와 회수한 자식의 I/O 정보를 포함할 수 있습니다. `rchar`·`wchar`는 관련 읽기·쓰기 호출이 반환한 바이트를, `read_bytes`·`write_bytes`는 저장 계층과 관련된 회계를 다룹니다. 취소된 쓰기와 지원 범위도 확인해야 합니다. [Linux proc_pid_io](https://man7.org/linux/man-pages/man5/proc_pid_io.5.html)

논리적으로 많이 읽었어도 캐시에서 처리되면 저장 장치 읽기와 수치가 다를 수 있습니다. 부모와 자식의 값을 합산할 때는 포함 범위를 먼저 검토합니다. 이 지표를 네트워크 송수신량 또는 디스크 장치 전체 처리량과 동일시하지 않습니다.

## 수집 중 변하는 대상

프로세스 목록을 읽은 다음 상세 파일을 여는 사이에 대상이 종료될 수 있습니다. 여러 파일이 모두 하나의 원자적인 순간을 나타낸다고 가정하지 않습니다. 이것은 수집 설계에서 처리해야 하는 동시성 문제입니다.

| 상황 | 처리 제안 |
| --- | --- |
| 상세 조회 시 대상 없음 | 종료·교체 가능성을 기록하고 이전 값과 연결을 재확인 |
| 접근 거부 | 권한 제한 상태를 기록 |
| 카운터가 감소 | 수명 변경·초기화·원천 회계 조건 확인 |
| 스레드 수와 목록 불일치 | 수집 시각 차이와 조회 중 변화 확인 |

프로세스별 고비용 정보는 필요한 대상과 빈도로 제한합니다. 원천 파일을 읽는 권한과 부하를 수집 명세에 적고, 실패를 0으로 바꾸지 않습니다. 별도 운영 프로세스의 조회 명령은 실행하지 않았으며, 위 실습은 소유한 자식 프로세스의 관측입니다.

## 이해 확인

- `FDSize=1024`면 현재 1,024개 FD가 열려 있는가? **할당 슬롯 크기이므로 그렇지 않다.**
- 프로세스 이름이 같으면 재시작 전후의 누적값을 이어 붙여도 되는가? **실행 수명을 확인해야 한다.**
- 부모와 자식의 I/O를 모두 더하면 항상 전체인가? **원천의 자식 포함 조건을 확인해야 한다.**
- VmSwap에 프로세스가 참조하는 shmem의 swap도 모두 포함되는가? **private anonymous 기준이며 shmem swap을 포함하지 않습니다.**
- smaps_rollup은 페이지를 조사하지 않는 저비용 합계인가? **출력은 줄지만 상세 페이지 조사 비용이 남으므로 status와 같은 비용으로 가정하지 않습니다.**
- 상태 I인 kernel thread도 load average에 더하는가? **TASK_IDLE은 TASK_NOLOAD를 포함하므로 해당 대기 상태는 제외합니다.**

관련: [CPU](cpu.md), [메모리](memory.md), [블록 I/O](disk-io.md), [컨테이너 격리](../containers/isolation-and-lifecycle.md)
