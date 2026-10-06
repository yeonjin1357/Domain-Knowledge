# 분포를 저장하는 방법: 지수 버킷, native histogram과 sketch

> 상태: 검토됨 · 범위: OTel ExponentialHistogram Stable 데이터 모델·Development 변환 절, Prometheus 3.13.4·3.15.0, DDSketch·t-digest · 3d 원천·저장 증거 확인: 2026-10-06 · promtool은 Claude가 2026-10-05 실행

## p99만 저장하면 나중에 질문을 바꿀 수 없다

오늘은 서비스별 p99가 필요하지만 내일은 전체 서비스의 300 ms 이하 비율이 필요할 수 있습니다. p99 숫자만 남기면 이 질문에 답할 분포가 사라집니다. 모든 요청을 저장하기에는 비용이 커서, 버킷이나 작은 요약 자료구조인 **sketch**에 관측값들을 모읍니다. 저장 크기를 줄이는 대신 어떤 오차를 허용하고 무엇을 합칠 수 있는지 정해야 합니다. 기본 평균·백분위수 계산은 [분포의 집계](distributions.md)를 먼저 읽습니다.

## OTel ExponentialHistogram: 값이 커질수록 버킷도 넓어진다

명시적 경계 Histogram이 `0.1, 0.2, 0.5초` 같은 경계를 나열한다면 ExponentialHistogram은 `scale`로 경계 배율을 정합니다. **값의 단위는 metric의 단위**이고 scale 자체에는 초·바이트 단위가 없습니다. 양수 버킷 index i의 범위는 `(base^i, base^(i+1)]`입니다. 음수는 절댓값을 같은 방식으로 분류해 별도의 배열에 담습니다. [OTel 데이터 모델](https://opentelemetry.io/docs/specs/otel/metrics/data-model/#exponentialhistogram)

```text
base = 2^(2^(-scale))
예시: scale=0 → base=2 → (1,2], (2,4], (4,8] …
예시: scale=1 → base=√2 ≈ 1.414214 → 1에서 2 사이에 버킷 2개
```

`zero_count`는 절댓값이 `zero_threshold` 이하인 관측을 셉니다. zero bucket을 “실제로 0인 요청 수”로만 해석하지 않습니다. positive/negative의 `offset`과 연속 `bucket_counts` 배열은 누적 `le` 값이 아닌 **각 버킷의 개수**입니다. 전체 개수·합계·시간 구간·temporality도 따로 보존합니다. [OTLP ExponentialHistogramDataPoint](https://github.com/open-telemetry/opentelemetry-proto/blob/v1.11.1/opentelemetry/proto/metrics/v1/metrics.proto)

scale을 1단계 낮추면 인접 버킷을 합쳐 더 거친 분포를 만들 수 있습니다. 이때 원래 개수가 다른 경계로 잘못 배분되는 오차 없이 재배치됩니다(perfect subsetting). 하지만 작은 버킷들의 차이는 사라지므로 **분위수의 정밀도가 그대로 유지된다는 뜻은 아닙니다**. 다른 zero threshold끼리 합칠 때에도 더 넓은 zero 영역에 맞추며 필요하면 채워진 버킷의 경계까지 넓혀야 합니다. [scale 축소](https://opentelemetry.io/docs/specs/otel/metrics/data-model/#exponential-scale), [zero 병합](https://opentelemetry.io/docs/specs/otel/metrics/data-model/#zero-count-and-zero-threshold)

## Prometheus native histogram: 전송·저장 단위도 달라진다

Classic Histogram은 버킷마다 별도 float 시계열을 둡니다. Native Histogram은 한 표본에 count·sum·버킷을 담습니다. 표준 exponential schema의 유효 범위는 −4~8이며, 값이 클수록 촘촘합니다. custom bucket schema −53(NHCB)은 명시한 경계를 담습니다. “native”가 항상 exponential이라는 뜻은 아닙니다. [Native histogram 명세](https://prometheus.io/docs/specs/native_histograms/#schema)

수신기는 schema 9~52를 −4~8의 유효 schema로 낮춰 받을 수 있습니다(MAY). Prometheus는 3.7.0부터 높은 schema의 수신 해상도를 줄이는 처리를 지원합니다. 이 허용을 “9~52가 그대로 저장되는 표준 schema”라고 설명하지 않습니다. [수신 schema 규약](https://prometheus.io/docs/specs/native_histograms/#schema), [3.7 변경 기록](https://github.com/prometheus/prometheus/blob/v3.15.0/CHANGELOG.md)

OTel scale과 Prometheus 표준 schema의 해상도는 대응하지만 **버킷 index는 1만큼 다릅니다**. Prometheus index n의 경계는 OTel index n−1에 대응합니다. OTLP의 dense 배열과 Prometheus의 sparse span 표현도 다릅니다. OTel→Prometheus의 **Exponential Histograms 변환 절은 확인일 현재 Development**이며 scale > 8이면 허용 범위로 downscale을 권고(SHOULD), scale < −4 또는 변환 불가능한 표본은 폐기(MUST)하도록 규정합니다. 반대 방향 변환 절의 Stable 표시나 데이터 모델의 안정 상태와 혼동하지 않습니다. 변환의 count·경계·부호·zero 영역·temporality와 손실 여부를 검증합니다. [OTel→Prometheus 변환 규약](https://opentelemetry.io/docs/specs/otel/compatibility/prometheus_and_openmetrics/#exponential-histograms)

### 기능 상태와 실제 수집 설정

Prometheus **3.8.0**은 native histogram을 stable이지만 선택적으로 켜는 기능으로 발표하며 `scrape_native_histograms`를 도입했습니다. **3.9.0**은 실험 상태 해제와 옛 feature flag의 no-op 처리를 명시합니다. 따라서 안정화의 시작을 3.9 하나로만 표시하지 않습니다. 이번 고정 대상 3.13.4·3.15.0에서 `--enable-feature=native-histograms`는 기능을 켜는 스위치가 아니라 no-op입니다. 서버의 scrape 설정과 원천의 노출 형식을 별도로 확인합니다. [3.8·3.9 변경 기록](https://github.com/prometheus/prometheus/blob/v3.15.0/CHANGELOG.md), [3.13.4 flag 처리](https://github.com/prometheus/prometheus/blob/v3.13.4/cmd/prometheus/main.go), [3.15.0 flag 처리](https://github.com/prometheus/prometheus/blob/v3.15.0/cmd/prometheus/main.go)

| 두 고정 버전의 설정 | 기본값 | 의미 |
| --- | --- | --- |
| `scrape_native_histograms` | false | 원천이 노출한 native 부분 수집; 프로토콜 협상도 확인 |
| `convert_classic_histograms_to_nhcb` | false | classic 경계를 유지하는 custom bucket native 형식으로 변환 |
| `always_scrape_classic_histograms` | false | native 수집·변환과 함께 원천 classic 부분도 추가로 수집 |

NHCB 변환은 **이미 잃은 버킷 내부의 원본 값을 복원하지 않습니다**. 같은 관측을 classic과 native로 함께 저장했으면 요청 수를 둘 다 더하지 않습니다. 위 설정은 서버 scrape 동작이며, promtool 단위 테스트가 통과했다는 사실만으로 exporter·scrape·remote write 경로까지 확인했다고 말할 수 없습니다. [3.13.4 구성](https://github.com/prometheus/prometheus/blob/v3.13.4/docs/configuration/configuration.md), [3.15.0 구성](https://github.com/prometheus/prometheus/blob/v3.15.0/docs/configuration/configuration.md)

## 같은 버킷 개수라도 보간 가정이 다르다

`histogram_quantile`은 classic과 custom bucket native에서 버킷 안을 선형 보간합니다. 표준 exponential native의 0이 아닌 버킷에서는 로그 공간에서 균등하다는 가정으로 지수 보간하며, zero bucket은 선형 보간합니다. `histogram_fraction`도 경계 사이를 추정할 때 같은 보간 방식을 씁니다. [Prometheus 3.15 함수 정의](https://github.com/prometheus/prometheus/blob/v3.15.0/docs/querying/functions.md#histogram_quantile)

다음은 **실측이 아닌 계산 예시**입니다. 양수 값 1.25·1.75·2.5·3.5초를 count=4, sum=9초, `(1,2]` 2개·`(2,4]` 2개로 집계합니다. classic 누적 버킷은 `le=1:0`, `le=2:2`, `le=4:4`, `le=+Inf:4`이며, native는 schema 0을 사용한다고 가정합니다.

| 질문 | classic 선형 보간 | 표준 native 지수 보간 |
| --- | --- | --- |
| p25 | 1 + (2−1)×1/2 = **1.5초** | 1×(2/1)^(1/2) = **√2 ≈ 1.414214초** |
| `(1,1.5]`의 추정 비율 | (2/4)×(1.5−1)/(2−1) = **0.25** | (2/4)×log₂(1.5) ≈ **0.292481** |

원래 표본의 `(1,1.5]` 비율은 1/4입니다. native의 값이 다른 것은 이 구간에서의 보간 가정 때문입니다. 더 조밀한 버킷은 오차를 줄일 수 있지만 특정 데이터에서 항상 더 정확하다는 보장은 아닙니다. `histogram_count`는 native 표본의 count를 읽으며, classic float 버킷을 넣으면 무시합니다. classic에서는 `_count` 또는 누적 `+Inf`를 사용합니다. 이 예시 산술은 `verify_examples`에 연결합니다. [fraction·count 정의](https://github.com/prometheus/prometheus/blob/v3.15.0/docs/querying/functions.md#histogram_fraction)

## Sketch: 무슨 오차를 보장하는가

| 방식 | 압축하는 방법 | 보장과 한계 |
| --- | --- | --- |
| DDSketch | 상대 크기에 맞춘 로그 버킷 | 양수 분위수 값 x에 대해 추정값의 상대 오차를 제한; 순위 오차와 구분 |
| t-digest | 가까운 표본을 가중 centroid로 합치되 꼬리 쪽을 세밀하게 유지 | 병합 가능하고 꼬리 정확도를 목표로 함; 모든 입력에 동일한 상대 오차 상한을 보장한다고 쓰지 않음 |

DDSketch의 상대 오차 α는 값 기준 `|추정값−x|/x`입니다. **예시:** x=100 ms, α=0.01이면 해당 보장 범위는 99~101 ms입니다. 이것은 p99가 p98~p100 사이로 움직인다는 뜻이 아닙니다. 메모리 한도를 위해 낮거나 높은 버킷을 collapse하는 구현은 합쳐진 영역까지 같은 오차 보장을 적용하지 않습니다. 병합 시에는 같은 mapping·오차 설정과 collapse 정책을 확인합니다. [원 논문](https://arxiv.org/abs/1908.10693), [저자 구현의 보장과 제한](https://github.com/DataDog/sketches-py)

t-digest는 압축 정도·입력 분포·병합 과정에 따른 정확도를 실제 데이터로 검증해야 합니다. centroid 크기의 불변식과 분위수 추정의 보편적인 오차 상한은 다른 주장입니다. 원 프로젝트도 GK·KLL 같은 엄격한 보장과의 차이를 설명합니다. 따라서 “병합 가능”을 “병합 순서와 무관하게 완전히 같은 결과”로 번역하지 않습니다. [t-digest 원 프로젝트](https://github.com/tdunning/t-digest), [설계 논문](https://arxiv.org/abs/1902.04023)

## 제품 적용 제안

1. SLO처럼 정확히 판정해야 할 경계가 있으면 해당 경계를 직접 세는 explicit bucket 또는 별도 good/total counter를 검토합니다. 분포에서 임의 경계 비율을 추정한 값에는 추정임을 표시합니다.
2. 지연 범위가 매우 넓으면 exponential 형식의 해상도·최대 버킷 수·zero threshold를 함께 정합니다. 압축 비율은 데이터 분포와 label 수에 따라 측정합니다.
3. 합치기 전에 단위, 관측 대상, 시간 구간, counter reset, sampling 조건이 호환되는지 검사합니다. 형식이 호환되어도 중복 관측을 합치면 틀립니다.
4. 수집·저장·조회·장기 집계의 모든 경로에서 형식 지원과 해상도 축소를 기록합니다. 결과 옆에 count와 보간 방식, 실제 보존 해상도를 보여 줍니다.

**합성 입력의 실행 결과:** Claude가 2026-10-05 실행한 promtool 3.13.4·3.15.0은 위 분포를 표현한 fixture에서 모두 classic p25=1.5, 표준 native p25=1.414213562373095를 반환했습니다. fraction은 각각 0.25와 0.29248125036057815, count는 4였습니다. NHCB는 같은 경계의 classic과 같은 선형 보간 결과를 냈고, classic float 입력에 `histogram_count`를 적용한 결과는 빈 벡터였습니다. fixture의 `classic_count_ignored=0`은 그 **빈 결과 벡터의 길이**이며 원래 관측 수가 0이라는 뜻은 아닙니다. [실행 요약·gzip 목록](../../labs/results/1.1-r3/histograms.json), [입력·판정식](../../labs/review-r3/histograms/fixture.json)

두 버전의 계산을 뒷받침하는 결과이며 실제 요청 분포, 서버 scrape·remote write, OTel 변환 경로까지 검증한 자료는 아닙니다. 모든 숫자와 입력 hash·원자료는 `verify_review_r3 --published`에서 재검사합니다.

## 이해 확인

1. scale을 낮춰 정확히 버킷을 합쳤으면 p99도 그대로인가? **개수 재배치는 정확해도 세부 경계가 사라져 분위수 추정이 달라질 수 있습니다.**
2. classic을 NHCB로 바꾸면 버킷 안의 원래 값들을 복원하는가? **아닙니다. 표현을 바꾸어도 잃은 정보는 돌아오지 않습니다.**
3. DDSketch의 1% 오차와 분위수 순위 1% 오차는 같은가? **값의 상대 오차와 순위 오차는 다릅니다.**
4. promtool 테스트 성공이 운영 scrape 지원을 보증하는가? **서버 설정·노출 형식·전송·저장 경로를 별도로 검증해야 합니다.**

관련: [분포의 집계](distributions.md), [관측 데이터의 시작 시각](metric-context-and-start-time.md), [저장과 조회](../product/storage-and-query.md)
