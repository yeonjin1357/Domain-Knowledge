# 스트림 처리: event time, watermark, checkpoint와 역압

> 상태: 검토됨 · 적용 범위: Flink 1.20, Spark Structured Streaming 문서, Pulsar 4.0 사례 · 검토일: 2026-10-04 · 실제 분산 작업 실행 없음

메시지를 저장하는 것과 메시지로 계산한 결과를 완성하는 것은 다릅니다. 메시지 broker가 건강해도 소비 작업의 상태 복구, 시간창 집계, 외부 저장이 막힐 수 있습니다. 스트림 처리는 계속 들어오는 사건을 읽어 상태를 갱신하거나 결과를 내는 처리 모델입니다.

## 사건 시각과 처리 시각

event time은 사건에 붙은 발생 시각이고 processing time은 처리 시스템이 그 사건을 처리하는 시각을 기준으로 합니다. 지연·재전송으로 도착 순서가 발생 순서와 달라질 수 있습니다. Flink의 event time 처리는 timestamp와 watermark를 사용해 시간의 진행을 다룹니다. [Flink 1.20 time](https://nightlies.apache.org/flink/flink-docs-release-1.20/docs/concepts/time/)

예시로 10:00:58에 발생한 결제가 10:01:07에 도착했다면 도착 시각으로만 1분 집계하면 10:01 창에 넣게 됩니다. 업무가 발생 시각 기준 매출을 원하면 timestamp·시간창·늦은 사건 정책을 명시해야 합니다. 어떤 집계가 맞는지는 업무 정의에 달려 있습니다.

## watermark는 벽시계가 아니다

watermark는 event time의 진행을 나타내는 신호입니다. “늦은 사건이 절대로 더 오지 않는다”는 물리적 증명이 아니라 시스템의 생성·처리 정책에 따른 기준입니다. 여러 입력을 가진 연산자에서는 느리거나 유휴인 입력이 진행에 영향을 줄 수 있어 idle input 처리도 확인합니다. [Flink watermark](https://nightlies.apache.org/flink/flink-docs-release-1.20/docs/concepts/time/)

가상으로 입력 A watermark가 10:05, B가 10:01이면 모든 입력의 진행을 기다리는 구성에서 출력 event time이 B에 제한될 수 있습니다. CPU가 낮아도 창 결과가 나오지 않는 이유를 처리량만으로 찾기 어려운 사례입니다. 실제 결합 규칙은 엔진과 연산자에서 확인합니다.

## 역압 backpressure

뒤 단계가 충분히 소비하지 못하면 앞 단계의 전송·처리가 대기하는 것이 역압입니다. 병목 연산자 앞의 여러 연산자가 모두 막혀 보일 수 있어, 가장 앞에서 보이는 대기를 원인이라고 자동 판정하지 않습니다.

Flink의 `backPressuredTimeMsPerSecond`, `idleTimeMsPerSecond`, `busyTimeMsPerSecond`는 task의 시간 분류에 활용됩니다. 값의 제공 범위와 unavailable 표현을 확인하고 CPU 사용률과 동일시하지 않습니다. [Flink 역압 관측](https://nightlies.apache.org/flink/flink-docs-release-1.20/docs/ops/monitoring/back_pressure/)

예시로 source에 backlog가 있고 중간 task에 backpressure가 높으며 sink 요청 지연도 늘었다면 sink를 포함한 downstream 가설을 조사합니다. sink가 정상이라는 추가 증거가 있으면 serialization, 네트워크, 특정 partition 편중 같은 다른 가설로 범위를 바꿉니다.

## checkpoint와 처리 보장

checkpoint는 복구할 처리 상태와 진행 위치 등을 일관된 방식으로 저장하는 메커니즘입니다. checkpoint 완료율·소요 시간·실패·마지막 성공 나이와 실제 복구 성공을 구분합니다. state 크기가 늘면 저장·복구 비용이 달라질 수 있습니다. [Flink checkpoints](https://nightlies.apache.org/flink/flink-docs-release-1.20/docs/ops/state/checkpoints/)

정확히 한 번이라는 표현은 source 재생, 상태 복구, sink의 commit 또는 멱등성 등의 전제를 포함합니다. 모든 외부 HTTP 호출까지 자동으로 한 번만 실행된다고 확대하지 않습니다. Spark Structured Streaming도 source·sink와 처리 모드의 보장 범위를 설명하므로 해당 조합을 확인해야 합니다. [Spark Structured Streaming](https://spark.apache.org/docs/latest/streaming/getting-started.html#fault-tolerance-semantics)

예시로 마지막 checkpoint가 3분 전이고 그 이후 외부 API 호출이 100건 성공했다면, 복구 뒤 동일 입력이 재처리될 때 외부 효과를 어떻게 다룰지 별도 설계가 필요합니다. checkpoint의 존재만으로 외부 중복을 배제할 수 없습니다.

## Pulsar와 캐시의 추가 관측 경계

Pulsar는 subscription 유형에 따라 메시지 전달과 공유 방식이 달라집니다. topic의 backlog와 특정 subscription의 미처리 상태를 구분하고, acknowledgment·redelivery·retention의 경계를 보존합니다. broker 하나의 건강 상태만으로 모든 subscription 처리를 설명하지 않습니다. [Pulsar 4.0 messaging](https://pulsar.apache.org/docs/4.0.x/concepts-messaging/)

파이프라인이 Memcached 같은 캐시를 사용하는 경우에는 hits/misses, eviction, 연결, 저장 여유를 함께 확인합니다. item이 없어지는 것은 앱이 명시적으로 삭제한 경우 외에도 만료·메모리 관리 등과 연결될 수 있습니다. 캐시 hit 비율은 실제 요청 구성과 함께 읽습니다. [Memcached protocol의 stats 필드](https://github.com/memcached/memcached/blob/master/doc/protocol.txt)

## 제품 적용 제안과 이해 확인

파이프라인을 source → operator → sink로 표현하고, event time 지연·처리율·backpressure·state 크기·checkpoint·외부 업무 성공을 별도 관측합니다. 입력 offset의 진전만을 “업무 최신화”로 표시하지 않습니다.

1. CPU가 낮으면 stream 결과가 늦을 수 없는가? **watermark·입력 유휴·외부 대기를 봐야 합니다.**
2. checkpoint 성공이면 외부 결제도 정확히 한 번인가? **sink와 업무 멱등성의 보장 경계가 필요합니다.**
3. broker backlog와 사용자 화면의 최신성은 같은가? **소비 이후 계산·저장·조회 경계도 있습니다.**
