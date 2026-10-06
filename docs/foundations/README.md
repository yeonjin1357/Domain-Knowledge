# 모니터링 공통 개념

> 상태: 검토됨 · 적용 범위: 도메인 공통, 일부 Prometheus 예시 · 원천 확인일: 2026-10-03 · 실습 여부: 각 상세 장에 명시

## 먼저 만나는 도구 이름

Prometheus는 지표를 수집하고 시계열로 저장·질의하는 도구이며, **scrape**는 대상 endpoint에서 지표를 읽어 오는 동작입니다. Prometheus의 **exporter**는 다른 원천의 값을 이 방식으로 노출하는 구성 요소입니다. OpenTelemetry(OTel)는 지표·로그·트레이스의 계측과 전송을 위한 규약·도구 모음이고, **OTLP**는 그 데이터를 주고받는 프로토콜입니다. OTel **Collector**는 receiver로 받아 처리한 뒤 exporter로 내보내는 프로세스이므로, 여기의 exporter는 Prometheus exporter와 방향·역할이 다릅니다. [Prometheus 개요](https://prometheus.io/docs/introduction/overview/), [OTel 개념](https://opentelemetry.io/docs/concepts/), [Collector](https://opentelemetry.io/docs/collector/)

명세의 **Stable**은 정해진 호환성 정책 아래 안정된 부분, **Development**는 바뀔 수 있는 개발 단계입니다. 도구 버전이나 실습 통과 여부와는 별개이며 해당 절의 상태를 확인합니다. [OTel 안정성 정책](https://opentelemetry.io/docs/specs/otel/versioning-and-stability/)

통합 모니터링에서 여러 도메인의 데이터를 함께 읽으려면 무엇을, 어디에서, 언제, 어떤 방식으로 관측했는지 알아야 합니다. 이 문서는 도메인별 설명에서 공통으로 사용할 출발점을 정리합니다.

## 관측 데이터의 종류

| 종류 | 의미 | 활용 예시 |
| --- | --- | --- |
| 메트릭 Metrics | 실행 중 측정한 수치 | 요청 수와 메모리 사용량의 변화 |
| 로그 Logs | 발생한 사건에 대한 기록 | 실패 메시지와 처리 문맥 확인 |
| 트레이스 Traces | 요청이 여러 작업을 거치는 경로 | 요청 처리 중 시간이 소요된 구간 확인 |
| 프로파일 Profiles | 코드 수준의 자원 사용 기록 | CPU 시간을 소비하는 함수 조사 |

각 데이터의 정의는 [OpenTelemetry Signals](https://opentelemetry.io/docs/concepts/signals/)를 참고했습니다. 표의 활용 예시는 이 문서의 설명을 위한 것입니다. 실제 수집 가능 여부와 지원 수준은 사용할 도구·계측 방식·버전에서 확인합니다.

## 지표의 값과 형태

Prometheus에서 Counter는 재시작 시 초기화될 수 있는 누적 증가값이고, Gauge는 오르내릴 수 있는 현재값입니다. Histogram은 관측값을 구간별로 집계하는 분포 표현이며, Summary는 관측 수·합계와 설정한 분위수를 제공할 수 있습니다. 이 명칭을 다른 수집 체계의 데이터형과 대응시킬 때는 각 체계의 정의를 확인합니다. [Prometheus Metric types](https://prometheus.io/docs/concepts/metric_types/)

예를 들어 오류 누적 횟수가 1,000이라는 사실만으로 최근 오류가 늘었다고 판단하기는 어렵습니다. 어느 구간에서 얼마나 증가했는지, 같은 구간의 전체 요청은 몇 건인지 함께 정의해야 합니다.

가상 예시로, 같은 완료 시점 기준으로 집계한 5분간 요청 1,000건 중 오류가 20건이면 오류율은 `20 / 1,000 × 100 = 2%`입니다. 오류의 정의, 대상 요청의 범위, 재시도 포함 여부는 이 계산을 사용하는 제품에서 정해야 합니다.

## 집계 시 주의할 점

인스턴스별 p95를 단순 평균해 전체 요청의 p95로 표시하면 안 됩니다. 전체 분포를 합칠 수 있는 원천 데이터를 사용하고, 히스토그램이라면 구간의 호환성과 집계 방식을 확인해야 합니다. [Prometheus Histograms and summaries](https://prometheus.io/docs/practices/histograms/)

다음은 이 프로젝트에서 지표 문서를 작성할 때 확인할 항목입니다.

| 확인 항목 | 문서에서 답할 질문 |
| --- | --- |
| 대상 | 호스트 전체, CPU 하나, 컨테이너, 프로세스 중 무엇인가? |
| 측정 위치 | 요청을 보낸 쪽인가, 처리한 쪽인가? |
| 단위와 분모 | 초인가 밀리초인가? 비율의 기준은 용량인가 설정 한도인가? |
| 시간 | 순간값인가 누적값인가? 어느 시간 구간을 집계했는가? |
| 집계 | 합계·평균·최댓값·분위수 중 무엇이며 왜 적절한가? |
| 수집 상태 | 값이 없는 것인가, 0인가, 이전 값이 남아 있는가? |

## 제품 적용 제안

이 저장소에서는 측정값과 함께 관측 시각, 수집 시각, 수집 성공 여부, 대상 식별 정보를 기록하는 방향을 제안합니다. 실제 저장 형식은 제품 설계 시 결정합니다.

화면에서는 데이터가 없는 상황을 자동으로 0이나 정상 상태로 바꾸지 않고, 수집 상태를 확인할 수 있게 합니다. 서로 다른 도메인의 그래프를 비교할 때는 조회 시간 구간과 집계 간격을 맞추는 기능을 검토합니다.

## 상세 본문

1. [처음 읽는 시스템 지도: 요청 하나가 지나가는 길](system-map.md)
2. [시계열과 지표의 데이터 모델](time-series.md)
3. [지표에 남겨야 할 문맥: exemplar와 카운터 시작 시각](metric-context-and-start-time.md)
4. [평균과 백분위수 및 분포의 집계](distributions.md)
5. [분포를 저장하는 방법: 지수 버킷, native histogram과 sketch](histogram-storage.md)
6. [성능을 읽는 순서: 처리량, 대기열, 표본과 실험](performance-and-statistics.md)
7. [서비스 수준 지표와 오류 예산](service-level-objectives.md)
8. [시간과 관측 데이터의 품질](time-and-data-quality.md)
9. [숫자가 다를 때: 측정 경계, 시간 구간과 오차](measurement-and-comparability.md)
10. [트레이스와 로그 및 프로파일의 연결](traces-logs-profiles.md)
11. [분산 시스템: 복제, 합의, 시간과 불확실한 결과](distributed-systems.md)

관련 문서: [지표 명세 템플릿](../../templates/metric.md), [도메인 간 장애 분석](../cross-domain/README.md)

이전: [제1.2판의 범위와 사실 확인 원칙](../scope.md) · 다음: [처음 읽는 시스템 지도: 요청 하나가 지나가는 길](system-map.md)
