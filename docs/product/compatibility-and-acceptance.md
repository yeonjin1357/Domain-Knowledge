# 어댑터를 지원한다고 말하기 전에: 필드 계약과 검증 근거

> 상태: 검토됨 · 적용 범위: 이 책의 제품 설계 제안과 연결된 원천 규약·실험 · 원천 확인일: 2026-10-06 · 실습 여부: 원천·가상 예시 중심; 연결 실습의 범위는 본문

## 먼저 이해할 것

서로 다른 전기 제품에 플러그가 맞는다고 전압까지 맞는 것은 아닙니다. 수집기도 endpoint에 접속하고 JSON을 읽었다고 의미가 맞는 지표를 만든 것은 아닙니다. 원천 필드부터 화면 값까지 무엇이 보장되는지를 적어야 “지원한다”는 말이 구체적이 됩니다.

이 장은 [어댑터 참조 구현](adapter-contracts.md)을 검토·출시 기준으로 연결합니다. 아래 이름과 상태 모델은 제품 설계 제안이며 외부 표준을 새로 정의한 것이 아닙니다.

## 필드 계약을 읽는 순서

각 필드에 다음 여덟 질문에 답하도록 제안합니다.

1. 어떤 버전·설정·endpoint에서 읽는가?
2. 값은 어떤 대상·계층을 포함하는가?
3. 원천 유형·단위와 정규화 단위는 무엇인가?
4. 순간값·구간 합·누적값 중 무엇인가?
5. 어떤 정체성과 수명이 바뀌면 연결을 끊는가?
6. NULL·필드 부재·권한 거절·timeout은 어떻게 구분하는가?
7. 합·평균·rate 중 어떤 계산이 가능한가?
8. 정의를 확인한 자료와 실제 실행 증거는 어디에 있는가?

OTel의 resource·metric 유형·temporality와 source의 식별 의미를 보존하는 것이 관련된 원리입니다. 아래 계약표를 OTLP wire format 자체라고 취급하지 않습니다. [OTel metric 모델](https://opentelemetry.io/docs/specs/otel/metrics/data-model/)

## Linux 필드의 구체적인 계약

| 원천 | 유형·단위 | 수명·계산 | 누락·범위 주의 |
| --- | --- | --- | --- |
| `/proc/PID/stat` utime·stime | 누적 ticks → CPU초 | 실제 CLK_TCK 사용; PID·starttime 기준 차분 | comm 파싱·접근 실패·읽는 중 종료 |
| `smaps`의 Rss | 매핑별 현재 kB | 해당 Linux 표시의 KiB를 byte로 변환 | 전체 프로세스·다른 매핑과 구분 |
| `/proc/PID/io` rchar | 누적 byte | 같은 프로세스 실행에서 차분 | 저장 장치 read byte와 다름 |
| `/proc/PID/io` read_bytes | 누적 byte | 저장 계층의 원천 계정 | 캐시·접근 권한·계층을 확인 |
| cgroup `memory.current` | 현재 byte | 계층 포함 범위를 유지 | heap으로 이름 바꾸지 않음 |
| cgroup `memory.max` | byte 또는 `max` | 사용률의 한도 후보; 상위 제한 별도 | `max`를 0이나 매우 큰 임의 정수로 바꾸지 않음 |
| cgroup `cpu.max` | quota·period, µs 또는 `max` | quota/period는 설정된 CPU 시간 예산 | 실제 CPU 사용량과 다름; cpuset·부모 제한 확인 |

원천 정의와 권한은 [호스트 수집 계약](../host/collection-contracts.md), [proc I/O](https://man7.org/linux/man-pages/man5/proc_pid_io.5.html), [cgroup v2](https://docs.kernel.org/admin-guide/cgroup-v2.html)에 있습니다. 실제 읽기는 [Linux 실습](../host/linux-observation-lab.md)의 범위입니다. 필드 읽기 성공과 제한 동작의 장애 실험은 구분합니다.

## PostgreSQL 필드의 구체적인 계약

| 원천 | 유형·단위 | 수명·계산 | 누락·범위 주의 |
| --- | --- | --- | --- |
| `xact_commit` | 누적 transaction 수 | 인스턴스·DB·통계 수명 안의 차분 | SQL 수·주문 수와 동일하지 않음 |
| `blks_read` | 누적 DB block 수 | byte 변환 시 DB block 크기 확인 | 물리 디스크 I/O 횟수와 동일하지 않음 |
| `stats_reset` | timestamp 또는 NULL | 통계 수명의 단서 중 하나 | 새 실습 인스턴스에서도 NULL 관측 |
| `pg_stat_activity.state` | 상태 문자열 또는 NULL | 현재 세션 관측; count로 바꾸려면 대상 집합 명시 | 다른 세션 정보의 권한 제한 |
| `wait_event_type` | 대기 분류 또는 NULL | state와 별도 해석 | NULL만으로 CPU 실행 중이라고 확정 불가 |
| `pg_blocking_pids()` | PID 배열 | instance·backend 수명과 연결 | 특수 반환값·병렬 작업·수집 비용 확인 |

정의는 [PostgreSQL 통계](https://www.postgresql.org/docs/18/monitoring-stats.html)와 [시스템 정보 함수](https://www.postgresql.org/docs/18/functions-info.html)를 따릅니다. [실제 수집 SQL](../../labs/postgresql/collect-database.sql)은 18.6의 한 로컬 인스턴스에서 실행했습니다. 이것이 MySQL·Oracle의 대응 필드까지 검증한 증거는 아닙니다.

`stats_reset` 하나를 언제나 존재하는 수명 ID로 쓰지 않습니다. DB OID·인스턴스 식별·server 시작 정보·counter 감소·관리자가 수행한 reset과 같은 단서를 조합하는 정책이 필요합니다. 프로세스 재시작과 모든 통계의 reset을 항상 같은 사건으로 가정하지도 않습니다.

## API와 전송 필드의 구체적인 계약

| 원천 | 유형 | 보존할 의미 | 피할 오해 |
| --- | --- | --- | --- |
| Kubernetes UID | 식별 문자열 | 객체 생성 수명 | 같은 이름이면 같은 객체 |
| Kubernetes resourceVersion | 버전 문자열 | 서버 버전·resource type에 맞춘 비교 | 다른 자원 사이의 전역 시계 |
| list의 continue | 연속 조회 token | 동일 목록의 다음 페이지 | token 부재만으로 모든 원천 상태가 완전 |
| OTLP rejectedSpans | 해당 응답의 거절 개수 | 부분 성공의 손실 정보 | 어떤 개별 span인지 항상 알 수 있음 |
| CloudWatch Timestamps·Values | 같은 길이의 쌍 | 인덱스별 시간과 값 대응 | 각각 독립 정렬해도 됨 |
| CloudWatch StatusCode | 결과별 상태 | Complete·PartialData·오류·거절 | HTTP 200이면 모두 Complete |

각 규약과 실행 구분은 [Kubernetes 인벤토리](../kubernetes/inventory-consistency.md), [OTLP 전송](telemetry-delivery-contracts.md), [cloud 재조회](../cloud/late-data-and-reconciliation.md)에 있습니다. cloud 표는 공식 자료 검토이며 실제 계정 호출 결과가 아닙니다.

## 호환성 표에 문서와 실행을 따로 기록하기

다음은 **이번 판의 근거 표**이며 사용자 제품의 지원 목록이 아닙니다.

| 대상 | 공식 자료 검토 | 실제 실행 | 남는 경계 |
| --- | --- | --- | --- |
| Linux | procfs·cgroup v2 | WSL2의 자기 프로세스·기존 cgroup 읽기 | 물리 Linux 전체·OOM·다른 배포판 |
| PostgreSQL | 18 규약 | 18.6 동시성·권한·수집 SQL와 prepared transaction·slot·standby의 회수 기준점 | 운영 replication 부하·HA 전환·상용 확장 |
| Kubernetes | 1.35 이상과 이전 규약의 경계 | 1.34.1·1.37.0 API server·etcd, 각각 watch cache true/false | 최신 patch·1.35/1.36 서버·kubelet·CNI·CSI |
| OTLP | 1.11.0 고정 문서, 1.11.1 릴리스 존재 확인 | 0.137.0 HTTP JSON 기록 보존; 0.162.0 내부 로그의 부분 거절·최종 실패 지표·queue 수락 경계 | gRPC·persistent queue·tail sampling·목적지 영속 저장 |
| HTTP | RFC·Python 문서 | loopback HTTP/1.1 | DNS·TLS·HTTP/2·외부 proxy |

고정 실행 버전, 검토 시점 최신 버전, 종료 일정은 [버전 상태 표](../coverage.md#교차-검토-시점의-버전-상태)에 따로 기록했습니다. 최신 릴리스 존재 확인을 그 릴리스의 동작 실험으로 표시하지 않습니다.

버전 문자열만 같은 환경끼리도 build 옵션·기능 활성화·권한·배포판에 따라 가용 필드가 다를 수 있습니다. “필드가 있다”와 “값이 의미 있게 계측된다”를 각각 확인합니다.

## 정의 변경을 과거 시계열에 숨기지 않기

**제품 설계 예시:** 첫 버전에서 container memory를 working set으로 노출하다가 다음 버전에서 memory.current로 바꾸면 값의 의미가 달라집니다. 이름을 유지한 채 과거 데이터와 이어 붙이면 갑작스러운 누수처럼 보일 수 있습니다.

새 지표를 만들거나 정의 버전과 변경 시점을 명시하고, 이전 의미를 유지하는 호환 경로를 검토합니다. 단위만 바꾸는 경우에도 저장·쿼리·알림에서 변환이 한 번만 적용되는지 확인합니다. [버전과 안정성의 한 사례](https://kubernetes.io/docs/concepts/cluster-administration/system-metrics/)

## 지원 판정의 근거

자동 검사는 출처 링크가 있다는 사실만으로 참을 판정하지 못합니다. 다음 단계를 **제품 수용 기준의 제안**으로 구분합니다.

| 단계 | 통과 근거 |
| --- | --- |
| 정의 검토 | 버전이 맞는 공식 원천에서 단위·계정·보장을 확인 |
| 입력 처리 | 정상값·0·NULL·부재·큰 정수·형식 오류를 구분 |
| 수명 처리 | reset·재생성·ID 재사용·재연결을 확인 |
| 실제 관측 | 알려진 작업과 원천 결과를 대조 |
| 실패 처리 | 권한·부분 목록·단절·중복·시간 초과를 재현 |
| 비용 확인 | 실제 대상에서 수집 부하·빈도·고카디널리티를 측정 |

한 단계의 통과를 나머지 단계의 통과로 확장하지 않습니다. 이 문서의 실행 증거도 표에 적힌 범위까지 유효합니다.

## 기계 계약을 수용 기준에 연결하기

[87개 필드 카탈로그](../../catalog/field-catalog.json)에서 원천·단위·reset·NULL·권한·검토 버전을 고른 다음 실제 대상의 capability를 확인합니다. 필드 존재, 읽기 권한, 의미 확인, 실측 통과는 각각 다른 근거입니다. [어댑터의 상태 축·fixture 흐름](adapter-contracts.md)을 수용 표에 연결합니다.

PG의 `backend_xmin=NULL`은 저장 실측이 있고 `replay_lag=NULL`의 어댑터 예는 가상 입력입니다. 한 필드에서 NULL을 관측했다고 모든 NULL 의미를 실행 검증한 것으로 표시하지 않습니다. 원천별 실제 지원을 승인할 때는 대상 버전·설정·계정·실패 조건을 명시합니다.

## 이해 확인

1. endpoint가 200이면 그 제품 지원을 완료했다고 할 수 있는가? **필드 의미·권한·실패·비용까지 별도의 근거가 필요합니다.**
2. 단위가 byte면 서로 다른 memory 지표를 합쳐도 되는가? **관측 범위와 의미가 같아야 합니다.**
3. 문서를 읽은 버전과 실행한 버전이 다르면 어떻게 기록하는가? **두 근거를 분리하고 검증하지 않은 차이를 남깁니다.**
4. working set을 current로 바꾸면 문서만 고치면 되는가? **시계열·쿼리·알림의 의미 변경도 다뤄야 합니다.**

이전: [어댑터 계약: 서로 다른 원천을 정확히 연결하는 규칙](adapter-contracts.md) · 다음: [모니터링 제품의 용량과 손실 예산](capacity-and-loss-budgets.md) · [분야 목차](README.md)
