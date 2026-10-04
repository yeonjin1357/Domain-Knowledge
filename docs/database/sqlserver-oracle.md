# SQL Server와 Oracle: 대기와 실행 통계

> 상태: 검토됨 · 적용 범위: SQL Server DMV·Query Store의 공통 의미, Oracle Database 19c · 출처 확인일: 2026-10-03 · 편집 검토일: 2026-10-04

## 먼저 이해할 것

각 DB는 세션·대기·실행 계획을 관측하는 고유한 관리 view를 제공합니다. 공통 화면을 만들 때도 원천의 ms·µs 단위, 실행 중 작업과 완료 통계, cache 수명을 보존해야 합니다. 여러 병렬 작업의 시간이 합쳐진 값을 사용자가 기다린 경과 시간으로 오해하지 않는 것이 핵심입니다.

상용 관계형 엔진의 관측도 현재 상태, 누적 집계, 보존된 이력을 분리해야 합니다. 같은 이름의 elapsed time도 엔진에 따라 포함하는 작업 범위가 다릅니다.

## SQL Server의 대기 통계

`sys.dm_os_wait_stats`는 대기 유형별 누적 통계를 제공합니다. `wait_time_ms`에는 `signal_wait_time_ms`가 포함됩니다. signal wait는 실행 가능 신호를 받은 뒤 실제 실행까지의 시간입니다. 이 view는 현재 대기 중인 모든 요청의 개별 목록을 대신하지 않습니다. [Microsoft sys.dm_os_wait_stats](https://learn.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-views/sys-dm-os-wait-stats-transact-sql?view=sql-server-ver17)

초기화가 없는 합성 구간을 생각해 봅시다.

```text
전체 대기 시간 증가 = 12,000 ms
그중 signal 증가    =  2,000 ms
나머지 대기 증가    = 10,000 ms
```

전체에 signal을 더한 14,000 ms는 중복입니다. 여러 작업의 대기 합은 벽시계 구간을 넘을 수 있습니다. 또한 총 대기 순위에는 정상적인 배경 대기도 포함될 수 있으므로 종류와 작업 맥락을 해석해야 합니다.

제품에서는 엔진 시작과 통계 초기화의 수명을 확인하고 구간 차분을 비교하도록 제안합니다. 현재 느린 요청을 찾는 자료와 인스턴스 전체의 누적 대기 분포를 나란히 두면 서로의 한계를 보완할 수 있습니다.

## 캐시 통계와 이력 저장

`sys.dm_exec_query_stats`는 캐시된 계획 내 문장의 집계 통계이며 계획이 캐시에서 제거되면 관련 행도 사라집니다. 실행 중인 문장보다 완료된 실행을 반영하므로 현재 진행 중인 긴 요청은 별도 관측이 필요합니다. [Microsoft sys.dm_exec_query_stats](https://learn.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-objects/sys-dm-exec-query-stats-transact-sql?view=sql-server-ver16)

Query Store는 쿼리·계획·런타임 통계의 이력을 보존해 계획 변화와 성능을 분석할 수 있게 합니다. 수집 모드와 보존·용량 설정을 확인해야 하며 캐시 view와 동일한 수명으로 취급하지 않습니다. [Microsoft Query Store](https://learn.microsoft.com/en-us/sql/relational-databases/performance/monitoring-performance-by-using-the-query-store?view=sql-server-ver16)

가상으로 어제 느렸던 계획이 오늘 캐시에서 사라졌다면 현재 DMV에 없다는 사실이 어제 실행되지 않았다는 증거는 아닙니다. 제품은 수집 당시의 계획·집계를 저장했는지, 엔진의 이력 수집이 켜져 있었는지를 구분합니다.

## Oracle 세션의 식별

Oracle `V$SESSION`에는 현재 세션의 SID와 SERIAL# 등이 있습니다. SERIAL#는 같은 SID가 새 세션에 재사용되는 경우를 구분하는 데 필요합니다. [Oracle 19c V$SESSION](https://docs.oracle.com/en/database/oracle/oracle-database/19/refrn/V-SESSION.html)

다중 인스턴스 환경까지 지원하는 제품 키에는 DB 식별, 인스턴스 범위, SID와 SERIAL#를 함께 고려하도록 제안합니다. SID만으로 이전 세션의 지표를 새 세션에 이어 붙이지 않습니다. 이 원리는 [OS PID 수명](../host/processes.md)과 비슷하지만 식별 필드는 엔진 고유입니다.

## Oracle elapsed time의 병렬성

`V$SQLSTATS`의 CPU_TIME과 ELAPSED_TIME은 microseconds 단위입니다. ELAPSED_TIME은 파싱·실행·fetch를 포함하며 병렬 실행에서는 query coordinator와 병렬 작업자들의 누적 시간이 포함됩니다. 따라서 사용자 한 요청의 벽시계 시간과 같다고 볼 수 없습니다. [Oracle 19c V$SQLSTATS](https://docs.oracle.com/en/database/oracle/oracle-database/19/refrn/V-SQLSTATS.html)

가상으로 coordinator 1초, 병렬 작업자 두 개가 각각 1초를 보고했다면 이 정의의 누적 시간은 3초 규모일 수 있습니다. 이를 근거로 사용자가 반드시 3초 기다렸다고 표시하지 않습니다. 클라이언트 관측 시간은 별도 자료가 필요합니다.

## 엔진 간 공통 화면의 경계

| 공통 질문 | 통합할 때 필요한 메타데이터 |
| --- | --- |
| 어떤 작업이 느린가 | 클라이언트·DB·병렬 작업 중 시간 범위 |
| 무엇을 기다리는가 | 엔진 원천 wait 이름과 분류 규칙 |
| 얼마나 실행했는가 | 누적 시작과 항목 교체·초기화 |
| 어떤 세션인가 | 엔진·인스턴스·세션 수명 식별 |
| 과거를 조회할 수 있는가 | 캐시, 엔진 이력, 제품 자체 저장의 차이 |

공통 분류는 제품의 해석 계층이며 원천 wait 이름과 값도 함께 남기는 것을 제안합니다. 새로운 버전에서 분류를 수정하더라도 원본 근거를 다시 확인할 수 있어야 합니다.

조회 권한과 제공 기능은 엔진 버전·배포 형태·활성화 설정에 따라 확인합니다. 이 장의 view 소개가 모든 환경에서 같은 계정으로 즉시 조회 가능하다는 뜻은 아닙니다. 실제 SQL Server·Oracle 연결이나 진단 명령 실행은 수행하지 않았습니다.

## 이해 확인

1. 전체 wait에 signal wait를 더해야 하는가? **이미 포함되므로 중복됩니다.**
2. 캐시에서 사라진 쿼리는 과거에도 없었는가? **캐시 수명과 실행 이력은 다릅니다.**
3. Oracle 병렬 elapsed time은 사용자 벽시계 시간인가? **여러 실행 주체의 누적 시간을 포함할 수 있습니다.**

다음: [복제와 복구](replication-and-recovery.md) · [DB 목차](README.md)
