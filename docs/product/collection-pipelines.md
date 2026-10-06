# 수집, 변환, 전송과 유실의 경계

> 상태: 검토됨 · 적용 범위: 공통 수집 구조, OpenTelemetry Collector·OTLP, Fluent Bit 5.1.3 및 명시한 이전 버전 차이 · 원천 확인일: 2026-10-06 · 실습 여부: 원천·가상 예시 중심; 연결 실습의 범위는 본문

## 먼저 이해할 것

관측 자료는 원천에서 읽힌 뒤 변환·대기·전송·저장 단계를 지납니다. 택배를 접수한 것과 최종 목적지에 도착한 것이 다르듯이 수신 성공과 조회 가능은 다른 완료 경계입니다. 각 단계의 실패·재시도·중복·버퍼 상태를 관측해야 수집 제품 자체의 문제를 설명할 수 있습니다. 호스트 상태·클라우드 제어 정보·업무 요청 중 필요한 자료를 정한 뒤 설치 형태와 수집 위치를 선택합니다.

## 배치와 통신 방향을 별도로 결정한다

| 구분 | 얻기 쉬운 정보 | 설계에서 확인할 조건 |
| --- | --- | --- |
| 호스트·노드 에이전트 | OS, 프로세스, 로컬 로그·런타임 | 권한, 업데이트, 자체 자원 사용 |
| 애플리케이션 계측 | 업무 경계, context, 내부 처리 구간 | 지원 라이브러리, 계측 누락·중복, 실행 비용 |
| 원격 API 수집 | 관리형 서비스, 계정·클러스터 자원 | 호출 제한, 조회 권한, 게시 지연 |
| 능동 검사 | 관측 지점에서의 실제 요청 결과 | 경로·빈도·검사 트래픽의 대표성 |
| 커널·런타임 탐침 | 선택한 이벤트와 실행·통신 동작 | 지원 환경, 탐침 위치, 암호화·상위 의미의 관측 여부 |

Pull은 수집기가 요청하고 Push는 발생 측이 보내는 통신 방향입니다. 에이전트 유무와 동일한 구분이 아닙니다. 에이전트가 로컬 지표를 Pull하고 중앙으로 Push할 수도 있습니다. Collector 공식 배치 문서도 애플리케이션 가까이에 둔 agent와 여러 발생원에서 받는 gateway를 구분합니다. [Agent 배치](https://opentelemetry.io/docs/collector/deployment/agent/), [Gateway 배치](https://opentelemetry.io/docs/collector/deployment/gateway/)

Linux BPF는 커널에서 사용할 수 있는 프로그램·맵·검증 등 여러 기능을 포함합니다. BPF를 쓴다는 설명만으로 HTTP 내용, TLS 평문, DB 트랜잭션 결과를 모두 얻는다고 판단하지 않습니다. 실제 probe와 지원 런타임·프로토콜을 확인해야 합니다. [Linux BPF 문서](https://docs.kernel.org/bpf/index.html)

## 파이프라인 단계별 책임

OpenTelemetry Collector의 파이프라인은 receiver가 받고, processor가 처리하고, exporter가 목적지로 내보내는 형태입니다. 구성 요소와 신호별 지원 여부는 실제 배포판에서 확인해야 합니다. [Collector architecture](https://opentelemetry.io/docs/collector/architecture/)

```mermaid
flowchart LR
    Source["계측·통계·API"] --> Receive["수신·파싱"]
    Receive --> Normalize["식별·단위·스키마 변환"]
    Normalize --> Policy["필터·sampling·batch"]
    Policy --> Queue["전송 대기·재시도"]
    Queue --> Store["저장 수신"]
    Store --> Query["조회 가능 상태"]
```

위 그림은 개념적 제품 구조이며 모든 Collector가 이 순서나 저장 방식을 강제한다는 뜻은 아닙니다. 각 단계에서 입력·출력 건수, 거절·폐기 사유, 지연, 구성 버전을 남기면 값이 없어진 위치를 찾을 수 있습니다.

특히 단위 변환과 신호의 의미 변환을 구분합니다. `ms → s`는 단위 배율 변환이지만 `Cumulative → Delta`는 대상별 이전 상태가 필요합니다. 처리 작업자를 바꿨는데 이전 상태를 잃거나, 한 시계열을 여러 작업자가 각각 처리하면 결과가 달라질 수 있습니다. 원리는 [시계열 데이터 모델](../foundations/time-series.md)을 따릅니다.

## 수신 성공은 어디까지의 성공인가

**OTLP(OpenTelemetry Protocol)**는 관측 신호를 주고받는 규약입니다. 성공은 해당 hop의 수용이고, 부분 성공 뒤에는 해당 요청을 재시도하면 안 됩니다. JSON의 `partialSuccess`와 protobuf의 `partial_success`는 표기 차이입니다. [응답→클라이언트 행동의 정본](telemetry-delivery-contracts.md#응답에서-클라이언트-행동으로)을 따릅니다.

`Accepted/Persisted/Queryable/Rejected`는 [어댑터 계약의 전송 단계](adapter-contracts.md#전송-단계의-제품-계약)로 정의합니다. 중간 성공을 최종 저장·조회·평가 완료로 바꾸지 않습니다.

## 버퍼와 역압

버퍼는 유입과 처리 속도의 일시 차이를 흡수하고, 역압은 상류의 유입·진행을 제한합니다. 소진·복구 시간 식과 900 MiB 가상 예시는 [용량 계산 정본](capacity-and-loss-budgets.md#버퍼가-견디는-시간)에 모았습니다.

Collector의 persistent sending queue는 디스크에 보관해 프로세스 재시작 후 재전송할 수 있게 하지만, 디스크 장애·공간 부족·재시도 한도 등의 유실 가능성은 남습니다. 메모리 큐를 영속 큐로 바꾸는 것과 종단 간 무손실을 증명하는 것은 별개입니다. [Collector resiliency](https://opentelemetry.io/docs/collector/resiliency/)

큐가 찼을 때 가능한 정책에는 입력 거절, 오래된 항목 폐기, 우선순위별 제한, 전송량 제한이 있습니다. 어떤 정책이든 버린 양과 이유를 남겨야 조회 결과의 모집단을 설명할 수 있습니다. 재시도 역시 [업무 요청의 재시도](../application/timeouts-and-retries.md)처럼 부하를 증폭할 수 있습니다.

## 로그가 없는 것과 로그를 잃은 것을 구분한다

검색 결과가 비었다면 애플리케이션이 기록하지 않았을 수도 있고, 파일을 읽지 못했거나 필터·버퍼·전송·색인 단계에서 사라졌을 수도 있습니다. 수집기가 읽기 전 파일이 삭제됐다면 수집기의 drop counter에도 잡히지 않을 수 있습니다. 따라서 “drop=0”만으로 종단 간 무손실을 보증하지 않습니다.

### 사례: Fluent Bit의 손실과 버퍼

처음에는 세 단위만 구분해 읽어도 됩니다. record는 개별 기록 수, chunk는 여러 기록을 묶은 재시도 단위, byte는 차지한 크기입니다. 아래 상세 이름은 이 단위 구분을 구현하는 참고표입니다.

다음은 **Fluent Bit 5.1.3 코드와 공식 monitoring 문서를 2026-10-06 확인한** 원천입니다. GitHub 릴리스 게시 시각은 2026-10-01 UTC이며 프로젝트 공지의 날짜는 9월 30일입니다. plugin instance별로 읽으며 누적 수명과 단위를 보존합니다. chunk는 여러 record를 모아 전송하는 묶음이므로 chunk 수와 로그 줄 수를 더하거나 같은 분모로 나누지 않습니다. [공식 릴리스](https://github.com/fluent/fluent-bit/releases/tag/v5.1.3), [프로젝트 공지](https://fluentbit.io/announcements/v5.1.3/), [monitoring](https://docs.fluentbit.io/manual/administration/monitoring)

**아래 fluentbit_* 이름은 `/api/v2/metrics/prometheus` 기준**입니다. v2의 일반 `/api/v2/metrics`는 cmetrics text, `/api/v2/metrics/prometheus`는 Prometheus text 0.0.4 형식입니다. v1 JSON·v1 Prometheus endpoint에 모든 같은 이름이 있다고 가정하지 않습니다. 특히 filter drop 등 cmetrics 원천의 가용성을 endpoint별로 확인하며, 표의 `/api/v1/storage`만 별도의 JSON 상태 응답입니다. [endpoint·v2 지표 구분](https://docs.fluentbit.io/manual/administration/monitoring)

| 지표 | 단위·형태 | 판단할 수 있는 것 |
| --- | --- | --- |
| `fluentbit_input_records_total` | 누적 record | input이 성공적으로 받아들인 수; 원천에서 발생한 전체 수는 아님 |
| `fluentbit_filter_drop_records_total` | 누적 record | filter에서 제거한 수; 의도한 정책일 수도 있음 |
| `fluentbit_output_proc_records_total` | 누적 record | output이 성공적으로 보낸 수; 최종 검색 완료와 구분 |
| `fluentbit_output_retries_total` | chunk 재시도 요청 횟수 | 같은 chunk의 여러 재시도 포함 가능; 유실 건수 아님 |
| `fluentbit_output_retries_failed_total` | 재시도 한도 소진 chunk 수 | 해당 chunk 재시도 만료·폐기 |
| `fluentbit_output_dropped_records_total` | 누적 record | 복구 불가 오류 또는 재시도 만료로 output에서 버린 수 |
| `fluentbit_output_errors_total` | 실패 chunk 수 | 로그 메시지 줄 수나 실패 record 수와 같지 않음 |
| `fluentbit_input_memrb_dropped_chunks`, `fluentbit_input_memrb_dropped_bytes` | 누적 chunk / byte | memrb가 가득 차서 버린 양; record 수로 바꾸지 않음 |
| `fluentbit_input_files_rotated_total` | 누적 file | Tail이 관측한 회전; 그 자체가 손실 수는 아님 |
| `fluentbit_input_long_line_skipped_total` | 누적 occurrence | Tail의 긴 줄 생략; 버퍼 크기·skip 설정과 함께 해석 |
| `fluentbit_processor_items_drop_total` | 누적 item | processor에서 제거한 항목; signal·processor 단계와 의도한 정책을 구분 |
| `fluentbit_input_ingestion_paused` | gauge 0/1 | input 수집이 pause된 상태; pause 횟수가 아님 |
| `fluentbit_input_storage_overlimit` | gauge 0/1 | input storage 한도 초과 상태; 유실 개수를 나타내지 않음 |
| `/api/v1/storage`의 chunk·byte 통계 | 상태값 | buffered 자료와 메모리/파일시스템 상태; 누적 전송량과 구분 |

버전 경계도 지표별로 다릅니다. memrb drop과 pause·overlimit gauge는 **v4.1.0 코드에도 존재**하며, files_rotated_total도 같은 버전의 Tail에서 확인됩니다. processor items_drop_total은 비교한 v4.2.0에는 없고 v5.0.0에는 있습니다. long_line_skipped_total은 여기서는 v5.1.3 제공을 확인한 범위로 쓰며 최초 도입 버전은 확정하지 않습니다. [v4.1.0 input 지표](https://github.com/fluent/fluent-bit/blob/v4.1.0/src/flb_input.c), [v4.1.0 memrb 폐기 계정](https://github.com/fluent/fluent-bit/blob/v4.1.0/src/flb_input_chunk.c), [v4.1.0 Tail](https://github.com/fluent/fluent-bit/blob/v4.1.0/plugins/in_tail/tail_config.c), [v5.0.0 processor](https://github.com/fluent/fluent-bit/blob/v5.0.0/src/flb_processor.c), [v5.1.3 Tail](https://github.com/fluent/fluent-bit/blob/v5.1.3/plugins/in_tail/tail_config.c)

Fluent Bit의 `Retry_Limit`은 chunk에 적용됩니다. filesystem buffering을 써도 무한 보존은 아닙니다. output의 `storage.total_limit_size`가 차면 해당 논리 목적지 큐의 가장 오래된 chunk를 버려 공간을 만듭니다. memrb도 한도 초과 때 가장 오래된 chunk를 버리는 별도 경로이며 해당 input drop 계수를 봅니다. input pause 동안 파일이 회전·삭제되는 조건도 따로 조사합니다. [buffering과 한도](https://docs.fluentbit.io/manual/administration/buffering-and-storage), [5.1.3 폐기 경로](https://github.com/fluent/fluent-bit/blob/v5.1.3/src/flb_input_chunk.c), [pause 계정](https://github.com/fluent/fluent-bit/blob/v5.1.3/src/flb_input.c), [overlimit 계정](https://github.com/fluent/fluent-bit/blob/v5.1.3/src/flb_storage.c)

여러 output으로 fan-out하면 성공·폐기 수가 목적지마다 생깁니다. 이를 합쳐 “원본 로그 손실 수”로 만들지 않습니다. 필터가 record를 추가하거나 multiline을 합치는 경우에도 입력−출력의 단순 차이는 손실이 아닐 수 있습니다. Collector의 `send_failed_*`는 [그 버전의 전달 계약](telemetry-delivery-contracts.md)에 따라 해석하며 Fluent Bit의 retry counter로 이름만 치환하지 않습니다.

제품 적용 제안: 원천 마지막 읽기 시각·파일 수명/offset·input 성공·의도한 filter 제거·buffer·output 실패·저장 수신·검색 가능을 단계별로 표시합니다. pipeline 설정 변경과 restart를 경계로 남기고, 분기·변환이 없는 같은 record 집합에서만 수지 계산을 합니다. 합성 sentinel 로그로 도착 여부를 확인하는 검사는 별도 트래픽이며 자연 발생 로그 전체를 증명하지 않습니다.

HTTP metric endpoint 조회는 읽기 전용이지만, 먼저 HTTP server·storage metrics가 구성되어야 하고 접근 제어가 필요합니다. 이를 켜는 것은 설정 변경입니다. 이 장에서는 endpoint를 켜거나 로그 전송 장애를 실행하지 않았습니다. 수집 빈도·응답량·endpoint 노출 범위도 설계에 포함합니다.

## 수집 연동을 완료했다고 판단할 근거

다음은 어댑터를 실제 구현할 때 수행할 검증 항목입니다. 이 문서 작성 중 실제 연동을 실행했다는 뜻은 아닙니다.

1. 알려진 입력을 만들고 원천 단위·type·관측 범위와 결과를 대조합니다.
2. 대상 재시작·삭제·ID 재사용 시 Counter와 대상 수명이 분리되는지 확인합니다.
3. 수집 권한 제거, API pagination 중간 실패, 전송 단절을 각각 재현합니다.
4. 중복·역순·늦은 도착을 주입하고 집계값과 품질 상태를 비교합니다.
5. 부하를 높여 수집 자체의 CPU·메모리·I/O와 폐기 정책을 측정합니다.

## 이해 확인

1. HTTP 200을 받았으면 모든 OTLP 항목이 저장되었는가? **부분 성공 본문과 수신 서버의 계약을 확인해야 한다.**
2. 영속 큐가 있으면 무한 장애 시간을 견디는가? **용량·디스크·재시도 조건에 한계가 있다.**
3. 변환 작업자가 재시작하면 누적값의 차이를 바로 계산할 수 있는가? **이전 값과 수명 정보를 복원하지 못하면 불확실한 첫 구간을 따로 처리해야 한다.**
4. retries_failed 1은 로그 1건 유실인가? **Fluent Bit의 해당 단위는 chunk이므로 포함 record 수가 필요합니다.**
5. drop counter가 0이면 원천 로그가 모두 검색 가능한가? **수집 전 손실·가시성 지연 등 관측 밖의 경계가 남습니다.**

관련: [식별과 관계](entities-and-topology.md), [저장과 조회](storage-and-query.md), [제품 자체 관측](self-observation-and-access.md)

이전: [관측 대상의 식별과 시간에 따른 관계](entities-and-topology.md) · 다음: [관측 데이터 전송 계약: 부분 성공, 재시도와 중복](telemetry-delivery-contracts.md) · [분야 목차](README.md)
