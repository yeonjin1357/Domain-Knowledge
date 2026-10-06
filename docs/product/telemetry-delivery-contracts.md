# 관측 데이터 전송 계약: 부분 성공, 재시도와 중복

> 상태: 검토됨 · 적용 범위: OTLP 1.11.0 문서, Collector 0.137.0·0.162.0의 OTLP/HTTP JSON 로컬 실험 · 원천 확인일: 2026-10-06 · 실습 여부: 저장된 로컬 실행 근거 포함; 구성·한계는 본문

## 먼저 이해할 것

**Collector 실패 계수를 읽는 세 줄:**

- 고정 버전의 `send_failed_*`는 exporter의 내부 retry가 최종 오류를 반환한 항목을 셉니다.
- 진행 중인 개별 재시도 횟수나 종단 간 영구 유실량을 세는 값이 아닙니다.
- 실측 구성의 부분 거절은 이 계수에 더해지지 않았으므로 warn 로그·목적지 거절도 확인합니다.

관측 데이터도 네트워크를 통해 전달되는 업무입니다. 보내는 쪽이 응답을 못 받았어도 받는 쪽은 이미 데이터를 읽었을 수 있습니다. 반대로 HTTP 200을 받았어도 목적지에서 일부 항목을 거절했을 수 있습니다. 전송 횟수, 받은 항목, 저장된 항목, 조회 가능한 항목을 구분해야 합니다.

이 장은 [수집 파이프라인](collection-pipelines.md)을 실제 Collector 동작으로 보강합니다. 테스트 목적지는 응답을 통제하는 임시 서버입니다. 영속 저장이나 검색은 구현하지 않았으므로 “저장 성공”을 측정한 실험으로 표시하지 않습니다.

## 기존 0.137.0 실험 경로와 고정 조건

```mermaid
flowchart LR
    Input["합성 span 2개"] --> Receiver["실제 Collector<br/>otlp HTTP receiver"]
    Receiver --> Exporter["otlphttp exporter<br/>queue 꺼짐"]
    Exporter --> Backend["응답을 통제하는<br/>loopback 서버"]
```

공식 Collector 0.137.0 실행 파일을 사용했습니다. receiver·exporter를 실제로 통과시켰으며 목적지는 JSON으로 성공·실패·부분 성공을 반환했습니다. sending queue는 껐고 재시도 시간은 짧게 제한했습니다. Collector 로그는 `error`, 내부 metric은 `none`으로 설정했습니다. 따라서 기록은 목적지 요청과 receiver 응답을 보여 주며, Collector 내부의 거절 인지 로그·거절 계수나 `send_failed_*` 증가를 직접 관측한 근거는 없습니다. 이 설정은 입력 요청과 exporter 결과의 관계를 관찰하기 위한 실험 조건입니다. [고정 버전 exporter 문서](https://github.com/open-telemetry/opentelemetry-collector/blob/v0.137.0/exporter/otlphttpexporter/README.md)

[실행 코드](../../scripts/run_otel_lab.py)와 [원시 기록](../../labs/results/1.1-otel.json)에 모든 시나리오의 목적지 요청 수·span ID·receiver 응답이 있습니다.

## HTTP 상태만으로 재시도 규칙을 추측하지 않는다

OTLP/HTTP 규약이 재시도 대상으로 열거한 상태는 429·502·503·504입니다. 그 외 4xx·5xx를 같은 방식으로 재시도하면 안 됩니다. 특히 “서버 오류면 모두 다시 전송”은 이 프로토콜의 규칙과 다릅니다. `Retry-After`와 backoff도 확인합니다. [OTLP HTTP 재시도 규약](https://opentelemetry.io/docs/specs/otlp/#retryable-response-codes)

### 응답에서 클라이언트 행동으로

| OTLP/HTTP 관측 | 클라이언트 행동 | 보존할 상태 |
| --- | --- | --- |
| HTTP 200, 정상 성공 | 해당 전송 완료 | 그 hop의 수용; 최종 저장과 구분 |
| 채워진 `partial_success` | **같은 요청을 재시도하면 안 됨(MUST NOT)** | 거절 수·사유, 개별 거절 ID가 없을 수 있음 |
| HTTP 429·502·503·504 | 규약의 backoff·Retry-After를 따라 재시도 | attempt와 논리 입력을 분리 |
| 그 밖의 4xx·5xx(500 포함) | 같은 재시도 가능 코드로 취급하지 않음 | 영구 실패 분류·원천 응답 |
| 응답 없이 연결 종료 | 재시도 규약 적용; 이미 수신됐을 가능성 보존 | 중복 수신 가능 |

**정상 응답의 생략값도 원천 규약대로 읽습니다.** OTLP/HTTP의 성공 코드는 200입니다. 유효하게 해석한 성공 응답에 `partial_success`가 없으면 거절 0건이며, 성공 응답에서는 서버가 이 필드를 비워 두어야 합니다. 거절 수가 0인데 `error_message`가 있으면 경고입니다. JSON의 int64 `rejectedSpans`는 `"1"` 같은 10진 문자열로 인코딩하고 수신기는 숫자 표현도 받아들입니다. ProtoJSON의 `null`은 필드를 설정하지 않은 것으로 읽습니다. 이 규칙은 SQL NULL이나 전송 실패·해석 불가 응답을 0으로 바꾸라는 뜻이 아닙니다. [OTLP 성공·부분 성공·JSON 규약](https://opentelemetry.io/docs/specs/otlp/), [ProtoJSON 기본값·null](https://protobuf.dev/programming-guides/json/)

protobuf 필드명은 `partial_success`·`rejected_spans`, **OTLP JSON은 `partialSuccess`·`rejectedSpans`**입니다. 아래 JSON 실습은 camelCase를 보존합니다. gRPC status는 별도 규약입니다. [OTLP partial success·retry·JSON](https://opentelemetry.io/docs/specs/otlp/)

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

목적지는 두 span을 받고 `rejectedSpans=1`을 선언했습니다. Collector는 그 요청을 다시 보내지 않았습니다. 채워진 부분 성공 응답 뒤에는 같은 요청을 재시도하면 안 됩니다(MUST NOT). 다시 보내면 이미 받아들인 항목도 중복될 수 있습니다. 또한 거절 **개수**만으로 어떤 개별 span이 거절됐는지 항상 알 수 있는 것은 아닙니다. [OTLP 부분 성공](https://opentelemetry.io/docs/specs/otlp/#partial-success)

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

Collector 0.137.0의 exporterhelper는 `queue → 관측 → retry → timeout → exporter` 순서로 호출을 감쌉니다. `send_failed_*`는 내부 retry가 오류를 반환한 뒤 관측 계층에서 항목 수를 기록합니다. 일시 실패 후 같은 retry 호출 안에서 성공하면 그 중간 시도마다 이 실패 계수가 증가하는 구조가 아닙니다. [호출 구성](https://github.com/open-telemetry/opentelemetry-collector/blob/v0.137.0/exporter/exporterhelper/internal/base_exporter.go#L66-L102), [실패 계수 기록](https://github.com/open-telemetry/opentelemetry-collector/blob/v0.137.0/exporter/exporterhelper/internal/obs_report_sender.go#L86-L141)

따라서 이 버전의 계수 증가를 “그 exporter의 동일한 내부 재시도가 아직 진행 중”이라고 풀이하지 않습니다. queue 경로에서는 최종 반환 오류에 대해 dropping 로그를 기록합니다. 다만 상류의 별도 재전송이나 다른 목적지의 성공까지 이 계수 하나로 알 수는 없어 종단 간 영구 유실 수와도 동일하지 않습니다. enqueue 실패, exporter 최종 실패, 목적지 부분 거절, 고유 저장 항목 수를 구분합니다. 이 설명은 코드 검토이며 0.137.0 실험의 내부 metric 관측 결과가 아닙니다. 0.162.0의 별도 실측은 다음 절에 있습니다. [QueueSender](https://github.com/open-telemetry/opentelemetry-collector/blob/v0.137.0/exporter/exporterhelper/internal/queue_sender.go#L38-L49), [일반 관측 안내](https://opentelemetry.io/docs/collector/internal-telemetry/)

단계 이름 `Accepted/Persisted/Queryable/Rejected`와 숫자 품질 상태의 정본은 [어댑터 계약](adapter-contracts.md#수집-상태는-서로-다른-축으로-보존한다)입니다. 아래는 전송 진단에 덧붙일 정보입니다.

다음은 **제품 적용 제안**입니다.

| 상태 | 보존할 정보 | 해석의 주의점 |
| --- | --- | --- |
| 수용 | 신호 종류·항목 수·수용 경계 | 최종 저장 완료와 구분 |
| 임시 실패 | 목적지·응답 분류·attempt | 한 항목이 여러 번 실패할 수 있음 |
| 거절 | 영구/부분 거절 수·사유 | 정상적인 sampling과 구분 |
| 재시도 대기 | 큐 단위·가장 오래된 항목·남은 시간 | 큐 길이만으로 지연 분포를 알 수 없음 |
| 중복 가능 | 안정적인 항목 식별·전송 수명 | 네트워크 단절 후 수신 여부가 모호할 수 있음 |

필터와 sampling이 있는 파이프라인에서 입력 수와 출력 수를 단순히 빼서 전부 “장애 유실”로 부르지 않습니다. 의도된 제거와 비의도적 유실을 같은 단위·시간 구간에서 각각 설명해야 합니다.

**이름과 계열 키:** 기본 Prometheus 내보내기는 counter에 `_total`을 붙여 `otelcol_exporter_send_failed_spans_total`을 노출합니다. 아래 0.162.0 실습은 `without_type_suffix: true`, `without_units: true`, `level: detailed`를 고정해 접미사 없는 이름을 관측했습니다. Collector 인스턴스·수명과 exporter 라벨을 보존하고 detailed 설정에서 붙는 `error` 등 모든 속성을 계열 키로 취급합니다. trace/span ID를 이 counter의 키로 쓰지 않습니다. 0.137.0 결과에는 내부 metric 표본이 없습니다. [내부 telemetry의 이름·설정](https://opentelemetry.io/docs/collector/internal-telemetry/), [0.162.0 실측 config·metric](../../labs/results/1.1-r2-otel.json)

## 0.162.0에서 내부 관측과 큐 경계를 다시 확인하기

**2026-10-05 실행:** 공식 core Collector 0.162.0, OTLP/HTTP JSON, loopback 목적지, debug 로그·detailed 내부 metric을 사용했습니다. `sending_queue.enabled`를 true/false로 나누고 `wait_for_result=false`, consumer 1개, 요청 단위 queue 10, 짧은 retry 한도를 고정했습니다. 프로세스마다 준비 요청(primer)으로 실패 계수를 만든 뒤 실험 요청 span 2개를 보냈습니다. 이 때문에 아래 시작값은 0이 아니라 **2**입니다. [원시 config·로그·metric](../../labs/results/1.1-r2-otel.json), [실행기](../../scripts/run_otel_r2_lab.py)

| 실험 요청의 결과 | queue | `send_failed_spans` 기준 → 종료 | upstream HTTP·완료 경계 |
| --- | --- | --- | --- |
| 정상 성공 | off / on | 각각 `2→2`, 증가 0 | 200 |
| 부분 거절 1개 | off / on | 각각 `2→2`, 증가 0 | 200, 빈 `partialSuccess` |
| 재시도 후 성공 | off / on | 각각 `2→2`, 증가 0 | off는 목적지 차단 해제 뒤 200, on은 해제 전 200 |
| 재시도 소진 | off / on | 각각 `2→4`, 증가 2 | off는 해제 뒤 503, on은 해제 전 200 |

**Collector 0.162.0의 이 구성에서는 재시도 진행 중 관측한 send_failed_spans가 기준값 2에 머물렀고, 재시도 소진 뒤 4로 증가해 실패한 span 2개를 계수했습니다.** 성공한 재시도에는 증가가 없었습니다. 마지막 목적지 시도 이전의 증가 표본은 없었으며 증가 시각은 metric polling의 관측 구간으로만 한정합니다. 실시간의 모든 순간을 계측한 것은 아닙니다. 이 결과는 코드에서 확인한 “내부 retry가 최종 오류를 반환한 뒤 항목 수를 기록”한다는 설명을 해당 새 버전·구성에서 지지합니다.

부분 성공에서는 목적지의 고유 사유 `r2-partial-rejected-one`과 `dropped_spans: 1`을 담은 warn 로그가 두 queue 구성 모두에 남았습니다. 준비 요청을 제외한 목적지 요청은 각각 1회였고 `send_failed_spans` 증가는 0이었습니다. **부분 거절을 Collector가 로그로 인지했다는 근거는 생겼지만, 이 실패 계수가 거절된 span 1개를 세지는 않았습니다.** upstream 응답도 거절 수를 보존하지 않았으므로 그 성공만으로 종단 간 수용률을 계산할 수 없습니다.

**`wait_for_result=false`인 queue를 켠 경우 upstream은 목적지 차단 해제 전에 200을 받았고, 끈 경우에는 차단 해제 뒤 exporter 결과를 받았습니다.** 이는 메모리 queue 수용 경계의 관측입니다. 재시작·영속 queue·실제 저장소의 commit을 시험한 결과로 확대하지 않습니다. 재시도 횟수와 ms 단위 지연은 재실행마다 달라질 수 있습니다.

`otlp_http`와 기존 `otlphttp` 이름은 모두 `validate`에서 수용됐습니다. 실제 전송 실험은 `otlp_http/lab`으로 수행했으므로 옛 별칭의 전체 전송 동작을 따로 실행했다고 표시하지 않습니다. core exporter 이름 변경은 0.144.0 릴리스부터 확인되며, 이름 수용 여부와 향후 alias 제거 정책은 별도입니다. [0.144.0 릴리스](https://github.com/open-telemetry/opentelemetry-collector/releases/tag/v0.144.0), [구성 검증 결과](../../labs/results/1.1-r2-otel.json)

## 재현

Ubuntu amd64의 저장소 루트에서 실행합니다. 기본 결과는 `.lab-runs/otel.json`입니다.

```bash
python3 scripts/get_runtime_lab_assets.py --which otelcol
python3 scripts/run_otel_lab.py
```

0.162.0 실행의 공식 자산 pin·새 결과 경로·재현 명령은 [공통 재현 절차](../cross-domain/reproducible-labs.md)에 있습니다.

## 이해 확인

1. HTTP 500이면 OTLP/HTTP에서 언제나 재시도하는가? **열거된 재시도 코드를 따라야 하며 이번 500은 한 번만 전송됐습니다.**
2. 부분 성공의 거절 수가 1이면 어느 span인지 반드시 아는가? **개수만으로 개별 항목을 식별할 수 없습니다.**
3. 재시도에서 같은 span ID가 다시 왔다면 새 업무가 하나 더 발생했는가? **같은 관측의 중복 전송일 수 있습니다.**
4. 이 결과로 영속 큐의 무손실을 보장하는가? **기존 queue-off와 새 메모리 queue on/off 관측이며 영속 큐 장애 검증은 별도입니다.**

## 검증 노트

버전 상태: 기존 0.137.0 실행을 보존하고 2026-10-05 실행으로 0.162.0의 내부 로그·metric과 queue on/off 결과를 추가했습니다. OTLP 웹 문서 1.11.0과 원천 릴리스 1.11.1도 구분합니다. [고정·최신·지원 상태](../coverage.md#교차-검토-시점의-버전-상태)

이전: [수집, 변환, 전송과 유실의 경계](collection-pipelines.md) · 다음: [텔레메트리 저장과 조회의 의미](storage-and-query.md) · [분야 목차](README.md)
