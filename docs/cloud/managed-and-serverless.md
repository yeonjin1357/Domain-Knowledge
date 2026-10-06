# 관리형 서비스와 서버리스 관측

> 상태: 검토됨 · 적용 범위: 관리형 관측 모델, AWS Lambda·Google Cloud Run 사례 · 원천 확인일: 2026-10-05 · 실습 여부: 원천·가상 예시 중심; 연결 실습의 범위는 본문

## 먼저 이해할 것

관리형 서비스는 내부 운영의 일부를 공급자가 맡지만 사용자 요청의 의미와 관측 책임은 남습니다. 서버리스에서는 실행 준비, 실제 실행, 동시성 제한, 대기하는 사건을 구분해야 합니다. 보이지 않는 호스트 내부를 추측해 채우기보다 제공되는 경계와 업무 성공을 연결합니다.

서버리스에서도 작업은 CPU·메모리·네트워크·저장소를 사용합니다. 달라지는 것은 사용자가 관리하고 관측할 수 있는 경계입니다.

## 관리 책임과 관측 경계

제품에서는 자원을 물리 호스트에 억지로 연결하기보다 서비스가 제공하는 함수·버전·revision·인스턴스·DB endpoint를 기준으로 모델링하도록 제안합니다. 내부 호스트가 공개되지 않은 경우 그 관계를 추측해 생성하지 않습니다.

관리형 DB도 SQL·트랜잭션의 원리는 [DB 본문](../database/README.md)과 연결되지만 OS 내부 진단 권한은 다를 수 있습니다. 공급자 상태, 서비스 지표, 엔진 view와 클라이언트 관측을 분리합니다.

## Lambda 호출 수의 분모

Lambda Invocations는 함수 코드가 호출된 횟수이며 throttled 요청 등 실행되지 않은 요청은 포함하지 않습니다. Errors/Invocations는 함수 실행 오류율이고, 전체 진입 요청의 실패율과 다를 수 있습니다. Duration은 코드가 이벤트를 처리한 시간이며 cold start 시간을 포함하지 않습니다. [AWS Lambda Metric Types](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-metrics-types.html)

가상 예시에서 진입 요청 1,000개, 실행 전 throttle 100개, 실제 실행 900개, 함수 오류 9개라고 가정합니다.

```text
함수 실행 오류율 = 9/900 = 1%
전체 요청 중 throttle 비율 = 100/1000 = 10%
```

둘 중 하나만 보면 다른 실패를 놓칠 수 있습니다. 실제 전체 요청의 결과를 합칠 때는 재시도·중복·다른 오류 유형도 확인합니다.

### Duration이라는 이름의 출처를 먼저 구분하기

| 출처 | 의미·포함 범위 | 대응 한계 |
| --- | --- | --- |
| CloudWatch `AWS/Lambda Duration` | 코드의 이벤트 처리 시간; 문서상 cold start 제외 | suppressed init의 포함 여부는 직접 확인되지 않음 |
| CloudWatch Logs REPORT `Duration` | invoke 보고 시간; suppressed init의 INIT+INVOKE 포함 가능 | CloudWatch 지표와 동일 필드라고 가정하지 않음 |
| REPORT `Init Duration` / Telemetry `platform.initReport` | 초기화 시간의 별도 보고 | 필드 부재만으로 초기화 부재를 확정하지 않음 |
| SnapStart `RESTORE_REPORT`·REPORT의 Restore Duration | snapshot 복원 관련 시간 | Init·Invoke Duration과 다른 단계 |

[지표 정의](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-metrics-types.html), [실행 환경·REPORT](https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtime-environment.html), [Telemetry 스키마](https://docs.aws.amazon.com/lambda/latest/dg/telemetry-schema-reference.html), [SnapStart 관측](https://docs.aws.amazon.com/lambda/latest/dg/snapstart-monitoring.html)

## 초기화 시간, 과금 시간과 오류 시각

Lambda 초기화의 관측 출처를 먼저 구분합니다. cold start의 `Init Duration`은 REPORT 로그에서 확인할 수 있으며, Telemetry API의 `platform.initReport`는 초기화 보고 이벤트와 `metrics.durationMs`를 제공합니다. invoke 실패 뒤 suppressed init은 CloudWatch Logs에 추가 INIT 단계로 명시되지 않으면서 **REPORT의 Duration에 INIT+INVOKE 시간이 포함**될 수 있습니다. Telemetry API의 `phase=invoke` 초기화 이벤트로 구분할 수 있으므로 “Init Duration 필드가 없으면 초기화가 없었다”고 결론 내리지 않습니다. [실행 환경 수명과 suppressed init](https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtime-environment.html), [Telemetry API 이벤트 스키마](https://docs.aws.amazon.com/lambda/latest/dg/telemetry-schema-reference.html)

REPORT와 CloudWatch 지표의 suppressed init 대응은 미확인입니다. 그 확인 범위는 장 끝 검증 노트에 남깁니다.

2025-08-01부터 managed runtime·ZIP·on-demand 함수의 INIT 단계도 과금 대상이 되었습니다. 다른 실행·배포 방식에서는 이미 적용되던 과금과 구분해야 합니다. **과금 규칙의 변경은 CloudWatch `Duration` 지표에 cold start가 포함된다는 뜻이 아닙니다.** 원천 지표, 로그의 Duration·Init Duration·Billed Duration을 각각의 정의로 읽습니다. [AWS INIT 과금 변경 공지](https://aws.amazon.com/blogs/compute/aws-lambda-standardizes-billing-for-init-phase/)

표준 Lambda `Errors`의 timestamp는 오류가 발생하거나 실행이 끝난 시각이 아니라 **호출이 시작된 시각**입니다. 오래 실행된 호출의 실패가 앞 구간의 지표를 늦게 바꿀 수 있습니다. 제품은 로그·trace의 실제 오류 시각과 지표의 귀속 구간을 구분하고 [재조회 정책](late-data-and-reconciliation.md)으로 연결하도록 제안합니다. [Lambda 지표 유형](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-metrics-types.html)

이 내용은 문서 대조이며 함수 호출·배포·설정 변경을 실행하지 않았습니다. Telemetry API는 실행 환경의 extension이 구독하는 경로입니다. 원격 지표 API 조회와 같지 않으며 extension의 처리·메모리 비용도 설계에 포함합니다. [Telemetry API](https://docs.aws.amazon.com/lambda/latest/dg/telemetry-api.html)

## 동시성과 확장

Lambda의 동시성은 동시에 실행되는 요청 규모와 관련되며 요청률과 실행 시간의 영향을 받습니다. 예약 동시성과 provisioned concurrency는 각각 용량 할당·제한과 준비된 실행 환경에 관한 다른 설정입니다. [AWS Lambda Concurrency](https://docs.aws.amazon.com/lambda/latest/dg/lambda-concurrency.html)

다음 평균 모델의 시간은 요청이 실행 환경을 점유하는 기간입니다. 요청 때문에 Init을 수행한다면 그 시간도 포함하며, 미리 준비된 환경의 유휴 시간을 요청마다 더하지 않습니다. cold start를 제외하는 `Duration` 지표를 그대로 점유 시간으로 대입하면 초기화 영향을 놓칠 수 있습니다. [Init·Invoke 동안의 점유](https://docs.aws.amazon.com/lambda/latest/dg/lambda-concurrency.html)

합성 안정 상태에서 100호출/s, 평균 점유 시간이 0.2초라면 평균 동시 실행 규모는 20입니다. 평균이 1초로 늘면 같은 호출률에 100 규모가 됩니다. 이 계산은 burst와 확장 속도, quota를 생략한 평균 모델입니다.

Cloud Run은 한 인스턴스가 여러 동시 요청을 처리하도록 설정할 수 있습니다. 따라서 인스턴스 수와 동시 요청 수를 일대일 매핑하지 않습니다. 실제 concurrency 설정과 앱의 병렬 처리 능력을 확인합니다. [Cloud Run Concurrency](https://docs.cloud.google.com/run/docs/about-concurrency)

## timeout 뒤에도 실행이 남을 수 있다

Cloud Run 요청 timeout은 응답 기한을 넘기면 연결을 닫고 504를 반환하지만 그 이유만으로 컨테이너 인스턴스가 종료되는 것은 아닙니다. 코드가 계속 실행하면서 다른 요청에 영향을 줄 수 있습니다. [Cloud Run Request Timeout](https://docs.cloud.google.com/run/docs/configuring/request-timeout)

제품은 요청 시간 초과, 실행 중 작업, 실제 취소와 후속 부작용을 구분하도록 제안합니다. 이는 [시간 제한·재시도](../application/timeouts-and-retries.md)의 원리와 연결됩니다.

## 이벤트 기반 실행의 지연

이벤트가 들어온 시각, 플랫폼이 전달한 시각, 함수 시작·완료 시각을 따로 관측하는 모델을 제안합니다. 함수 자체가 빨라도 앞의 backlog가 크면 업무 완료는 늦을 수 있습니다. 실행 Duration만으로 이벤트 발생부터의 전체 지연을 대표하지 않습니다.

가상으로 이벤트가 12:00:00에 발생하고 함수가 12:00:30에 시작해 0.2초 만에 완료했다면 실행은 짧지만 전체는 30.2초입니다. 시각 원천과 시계 오차도 확인해야 합니다.

## 이해 확인

1. Errors/Invocations가 모든 진입 요청의 실패율인가? **throttle 등 빠지는 범주가 있습니다.**
2. Lambda Duration에 cold start가 포함되는가? **해당 지표의 정의에서는 포함하지 않습니다.**
3. Cloud Run 504면 코드 실행도 종료됐는가? **그렇다고 보장되지 않습니다.**
4. Errors의 표본 시각은 에러 로그가 기록된 시각인가? **표준 Lambda Errors는 호출 시작 시각에 귀속됩니다.**
5. INIT 과금이 시작되면 Duration 지표도 자동으로 같은 시간이 되는가? **과금·지표·로그의 계약을 각각 확인해야 합니다.**


## 검증 노트

기본 on-demand Init의 10초 제한을 넘으면 첫 호출 시 함수 timeout 범위에서 Init을 다시 시도하는 경로도 있습니다. 이는 invoke 실패 뒤 suppressed init과 구분합니다. REPORT 로그에서 확인한 시간 포함 관계를 CloudWatch `Duration` 지표에도 그대로 적용하지 않습니다. **2026-10-05 재확인에서도**, 실행 환경 문서는 REPORT의 포함 관계를 명시하고 지표 문서는 cold start 제외를 설명하지만, suppressed init이 `AWS/Lambda`의 `Duration` 지표에도 포함되는지를 직접 연결하는 공식 문장은 확인하지 못했습니다. 이 세부 대응은 미확인 상태이며 실측하지 않았습니다. [Init 실패·재시도](https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtime-environment.html), [Duration 지표 정의](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-metrics-types.html)

이전: [늦게 도착하는 클라우드 지표: 재조회, 부분 결과와 중복 집계](late-data-and-reconciliation.md) · 다음: [클라우드 네트워크: 경로, 정책과 흐름 로그](networking.md) · [분야 목차](README.md)
