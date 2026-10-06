# PostgreSQL 운영 관측: 오래된 ID, 회수 기준점, 통계 호환성

> 상태: 검토됨 · 적용 범위: PostgreSQL 18, 어댑터 비교용 12–17 공식 문서 · 원천 확인일: 2026-10-06 · 실습 여부: 저장된 로컬 실행 근거 포함; 구성·한계는 본문

## 먼저 이해할 상황

선수: [복제 경로·slot](replication-and-recovery.md), [MVCC에서 회수와 freeze까지](transactions-and-locks.md#mvcc에서-회수와-freeze까지).

DB 디스크가 계속 커지는데 “오래 실행 중인 쿼리”는 보이지 않을 수 있습니다. 세션이 끝난 prepared transaction, 사용하지 않는 replication slot, standby가 보내는 피드백도 오래된 행 버전을 보존하게 만들 수 있기 때문입니다. 한편 오래된 transaction ID를 정리하는 freeze는 삭제된 행을 회수하는 일과 목적이 다릅니다. [MVCC와 회수 기준점](transactions-and-locks.md), [PostgreSQL 기본 관측](postgresql.md)을 바탕으로 두 위험을 나눠 봅니다.

## XID와 MultiXact의 나이는 시간이 아니다

PostgreSQL의 행 버전에 쓰이는 일반 XID는 32-bit 공간을 순환합니다. 오래된 XID의 가시성을 잘못 해석하지 않도록 VACUUM은 충분히 오래된 행의 XID를 freeze합니다. `age(datfrozenxid)`는 DB의 freeze 진행점(datfrozenxid)이 현재 XID에서 얼마나 오래됐는지를 **transaction ID 거리**로 표현합니다. 초·일수·완료된 SQL 문장 수가 아닙니다. XID가 필요 없는 작업도 있으므로 요청률과 같다고 가정하지 않습니다. [wraparound와 freezing](https://www.postgresql.org/docs/18/routine-vacuuming.html#VACUUM-FOR-WRAPAROUND)

MultiXact는 여러 transaction이 한 행을 잠글 때 관련 XID 집합을 가리키는 별도 ID입니다. 역시 순환 공간과 구성원 저장소를 관리해야 합니다. `mxid_age(datminmxid)`와 `mxid_age(relminmxid)`를 별도로 수집하며 XID age와 더하지 않습니다. ID 나이만 낮아도 구성원 저장량 위험까지 사라지는 것은 아닙니다. [MultiXact 관리](https://www.postgresql.org/docs/18/routine-vacuuming.html#VACUUM-FOR-MULTIXACT-WRAPAROUND)

| 관측값 | 단위·범위 | 해석 |
| --- | --- | --- |
| `age(pg_database.datfrozenxid)` | DB별 XID 거리 | DB 내 테이블의 오래된 freeze 진행점을 요약 |
| `age(pg_class.relfrozenxid)` | relation별 XID 거리 | 무엇이 DB 기준점을 붙잡는지 세분화 |
| `mxid_age(datminmxid / relminmxid)` | DB/relation별 MultiXact 거리 | XID와 별개 경보 축 |
| `autovacuum_freeze_max_age` | transaction 수 설정 | 테이블의 강제 anti-wraparound vacuum 시작 기준; 즉시 장애 경계 아님 |
| `autovacuum_multixact_freeze_max_age` | MultiXact 수 설정 | MultiXact 정리 기준 |
| `pg_stat_progress_vacuum` | 실행 중 VACUUM의 phase·block·tuple 관련 관측 | 완료율 하나로 모든 phase의 남은 시간을 계산할 수 없음 |

18의 기본 `autovacuum_freeze_max_age`는 2억, MultiXact 대응 설정은 4억입니다. 실제 설정과 테이블 override를 우선 확인합니다. 일반 autovacuum을 끄더라도 wraparound 방지용 작업은 시작될 수 있습니다. 이를 “autovacuum=false이면 안전 작업도 완전히 중지”로 해석하지 않습니다. [vacuum 설정](https://www.postgresql.org/docs/18/runtime-config-vacuum.html), [진행 view](https://www.postgresql.org/docs/18/progress-reporting.html#VACUUM-PROGRESS-REPORTING)

**가상 예시:** XID age가 1억 5000만이고 설정값이 2억이면 설정 기준 비율은 `75%`입니다. 차이는 5000만 XID입니다. 이후에도 초당 1000 XID가 할당되고 freeze 진행점이 전혀 전진하지 않는다는 가정에서 그 설정값까지 `50000초 ≈ 13.89시간`입니다. 이는 위험 추적용 가정 계산이며 wraparound 장애까지 남은 시간의 보장이 아닙니다. freeze 진행·부하 변화·다른 제한으로 결과가 달라집니다.

18에서는 wraparound까지 약 **4000만 XID**가 남으면 경고하고 **300만 미만**이면 새 XID 할당을 거부합니다. 이미 진행 중인 transaction, 새 읽기 전용 transaction, VACUUM의 가능 여부까지 모든 SQL 실패로 뭉뚱그리지 않습니다. `vacuum_failsafe_age` 기본값은 **16억**이며 비용 지연·비필수 작업을 생략하는 최후 수단입니다. autovacuum 시작 기준·failsafe·할당 거부는 서로 다른 경계이고, MultiXact도 별도 기준으로 관리합니다. [실제 경계](https://www.postgresql.org/docs/18/routine-vacuuming.html#VACUUM-FOR-WRAPAROUND), [failsafe와 유효값 보정](https://www.postgresql.org/docs/18/runtime-config-vacuum.html#GUC-VACUUM-FAILSAFE-AGE)

### XID 나이와 남은 거리를 한 축에 놓기

다음은 PostgreSQL 18의 **기본 설정과 wraparound 보호 경계를 설명하는 축**입니다. 가로 간격은 비례하지 않습니다.

```text
오래된 XID의 나이 증가 →
0 ─ 2억 ─ 16억 ─ 약 2^31−4000만 ─ 약 2^31−300만 ─ 약 2^31
    강제 vacuum  failsafe     경고              새 XID 할당 거부   보호할 경계
```

2억과 16억은 설정의 나이 기준, 4000만과 300만은 wraparound까지 **남은 거리**입니다. 설정 변경·유효값 보정·XID 순환 산술과 특수 ID 때문에 이 그림을 정확한 잔여 시간 계산기로 쓰지 않습니다. [18 문서의 경계](https://www.postgresql.org/docs/18/routine-vacuuming.html#VACUUM-FOR-WRAPAROUND), [failsafe 설정](https://www.postgresql.org/docs/18/runtime-config-vacuum.html#GUC-VACUUM-FAILSAFE-AGE), [18.6 SetTransactionIdLimit](https://github.com/postgres/postgres/blob/REL_18_6/src/backend/access/transam/varsup.c)

## 회수 기준점을 붙잡는 원천별로 읽기

**회수 기준점(xmin horizon)**은 아직 누군가 필요로 할 수 있는 오래된 행 버전을 회수하지 못하게 하는 경계입니다. 원천별 ID 나이는 `age()`로, 운영상 경과 시간은 각 원천의 timestamp로 따로 읽습니다. [slot 필드](https://www.postgresql.org/docs/18/view-pg-replication-slots.html), [prepared transaction](https://www.postgresql.org/docs/18/view-pg-prepared-xacts.html), [통계 view](https://www.postgresql.org/docs/18/monitoring-stats.html)

| 원천 | ID 거리 | 시각·보조 증거 | 주의 |
| --- | --- | --- | --- |
| 실행 중 transaction·snapshot | `age(backend_xid)`, `age(backend_xmin)` | `backend_type`, `xact_start`, `state`, wait event | walsender는 아래 복제 관측으로 분리; 오래 열린 시각만으로 같은 xmin 보존을 확정하지 않음 |
| prepared transaction | `age(pg_prepared_xacts.transaction)` | `prepared`, `gid`, 소유자·DB | 원래 세션이 없어도 남음 |
| replication slot | `age(xmin)`, `age(catalog_xmin)` | `active`, `slot_type`, `restart_lsn` | `xmin`과 catalog 전용 기준점은 다름; NULL은 0세 아님 |
| standby feedback (`hot_standby_feedback`) | slot 미사용: `age(pg_stat_replication.backend_xmin)`; slot 사용: 해당 slot의 `age(xmin)`·`age(catalog_xmin)` | sender PID·slot·standby 식별자, standby snapshot | slot 사용 시 walsender의 `backend_xmin`은 NULL일 수 있음 |

**설정 전제:** `hot_standby_feedback`은 피드백을 보내는 **standby에서** 켜며 기본값은 `off`입니다. 켜면 필요한 행 버전의 기준을 primary 또는 upstream standby에 알립니다. 전송 빈도에는 `wal_receiver_status_interval`도 관여합니다. 연결만 존재한다고 feedback이 활성인 것은 아닙니다. [PostgreSQL 18 설정 정의](https://www.postgresql.org/docs/18/runtime-config-replication.html#GUC-HOT-STANDBY-FEEDBACK)

PostgreSQL 18.6의 walsender는 physical slot을 사용하면 feedback 기준점을 slot에 두고 자신의 프로세스 xmin을 비웁니다. slot이 없으면 자신의 xmin에 보존하므로 `pg_stat_replication`과 `pg_stat_activity`의 같은 walsender PID에서 중복 관측할 수 있습니다. `backend_type=walsender`를 별도 분류하고 두 view를 독립 보존 원인으로 더하지 않습니다. NULL인 sender xmin만으로 feedback 부재를 판정하지 않습니다. [18.6 PhysicalReplicationSlotNewXmin·ProcessStandbyHSFeedback](https://github.com/postgres/postgres/blob/REL_18_6/src/backend/replication/walsender.c#L2553)

WAL 보존 위치인 `restart_lsn`은 byte 위치이고 `xmin`은 행 버전 회수 경계입니다. 둘 다 slot에 있어도 같은 지연이 아닙니다. feedback은 standby 쿼리 취소를 줄이는 대신 primary의 회수를 지연시킬 수 있습니다. standby 연결이 끊겼을 때 slot이 어떤 기준점을 유지하는지도 확인해야 합니다. [replication 설정](https://www.postgresql.org/docs/18/runtime-config-replication.html#GUC-HOT-STANDBY-FEEDBACK)

관측은 `n_dead_tup` 추정치, `VACUUM VERBOSE`의 제거 불가 행 수, 관련 horizon ID, 해제 후 회수 결과를 함께 봅니다. `n_dead_tup` 감소와 `datfrozenxid` 전진은 같은 판정이 아닙니다. 다음 표는 **2026-10-05, PostgreSQL 18.6, WSL의 격리된 primary·standby**에서 실행한 저장소 결과입니다. [원시 증거](../../labs/results/1.1-r2-postgresql.json), [실행기](../../scripts/run_postgres_r2_lab.py), [입력 hash 연결](../../review/evidence-provenance.json)

| 시나리오 | 보존 중 증거 | 해제 전 → 후 VACUUM 결과 |
| --- | --- | --- |
| prepared transaction | 세션은 idle, prepared XID `756` 존재 | 제거 불가 128행 → 128행 제거·제거 불가 0 |
| logical slot의 catalog horizon | `xmin=NULL`, `catalog_xmin=759`; `pg_class` 대상 | 제거 불가 24행 → 24행 제거·제거 불가 0 |
| slot 없는 standby feedback (`hot_standby_feedback=on`) | sender `backend_xmin=813`, standby snapshot 유지 | 제거 불가 128행 → snapshot 종료 후 128행 제거 |
| physical slot의 xmin (standby feedback 활성) | 연결 중 slot `xmin=815`, sender xmin NULL; 강제 단절 뒤 inactive slot도 `xmin=815` | 제거 불가 128행 → slot 삭제 후 128행 제거 |

두 standby 시나리오는 standby에 `hot_standby_feedback=on`, `wal_receiver_status_interval='1s'`를 명시했습니다. 이는 실습 설정이며 운영 권장값을 뜻하지 않습니다. [실행기 설정](../../scripts/run_postgres_r2_lab.py)

**이 실행에서는 prepared transaction, logical slot의 catalog_xmin, slot 없는 standby feedback, 단절 뒤 physical slot의 xmin이 각각 행 회수를 붙잡았고, 해당 원천을 해제한 뒤 대상 행이 회수됐습니다.** `n_dead_tup`도 각 대상에서 128 또는 24에서 0으로 변했지만 원래 추정치이므로 일반적인 정확한 행 수 API로 승격하지 않습니다. DB `datfrozenxid`는 모든 표본에서 `744`였고 `postgres`의 age는 각 전후 구간에서 `14→15`, `63→63`, `70→71`, `72→73`이었습니다. 이번 결과는 DB 전체 freeze 진행점의 전진이나 wraparound 방지를 검증한 실험이 아닙니다.

실습은 새 DB 생성, fixture 삽입·삭제, prepared transaction, slot 생성·삭제, VACUUM, 로컬 standby 강제 종료를 수행했습니다. 전용 임시 클러스터의 관리 권한으로만 실행했으며 운영 DB용 수집 SQL이 아닙니다. 성공한 실행은 소유 프로세스와 임시 데이터 디렉터리를 정리했습니다. DrvFs의 mode 제약 때문에 데이터 디렉터리만 Linux native 임시 경로를 사용한 예외와 실패 경로 보완은 [재현 절차](../cross-domain/reproducible-labs.md)에 설명합니다.

## 읽기 전용 수집 SQL과 권한

다음은 **PostgreSQL 18용 미실행 예시**입니다. 대상 DB에 연결할 권한과 각 catalog/view의 읽기 권한이 필요합니다. 전체 세션 정보를 보려면 관리자가 승인한 `pg_read_all_stats` 등의 범위를 확인합니다. DB 상태를 변경하거나 VACUUM을 실행하지 않지만, catalog·통계 조회도 객체·세션 수에 비례한 부하가 있습니다. 하나의 짧은 수집 transaction 또는 autocommit으로 읽고 장기간 transaction을 유지하지 않습니다.

```sql
SELECT statement_timestamp() AS sampled_at, datname,
       age(datfrozenxid) AS xid_age,
       mxid_age(datminmxid) AS multixact_age
FROM pg_database;

SELECT statement_timestamp() AS sampled_at, pid, datname, backend_type, state,
       age(backend_xid) AS backend_xid_age,
       age(backend_xmin) AS backend_xmin_age, xact_start
FROM pg_stat_activity
WHERE backend_type <> 'walsender';

SELECT statement_timestamp() AS sampled_at, gid, database, prepared,
       age(transaction) AS prepared_xid_age
FROM pg_prepared_xacts;

SELECT statement_timestamp() AS sampled_at, slot_name, slot_type, active,
       age(xmin) AS xmin_age, age(catalog_xmin) AS catalog_xmin_age,
       restart_lsn, inactive_since
FROM pg_replication_slots;

SELECT statement_timestamp() AS sampled_at, pid, application_name,
       age(backend_xmin) AS feedback_xmin_age
FROM pg_stat_replication;
```

`statement_timestamp()`는 정확히는 client의 가장 최근 command message를 받은 시각입니다. 여러 SELECT를 하나의 simple Query 메시지로 보내면 같은 값이 나올 수 있습니다. 같은 timestamp가 여러 view의 원자적 snapshot을 보장하지는 않습니다. 위 SQL은 walsender를 activity 목록에서 제외해 복제 목록과의 중복 표시를 피합니다. 사용자 쿼리 본문은 이 예시에 포함하지 않았습니다. `pg_monitor`는 `pg_read_all_settings`, `pg_read_all_stats`, `pg_stat_scan_tables`를 포함하므로 단순 통계 읽기보다 넓습니다. 마지막 역할은 table lock을 수반할 수 있는 진단 함수도 허용합니다. `pg_read_all_stats`가 업무 테이블 전체 SELECT 권한을 주는 것은 아닙니다. [사전 정의 역할](https://www.postgresql.org/docs/18/predefined-roles.html), [시각 함수](https://www.postgresql.org/docs/18/functions-datetime.html)

**NULL은 컬럼마다 권한 경계가 다릅니다.** PostgreSQL 18.6의 `pg_stat_replication.replay_lag` 등 walsender 통계를 읽으려면 superuser 또는 `pg_read_all_stats` 권한이 필요합니다(`pg_monitor`도 포함). 권한이 없을 때의 NULL을 따라잡은 뒤 유휴 상태의 NULL과 구분합니다. 반면 이 view의 `backend_xmin`은 `pg_stat_get_activity()`가 모든 호출자에게 공개하는 필드에서 가져옵니다. “pid 외 모든 열이 NULL”은 `pg_stat_get_wal_senders()`의 제한 분기 설명이지 조인된 view 전체의 규칙이 아닙니다. [18.6 view 정의](https://github.com/postgres/postgres/blob/REL_18_6/src/backend/catalog/system_views.sql#L906), [공개 xmin과 권한 검사](https://github.com/postgres/postgres/blob/REL_18_6/src/backend/utils/adt/pgstatfuncs.c#L361), [walsender 제한](https://github.com/postgres/postgres/blob/REL_18_6/src/backend/replication/walsender.c#L4018)

`pg_stat_activity.state`의 NULL도 권한 제한만 뜻하지 않습니다. 일부 보조 프로세스처럼 내부 상태가 `STATE_UNDEFINED`인 경우에도 NULL을 반환합니다. `backend_type`, 명시적 권한 제한 표시, 수집 역할을 함께 보되 `backend_type` 자체도 가려질 수 있으므로 NULL 하나로 원인을 확정하지 않습니다. [18.6 상태 변환](https://github.com/postgres/postgres/blob/REL_18_6/src/backend/utils/adt/pgstatfuncs.c#L412)

## 통계가 멈춰 보이는 transaction

18의 `stats_fetch_consistency` 기본값은 `cache`입니다. 한 transaction에서 처음 읽은 객체의 누적 통계가 재사용되므로 같은 연결에서 BEGIN 후 계속 조회하면 값이 고정돼 보일 수 있습니다. `snapshot`은 현재 DB에서 접근 가능한 누적 통계들을 함께 캐시하며, `none`은 접근마다 다시 읽습니다. 공식 문서는 한 번씩 읽는 모니터링에 `none`을 적합한 선택으로 설명합니다. [통계 설정](https://www.postgresql.org/docs/18/runtime-config-statistics.html#GUC-STATS-FETCH-CONSISTENCY)

제품 적용 제안은 짧은 수집 transaction과 목적에 맞는 일관성 정책입니다. `none`도 원천 backend의 통계 보고 지연이나 여러 view 사이의 원자성을 해결하지는 않습니다. `pg_stat_clear_snapshot()`은 현재 transaction의 통계 캐시를 버리는 함수이며 서버의 누적 통계 counter를 초기화하는 함수와 다릅니다. 설정 변경·함수 호출 예제는 이번에 실행하지 않았습니다. [누적 통계 시스템](https://www.postgresql.org/docs/18/monitoring-stats.html)

## 어댑터의 버전 분기 표

아래는 **각 major에 맞는 bundled extension 정의**를 기준으로 한 차이입니다. 서버 major만 검사하지 말고 `server_version_num`, 설치된 extension의 `extversion`, 실제 view·컬럼 존재도 확인합니다. 과거 버전의 표는 호환성 설명이며 지원 종료 버전을 새로 배포하라는 권장이 아닙니다.

| 경계 | 확인한 변경 | 수집 설계 |
| --- | --- | --- |
| PostgreSQL 16 | `pg_stat_io` 도입 | 15 이하는 view 부재를 장애·0으로 처리하지 않음. [16 릴리스](https://www.postgresql.org/docs/16/release-16.html) |
| 16–17 → 18 | `read_bytes`, `write_bytes`, `extend_bytes` 추가, `op_bytes` 제거; `object=wal` 등의 WAL I/O 행 추가 | 16–17의 `reads`는 `op_bytes` 크기 블록 수이고 18은 읽기 요청 수. `reads × op_bytes`는 16–17에만 적용하며 18은 `read_bytes` 사용. backend/object/context 차원 보존. [18 릴리스](https://www.postgresql.org/docs/18/release-18.html) |
| 16 → 17 | checkpointer를 별도 view로 분리; `checkpoints_timed/req` → `num_timed/requested`, `checkpoint_write_time/sync_time` → `write_time/sync_time`, `buffers_checkpoint` → `buffers_written` | `buffers_backend`·`buffers_backend_fsync`는 이동이 아니라 제거; 관련 I/O는 `pg_stat_io`로 관측. [17 릴리스](https://www.postgresql.org/docs/17/release-17.html), [17 view](https://www.postgresql.org/docs/17/monitoring-stats.html#MONITORING-PG-STAT-CHECKPOINTER-VIEW) |
| 17 → 18 checkpointer | `num_done`, `slru_written` 추가 | `num_timed`·`num_requested`는 생략된 checkpoint도 셈. 완료 횟수는 `num_done`으로 구분. [18 view](https://www.postgresql.org/docs/18/monitoring-stats.html#MONITORING-PG-STAT-CHECKPOINTER-VIEW) |
| 17 → 18 | `pg_stat_wal`의 `wal_write`, `wal_sync`, `wal_write_time`, `wal_sync_time` 제거 | WAL 생성량 필드와 WAL I/O 시간 필드를 분리하고 후자는 `pg_stat_io` 경로 사용. [18 릴리스](https://www.postgresql.org/docs/18/release-18.html) |
| pg_stat_statements 12 → 13 | 실행 시간 `total_time`을 `total_exec_time`으로 이름 변경; 계획 시간 `total_plan_time`을 새로 선택 수집 | **실행 시간 의미는 직접 매핑**. 계획 시간을 더해 과거 실행 시간과 비교하지 않음. `track_planning` 기본 off일 때 계획 통계는 0. [13 릴리스](https://www.postgresql.org/docs/13/release-13.html), [13 확장 정의](https://www.postgresql.org/docs/13/pgstatstatements.html) |
| 14 | `pg_stat_statements_info.dealloc`·`stats_reset` | 추적 항목 축출과 통계 reset을 함께 수집. [14 정의](https://www.postgresql.org/docs/14/pgstatstatements.html) |
| 16 → 17 | `blk_read_time`/`blk_write_time` → `shared_blk_read_time`/`shared_blk_write_time`; local I/O 시간 분리, `stats_since`, `minmax_stats_since` 추가 | statement 항목의 수명과 min/max 재설정 시각을 구분. [17 정의](https://www.postgresql.org/docs/17/pgstatstatements.html) |
| 16 → 17 progress vacuum | `max_dead_tuples` → `max_dead_tuple_bytes`, `num_dead_tuples` → `num_dead_item_ids`, `dead_tuple_bytes`·`indexes_total`·`indexes_processed` 추가 | 인덱스 수의 진행은 index vacuum/cleanup phase에서 읽음. [17 진행 view](https://www.postgresql.org/docs/17/progress-reporting.html#VACUUM-PROGRESS-REPORTING) |
| 17 → 18 progress vacuum | `delay_time` 추가, ms | `track_cost_delay_timing` 활성 시 비용 지연 sleep 합; 비활성 0을 무대기로 해석하지 않음. [18 진행 view](https://www.postgresql.org/docs/18/progress-reporting.html#VACUUM-PROGRESS-REPORTING) |
| 16 → 17 replication slot | `inactive_since` 추가 | ID age와 비활성 경과 시간을 분리; 동기화 slot의 별도 의미 확인. [17 slot view](https://www.postgresql.org/docs/17/view-pg-replication-slots.html) |

**`pg_stat_io.reads`의 이름이 같아도 17→18에서 같은 계열로 잇지 않습니다.** 16–17은 각 `op_bytes` 크기 블록을 세지만 18의 I/O 요청에는 여러 블록이 합쳐질 수 있습니다. 카탈로그도 16–17의 `pg.io.reads`와 18의 `pg.io.read_requests`를 분리합니다. [16 정의](https://www.postgresql.org/docs/16/monitoring-stats.html#MONITORING-PG-STAT-IO-VIEW), [18 정의](https://www.postgresql.org/docs/18/monitoring-stats.html#MONITORING-PG-STAT-IO-VIEW), [요청 병합과 계정 변경](https://github.com/postgres/postgres/commit/f92c854c)

`pg_stat_checkpointer.num_timed`는 **17에서도 완료·생략된 checkpoint를 모두 셉니다.** 18에 완료 횟수 `num_done` 등이 추가된 것을 기존 `num_timed`의 의미 변경으로 읽지 않습니다. [17 정의](https://www.postgresql.org/docs/17/monitoring-stats.html#MONITORING-PG-STAT-CHECKPOINTER-VIEW)

I/O 시간은 `track_io_timing`·`track_wal_io_timing` 설정을 함께 수집합니다. 비활성화 때문에 0인 시간과 I/O가 없어서 0인 시간을 구분합니다. `dealloc`은 덜 실행된 statement 항목들을 축출한 **횟수**이며 사라진 개별 쿼리 수와 같지 않습니다. 확장 설치·preload 설정·통계 reset은 이 장의 읽기 수집 범위에 포함하지 않습니다. [18 통계 설정](https://www.postgresql.org/docs/18/runtime-config-statistics.html), [18 pg_stat_statements](https://www.postgresql.org/docs/18/pgstatstatements.html)

## 제품 적용 제안과 이해 확인

장기 보존 원인 목록은 세션·prepared·slot·standby를 PID·slot 기준으로 중복 제거해 같은 화면에서 보여 주되 XID age, 경과 시간, WAL byte 지연을 별도 열로 둡니다. 자동으로 slot을 삭제하거나 prepared transaction을 rollback하는 조치는 통계 수집과 분리합니다. 각각 복제·업무 transaction의 의미를 알아야 결정할 수 있습니다.

1. XID age 1억은 1억 초인가? **아니다. transaction ID 공간의 거리다.**
2. 실행 중인 장기 쿼리가 없으면 vacuum 회수 방해 요인도 없는가? **prepared transaction·slot·standby feedback이 남을 수 있다.**
3. `dealloc=10`이면 정확히 쿼리 10개가 사라졌는가? **항목 축출 작업 횟수이며 제거 항목 수와 다르다.**
4. 18에서 `op_bytes`가 없으면 설치 오류인가? **버전 변경이며 byte 컬럼을 사용하는 분기가 필요하다.**

## 함께 읽기

[DB 수집 계약](collection-contracts.md) · [PostgreSQL 실습](postgresql-concurrency-lab.md) · [복제와 복구](replication-and-recovery.md)

이전: [DB 고가용성: 장애 전환, fencing과 복구 완료의 의미](high-availability.md) · 다음: [MySQL: 잠금 대기, 커밋과 복제의 서로 다른 완료 지점](mysql-operations.md) · [분야 목차](README.md)
