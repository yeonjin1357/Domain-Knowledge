# 어댑터 계약: 서로 다른 원천을 정확히 연결하는 규칙

> 상태: 검토됨 · 적용 범위: 이 책의 제품 설계 제안과 실행 가능한 참조 예제 · 원천 확인일: 2026-10-06 · 실습 여부: 저장 입력 계약 검사; live 수집 없음

어댑터는 원천의 데이터를 제품의 공통 형식으로 바꾸는 계층입니다. 통합의 목적은 숫자 모양을 같게 만드는 것이 아니라, 같은 의미는 함께 비교하고 다른 의미는 보존하는 것입니다. “usage”라는 이름만 같다고 CPU 시간과 메모리 현재량을 같은 계산에 넣지 않습니다.

## 하나의 관측에 필요한 정보

| 정보 | 설계 예시 | 이유 |
| --- | --- | --- |
| 인증된 관리 범위 | tenant·account·cluster | payload의 주장만으로 접근 경계를 결정하지 않음 |
| 대상 정체성·수명 | source ID, boot ID, process start | 재생성과 재사용 구분 |
| 지표 정의 버전 | 원천 필드·계산 버전 | 의미 변경을 과거 series에 숨기지 않음 |
| 값·단위·유형 | 누적 3,000,000µs | 변환과 집계 규칙 결정 |
| 시간·시간 범위 | 관측 시각, 구간 시작·끝, 수집 시각 | 지연·차분·중복 판정 |
| 품질·capability | known/null/absent, restricted, 원천 오류 | 0과 관측 불가 구분 |

OpenTelemetry의 metric 모델도 Resource·속성·metric 종류·시간적 의미와 집계를 다룹니다. 이 표는 그 wire format을 그대로 복제한 schema가 아니라 제품 저장과 변환의 검토 질문입니다. 실제 OTLP를 구현할 때는 명세에 맞춥니다. [OTel metric data model](https://opentelemetry.io/docs/specs/otel/metrics/data-model/)

## 단위만 바꾸면 되는 경우와 아닌 경우

ns 누적 CPU 시간을 초로 바꾸는 것은 단위 변환입니다. working set을 RSS라고 이름 바꾸는 것은 의미 변경입니다. 동일 범위·수명에서 단위를 바꾼 값과, 서로 다른 계정의 값은 별도로 다룹니다.

예시로 A가 `2,000,000,000ns`, B가 `2,000,000µs`를 보고한다면 둘 다 2 CPU초일 수 있습니다. 하지만 A가 프로세스 자체, B가 자식까지 포함한 cgroup이라면 같은 값이어도 동일한 계정이라고 합치지 않습니다.

## 수집 상태는 서로 다른 축으로 보존한다

값의 가용성, 차분 품질, 접근 가시성, 전송 완료 단계는 독립적입니다. 이 책의 참조 코드가 쓰는 이름을 아래처럼 구분하며 단일 성공/실패 enum으로 합치지 않습니다.

| 축·참조 함수 | 상태 이름 | 해석 |
| --- | --- | --- |
| 값 `nullable_number()` | `known`, `null`, `absent` | 정상 값(0 포함), 명시 NULL, 필드 없음 |
| 가시성 `pg_activity_visibility()` | `visible`, `restricted`, `unknown` | 보이는 상태, 명시 권한 제한, NULL만으로 원인 미확정 |
| 차분 `transform()` | `first`, `ok`, `decrease`, `reset`, `identity_changed`, `definition_changed` | 첫 기준·차분 가능·미확정 감소·수명/정의 경계 |
| 시간·입력 `transform()` | `duplicate`, `conflicting_duplicate`, `out_of_order`, `gap`, `unavailable`, `unsupported_unit`, `invalid` | 중복·충돌·역순·간격·수집/형식 제약 |
| 제한된 wrap `bounded_counter_delta()` | `ok`, `wrap_candidate`, `reset`, `continuity_unknown`, `wrap_count_unknown`, `bound_violated`, `invalid` | 외부 근거가 있어야 wrap 후보의 차분 제공 |
| 시계 품질 `cpu_clock_quality()`의 flag | `single_thread_cpu_over_monotonic`, `monotonic_raw_rate_difference`, `clock_slew_suspected` | 복수 flag 가능; 조정 주체나 외부 정확도 인증 아님 |
| OTLP `otlp_http_response()` | `outcome=hop_success/partial_success/failure` | `retryable`은 별도 boolean. `warning`과 `error_message`도 보존하며 종단 간 저장은 미확정 |
| 선택 watch `selected_watch_delete()` | `selected_membership=removed`, `object_state=present_at_recheck/absent_at_recheck/unknown` | 집합 이탈과 재조회 결과이며 삭제 원인의 증명 아님 |
| 대상 수명 `uid_transition()` | `identity=same/replaced` | `remove_current` boolean은 삭제 event UID가 현재 UID와 같은지 판정 |
| CloudWatch `cloudwatch_page()` | 결과별 `status=Complete/PartialData/InternalError/Forbidden` | `complete` boolean과 요청 최상위 `next_token`을 별도로 보존 |

카탈로그의 `missing.absent/null/zero`는 **필드별 의미 설명**이며 위 품질 코드 자체를 대체하지 않습니다. HTTP 403 같은 원천 오류도 보존한 뒤 가시성·가용성으로 매핑합니다. SQL·Cloud 원천의 NULL을 임의로 `known=0`으로 바꾸지 않습니다. OTLP 성공 응답의 거절 수 생략처럼 프로토콜이 0 기본값을 정한 경우에는 그 규약을 따릅니다. 잘못된 응답 형식은 참조 함수에서 오류로 거부하며 `hop_success`로 만들지 않습니다.

### 전송 단계의 제품 계약

| 제품 단계 이름 | 명시해야 할 완료 경계 |
| --- | --- |
| `Accepted` | 지정한 receiver가 요청을 수용; 메모리 queue인지 함께 기록 |
| `Persisted` | 명시한 저장소·복제·실패 범위의 지속성 조건 완료 |
| `Queryable` | 지정한 조회 경로에서 찾을 수 있음 |
| `Rejected` | 수용하지 않은 항목·사유·재시도 가능 조건 |

수용 이전의 관측도 아래처럼 보존합니다. 이들은 `Accepted`와 같은 완료 상태가 아니라 위치가 다른 처리 증거입니다.

| 수용 전 관측 경계 | 남길 증거 | 아직 보장하지 않는 것 |
| --- | --- | --- |
| agent가 원천을 읽음 | 원천·읽은 시각·수집 결과·입력 수 | gateway 수신, 저장 또는 조회 가능 |
| gateway가 인증·schema 검증을 수행함 | 인증된 tenant·검증 결과·거절 사유·시각 | 메모리 queue나 저장소 수용; 검증 성공만으로 Accepted를 합성하지 않음 |

이는 **제품 적용 제안**이며 OTLP의 wire enum이나 참조 함수의 `quality` 값이 아닙니다. 한 요청이 Accepted여도 그 안의 개별 관측은 null일 수 있습니다. 상태마다 경계·대상·시각을 같이 보존하며 단계 완료를 추정해서 채우지 않습니다. [전송 응답 계약](telemetry-delivery-contracts.md)

## 두 표본 차분의 참조 구현

[adapter_contract.py](../../scripts/adapter_contract.py)의 `transform()`은 누적 정수 카운터를 두 번 관측하는 좁은 학습용 계약입니다. 같은 수명의 monotonic clock 표본만 비교하고, 지원 단위·정체성·정의 버전을 확인합니다. Prometheus `rate()`의 범위 외삽이나 reset 보정 알고리즘을 구현한 것은 아닙니다. [Prometheus rate](https://prometheus.io/docs/prometheus/latest/querying/functions/#rate)

| 입력 상황 | 반환 품질 | 숫자 처리 |
| --- | --- | --- |
| 첫 표본 | first | 기준만 존재, rate 없음 |
| 정상 증가·같은 수명 | ok | 증가량 / 경과 시간 |
| 정상 관측에 증가 없음 | ok | 알려진 0 |
| 원인 미상의 값 감소 | decrease | wrap·reset·오류 구분 전에는 rate 없음 |
| boot 또는 clock 수명 변경 | reset | 확인된 수명 경계, 새 기준 필요 |
| 대상·정의·단위 변경 | 별도 changed 상태 | 기존 차분 중단 |
| 같은 시각·같은 값 | duplicate | 새 rate 생성 안 함 |
| 같은 시각·다른 값 | conflicting_duplicate | 충돌로 남김 |
| 역순·허용 간격 초과 | out_of_order 또는 gap | 자동 보간 안 함 |
| 수집 실패·지원 불가·형식 오류 | 해당 품질 | 0 합성 안 함 |

이 구현은 이전 입력이 이미 검증된 표본이라는 전제를 가집니다. 호출자는 오류 표본으로 기준을 덮지 않고, reset·identity 변경 때 적절히 기준을 바꾸는 상태 관리가 필요합니다. 기존 `transform()` 함수는 diskstats의 32bit wrap 복원을 수행하지 않습니다. 별도 `bounded_counter_delta()`는 연속성과 구간 최대 증가량이 입증된 경우에만 modulo 차분을 계산합니다. 기존 `transform()`은 감소를 재시작 사건으로 확정하지 않고 [필드 폭과 연속성 조건](../host/collection-contracts.md)을 확인하도록 `decrease`로 반환합니다. 수집 사이 reset이 발생했으나 새 누적값이 이전보다 더 커졌고 수명 표식도 없다면 두 숫자만으로 reset을 알아낼 수 없습니다.

## 큰 정수의 차분

64bit 누적값을 binary64 부동소수점으로 먼저 바꾸면 큰 값에서 작은 증가분을 잃을 수 있습니다. 참조 구현은 정수 차분을 먼저 계산한 다음 단위·시간으로 나눕니다. 예를 들어 `2^60→2^60+10`의 10초 증가율은 1/초이며, 이를 검사 입력에 포함했습니다. 실제 저장소가 정수·decimal·float 중 어떤 것을 사용하는지까지 검토해야 합니다.

## 분포 변환은 원래 정보를 보존하기

histogram에는 bucket 경계와 count·sum 등의 일관성이 필요합니다. delta bucket을 누적 bucket으로 바꾸는 정책, temporality 변환 상태, reset, 음수 관측 지원 여부가 정의되어야 합니다. p95 값 하나에서 원래 분포를 복원할 수 없으므로 percentile-only 원천은 합칠 수 있는 histogram인 것처럼 변환하지 않습니다. [OTel histogram](https://opentelemetry.io/docs/specs/otel/metrics/data-model/#histogram)

## 목록 동기화와 삭제

부분 pagination 결과, 접근 거절, timeout은 완전한 목록이 아닙니다. 원천별 scan ID와 완료 상태를 남긴 뒤 삭제 판단에 사용하도록 제안합니다. 삭제 의도, 마지막 관측, 실제 원천 삭제를 서로 다른 상태로 관리하면 일시적인 수집 장애가 topology 전체 삭제로 번지는 것을 막을 수 있습니다.

## 카탈로그 한 행에서 수용 테스트까지

[기계가 읽는 필드 카탈로그](../../catalog/field-catalog.json)는 Linux 29, cgroup v2 10, Kubernetes 9, PostgreSQL 20, MySQL 8, OTLP 6, CloudWatch 5, **총 87개** 계약을 담습니다. 전수 지원 목록이 아니라 정의를 확인한 범위의 참조입니다. [형식·사용 안내](../../catalog/README.md), [스키마](../../catalog/field-catalog.schema.json)를 함께 읽습니다.

```text
필드 ID 선택 → 원천·버전·권한·실행 수명 확인 → 원시 값과 상태 보존
  → 단위·시간·reset 계약 적용 → 값/품질 출력 → fixture의 기대값과 대조
```

가령 MySQL SBS의 XML 숫자 문자열은 `known` 숫자로, `xsi:nil`은 `null`로 읽습니다. IO/SQL 상태·GTID·파일 위치를 별도로 보존해야 0을 원본 전체의 최신성으로 오인하지 않습니다. 카탈로그의 SQL locator는 열을 식별하는 표현으로, 운영용 조회·인증·timeout 코드가 아닙니다.

**종류와 시간 집계는 다른 축**입니다. `kind=counter`와 `temporality=cumulative/delta`를 구분하고, CloudWatch `kind=dynamic`은 조회 정의를 더 알아야 유형을 결정할 수 있다는 뜻입니다. `availability.min_inclusive/max_exclusive`는 검토 범위, `introduced_in/removed_in`은 확인한 도입·제거, `stable_since`는 안정화 시점입니다. 범위 끝을 제품의 실제 제거 버전으로 읽지 않습니다.

[어댑터 fixture](../../labs/fixtures/adapter-r4.json)는 출처 파일·SHA256·추출 위치·기대 결과를 연결합니다. 74개 사례는 실측 입력 29개, 가상 입력 44개, 실측에 제한된 실습 문맥을 더한 1개입니다. 기존 `transform()` 22개를 합친 96개는 **제품 구현 전체가 아니라 계약의 실행 가능한 참조**입니다. 같은 이름의 실제 parser·수집기·인증·저장소를 검증한 인증으로 사용하지 않습니다.

### 무엇을 실제로 관측했는가

| 계약 묶음 | 저장 증거 또는 가상 입력의 범위 |
| --- | --- |
| CPU 시계 품질 | Linux의 MONOTONIC·RAW·CPU clock 원시 표본 |
| NULL·가시성 | MySQL 두 버전 SBS XML, PG 권한 제한·backend_xmin; PG replay_lag는 가상 입력 |
| 객체 수명 | selector 이탈 DELETED와 후속 GET, UID 교체; 404 해석 등은 가상 경계 |
| 전송 | OTLP 부분 거절·중복 수신, Collector retry 진행/소진 snapshot |
| 분포 | promtool이 가상 분포를 계산한 원문 출력; 실제 서비스 지연 분포 아님 |
| wrap·cloud | diskstats/SNMP wrap·CloudWatch·Azure는 가상 계약; 실제 wrap·cloud 호출 미실행 |

추출·검증 명령과 세부 제외 범위는 [검증 기록](../validation.md), [fixture 안내](../../catalog/README.md)에 있습니다. 제품에 적용할 때는 실제 버전의 capability·수집 부하·연결 복구·저장 멱등성을 추가로 검사합니다.

## 이해 확인

1. 수집 실패 뒤 rate=0을 내보내는가? **0과 관측 불가를 구분합니다.**
2. timestamp와 값이 같으면 업무 중복도 없다고 입증되는가? **이 표본의 중복 판단일 뿐 업무 사건의 멱등성 증명은 아닙니다.**
3. 원천에 없는 histogram을 p95 하나로 생성할 수 있는가? **원래 분포 정보가 부족합니다.**

이전: [모니터링 제품 자체의 관측과 접근 경계](self-observation-and-access.md) · 다음: [어댑터를 지원한다고 말하기 전에: 필드 계약과 검증 근거](compatibility-and-acceptance.md) · [분야 목차](README.md)
