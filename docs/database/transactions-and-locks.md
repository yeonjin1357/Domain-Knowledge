# 트랜잭션, 격리, MVCC와 잠금

> 상태: 검토됨 · 적용 범위: 관계형 DB 공통 개념, PostgreSQL 18과 MySQL 8.4 InnoDB 사례 · 원천 확인일: 2026-10-06 · 실습 여부: 원천·가상 예시 중심; 연결 실습의 범위는 본문

## 먼저 이해할 것

송금에서 한 계좌를 줄이고 다른 계좌를 늘리는 변경은 함께 성공하거나 취소되어야 합니다. transaction은 이런 작업 묶음과 동시 접근의 규칙을 다룹니다. 다른 세션의 변경을 언제 볼 수 있는지, 어떤 작업을 기다려야 하는지는 엔진과 격리 수준에 따라 달라집니다.

DB의 작업 단위에는 연결, 세션, 트랜잭션, 문장이 있습니다. 하나의 연결에서 여러 트랜잭션을 수행할 수 있고 한 트랜잭션에는 여러 문장이 들어갈 수 있습니다. 애플리케이션 요청과도 일대일 대응한다고 가정하면 안 됩니다.

## 트랜잭션의 보장과 범위

트랜잭션은 여러 변경을 하나의 완료 또는 취소 단위로 묶습니다. PostgreSQL에서는 명시적인 블록 외에도 개별 문장이 트랜잭션 안에서 실행되며, 클라이언트 라이브러리가 자동으로 시작·완료를 관리할 수 있습니다. [PostgreSQL Transactions](https://www.postgresql.org/docs/18/tutorial-transactions.html)

ACID를 이해할 때 다음 질문으로 나눠 보는 것이 유용합니다.

| 개념 | 확인할 질문 |
| --- | --- |
| Atomicity, 원자성 | 묶인 변경이 부분 완료로 남는가 |
| Consistency, 일관성 | 정의된 제약과 업무 불변식을 유지하는가 |
| Isolation, 격리성 | 동시에 실행되는 작업이 무엇을 볼 수 있는가 |
| Durability, 지속성 | 커밋된 변경을 어떤 저장·복제 설정과 장애 범위에서 보존하는가 |

DB가 애플리케이션의 모든 업무 규칙을 자동으로 아는 것은 아닙니다. 예를 들어 “재고가 음수가 되면 안 된다”는 규칙은 제약·조건부 갱신·트랜잭션 로직으로 구체화해야 합니다. 지속성의 실패 범위와 설정은 [로그와 복제](replication-and-recovery.md)에서 다룹니다.

## MVCC와 읽기 시점

MVCC는 여러 버전의 데이터를 이용해 읽는 쪽이 자신에게 보이는 상태를 판단하는 방식입니다. PostgreSQL의 기본 Read Committed에서 일반 SELECT는 문장 시작 시점에 커밋된 데이터를 보는 스냅샷을 사용합니다. 따라서 같은 트랜잭션의 두 SELECT가 다른 커밋 상태를 볼 수 있습니다. PostgreSQL의 Read Uncommitted 요청은 Read Committed처럼 처리됩니다. [PostgreSQL Transaction Isolation](https://www.postgresql.org/docs/18/transaction-iso.html)

가상 시간표입니다.

| 순서 | 세션 A | 세션 B | PostgreSQL RR의 A |
| --- | --- | --- | --- |
| 1 | 트랜잭션 시작, 값 10 조회 | | 첫 일반 SELECT의 snapshot에서 10 |
| 2 | | 값을 20으로 변경하고 커밋 | 같은 snapshot 유지 |
| 3 | 같은 값을 다시 조회 | | 다시 10 |

PostgreSQL Read Committed의 일반 SELECT라면 3번에서 20을 볼 수 있습니다. 이를 데이터 손상으로 해석하지 않습니다. Repeatable Read와 Serializable은 관측·충돌 처리 규칙이 다르고, 직렬화 충돌로 트랜잭션 재시도가 필요할 수 있습니다. 이름만 보고 모든 엔진의 세부 동작을 같다고 간주하지 않습니다.

MySQL 8.4 InnoDB의 기본 격리 수준은 Repeatable Read이며 격리 수준에 따라 잠금 전략이 달라집니다. PostgreSQL의 기본값을 MySQL 수집기에 그대로 적용하면 잘못된 설명이 됩니다. [InnoDB Transaction Isolation](https://dev.mysql.com/doc/refman/8.4/en/innodb-transaction-isolation-levels.html)

### 엔진별 읽기 경계를 맞추기

| 엔진·기본 격리 | 일반 SELECT가 보는 시점 | 잠금 읽기에서 주의 |
| --- | --- | --- |
| PostgreSQL 18: READ COMMITTED | 문장 시작 snapshot; RR은 첫 비제어 문장 시점 snapshot | `FOR UPDATE`는 행 잠금을 요구하며 갱신·충돌의 별도 규칙 적용 |
| MySQL 8.4 InnoDB: REPEATABLE READ | 보통 첫 일관 읽기의 snapshot을 이후 일관 읽기에 사용 | `FOR UPDATE`는 일반 일관 읽기와 다른 현재 읽기·잠금 경로 |
| SQL Server: READ COMMITTED | RCSI off는 잠금 기반, on은 문장 snapshot; SNAPSHOT 격리는 transaction snapshot | `SELECT FOR UPDATE` 문법 없음; `UPDLOCK` 등은 별도 T-SQL 규칙 |

`DECLARE CURSOR … FOR UPDATE`는 SQL Server에도 있는 **커서 선언** 절입니다. 위 표의 일반 `SELECT … FOR UPDATE`와 같은 문법·잠금 계약이라는 뜻은 아닙니다. [DECLARE CURSOR](https://learn.microsoft.com/en-us/sql/t-sql/language-elements/declare-cursor-transact-sql?view=sql-server-ver17)

SQL Server의 RCSI 기본값은 배포 제품에 따라 다르므로 DB 설정을 읽습니다. 여기서는 버전 읽기를 **일관 읽기**, 잠금을 요구하는 읽기를 **잠금 읽기**로 부르되 엔진의 격리 수준을 함께 적습니다. [PostgreSQL](https://www.postgresql.org/docs/18/transaction-iso.html), [InnoDB](https://dev.mysql.com/doc/refman/8.4/en/innodb-transaction-isolation-levels.html), [SQL Server 격리·RCSI](https://learn.microsoft.com/en-us/sql/t-sql/statements/set-transaction-isolation-level-transact-sql?view=sql-server-ver17), [UPDLOCK](https://learn.microsoft.com/en-us/sql/t-sql/queries/hints-transact-sql-table?view=sql-server-ver17#updlock)

## 잠금 대기와 교착 상태

PostgreSQL은 테이블·행 등 여러 종류의 잠금을 사용하고, 충돌하는 잠금은 대기를 일으킬 수 있습니다. 교착 상태는 서로의 잠금 해제를 기다리는 순환 관계이며 DB는 이를 감지해 한 트랜잭션을 중단할 수 있습니다. 모든 잠금 대기가 교착 상태는 아닙니다. [PostgreSQL Explicit Locking](https://www.postgresql.org/docs/18/explicit-locking.html)

```mermaid
flowchart LR
    A[트랜잭션 A: 행 X 보유] -->|행 Y를 기다림| B[트랜잭션 B: 행 Y 보유]
    B -->|행 X를 기다림| A
```

반면 A가 X를 보유하고 B만 X를 기다리는 단방향 관계에는 그 사실만으로 순환이 없습니다. 모니터링은 대기자, 차단자, 대상 자원, 대기 시작, 트랜잭션 시작 시각을 연결하는 것이 좋습니다.

## MVCC에서 회수와 freeze까지

```text
① MVCC: 읽는 시점에 필요한 행 버전을 고른다
        ↓ UPDATE·DELETE 뒤 이전 버전이 남을 수 있다
② dead tuple: UPDATE·DELETE로 대체·삭제된 이전 버전이 남는다
        ↓ 아직 필요한 버전을 먼저 구분한다
③ 회수 기준점(xmin horizon): 보존 필요 범위가 회수를 제한한다
        ↓ 행 회수와 별도로 오래된 XID의 가시성을 보호한다
④ freeze 진행점(datfrozenxid): DB의 오래된 미동결 XID 경계를 추적한다
```

이 그림은 학습 순서이며 한 행이 반드시 네 상태를 차례로 거치는 상태 기계는 아닙니다. 살아 있는 행도 오래된 XID를 freeze할 수 있습니다. `n_dead_tup` 감소와 `datfrozenxid` 전진은 서로 다른 결과입니다. [PostgreSQL VACUUM의 목적](https://www.postgresql.org/docs/18/routine-vacuuming.html)

## 오래 열린 트랜잭션의 영향

트랜잭션이 오래 열려 있으면 잠금을 오래 유지하거나 이전 버전의 회수를 늦추는 원인이 될 수 있습니다. PostgreSQL의 행 버전 회수는 어떤 트랜잭션에도 필요하지 않은 버전을 대상으로 하므로 오래 유지되는 관측 시점이 중요합니다. [PostgreSQL Routine Vacuuming](https://www.postgresql.org/docs/18/routine-vacuuming.html)

**dead tuple이라고 해서 지금 모두 제거할 수 있는 것은 아닙니다.** 오래된 snapshot이 아직 볼 수 있는 이전 버전은 회수 기준점 때문에 보존됩니다. PostgreSQL 18.6의 VACUUM 보고도 죽었지만 아직 제거할 수 없는 버전을 구분하며 `n_dead_tup`에는 이 추정량이 포함됩니다. [VACUUM의 recently_dead 계정](https://github.com/postgres/postgres/blob/REL_18_6/src/backend/access/heap/vacuumlazy.c#L941)

일반 세션뿐 아니라 prepared transaction·replication slot·standby feedback도 회수 기준점(xmin horizon)을 붙잡을 수 있습니다. 선수 개념은 [복제와 복구](replication-and-recovery.md), 원천별 범위·NULL·중복 관측은 [PostgreSQL 회수 기준점 표](postgresql-operations.md#회수-기준점을-붙잡는-원천별로-읽기)를 봅니다.

여기서 “현재 실행 중인 쿼리가 짧다”와 “트랜잭션이 짧다”는 다른 주장입니다. 문장 사이에 앱이 외부 호출을 기다리는 동안에도 트랜잭션이 남아 있을 수 있습니다. 제품에서는 문장 시작, 트랜잭션 시작, 세션 생성 시각을 분리하도록 제안합니다.

## 가상 진단

CPU 15%, 쿼리 지연 급증, 차단된 세션 100개라는 사례에서 먼저 차단 관계의 뿌리를 찾습니다. 차단자 한 개가 끝나면 많은 대기가 풀릴 수 있지만, 취소·종료의 업무 영향은 별도 판단입니다. 수집기는 관측을 수행하며 세션 종료를 자동으로 실행하는 규칙을 기본 진단과 혼합하지 않습니다.

## 오류 뒤 연결을 돌려주기 전에

| 엔진·상황 | 트랜잭션 상태 | 수집기·앱 처리 |
| --- | --- | --- |
| PostgreSQL 명시적 transaction 안의 문장 오류 | 실패 상태; 후속 문장은 25P02가 될 수 있음 | ROLLBACK 또는 미리 둔 SAVEPOINT로 복구 후 재사용 |
| MySQL InnoDB 기본 lock timeout / 감지된 deadlock | timeout은 보통 문장만, deadlock은 희생 transaction 롤백 | 오류 종류·`innodb_rollback_on_timeout` 설정을 확인 |
| SQLite 오류 | `SQLITE_FULL`·`IOERR`·`INTERRUPT`·`NOMEM`은 전체 transaction이 자동 롤백될 수도 있음; COMMIT의 `SQLITE_BUSY`는 transaction 유지 | 앞의 오류는 명시적 ROLLBACK으로 상태를 정리하도록 권고됨. COMMIT의 BUSY는 활성 transaction에서 다시 COMMIT할 수 있음 |

모든 오류를 같은 자동 재시도로 처리하지 않습니다. [PostgreSQL SAVEPOINT](https://www.postgresql.org/docs/18/sql-savepoint.html), [MySQL 오류 처리](https://dev.mysql.com/doc/refman/8.4/en/innodb-error-handling.html), [SQLite transaction 오류](https://www.sqlite.org/lang_transaction.html#response_to_errors_within_a_transaction)

실제로 관측하는 방법은 [PostgreSQL 동시성 실습](postgresql-concurrency-lab.md)에 있습니다.

## 이해 확인

1. 같은 트랜잭션이면 두 SELECT가 항상 같은 결과인가? **격리 수준과 엔진에 따라 다릅니다.**
2. 대기자가 많으면 교착 상태인가? **순환 대기 여부가 필요합니다.**
3. 현재 쿼리 나이가 트랜잭션 나이인가? **시작 경계가 다릅니다.**


## 검증 노트

버전 상태: MySQL 사례는 8.4 LTS 문서에 고정했습니다. 9.7 LTS와 이후 YY.M 번호 체계가 존재하며, 새 계열의 모든 동작을 검증한 설명은 아닙니다. 9.7.3은 Docker image 전용 보안 패치입니다. [버전별 기준과 지원 상태](../coverage.md#교차-검토-시점의-버전-상태)

8.4.11·9.7.2의 잠금·복제 로컬 실측 범위는 [MySQL 운영 관측](mysql-operations.md)에 있습니다. 원천 기준 버전과 실제 실행 patch를 구분합니다.

이전: [데이터베이스 도메인](README.md) · 다음: [쿼리, 인덱스, 실행 계획과 비용](queries-and-indexes.md) · [분야 목차](README.md)
