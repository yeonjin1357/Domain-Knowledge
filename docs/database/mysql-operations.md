# MySQL: 잠금 대기, 커밋과 복제의 서로 다른 완료 지점

> 상태: 검토됨 · 적용 범위: MySQL 8.4·9.7 InnoDB 공식 문서 · 원천 확인일: 2026-10-06 · 실습 여부: 저장된 로컬 실행 근거 포함; 구성·한계는 본문

## 행 하나를 넣는데 왜 기다릴까

주문 번호가 아직 존재하지 않는데 INSERT가 기다리는 상황을 생각해 봅시다. 다른 트랜잭션이 그 번호가 들어갈 **인덱스 구간**을 잠갔을 수 있습니다. 반대로 커밋 응답이 왔어도 복제본에 적용되었다는 뜻은 아닙니다. 잠금 획득, 로컬 지속성, 복제 수신, 복제 적용은 각각 다른 완료 지점입니다.

## 레코드와 그 사이의 빈 구간을 잠근다

InnoDB의 기본 REPEATABLE READ에서 범위를 검색하는 locking read·UPDATE·DELETE는 일반적으로 next-key lock을 사용합니다. 이는 인덱스 레코드 잠금과 그 **앞 gap**의 잠금을 합친 것입니다. gap lock은 그 구간으로의 삽입을 막습니다. 서로 다른 트랜잭션의 gap lock 자체는 함께 존재할 수 있어, 이름의 S/X만으로 일반 레코드 잠금의 충돌 규칙을 적용하면 안 됩니다. 일반적인 일관 읽기 SELECT와 `SELECT ... FOR UPDATE`도 구분합니다. [8.4 InnoDB locking](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking.html), [9.7 InnoDB locking](https://dev.mysql.com/doc/refman/9.7/en/innodb-locking.html)

완전한 unique index 조건으로 **존재하는 한 레코드**를 찾는 경우에는 gap 없이 레코드만 잠글 수 있습니다. “PK 조건이면 언제나 gap 없음”으로 넓히지 않습니다. 없는 값, 복합 unique key 일부 조건, 실제 사용한 인덱스에 따라 잠금 범위가 달라집니다. **가상 예시:** 인덱스 값이 10과 20이고 `(10, 20]` next-key 구간을 잠갔다면 15 삽입이 기다릴 수 있습니다. 아래 실습에서도 k가 10·20인 보조 인덱스와 15 삽입을 사용했으며, 실제 query·잠금 행은 별도 근거로 보존했습니다. [잠금 범위를 결정하는 검색](https://dev.mysql.com/doc/refman/8.4/en/innodb-locks-set.html)

| 원천 | 무엇을 보여 주는가 | 해석할 때 보존할 것 |
| --- | --- | --- |
| `performance_schema.data_locks` | 엔진이 보유하거나 요청한 잠금 | schema·table·index, RECORD/TABLE, mode, GRANTED/WAITING |
| `performance_schema.data_lock_waits` | 요청 잠금과 이를 막는 잠금 사이의 관계 | requested/blocking 엔진·트랜잭션·잠금 ID |
| `sys.innodb_lock_waits` | 대기 시간·세션 등과 결합한 진단 view | 관측 시각, waiter와 blocker, 오래 열린 트랜잭션 |

잠금 ID는 내부 구조를 파싱할 안정적인 업무 키가 아닙니다. 조회 도중 대기가 끝날 수 있으므로 세 view의 행을 원자적인 전체 그래프로 간주하지 않습니다. 잠금 수는 요청 수나 잠긴 업무 행 수와도 같지 않습니다. [data_locks](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-data-locks-table.html), [data_lock_waits](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-data-lock-waits-table.html), [sys.innodb_lock_waits](https://dev.mysql.com/doc/refman/8.4/en/sys-innodb-lock-waits.html)

8.4.11·9.7.2의 같은 REPEATABLE READ 실습에서 다음 **원래 LOCK_MODE 문자열**을 확인했습니다. `X` 하나만 보고 모든 잠금을 next-key라고 분류하지 않습니다. 아래 해석은 실습용 테이블의 실제 레코드·사용 인덱스·쿼리와 함께 확인한 것입니다. [8.4.11 보완 실행 결과](../../labs/results/1.1-r3/mysql-8.4.11-r2.json), [9.7.2 보완 실행 결과](../../labs/results/1.1-r3/mysql-9.7.2-r2.json), [원천 잠금 정의](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking.html)

| LOCK_TYPE·위치 | 실제 LOCK_MODE·상태 | 이 실습의 의미 |
| --- | --- | --- |
| RECORD, 보조 인덱스 k | `X` · GRANTED | 범위 locking read의 next-key 잠금, k=10·20 레코드에서 관측 |
| RECORD, 보조 인덱스 k | `X,GAP` · GRANTED | k=15가 없는 구간의 gap 잠금 |
| RECORD, PRIMARY | `X,REC_NOT_GAP` · GRANTED | 앞 gap을 포함하지 않는 레코드 잠금 |
| RECORD, 보조 인덱스 k | `X,GAP,INSERT_INTENTION` · WAITING | k=15를 넣으려는 삽입 의도 잠금의 대기 |
| TABLE | `IX` · GRANTED | 행의 배타 잠금을 위한 테이블 수준 intention 잠금 |

제품 적용 제안: 직접 잠금 관계와 sys view의 표시를 별도 상태로 보존합니다. 실제 다음 next-key 표본에는 `data_lock_waits`의 관계가 있었지만 `sys.innodb_lock_waits`는 비어 있었습니다. sys view는 `INNODB_TRX`와 inner join하며, 두 고정 버전의 InnoDB 코드는 마지막 정보 cache 읽기 뒤 **100 ms 초과**가 지나야 갱신을 허용합니다. 연속된 서로 다른 트랜잭션의 표본을 즉시 모두 연결할 수 있다는 보장은 없습니다. 세 표의 비일관성은 공식 문서에도 명시되어 있습니다. [일관성 제한](https://dev.mysql.com/doc/refman/8.4/en/innodb-information-schema-internal-data.html), [8.4.11 sys view](https://github.com/mysql/mysql-server/blob/mysql-8.4.11/scripts/sys_schema/views/p_s/innodb_lock_waits.sql), [8.4.11 cache 코드](https://github.com/mysql/mysql-server/blob/mysql-8.4.11/storage/innobase/trx/trx0i_s.cc), [9.7.2 cache 코드](https://github.com/mysql/mysql-server/blob/mysql-9.7.2/storage/innobase/trx/trx0i_s.cc)

### 교착과 오래 기다리는 것은 다르다

교착은 서로가 놓아야 진행할 수 있는 순환 대기입니다. `innodb_deadlock_detect`의 기본값은 ON입니다. InnoDB가 교착을 발견하면 희생 트랜잭션을 롤백합니다. 반면 `innodb_lock_wait_timeout` 기본 50초는 InnoDB 행 잠금 대기 한도이며, 기본적으로 timeout이 난 **문장**을 롤백합니다. `innodb_rollback_on_timeout`을 켜면 전체 트랜잭션 롤백이 됩니다. 따라서 ERROR 1213과 1205를 동일한 재시도 지점으로 취급하면 안 됩니다. timeout은 모든 쿼리의 실행 제한 시간도 아닙니다. [교착 처리](https://dev.mysql.com/doc/refman/8.4/en/innodb-deadlocks-handling.html), [8.4 InnoDB 변수](https://dev.mysql.com/doc/refman/8.4/en/innodb-parameters.html), [9.7 InnoDB 변수](https://dev.mysql.com/doc/refman/9.7/en/innodb-parameters.html)

ERROR 1213만으로 실제 순환을 확인했다고 표시하지 않습니다. 공식 문서는 wait-for 목록의 200개 트랜잭션 한도 초과나 1,000,000개를 초과하는 잠금 탐색도 교착으로 간주해 롤백한다고 설명합니다. 원문 `LATEST DETECTED DEADLOCK`의 탐색 한도 메시지를 구분합니다. 반대로 InnoDB가 인식하지 못하는 다른 엔진의 잠금이나 MySQL 계층의 테이블 잠금이 포함된 교착은 감지되지 않아 lock timeout으로 끝날 수 있습니다. **LOCK TABLES가 항상 감지 불가인 것은 아닙니다.** `innodb_table_locks=1`과 `autocommit=0` 등의 인식 조건을 확인합니다. [교착 탐색 범위·한도](https://dev.mysql.com/doc/refman/8.4/en/innodb-deadlock-detection.html)

제품 적용 제안: 잠금 대기의 길이, 엔진이 보고한 교착/탐색 한도 사건, 실제 확인한 순환 관계를 구분하고 blocker의 트랜잭션 시작 시각과 마지막 문장을 연결합니다. 잠금 해제를 위한 세션 종료·설정 변경은 읽기 전용 모니터링에 포함하지 않습니다.

## 커밋 응답과 저장 장치의 지속성

redo log는 InnoDB 복구에 쓰이고 binary log는 복제·시점 복구 등에 쓰입니다. 한쪽의 flush 설정만으로 두 경로 모두의 지속성을 설명할 수 없습니다.

| 설정 | 8.4·9.7에서 확인한 의미 |
| --- | --- |
| `innodb_flush_log_at_trx_commit=1` — 기본 | 각 커밋에서 redo를 쓰고 디스크 flush를 요청 |
| `=2` | 커밋마다 redo를 쓰되 flush는 주기적으로 수행 |
| `=0` | redo 쓰기와 flush를 주기적으로 수행 |
| `sync_binlog=1` — 기본 | 커밋 전에 binary log 동기화; group commit의 묶음을 고려 |
| `sync_binlog=0` | MySQL의 binary log 동기화를 끄고 OS 쓰기 반영에 의존 |
| `sync_binlog=N`, N > 1 | N개 binary log **commit group**이 모인 뒤 동기화 |

redo의 주기는 기본 1초이며 `innodb_flush_log_at_timeout` 설정과 스케줄링의 영향을 받습니다. 이를 정확히 매초 수행하거나 최대 1초 손실을 항상 보장하는 타이머로 쓰지 않습니다. OS·장치가 flush를 올바르게 이행하는지도 필요합니다. 두 설정이 1이라는 관측은 설정 증거이며, 전원 장애 복구를 실험한 증거가 아닙니다. [redo flush 설명](https://dev.mysql.com/doc/refman/9.7/en/innodb-parameters.html#sysvar_innodb_flush_log_at_trx_commit), [8.4 sync_binlog](https://dev.mysql.com/doc/refman/8.4/en/replication-options-binary-log.html#sysvar_sync_binlog), [9.7 sync_binlog](https://dev.mysql.com/doc/refman/9.7/en/replication-options-binary-log.html#sysvar_sync_binlog), [저장 쓰기 경로](../storage/write-path-and-durability.md)

`sync_binlog=1`도 group commit을 없애지 않습니다. 개별 트랜잭션마다 독립적인 fsync 한 번이라는 뜻으로 읽지 않습니다. 구현 근거는 장 끝에 두며 이번 실습은 syscall 횟수·전원 장애 지속성을 검증하지 않았습니다.

## 복제의 수신과 적용을 따로 본다

```text
source binary log(binlog)
  → receiver(IO thread): 변경을 받아 relay log에 기록
  → relay log: 복제본의 중계 로그
  → applier(SQL thread): 병렬 구성에서는 coordinator → workers
  → 복제본 데이터에 적용
```

coordinator는 적용 작업을 배정하고 workers는 실제 적용을 수행합니다. `IO/SQL`은 SHOW 상태의 전통적 이름, 본문의 **receiver/applier**는 같은 역할을 가리키는 이름입니다. [MySQL 복제 스레드](https://dev.mysql.com/doc/refman/8.4/en/replication-threads.html)

GTID는 트랜잭션을 식별하고 자동 위치 결정에 사용하는 식별자입니다. 하나의 증가 숫자만으로 모든 source·channel의 순서를 비교하는 시계가 아닙니다. source에서 만들어진 집합, receiver가 받은 집합, 실행된 집합을 구분합니다. 수신 집합에 GTID가 나타난 것만으로 해당 트랜잭션 전체가 수신·커밋되었다고 확정하지 않습니다. [GTID 개념](https://dev.mysql.com/doc/refman/8.4/en/replication-gtids-concepts.html), [SHOW REPLICA STATUS의 GTID 필드](https://dev.mysql.com/doc/refman/9.7/en/show-replica-status.html)

| 단계 | 원천과 주요 필드 | 시간의 의미 |
| --- | --- | --- |
| 수신 | `replication_connection_status`: `SERVICE_STATE`, `LAST_ERROR_*`, `RECEIVED_TRANSACTION_SET` | 채널 연결·수신 진행과 오류 |
| 최근 수신 완료 | 같은 표의 `LAST_QUEUED_TRANSACTION_*` | ORIGINAL/IMMEDIATE_COMMIT_TIMESTAMP, START/END_QUEUE_TIMESTAMP |
| 적용 중·적용 완료 | `replication_applier_status_by_worker`: `APPLYING_TRANSACTION_*`, `LAST_APPLIED_TRANSACTION_*` | ORIGINAL/IMMEDIATE_COMMIT_TIMESTAMP, START_APPLY_TIMESTAMP; 완료 쪽 END_APPLY_TIMESTAMP |

ORIGINAL은 최초 원본에서 커밋한 시각, IMMEDIATE는 바로 위 source에서 커밋한 시각입니다. queue·apply 시각은 replica에서 해당 단계를 처리한 시각입니다. 필드는 microsecond 정밀도의 timestamp이며 Performance Schema의 ps 누적 타이머와 다릅니다. 동일 트랜잭션의 apply 종료−시작은 그 worker의 처리 구간을 나타내지만, 서로 다른 서버의 commit−apply 시각 차이는 시계 오프셋도 포함합니다. 빈 식별자·영 시각·NULL의 의미를 보존하고 유효한 두 시각이 없는 경우 지연을 계산하지 않습니다. [connection status](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-replication-connection-status-table.html), [worker status](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-replication-applier-status-by-worker-table.html)

### Seconds_Behind_Source의 NULL은 0이 아니다

8.4와 9.7 문서는 applier가 멈췄거나, relay log를 모두 소비한 applier에 더 들어올 자료가 없고 receiver도 멈췄으면 `Seconds_Behind_Source`가 NULL이라고 설명합니다. receiver가 실행 중이고 relay log를 모두 소비했으면 0입니다. **병렬 복제에서 목표 GTID의 실행 완료를 이 위치 판정과 동일시하지 않습니다. receiver가 멈췄다는 조건 하나로도 NULL을 보장하지 않습니다.** [8.4 정의](https://dev.mysql.com/doc/refman/8.4/en/show-replica-status.html), [9.7 정의](https://dev.mysql.com/doc/refman/9.7/en/show-replica-status.html)

0이어도 receiver가 느려 원본의 새 자료를 아직 못 받았을 수 있습니다. 병렬 replica에서는 이 값이 최신 worker 하나의 완료 위치를 대표하지 않으며, 시계 차이의 변화도 계산에 영향을 줍니다. 제품에는 원천 값·수신 상태·적용 상태·오류를 함께 보이고, 사용자가 필요한 GTID나 업무 데이터가 적용되었는지는 별도 질문으로 제시합니다.

제품 적용 제안: 자신이 확인하려는 source의 GTID 집합을 먼저 고정하고, replica의 실행 집합 또는 `WAIT_FOR_EXECUTED_GTID_SET`의 반환 0으로 그 집합의 실행 완료를 확인합니다. 이 대기는 운영 수집의 기본 동작으로 넣지 않고 필요할 때 제한 시간과 권한을 정한 진단으로 둡니다. 실습처럼 다른 writer·필터가 없는 소유 인스턴스의 증거 범위를 보존합니다. worker의 마지막 GTID·apply 종료 시각은 해당 작업의 완료를 연결하는 자료이지 모든 worker·모든 트랜잭션의 최신 상태를 대표하는 단일 시계가 아닙니다. `SHOW`와 Performance Schema 조회도 순차 표본입니다. [GTID 대기의 반환값](https://dev.mysql.com/doc/refman/8.4/en/gtid-functions.html), [worker timestamp](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-replication-applier-status-by-worker-table.html)

**GTID 실행 완료와 coordinator 위치 갱신은 별개입니다.** 그래서 목표 GTID가 적용된 직후에도 SBS가 0이 아닌 표본이 있을 수 있습니다. 아래 실습은 GTID·파일 위치·스레드 상태를 함께 비교하며, SBS 계산식의 구현 근거는 검증 노트에 둡니다.

## 읽기 전용 수집과 버전 분기

다음 SQL은 **읽기 전용 수집 예시**입니다. 실습은 이 중 잠금·설정·복제 상태에 해당하는 SQL을 임시 인스턴스에서 실행했으며, 운영 계정의 최소 권한으로 이 예시 전체를 실행 검증한 것은 아닙니다. 필요한 Performance Schema 표에 SELECT 권한이 있어야 합니다. `SHOW REPLICA STATUS`에는 `REPLICATION CLIENT` 또는 문서에 명시된 관리 권한이 필요합니다. `sys.innodb_lock_waits`는 기반 view의 권한도 확인합니다. [Performance Schema 표의 권한](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-table-characteristics.html), [SHOW 권한](https://dev.mysql.com/doc/refman/8.4/en/show-replica-status.html)

data_locks는 이미 엔진에 존재하는 정보를 노출하므로 공식 문서는 그 정보를 **생성하는 추가 메모리·CPU 비용이 없다**고 설명합니다. 전체 행의 조회·전송·제품 측 저장까지 비용이 0이라는 뜻으로 확대하지 않습니다. 조회 비용은 실제 잠금 수·주기에서 측정할 제품 설계 항목으로 두고, SQL·키의 노출 범위도 제한합니다. 조회는 설정·복제 상태를 바꾸지 않습니다. 또한 INNODB_TRX·data_locks·data_lock_waits 사이의 일관성이 보장되지 않으므로 일시적으로 연결할 상대 행이 없어도 parser 오류로 단정하지 않습니다. [data_locks의 비용 범위](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-data-locks-table.html), [표 사이의 일관성 제한](https://dev.mysql.com/doc/refman/8.4/en/innodb-information-schema-internal-data.html)

```sql
SELECT @@version, @@global.innodb_flush_log_at_trx_commit,
       @@global.sync_binlog, @@global.innodb_deadlock_detect,
       @@global.innodb_lock_wait_timeout;
SELECT ENGINE, ENGINE_TRANSACTION_ID, OBJECT_SCHEMA, OBJECT_NAME,
       INDEX_NAME, LOCK_TYPE, LOCK_MODE, LOCK_STATUS
FROM performance_schema.data_locks;
SELECT * FROM performance_schema.data_lock_waits;
SHOW REPLICA STATUS;
```

기본 잠금·flush 설정과 위 NULL 조건은 두 계열 문서에서 일치했습니다. 이것을 모든 호환성의 보증으로 넓히지 않습니다. 실제 차이의 예로 `mysql_native_password`는 8.4에서 기본 비활성화되고 9.0부터 제거되었습니다. 9.7 연결 실패를 8.4의 옛 plugin 활성화 방법으로 고칠 수는 없습니다. [인증 plugin 수명](https://dev.mysql.com/doc/refman/8.4/en/native-pluggable-authentication.html)

제품 적용 제안: 엔진·버전·channel·worker·서버 시계 상태와 기능 가용성을 수집 계약에 남깁니다. 잠금 ID와 GTID·SQL 원문을 무제한 지표 label로 만들지 않고 제한된 진단 자료에 보존합니다.

## 실습: 완료 조건을 맞춘 잠금과 복제 관측

2026-10-06 KST(원문 UTC 10월 5일)에 WSL Ubuntu 24.04·커널 6.18.33.2에서 **8.4.11·9.7.2**를 실행했습니다. 두 버전 모두 `supported 5`이며 버전마다 JSON과 gzip 132개를 출판했습니다. 이는 아래 고정 구성·입력의 판정입니다. [8.4.11 보완 실행](../../labs/results/1.1-r3/mysql-8.4.11-r2.json), [9.7.2 보완 실행](../../labs/results/1.1-r3/mysql-9.7.2-r2.json), [출판·입력 연결](../../review/evidence-provenance.json)

두 버전은 2026-07-28 일반 릴리스 쌍이며 8.4.12·9.7.3은 Docker 전용 패치입니다. 고정 libaio/libnuma를 전용 디렉터리에서 읽고, 소유한 임시 인스턴스 두 개씩만 사용했습니다. 실행 후 프로세스와 native 데이터 디렉터리 정리를 확인했습니다. 최초 라이브러리 부재 시도는 별도 이력이며 시스템 설치·기존 DB 변경은 하지 않았습니다. [8.4.11 릴리스](https://dev.mysql.com/doc/relnotes/mysql/8.4/en/news-8-4-11.html), [9.7.2 릴리스](https://dev.mysql.com/doc/relnotes/mysql/9.7/en/news-9-7-2.html), [8.4.12 범위](https://dev.mysql.com/doc/relnotes/mysql/8.4/en/news-8-4-12.html), [9.7.3 범위](https://dev.mysql.com/doc/relnotes/mysql/9.7/en/news-9-7-3.html), [준비·검토 기록](../../review/claude-codex-r3.md)

| 보완 실행 시나리오 | 두 버전의 판정 | 확인한 범위 |
| --- | --- | --- |
| defaults | supported | redo flush=1, sync_binlog=1; 전원 장애 지속성 시험은 아님 |
| gap_lock | supported | gap 잠금·INSERT 대기·직접 대기 관계·sys 행, blocker rollback 뒤 삽입 행 확인 |
| next_key_lock | supported | next-key·INSERT_INTENTION의 engine lock ID 관계, 같은 세션 쌍의 sys 행, rollback 뒤 삽입 행 확인 |
| deadlock | supported | 구성한 순환에서 ERROR 1213 한 건과 엔진 교착 보고 |
| replication | supported | GTID와 coordinator 위치를 따로 확인한 뒤 수신·적용 중지에 따른 SBS의 NULL/0 구분 |

복제 실행기는 **replica_parallel_workers=2를 명시**했습니다. 위치가 일치한 뒤의 최종 표본은 두 버전이 같습니다. GTID 적용 직후의 SBS 값은 버전별로 함께 적었습니다. `Read/Exec`는 같은 `binlog.000001`의 읽은 위치와 coordinator 실행 위치이며, GTID는 같은 source UUID 뒤 구간만 표시했습니다. SQL 중지 이외의 행은 파일·위치와 thread 상태를 대기 조건으로 삼았으며 **SBS 값은 대기 조건으로 사용하지 않았습니다.**

| 단계 | receiver(IO) / applier(SQL) | Read/Exec | SBS | source / replica 실행 GTID |
| --- | --- | --- | --- | --- |
| GTID 적용 직후 | Yes / Yes | 1073 / 158 | 8.4.11: 12, 9.7.2: 14 | 목표 GTID 실행 완료 |
| 위치 일치 후(baseline) | Yes / Yes | 1073 / 1073 | 0 | 1–4 / 1–4 |
| io_stopped | No / Yes | 1073 / 1073 | NULL | 1–5 / 1–4 |
| sql_stopped | Yes / No | 1611 / 1342 | NULL | 1–6 / 1–5 |
| resumed | Yes / Yes | 1611 / 1611 | 0 | 1–6 / 1–6 |

**두 버전의 보완 실행에서 coordinator 파일·위치가 일치한 뒤 baseline·resumed의 SBS는 0이었고, IO 중지·SQL 중지 표본은 NULL이었습니다.** IO 중지 때 적용한 것은 이미 받은 1–4이며, source의 새 GTID 5까지 적용했다는 뜻은 아닙니다. GTID 집합·스레드 상태·파일 위치와 NULL을 함께 보존해야 이 차이를 알 수 있습니다. [보완 실행의 GTID·SQL 원자료](../../labs/results/1.1-r3/mysql-8.4.11-r2.json), [SHOW의 위치·SBS 정의](https://dev.mysql.com/doc/refman/8.4/en/show-replica-status.html)

### 실제 작업과 표시의 완료 시점은 다르다

보완 실행은 전후 표본을 함께 남겼습니다. 두 버전 모두 next-key의 첫 sys 조회는 0행이었고, 잠금을 유지한 채 200 ms 대기를 포함한 재조회 한 번 뒤 1행이 나타났습니다. **sys view가 비어 있다는 사실만으로 직접 관측한 잠금 대기를 부정할 수 없습니다.** 이는 위 INNODB_TRX cache·join 설명과 부합하며, 모든 환경의 표시 지연이 200 ms라는 보증은 아닙니다. [sys view의 고정 소스](https://github.com/mysql/mysql-server/blob/mysql-8.4.11/scripts/sys_schema/views/p_s/innodb_lock_waits.sql), [cache 갱신 조건](https://github.com/mysql/mysql-server/blob/mysql-8.4.11/storage/innobase/trx/trx0i_s.cc)

보완 실행의 GTID 적용 직후 표본에서는 Read/Exec가 1073/158이었고 SBS는 **8.4.11은 12, 9.7.2는 14**였습니다. 파일·위치 일치 뒤에야 위 표의 0을 관측했습니다. 반대로 재개 직후에는 두 버전 모두 SBS=0인데 위치가 1611/1342인 표본도 있었습니다. **GTID 실행 완료, coordinator 위치 갱신, SBS=0을 서로 같은 완료 조건으로 취급하지 않습니다.** 이 관측을 WSL 시계 조정의 인과나 내부 clock_diff 값의 측정으로 확대하지 않습니다. [8.4.11 보완 실행 전후 표본](../../labs/results/1.1-r3/mysql-8.4.11-r2.json), [9.7.2 보완 실행 전후 표본](../../labs/results/1.1-r3/mysql-9.7.2-r2.json), [SBS·checkpoint 코드](https://github.com/mysql/mysql-server/blob/mysql-8.4.11/sql/rpl_replica.cc)

## 이해 확인

1. 존재하지 않는 키를 INSERT하는데도 기다릴 수 있는가? **인덱스 gap 잠금이 삽입 위치를 막을 수 있습니다.**
2. lock timeout과 deadlock의 롤백 범위가 항상 같은가? **아닙니다. 기본 timeout은 해당 문장, 감지된 InnoDB deadlock은 희생 트랜잭션을 롤백합니다.**
3. sync_binlog=10이면 정확히 트랜잭션 10개마다 동기화하는가? **commit group 수이므로 개별 트랜잭션 수와 같지 않습니다.**
4. Seconds_Behind_Source NULL을 0으로 바꾸어도 되는가? **알 수 없거나 중지된 상태를 정상으로 바꾸므로 안 됩니다.**
5. sys.innodb_lock_waits가 비어 있으면 잠금 대기도 없는가? **아닙니다. 직접 잠금 관계와 INNODB_TRX cache의 표시 시점이 다를 수 있습니다.**
6. 목표 GTID가 모두 실행되면 SBS가 반드시 0인가? **병렬 replica의 coordinator 위치가 아직 갱신되지 않은 표본에서는 0이 아닐 수 있습니다.**

관련: [MySQL·MariaDB 기초](mysql-mariadb.md), [복제와 복구](replication-and-recovery.md), [수집 품질과 시계](../foundations/time-and-data-quality.md)

## 검증 노트

### 커밋 구현 근거

`sync_binlog=1`도 동시 트랜잭션을 묶는 group commit을 없애는 설정은 아닙니다. MySQL 8.4.11의 `ordered_commit`은 SYNC_STAGE에서 모은 큐에 대해 `sync_binlog_file(false)`를 호출하고, 이 함수는 sync 주기가 1이면 그 단계에서 동기화합니다. 따라서 “각 트랜잭션마다 서로 독립적인 fsync 1회”로 바꾸어 읽지 않습니다. 이는 코드 확인이며 이번 실습에서 syscall 횟수나 전원 장애 지속성을 측정한 결과는 아닙니다. [8.4.11 binlog.cc의 SYNC_STAGE·sync_binlog_file](https://github.com/mysql/mysql-server/blob/mysql-8.4.11/sql/binlog.cc)


r1은 **판정 설계 결함으로 반증된 실행**으로 보존했습니다. 두 버전의 `supported 3, refuted 2`를 고치지 않았습니다. next-key 자체와 INSERT 대기·해제는 있었지만 sys view가 즉시 보여야 한다는 조건이 실패했고, 목표 GTID 실행 완료를 coordinator 위치 갱신과 동일시한 조건도 실패했습니다. r1 재개 SBS는 8.4.11에서 0, 9.7.2에서 1이었습니다. [8.4.11 r1](../../labs/results/1.1-r3/mysql-8.4.11-r1.json), [9.7.2 r1](../../labs/results/1.1-r3/mysql-9.7.2-r1.json), [보존 실행기·원인 분석](../../review/claude-codex-r3.md)

8.4.11·9.7.2의 `SHOW REPLICA STATUS` 코드는 SQL thread가 실행 중이면 source의 읽은 파일·위치와 coordinator의 group 파일·위치를 비교합니다. 같을 때 receiver가 연결되어 있으면 0, 멈췄으면 NULL입니다. 위치가 다르면 원칙적으로 `max(0, time(nullptr) − last_master_timestamp − clock_diff_with_master)`를 쓰며, 마지막 timestamp가 0인 경우에는 0을 냅니다. 병렬 worker의 commit과 coordinator checkpoint의 갱신은 별개이므로 **목표 GTID가 적용된 표본에서도 SBS가 0이 아닐 수 있습니다.** [8.4.11 SBS·checkpoint 코드](https://github.com/mysql/mysql-server/blob/mysql-8.4.11/sql/rpl_replica.cc), [9.7.2 같은 경로](https://github.com/mysql/mysql-server/blob/mysql-9.7.2/sql/rpl_replica.cc)

이전: [PostgreSQL 운영 관측: 오래된 ID, 회수 기준점, 통계 호환성](postgresql-operations.md) · 다음: [DB 수집 명세: 읽기 전용 쿼리, 단위, 권한과 통계 수명](collection-contracts.md) · [분야 목차](README.md)
