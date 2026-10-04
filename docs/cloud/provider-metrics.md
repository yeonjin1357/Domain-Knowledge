# 클라우드 지표의 기간, 통계와 정규화

> 상태: 검토됨 · 적용 범위: CloudWatch·Azure Monitor·Cloud Monitoring · 출처 확인일: 2026-10-03 · 편집 검토일: 2026-10-04

## 먼저 이해할 것

클라우드가 제공하는 지표는 이미 정해진 시간 구간으로 집계된 값일 수 있습니다. 1분간 byte 합계는 서버 시작 이후의 누적 byte counter와 다릅니다. 원천의 통계 종류·시간 간격·차원을 확인한 뒤 초당 값이나 전체 평균으로 변환합니다.

클라우드에서 받은 숫자는 이미 일정 기간으로 집계된 값일 수 있습니다. 누적 카운터처럼 다시 rate를 적용하거나 평균을 무조건 더하면 잘못된 결과를 얻습니다.

## 공급자별 메타데이터

CloudWatch에서는 namespace·metric name·dimension을 구분하고 period에 대해 Sum·Average·SampleCount 등의 통계를 선택합니다. 같은 이름이라도 dimension 조합이 다르면 다른 시계열입니다. [CloudWatch Metrics Concepts](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html)

Azure Monitor의 time granularity와 aggregation은 시간 구간의 데이터를 요약하는 방식을 결정합니다. 합·평균·최대 등은 서로 다른 질문이며 null과 0의 해석도 구분해야 합니다. [Azure Metrics Aggregation](https://learn.microsoft.com/en-us/azure/azure-monitor/metrics/metrics-aggregation-explained)

Google Cloud Monitoring은 GAUGE·DELTA·CUMULATIVE의 metric kind와 값의 유형을 구분합니다. 단순 숫자와 distribution도 같은 저장 형태가 아닙니다. [Google Cloud Metric Kinds and Types](https://docs.cloud.google.com/monitoring/api/v3/kinds-and-types)

## 두 번 미분하지 않는다

합성 예로 제공 API가 60초 동안 발생한 요청의 Sum=1,200을 돌려줬다면 그 구간 평균 요청률은 20/s입니다. 다음 구간의 Sum=900과 차분해 `−300/60`을 요청률로 계산하면 틀립니다. 두 값은 각 구간의 건수이지 서버 시작 이후 누적 건수가 아니기 때문입니다.

반면 원천이 시작 이후 누적 카운터라면 [초기화를 고려한 rate](../foundations/time-series.md)를 사용합니다. 이름에 count가 들어 있다는 이유만으로 유형을 정하지 않습니다.

## 이미 집계된 평균 합치기

가상의 두 구간에 다음 통계가 있습니다.

| 구간 | 평균 지연 | 표본 수 | 시간 합 |
| --- | ---: | ---: | ---: |
| A | 10 ms | 900 | 9,000 ms |
| B | 100 ms | 100 | 10,000 ms |

전체 평균은 `(9,000+10,000)/(900+100) = 19 ms`입니다. 구간 평균의 단순 평균 55 ms가 아닙니다. 백분위는 이 방법으로도 합칠 수 없으며 원본 분포의 집계 가능성을 확인해야 합니다.

## 정렬과 시계열 간 집계

Cloud Monitoring은 개별 시계열을 시간 구간으로 정렬하는 alignment와 여러 시계열을 합치는 reduction을 구분합니다. 시간 경계를 맞춘 뒤 시계열을 합쳐야 합니다. [Google Cloud Aggregation](https://docs.cloud.google.com/monitoring/api/v3/aggregation)

제품에서는 원천 period, 통계 유형, 시간 경계, 원천·수신 시각을 보존하고 자체 downsampling의 결과와 구별하는 설계를 제안합니다. 서로 다른 1분 경계의 최대값을 섞어 “동시에 발생한 전체 최대”로 표시하지 않습니다.

## 에이전트 지표와 공급자 지표

CloudWatch agent는 OS 내부의 CPU·메모리·디스크 등 지표를 수집할 수 있습니다. 이것은 공급자 기본 지표와 별도 수집 경로입니다. 두 경로의 이름이 비슷해도 측정 범위·구간을 비교해야 합니다. [CloudWatch Agent Metrics](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/metrics-collected-by-CloudWatch-agent.html)

VM의 내부 파일시스템과 클라우드 블록 볼륨은 다른 계층입니다. 에이전트가 없는 환경에서 내부 메모리나 프로세스 지표를 원천 API가 제공한다고 추정하지 않습니다.

## 수집 명세의 최소 항목

다음은 제품용 제안입니다.

```text
원천 metric ID, dimension/resource labels
kind와 value type, unit
period와 statistic 또는 aligner/reducer
원천 timestamp의 의미
가용 지연, 재조회·중복 제거 방식
지원 범위와 권한, 결측 상태
```

지연 도착한 표본을 다시 조회하는 창은 원천 동작에 맞춰 정하고 같은 표본을 두 번 더하지 않습니다. 숫자의 정규화뿐 아니라 집계 의미의 정규화가 필요합니다.

## 이해 확인

1. 분당 Sum을 다음 분 Sum과 차분하면 요청률인가? **각 구간 건수라면 기간으로 나눠야 합니다.**
2. 표본 수가 다른 평균을 같은 가중치로 합쳐도 되는가? **표본 수가 필요합니다.**
3. 공급자 지표와 에이전트 지표는 자동으로 동일한가? **범위·구간·정의를 비교해야 합니다.**

다음: [관리형·서버리스](managed-and-serverless.md) · [클라우드 목차](README.md)
