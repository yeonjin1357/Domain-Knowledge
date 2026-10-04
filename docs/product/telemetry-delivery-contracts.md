# 관측 데이터 전송 계약: 부분 성공, 재시도와 중복

> 상태: 검토됨 · 적용 범위: OTLP 1.11.0 문서, Collector 0.137.0의 OTLP/HTTP JSON 로컬 실험 · 검토일: 2026-10-04

## 먼저 이해할 것

관측 데이터도 네트워크를 통해 전달되는 업무입니다. 보내는 쪽이 응답을 못 받았어도 받는 쪽은 이미 데이터를 읽었을 수 있습니다. 반대로 HTTP 200을 받았어도 목적지에서 일부 항목을 거절했을 수 있습니다. 전송 횟수, 받은 항목, 저장된 항목, 조회 가능한 항목을 구분해야 합니다.

이 장은 [수집 파이프라인](collection-pipelines.md)을 실제 Collector 동작으로 보강합니다. 테스트 목적지는 응답을 통제하는 임시 서버입니다. 영속 저장이나 검색은 구현하지 않았으므로 “저장 성공”을 측정한 실험으로 표시하지 않습니다.

## 실험 경로와 고정 조건

```mermaid
flowchart LR
    Input["합성 span 2개"] --> Receiver["실제 Collector<br/>otlp HTTP receiver"]
    Receiver --> Exporter["otlphttp exporter<br/>queue 꺼짐"]
    Exporter --> Backend["응답을 통제하는<br/>loopback 서버"]
```

공식 Collector 0.137.0 실행 파일을 사용했습니다. receiver·exporter를 실제로 통과시켰으며 목적지는 JSON으로 성공·실패·부분 성공을 반환했습니다. sending queue는 껐고 재시도 시간은 짧게 제한했습니다. 이 설정은 입력 요청과 exporter 결과의 관계를 관찰하기 위한 실험 조건입니다. [고정 버전 exporter 문서](https://github.com/open-telemetry/opentelemetry-collector/blob/v0.137.0/exporter/otlphttpexporter/README.md)

[실행 코드](../../scripts/run_otel_lab.py)와 [원시 기록](../../labs/results/1.1-otel.json)에 모든 시나리오의 목적지 요청 수·span ID·receiver 응답이 있습니다.

## HTTP 상태만으로 재시도 규칙을 추측하지 않는다

OTLP/HTTP 규약이 재시도 대상으로 열거한 상태는 429·502·503·504입니다. 그 외 4xx·5xx를 같은 방식으로 재시도하면 안 됩니다. 특히 “서버 오류면 모두 다시 전송”은 이 프로토콜의 규칙과 다릅니다. `Retry-After`와 backoff도 확인합니다. [OTLP HTTP 재시도 규약](https://opentelemetry.io/docs/specs/otlp/#retryable-response-codes)

| 통제한 목적지 응답 | 실제 목적지 시도 횟수 | receiver에서 받은 HTTP |
| --- | ---: | ---: |
| 200 정상 성공 | 1 | 200 |
| 첫 503, 다음 200 | 2 | 200 |
| 400 지속 | 1 | 400 |
| 500 지속 | 1 | 500 |
| 200, span 1개 거절을 알리는 부분 성공 | 1 | 200 |
| 본문 수신 후 응답 없이 연결 종료, 다음 200 | 2 | 200 |
| 503 지속, 제한된 재시도 시간 소진 | 이번 실행에서 6 | 503 |

마지막 6회는 해당 실행의 관측값입니다. backoff의 시간 조건 때문에 모든 재실행에서 같은 횟수라고 보장하지 않습니다. 재시도 오류의 전체 분류를 gRPC에 그대로 복사하지도 않습니다. OTLP/gRPC는 별도 status 규약을 갖습니다.

## 부분 성공에서 무엇을 잃는가

목적지는 두 span을 받고 `rejectedSpans=1`을 선언했습니다. Collector는 그 요청을 다시 보내지 않았습니다. 부분 성공 응답 뒤 같은 전체 요청을 재전송하면 이미 받아들인 항목도 다시 보낼 수 있습니다. 또한 거절 **개수**만으로 어떤 개별 span이 거절됐는지 항상 알 수 있는 것은 아닙니다. [OTLP 부분 성공](https://opentelemetry.io/docs/specs/otlp/#partial-success)

이번 구성에서는 upstream receiver가 HTTP 200과 빈 `partialSuccess` 객체를 반환했습니다. 즉, 목적지의 거절 개수가 upstream 응답에 그대로 전달되지 않았습니다. **이것은 고정 버전·구성에서의 관측**이며 모든 Collector 배치나 SDK가 반드시 같은 응답을 만든다는 주장은 아닙니다.

제품은 목적지 거절량·사유를 별도로 관측해야 합니다. upstream 성공만 보고 종단 간 수용률을 100%라고 계산하면 이 실험의 거절을 놓칩니다. 테스트 서버는 영속 저장을 하지 않았으므로 나머지 한 span이 실제 디스크에 저장됐다는 결론도 내리지 않습니다.

## 응답 유실이 만드는 중복

응답 유실 실험에서는 목적지가 첫 요청의 본문을 읽은 뒤 응답을 보내지 않고 연결을 닫았습니다. Collector가 재시도했고 목적지는 같은 두 span ID를 두 번 받았습니다.

```text
논리 입력 span: 2개
목적지에서 관측한 요청: 2회
목적지 수신 span 항목: 4개
서로 다른 span ID: 2개
```

“전송 성공 횟수”와 “서로 다른 관측 항목 수”는 다릅니다. 이 실험은 중복 수신을 보여 주며 저장소의 중복 제거 정책을 검증하지는 않습니다. 제품의 키·수명·보관 기간에 맞춘 중복 정책이 별도로 필요합니다.

## 큐를 켜면 완료 경계가 달라질 수 있다

위 실험의 sending queue는 꺼져 있습니다. 비동기 큐를 켠 배치에서는 receiver 요청이 반환되는 시점과 exporter의 최종 성공·실패 시점이 분리될 수 있습니다. 큐 수용이 메모리 보관인지 영속 기록인지, 재시작 시 복원되는 범위가 무엇인지 확인합니다. [Collector resiliency](https://opentelemetry.io/docs/collector/resiliency/)

영속 큐에도 유한한 용량, 재시도 한도, 디스크 오류, 처리 중 상태의 경계가 있습니다. queue 크기 숫자는 요청·batch·항목·byte 중 무엇을 세는지 설정과 버전을 대조합니다. 이 장에서 persistent queue 재시작이나 전원 장애는 실행하지 않았습니다.

## 수집기의 실패 지표를 읽기

Collector의 전송 실패 지표가 증가했다고 모든 항목이 영구 유실됐다고 해석하지 않습니다. 재시도 중일 수 있습니다. enqueue 실패, 원천 거절, 최종 폐기, 재전송 성공을 구분해 봅니다. [Collector 내부 관측](https://opentelemetry.io/docs/collector/internal-telemetry/)

다음은 **제품 적용 제안**입니다.

| 상태 | 보존할 정보 | 해석의 주의점 |
| --- | --- | --- |
| 수용 | 신호 종류·항목 수·수용 경계 | 최종 저장 완료와 구분 |
| 임시 실패 | 목적지·응답 분류·attempt | 한 항목이 여러 번 실패할 수 있음 |
| 거절 | 영구/부분 거절 수·사유 | 정상적인 sampling과 구분 |
| 재시도 대기 | 큐 단위·가장 오래된 항목·남은 시간 | 큐 길이만으로 지연 분포를 알 수 없음 |
| 중복 가능 | 안정적인 항목 식별·전송 수명 | 네트워크 단절 후 수신 여부가 모호할 수 있음 |

필터와 sampling이 있는 파이프라인에서 입력 수와 출력 수를 단순히 빼서 전부 “장애 유실”로 부르지 않습니다. 의도된 제거와 비의도적 유실을 같은 단위·시간 구간에서 각각 설명해야 합니다.

## 재현

Ubuntu amd64의 저장소 루트에서 실행합니다. 기본 결과는 `.lab-runs/otel.json`입니다.

```bash
python3 scripts/get_runtime_lab_assets.py --which otelcol
python3 scripts/run_otel_lab.py
```

## 이해 확인

1. HTTP 500이면 OTLP/HTTP에서 언제나 재시도하는가? **열거된 재시도 코드를 따라야 하며 이번 500은 한 번만 전송됐습니다.**
2. 부분 성공의 거절 수가 1이면 어느 span인지 반드시 아는가? **개수만으로 개별 항목을 식별할 수 없습니다.**
3. 재시도에서 같은 span ID가 다시 왔다면 새 업무가 하나 더 발생했는가? **같은 관측의 중복 전송일 수 있습니다.**
4. 이 결과로 영속 큐의 무손실을 보장하는가? **큐를 끈 HTTP 전송 실험이며 영속 큐 장애 검증은 별도입니다.**
