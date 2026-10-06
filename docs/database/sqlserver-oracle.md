# SQL Server와 Oracle: 대기와 실행 통계

> 상태: 검토됨 · 적용 범위: SQL Server DMV·Query Store의 공통 의미, Oracle Database 19c · 출처 확인일: 2026-10-03 · 편집 검토일: 2026-10-04 · 3d 원천 검토: 2026-10-06

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

## SQL Server: 읽기 충돌을 줄여도 이전 행 버전은 남는다

**보강 확인: 2026-10-05, SQL Server 2019·2022 및 명시한 이후 차이.** 조회가 UPDATE를 덜 막게 만드는 row versioning은 이전 행을 보존하는 비용을 다른 곳에 둡니다. RCSI(`READ_COMMITTED_SNAPSHOT`)는 READ COMMITTED의 문장 단위 일관 읽기, SNAPSHOT은 트랜잭션 단위 일관 읽기를 제공합니다. 오래 유지되는 읽기·트랜잭션은 필요한 이전 버전의 정리를 늦출 수 있습니다. “읽기 잠금 감소”와 “저장 공간 부담 없음”은 다른 주장입니다. [잠금과 row versioning](https://learn.microsoft.com/en-us/sql/relational-databases/sql-server-transaction-locking-and-row-versioning-guide?view=sql-server-ver16)

기본적인 version store는 tempdb에 있지만 **ADR(Accelerated Database Recovery)을 켠 사용자 DB는 그 DB의 persistent version store(PVS)를 사용**합니다. SQL Server 2025에서 tempdb 자체에 ADR을 켜는 경우의 PVS도 별도 구분해야 합니다. 따라서 tempdb만 확인하여 모든 row version 사용량이 작다고 결론 내리지 않습니다. [ADR와 PVS](https://learn.microsoft.com/en-us/sql/relational-databases/accelerated-database-recovery-concepts?view=sql-server-ver17)

`sys.dm_tran_version_store_space_usage`는 DB별로 tempdb에 사용한 version store 공간을 집계합니다. `reserved_space_kb`는 KB, `reserved_page_count`는 페이지 수입니다. 개별 version record를 전수 스캔하는 `sys.dm_tran_version_store`보다 정기 관측에 적합한 집계 원천입니다. PVS는 `sys.dm_tran_persistent_version_store_stats` 등으로 따로 조사하고 in-row/off-row 범위도 확인합니다. [tempdb 집계 DMV](https://learn.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-objects/sys-dm-tran-version-store-space-usage?view=sql-server-ver17), [PVS 통계](https://learn.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-views/sys-dm-tran-persistent-version-store-stats?view=sql-server-ver17)

## SQL Server AG: 아직 보내지 않은 로그와 아직 redo하지 않은 로그

`sys.dm_hadr_database_replica_states`는 DB·replica별 복제 상태입니다. `log_send_queue_size`는 primary에서 secondary로 아직 보내지 않은 로그 양, `redo_queue_size`는 secondary 로그에 도착했지만 아직 redo하지 않은 양이며 둘 다 **KB**입니다. 이름에 record가 들어간 설명을 보고 행 수로 저장하지 않습니다. `log_send_rate`·`redo_rate`의 단위는 KB/s입니다. [AG DMV의 필드·권한](https://learn.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-objects/sys-dm-hadr-database-replica-states-transact-sql?view=sql-server-ver17)

큐 크기는 시점의 잔량이며 지연 초가 아닙니다. redo_rate는 **DB 엔진 시작 이후 누적 redo 양을 실제 redo가 수행된 누적 시간으로 나눈 평균**입니다. 최근 몇 초의 속도도, 엔진 시작 후 벽시계 전체 시간으로 나눈 속도도 아닙니다. workload나 자원 배치가 바뀌면 과거 평균으로 queue/rate를 계산한 추정이 현재와 어긋날 수 있습니다. `queue/rate`는 유입·실행 조건이 유지된다는 가정하의 추정이며 복구 시간 보증이 아닙니다. primary가 알고 있는 secondary 상태는 마지막 보고에 의존할 수 있어 로컬 관측과 freshness를 함께 남깁니다. 제품은 전송 대기와 redo 대기를 서로 다른 병목 후보로 표시하도록 제안합니다. [send queue 해석](https://learn.microsoft.com/en-us/troubleshoot/sql/database-engine/availability-groups/troubleshooting-log-send-queuing-in-alwayson-availability-group)

다음은 **실행하지 않은 읽기 전용 SQL**입니다. 위 tempdb 집계와 AG DMV는 SQL Server 2019 이하에서 `VIEW SERVER STATE`, 2022 이상에서는 더 좁은 `VIEW SERVER PERFORMANCE STATE`로 조회할 수 있습니다. 기존 `VIEW SERVER STATE`도 이 권한을 포함하므로 새 권한만으로 교체해야 조회되는 것은 아닙니다. 최소 권한 구성을 선택하고 DENY 등의 유효 권한도 확인합니다. [서버 권한 포함 관계](https://learn.microsoft.com/en-us/sql/t-sql/statements/grant-server-permissions-transact-sql?view=sql-server-ver17) 이를 모든 DMV·Azure 배포 형태의 공통 권한으로 넓히지 않습니다. 낮은 빈도의 집계 조회이며, row version 전체 스캔·설정 변경·복제 재시작은 수행하지 않습니다.

```sql
SELECT database_id, reserved_page_count, reserved_space_kb
FROM sys.dm_tran_version_store_space_usage;
SELECT database_id, replica_id, is_local, synchronization_state_desc,
       log_send_queue_size, log_send_rate, redo_queue_size, redo_rate
FROM sys.dm_hadr_database_replica_states;
```

## Oracle 세션의 식별

Oracle `V$SESSION`에는 현재 세션의 SID와 SERIAL# 등이 있습니다. SERIAL#는 같은 SID가 새 세션에 재사용되는 경우를 구분하는 데 필요합니다. [Oracle 19c V$SESSION](https://docs.oracle.com/en/database/oracle/oracle-database/19/refrn/V-SESSION.html)

다중 인스턴스 환경까지 지원하는 제품 키에는 DB 식별, 인스턴스 범위, SID와 SERIAL#를 함께 고려하도록 제안합니다. SID만으로 이전 세션의 지표를 새 세션에 이어 붙이지 않습니다. 이 원리는 [OS PID 수명](../host/processes.md)과 비슷하지만 식별 필드는 엔진 고유입니다.

## Oracle elapsed time의 병렬성

`V$SQLSTATS`의 CPU_TIME과 ELAPSED_TIME은 microseconds 단위입니다. ELAPSED_TIME은 파싱·실행·fetch를 포함하며 병렬 실행에서는 query coordinator와 병렬 작업자들의 누적 시간이 포함됩니다. 따라서 사용자 한 요청의 벽시계 시간과 같다고 볼 수 없습니다. [Oracle 19c V$SQLSTATS](https://docs.oracle.com/en/database/oracle/oracle-database/19/refrn/V-SQLSTATS.html)

가상으로 coordinator 1초, 병렬 작업자 두 개가 각각 1초를 보고했다면 이 정의의 누적 시간은 3초 규모일 수 있습니다. 이를 근거로 사용자가 반드시 3초 기다렸다고 표시하지 않습니다. 클라이언트 관측 시간은 별도 자료가 필요합니다.

## Oracle: ASH·AWR의 기능 활성화와 사용 권리를 구분한다

**Oracle Database 19c 라이선스 문서 확인: 2026-10-05.** ASH는 활성 세션 표본의 이력, AWR은 성능 통계의 이력을 제공하지만, SQL로 조회 가능하다는 것만으로 사용 권리가 있는 것은 아닙니다. `V$ACTIVE_SESSION_HISTORY`와 그 기반 `X$ASH`, AWR 보고서·관련 API는 Diagnostics Pack 범위입니다. 일반적으로 `DBA_HIST_*`도 해당하며, 공식 문서는 `DBA_HIST_SNAPSHOT`, `DBA_HIST_DATABASE_INSTANCE`, `DBA_HIST_SNAP_ERROR`, `DBA_HIST_SEG_STAT`, `DBA_HIST_SEG_STAT_OBJ`, `DBA_HIST_UNDOSTAT`를 예외로 명시합니다. 예외 view 하나를 허용했다고 이를 다른 유료 view와 조인하는 사용까지 허용된 것으로 취급하지 않습니다. [19c Licensing Information — Diagnostics Pack](https://docs.oracle.com/en/database/oracle/oracle-database/19/dblic/Licensing-Information.html)

`CONTROL_MANAGEMENT_PACK_ACCESS`는 NONE·DIAGNOSTIC·DIAGNOSTIC+TUNING으로 기능 활성 범위를 제어합니다. Enterprise Edition의 기본값은 DIAGNOSTIC+TUNING이지만 이 설정이 계약상 이용 권리의 증거는 아닙니다. 제품은 에디션·서비스에 포함된 권리와 고객의 허용 범위를 명시적으로 등록한 뒤 해당 adapter를 활성화하도록 제안합니다. 비활성 상태에서 “되는지 시험”하려고 ASH/AWR를 조회하지 않습니다. [19c 설정 정의](https://docs.oracle.com/en/database/oracle/oracle-database/19/refrn/CONTROL_MANAGEMENT_PACK_ACCESS.html)

Diagnostics Pack을 이용하지 않는 관측 경로로는 허용된 `V$SESSION` 현재 상태를 일정 간격으로 자체 저장하는 방법과 Statspack을 검토할 수 있습니다. 자체 표본은 간격 사이의 짧은 활동을 놓치므로 ASH와 동등한 이력이 아닙니다. Statspack도 스냅샷 통계이며 설치·스냅샷 생성은 DB 객체·저장 공간을 변경하는 관리 작업입니다. 모니터링 계정이 자동 설치하지 않고 DBA가 구성한 허용 원천을 읽는 형태로 구분합니다. [V$SESSION 정의](https://docs.oracle.com/en/database/oracle/oracle-database/19/refrn/V-SESSION.html), [19c RAC의 Statspack 보고 기능·호환성 설명](https://docs.oracle.com/en/database/oracle/oracle-database/19/racad/monitoring-performance.html)

19c 문서는 Statspack을 하위 호환성을 위한 보고 기능으로 남겨 두고 있습니다. 실제 설치·조회 원천은 해당 배포의 문서와 DBA 구성을 확인합니다. 특히 `spawrio.sql`·`spawrrac.sql`은 19c Licensing Information에서 Diagnostics Pack에 포함하므로 **파일명이 sp로 시작한다는 이유로 무료 Statspack 범위라고 분류하지 않습니다**. [19c 라이선스의 보고서 목록](https://docs.oracle.com/en/database/oracle/oracle-database/19/dblic/Licensing-Information.html)

이 절에서는 Oracle에 연결하거나 조회·설정 변경을 실행하지 않았습니다. 제품 설계는 허용 view·열별 조회 권한과 계약상 사용 범위를 함께 확인하고, 자체 표본의 빈도·SQL 민감 정보·보존량을 제한합니다. 기능 미허용·권한 부족·표본 부재를 각각 다른 상태로 남깁니다.

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
4. tempdb version store가 작으면 모든 이전 행 버전도 작은가? **ADR의 사용자 DB PVS 등 저장 위치를 확인해야 합니다.**
5. AG redo queue 0은 전송 대기도 0이라는 뜻인가? **전송과 redo는 서로 다른 단계입니다.**
6. ASH SELECT가 성공하면 Diagnostics Pack 사용 권리가 확인되는가? **조회 권한·기능 활성화와 계약상 사용 권리는 다릅니다.**

다음: [복제와 복구](replication-and-recovery.md) · [DB 목차](README.md)
