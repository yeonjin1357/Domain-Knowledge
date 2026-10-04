# PostgreSQL 관측: 활동, 누적 통계와 정리 작업

> 상태: 검토됨 · 적용 범위: PostgreSQL 18 · 출처 확인일: 2026-10-03 · 편집 검토일: 2026-10-04

## 먼저 이해할 것

PostgreSQL에서는 지금 무엇을 기다리는지 보여 주는 활동 정보와 과거부터 누적한 통계가 서로 다릅니다. 한 시점에 연결 100개가 보였다는 사실로 최근 1분 동안 쿼리 100개가 실행되었다고 계산할 수 없습니다. 상태·누적량·통계가 시작된 시각을 함께 이해해야 합니다.

PostgreSQL 수집은 현재 활동과 누적 통계를 구분하는 것에서 시작합니다. 시점의 세션 수와 시작 이후 누적 실행 수를 같은 유형으로 저장하면 안 됩니다.

## 관측 원천

`pg_stat_activity`의 state와 wait event는 별개 정보입니다. active인 세션도 대기할 수 있습니다. 누적 통계는 즉시 완전히 동기화되는 값만 있는 것이 아니며 설정·트랜잭션 내 조회 방식·권한에 따라 보이는 자료가 달라집니다. [PostgreSQL Cumulative Statistics](https://www.postgresql.org/docs/18/monitoring-stats.html)

| 조사 목적 | 원천 예 | 함께 해석할 내용 |
| --- | --- | --- |
| 현재 작업과 대기 | pg_stat_activity | 세션·문장·트랜잭션의 시작 시점 |
| 쿼리별 누적 비용 | pg_stat_statements | 호출 수, 실행 시간, 통계 수명 |
| 테이블 정리 | vacuum 관련 통계·로그 | 변경률, 오래 열린 트랜잭션 |
| 로그와 복제 | WAL·복제 상태 | 생성·전송·적용 경계 |

표는 목적별 연결 안내입니다. 실제 수집 쿼리는 해당 버전의 컬럼과 조회 권한을 확인해 구성합니다.

## pg_stat_statements의 단위와 그룹

이 확장은 SQL 계획·실행 통계를 집계합니다. `calls`는 실행 수, `total_exec_time`은 누적 실행 시간이며 ms 단위입니다. 추적 설정이 필요한 계획·I/O 시간 항목은 수집이 꺼져 있으면 0일 수 있습니다. 문장은 사용자·DB·queryid 등의 집계 기준으로 구분되므로 queryid만 전역 키로 사용하지 않습니다. [PostgreSQL pg_stat_statements](https://www.postgresql.org/docs/18/pgstatstatements.html)

초기화와 항목 교체가 없다는 가정의 합성 표본입니다.

```text
시점 1: calls=1,000, total_exec_time=12,000 ms
시점 2: calls=1,200, total_exec_time=15,000 ms
구간 평균 = (15,000 − 12,000) / (1,200 − 1,000) = 15 ms
```

두 시점의 lifetime mean을 빼는 것은 구간 평균을 구하는 방법이 아닙니다. 실행 수 차이가 0이면 나눗셈 결과를 만들지 않습니다. 카운터 수명이 바뀌거나 수집 간 항목이 사라졌다 돌아오면 차분의 연속성을 다시 판단합니다.

## VACUUM이 하는 일

UPDATE·DELETE 뒤 남는 이전 행 버전은 더 필요하지 않을 때 정리할 수 있습니다. 일반 VACUUM은 공간을 재사용 가능하게 만들지만 대부분의 경우 파일 크기를 그대로 OS에 반환하는 작업은 아닙니다. VACUUM FULL은 재작성으로 압축하며 잠금·작업 특성이 다릅니다. [PostgreSQL Routine Vacuuming](https://www.postgresql.org/docs/18/routine-vacuuming.html)

따라서 “vacuum이 성공했는데 파일 크기가 그대로”라는 사실만으로 실패를 판정하지 않습니다. 회수 가능 공간과 물리 파일 크기는 다른 지표입니다. 관측 시스템에서는 자동 정리 작업의 최근 성공, 처리량, 실패, 오래 열린 트랜잭션과 여유 저장 공간을 함께 보여 주도록 제안합니다.

## 버전 차이를 다루는 수집기

이 장의 기준은 18이며 이전 버전에서 모든 view와 컬럼이 같다고 가정하지 않습니다. 수집 시작 시 버전을 기록하고 지원 view를 확인하며, 없는 컬럼은 0으로 채우지 않고 지원 여부를 표시합니다. 확장 설치·설정 변경이 필요한 자료와 기본 조회 자료도 구분합니다.

## 읽기 전용 조회 예시

아래는 개념 확인용 조회이며 실제 DB에서 실행하지 않았습니다. 자신의 계정과 다른 세션의 상세 정보 접근 범위는 권한에 따라 다릅니다.

```sql
SELECT state, wait_event_type, wait_event, count(*) AS sessions
FROM pg_stat_activity
GROUP BY state, wait_event_type, wait_event;
```

이 결과를 “대기 원인의 전체 시간 비중”으로 해석하면 안 됩니다. 한 번의 시점별 세션 집계일 뿐이며, 시간 비중 추정에는 표본 간격과 수집 누락을 고려한 반복 관측이 필요합니다.

## 가상 진단

쿼리 호출률이 비슷한데 구간 평균이 15→150 ms로 늘었다고 가정합니다. 대기 종류, 실행 계획, 블록 접근량, 반환 행 수, WAL과 저장소를 비교합니다. 연결 풀 대기는 DB 통계에 도착하기 전의 시간이므로 [애플리케이션](../application/requests-and-concurrency.md)에서 추가 확인합니다.

## 이해 확인

1. active 세션이면 CPU 실행 중인가? **대기 이벤트가 있을 수 있습니다.**
2. 일반 VACUUM 뒤 파일이 작아져야만 성공인가? **재사용 가능한 공간 확보와 파일 축소는 다릅니다.**
3. 누적 mean 차분은 구간 mean인가? **시간 합의 차분을 호출 수 차분으로 나눠야 합니다.**

다음: [MySQL·MariaDB](mysql-mariadb.md) · [DB 목차](README.md)
