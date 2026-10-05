# DB 수집 명세: 읽기 전용 쿼리, 단위, 권한과 통계 수명

> 상태: 검토됨 · 적용 범위: PostgreSQL 18·MySQL 8.4의 원천 필드와 수집 설계 · 검토일: 2026-10-04 · PostgreSQL 수집 SQL은 18.6에서 실행, MySQL SQL은 문서 검토

버전 상태: MySQL 사례는 8.4 LTS 문서에 고정했습니다. 9.7 LTS와 이후 YY.M 번호 체계가 존재하며, 새 계열의 모든 동작을 검증한 설명은 아닙니다. 9.7.3은 Docker image 전용 보안 패치입니다. [버전별 기준과 지원 상태](../coverage.md#교차-검토-시점의-버전-상태)

DB 모니터링 쿼리도 DB가 실행하는 작업입니다. 작은 메타데이터 조회라도 빈도·행 수·권한을 관리해야 합니다. 문장 텍스트에 개인정보가 들어갈 수도 있습니다. 이 장의 쿼리는 수집 계약을 검토하기 위한 예시이며 사용자 환경에 적용한 배포 명세가 아닙니다.

## PostgreSQL에서 먼저 확인할 것

접속 대상과 `server_version_num`, DB 이름, 인스턴스 수명, 계정 권한을 기록합니다. 일반 계정으로 다른 세션의 상세를 모두 볼 수 있는 것은 아닙니다. `pg_read_all_stats` 등 역할의 범위를 확인하고 실제 필요한 조회만 허용하는 배포 구성을 정합니다. [누적 통계와 권한](https://www.postgresql.org/docs/18/monitoring-stats.html), [기본 제공 역할](https://www.postgresql.org/docs/18/predefined-roles.html)

다음은 버전과 DB별 누적 통계를 읽는 예시입니다. 읽기 전용 트랜잭션과 statement timeout을 명시했습니다. 2초는 예시 설정이며 모든 환경의 권장값이 아닙니다. 일반 DB 접속 권한이 필요하고, 반환 행 수는 DB 수에 따라 달라집니다.

```sql
BEGIN READ ONLY;
SET LOCAL statement_timeout = '2s';
SELECT current_setting('server_version_num')::integer AS server_version_num;
SELECT clock_timestamp() AS collected_at,
       datid, datname, xact_commit, xact_rollback,
       blks_read, blks_hit, stats_reset
FROM pg_stat_database
WHERE datid <> 0;
COMMIT;
```

`collected_at`은 이 예시에서 **각 행의 표현식을 평가할 때 읽은 시각**입니다. `clock_timestamp()`는 같은 문장 안에서도 달라질 수 있고 실제 결과의 행들에서도 달랐습니다. 한 문장에 공통인 시작 시각이 목적이면 `statement_timestamp()`를 선택합니다. 어느 쪽도 DB 전체의 원자적 수집 완료 시각이라는 뜻은 아닙니다. 이번에는 실행 입력·hash를 유지하고 행별 시각이라는 계약을 명시했습니다. [PostgreSQL 현재 시각 함수](https://www.postgresql.org/docs/18/functions-datetime.html#FUNCTIONS-DATETIME-CURRENT)

위 SQL은 [고정된 입력 파일](../../labs/postgresql/collect-database.sql)로 보존해 PostgreSQL 18.6의 임시 인스턴스에서 실행했습니다. 누적값이 존재해도 `stats_reset`이 NULL인 행이 반환됐습니다. 이 필드를 항상 존재하는 reset 시각으로 가정하지 않습니다. 권한·통계 snapshot·오류 후 연결 상태는 [실제 동시성 실습](postgresql-concurrency-lab.md)에서 설명합니다.

한 transaction 안에서 누적 통계를 계속 조회하면 통계 snapshot 관련 설정에 따라 이전에 본 값이 유지될 수 있습니다. 주기마다 transaction을 끝내고, `stats_fetch_consistency` 등 해당 버전의 동작을 확인합니다. 쿼리가 실패하면 클라이언트에서 rollback과 연결 반환을 보장해야 합니다.

## 필드의 뜻을 변환하기

| 원천 | 유형·단위 | 계산·해석 |
| --- | --- | --- |
| `pg_stat_database.xact_commit` | 누적 transaction 수 | 같은 DB 통계 수명에서 차분/경과초 |
| `xact_rollback` | 누적 rollback 수 | 업무 오류 수와 같지 않음; 명시 rollback도 포함 가능 |
| `blks_hit`, `blks_read` | 블록 접근 누적 수 | DB buffer hit 구분; read가 물리 디스크 직접 읽기를 의미하지 않음 |
| `stats_reset` | 통계 reset 시각 | 차분 연결의 수명 단서 |
| `pg_stat_activity.state` | 상태 | 현재 시점 분류; 누적 count가 아님 |
| `wait_event_type`, `wait_event` | 대기 분류 | active 여부와 독립적으로 해석 |
| `pg_stat_statements.calls` | 누적 실행 수 | queryid 단독 전역 키 금지 |
| `total_exec_time` | 누적 ms | 초로 정규화하거나 차분/calls 차분으로 ms 평균 |

위 필드는 [PostgreSQL 통계](https://www.postgresql.org/docs/18/monitoring-stats.html)와 [pg_stat_statements](https://www.postgresql.org/docs/18/pgstatstatements.html)를 기준으로 합니다. 후자는 확장·설정이 필요합니다. 확장이 없을 때 0 호출률로 대신하지 않습니다.

가상으로 10초에 commit이 120 증가하면 해당 원천 기준 12 transaction/초입니다. 사용자의 주문 수나 SQL 문장 수가 120건이라는 뜻은 아닙니다. 수집기가 발생시키는 transaction도 원천 통계에 영향을 줄 수 있어 이를 고려합니다.

## 차단 관계 조회

`pg_blocking_pids(pid)`는 해당 backend를 차단하는 PID 정보를 제공합니다. 빈번한 호출은 잠금 관리자 공유 상태 접근으로 부담을 줄 수 있으므로 모든 PID를 높은 빈도로 호출하는 기본 정책을 먼저 정하지 않습니다. [시스템 정보 함수](https://www.postgresql.org/docs/18/functions-info.html)

차단 그래프의 노드는 인스턴스·PID·backend 시작 시각과 관측 시각을 함께 가집니다. prepared transaction 등에서 반환되는 특수 값과 병렬 worker 관련 의미는 함수 규약을 보존합니다. 한 번의 조회에 없는 관계를 “해결 완료”로 확정하려면 표본 간 변경과 접근 범위도 고려합니다.

## MySQL 원천 예시

MySQL 8.4에서는 `performance_schema.global_status`를 통해 전역 status variable을 읽을 수 있습니다. 아래 조회는 지원 테이블 조회 권한이 필요한 읽기 예시이며 실제 서버에서는 실행하지 않았습니다. [Status variable tables](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-status-variable-tables.html)

```sql
SELECT VARIABLE_NAME, VARIABLE_VALUE
FROM performance_schema.global_status
WHERE VARIABLE_NAME IN ('Threads_connected', 'Threads_running',
                        'Questions', 'Uptime');
```

`Threads_connected`는 현재 연결 수, `Threads_running`은 잠자지 않는 thread 수이며 CPU에서 실행 중인 thread 수와 동일하지 않습니다. `Questions`의 집계 범위도 모든 내부 문장 실행과 같지 않으므로 수집기에는 원천 정의를 연결합니다. [Server status variables](https://dev.mysql.com/doc/refman/8.4/en/server-status-variables.html)

Performance Schema의 statement summary 시간 값은 ps 단위를 사용합니다. 시간 합 2,500,000,000,000ps와 실행 500이면 평균은 5ms입니다. `COUNT_STAR`, `SUM_TIMER_WAIT`, digest 집계 범위와 통계 초기화·행 수 제한을 함께 다룹니다. [Statement summary tables](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-statement-summary-tables.html)

## 누락과 민감 데이터

권한 부족, 테이블 미지원, 계측 비활성화, SQL timeout, DB 접속 실패를 별도 상태로 남깁니다. 특히 원천이 비활성화된 항목을 0으로 반환할 수 있으면 capability 정보와 함께 해석합니다. SQL 원문·바인드 값·접속 문자열은 수집 목적과 보관 정책을 정하고, 기본 cardinality key로 원문 전체를 사용하지 않도록 제안합니다.

## 이해 확인

1. blks_read 증가를 물리 디스크 읽기 수로 그대로 쓰는가? **OS 캐시 등 다른 층이 있으므로 DB 경계의 블록 읽기로 둡니다.**
2. DB 연결에 성공하면 모든 통계가 보이는가? **필드와 view별 권한이 다릅니다.**
3. SQL 오류 하나가 발생하면 모든 엔진이 전체 transaction을 자동 rollback하는가? **엔진·오류·클라이언트 동작에 따라 다르며 명시 처리해야 합니다. [SQLite 실습](../cross-domain/reproducible-labs.md)이 그 차이를 보여 줍니다.**
