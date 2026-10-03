# Kafka: 파티션, offset, lag와 처리 보장

> 상태: 본문 초안 · 적용 범위: Apache Kafka 4.3, 일반 consumer group · 출처 확인일: 2026-10-03

Kafka를 관측할 때는 기록, 복제, 읽기, 업무 처리, offset commit을 구분해야 합니다. 소비자가 읽었다는 사실만으로 후속 DB 반영이 완료됐다고 할 수 없습니다.

## 로그와 파티션

Kafka의 topic은 partition으로 나뉘고 각 partition은 순서가 있는 로그를 제공합니다. 복제는 partition의 가용성과 내구성에 관여합니다. 여러 partition을 하나의 전역 순서로 간주하지 않습니다. [Kafka Design](https://kafka.apache.org/43/design/design/)

관측 키에는 클러스터, topic, partition, consumer group과 client 범위를 구분하도록 제안합니다. topic 전체 평균만 보면 한 partition에 작업이 몰리는 현상이 가려질 수 있습니다.

## 서로 다른 offset

consumer의 현재 position은 다음에 읽을 위치이고 committed position은 복구 시 사용할 저장 위치입니다. `endOffsets()`가 제공하는 경계도 isolation level에 따라 다릅니다. `read_uncommitted`에서는 high watermark, `read_committed`에서는 high watermark와 열린 트랜잭션 위치를 고려한 last stable offset을 사용합니다. [KafkaConsumer API](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html)

다음은 개념을 설명하는 합성 위치입니다.

```text
같은 경계에서 읽을 수 있는 끝 위치: 1,000
현재 consumer position:              950
저장된 committed position:           900

현재 위치 기준 차이: 50
commit 기준 차이:   100
```

이 차이는 서로 다른 질문에 답합니다. offset 공간에는 압축·트랜잭션 등의 영향이 있으므로 모든 환경에서 차이를 정확한 미처리 업무 메시지 수로 부르지 않습니다. 실제 처리 완료 위치는 애플리케이션의 commit 정책을 함께 알아야 합니다.

## 같은 lag 이름도 원천을 확인한다

Kafka consumer의 `records-lag-max`는 현재 offset 기준이며 committed offset 기준이 아닙니다. 창 안에서 partition별 lag의 최대를 나타내므로 합계 lag와도 다릅니다. [Kafka Monitoring](https://kafka.apache.org/43/operations/monitoring/)

제품에서는 다음을 지표 정의에 포함하도록 제안합니다.

- 끝 위치를 얻은 API와 격리 수준
- 현재·committed·업무 처리 중 어느 위치인지
- partition별 값, 합계, 최대의 구분
- 수집 시점 차이와 누락 partition
- consumer 재배치와 offset 초기화 여부

## lag의 증가율과 따라잡기

합성 예에서 처리 대기 작업을 직접 센 값이 60,000건이고 지속 유입이 800건/s, 완료가 1,000건/s로 일정하면 순감소는 200건/s입니다. 같은 조건이 계속되면 300초가 필요합니다. 이 계산은 offset 차이를 무조건 실제 건수로 간주한 것이 아니라 실제 작업 수가 알려진 모델입니다.

완료율이 유입률보다 낮으면 잔량이 늘어납니다. consumer 개수를 늘리는 선택은 partition 수, 할당, 병목과 처리 순서 제약을 확인한 뒤 평가합니다. consumer 개수만 늘면 언제나 처리율이 비례 증가한다는 보장은 없습니다.

## producer 확인과 업무 완료

producer의 acks와 idempotence 설정은 기록 확인과 재시도 중복 처리에 영향을 줍니다. idempotence와 관련 설정에는 함께 만족해야 하는 조건이 있으므로 옵션 이름 하나만으로 보장을 설명하지 않습니다. [Kafka Producer Configs](https://kafka.apache.org/43/configuration/producer-configs/)

Kafka 트랜잭션으로 관련 Kafka 작업을 묶는 보장과 외부 DB·HTTP 부작용까지 정확히 한 번 수행하는 보장은 범위가 다릅니다. 제품에서는 broker 기록 성공, 읽기 성공, consumer의 업무 성공을 분리해 관측하도록 제안합니다. 외부 시스템과의 원자성이 필요한 경우에는 별도 프로토콜과 중복 처리 설계를 확인합니다.

## 가상 진단

lag가 증가하고 broker는 여유롭다면 consumer 처리 시간, DB 호출, 재시도와 할당 변화를 봅니다. 반대로 producer 지연과 복제 상태 변화가 함께 나타나면 broker·저장소·복제 경로를 조사합니다. 네트워크 byte rate만으로 어느 단계인지 단정하지 않습니다.

## 이해 확인

1. position 기준 lag와 commit 기준 lag는 같은가? **참조 위치가 다릅니다.**
2. 최대 lag를 더하면 모든 partition의 합계인가? **집계 의미가 다릅니다.**
3. broker 기록 성공이면 후속 업무가 완료됐는가? **소비와 업무 결과를 따로 확인해야 합니다.**

다음: [메시지 큐](message-queues.md) · [미들웨어 목차](README.md)
