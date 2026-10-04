# 트레이스를 읽는 전제: 문맥 전파, sampling과 모집단

> 상태: 검토됨 · 적용 범위: W3C Trace Context, OpenTelemetry 개념·SDK 규약, tail sampling processor 0.137.0 문서 · 검토일: 2026-10-04 · sampling 수치는 가상 예시

## 먼저 이해할 것

Trace는 한 요청과 관련된 작업들을 연결한 기록입니다. Span은 그 안의 한 작업 구간입니다. 기록을 일부만 남기는 sampling이 적용되면 화면에서 보는 trace 집합은 전체 요청 집합과 달라질 수 있습니다. “보이는 오류의 비율”을 바로 “모든 사용자의 오류율”로 해석하지 않는 것이 출발점입니다.

선수 내용은 [trace·log·profile](../foundations/traces-logs-profiles.md)과 [계측 위치](instrumentation-and-profiling.md)입니다. 이 장의 tail sampling과 SDK 정책은 공식 자료 검토이며 직접 실행한 sampling 성능 실험은 아닙니다.

## traceparent가 전달하는 것

W3C `traceparent`에는 형식 버전, trace ID, parent ID, trace flags가 들어갑니다. 다음은 형식을 보여 주는 예시입니다.

```text
00-11111111111111111111111111111111-2222222222222222-01
```

trace ID는 같은 trace를 연결하고 parent ID는 전달한 문맥의 span을 가리킵니다. flags의 sampled bit는 sampling 관련 문맥을 전달합니다. 이 값은 사용자·tenant 인증 정보가 아닙니다. 수신 측은 형식·유효성을 검사하고 신뢰 경계에 맞는 정책을 사용합니다. [W3C Trace Context](https://www.w3.org/TR/trace-context/)

수집 제품은 같은 trace ID가 있다는 사실을 접근 권한의 증거로 사용하지 않도록 설계해야 합니다. 계측 문맥과 인증된 수집 범위는 별도 정보입니다.

## 비동기 작업은 단순한 함수 호출 트리와 다르다

요청 하나가 메시지를 넣고 바로 반환한 뒤 몇 분 후 다른 프로세스가 소비할 수 있습니다. 여러 메시지를 한 번에 처리하면 작업 하나에 선행 원인이 여러 개 있을 수도 있습니다. OpenTelemetry span은 parent 외에 link로 다른 span 문맥과 관계를 표현할 수 있습니다. [Trace API의 links](https://opentelemetry.io/docs/specs/otel/trace/api/#specifying-links)

따라서 span 그림에서 선이 없다고 실제 업무 관계가 없다고 확정하지 않습니다. 문맥이 유실됐는지, link로 표현됐는지, 다른 trace로 분리하는 계측 규약인지 확인합니다. 반대로 IP·시간이 비슷하다는 이유만으로 확정적인 parent 관계를 만들어도 안 됩니다.

## head와 tail은 언제 결정하는가의 차이

| 방식 | 결정 시점 | 설명하기 쉬운 장점 | 확인할 비용·한계 |
| --- | --- | --- | --- |
| Head sampling | trace/span 생성 시점의 정보로 판단 | 초기에 기록·전송량을 줄일 수 있음 | 나중에 발생할 오류·최종 지연을 미리 알 수 없음 |
| Tail sampling | 모은 span을 바탕으로 나중에 판단 | 오류·긴 지연 등 관측된 특성으로 선택 가능 | 대기 상태·메모리·늦은 span·분산 배치 문제 |

이는 처리 시점의 분류입니다. 모든 head 정책이 단순 무작위이고 모든 tail 정책이 오류 100% 보존이라는 뜻은 아닙니다. 실제 정책·SDK·수집 경로를 확인합니다. [OpenTelemetry sampling](https://opentelemetry.io/docs/concepts/sampling/)

SDK에는 기록하지 않음, 기록만 함, 기록하고 sampled로 표시함의 구분이 있습니다. 또한 parent 기반 sampler는 상위 문맥을 고려합니다. sampled flag 하나로 전체 경로의 수집·저장 성공을 증명하지 않습니다. [Tracing SDK sampling](https://opentelemetry.io/docs/specs/otel/trace/sdk/#sampling)

## 오류를 더 많이 보존하면 오류율도 커 보인다

**가상 예시:** 전체 요청 10,000개 중 오류가 1,000개, 정상 요청이 9,000개입니다. 오류는 전부 남기고 정상 요청은 그중 900개를 남겼다고 가정합니다.

```text
전체 요청 오류율 = 1,000 / 10,000 = 10%
보존된 trace의 오류 비율 = 1,000 / (1,000 + 900) ≈ 52.63%
```

52.63%는 보존된 집합의 비율로서 맞습니다. 그러나 전체 요청 오류율의 답으로 사용하면 틀립니다. 오류를 더 잘 조사하려고 선택한 집합이므로 선택 기준 자체가 결과 분포에 영향을 줍니다.

제품 적용 제안은 요청 성공률·SLO를 계산할 집계 경로와 상세 trace 탐색 경로의 모집단을 명세하는 것입니다. 전수 metric을 사용하더라도 그 metric의 계측 누락·필터·전송 유실이 없는지는 별도로 확인해야 합니다.

## “10%니까 열 배”의 조건

모든 요청이 같은 알려진 확률로 선택되고, 이후 유실이 없으며, 요청당 집계 단위가 일치한다는 가정 아래 표본 수를 확률로 나누어 전체 수를 추정할 수 있습니다. 그래도 특정 구간의 정확한 실제 건수와 항상 같다는 뜻은 아닙니다.

오류·서비스·tenant마다 선택 확률이 다르거나 제한에 걸린 trace가 더 빠진다면 단일 10배를 적용할 수 없습니다. trace 하나의 span 수를 요청 수와 혼동해서도 안 됩니다. 포함 확률을 모르면 정확한 전체 비율을 복원할 정보가 부족할 수 있습니다.

## tail sampling의 기다림과 배치

고정 버전 tail sampling processor는 같은 trace의 span을 모아 정책을 평가하는 상태를 유지합니다. 관련 span이 서로 다른 Collector에 흩어지면 각자 불완전한 정보로 판단할 수 있으므로 trace ID를 고려한 라우팅이 필요합니다. 결정 대기 시간, 보관 가능한 trace 수, decision cache와 늦게 도착한 span의 처리를 실제 버전에 맞춰 검토합니다. [Tail sampling processor 0.137.0](https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/v0.137.0/processor/tailsamplingprocessor/README.md)

**가상 예시:** 초당 새 trace 2,000개를 평균 10초간 판단 대기 상태로 보관한다면 단순한 정상 상태 모델의 대기 trace 수는 약 20,000개입니다. trace당 byte가 일정하다는 추가 가정 없이는 이 숫자만으로 메모리 MiB를 계산할 수 없습니다. span 수·속성·큐·런타임 객체 오버헤드도 필요합니다.

이 계산은 용량 계획의 출발점입니다. 실제 processor의 모든 메모리를 이 곱 하나로 설명하거나 특정 설정의 권장값으로 제시하지 않습니다.

## trace 화면에서 함께 보여 줄 정보

다음은 제품 적용 제안입니다.

| 정보 | 독자가 판단할 수 있는 것 |
| --- | --- |
| sampling 정책·변경 시점 | 배포 전후 집합 차이가 정책 변화인지 |
| trace/span 단위와 선택 비율의 범위 | 무엇의 몇 %인지 |
| 일부 span 누락 가능성 | 전체 실행 경로가 완성됐는지 |
| 원천·수신 시각 | 지연 도착인지 실제 긴 작업인지 |
| 계측·Collector 버전 | 문맥·의미 규약의 차이가 있는지 |
| 전송 거절·유실·재시도 | 표본 선택 후 추가로 빠진 데이터가 있는지 |

## 이해 확인

1. 오류 trace를 모두 보존하면 trace 화면의 오류 비율이 전체 요청 오류율인가? **정상 요청의 보존 정책이 다르면 그렇지 않습니다.**
2. sampled bit가 있으면 목적지 저장까지 보장되는가? **sampling 문맥이며 수집·전송·저장 성공을 보장하지 않습니다.**
3. tail sampling을 쓰면 모든 늦은 span까지 반드시 모이는가? **대기·용량·라우팅·늦은 데이터 정책에 한계가 있습니다.**
4. trace ID를 tenant 접근 권한으로 사용해도 되는가? **관측 연결 정보와 인증된 접근 범위를 분리합니다.**
