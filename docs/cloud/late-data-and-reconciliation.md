# 늦게 도착하는 클라우드 지표: 재조회, 부분 결과와 중복 집계

> 상태: 검토됨 · 적용 범위: CloudWatch GetMetricData·PutMetricData, Azure·Google Cloud의 연결된 집계 규약 · 원천 확인일: 2026-10-06 · 실습 여부: 원천·가상 예시 중심; 연결 실습의 범위는 본문

## 먼저 이해할 것

오늘 받은 지난달 청구서가 지난달에 지출이 없었다는 사실을 바꾸는 것은 아닙니다. 사건의 시각과 자료를 받은 시각이 다르다는 뜻입니다. 클라우드 지표도 원천이 측정한 시각, 게시된 시각, 제품이 받아 저장한 시각을 구분해야 합니다.

이 장은 [공급자 지표의 집계](provider-metrics.md)에서 배운 period·statistic을 수집기의 재조회 정책으로 연결합니다. 아래 수치는 학습용 합성 입력이며 실제 AWS·Azure·Google Cloud의 응답 기록이 아닙니다.

## 조회 성공과 결과 완전성

CloudWatch GetMetricData 응답에는 여러 `MetricDataResult`가 들어갈 수 있습니다. 개별 결과의 `StatusCode`는 Complete·PartialData·InternalError·Forbidden을 구분합니다. 전체 HTTP 요청의 성공만 확인하고 각 결과를 모두 완전한 것으로 처리하면 안 됩니다. [MetricDataResult](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_MetricDataResult.html)

| 원천 결과 | 수집기가 보존할 정보 | 하지 않을 변환 |
| --- | --- | --- |
| Complete | 요청 범위와 시점, 반환된 표본 | 미래의 늦은 게시까지 영원히 완료됐다고 단정 |
| PartialData | 결과별 미완료 상태와 받은 구간, 응답 최상위 NextToken | 누락 구간을 0으로 채움 |
| InternalError | 오류·재시도 상태 | 이미 받은 값 전체를 실제 0으로 덮음 |
| Forbidden | 원천 상태값·Messages·요청 문맥; 권한 원인은 추가 확인 | 지표 미사용 또는 대상 없음으로 표시 |

`NextToken`은 개별 `MetricDataResult`의 필드가 아니라 **GetMetricData 응답 최상위의 요청 단위 token**입니다. 원래 요청의 다음 결과 묶음을 받는 데 사용하며 특정 metric만의 token으로 저장하지 않습니다. `Forbidden`은 이 API 문서에 유효 값으로 열거되어 있지만 구체적인 발생 원인이 정의되어 있지 않습니다. 권한 문제는 조사할 가설로 남기고 상태·Messages를 보존합니다. [GetMetricData 응답 구조](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_GetMetricData.html)

PartialData에서 응답 최상위 NextToken으로 이어 받을 수 있지만 metric math 표현식 등에서는 token이 없는 경우도 있습니다. “token이 없으면 모든 결과가 완전하다”는 단일 규칙을 만들지 않습니다.

**단위는 응답 숫자만으로 복원하지 않습니다.** `MetricDataResult`에는 `Unit` 필드가 없으며, GetMetricData에서 요청 Unit을 생략하면 게시된 여러 unit의 데이터가 반환될 수 있고 단위 변환도 수행하지 않습니다. **제품 적용 제안:** 직접 metric을 조회하는 `MetricStat.Unit`을 원하는 단위로 지정하고 요청 정의와 함께 보존합니다. API 자체에서 Unit은 선택 사항입니다. metric math는 식의 단위를 따로 정의해야 합니다. [GetMetricData 단위 규약](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_GetMetricData.html), [MetricDataResult 필드](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_MetricDataResult.html)

## Timestamps와 Values는 쌍이다

MetricDataResult의 `Timestamps[x]`에 대응하는 값은 `Values[x]`입니다. 두 배열을 각각 독립적으로 정렬하면 시간과 값이 잘못 연결됩니다. 먼저 쌍으로 묶고 그 쌍을 정렬하거나 저장합니다. 반환 순서도 요청의 ScanBy와 실제 API 계약을 확인합니다. [GetMetricData](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_GetMetricData.html)

**가상 응답:** timestamp 배열이 `[10:02, 10:00, 10:01]`, 값 배열이 `[30, 10, 20]`이면 정렬 후 쌍은 `(10:00,10)`, `(10:01,20)`, `(10:02,30)`입니다. timestamp만 정렬해 첫 값 30을 10:00에 붙이면 다른 시계열을 만든 셈입니다.

## 시간 범위의 포함 관계

CloudWatch GetMetricData의 StartTime은 포함, EndTime은 제외입니다. 또한 시작 시각의 정렬·반올림과 데이터 나이에 따른 period 제약을 확인해야 합니다. 이 규칙을 다른 공급자 API의 시간 경계에도 자동 적용하지 않습니다. [GetMetricData 시간 규약](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_GetMetricData.html)

제품 내부에서 `[시작, 끝)`처럼 시간 창을 정했다면 어댑터가 원천 경계와의 변환을 책임지도록 제안합니다. 경계가 어긋나면 인접 조회 사이 표본이 빠지거나 중복될 수 있습니다.

## 지난 구간을 다시 받으면 더할까, 바꿀까

**가상 예시:** 아래 원천은 각 1분 구간의 요청 수 Sum을 반환한다고 정의합니다. 누적 counter가 아니며, 재조회 값은 같은 구간의 갱신된 집계입니다.

| 구간 시작 | 첫 조회 | 늦은 자료 반영 후 재조회 |
| --- | ---: | ---: |
| 10:00 | 900 | 1,200 |
| 10:01 | 600 | 600 |

마지막으로 확보한 두 구간 합은 `1,200+600=1,800`입니다. 두 응답을 모두 더한 `900+600+1,200+600=3,300`이 아닙니다. 2분 평균 처리율은 이 가상 계약에서 `1,800/120=15/초`입니다.

이 예시는 동일 구간 집계의 대체 정책입니다. 반대로 원천이 서로 겹치지 않는 delta 항목을 매번 보내는 계약이면 처리가 달라집니다. “클라우드 count니까 모두 더한다” 또는 “같은 시각이면 항상 덮는다”는 일반 규칙을 만들지 않습니다.

## 늦은 게시와 새 지표 발견

CloudWatch PutMetricData 문서는 새 metric이 ListMetrics에 나타나기까지의 지연과 과거 timestamp를 가진 자료의 조회 가용 지연을 설명합니다. 지표 목록에 아직 없다는 것과 실제 데이터가 전혀 없다는 것을 같은 상태로 취급하지 않습니다. [PutMetricData 가용 지연](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_PutMetricData.html)

제품이 과거 구간을 일정 범위 다시 조회하는 것은 이런 지연을 다루기 위한 **설계 정책**입니다. 5분이나 1시간 같은 하나의 backfill 창을 모든 공급자·서비스의 보장으로 적지 않습니다. 원천 문서와 실제 관측에 근거해 선택하고, 그 창보다 늦게 도착한 자료의 처리도 정의합니다.

## 재조회 자료의 식별과 충돌

다음은 **저장 키 설계의 예시**입니다. 공급자가 공식적으로 정의한 metric 정체성과 제품의 조회·정규화 키를 구분합니다.

```text
인증된 account/project/subscription, region
원천 namespace·metric·dimension/resource labels
요청한 statistic·period·unit filter 등 조회 계약
원천 표본 시각 또는 원천이 정의한 구간
정규화 정의 버전
```

같은 키에 다른 값이 오면 이전값·새값·수집 요청 문맥을 추적할 수 있게 합니다. 먼저 시작한 요청이 나중에 끝날 수도 있으므로 수신 시각만으로 원천의 최신 버전을 증명할 수는 없습니다. 원천 revision이 없다면 선택한 갱신 정책과 그 한계를 문서화하고 필요한 경우 재조회합니다.

## 늦은 자료와 알림은 별도 정책이다

지연 도착으로 어제의 오류율이 바뀌었다고 현재의 장애 알림을 그대로 새로 발송할지는 제품이 정해야 할 문제입니다. 현재 알림 평가, 과거 SLO 재계산, 보고서 수정, 늦은 자료 경고를 구분하도록 제안합니다.

Azure의 null과 0, 시간 집계의 의미를 확인하고 Google Cloud의 alignment와 cross-series reduction도 원천 규칙을 따릅니다. 공급자별 정책을 하나의 고정된 resample 함수로 숨기지 않습니다. [Azure 집계](https://learn.microsoft.com/en-us/azure/azure-monitor/metrics/metrics-aggregation-explained), [Google Cloud 집계](https://docs.cloud.google.com/monitoring/api/v3/aggregation)

## 가상 입력으로 확인할 수집기 수용 기준

1. 시간 배열이 역순이어도 timestamp-value 쌍이 유지되는가?
2. 한 metric만 Forbidden일 때 다른 metric의 성공과 분리되는가?
3. 같은 구간을 재조회해도 값이 중복 합산되지 않는가?
4. PartialData인데 token이 없을 때 미완료 상태를 보존하는가?
5. period·statistic이 바뀐 결과를 같은 정의로 덮지 않는가?
6. 늦은 자료의 보고서 반영과 현재 알림 정책이 구분되는가?

이는 구현에 적용할 계약 질문입니다. 이 판에서 실제 cloud adapter를 배포·실행해 모두 통과시켰다는 표시는 아닙니다.

## 이해 확인

1. HTTP 200이면 응답 안의 모든 metric도 완전한가? **각 결과의 상태를 읽어야 합니다.**
2. 같은 1분 Sum을 두 번 받으면 더하는가? **같은 구간을 갱신한 값이라면 중복 합산하지 않습니다.**
3. 모든 원천 API의 EndTime은 제외되는가? **CloudWatch의 해당 API 규칙이며 원천마다 확인합니다.**
4. 먼저 도착한 결과가 반드시 더 오래된 원천 상태인가? **요청·처리·전송 순서와 원천 revision을 구분해야 합니다.**

이전: [클라우드 지표의 기간, 통계와 정규화](provider-metrics.md) · 다음: [관리형 서비스와 서버리스 관측](managed-and-serverless.md) · [분야 목차](README.md)
