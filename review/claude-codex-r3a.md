# Claude–Codex 3라운드 3a: 실행 준비 기록

확인일: 2026-10-05. 브랜치 `review/claude-codex-r3`, 시작 revision `9dfbede`. 원고·판 번호·기존 실행 결과를 바꾸지 않았다. Linux/WSL 바이너리와 실험 SQL은 **실행하지 않았다**. 실제 실행은 Claude가 담당한다.

## 증거와 경계

[증거 크기 정책](../labs/review-r3/evidence-policy.md): 요약 JSON 1 MiB, 원시 파일 하나 16 MiB, 원시 총량 64 MiB. JSON과 gzip sidecar 전체가 출판 단위다. 압축 전후 SHA256과 바이트 수를 검증하고, 초과·누락·변조·덮어쓰기를 거부한다. sidecar gzip은 mtime=0이다. 예전 12.9 MB OTel 증거는 그대로 둔다.

[공통 실행기](../scripts/lab_r3_common.py)는 기존 r2의 소유 프로세스 종료와 native_directory 구현을 가져오며 r2 실행기를 수정하지 않는다. 모든 출력은 `.lab-runs/`, 자산은 `.tools/`에 둔다. MySQL 데이터·소켓은 권한이 검증된 Linux native_directory에 만들고 소유 프로세스가 종료된 뒤 제거한다. 쿼리는 새 로컬 인스턴스에만 실행하며 최초 연결에서 `@@datadir`을 대조한다. 시스템 설치, 서비스 등록, root, 클라우드 호출, 시계 설정 변경은 하지 않는다.

실패 실행도 진단 JSON을 남기며, 정리 실패 또는 보존 실패를 성공으로 보고하지 않는다. Ctrl-C를 포함한 Python 예외 경로는 정리한다. SIGKILL·VM 종료처럼 실행기가 더 이상 실행되지 못하는 경우까지 정리를 보증할 수는 없으며 독점 생성한 `incomplete` 결과가 남는다. `recorded`는 기록 완료이며 가설 지지는 개별 `supported` 판정이다.

## 실습과 판정 기준

| 실습 | 준비 파일 | 성공·반증 기준과 해석 한계 |
| --- | --- | --- |
| Linux 메모리 | [run_linux_memory_r3_lab.py](../scripts/run_linux_memory_r3_lab.py) | 익명 private, 파일 private read-only, memfd shared를 각각 별도 자식에서 기본 8 MiB touch. smaps_rollup의 해당 Pss_Anon/File/Shmem 증가가 크기의 80% 이상이면 지지, 완전한 표본에서 미달하면 반증. 한 프로세스만 매핑한 페이지라 이 실험의 PSS/RSS 분류를 대조할 수 있다. status/statm은 근사·비동기 값이므로 같아야 한다고 단정하지 않는다. before/allocated/released의 VmRSS·RssAnon·RssFile·RssShmem·VmSwap, statm 페이지와 바이트 환산, smaps/rollup 원문을 보존한다. |
| 조회 비용 | 같은 실행기 | 자식이 정지한 구간에서 status·smaps_rollup·smaps 순서를 섞어 각각 30회 읽고 RAW ns·바이트 수·median·p95를 기록. 보편적인 비용 순서를 성공 조건으로 만들지 않는다. 작은 프로세스의 관측값만 제공한다. |
| PSI·vmstat·cgroup | 같은 실행기 | `/proc/pressure/{cpu,memory,io,irq}` 존재·권한·형식, vmstat의 요청한 prefix와 원문을 기록. 부재를 0으로 바꾸지 않는다. 이미 노출된 cgroup v2와 조상 한도만 읽는다. `--probe-delegated-cgroup`은 현재 cgroup 아래 빈 child 생성·제거만 시도한다. controller 활성화·한도 쓰기·프로세스 이동은 하지 않는다. |
| MySQL RR 잠금 | [run_mysql_r3_lab.py](../scripts/run_mysql_r3_lab.py) | `FORCE INDEX(k)`로 RR 조회를 고정. gap/next-key의 granted lock과 INSERT_INTENTION waiter, data_lock_waits 연결, sys.innodb_lock_waits 행, rollback 후 INSERT 진행을 모두 확인한다. 완전한 관측이 조건과 다르면 반증. 스케줄링/시작 전제가 충족되지 않으면 오류/미완료로 남긴다. |
| MySQL deadlock | 같은 실행기 | 두 트랜잭션이 서로의 행을 요구. ERROR 1213 한 건과 `LATEST DETECTED DEADLOCK` 원문이 있으면 지지. 희생 트랜잭션의 신원은 고정하지 않는다. |
| MySQL GTID | 같은 실행기 | source/replica 2개, baseline catch-up의 0 → IO thread 정지·relay 소진 후 NULL → 재개 → SQL thread 정지 시 receiver가 GTID를 받았지만 적용하지 않았고 NULL → 재개 후 GTID 일치. worker·connection 표 전체와 timestamp를 같이 저장한다. NULL, `"0"`, 빈 문자열, 0 timestamp를 구별한다. 각 상태는 순차 표본이며 원자적 snapshot이 아니다. |
| MySQL 기본값 | 같은 실행기 | 바꾸지 않은 `innodb_flush_log_at_trx_commit`·`sync_binlog`가 1인지 기록한다. 전원 장애·fsync·복제 지속성을 검증한 것이 아니다. |
| Histogram | [run_histogram_r3_lab.py](../scripts/run_histogram_r3_lab.py), [fixtures](../labs/review-r3/histograms/fixture.json) | 예시 `[1.25,1.75,2.5,3.5]`, count 4, sum 9. classic·exponential native·custom native를 같은 경계/개수로 입력한다. q25의 예상값은 선형 1.5, 지수 √2; fraction(1,1.5)은 선형 0.25, 지수 log2(1.5)/2; count는 4. classic float에 histogram_count는 빈 결과. promtool debug의 실제 recording-rule 값을 파싱하며 예상값으로 대체하지 않는다. |
| 시계 상태 | [run_clock_r3_lab.py](../scripts/run_clock_r3_lab.py) | 2초 sleep 전후의 MONO/RAW/process clock·읽기 전용 adjtimex와 timedatectl show/show-timesync/timesync-status 원문. 동기화 전용 명령이 성공하면 정보 노출을 지지. 서비스 부재는 blocked이며 비동기 상태의 증거가 아니다. RAW 외부 정확도와 tick 설정 주체를 확정하지 않는다. |

강제 메모리 압박·OOM·swap 유발은 제외했다. 비 root WSL에서 다른 작업에 영향이 없음을 보장할 격리/위임이 없기 때문이다. 메모리 매핑 전 MemAvailable과 보이는 cgroup 조상 여유를 점검한다. 이 점검은 순간 관측이며 메모리 예약이 아니다. MySQL은 가시 여유 1 GiB 이상이 필요하다.

## 원천 확인

- Linux 분류·비동기 RSS·smaps 비용: [proc 문서](https://docs.kernel.org/filesystems/proc.html), [PSI 형식](https://docs.kernel.org/accounting/psi.html), [cgroup v2](https://docs.kernel.org/admin-guide/cgroup-v2.html). irq 파일 유무나 cgroup 생성 가능 여부는 실행 결과에서만 판단한다.
- MySQL 잠금: [InnoDB locking](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking.html), [data_locks](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-data-locks-table.html), [sys view](https://dev.mysql.com/doc/refman/8.4/en/sys-innodb-lock-waits.html), [deadlock](https://dev.mysql.com/doc/refman/8.4/en/innodb-deadlocks-handling.html).
- NULL/0 기준은 [8.4 SHOW REPLICA STATUS](https://dev.mysql.com/doc/refman/8.4/en/show-replica-status.html), [9.7의 같은 규약](https://dev.mysql.com/doc/refman/9.7/en/show-replica-status.html)과 대조했다. [worker timestamp](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-replication-applier-status-by-worker-table.html), [sync_binlog](https://dev.mysql.com/doc/refman/8.4/en/replication-options-binary-log.html#sysvar_sync_binlog), [InnoDB 설정](https://dev.mysql.com/doc/refman/8.4/en/innodb-parameters.html#sysvar_innodb_flush_log_at_trx_commit).
- mysql CLI의 `--unbuffered` 출력 flush와 XML NULL 표기는 [8.4.10 client/mysql.cc](https://github.com/mysql/mysql-server/blob/mysql-8.4.10/client/mysql.cc)의 `com_go`·`print_table_data_xml` 경로를 확인했다. Python 의존 패키지를 설치하지 않는다.
- Histogram 표기·debug dump는 [3.13.4 unit testing](https://github.com/prometheus/prometheus/blob/v3.13.4/docs/configuration/unit_testing_rules.md), [3.15.0 unit testing](https://github.com/prometheus/prometheus/blob/v3.15.0/docs/configuration/unit_testing_rules.md), [promtool 소스](https://github.com/prometheus/prometheus/blob/v3.15.0/cmd/promtool/unittest.go), [출력 형식](https://github.com/prometheus/prometheus/blob/v3.15.0/promql/value.go), [버킷 경계](https://github.com/prometheus/prometheus/blob/v3.15.0/model/histogram/generic.go), [보간 규약](https://prometheus.io/docs/prometheus/latest/querying/functions/#histogram_quantile)과 대조했다.
- 고정한 [3.13.4](https://github.com/prometheus/prometheus/blob/v3.13.4/CHANGELOG.md)·[3.15.0](https://github.com/prometheus/prometheus/blob/v3.15.0/CHANGELOG.md) CHANGELOG에서 Native Histogram 안정화 항목은 **3.9.0**이다. 이번 test rules 호출은 feature flag 없이 실행한다. 서버의 `scrape_native_histograms` 설정 및 실제 수집·저장·remote write는 이 실습에서 검증하지 않는다.
- 부동소수점 마지막 비트 차이를 피하기 위해 promtool의 예상값 assertion은 1e9를 곱해 반올림한 정수로 검사한다. 출판용 숫자는 반올림 전 debug 출력에서 읽고 별도로 1e-12 오차 이내인지 대조한다.
- 시계 관측은 기존 1라운드 검증 실행기의 read-only 함수를 재사용하며 해당 파일 hash도 입력에 포함한다. [clock_gettime](https://man7.org/linux/man-pages/man2/clock_gettime.2.html), [adjtimex](https://man7.org/linux/man-pages/man2/adjtimex.2.html).

## 자산 검증

[manifest](../labs/review-r3/assets.json)에 공식 URL·고정 SHA256·서명/검증 파일 URL을 기록했다. Windows Python으로 MySQL minimal tar.xz 두 개를 내려받아 기존 Git 배포 GPG/GPGV로 검증한 뒤 압축을 풀었다. GPG key import·agent·시스템 설치를 사용하지 않았다. 개인 키링 대신 `.tools/r3/archives/` 아래 일회성 dearmor keyring을 썼다.

공식 키: [RPM-GPG-KEY-mysql-2025](https://repo.mysql.com/RPM-GPG-KEY-mysql-2025), SHA256 `a4bcd9f16a53cc763f87b9955dbcdced33c7aa90296b157eb6ceef0f156f4327`. [공식 지문 설명](https://dev.mysql.com/doc/refman/8.4/en/checking-gpg-signature.html)의 `BCA43417C3B485DD128EC6D4B7B3B788A8D3785C`와 두 자산의 `VALIDSIG`가 일치했고 gpgv exit=0이다. 아래 MySQL SHA256은 **공식 서명으로 인증한 파일을 로컬에서 계산한 값**이며 공식 SHA256 checksum 게시물이라는 뜻이 아니다.

| 고정 자산 | 검증한 SHA256 |
| --- | --- |
| [MySQL 8.4.10 minimal, glibc 2.28 amd64](https://cdn.mysql.com/Downloads/MySQL-8.4/mysql-8.4.10-linux-glibc2.28-x86_64-minimal.tar.xz) | `88ac9cc85bed076c4c8c6e816c3369a6febfbb5db13e6e174f1d8971161e0b77` |
| [MySQL 9.7.2 minimal, glibc 2.28 amd64](https://cdn.mysql.com/Downloads/MySQL-9.7/mysql-9.7.2-linux-glibc2.28-x86_64-minimal.tar.xz) | `6fe0baf13792e56afa3d93d6a174b4d5700901db1c8d09665225423dc094d0bb` |
| [Prometheus 3.13.4 linux-amd64](https://github.com/prometheus/prometheus/releases/download/v3.13.4/prometheus-3.13.4.linux-amd64.tar.gz) | `87f21a66f96c597a189cef8d640e8921b621fc17a9feff707c332c4f3b3ddd56` |
| [Prometheus 3.15.0 linux-amd64](https://github.com/prometheus/prometheus/releases/download/v3.15.0/prometheus-3.15.0.linux-amd64.tar.gz) | `2a542df32eac02ee17b9d844fb2aa1de00dafa5476579ba8a3ba862e9d572ea0` |

Prometheus는 기존 `.tools/r2` 실행 파일을 재사용한다. GitHub release API digest와 각 공식 `sha256sums.txt`를 이번에도 받아 동일함을 확인했다. MySQL은 8.4/9.7 LTS 계열의 위 두 패치로 고정했으며 최신 패치라는 주장은 하지 않는다. 요청 계열의 공식 자산이 없는 경우는 없었다.

tar member를 직접 검사한 뒤 regular file만 생성했다. tar symlink는 인증된 아카이브 내부 regular target의 내용으로 복사해 Windows symlink 권한 없이 재현한다. 장치 파일·경로 이탈·순환 링크·중복 일반 파일은 거부한다. MySQL tar가 반복하는 동일 부모 디렉터리 header만 허용한다.

ELF DT_NEEDED를 Windows에서 읽어 두 서버가 `libaio.so.1`, `libnuma.so.1`, 클라이언트가 `libncurses.so.6`·`libtinfo.so.6`에 의존함을 확인했다. 공식 tar에 포함되지 않는 이 라이브러리가 WSL에 있는지는 실행하지 않아 알 수 없다. 기존 라이브러리가 없으면 `blocked`; 설치나 이름 우회 symlink를 만들지 않는다. OpenSSL/Abseil 등 번들 라이브러리는 해당 자산의 private lib 경로를 사용한다.

## Claude 실행 순서

아래 명령은 저장소 루트 PowerShell에서 순서대로 사용한다. Linux 명령의 `python3 -B`는 bytecode 쓰기를 막는다. 결과 이름이 이미 있으면 덮어쓰지 말고 새 접미사를 붙여 실행한다. 실행 중 입력 파일을 수정하지 않는다.

```powershell
python -X utf8 -B scripts/get_review_r3_assets.py --verify-only
python -X utf8 -B scripts/verify_review_r3.py --assets
wsl -d Ubuntu --cd /mnt/c/project/Domain-Knowledge -- python3 -B scripts/run_linux_memory_r3_lab.py --probe-delegated-cgroup --output .lab-runs/r3/linux-memory.json
wsl -d Ubuntu --cd /mnt/c/project/Domain-Knowledge -- python3 -B scripts/run_histogram_r3_lab.py --output .lab-runs/r3/histograms.json
wsl -d Ubuntu --cd /mnt/c/project/Domain-Knowledge -- python3 -B scripts/run_mysql_r3_lab.py --version 8.4.10 --output .lab-runs/r3/mysql-8.4.10.json
wsl -d Ubuntu --cd /mnt/c/project/Domain-Knowledge -- python3 -B scripts/run_mysql_r3_lab.py --version 9.7.2 --output .lab-runs/r3/mysql-9.7.2.json
wsl -d Ubuntu --cd /mnt/c/project/Domain-Knowledge -- python3 -B scripts/run_clock_r3_lab.py --output .lab-runs/r3/clock-state.json
python -X utf8 -B scripts/verify_review_r3.py --result .lab-runs/r3/linux-memory.json --result .lab-runs/r3/histograms.json --result .lab-runs/r3/mysql-8.4.10.json --result .lab-runs/r3/mysql-9.7.2.json --result .lab-runs/r3/clock-state.json
```

Windows 다운로드·검증·추출은 완료했다. 자산을 지운 별도 checkout에서는 첫 명령의 `--verify-only`를 생략해 고정 공식 자산을 다시 준비할 수 있다. GPG가 없으면 설치하지 말고 그 사유를 보고한다. 기존 Prometheus r2 도구는 재사용 전제다.

| 단계 | 예상 시간 | 예상 메모리 | 출력 |
| --- | --- | --- | --- |
| 자산 재검증·준비 검사 | 5–30초, 저장소 드라이브에 따라 증가 | 약 100 MiB 이하 | PASS 및 `.lab-runs/r3/preparation/`의 제거되는 합성 fixture |
| Linux 메모리 | 5–20초 | 약 50–100 MiB, 매핑은 8 MiB씩 순차 | `linux-memory.json` + `linux-memory.raw/` |
| Histogram | 5–30초 | 약 100–300 MiB | `histograms.json` + `histograms.raw/` |
| MySQL 각 버전 | 1–5분; 의존성 차단 시 수초 | 두 인스턴스 합계 약 0.5–1 GiB, 시작 전 1 GiB 가시 여유 요구 | 버전별 JSON + 같은 stem의 `.raw/` |
| 시계 | 3–30초 | 약 30–60 MiB | `clock-state.json` + `clock-state.raw/` |
| 결과 검증 | 1–10초 | 약 100 MiB 이하 | PASS 또는 명시적 실패 |

위 비용은 예산 추정이며 실제 측정값이 아니다. 자산 디스크는 압축+전개에 약 1.3 GiB, MySQL 임시 데이터는 버전당 약 1 GiB 여유를 예상한다. 두 MySQL 버전을 동시에 돌리지 않는다. 실패 JSON은 `--allow-error --result 경로`로 무결성을 조사할 수 있지만 출판 승인이나 실습 성공을 뜻하지 않는다.

## 기존 검증 연결 복구

처음 실행한 여섯 검사 중 `verify_revision`만 실패했다. r2 결과 네 개의 manifest hash는 `6859cca0…`(CRLF)인데 `.gitattributes`의 LF 정규화 후 현재 파일은 `bb4424f3…`였다. 현재 manifest와 2a 기록의 `assets` 객체가 동일함을 확인했고, CRLF로 직렬화한 바이트가 **기존 기록 hash 전체와 정확히 일치**했다.

기존 증거를 바꾸는 대신 [보관 manifest](../labs/archive/review_r2_assets_2026_10_05.json)를 추가하고 [provenance](evidence-provenance.json)에 네 결과의 입력 연결을 추가했다. 이 파일에는 `-text`를 지정해 다시 정규화되지 않게 했다. 보관 runner·기존 결과·해시는 그대로다. 검증기를 느슨하게 만들거나 hash 비교를 생략하지 않았다.

## 준비 검증과 남은 일

[verify_review_r3.py](../scripts/verify_review_r3.py)는 구문·독립 산술·출력 파서·NULL 구분·gzip hash/크기·경로·덮어쓰기·실패 정리를 검사한다. 결과가 오면 입력 hash와 raw 파싱 결과, RSS delta, histogram 실제 값과 판정을 다시 계산한다. `--assets`는 도구를 실행하지 않고 archive/추출 파일 hash를 검사한다.

여섯 기존 검사는 통과했다. 구체적인 명령·출력과 이번 준비 입력 hash는 [기계 판독 기록](claude-codex-r3a.json)에 보존한다. 원고가 바뀌지 않아 BOOK 재생성은 필요하지 않았다. HTML 화면 검사는 이번 준비 범위에서 실행하지 않았다.

추가 의사결정 질문은 없다. Claude는 각 JSON **및 `.raw/` 전체**, 특히 MySQL preflight 차단 여부와 cgroup/irq/timesyncd 가용성 결과를 돌려주면 된다. Linux 실행 성공 여부는 3b 결과 전까지 미확인이다.
