# MySQL과 MariaDB 관측

> 상태: 본문 초안 · 적용 범위: MySQL 8.4 InnoDB·Performance Schema, MariaDB 진단 명령의 차이 · 출처 확인일: 2026-10-03

연결 프로토콜이 비슷하더라도 MySQL과 MariaDB를 하나의 버전 체계로 취급하면 안 됩니다. 원천 지표, 문법, 내부 동작을 엔진별로 확인합니다.

## InnoDB의 동시성

MySQL 8.4 InnoDB의 기본 격리는 Repeatable Read입니다. 일관된 읽기와 잠금을 사용하는 읽기·갱신은 같은 방식으로 해석되지 않으며 격리 수준에 따라 레코드·범위 잠금의 동작이 달라집니다. [InnoDB Isolation Levels](https://dev.mysql.com/doc/refman/8.4/en/innodb-transaction-isolation-levels.html)

따라서 단순히 “읽기 쿼리”라는 분류만으로 잠금 영향이 없다고 판단하지 않습니다. 트랜잭션 경계, 실제 문장 유형, 접근 인덱스와 대기 관계를 함께 관측하는 것이 좋습니다. 공통 개념은 [트랜잭션과 잠금](transactions-and-locks.md)에 설명했습니다.

## Performance Schema의 시간 단위

Performance Schema의 `TIMER_WAIT` 등 노출 시간은 picoseconds 단위로 정규화됩니다. 이것이 실제 하드웨어 타이머가 1 ps의 정확도를 보장한다는 뜻은 아닙니다. `TIMER_START`는 초기화 기준의 경과 값이며 벽시계 Unix timestamp로 해석하지 않습니다. [MySQL Performance Schema Event Timing](https://dev.mysql.com/doc/refman/8.4/en/performance-schema-timing.html)

합성 예입니다.

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

`Seconds_Behind_Source`는 receiver와 applier의 진행을 해석하는 특정 지표입니다. receiver가 원본보다 늦게 받고 있어도 applier가 받은 자료를 따라잡았으면 0이 표시될 수 있습니다. 따라서 0 하나로 원본과 모든 데이터가 동일하다고 판단하지 않습니다. [MySQL SHOW REPLICA STATUS](https://dev.mysql.com/doc/refman/8.4/en/show-replica-status.html)

복제 채널, receiver·applier 상태, 오류, 로그 위치와 필요한 데이터의 적용 여부를 함께 비교합니다. 시간 지표를 바이트 잔량이나 실제 업무 데이터의 신선도와 혼동하지 않습니다.

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

## 이해 확인

1. TIMER_WAIT 1,000,000,000 ps는 몇 ms인가? **1 ms입니다.**
2. digest NULL 행을 지우면 전체 쿼리를 분석한 것인가? **상세 분류되지 않은 실행을 감출 수 있습니다.**
3. 복제 지연 0이면 receiver도 원본과 동일 위치인가? **그 지표만으로 보장하지 못합니다.**

다음: [SQL Server·Oracle](sqlserver-oracle.md) · [DB 목차](README.md)
