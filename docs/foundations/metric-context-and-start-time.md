# 지표에 남겨야 할 문맥: exemplar와 카운터 시작 시각

> 상태: 검토됨 · 적용 범위: OpenTelemetry Metrics Data Model, OpenMetrics 1.0, Prometheus 3.15.0 기능 문서 · 원천 확인일: 2026-10-05 · 실습 여부: 원천·가상 예시 중심; 연결 실습의 범위는 본문

> **심화 안내:** 처음 읽을 때 건너뛰어도 됩니다. 선수: [시계열](time-series.md), [분포와 집계](distributions.md). 수집·저장 계약을 설계할 때 돌아오세요.

## 먼저 이해할 상황

지연 histogram에서 긴 요청이 보이면 어떤 trace였는지 보고 싶습니다. 한편 새 프로세스의 첫 counter 값이 7이라면 “이번 수집 구간에 7건이 발생했다”라고 더해도 되는지 고민하게 됩니다. 두 문제 모두 값만으로 부족합니다. 첫 문제에는 관측 사건의 연결 정보, 두 번째에는 카운터의 시작 시각과 연속성이 필요합니다.

## Exemplar는 집계값에서 원래 사건으로 가는 연결이다

OTel exemplar는 지표 관측 사건의 값·시각과 문맥을 남깁니다. `trace_id`, `span_id`는 선택 사항이고, 지표 집계에서 필터된 attribute를 보존할 수도 있습니다. histogram의 모든 관측을 저장하는 기능은 아니며 reservoir와 filter 정책으로 일부를 선택합니다. 따라서 exemplar가 없다고 해당 bucket에 관측이 없었던 것은 아닙니다. [데이터 모델](https://opentelemetry.io/docs/specs/otel/metrics/data-model/#exemplars), [SDK exemplar 규약](https://opentelemetry.io/docs/specs/otel/metrics/sdk/#exemplar)

OpenMetrics 1.0의 exemplar는 별도의 label 집합과 값, 선택적인 시각으로 표현합니다. 아래는 **가상 형식 예시**이며 서버에 노출하거나 수집하지 않았습니다. `trace_id`는 bucket 시계열의 label이 아니라 뒤에 붙은 exemplar의 label입니다. [OpenMetrics exemplars](https://prometheus.io/docs/specs/om/open_metrics_spec/#exemplars)

```text
# TYPE demo_request_duration_seconds histogram
demo_request_duration_seconds_bucket{le="1.0"} 20 # {trace_id="11111111111111111111111111111111"} 0.8
demo_request_duration_seconds_bucket{le="+Inf"} 20
demo_request_duration_seconds_count 20
demo_request_duration_seconds_sum 4.2
# EOF
```

여기서 20은 누적 관측 수이고 0.8초는 연결된 한 사건의 값입니다. 이를 “20건 모두가 0.8초”, “p95가 0.8초”로 해석할 수 없습니다. exemplar를 metric point의 일반 label로 펼치면 요청마다 시계열이 늘 수 있습니다. trace 저장 기간·sampling·tenant 권한이 달라 링크를 따라가도 trace가 없을 수 있습니다.

## 시작 시각은 처음 수집한 시각과 다르다

OTel의 `StartTimeUnixNano`와 `TimeUnixNano`는 누적 또는 구간 집계의 범위를 해석하게 합니다. Cumulative sum에서 같은 시작 시각을 유지하는 연속 구간과 reset 이후 새 구간을 구분합니다. 시작을 알 수 없는 첫 점을 실제 0 시작으로 꾸미지 않습니다. `StartTimeUnixNano = TimeUnixNano`인 첫 점은 시작 시각을 모르는 reset을 나타내는 모델이므로 그 첫 값의 전체를 알려진 구간 증가량으로 귀속할 수 없습니다. [reset과 start time](https://opentelemetry.io/docs/specs/otel/metrics/data-model/#resets-and-gaps)

OpenMetrics Counter의 선택적 Created 값은 Unix epoch 이후 **초** 단위이며 text 형식의 `_created`로 표현합니다. OTel의 시작 필드는 epoch 이후 **nanosecond**입니다. Created는 scrape 수행 시각이 아니며, `_created` 시계열이 보인다는 사실만으로 저장·질의 엔진이 이를 counter의 시작 문맥으로 사용한다고 단정하지 않습니다. [OpenMetrics counter](https://prometheus.io/docs/specs/om/open_metrics_spec/#counter), [OTel 변환 규약](https://opentelemetry.io/docs/specs/otel/compatibility/prometheus_and_openmetrics/)

## 계산 예시: 첫 증가분을 어디까지 알 수 있는가

**가상 예시:** 프로세스가 상대 시각 0초에 counter=0으로 시작했고 10초에 7, 20초에 12를 노출했다고 가정합니다.

| 보존한 정보 | 말할 수 있는 것 | 말할 수 없는 것 |
| --- | --- | --- |
| 10초의 7, 20초의 12만 | **그 사이 reset·수명 교체가 없다는 전제에서** 증가량 `12−7=5건`, 평균 `0.5건/초` | 처음 7건의 시작 시각·구간 내 배치; 값 증가만으로 중간 reset 부재를 증명할 수 없음 |
| 실제 0초의 시작과 위 표본 | 연속성이 확인되면 0–20초 총 `12건`, 평균 `0.6건/초` | 각 요청이 발생한 개별 시각 |
| 10초에 발견했으므로 임의의 0을 삽입 | 새로운 가정을 추가한 것 | 0–10초의 실제 기록을 복구했다고 주장할 수 없음 |

이는 두 점 차분의 설명입니다. 실제 PromQL `rate()`·`increase()`는 query window·외삽·reset·사용 기능에 영향을 받으므로 위 산술과 모든 조건에서 같은 값을 반환한다고 주장하지 않습니다. [시계열 계산](time-series.md)

**구현 결론:** exemplar·시작 시각은 원천이 제공하고 전송 형식과 저장 설정이 지원해야 보존됩니다. 도구 이름만으로 연결·reset 처리가 자동 완성된다고 가정하지 않습니다. 아래는 구현자 참고입니다.

## Prometheus의 수용과 질의는 별도 확인한다

**3.15.0 고정 문서 기준** 기능 flag를 구분합니다. 최신 기본값을 추측해 “Prometheus면 자동 해결”로 표현하지 않습니다. 아래 기능은 이번 promtool 규칙 재평가만으로 검증되지 않습니다. 실제 scrape·저장·PromQL 시나리오가 별도로 필요합니다. [v3.15.0 feature flags](https://github.com/prometheus/prometheus/blob/v3.15.0/docs/feature_flags.md)

| 기능 | 의미 | 구현 시 확인할 것 |
| --- | --- | --- |
| `created-timestamp-zero-ingestion` | 제공된 시작 시각에 적절한 0 표본을 삽입하는 방식 | 전역 기본 `scrape_protocols`를 PrometheusProto 우선으로 변경; 명시 설정은 별도 |
| `st-storage` | 표본별 start timestamp를 WAL·TSDB/Agent·Remote Write 2.0으로 보존 | 실험 기능의 저장·복구 호환성 |
| `use-start-timestamps` | `rate`, `irate`, `increase` 등의 질의가 start timestamp를 사용 | 저장 여부와 질의 사용 여부를 별도 점검 |
| `st-synthesis` | 첫 점을 기준으로 빼고 새 시작 문맥을 합성 | 첫 점이 제거되고 raw counter가 바뀜; 잃은 최초 증가분 복구 아님 |

3.15.0의 `created-timestamp-zero-ingestion`이 바꾸는 전역 기본 순서는 `PrometheusProto, OpenMetricsText1.0.0, OpenMetricsText0.0.1, PrometheusText0.0.4`입니다. exporter가 시작 시각을 실제로 노출해야 하며 OpenMetrics의 `_created`가 추가 시계열로 저장되는 비용·불필요한 증가도 확인합니다. [고정 버전 flag 설명](https://github.com/prometheus/prometheus/blob/v3.15.0/docs/feature_flags.md)

Prometheus 3.15.0의 exemplar 수용에는 기본 비활성인 `--enable-feature=exemplar-storage`가 필요합니다. 로컬 조회 저장소는 모든 시계열이 공유하는 **개수 제한 원형 메모리 버퍼**이며 오래된 항목은 새 항목에 밀려납니다. 켜면 WAL에도 기록하지만 그 디스크 지속성은 WAL 보존 범위에 한정됩니다. 따라서 “항상 WAL 기간만큼 조회 가능”이라는 고정 시간 보존 보장은 아닙니다. 일반 TSDB metric 보존 기간과도 다릅니다. Prometheus text 0.0.4는 exemplar를 전달하지 못하므로 OpenMetrics 등 지원 형식과 exporter 출력을 확인합니다. [exemplar flag](https://github.com/prometheus/prometheus/blob/v3.15.0/docs/feature_flags.md#exemplars-storage), [원형 버퍼 구현](https://github.com/prometheus/prometheus/blob/v3.15.0/tsdb/exemplar.go), [노출 형식](https://prometheus.io/docs/instrumenting/exposition_formats/#exemplars-experimental)

서버가 지원해도 exporter·전송 변환이 시작 시각이나 exemplar를 버리면 끝까지 보존되지 않습니다. 반대로 형식에 필드가 있어도 SDK가 넣지 않을 수 있습니다. 기능 설정·도구 버전·지원 형식을 수집 계약에 포함해야 합니다.

## 제품 적용 제안

exemplar는 해당 tenant의 trace 조회로 연결하며 “표본 연결”, “trace 미보존”, “접근 불가”를 구분합니다. 시계열 identity와 exemplar의 사건 identity를 분리합니다. Counter에서는 원천 시작 시각·관측 시각·수명 ID·temporality·시작을 아는지 여부를 보존하고, 초기 증가량을 계산에서 제외했으면 그 경계를 표시합니다.

계측·저장 기능을 켜는 일은 수집 메모리와 보존 비용을 바꿀 수 있습니다. 이 장에서는 기능 flag 설정, 서버 실행, scrape 요청을 수행하지 않았습니다. 가상 형식과 산술만 문서 검사 대상으로 사용합니다.

## 이해 확인

1. exemplar 하나가 histogram의 모든 관측을 대표하는가? **일부 사건의 연결이며 모집단의 분포를 대신하지 않는다.**
2. 처음 본 counter=7을 바로 이번 구간 7건으로 더해도 되는가? **시작 시각과 연속성을 알아야 한다.**
3. `_created`가 저장돼 있으면 모든 `rate()`가 이를 사용했는가? **수용 형식·flag·저장과 질의 동작을 확인해야 한다.**
4. start time 합성이 원래 첫 7건의 발생 시각을 되살리는가? **아니다. 기준점을 새로 정하는 처리다.**

## 함께 읽기

[시계열](time-series.md) · [분포](distributions.md) · [sampling 확률과 추정](../application/trace-sampling-and-context.md) · [전송 계약](../product/telemetry-delivery-contracts.md)

이전: [시계열과 지표의 데이터 모델](time-series.md) · 다음: [평균과 백분위수 및 분포의 집계](distributions.md) · [분야 목차](README.md)
