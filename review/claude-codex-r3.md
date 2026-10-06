# Claude–Codex 3라운드: 3f 결과 확정과 검토 이력

## 3f 범위와 결론 — 2026-10-06

Claude가 2026-10-06 KST에 실행한 MySQL 8.4.11·9.7.2 r2를 원자료와 대조해 출판했다. 원문 UTC 시작 시각은 각각 2026-10-05 16:14:23.655302, 16:15:08.510543이다. 두 버전 모두 **supported 5·gzip 132개**이며 기존 r1은 **판정 설계 결함으로 반증된 실행**으로 그대로 보존했다. branch `review/claude-codex-r3`·HEAD `9dfbede`·판 번호·book.json.as_of는 유지했다. commit·push·branch 전환은 하지 않았다.

| 출판 JSON | SHA256 | 크기·판정 |
| --- | --- | --- |
| [8.4.11 r2](../labs/results/1.1-r3/mysql-8.4.11-r2.json) | `981b612dd4adcd5fd6e3a3c02a6c98104298c90e026d02f379f95d4421a86034` | JSON 324,817 B, gzip 132개·53,981 B; supported 5 |
| [9.7.2 r2](../labs/results/1.1-r3/mysql-9.7.2-r2.json) | `647cc93e33b75a3afef6bf250a34ce2bc6537a3c2273570438e28a2a753a10e5` | JSON 324,118 B, gzip 132개·54,178 B; supported 5 |

전달 JSON과 `.raw/` 전체를 byte 그대로 복사했다. 원본·기존 r1·당시 보존 실행기는 수정하지 않았다. r2 runner SHA256은 `fde7265ffe3a262a65a3722c0b026cc5e996de432613cf65826bab534c98de3b`이며 [provenance](evidence-provenance.json)와 각 결과의 입력 hash가 현재 실행기·고정 자산 manifest를 연결한다. 이번에는 실행기·manifest·공통 모듈을 변경하지 않았다. 검증기만 새 출판 근거와 본문 대조를 추가했다.

### 원자료에서 확인한 전후 관측

- **잠금:** 두 버전 모두 gap sys는 첫 조회 1행이었다. next-key sys는 `initial_query_refs`의 마지막 조회(client-0-15)에서 0행, `sys_visibility.query_refs`의 다음 조회(client-0-17)에서 1행이었다. 같은 waiter/blocker를 대상으로 잠금을 유지한 채 재조회했고, 직접 engine lock ID 관계와 blocker rollback 뒤 삽입 행도 확인했다. 두 번의 조회를 모든 환경에서 필요한 고정 재시도 횟수로 일반화하지 않는다.
- **복제:** `immediate_after_gtid_or_stop.baseline`은 목표 GTID가 실행된 뒤에도 Read/Exec=1073/158, SBS는 8.4.11에서 12·9.7.2에서 14였다. 파일·위치 검사 2회 뒤 1073/1073·SBS=0이 됐다. IO 중지의 위치 검사는 1회, 재개의 검사는 3회였다. 재개 직후에는 SBS=0인데 1611/1342인 표본도 있어서, 기대 SBS를 대기 조건으로 쓰지 않았다는 것을 저장된 표본으로도 확인했다.
- **최종 상태:** 두 버전이 아래 표와 같다. 모든 수치는 같은 `binlog.000001`에서 관측했으며 SQL/XML 원문까지 대조했다. 복제 worker 수는 `replica_parallel_workers=2`라는 명시 설정과 실제 조회값이 일치한다.

| 단계 | IO / SQL | Read/Exec | SBS |
| --- | --- | --- | --- |
| baseline | Yes / Yes | 1073 / 1073 | 0 |
| io_stopped | No / Yes | 1073 / 1073 | NULL |
| sql_stopped | Yes / No | 1611 / 1342 | NULL |
| resumed | Yes / Yes | 1611 / 1611 | 0 |

sys의 cache·join 구조와 GTID 적용/coordinator checkpoint 구분은 아래 3e에서 검토한 고정 소스 설명을 유지한다. r2는 표시가 바뀌기 전후를 직접 보존한 추가 근거다. r1의 빈 sys·SBS 13과 9.7.2 재개 1을 r2의 성공값으로 고쳐 쓰지 않았다. 이 결과로 내부 clock_diff 값이나 WSL 시계 조정의 인과를 확정하지 않는다.

[MySQL 본문](../docs/database/mysql-operations.md)은 r2의 최종 판정을 먼저 제시하고 r1의 원인을 짧은 학습 절로 남겼다. [실습 안내](../docs/cross-domain/reproducible-labs.md)·[검증](../docs/validation.md)·[검토](../docs/review.md)·[범위](../docs/coverage.md)도 갱신했다. 추가 장·판 번호 변경은 없다.

### 3라운드 출판 합계와 검증

최종 채택 실행인 메모리·분포·시계·MySQL r2는 **17개 supported 조건**이다. r1 반복 실행을 포함한 전체 보존 근거는 **7묶음·27개 판정(supported 23·refuted 4), gzip 525개**다. 요약 JSON은 총 1,174,117 B, gzip은 총 221,450 B이며 각 파일의 크기 제한을 만족한다. supported를 운영 환경 전체나 독립 기능 27개의 지원 인증으로 쓰지 않는다.

다음 명령을 Windows Python에서 실행해 PASS를 확인했다. 검사기는 완전한 gzip 복원·hash·SQL/XML·NULL·가시성/위치 전이·verdict·본문 값을 확인한다. DB 프로세스를 새로 띄운 것은 아니다.

```powershell
python -X utf8 -B scripts/verify_review_r3.py --result .lab-runs/r3/mysql-8.4.11-r2.json --result .lab-runs/r3/mysql-9.7.2-r2.json
python -X utf8 -B scripts/verify_review_r3.py --published
python -X utf8 -B scripts/build_book.py
python -X utf8 -B scripts/build_html.py
python -X utf8 -B scripts/check_docs.py
python -X utf8 -B scripts/verify_examples.py
python -X utf8 -B scripts/verify_contracts.py
python -X utf8 -B scripts/verify_revision.py
python -X utf8 -B scripts/build_book.py --check
python -X utf8 -B scripts/build_html.py --check
```

Claude가 전달한 3e HTML 화면 PASS는 [incoming receipt](html-check-r3e-incoming.json)의 hash `73df5acc3d85fd31eebfba3a2784d86cbb8ec56e9e328d7b2d9fe6ac9134e058`와 수신 당시 BOOK.html이 일치했다. 6 viewports·17 diagrams 검사 기록을 보존하며 새 생성본 검사와 구분한다. 새 3f HTML에 `python -X utf8 -B scripts/check_html.py`를 실행했으나 **Chrome DevTools의 `Page.enable`이 20초 시간 초과**로 exit 1이었다. [시도 기록](html-check-r3f-attempt.json)에 대상 HTML hash와 미완료 상태를 남겼다. 이전 PASS receipt는 덮이지 않았으며 새 생성본의 화면 PASS로 쓰지 않는다. 기본 6개 검사는 모두 통과했다. 화면 확인만 Claude가 같은 명령으로 다시 수행하면 되며 MySQL 재실행은 필요하지 않다.

3라운드의 MySQL 준비·실행·원인 분석·보완 결과 반영을 마쳤으며 추가 DB 재실행은 필요하지 않다. Lambda CloudWatch Duration의 suppressed init 포함, 내부 시계 보정값·WSL tick 설정 주체·RAW 외부 정확도는 이미 명시한 미확인 범위로 남는다. 이러한 범위를 임의로 사실로 채우거나 이번 supported 판정으로 대체하지 않는다.

이하 **3e·3d·3b 절은 당시 이력**이다. 당시 실행 대기·검증 대상·재현 명령을 현재 3f 상태로 읽지 않는다.

## 3e 범위와 결론 — 2026-10-06

Claude가 2026-10-05 UTC에 실행한 MySQL 8.4.11·9.7.2 r1의 원본 JSON·gzip 200개를 직접 대조했다. `supported 3, refuted 2`를 버전별로 유지해 출판했다. Codex는 Windows에서 저장 근거·공식 소스·수정한 관측 코드의 회귀 조건을 확인했으며 WSL/MySQL을 실행하지 않았다. branch `review/claude-codex-r3`·HEAD `9dfbede`·판 번호·book.json.as_of를 유지하고 commit·push·branch 전환은 하지 않았다.

두 refuted는 **즉시 관측 조건을 잘못 묶은 실험 설계**와 관련 있다. next-key 잠금이 없었던 것이 아니라 sys join이 비었으며, GTID 실행을 기다리지 않은 것이 아니라 coordinator 위치까지 갱신됐다고 가정했다. 그 조건을 반증한 실제 출력은 지우지 않는다. 보완한 runner의 DB 재실행은 새 r2 출력으로 Claude에게 요청한다.

### 출판·provenance

| 출판 JSON | SHA256 | 그대로 보존한 내용 |
| --- | --- | --- |
| [mysql-8.4.11-r1](../labs/results/1.1-r3/mysql-8.4.11-r1.json) | `1f2736fad023e23084b61dd2d55407c15e9ae28e7c1f6bd9adc782272b670ed6` | supported 3·refuted 2, JSON 204,624 B, gzip 100개·36,181 B |
| [mysql-9.7.2-r1](../labs/results/1.1-r3/mysql-9.7.2-r1.json) | `e97f442ce3701ac4ef8119de32c7219eeea9dfed70e004f7b0875506ed6c354c` | supported 3·refuted 2, JSON 204,128 B, gzip 100개·36,442 B |

원래 `.lab-runs/r3/` 파일은 변경하지 않았다. 같은 basename의 `.raw/`에 완전한 gzip을 복사했고 [provenance](evidence-provenance.json)가 당시 runner 입력을 [보존 실행기](../labs/archive/review_r3_2026_10_05/mysql_r1/run_mysql_r3_lab.py)로 연결한다. 그 runner SHA256은 `0bff81f2c5c9ac8de30b6b867f4706df8d81a70a56479adc47c10cfe47f8d171`이다. [당시 verifier](../labs/archive/review_r3_2026_10_05/mysql_r1/verify_review_r3.py)도 보존했다. 현재 runner hash로 옛 출력을 재작성하지 않았다.

[3e 분석 JSON](mysql-r3e-analysis.json)에 원본 hash·SQL query ref·sys XML hash·LOCK_MODE·GTID/worker timestamp·위치·시각 계산과 고정 소스 URL/hash를 남겼다. 검사는 gzip 복원과 SQL/XML 대조를 먼저 하고 분석 수치도 다시 계산한다. 이제 3라운드 출판은 **5묶음, 17개 판정(supported 13·refuted 4), gzip 261개**다. summary JSON 총 525,182 B와 gzip 총 113,291 B이며 이전 r2의 큰 증거는 변경하지 않았다.

### next_key_lock 판정: sys 즉시 표시 전제가 실패

두 버전 모두 `k X GRANTED`의 (10,1)·(20,2), `k X,GAP,INSERT_INTENTION WAITING`의 (20,2), `PRIMARY X,REC_NOT_GAP GRANTED`의 (1), TABLE `IX`를 기록했다. 요청/차단 `ENGINE_LOCK_ID`를 연결한 직접 대기 관계가 1개 있었다. blocker ROLLBACK 이후 INSERT가 오류 없이 완료됐다. **sys_rows만 빈 배열**이어서 기존 합성 성공 조건이 false였다. 기존 runner는 이미 next-key `X`와 INSERT_INTENTION 부분 문자열을 받으므로 `X,INSERT_INTENTION`만 기대한 문자열 결함은 아니다. 별도 gap 시나리오에는 `X,GAP`도 실제로 있었다.

직접 확인한 원천:

- [8.4.11 trx0i_s.cc](https://github.com/mysql/mysql-server/blob/mysql-8.4.11/storage/innobase/trx/trx0i_s.cc)의 `can_cache_be_updated`(679–699 부근)는 `steady_clock` 기준 마지막 cache 읽기 뒤 **100 ms 초과**를 요구한다. `trx_i_s_cache_end_read`(894–900 부근)가 last_read를 갱신한다. [9.7.2 같은 파일](https://github.com/mysql/mysql-server/blob/mysql-9.7.2/storage/innobase/trx/trx0i_s.cc)도 대조했다.
- [8.4.11 i_s.cc](https://github.com/mysql/mysql-server/blob/mysql-8.4.11/storage/innobase/handler/i_s.cc)의 INNODB_TRX 생성 경로와 [sys view SQL](https://github.com/mysql/mysql-server/blob/mysql-8.4.11/scripts/sys_schema/views/p_s/innodb_lock_waits.sql)은 live P_S 대기를 cached INNODB_TRX의 waiter/blocker에 inner join한다. 비교한 8.4.11·9.7.2의 cache 파일과 sys SQL은 각각 byte 단위로 동일하다.
- [공식 일관성 제한](https://dev.mysql.com/doc/refman/8.4/en/innodb-information-schema-internal-data.html)은 이 표들의 비일관성을 설명한다. 이 웹 문서에 100 ms 문구가 있다고 쓰지 않고 해당 버전 소스로 근거를 한정했다.

| 버전 | 앞 gap sys SELECT 시작 → 다음 next-key sys SELECT 끝, MONO | 같은 경계 RAW | 해석 |
| --- | ---: | ---: | --- |
| 8.4.11 | 96.071806 ms | 98.590744 ms | 두 cache 읽기 자체를 포함하는 전체 구간도 100 ms 미만 |
| 9.7.2 | 86.605013 ms | 90.105283 ms | 같은 조건 |

첫 sys에는 이전 세션의 gap 행이 있고 다음 sys에는 새 세션의 행이 없다는 관측이 위 cache·join 경로로 설명된다. 내부 cache dump를 보존한 것은 아니므로 내부 transaction 목록까지 직접 측정했다고 주장하지 않는다. next-key locking 규칙 자체를 반박하는 실험으로 출판하지 않는다.

### replication 판정: GTID 완료와 coordinator checkpoint를 혼동

원래 `catch_up`은 이미 source GTID를 고정해 `WAIT_FOR_EXECUTED_GTID_SET(target,8)`의 **반환 0**을 요구한다. 두 버전 모두 성공했고 baseline의 source/replica 실행 집합은 1–4였다. 8.4.11은 worker의 GTID 4 apply 종료 15:45:07.149019, WAIT 종료 .149808, SHOW 시작 .157181 순서였다. 9.7.2도 15:45:49.762093, .763233, .770088 순서였다. timestamp만으로 전체 완료를 추정하지 않고 GTID 대기·집합을 함께 확인했다.

| 단계 | IO/SQL | SBS 8.4.11 / 9.7.2 | Read/Exec, 같은 binlog.000001 | source / replica 실행 GTID 구간 |
| --- | --- | --- | --- | --- |
| baseline | Yes/Yes | 13 / 13 | 1073 / 158 | 1–4 / 1–4 |
| io_stopped | No/Yes | 13 / 13 | 1073 / 158 | 1–5 / 1–4 |
| sql_stopped | Yes/No | NULL / NULL | 1611 / 1342 | 1–6 / 1–5 |
| resumed | Yes/Yes | 0 / **1** | 1611 / 1342 | 1–6 / 1–6 |

IO 중지 표본의 retrieved GTID는 1–4로 적용 집합과 같았다. SQL 중지는 received 1–6·executed 1–5였고, 재개 뒤 WAIT 0·worker 마지막 GTID 6·실행 집합 일치도 확인했다. 사용하지 않은 worker의 빈 GTID·영 timestamp는 누락이나 현재 시각으로 바꾸지 않았다. 각 snapshot 내부 조회도 순차 수행이므로 원자적인 서버 전체 snapshot으로 표현하지 않는다.

[8.4.11 rpl_replica.cc](https://github.com/mysql/mysql-server/blob/mysql-8.4.11/sql/rpl_replica.cc)의 SBS 계산(3584–3625 부근)은 SQL running 상태에서 source read file/pos와 rli group file/pos를 먼저 비교한다. 같을 때 IO connected이면 0, 아니면 NULL이며, 다르면 `max(0, time(nullptr) - last_master_timestamp - clock_diff_with_master)`를 사용한다(last timestamp=0의 0 예외 포함). 병렬 적용의 timestamp는 첫 이벤트 예약과 이후 GAQ 정리 경로(4934–4954 부근), group 위치는 `mta_checkpoint_routine`(6463–6574 부근)에서 갱신된다. [rpl_rli.cc](https://github.com/mysql/mysql-server/blob/mysql-8.4.11/sql/rpl_rli.cc)의 checkpoint 알림·주기 경로와 [9.7.2 rpl_replica.cc](https://github.com/mysql/mysql-server/blob/mysql-9.7.2/sql/rpl_replica.cc)도 대조했다. [SHOW 매뉴얼](https://dev.mysql.com/doc/refman/8.4/en/show-replica-status.html)은 MTS의 Exec_Source_Log_Pos가 최근 commit 위치와 다를 수 있음을 설명한다.

| Claude의 후보 | 판정·범위 |
| --- | --- |
| (a) GTID를 따라잡기 전 baseline | **그 의미로는 반박.** WAIT 0과 1–4 실행 집합·worker 종료가 있다. 다만 coordinator 위치의 수렴까지 기다리지 않은 설계 결함은 수용 |
| (b) 병렬 applier의 표시·checkpoint | **수용.** 두 실행은 기본값에 맡긴 것이 아니라 `--replica-parallel-workers=2`를 명시했다. GTID 완료와 Read/Exec 불일치, SBS의 실제 코드 분기가 일치함 |
| (c) 같은 호스트의 clock_diff | **값 미확인.** 연결 시 remote UNIX_TIMESTAMP와 local time(nullptr)로 계산하므로 같은 호스트라도 초 경계·왕복 동안 0을 보장할 수 없다. 내부 값이 없어 숫자 13의 정확한 산술 분해는 하지 않음 |
| (d) WSL 시계 조정과 인과 | **확정하지 않음.** SBS 계산은 REALTIME 계열 time(nullptr)를 쓰며 MONOTONIC rate를 직접 분모로 쓰지 않는다. NTP 변화 일반 가능성은 매뉴얼에 있지만 이번 WSL 조정이 13을 만들었다는 실험 증거는 없음 |

worker의 last-applied timestamp는 해당 트랜잭션의 완료를 뒷받침하지만 한 worker의 최신값으로 전체 채널 완료를 판정하지 않는다. 이 실습의 고정 target·WAIT 반환·실행 집합은 필터·다른 writer가 없는 소유 인스턴스에서 그 target의 실행 완료를 확인한다. [GTID 함수](https://dev.mysql.com/doc/refman/8.4/en/gtid-functions.html), [worker 표](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-replication-applier-status-by-worker-table.html)

**Claude 요약의 정정:** 9.7.2 resumed SBS는 0이 아닌 1이다. LOCK_MODE는 제시한 네 문자열 외에 gap 실험의 `X,GAP`도 있다. worker 수 2는 엔진 기본값 측정이 아니다. 나머지 baseline·IO/SQL 중지 값과 입력 hash·정리 완료 보고는 원자료와 부합한다.

### 보완 실행기·검증의 범위

[run_mysql_r3_lab.py](../scripts/run_mysql_r3_lab.py)는 `mysql_observation_revision=2`를 기록한다. 자산·runtime manifest·common 모듈은 이번에 바꾸지 않았다. [verify_review_r3.py](../scripts/verify_review_r3.py)는 옛 판정과 새 조건을 구분한다.

- **잠금:** 첫 세 원천 표본을 보존한다. 동일 waiter/blocker로 제한한 sys 행과 INNODB_TRX 진단을 200 ms 간격으로 최대 20회 재시도한다. 이어 직접 engine lock ID 관계를 다시 읽고, blocker rollback 뒤 INSERT의 실제 행 가시성과 waiter rollback도 기록한다. 직접 대기·해제가 확인되어도 sys 표시를 끝내 얻지 못하면 inconclusive이며, 직접 잠금 조건 불일치는 refuted다.
- **복제:** 고정 GTID·WAIT 반환과 원문 참조, 실제 worker/checkpoint 설정을 기록한다. GTID 직후와 IO 중지 직후 표본을 그대로 보존한다. 별도로 유효한 source/group 파일·위치와 thread 상태를 최대 24회·200 ms 간격으로 검사한 뒤 SBS를 판정한다. **SBS가 기대값이 될 때까지 기다리지 않는다.** 위치 조건 미확보는 inconclusive, 위치가 일치한 뒤 규칙 불일치는 refuted다. SQL 중지는 target received 확인도 원문으로 연결한다.
- **회귀 검사:** 실제 r1 잠금·GTID 표본으로 sys 빈 행과 직접 대기를 구분한다. 다른 lock ID·세션·파일 이름, REC_NOT_GAP의 부분 문자열 오인, 위치 0을 거부한다. SBS=13이어도 파일·위치가 같으면 대기 종료하는 합성 반례로 기대값 대기를 막는다. gzip 전체·SQL/XML·NULL 보존·원래 3/2 판정·계산을 검사한다.

새 r2를 실행해야 이 보완의 실제 sys 표시·checkpoint 수렴을 확인할 수 있다. r1을 재해석했다는 이유로 새 결과의 성공을 미리 쓰지 않았다. Windows 검증은 실제 MySQL 재실행을 대신하지 않는다.

### Claude가 실행할 명령 — 새 r2 출력

PowerShell 저장소 루트에서 순서대로 실행한다. 공식 자산과 private runtime은 이미 준비됐으므로 재다운로드·새 symlink 생성은 필요하지 않다. 아래 검사는 기존 자산을 읽고, runner는 소유한 loopback DB 두 개와 native 0700 임시 데이터에만 상태를 쓴다. 운영 DB·시스템 설정·전역 환경은 변경하지 않는다. 결과·raw는 `.lab-runs/`에 저장하며 존재하는 출력은 덮어쓰지 않는다. 이미 r2 이름이 있으면 다른 새 이름을 양쪽 명령에 일치시킨다.

```powershell
python -X utf8 -B scripts/get_review_r3_assets.py --verify-only
wsl -d Ubuntu --cd /mnt/c/project/Domain-Knowledge -- python3 -B scripts/prepare_mysql_r3_runtime.py --verify-only
wsl -d Ubuntu --cd /mnt/c/project/Domain-Knowledge -- python3 -B scripts/run_mysql_r3_lab.py --version 8.4.11 --output .lab-runs/r3/mysql-8.4.11-r2.json
wsl -d Ubuntu --cd /mnt/c/project/Domain-Knowledge -- python3 -B scripts/run_mysql_r3_lab.py --version 9.7.2 --output .lab-runs/r3/mysql-9.7.2-r2.json
python -X utf8 -B scripts/verify_review_r3.py --result .lab-runs/r3/mysql-8.4.11-r2.json --result .lab-runs/r3/mysql-9.7.2-r2.json
python -X utf8 -B scripts/check_html.py
```

자산·runtime 검사는 수초–수십 초, MySQL은 버전별 2–5분·RAM 1–2 GiB 여유를 계획치로 둔다. 이번 r1은 버전별 약 42초였으나 다음 소요 시간 보증은 아니다. 버전별로 직렬 실행해 DB 네 개가 동시에 뜨지 않게 한다. 각 JSON 옆에 같은 이름의 `.raw/`를 남기고 임시 DB는 종료 후 정리한다. 결과 검사에는 보통 수초가 필요하다. HTML 검사는 새 `review/html-check.json`을 기록한다.

### 3e 검증·남은 범위

실행한 Windows 명령은 다음과 같다. 6개 기본 검사를 모두 PASS한 뒤 제출했으며 상세 장 100개·원문 122개의 판 번호는 유지했다.

```powershell
python -X utf8 -B scripts/verify_review_r3.py
python -X utf8 -B scripts/verify_review_r3.py --published
python -X utf8 -B scripts/build_book.py
python -X utf8 -B scripts/build_html.py
python -X utf8 -B scripts/check_docs.py
python -X utf8 -B scripts/verify_examples.py
python -X utf8 -B scripts/verify_contracts.py
python -X utf8 -B scripts/verify_revision.py
python -X utf8 -B scripts/build_book.py --check
python -X utf8 -B scripts/build_html.py --check
```

3d 화면 검사는 Claude의 incoming receipt와 당시 BOOK.html SHA256 `e123f75e1ea5c417b7a1ee9de75dbccf50b22e7f0aaf3f3f49e09059c104441f`가 일치함을 확인하고 [receipt 사본](html-check-r3d-incoming.json)에 남겼다. 새 3e BOOK.html의 화면 PASS라고 쓰지 않았다. Linux r2와 새 HTML 화면 검사는 Claude 후속 실행이다.

남은 미확인은 Lambda suppressed init의 CloudWatch Duration 포함 여부, SBS 내부 clock_diff·13초의 정확한 산술 원인, WSL tick 설정 주체·RAW의 외부 정확도다. 현재 자료만으로 사실처럼 채우지 않는다. 3라운드 마무리에는 위 r2 원자료와 새 화면 결과 대조를 우선한다. 4라운드 후보는 실제 제품 어댑터의 reset·누락·권한·대상 교체 계약 검사, 사용할 DB/OS/런타임의 버전별 수집 스키마, 허용 환경이 있는 상용 DB·GPU·runtime 원천 실측이다. 분야 이름을 늘리기 전에 제품 우선 지원 대상에 맞춰 선정한다.

이하 **3d·3b 절은 당시 이력**이다. 그 안의 실행 대기·준비 hash·명령은 이후 3e 상태를 뜻하지 않는다.

## 3d 범위와 결론 — 2026-10-06

브랜치 `review/claude-codex-r3`, 기존 HEAD `9dfbede`에서 수행했다. 판 번호·book.json.as_of·과거 출판 결과는 유지했고 commit·push·branch 전환은 하지 않았다. Claude의 3c 지적 **24개를 원천에 직접 대조**해 22개 수용·2개 부분 수용으로 반영했다. 독립된 AI 간 검토이며 모든 문장의 무오류 인증은 아니다.

Claude가 2026-10-05 실행한 Linux 메모리·histogram·시계 묶음을 출판했다. WSL·DB·시계 설정 변경은 이번 Codex 턴에 실행하지 않았다. MySQL 8.4.11·9.7.2와 private runtime을 재준비했으며 **Linux loader와 DB 관측은 3e 대기**다. 아래 3b 기록은 당시 이력이다. 거기에 적힌 버전·준비 hash 보존·실행 대기는 이번 3d 이후의 현재 상태를 뜻하지 않는다.

## 출판 근거와 보존 정책

| 최종 출판 JSON | 원본 SHA256 | 판정·원자료 |
| --- | --- | --- |
| [linux-memory](../labs/results/1.1-r3/linux-memory.json) | `7d895a7a30d10181f4a6426d83d78ba3ca4f8306beced0a0e72f814c5ddb3f83` | supported 4, gzip 52개 |
| [histograms](../labs/results/1.1-r3/histograms.json) | `e299135d7b4c93f935ec69db09765062d6598f37c756b4272ba4ea79d64de34d` | supported 2, gzip 6개 |
| [clock-state](../labs/results/1.1-r3/clock-state.json) | `8eca5bf3afb1343a57edfe1e233a706850efa96a5887abcbaeed75615dc114da` | supported 1, gzip 3개 |

세 JSON은 `.lab-runs/r3/` 전달본과 byte 단위로 같다. JSON 총 116,430 B와 **가리키는 모든 gzip 61개 총 40,668 B**를 함께 보존했다. 원자료를 버리고 hash만 출판하지 않았다. 각 sidecar는 상대 경로·압축 전후 크기·SHA256으로 연결하고 검증한다. [증거 정책](../labs/review-r3/evidence-policy.md), [provenance](evidence-provenance.json)

성공한 실행이 참조한 당시 assets.json은 [보존 입력](../labs/archive/review_r3_2026_10_05/assets.json)에 두고 hash `91fc56d5debea87e2a94a2e66a9055552646014404f7d530b8a3e091613eb659`로 연결했다. MySQL 실행기·자산 준비기·검증기의 변경 전 사본도 같은 archive에 보존했다. `.gitattributes`로 archive와 새 출판 묶음의 줄바꿈 변환을 막았다. Linux 메모리·histogram·시계 실행기와 공통 r3 모듈은 변경하지 않았다. 이전 r2의 큰 JSON을 소급 압축·교체하거나 Git 이력을 고치지 않았다.

핵심 관측은 다음과 같으며 세부 해석은 본문에 있다.

- 익명·파일·memfd 각 8 MiB가 해당 PSS 분류에 정확히 반영됐다. anonymous의 statm resident 7,320 × 4 KiB = VmRSS 29,280 KiB, memfd의 shared 4,709 × 4 KiB = RssFile 10,644 + RssShmem 8,192 KiB를 원자료로 대조했다. 30회 읽기 비용의 중앙값도 다시 계산했다. 보편적인 RSS 정확도·고정 조회 비용 보증은 아니다.
- PSI cpu/memory/io는 읽을 수 있었고 irq는 없었다. 기존 cgroup은 읽었으나 하위 생성은 권한 거부였다. vmstat에 pgscan_proactive가 있었고 선택한 계수들은 해당 시점 모두 0이었다. 강제 회수·OOM·호스트 압박은 일으키지 않았다.
- promtool 3.13.4·3.15.0 모두 p25 classic 1.5 / exponential native 1.414213562373095, fraction 0.25 / 0.29248125036057815, count 4를 출력했다. custom bucket native는 classic과 같은 보간값이었다. 합성 분포의 평가이며 서버 scrape·변환·저장 시험은 아니다.
- 2초 구간 MONO 2.000092274초 / RAW 2.076169165초, 비율 약 0.963357이었다. tick 9634, freq −42.8343811035 ppm을 읽었다. `NTPSynchronized=yes`와 timesync-status offset +873.315 ms가 함께 기록됐으므로 동기화 표시를 정확도 허용 범위 통과로 쓰지 않았다. 순차 조회를 동일 시점 snapshot이나 tick 제어 주체의 증거로 쓰지 않는다.

본문 연결: [회수·OOM](../docs/host/reclaim-and-oom.md), [프로세스](../docs/host/processes.md), [PSI](../docs/host/numa-and-pressure.md), [분포](../docs/foundations/histogram-storage.md), [시간](../docs/foundations/time-and-data-quality.md), [실습 안내](../docs/cross-domain/reproducible-labs.md), [검증](../docs/validation.md), [검토](../docs/review.md), [범위·버전](../docs/coverage.md).

## 3c 지적별 판정

아래 ID는 **3c 지적 ID**다. 아래쪽 3b 주제 번호와는 구분한다. 태그로 고정한 코드 또는 공식 문서에서 정의·증가 위치·버전 경계를 확인했으며, 실험하지 않은 동작을 실측으로 표시하지 않았다.

| ID | 판정 | 직접 확인한 원천과 수정 범위 | 바꾼 원고 |
| --- | --- | --- | --- |
| H1 | 수용 | [Linux v6.12 vmscan.c](https://github.com/torvalds/linux/blob/v6.12/mm/vmscan.c): shrink_inactive_list·scan_folios·evict_folios의 cgroup_reclaim 조건, MGLRU isolated 계수. kswapd/direct와 anon/file은 다른 모집단 | [회수·OOM](../docs/host/reclaim-and-oom.md) |
| H2 | 수용 | [v6.12 page_io](https://github.com/torvalds/linux/blob/v6.12/mm/page_io.c)·[zswap](https://github.com/torvalds/linux/blob/v6.12/mm/zswap.c): zero/zswap 경로를 pswpout과 분리. [zram](https://docs.kernel.org/admin-guide/blockdev/zram.html)은 backing block device | [회수·OOM](../docs/host/reclaim-and-oom.md) |
| H3 | 수용 | [v6.13 memcontrol](https://github.com/torvalds/linux/blob/v6.13/mm/memcontrol.c)에서 PSWPIN/OUT, [v6.15](https://github.com/torvalds/linux/blob/v6.15/mm/memcontrol.c)과 [vmscan](https://github.com/torvalds/linux/blob/v6.15/mm/vmscan.c)에서 proactive 분리. 6.12·6.14의 부재와 6.18 raw도 대조 | [회수·OOM](../docs/host/reclaim-and-oom.md) |
| H4 | 수용 | [v6.12 oom_kill.c](https://github.com/torvalds/linux/blob/v6.12/mm/oom_kill.c): dump_header의 current와 __oom_kill_process의 victim. 두 oom_score_adj를 별도 대상 필드로 정의 | [회수·OOM](../docs/host/reclaim-and-oom.md) |
| H5 | 수용 | [현재 NVML utilization 구조체](https://docs.nvidia.com/deploy/nvml-api/latest/api/structnvmlUtilization__t.html)로 링크 교체 | [GPU](../docs/host/gpu.md) |
| H6 | 수용 | [v6.12 proc 점수](https://github.com/torvalds/linux/blob/v6.12/fs/proc/base.c)·[oom 분모](https://github.com/torvalds/linux/blob/v6.12/mm/oom_kill.c): totalram+swap 대 mem_cgroup_get_max. 실제 cgroup 순위로 표시하지 않음 | [회수·OOM](../docs/host/reclaim-and-oom.md) |
| H7 | 수용 | [cgroup v2](https://docs.kernel.org/6.12/admin-guide/cgroup-v2.html): cgroup.pressure는 비계층적, 그 cgroup 자신에게만 적용 | [PSI](../docs/host/numa-and-pressure.md) |
| D1 | 부분 수용 | [8.4 deadlock detection](https://dev.mysql.com/doc/refman/8.4/en/innodb-deadlock-detection.html): 200 트랜잭션·1,000,000 잠금의 탐색 한계 수용. LOCK TABLES는 조건에 따라 감지하므로 일괄 불가 설명은 제외 | [MySQL 운영](../docs/database/mysql-operations.md) |
| D2 | 수용 | [8.4.11](https://dev.mysql.com/doc/relnotes/mysql/8.4/en/news-8-4-11.html)·[9.7.2](https://dev.mysql.com/doc/relnotes/mysql/9.7/en/news-9-7-2.html)는 7월 28일 일반 릴리스. 8.4.12·9.7.3 Docker 전용. 준비 버전과 본문을 수정 | [MySQL 운영](../docs/database/mysql-operations.md), [버전 표](../docs/coverage.md) |
| D3 | 수용 | [data_locks](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-data-locks-table.html)의 정보 생성 비용 범위와 [P_S 권한](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-table-characteristics.html), [세 표의 일관성 한계](https://dev.mysql.com/doc/refman/8.4/en/innodb-information-schema-internal-data.html)를 분리 | [MySQL 운영](../docs/database/mysql-operations.md) |
| D4 | 수용 | [GRANT SERVER의 covering permission 표](https://learn.microsoft.com/en-us/sql/t-sql/statements/grant-server-permissions-transact-sql?view=sql-server-ver17): PERFORMANCE STATE는 SERVER STATE가 imply. 2022+ 최소 권한 대안으로 표현 | [SQL Server·Oracle](../docs/database/sqlserver-oracle.md) |
| D5 | 수용 | [AG DMV](https://learn.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-objects/sys-dm-hadr-database-replica-states-transact-sql?view=sql-server-ver17): redo_rate는 엔진 시작 이후 실제 redo 활동 시간으로 계산한 평균, 현재 구간 벽시계 속도와 구분 | [SQL Server·Oracle](../docs/database/sqlserver-oracle.md) |
| D6 | 수용 | [19c Licensing Information](https://docs.oracle.com/en/database/oracle/oracle-database/19/dblic/Licensing-Information.html)의 spawrio.sql·spawrrac.sql 포함과 [19c RAC의 Statspack](https://docs.oracle.com/en/database/oracle/oracle-database/19/racad/monitoring-performance.html). 10g 외부 기고를 대체 | [SQL Server·Oracle](../docs/database/sqlserver-oracle.md) |
| S1 | 수용 | [Prometheus v3.15 CHANGELOG](https://github.com/prometheus/prometheus/blob/v3.15.0/CHANGELOG.md)의 3.8 stable/optional과 3.9 no-op 단계를 나눔 | [분포 저장](../docs/foundations/histogram-storage.md) |
| S2 | 수용 | [native schema](https://prometheus.io/docs/specs/native_histograms/#schema)의 9–52 downscale MAY, [OTel 변환](https://opentelemetry.io/docs/specs/otel/compatibility/prometheus_and_openmetrics/#exponential-histograms)의 >8 SHOULD/<−4 MUST 및 Development 상태 | [분포 저장](../docs/foundations/histogram-storage.md) |
| S3 | 수용 | [exponential-scale](https://opentelemetry.io/docs/specs/otel/metrics/data-model/#exponential-scale) 직접 링크 추가. 재배치 무오차와 분위수 해상도 손실을 구분 | [분포 저장](../docs/foundations/histogram-storage.md) |
| S4 | 수용 | [chrony news](https://chrony-project.org/news.html)와 [4.9 tracking](https://chrony-project.org/doc/4.9/chronyc.html#tracking): 4.9(2026-08-27)로 범위와 링크 정리 | [시간·품질](../docs/foundations/time-and-data-quality.md) |
| R1 | 수용 | [dotnet-trace collect-linux](https://learn.microsoft.com/en-us/dotnet/core/diagnostics/dotnet-trace#dotnet-trace-collect-linux): 일반 collect와 구분. .NET 10+, root, kernel 6.4+·user_events 등의 조건과 preview 상태 명시 | [managed runtimes](../docs/application/managed-runtimes.md) |
| R2 | 부분 수용 | [5.1.3 릴리스](https://github.com/fluent/fluent-bit/releases/tag/v5.1.3)와 고정 코드로 기준 상향. [4.1.0 input_chunk](https://github.com/fluent/fluent-bit/blob/v4.1.0/src/flb_input_chunk.c)·[Tail](https://github.com/fluent/fluent-bit/blob/v4.1.0/plugins/in_tail/tail_config.c)에 memrb drop·files_rotated가 이미 있음. 세부 비교는 아래 | [로그 pipeline](../docs/product/collection-pipelines.md) |
| R3 | 수용 | [Node v24.19.0](https://github.com/nodejs/node/blob/v24.19.0/doc/api/perf_hooks.md)·[v26.10.0](https://github.com/nodejs/node/blob/v26.10.0/doc/api/perf_hooks.md)에서 samplePerIteration의 24.19/26.5 도입 주석 확인. 비교한 v25.9.0에는 부재 | [async runtimes](../docs/application/async-runtimes.md) |
| R4 | 수용 | [Node v26.10.0 perf_hooks](https://github.com/nodejs/node/blob/v26.10.0/doc/api/perf_hooks.md)로 고정 기준 갱신 | [async runtimes](../docs/application/async-runtimes.md) |
| R5 | 수용 | [dotnet-counters](https://learn.microsoft.com/en-us/dotnet/core/diagnostics/dotnet-counters): System.Runtime의 .NET 8 이하 EventCounters fallback 조건을 추가 | [managed runtimes](../docs/application/managed-runtimes.md) |
| R6 | 수용 | [monitoring endpoint 표와 v2 절](https://docs.fluentbit.io/manual/administration/monitoring), [5.1.3 input](https://github.com/fluent/fluent-bit/blob/v5.1.3/src/flb_input.c)·[storage](https://github.com/fluent/fluent-bit/blob/v5.1.3/src/flb_storage.c): v1/v2 구분, ingestion_paused·storage_overlimit gauge | [로그 pipeline](../docs/product/collection-pipelines.md) |
| R7 | 수용 | HAProxy 3.2·Fluent Bit 5.1.3의 실제 설명 범위를 머리말에도 일치시킴. [HAProxy 3.2 management](https://www.haproxy.org/download/3.2/doc/management.txt) | [프록시](../docs/middleware/proxies-and-mesh.md), [로그 pipeline](../docs/product/collection-pipelines.md) |

### 부분 수용과 추가 확인

**D1:** 1213을 실제 순환의 단독 증거로 쓰지 않는다는 지적은 수용했다. 다만 MySQL 문서는 innodb_table_locks=1·autocommit=0에서 InnoDB가 table lock을 인지하고 MySQL 계층이 row lock을 인지하면 이 범위의 교착을 감지할 수 있다고 설명한다. 이 조건이 성립하지 않거나 다른 엔진의 lock이 섞인 경우 감지 한계와 timeout을 설명했다. LOCK TABLES 자체를 무조건 감지 불가의 원인으로 적지 않았다.

**R2:** v4.1.0의 flb_input.c에 memrb dropped_chunks/bytes 지표 생성, flb_input_chunk.c에 실제 증가가 있다. 같은 태그 tail_config.c에 files_rotated_total도 있다. 반면 long_line_skipped_total은 비교한 4.1.0·4.2.0 코드에서 없고 5.1.3에는 있으므로 “4.2+에 모두 추가”를 쓰지 않았다. 최초 도입 버전을 새로 추정하지 않고 현재 고정 버전의 가용성만 적었다. processor items_drop_total은 4.2.0에 없고 [5.0.0](https://github.com/fluent/fluent-bit/blob/v5.0.0/src/flb_processor.c)에 있다. 5.1.3 프로젝트 공지는 9월 30일, GitHub release published_at은 10월 1일 UTC로 날짜 종류도 분리했다.

**sync_binlog 미확인 해소:** [mysql-8.4.11 sql/binlog.cc](https://github.com/mysql/mysql-server/blob/mysql-8.4.11/sql/binlog.cc)의 sync_binlog_file과 SYNC_STAGE에서 group queue를 받아 sync_counter를 증가·검사하는 위치를 확인했다. N은 개별 트랜잭션 수와 같지 않다는 설명을 유지하고 코드 근거를 붙였다. 전원 차단 지속성 검증은 아니다.

**ptp4l offset 근거 보완:** [LinuxPTP v4.4 tsproc.c](https://github.com/richardcochran/linuxptp/blob/v4.4/tsproc.c)의 tsproc_update_offset(t2−t1−delay), [clock.c](https://github.com/richardcochran/linuxptp/blob/v4.4/clock.c)의 clock_synchronize·UTC 보정·master_offset 출력 경로를 대조했다. hardware timestamp 모드의 PHC offset을 CLOCK_REALTIME offset과 동일시하지 않는다.

**유지한 미확인:** Lambda suppressed init의 REPORT Duration 설명을 CloudWatch Duration 포함의 직접 근거로 쓰지 않았다. 3c에서도 명시적 AWS 문장이 확인되지 않아 미확인 상태를 유지한다. PSI trigger의 오래된 문서와 코드 차이는 3b의 고정 코드 판정을 유지했다.

## MySQL 재준비: 자산·ABI·정리

[자산 manifest](../labs/review-r3/assets.json), [runtime manifest](../labs/review-r3/mysql-runtime.json), [준비 검사 기록](mysql-r3d-preparation.json), [runtime 준비기](../scripts/prepare_mysql_r3_runtime.py), [MySQL 실행기](../scripts/run_mysql_r3_lab.py)에 반영했다. 기존 8.4.10 자산과 hash는 보존하며 실행 선택만 8.4.11·9.7.2로 바꿨다. 8.4.10·9.7.2의 blocked JSON은 존재 이력과 hash만 준비 기록에 남기고 DB 성공 근거로 출판하지 않는다.

| 자산 | 공식 출처·검증 | 고정 SHA256 |
| --- | --- | --- |
| MySQL 8.4.11 minimal Linux AMD64 tar.xz | [CDN tarball](https://cdn.mysql.com/Downloads/MySQL-8.4/mysql-8.4.11-linux-glibc2.28-x86_64-minimal.tar.xz), [detached signature](https://cdn.mysql.com/Downloads/MySQL-8.4/mysql-8.4.11-linux-glibc2.28-x86_64-minimal.tar.xz.asc). 공식 키로 GPG 검증 후 계산한 SHA256 | `383f54e124d5f325d67f0c6912a8f96814eedc761a17ea30112e52fa4cc6b143` |
| 위 .asc | GPG GOODSIG·VALIDSIG, returncode=0 | `3f2627cbdba3e1ed5ab6d82aafc38e3e42f4509649ae5e8ca5036f803dd44d3f` |
| libaio1t64 0.3.113-6build1.1 amd64 | [Ubuntu deb](https://archive.ubuntu.com/ubuntu/pool/main/liba/libaio/libaio1t64_0.3.113-6build1.1_amd64.deb), [noble-updates Packages.xz](https://archive.ubuntu.com/ubuntu/dists/noble-updates/main/binary-amd64/Packages.xz)의 SHA256 | `433212b33e26d424605c01cec1de33b63f2cc12870987b4cb7b3625baba66a19` |
| libnuma1 2.0.18-1ubuntu0.24.04.1 amd64 | [Ubuntu deb](https://archive.ubuntu.com/ubuntu/pool/main/n/numactl/libnuma1_2.0.18-1ubuntu0.24.04.1_amd64.deb), 기존 [PG pin](../labs/postgresql/packages.json) 재사용 | `f333b8edf6f0b705c19f2a67008194df66f7aab0fa2350dc98510569a033ff29` |

MySQL 키는 [공식 2025 키](https://repo.mysql.com/RPM-GPG-KEY-mysql-2025), fingerprint **BCA43417C3B485DD128EC6D4B7B3B788A8D3785C**다. tarball 79,777,440 B의 서명을 검증한 뒤 추출 파일 382개의 hash를 확인했다. tarball SHA256을 공급자가 별도로 게시한 값이라고 표현하지 않는다. libaio의 검증은 **공식 HTTPS Packages index 기반**이며 서명된 InRelease 체인 검증은 수행하지 않았다. 다운로드한 index의 hash·해당 package stanza를 runtime manifest에 보존했다.

**AMD64 ABI 범위:** [Ubuntu의 libaio 배포 소스](https://archive.ubuntu.com/ubuntu/pool/main/liba/libaio/libaio_0.3.113-6build1.1.debian.tar.xz) SHA256 `9e33ca6ce335e41bfccf329110d6d52f823f7b9d1e4d75f7df9b2895c0a55aae`에서 0021 time64 syscall·0022 public 32-bit 함수 patch를 확인했다. 기존 io_getevents/io_pgetevents와 LIBAIO symbol version을 보존하고, 새 public 함수·redirect는 __BITS_PER_LONG==32에 한정한다. [배포판 maintainer 변경 기록](https://tracker.debian.org/news/1509816/accepted-libaio-03113-6-source-into-unstable/)도 확인했다. **amd64 LP64에서 기존 timespec ABI가 유지된다는 소스 기반 판단**이며 i386·x32·모든 아키텍처의 호환성이나 MySQL 공급자의 지원 인증은 아니다.

[MySQL generic 설치 문서](https://dev.mysql.com/doc/refman/8.4/en/binary-installation.html)는 libaio 의존성을 설명한다. Ubuntu 24.04의 symlink 방법은 [공식 bug tracker의 사용자 제보](https://bugs.mysql.com/bug.php?id=119954)에서 확인했지만 공식 매뉴얼의 호환성 보증으로 인용하지 않았다. 최종 loader 동작은 아래 실행의 `mysqld --version`과 `ldd` 원문으로 검증한다.

libaio의 실제 ELF hash는 `9dbba7441fe096f6654bfd31bfdbba52f41a209bd4a560468293c226ff63c998`, libnuma는 `02d7582c5d391e460e56aa67a414360e3183b968206645b9123f9dc7bff5d009`다. 고정 deb의 내용과 대조했고 기존 `.tools/pg18/usr/lib/x86_64-linux-gnu/libnuma.so.1.0.0`도 같은 바이트임을 확인했다. 필요한 두 ELF만 private lib 디렉터리에 복사하며 PG 라이브러리 디렉터리 전체를 mysqld에 노출하지 않는다.

준비기는 hash 검증 후 dpkg-deb tar member를 검사하고 경로 이탈·외부 symlink·중복·장치 파일을 거부한다. private `libaio.so.1 → libaio.so.1t64.0.2`와 upstream alias를 만든다. 전역 환경을 변경하지 않고 **mysqld 자식의 LD_LIBRARY_PATH에만** 새 runtime 경로를 추가한다. 기존 mysql CLI의 자체 private library 경로는 유지한다. Windows에서는 다운로드·archive 내용·ELF hash를 확인했고 Linux alias는 아직 생성하지 않았다.

목적지는 독점 생성하며 기존 완성/불완전 디렉터리를 덮어쓰지 않는다. 준비 실패 시 이번 실행이 소유한 staging·목적지만 정리한다. Windows의 합성 실패 주입으로 최종 검증 실패 뒤 삭제와 기존 sentinel 보존을 확인했다. MySQL 데이터는 기존 native_directory의 소유권·0700·프로세스 종료 우선 정리 규칙을 따른다. 원자료·JSON 출력은 계속 `.lab-runs/`에 제한한다.

LOCK_MODE는 예상 문자열로 변환하지 않고 원래 SQL/XML과 정렬한 관측 문자열 집합을 함께 저장한다. RECORD/TABLE·index·GRANTED/WAITING도 보존한다. 특히 TABLE의 X를 next-key로 해석하지 않는다. 기대한 네 문자열 모두가 해당 query에서 나왔는지는 3e 결과로 판정한다.

## Claude가 실행할 명령 — PowerShell, 저장소 루트

일반 사용자로 순서대로 실행한다. 시스템 설치·sudo·서비스 등록·cloud 호출이 없으며, 기존 결과 파일을 덮어쓰지 않는다. 이미 출력명이 존재하면 **새 이름으로** 실행한다. 아래 WSL 명령은 Codex가 실행하지 않았다. 버전별 실행을 직렬로 두어 두 버전의 DB 인스턴스 네 개가 동시에 뜨지 않게 한다.

```powershell
python -X utf8 -B scripts/get_review_r3_assets.py
python -X utf8 -B scripts/prepare_mysql_r3_runtime.py --download-only
python -X utf8 -B scripts/get_review_r3_assets.py --verify-only
wsl -d Ubuntu --cd /mnt/c/project/Domain-Knowledge -- python3 -B scripts/prepare_mysql_r3_runtime.py
wsl -d Ubuntu --cd /mnt/c/project/Domain-Knowledge -- python3 -B scripts/prepare_mysql_r3_runtime.py --verify-only
wsl -d Ubuntu --cd /mnt/c/project/Domain-Knowledge -- python3 -B scripts/run_mysql_r3_lab.py --version 8.4.11 --output .lab-runs/r3/mysql-8.4.11-r1.json
wsl -d Ubuntu --cd /mnt/c/project/Domain-Knowledge -- python3 -B scripts/run_mysql_r3_lab.py --version 9.7.2 --output .lab-runs/r3/mysql-9.7.2-r1.json
python -X utf8 -B scripts/verify_review_r3.py --result .lab-runs/r3/mysql-8.4.11-r1.json --result .lab-runs/r3/mysql-9.7.2-r1.json
python -X utf8 -B scripts/check_html.py
```

| 단계 | 계획상 시간·메모리, 실측 보증 아님 | 출력·변경 |
| --- | --- | --- |
| 자산 준비·재확인 | cache가 있으면 대체로 수십 초, 없으면 다운로드 시간 추가; 수백 MiB 여유 | `.tools/r3/`·기존 `.tools/pg18-archives/`에 고정 자산, 기존 일치 파일 재사용 |
| private runtime 준비·검사 | 수초–30초, 작은 deb 두 개 | `.tools/r3/mysql-runtime-ubuntu24.04-amd64/`의 ELF·alias·verified.json |
| MySQL 8.4.11 | 2–5분 예상, RAM 1–2 GiB 여유 권장; 실행기 가드는 보이는 여유 1 GiB | `.lab-runs/r3/mysql-8.4.11-r1.json`와 같은 이름의 `.raw/`, native 임시 DB 두 개 정리 |
| MySQL 9.7.2 | 위와 같음, 앞 실행 완료 후 수행 | `.lab-runs/r3/mysql-9.7.2-r1.json`와 `.raw/` |
| 결과 검증 | 수초, 묶음 용량 범위 메모리 | 읽기·복원·hash·SQL NULL·LOCK_MODE·판정 대조 |
| HTML 화면 | 약 1분, Chrome 메모리 별도 | `review/html-check.json`; 시간 초과는 사실 그대로 전달 |

자산·입력 hash를 기록하므로 실행 도중 준비 코드를 수정하지 않는다. 결과 두 JSON과 `.raw/` 전체, preflight/정리 실패가 있으면 그 원문도 전달하면 된다. 이번에 출판한 Linux·histogram·clock 실습을 다시 실행할 필요는 없다.

## 3d 검증과 남은 범위

Windows Python에서 `get_review_r3_assets --verify-only`, `prepare_mysql_r3_runtime --download-only`, `verify_review_r3 --assets`·`--published`를 실행했다. 고정 자산과 추출 hash, package member와 기존 libnuma 비교, gzip 손상·경로 이탈·용량 초과·정리 실패·NULL 구분·ELF 형식의 준비 검사를 통과했다. Linux library 로딩까지 통과했다고 쓰지 않는다.

기본 6개 검사 `check_docs`, `verify_examples`, `verify_contracts`, `verify_revision`, `build_book --check`, `build_html --check`를 모두 통과한 상태로 전달한다. BOOK.md·BOOK.html을 재생성했으며 판 번호는 유지한다. `verify_revision`은 이번 7개 시나리오·61개 원자료를 추가 검사한다. 새 HTML 화면은 Claude가 검사한다. [현재 검증 범위](../docs/validation.md)

현재 판단을 막는 질문은 없다. 3e에서 필요한 것은 새 MySQL 실제 결과이며, 1213 탐색 한계나 ABI 소스 해석을 실제 서버·전원 장애 전체의 보증으로 확장하지 않는다. Lambda Duration의 직접 공식 문장이 확보되기 전까지 미확인을 유지한다.

## 3b 당시 원고 보강 기록 — 아래는 변경 전 단계의 이력

- 확인일: **2026-10-05**. 기준 브랜치 `review/claude-codex-r3`, 기존 출판 HEAD `9dfbede`.
- 단계: Codex의 1차 원천 대조·작성·자체 검토. **Claude의 3c 검토와 3d 실습 결과 반영은 아직 수행하지 않았다.**
- 판 번호·`book.json.as_of`는 유지했다. 새 3장을 더해 상세 본문 100장으로 연결했다.
- 실습 실행기·manifest·`.tools/`·`.lab-runs/`와 기존 출판 결과는 변경하지 않았다. 3a의 `prepared_files_sha256` 16개를 읽기 전용으로 대조해 모두 일치함을 확인했다. 3a의 검증기를 실행하면 임시 실습 자료를 생성하므로 이번 턴에 재실행하지 않았다.
- 새 계산은 원고 전용 `verify_examples.py`에 추가했다. SQL·운영 명령·진단 세션은 실행하지 않았다. commit·push·branch 전환도 하지 않았다.

## 주제별 원천과 반영

| ID | 직접 확인한 주요 1차 원천 | 쓴 위치와 판정 | 쓰지 않은 단서·확장과 이유 |
| --- | --- | --- | --- |
| H1 | Linux v6.12 [vmstat](https://github.com/torvalds/linux/blob/v6.12/mm/vmstat.c), [vmscan](https://github.com/torvalds/linux/blob/v6.12/mm/vmscan.c), [workingset](https://github.com/torvalds/linux/blob/v6.12/mm/workingset.c), [oom_kill](https://github.com/torvalds/linux/blob/v6.12/mm/oom_kill.c), [memcontrol](https://github.com/torvalds/linux/blob/v6.12/mm/memcontrol.c), [cgroup v2](https://docs.kernel.org/6.12/admin-guide/cgroup-v2.html#memory-interface-files) | 새 [회수·OOM 장](../docs/host/reclaim-and-oom.md). 페이지·사건·시간의 단위, scan/steal의 분류 축, memcg/전역 OOM 로그·score·eviction 증거 | allocstall을 시간으로, oom_kill을 전역 메모리 고갈 사건 수로 쓰지 않음. 강제 OOM·압박 실험을 수행했다는 주장 없음 |
| H2 | v6.0·6.1·6.12·6.18 [psi.c](https://github.com/torvalds/linux/blob/v6.12/kernel/sched/psi.c), [Kconfig](https://github.com/torvalds/linux/blob/v6.12/init/Kconfig), [cgroup pressure_write](https://github.com/torvalds/linux/blob/v6.12/kernel/cgroup/cgroup.c), [PSI 문서](https://docs.kernel.org/accounting/psi.html) | [NUMA·압력](../docs/host/numa-and-pressure.md). IRQ upstream 6.1, 설정·runtime 가용성, 시스템 CPU full, trigger 권한·window·fd 수명 | 문서의 오래된 최소 500 ms를 고정 소스의 입력 검증 규칙으로 옮기지 않음. cgroup trigger에 항상 CAP_SYS_RESOURCE가 필수라는 일반화도 코드와 맞지 않음 |
| H3 | [proc 문서](https://docs.kernel.org/6.12/filesystems/proc.html), [status](https://man7.org/linux/man-pages/man5/proc_pid_status.5.html), [statm](https://man7.org/linux/man-pages/man5/proc_pid_statm.5.html), v6.12 [sched.h](https://github.com/torvalds/linux/blob/v6.12/include/linux/sched.h)·[scheduler](https://github.com/torvalds/linux/blob/v6.12/kernel/sched/core.c) | [프로세스](../docs/host/processes.md). RSS 분류·VmSwap 제외 범위·statm 페이지 단위, rollup 비용, TASK_IDLE/TASK_NOLOAD | smaps_rollup을 page walk 없는 공짜 합계로 설명하지 않음. 수집 비용의 고정 배수·실측값은 3d 전이므로 없음 |
| D1 | MySQL [8.4 locking](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking.html)·[9.7 locking](https://dev.mysql.com/doc/refman/9.7/en/innodb-locking.html), 두 버전 InnoDB 변수·sync_binlog·SHOW REPLICA STATUS, [worker](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-replication-applier-status-by-worker-table.html)·[receiver](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-replication-connection-status-table.html) | 새 [MySQL 운영 장](../docs/database/mysql-operations.md), [기초 장](../docs/database/mysql-mariadb.md) 연결. next-key·대기 graph·교착, flush 기본값과 한계, 단계별 timestamp·GTID·NULL | receiver 정지만으로 항상 NULL이라고 쓰지 않음. sync_binlog의 N은 commit group 수. 같은 설정을 확인한 것을 두 계열의 모든 호환성·전원 장애 지속성 보증으로 넓히지 않음 |
| S1 | [OTel ExponentialHistogram](https://opentelemetry.io/docs/specs/otel/metrics/data-model/#exponentialhistogram), [OTLP proto v1.11.1](https://github.com/open-telemetry/opentelemetry-proto/blob/v1.11.1/opentelemetry/proto/metrics/v1/metrics.proto), [Prometheus native 명세](https://prometheus.io/docs/specs/native_histograms/), 3.13.4·3.15.0 config·main.go·functions, [DDSketch 논문](https://arxiv.org/abs/1908.10693)·[저자 구현](https://github.com/DataDog/sketches-py), [t-digest](https://github.com/tdunning/t-digest) | 새 [분포 저장 장](../docs/foundations/histogram-storage.md), [기초 분포](../docs/foundations/distributions.md). scale/schema·zero·index 차이, 보간 계산, 형식 선택 | “3.x 전체가 실험 기능”을 배제. 3.9 이후의 안정 상태와 scrape 기본 false를 구분. downscale의 정확한 재배치가 분위수 정밀도 보존이라는 해석, t-digest의 보편적 상대 오차 보장, collapsing DDSketch의 무조건 보장 제외 |
| C1 | [chrony 4.8 tracking](https://chrony-project.org/doc/4.8/chronyc.html#tracking), [leap 정책](https://chrony-project.org/doc/4.8/chrony.conf.html#leapsecmode), [timedatectl](https://www.freedesktop.org/software/systemd/man/latest/timedatectl.html), [ptp4l](https://www.linuxptp.org/documentation/ptp4l/)·[phc2sys](https://www.linuxptp.org/documentation/phc2sys/) | [시간·품질](../docs/foundations/time-and-data-quality.md). offset·frequency·skew 단위, PHC/시스템 시계, step/slew/smear·A1 연결 | 1라운드 tick 조정 주체와 RAW 외부 정확도는 여전히 확정하지 않음. timesyncd 조회를 모든 동기화 daemon의 API로 쓰지 않음 |
| D2 | Microsoft [version store DMV](https://learn.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-objects/sys-dm-tran-version-store-space-usage?view=sql-server-ver17), [row versioning](https://learn.microsoft.com/en-us/sql/relational-databases/sql-server-transaction-locking-and-row-versioning-guide?view=sql-server-ver16), [ADR](https://learn.microsoft.com/en-us/sql/relational-databases/accelerated-database-recovery-concepts?view=sql-server-ver17), [AG DMV](https://learn.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-objects/sys-dm-hadr-database-replica-states-transact-sql?view=sql-server-ver17) | [SQL Server·Oracle](../docs/database/sqlserver-oracle.md). RCSI/SNAPSHOT·tempdb와 ADR PVS, send/redo KB·freshness, 해당 DMV의 2022 권한 분기 | row version을 무조건 tempdb에 둔다고 설명하지 않음. redo_rate를 항상 벽시계 처리율로 사용하거나 queue/rate를 복구 시간 보증으로 쓰지 않음 |
| D3 | Oracle 19c [Licensing Information](https://docs.oracle.com/en/database/oracle/oracle-database/19/dblic/Licensing-Information.html), [CONTROL_MANAGEMENT_PACK_ACCESS](https://docs.oracle.com/en/database/oracle/oracle-database/19/refrn/CONTROL_MANAGEMENT_PACK_ACCESS.html), [V$SESSION](https://docs.oracle.com/en/database/oracle/oracle-database/19/refrn/V-SESSION.html), [Statspack 소개](https://www.oracle.com/jp/technical-resources/articles/statspack-and-diagnostics-pack.html) | [SQL Server·Oracle](../docs/database/sqlserver-oracle.md). ASH/AWR·예외 DBA_HIST view·활성화와 권리의 차이, 자체 표본·Statspack 대안 | 모든 DBA_HIST view가 무조건 유료라는 단순화는 예외 때문에 채택하지 않음. 사용자의 실제 계약·배포 권리를 추정하지 않음. 자체 V$SESSION 표본을 ASH와 동등하게 설명하지 않음 |
| R1 | JDK 25 MemoryPool·GarbageCollector·BufferPool MXBean과 JFR·jcmd, Microsoft [EventPipe](https://learn.microsoft.com/en-us/dotnet/core/diagnostics/eventpipe)·[dotnet-counters](https://learn.microsoft.com/en-us/dotnet/core/diagnostics/dotnet-counters), [Node v26.9.0 perf_hooks](https://github.com/nodejs/node/blob/v26.9.0/doc/api/perf_hooks.md) | [managed runtimes](../docs/application/managed-runtimes.md), [async runtimes](../docs/application/async-runtimes.md). pool 범위·JFR 이벤트/비용·진단 세션, ELU·26.5의 samplePerIteration | 모든 workload에서 JFR 고정 오버헤드 보장 제외. Node 두 sampling 모드는 API가 직접 비교를 금지하므로 하나의 분포로 연결하지 않음. 진단 세션을 단순 파일 읽기라고 쓰지 않음 |
| L1 | Fluent Bit **4.1** [monitoring](https://github.com/fluent/fluent-bit-docs/blob/4.1/administration/monitoring.md)·[buffering](https://github.com/fluent/fluent-bit-docs/blob/4.1/administration/buffering-and-storage.md), HAProxy **3.2** [management](https://www.haproxy.org/download/3.2/doc/management.txt) | [수집 pipeline](../docs/product/collection-pipelines.md), [프록시](../docs/middleware/proxies-and-mesh.md). record/chunk·retry/drop·fan-out·source 전 손실, stats 행 유형·현재값/누적값 | Fluent Bit를 선택해 구체화했으며 Vector/filelog의 완전한 counter 비교는 수행하지 않음. eresp=5xx, backend+server 합산, drop=0이면 무손실 등의 해석 배제 |
| G1 | DCGM **v4.0.0** [field header](https://github.com/NVIDIA/DCGM/blob/v4.0.0/dcgmlib/dcgm_fields.h), 확인일의 공식 latest profiling·header alias, [Xid](https://docs.nvidia.com/deploy/xid-errors/latest/introduction.html), [nvidia-smi](https://docs.nvidia.com/deploy/nvidia-smi/index.html), [NVML field units](https://docs.nvidia.com/deploy/nvml-api/latest/api/group__nvmlFieldValueEnums.html) | [GPU](../docs/host/gpu.md). field ID·ratio 분모·NVML 차이, Xid·ECC·row remapping·clock reason | 문서의 경험적 activity 임계를 모든 GPU의 경보 기준으로 채택하지 않음. 최신 alias 최초 도입 릴리스는 미확인. nvidia-smi µs와 최신 NVML 시간 필드 ns를 같은 배율로 처리하지 않음 |

각 장의 근처 링크가 개별 문장의 상세 근거다. 변경한 상세 장의 검토 초점·현재 hash는 [chapter-review.json](chapter-review.json)에 기록한다. hash 일치는 검토한 원문을 식별할 뿐 사실을 자동 증명하지 않는다.

## 원천 대조 중 특히 확인한 경계

### PSI의 문서·코드 차이

v6.12와 v6.18 `psi_trigger_create`는 window가 양수이고 10,000,000 µs 이하인지, threshold가 양수이고 window 이하인지 검사한다. fd를 연 자격의 `CAP_SYS_RESOURCE`가 없으면 2,000,000 µs의 배수를 요구한다. cgroup `pressure_write`도 이 함수를 호출한다. 그래서 오래된 문서의 일반 최소 500 ms와 항상 관리자 권한이라는 설명 대신 **고정 코드의 입력 규칙과 파일 쓰기 권한을 분리**해 적었다. 실제 trigger 등록은 하지 않았다.

### MySQL 버전 차이를 확인한 범위

8.4·9.7의 InnoDB 변수 설명과 `Seconds_Behind_Source`의 NULL 조건은 이 장에서 다룬 항목에서 일치한다. 확인된 연결 차이는 `mysql_native_password`가 8.4에서 기본 비활성, 9.0부터 제거된 점이다. 9.7용으로 이 옛 plugin을 다시 켜라고 제안하지 않는다. [공식 인증 plugin 수명](https://dev.mysql.com/doc/refman/8.4/en/native-pluggable-authentication.html)

잠금·복제 실제 결과는 Claude가 실행 중인 8.4.10·9.7.2 자료를 3d에서 확인한다. 그 숫자·오류·NULL 전이를 이 원고 작성 결과로 선인용하지 않는다.

### Native histogram 상태와 계산

3.9.0 CHANGELOG는 native histogram의 실험 상태 해제를 설명한다. changelog의 단수형 flag 표기와 달리 main.go에서 확인한 실제 옛 option은 `native-histograms`이며 no-op이다. 3.13.4·3.15.0 모두 scrape_native_histograms·convert_classic_histograms_to_nhcb·always_scrape_classic_histograms의 기본 false를 확인했다. 형식의 안정 상태와 실제 수집 활성화는 다른 사실이다.

새 표의 p25·fraction 차이는 명시한 synthetic population과 선형/지수 보간식의 독립 계산이다. promtool 출력·서버 scrape 지원·OTel end-to-end 변환 실측으로 설명하지 않는다. 원고 산술 검사는 실행 중인 fixture를 import하거나 변경하지 않는다.

## 2라운드의 미확인 두 건

### Kubernetes hugepage 보정: 코드로 해소

**수용 범위를 확대한다.** v1.37.0 [summary.go](https://github.com/kubernetes/kubernetes/blob/v1.37.0/pkg/kubelet/server/stats/summary.go)의 `summaryProviderImpl.Get`과 `GetCPUAndMemoryStats`는 gate가 활성일 때 `adjustForHugePages`가 반환한 MemoryStats를 node summary에 넣는다. 이 함수는 Node Capacity의 hugepage 자원 합을 AvailableBytes에서 차감하고 하한 0을 적용한다. nil·용량 0이면 기존 값을 유지하며 WorkingSetBytes 자체는 바꾸지 않는다.

따라서 **Summary API `node.memory.availableBytes`에도 이미 반영된다**. 제품에서 같은 hugepage 총용량을 다시 빼지 않는다. 이는 코드 경로 확인이며 hugepage workload를 실행한 관측은 아니다. [반영 본문](../docs/kubernetes/pressure-and-termination.md)

### Lambda suppressed init: 미확인 유지

공식 [실행 환경 문서](https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtime-environment.html)는 suppressed init이 REPORT Duration에 추가될 수 있다고 명시한다. 공식 [지표 문서](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-metrics-types.html)는 Duration에서 cold start를 제외한다고 설명한다. 두 정의를 연결해 **suppressed init이 CloudWatch `AWS/Lambda Duration`에도 포함된다**고 직접 명시한 문장은 확인하지 못했다. REPORT·Telemetry API 관측을 지표로 추론해 확정하지 않으며 기존 미확인을 유지한다. cloud 호출도 수행하지 않았다. [반영 본문](../docs/cloud/managed-and-serverless.md)

## 검증과 후속

- `verify_examples`: 새 15개를 더해 **185개 검사·60개 원문** 통과. 회수 비율·swap 페이지 환산·PSI threshold 단위·base·보간·fraction·DDSketch 경계를 본문 문자열과 대조했다.
- 아래 6개 검사를 모두 실행해 PASS를 확인했다. [검증 기록](../docs/validation.md)에도 범위를 남겼으며 BOOK.md·BOOK.html은 원문 122개로 재생성했다.
- `git diff --check` 통과. 기존 출판 결과·실행기·r2 입력 30개를 HEAD와 byte 단위로 대조해 변경 없음, 3a 준비 hash 16개 일치, branch `review/claude-codex-r3`·HEAD `9dfbede`·판 `1.1`·기준일 `2026-10-04` 유지.
- 새 HTML의 화면 검사는 수행하지 않았다. 이전 화면 기록을 새 생성본 검증으로 취급하지 않는다.
- 3c는 위 코드/문서 차이·버전 조건·표의 단위와 명령 권한을 우선 재검토한다. 3d는 Linux 메모리/PSI·MySQL·native histogram·시계 실습에서 확인된 범위만 결과와 연결한다.
- 추가 실험 후보는 Node 두 sampling 모드 대조, JVM/.NET 진단 비용, Fluent Bit 재시도 소진·파일 회전, GPU별 profiling 가용성이다. 현재 원고만으로 실행 지원을 보증하지 않는다.

| 실행 명령 | 결과 |
| --- | --- |
| `python -X utf8 -B scripts/check_docs.py` | PASS: Markdown 124개·상세 100장·로컬 링크 2,241개·외부 URL 546개 목록화 |
| `python -X utf8 -B scripts/verify_examples.py` | PASS: 산술·해석 185개, 원문 60개 |
| `python -X utf8 -B scripts/verify_contracts.py` | PASS: 어댑터 경계 22개·본문 계산 28개·보존 실습 hash |
| `python -X utf8 -B scripts/verify_revision.py` | PASS: 기존 31개 실행 시나리오·계산 12개·Linux 시계·r2 36개 판정과 hash |
| `python -X utf8 -B scripts/build_book.py --check` | PASS: 원문 122개와 일치 |
| `python -X utf8 -B scripts/build_html.py --check` | PASS: 원문과 고정 renderer 생성 일치 |
