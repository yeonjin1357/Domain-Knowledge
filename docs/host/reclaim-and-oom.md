# 메모리 회수와 OOM: 부족해지는 과정과 종료의 증거

> 상태: 검토됨 · 적용 범위: Linux 6.12 VM·OOM 코드, 6.13·6.15·6.18의 명시한 차이, cgroup v2 · 3d 원천·저장 증거 확인: 2026-10-06 · WSL 실습은 Claude가 2026-10-05 실행; 강제 회수·OOM 실험 없음

## 사용량이 그대로인데 요청이 느려지는 상황

서버가 빈 공간을 만들려고 오래된 페이지를 정리하면 애플리케이션은 실행 대신 그 작업을 기다릴 수 있습니다. 필요해서 다시 읽는 페이지를 계속 밀어내면 사용량 그래프는 비슷해도 응답 시간이 나빠집니다. **얼마나 차 있는가**, **얼마나 회수하는가**, **얼마나 기다리는가**, **무엇이 종료됐는가**는 서로 다른 질문입니다.

깨끗한 파일 캐시는 원본 파일에서 다시 읽을 수 있지만, 수정된 페이지는 writeback이 필요하고 익명 메모리는 보존할 swap 등의 조건을 봐야 합니다. 백그라운드 `kswapd` 회수와 할당 경로가 직접 수행하는 direct reclaim을 구분합니다. direct reclaim 증가는 할당자가 회수 작업에 참여한다는 단서이며 시간 자체를 측정한 값은 아닙니다. [Linux 6.12 회수 경로](https://github.com/torvalds/linux/blob/v6.12/mm/vmscan.c)

## /proc/vmstat의 누적값과 단위

다음은 Linux 6.12 이름을 기준으로 한 표입니다. 커널 설정·버전·배포판에 따라 키가 달라지므로 순서나 전체 필드 수를 고정하지 않습니다. 이 파일은 시스템 VM 통계이며 컨테이너 안에서 읽었다고 그 컨테이너만의 통계가 되지 않습니다. [vmstat 출력](https://github.com/torvalds/linux/blob/v6.12/mm/vmstat.c), [proc_vmstat](https://man7.org/linux/man-pages/man5/proc_vmstat.5.html)

| 원천 | 단위·형태 | 의미와 주의 |
| --- | --- | --- |
| `pgscan_kswapd`, `pgscan_direct` | 누적 페이지 수 | 전역 회수 경로의 scan 계정; cgroup 대상 회수는 제외. MGLRU의 계수 지점은 아래 참고 |
| `pgsteal_kswapd`, `pgsteal_direct` | 누적 페이지 수 | 전역 회수 경로의 회수량; cgroup 대상 회수는 제외 |
| `pgscan_anon/file`, `pgsteal_anon/file` | 누적 페이지 수 | 익명/파일 유형별 계정으로 cgroup 대상 회수도 포함; 위 두 행과 같은 모집단의 분할이 아님 |
| `allocstall_*` | 누적 사건 수, zone별 | 할당에 따른 회수 진입의 단서; 대기 중인 프로세스 수나 µs가 아님 |
| `workingset_refault_anon/file` | 누적 페이지 수 | 이전에 밀려났던 페이지를 다시 가져오는 refault; 모든 page fault와 같지 않음 |
| `pswpin`, `pswpout` | 누적 swap 페이지 수 | swap backing 저장소 읽기/쓰기 경로의 페이지 계정; zswap 적재·zero 최적화까지 합친 총 회수량이 아님 |
| `oom_kill` | 누적 OOM kill 계수 | 커널 OOM victim 처리 경로의 계수; 호스트 전체 부족 사건 수로 바로 해석하지 않음 |

회수량은 [vmscan](https://github.com/torvalds/linux/blob/v6.12/mm/vmscan.c), refault는 [workingset의 folio 페이지 수 계정](https://github.com/torvalds/linux/blob/v6.12/mm/workingset.c)을 따른다. `allocstall_*`은 같은 커널에서 cgroup reclaim을 제외한 `do_try_to_free_pages` 경로에서 증가한다. `oom_kill`은 전역·memcg OOM이 공유하는 kill 경로에서 증가하므로 “호스트 OOM 발생 횟수”라는 이름은 범위를 과장한다. 한 OOM 처리의 희생자 수와 사건 수도 구분한다. [OOM 계정 코드](https://github.com/torvalds/linux/blob/v6.12/mm/oom_kill.c)

특히 Linux 6.12의 `shrink_inactive_list`와 MGLRU `scan_folios`·`evict_folios`는 kswapd/direct 전역 계수를 `!cgroup_reclaim(sc)` 조건에서 증가시키지만 anon/file 계수에는 그 조건을 두지 않습니다. 컨테이너의 memory.high/max/reclaim에 따른 회수가 전역 `pgscan_direct`에 그대로 나타난다고 가정하지 않습니다. MGLRU의 scan 계수는 조사한 모든 페이지가 아니라 **회수 대상으로 LRU에서 분리한 isolated 페이지 수**를 넣으므로, 옛 LRU 경로와 비율의 의미도 달라집니다. [6.12 계수 지점](https://github.com/torvalds/linux/blob/v6.12/mm/vmscan.c)

**계산 예시:** 초기화·부팅 변경이 없는 10초 동안 direct scan이 10,000페이지, direct steal이 2,500페이지 증가했다면 관측 구간의 회수/scan 비는 `2,500 / 10,000 = 25%`입니다. scan 증가가 0이면 비율을 계산하지 않습니다. 같은 커널·회수 경로·범위에서 추이를 비교하고, MGLRU 여부와 서로 다른 수집 시점을 기록합니다. 이를 페이지 검사의 엄밀한 성공 확률이나 보편적인 장애 임계값으로 쓰지 않습니다.

**계산 예시:** base page가 4 KiB인 환경에서 10초 동안 `pswpout`이 512 증가하면 페이지 환산량은 2 MiB, 평균 0.2 MiB/s입니다. 페이지 크기를 4 KiB로 고정해 구현하지 않습니다. Linux 6.12에서 zero-filled folio의 최적화는 `swpout_zero`, zswap의 메모리 내 압축 저장은 `zswpout`으로 집계하며, 그 시점에는 backing 저장소 쓰기의 `pswpout`을 증가시키지 않습니다. 따라서 `pswpout`만으로 모든 swap-out 활동을 세면 빠지는 경로가 있습니다. 반면 **zram은 swap backing block device이므로 그쪽 쓰기는 pswpout에 포함**됩니다. 둘을 같은 “압축 swap 제외” 규칙으로 처리하지 않으며, 페이지 환산량을 물리 디스크 쓰기 바이트로 단정하지도 않습니다. [6.12 page_io](https://github.com/torvalds/linux/blob/v6.12/mm/page_io.c), [zswap 계정](https://github.com/torvalds/linux/blob/v6.12/mm/zswap.c), [zram](https://docs.kernel.org/admin-guide/blockdev/zram.html)

## cgroup에서 같은 질문을 한다

`memory.stat`의 `pgscan`, `pgsteal`, `pgscan_kswapd/direct`, `pgsteal_kswapd/direct`, `workingset_refault_anon/file`은 해당 cgroup 범위의 회수·refault를 조사하는 원천입니다. `anon`, `file`, `shmem` 같은 바이트 단위 상태값과 페이지·사건 누적값을 같은 단위로 합치지 않습니다. 모든 vmstat 이름에 동일한 cgroup 필드가 있다고 가정하지 않으며 `allocstall_*`을 이름만 바꾸어 만들어 내지 않습니다. [cgroup v2 memory.stat](https://docs.kernel.org/6.12/admin-guide/cgroup-v2.html#memory-interface-files)

버전 분기도 필요합니다. upstream **6.13부터 memory.stat에 pswpin/pswpout**, **6.15부터 pgscan_proactive/pgsteal_proactive**가 들어옵니다. 후자의 `memory.reclaim`에 의한 자발적 회수는 direct 분류에서 분리됩니다. 6.12 수집 계약을 그대로 적용하면 새 키를 누락하거나 direct 감소를 회수 감소로 오독할 수 있습니다. 배포판 backport를 고려해 버전과 실제 필드 가용성을 함께 확인합니다. [6.13 memcontrol](https://github.com/torvalds/linux/blob/v6.13/mm/memcontrol.c), [6.15 memcontrol](https://github.com/torvalds/linux/blob/v6.15/mm/memcontrol.c), [6.15 reclaimer_offset](https://github.com/torvalds/linux/blob/v6.15/mm/vmscan.c), [6.18 계정](https://github.com/torvalds/linux/blob/v6.18/mm/memcontrol.c)

`memory.swap.current`는 현재 swap 사용량이지 swap I/O율이 아닙니다. `memory.events`의 `high`는 high 경계로 인한 throttle·direct reclaim, `oom`은 메모리 할당이 OOM 상태에 이른 계수, `oom_kill`은 해당 그룹의 프로세스가 OOM killer에 의해 죽은 계수입니다. `oom`이 증가해도 반드시 kill이 발생하지 않으며, `oom_kill`만으로 한도 초과의 원인을 확정할 수 없습니다. 기본 `memory.events`는 하위 계층 사건도 포함하므로 `memory.events.local`과 mount 옵션을 확인합니다. [events·swap 규약](https://docs.kernel.org/6.12/admin-guide/cgroup-v2.html#memory-interface-files)

회수율·refault율이 증가하면서 `memory.pressure`와 요청 지연도 증가하면 working set이 유효 용량보다 큰지 조사합니다. 단순히 캐시를 비우는 것을 해결책으로 제시하지 않습니다. 캐시 제거가 재읽기 비용을 더 늘릴 수 있기 때문입니다.

## OOM 로그에서 원인 범위와 희생자를 분리한다

Linux 6.12의 커널 로그는 다음 필드를 원인 조사에 사용합니다. 로그 문구를 장기 고정 API로 취급하지 않고 커널별 parser와 원문을 보존합니다. [oom_kill.c](https://github.com/torvalds/linux/blob/v6.12/mm/oom_kill.c), [memcontrol.c의 OOM 문맥](https://github.com/torvalds/linux/blob/v6.12/mm/memcontrol.c)

| 필드·문구 | 질문 |
| --- | --- |
| `invoked oom-killer`, `gfp_mask`, `order` | 어떤 할당 시도가 OOM 처리를 유발했는가? 이 작업이 최종 희생자라는 뜻은 아님 |
| `constraint`, `nodemask`, `mems_allowed` | 전체 메모리뿐 아니라 cpuset·mempolicy 제한이 관련됐는가? |
| `global_oom`, `oom_memcg`, `task_memcg` | OOM 판단 범위와 희생자의 cgroup은 무엇인가? |
| `Killed process`, PID·UID·comm | 어떤 실행이 종료됐는가? PID 재사용과 namespace도 확인 |
| `total-vm`, `anon-rss`, `file-rss`, `shmem-rss`, `pgtables` | 주소 공간·상주 분류·페이지 테이블 사용량; total-vm을 RAM 점유로 읽지 않음 |
| `oom_score_adj` | `invoked oom-killer` 줄은 **유발한 작업**, `Killed process` 줄은 **희생자**의 조정값; 서로 다른 대상 필드로 저장 |

`/proc/PID/oom_score`는 현재 조건에서의 badness 점수이며 미래에 죽을 확률이 아닙니다. `oom_score_adj`의 범위는 −1000…1000이고 −1000은 커널 OOM 선정에서 제외하는 특수값입니다. 이 보호를 일반 SIGKILL이나 userspace 메모리 관리자의 종료까지 막는 것으로 해석하지 않습니다. 기본 수집기는 값을 읽으며 조정값을 바꾸지 않습니다. [oom_score](https://man7.org/linux/man-pages/man5/proc_pid_oom_score.5.html), [oom_score_adj](https://man7.org/linux/man-pages/man5/proc_pid_oom_score_adj.5.html)

Linux 6.12의 `/proc/PID/oom_score`는 `totalram_pages + total_swap_pages`를 분모 기준으로 사용합니다. 실제 memcg OOM은 `mem_cgroup_get_max()`로 정한 해당 범위의 totalpages를 사용하므로, proc 점수 목록을 cgroup OOM의 실제 희생자 순위라고 표시하지 않습니다. [proc 점수 계산](https://github.com/torvalds/linux/blob/v6.12/fs/proc/base.c), [OOM 범위별 분모](https://github.com/torvalds/linux/blob/v6.12/mm/oom_kill.c)

## 종료 원인별 증거

| 분류 | 필요한 증거 조합 | 혼동하기 쉬운 것 |
| --- | --- | --- |
| 전역 또는 할당 범위의 커널 OOM | 커널 OOM 문맥·제약, 당시 가용량·회수·PSI, 희생자 수명 | `oom_kill` 증가만으로 물리 RAM 전체 고갈 확정 |
| cgroup 한도 관련 OOM | `oom_memcg`, 유효 조상 한도, events 차분, 해당 컨테이너 종료 | 현재 사용량이 한도보다 낮으므로 과거 OOM 부정; 종료 후 이미 해제됐을 수 있음 |
| Kubernetes node-pressure eviction | Pod `Evicted` 상태·메시지, kubelet 이벤트·신호 | 모든 Evicted를 컨테이너 memory.max 초과로 취급 |
| 다른 SIGKILL·userspace 종료 | 서비스 관리자·운영 조작 등의 기록 | exit 137만으로 OOMKilled 확정 |

Pod의 `state.terminated`와 `lastState.terminated`를 함께 확인하는 이유와 kubelet의 종료 구분은 [자원 압박과 종료](../kubernetes/pressure-and-termination.md)에 있습니다. [컨테이너 메모리 회계](../containers/memory-accounting-and-oom.md)와 연결해 원천마다 대상·수명을 맞춥니다.

## 수집과 제품 적용 제안

읽기 전용 예시는 `cat /proc/vmstat`, `cat /proc/pressure/memory`, `getconf PAGESIZE`입니다. 대상 PID의 score/status 읽기는 procfs 접근 정책을 따릅니다. 커널 로그 조회인 `dmesg`는 `dmesg_restrict`·권한·컨테이너 격리로 제한될 수 있고, 전체 로그 반복 수집은 비용과 민감 정보 범위를 검토합니다. 위 쉘 명령과 dmesg 예시는 별도로 실행하지 않았으며, 아래 실습에서는 procfs 파일만 읽었습니다. 권한 부족·로그 유실을 “OOM 없음”으로 변환하지 않습니다. [dmesg 권한](https://man7.org/linux/man-pages/man1/dmesg.1.html)

제품에는 호스트 boot ID와 cgroup 수명을 붙여 누적값을 차분하고, 회수 활동·PSI·종료 타임라인을 나란히 표시할 것을 제안합니다. 키가 없는 커널에는 미지원 상태를 남깁니다. 그룹과 조상 통계를 중복 합산하지 않고, 종료 직전 한도와 종료 후 사용량을 다른 시점으로 보존합니다.

**저장된 실습 결과:** 2026-10-05의 WSL2 Linux 6.18.33.2에서 `oom_kill`, `pgscan/pgsteal_*`, `allocstall_*`, `workingset_refault_*` 키를 읽었고, `pgscan_proactive`·`pgsteal_proactive`도 존재했습니다. 선택한 계수의 당시 값은 모두 0이었습니다. 이는 원천의 존재·형식 관측이며, 강제 메모리 압박·회수·OOM 동작 검증은 아닙니다. 익명·파일·memfd의 8 MiB 매핑 결과는 [프로세스 장](processes.md)에 연결했습니다. [요약과 원자료 목록](../../labs/results/1.1-r3/linux-memory.json), [vmstat 원문 gzip](../../labs/results/1.1-r3/linux-memory.raw/vmstat.gz)

## 이해 확인

1. `allocstall` 100은 100초 대기인가? **사건 계수이므로 시간을 알 수 없습니다. PSI와 지연을 함께 봅니다.**
2. 컨테이너 `oom_kill` 증가만으로 memory.max 초과를 확정하는가? **커널 OOM 문맥과 한도·events·종료 정보를 대조해야 합니다.**
3. swap 사용량이 일정하면 swap I/O도 없는가? **점유량과 들어오고 나가는 활동은 다릅니다.**

관련: [메모리 기초](memory.md), [프로세스 메모리 원천](processes.md), [NUMA·PSI](numa-and-pressure.md)
