# 로그, 지속성, 복제와 복구

> 상태: 본문 초안 · 적용 범위: 공통 복구 모델과 PostgreSQL 18 사례 · 출처 확인일: 2026-10-03

저장 성공, 복제 전송, 복제 적용, 백업 성공은 서로 다른 단계입니다. 제품은 어느 실패 범위에서 어떤 데이터를 보존하는지를 드러내야 합니다.

## WAL이 필요한 이유

Write-Ahead Logging은 데이터 파일 변경을 영구 저장하기 전에 해당 변경을 설명하는 로그를 먼저 영구 저장하는 원리입니다. PostgreSQL은 이를 통해 커밋 때 변경된 모든 데이터 페이지를 즉시 기록하지 않아도 로그로 복구할 수 있습니다. 여러 트랜잭션의 로그 동기화를 묶는 경우도 있습니다. [PostgreSQL WAL Introduction](https://www.postgresql.org/docs/18/wal-intro.html)

따라서 커밋 지연을 조사할 때 데이터 파일의 IOPS만 보면 부족합니다. WAL 생성량, 동기화 지연과 저장 경로를 구분하는 관측을 제안합니다. 캐시에 쓰인 것과 장애 후 보존 가능한 저장에 도달한 것도 구분합니다.

## 성공 응답의 경계

PostgreSQL의 `synchronous_commit`은 성공 응답 전에 어느 WAL 처리까지 기다릴지를 설정합니다. `off`에서는 최근 성공 응답된 트랜잭션이 충돌로 유실될 수 있습니다. 동기 standby가 설정된 경우 `on`은 해당 standby의 영구 저장, `remote_apply`는 적용까지 기다리는 의미를 가집니다. 동기 standby 설정이 없으면 이름만으로 원격 보장을 얻지 않습니다. [PostgreSQL WAL Configuration](https://www.postgresql.org/docs/18/runtime-config-wal.html)

이 예는 설정 이름이 실제 보장과 함께 읽혀야 함을 보여 줍니다. 모든 엔진에서 같은 옵션 이름이나 기본값을 사용한다고 일반화하지 않습니다.

## 복제의 여러 위치

```text
원본 로그 생성 → 송신 → 복제본 수신 → 기록·동기화 → 적용 → 읽기에 반영
```

위는 관측을 위한 공통 단계 모델입니다. 원천이 어느 위치를 제공하는지 명세하고, 같은 로그 계열에서 비교 가능한 위치만 차분합니다. 역할 전환이나 계열 변경 뒤의 위치를 이어서 빼지 않습니다.

PostgreSQL의 replication slot은 필요한 WAL을 남겨 두는 데 사용됩니다. 복제본이 진행하지 못하면 보존량이 커져 `pg_wal` 공간을 채울 수 있으며 관련 제한 설정을 고려해야 합니다. [PostgreSQL Standby and Replication Slots](https://www.postgresql.org/docs/18/warm-standby.html)

따라서 “원본 DB의 데이터 변경량은 평소와 같은데 로그 디스크가 찬다”는 사례에서는 오래된 slot과 복제 진행을 확인하는 가설을 세울 수 있습니다.

## lag는 하나의 숫자가 아니다

PostgreSQL의 `pg_stat_replication` lag는 최근 WAL의 기록·동기화·적용과 통지에 걸린 시간을 나타냅니다. 복제본이 따라잡은 뒤 원본이 유휴 상태가 되면 NULL이 될 수 있으며, 현재 잔량을 모두 처리하는 데 필요한 예상 시간은 아닙니다. [PostgreSQL Replication Statistics](https://www.postgresql.org/docs/18/monitoring-stats.html#MONITORING-PG-STAT-REPLICATION-VIEW)

제품은 시간 지연, 로그 위치 차이, receiver 상태, 마지막 진행 시각과 업무 데이터의 신선도를 구분하도록 제안합니다. [MySQL의 Seconds_Behind_Source](mysql-mariadb.md)도 고유한 의미와 한계가 있습니다.

가상 계산에서 잔량이 8 GiB, 적용률이 40 MiB/s, 원본 신규 생성률이 24 MiB/s로 계속 일정하다고 가정하면 순감소율은 16 MiB/s입니다.

```text
추정 따라잡기 시간 = 8 × 1024 MiB / (40 − 24) MiB/s = 512 s
```

이는 조건부 추정입니다. 생성률이 적용률 이상이면 이 식으로 유한한 완료 시간을 얻지 못합니다. 로그 작업의 난이도가 바뀌면 같은 바이트라도 적용 시간이 달라질 수 있어 실측 예측 정확도를 보장하지 않습니다.

## 복제와 백업의 차이

복제본에 잘못된 삭제까지 전달된다면 복제본이 있다는 사실만으로 삭제 이전 상태를 복구할 수 있는 것은 아닙니다. PostgreSQL의 PITR은 기반 백업과 이어지는 WAL 기록을 사용해 원하는 지점까지 복원하는 방식입니다. 필요한 로그 연속성이 있어야 합니다. [PostgreSQL Continuous Archiving and PITR](https://www.postgresql.org/docs/18/continuous-archiving.html)

제품의 복구 관측에는 다음을 별도로 두는 것을 제안합니다.

- 최근 백업 작업의 실행 성공
- 사용 가능한 복구 지점과 로그 연속성
- 실제 복원 검증의 시각과 결과
- 복구에 필요한 예상·실측 시간의 구분

이 지식서에서 RPO는 허용 데이터 손실 범위의 시간 목표, RTO는 서비스 복구까지 허용하는 시간 목표로 사용합니다. 목표와 실제 시험 결과를 분리합니다. 백업 파일 생성 성공만으로 두 목표를 달성했다고 표시하지 않습니다.

## 이해 확인

1. 복제 수신 완료가 적용 완료인가? **단계가 다릅니다.**
2. lag 시간은 따라잡기 예상 시간인가? **원천 정의가 그와 다를 수 있습니다.**
3. 백업 성공은 복원 검증 성공인가? **실제 복원 자료를 따로 확인해야 합니다.**

다음: [비관계형·분산·분석 DB](distributed-and-analytical.md) · [DB 목차](README.md)
