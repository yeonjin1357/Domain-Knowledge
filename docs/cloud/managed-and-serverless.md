# 관리형 서비스와 서버리스 관측

> 상태: 본문 초안 · 적용 범위: 관리형 관측 모델, AWS Lambda·Google Cloud Run 사례 · 출처 확인일: 2026-10-03

서버리스에서도 작업은 CPU·메모리·네트워크·저장소를 사용합니다. 달라지는 것은 사용자가 관리하고 관측할 수 있는 경계입니다.

## 관리 책임과 관측 경계

제품에서는 자원을 물리 호스트에 억지로 연결하기보다 서비스가 제공하는 함수·버전·revision·인스턴스·DB endpoint를 기준으로 모델링하도록 제안합니다. 내부 호스트가 공개되지 않은 경우 그 관계를 추측해 생성하지 않습니다.

관리형 DB도 SQL·트랜잭션의 원리는 [DB 본문](../database/README.md)과 연결되지만 OS 내부 진단 권한은 다를 수 있습니다. 공급자 상태, 서비스 지표, 엔진 view와 클라이언트 관측을 분리합니다.

## Lambda 호출 수의 분모

Lambda Invocations는 함수 코드가 호출된 횟수이며 throttled 요청 등 실행되지 않은 요청은 포함하지 않습니다. Errors/Invocations는 함수 실행 오류율이고, 전체 진입 요청의 실패율과 다를 수 있습니다. Duration은 코드가 이벤트를 처리한 시간이며 cold start 시간을 포함하지 않습니다. [AWS Lambda Metric Types](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-metrics-types.html)

합성 예에서 진입 요청 1,000개, 실행 전 throttle 100개, 실제 실행 900개, 함수 오류 9개라고 가정합니다.

```text
함수 실행 오류율 = 9/900 = 1%
전체 요청 중 throttle 비율 = 100/1000 = 10%
```

둘 중 하나만 보면 다른 실패를 놓칠 수 있습니다. 실제 전체 요청의 결과를 합칠 때는 재시도·중복·다른 오류 유형도 확인합니다.

## 동시성과 확장

Lambda의 동시성은 동시에 실행되는 요청 규모와 관련되며 요청률과 실행 시간의 영향을 받습니다. 예약 동시성과 provisioned concurrency는 각각 용량 할당·제한과 준비된 실행 환경에 관한 다른 설정입니다. [AWS Lambda Concurrency](https://docs.aws.amazon.com/lambda/latest/dg/lambda-concurrency.html)

합성 안정 상태에서 100호출/s, 평균 실행 0.2초라면 평균 동시 실행 규모는 20입니다. 평균이 1초로 늘면 같은 호출률에 100 규모가 됩니다. 이 계산은 burst와 확장 속도, quota를 생략한 평균 모델입니다.

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

다음: [클라우드 네트워크](networking.md) · [클라우드 목차](README.md)
