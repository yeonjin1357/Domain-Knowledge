# MySQL과 MariaDB 관측

> 상태: 검토됨 · 적용 범위: MySQL 8.4 InnoDB·Performance Schema, MariaDB 진단 명령의 차이 · 원천 확인일: 2026-10-06 · 실습 여부: 원천·가상 예시 중심; 연결 실습의 범위는 본문

## 먼저 이해할 것

MySQL과 MariaDB는 공통된 배경이 있지만 모든 기능·view·필드가 같은 제품은 아닙니다. 엔진이 실제로 기록한 실행 시간과 문장 수를 확인하고, 계측 설정과 통계 제한을 함께 봅니다. 이름이 비슷한 replication 지연 값도 어떤 진행 단계와 시간을 뜻하는지 구분합니다.

연결 프로토콜이 비슷하더라도 MySQL과 MariaDB를 하나의 버전 체계로 취급하면 안 됩니다. 원천 지표, 문법, 내부 동작을 엔진별로 확인합니다.

## InnoDB의 동시성

개요를 읽은 뒤 next-key·gap·오류 뒤 롤백 범위는 [MySQL 잠금 정본](mysql-operations.md#레코드와-그-사이의-빈-구간을-잠근다)으로 이어집니다.

MySQL 8.4 InnoDB의 기본 격리는 Repeatable Read입니다. 일관된 읽기와 잠금을 사용하는 읽기·갱신은 같은 방식으로 해석되지 않으며 격리 수준에 따라 레코드·범위 잠금의 동작이 달라집니다. [InnoDB Isolation Levels](https://dev.mysql.com/doc/refman/8.4/en/innodb-transaction-isolation-levels.html)

따라서 단순히 “읽기 쿼리”라는 분류만으로 잠금 영향이 없다고 판단하지 않습니다. 트랜잭션 경계, 실제 문장 유형, 접근 인덱스와 대기 관계를 함께 관측하는 것이 좋습니다. 공통 개념은 [트랜잭션과 잠금](transactions-and-locks.md)에 설명했습니다.

## Performance Schema의 시간 단위

Performance Schema의 `TIMER_WAIT` 등 노출 시간은 picoseconds 단위로 정규화됩니다. 이것이 실제 하드웨어 타이머가 1 ps의 정확도를 보장한다는 뜻은 아닙니다. `TIMER_START`는 초기화 기준의 경과 값이며 벽시계 Unix timestamp로 해석하지 않습니다. [MySQL Performance Schema Event Timing](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-timing.html)

가상 예시입니다.

```text
구간 SUM_TIMER_WAIT 증가 = 2,500,000,000,000 ps = 2.5 s
구간 COUNT_STAR 증가 = 500
구간 평균 = 2.5 s / 500 = 0.005 s = 5 ms
```

ps를 ns로 오해하면 1,000배의 오류가 생깁니다. 제품의 공통 저장 단위로 변환할 때 원천 단위와 변환식을 명세에 남깁니다.

## 문장 digest와 집계 누락

문장 요약은 digest와 schema 등 집계 차원에 따라 통계를 모읍니다. digest 요약 테이블이 가득 차면 `DIGEST = NULL` 행이 다른 행에 들어가지 못한 문장들을 함께 집계할 수 있습니다. 이 행의 비중은 상세 분류의 포괄 범위를 판단하는 단서입니다. [MySQL Statement Summary Tables](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-statement-summary-tables.html)

가상으로 전체 실행 100,000건 중 이 기타 집계에 40,000건이 있다면 상세 digest별 순위는 전체의 60%만 구분한 것입니다. 화면에서 나머지를 “쿼리 없음”으로 처리하면 안 됩니다. 수집·추적 설정, 테이블 크기와 초기화도 함께 확인하도록 제안합니다.

## 복제 지연 0의 한계

`Seconds_Behind_Source`는 원본 데이터 전체의 신선도 인증이 아닙니다. NULL·0, receiver/applier·GTID·위치를 함께 읽는 계약과 저장 실측은 [MySQL 운영 관측](mysql-operations.md#seconds_behind_source의-null은-0이-아니다)에 모았습니다. MariaDB에는 엔진별 규약을 별도로 적용합니다.

## MariaDB의 진단 명령

MariaDB의 `EXPLAIN`은 계획 정보를 제공하고 `ANALYZE`는 문장을 실제 실행하여 실행 통계를 얻습니다. `SHOW EXPLAIN FOR`는 다른 연결에서 현재 실행 중인 문장의 계획을 확인하는 기능입니다. MySQL용 명령 문자열을 그대로 복사하지 말고 엔진과 버전을 분기합니다. [MariaDB EXPLAIN](https://mariadb.com/docs/server/reference/sql-statements/administrative-sql-statements/analyze-and-explain-statements/explain), [MariaDB SHOW EXPLAIN](https://mariadb.com/docs/server/reference/sql-statements/administrative-sql-statements/show/show-explain)

이 문서는 개념을 설명하며 대상 DB에 ANALYZE나 통계 초기화 명령을 실행하지 않았습니다. 정기 수집은 문장을 재실행하는 진단과 분리하도록 제안합니다.

## 제품 어댑터 명세 제안

| 항목 | 명세할 내용 |
| --- | --- |
| 엔진 | MySQL/MariaDB와 정확한 버전 |
| 스토리지 엔진 | InnoDB 등 적용 범위 |
| 관측 기능 | Performance Schema와 필요한 instrument·consumer |
| 누적 수명 | 서버 시작, 명시 초기화, 항목 교체 |
| 권한 | 자신의 세션과 다른 세션의 가시성 |
| 시간 | ps 등 원천 단위와 초 변환 |
| 쿼리 | 원문·정규화 형태·매개변수 수집 정책 |

**MySQL 8.4 digest 통계의 수명:** `events_statements_summary_by_digest`의 행 키는 `(SCHEMA_NAME, DIGEST)`입니다. 표가 가득 차서 새 digest를 담지 못하면 `DIGEST=NULL`인 catch-all 행에 합산하므로 이를 실제 쿼리 digest 하나로 표시하지 않습니다. `FIRST_SEEN`은 행 생성 시각의 보조 표식이고, `TRUNCATE`는 이 표의 행을 삭제합니다. reset을 직접 실행하는 수집은 제안하지 않습니다. [Statement summary 정의](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-statement-summary-tables.html)

## 이해 확인

1. TIMER_WAIT 1,000,000,000 ps는 몇 ms인가? **1 ms입니다.**
2. digest NULL 행을 지우면 전체 쿼리를 분석한 것인가? **상세 분류되지 않은 실행을 감출 수 있습니다.**
3. 복제 지연 0이면 receiver도 원본과 동일 위치인가? **그 지표만으로 보장하지 못합니다.**


## 검증 노트

버전 상태: MySQL 사례는 8.4 LTS 문서에 고정했습니다. 9.7 LTS와 이후 YY.M 번호 체계가 존재하며, 새 계열의 모든 동작을 검증한 설명은 아닙니다. 9.7.3은 Docker image 전용 보안 패치입니다. [버전별 기준과 지원 상태](../coverage.md#교차-검토-시점의-버전-상태)

8.4.11·9.7.2의 잠금·복제 로컬 실측 범위는 [MySQL 운영 관측](mysql-operations.md)에 있습니다. 원천 기준 버전과 실제 실행 patch를 구분합니다.

이전: [PostgreSQL 관측: 활동, 누적 통계와 정리 작업](postgresql.md) · 다음: [SQL Server와 Oracle: 대기와 실행 통계](sqlserver-oracle.md) · [분야 목차](README.md)
