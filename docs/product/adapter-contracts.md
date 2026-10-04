# 어댑터 계약: 서로 다른 원천을 정확히 연결하는 규칙

> 상태: 검토됨 · 적용 범위: 이 책의 제품 설계 제안과 실행 가능한 참조 예제 · 검토일: 2026-10-04 · 사용자 제품에 구현된 기능을 뜻하지 않음

어댑터는 원천의 데이터를 제품의 공통 형식으로 바꾸는 계층입니다. 통합의 목적은 숫자 모양을 같게 만드는 것이 아니라, 같은 의미는 함께 비교하고 다른 의미는 보존하는 것입니다. “usage”라는 이름만 같다고 CPU 시간과 메모리 현재량을 같은 계산에 넣지 않습니다.

## 하나의 관측에 필요한 정보

| 정보 | 설계 예시 | 이유 |
| --- | --- | --- |
| 인증된 관리 범위 | tenant·account·cluster | payload의 주장만으로 접근 경계를 결정하지 않음 |
| 대상 정체성·수명 | source ID, boot ID, process start | 재생성과 재사용 구분 |
| 지표 정의 버전 | 원천 필드·계산 버전 | 의미 변경을 과거 series에 숨기지 않음 |
| 값·단위·유형 | 누적 3,000,000µs | 변환과 집계 규칙 결정 |
| 시간·시간 범위 | 관측 시각, 구간 시작·끝, 수집 시각 | 지연·차분·중복 판정 |
| 품질·capability | ok, forbidden, unsupported | 0과 관측 불가 구분 |

OpenTelemetry의 metric 모델도 Resource·속성·metric 종류·시간적 의미와 집계를 다룹니다. 이 표는 그 wire format을 그대로 복제한 schema가 아니라 제품 저장과 변환의 검토 질문입니다. 실제 OTLP를 구현할 때는 명세에 맞춥니다. [OTel metric data model](https://opentelemetry.io/docs/specs/otel/metrics/data-model/)

## 단위만 바꾸면 되는 경우와 아닌 경우

ns 누적 CPU 시간을 초로 바꾸는 것은 단위 변환입니다. working set을 RSS라고 이름 바꾸는 것은 의미 변경입니다. 동일 범위·수명에서 단위를 바꾼 값과, 서로 다른 계정의 값은 별도로 다룹니다.

예시로 A가 `2,000,000,000ns`, B가 `2,000,000µs`를 보고한다면 둘 다 2 CPU초일 수 있습니다. 하지만 A가 프로세스 자체, B가 자식까지 포함한 cgroup이라면 같은 값이어도 동일한 계정이라고 합치지 않습니다.

## 두 표본 차분의 참조 구현

[adapter_contract.py](../../scripts/adapter_contract.py)는 누적 정수 카운터를 두 번 관측하는 좁은 학습용 계약입니다. 같은 수명의 monotonic clock 표본만 비교하고, 지원 단위·정체성·정의 버전을 확인합니다. Prometheus `rate()`의 범위 외삽이나 reset 보정 알고리즘을 구현한 것은 아닙니다. [Prometheus rate](https://prometheus.io/docs/prometheus/latest/querying/functions/#rate)

| 입력 상황 | 반환 품질 | 숫자 처리 |
| --- | --- | --- |
| 첫 표본 | first | 기준만 존재, rate 없음 |
| 정상 증가·같은 수명 | ok | 증가량 / 경과 시간 |
| 정상 관측에 증가 없음 | ok | 알려진 0 |
| 값 감소·boot 또는 clock 수명 변경 | reset | 이번 rate 없음, 새 기준 필요 |
| 대상·정의·단위 변경 | 별도 changed 상태 | 기존 차분 중단 |
| 같은 시각·같은 값 | duplicate | 새 rate 생성 안 함 |
| 같은 시각·다른 값 | conflicting_duplicate | 충돌로 남김 |
| 역순·허용 간격 초과 | out_of_order 또는 gap | 자동 보간 안 함 |
| 수집 실패·지원 불가·형식 오류 | 해당 품질 | 0 합성 안 함 |

이 구현은 이전 입력이 이미 검증된 표본이라는 전제를 가집니다. 호출자는 오류 표본으로 기준을 덮지 않고, reset·identity 변경 때 적절히 기준을 바꾸는 상태 관리가 필요합니다. 수집 사이 reset이 발생했으나 새 누적값이 이전보다 더 커졌고 수명 표식도 없다면 두 숫자만으로 reset을 알아낼 수 없습니다.

## 큰 정수의 차분

64bit 누적값을 binary64 부동소수점으로 먼저 바꾸면 큰 값에서 작은 증가분을 잃을 수 있습니다. 참조 구현은 정수 차분을 먼저 계산한 다음 단위·시간으로 나눕니다. 예를 들어 `2^60→2^60+10`의 10초 증가율은 1/초이며, 이를 검사 입력에 포함했습니다. 실제 저장소가 정수·decimal·float 중 어떤 것을 사용하는지까지 검토해야 합니다.

## 분포 변환은 원래 정보를 보존하기

histogram에는 bucket 경계와 count·sum 등의 일관성이 필요합니다. delta bucket을 누적 bucket으로 바꾸는 정책, temporality 변환 상태, reset, 음수 관측 지원 여부가 정의되어야 합니다. p95 값 하나에서 원래 분포를 복원할 수 없으므로 percentile-only 원천은 합칠 수 있는 histogram인 것처럼 변환하지 않습니다. [OTel histogram](https://opentelemetry.io/docs/specs/otel/metrics/data-model/#histogram)

## 목록 동기화와 삭제

부분 pagination 결과, 접근 거절, timeout은 완전한 목록이 아닙니다. 원천별 scan ID와 완료 상태를 남긴 뒤 삭제 판단에 사용하도록 제안합니다. 삭제 의도, 마지막 관측, 실제 원천 삭제를 서로 다른 상태로 관리하면 일시적인 수집 장애가 topology 전체 삭제로 번지는 것을 막을 수 있습니다.

## 검증과 제품 적용 제안

[verify_contracts.py](../../scripts/verify_contracts.py)는 정상 단위 변환, 0, 리셋, 큰 정수, 중복, 역순, 누락 등 22가지 사례를 실행합니다. 이 검사는 학습용 계약의 동작을 검증하며 실제 Linux·SNMP·DB 어댑터 전체를 검증한 기록이 아닙니다. 원천별 계약은 [호스트](../host/collection-contracts.md), [SNMP](../network/snmp-and-device-models.md), [DB](../database/collection-contracts.md)에 있습니다.

## 이해 확인

1. 수집 실패 뒤 rate=0을 내보내는가? **0과 관측 불가를 구분합니다.**
2. timestamp와 값이 같으면 업무 중복도 없다고 입증되는가? **이 표본의 중복 판단일 뿐 업무 사건의 멱등성 증명은 아닙니다.**
3. 원천에 없는 histogram을 p95 하나로 생성할 수 있는가? **원래 분포 정보가 부족합니다.**
