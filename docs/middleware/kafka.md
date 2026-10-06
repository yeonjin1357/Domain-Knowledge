# Kafka: 파티션, offset, lag와 처리 보장

> 상태: 검토됨 · 적용 범위: Apache Kafka 4.3, 일반 consumer group · 원천 확인일: 2026-10-06 · 실습 여부: 원천·가상 예시 중심; 연결 실습의 범위는 본문

## 먼저 이해할 것

Kafka에서는 topic을 partition으로 나누고 그 안의 로그 위치로 처리 진행을 설명합니다. 소비자가 읽은 위치와 다시 시작할 때 사용할 commit 위치는 다를 수 있습니다. offset 차이가 언제나 남은 업무 개수와 같지는 않으므로 데이터 보존·압축·transaction과 소비 규칙을 함께 확인합니다. 제품은 기록·복제·읽기·업무 처리·offset commit을 서로 다른 완료 단계로 다룹니다.

## 용어 먼저

| 용어 | 이 장에서의 뜻 |
| --- | --- |
| partition | topic을 나눈 순서 있는 로그 단위; 서로 다른 partition 사이 전역 순서는 없음 |
| consumer group | partition 소비를 분담하는 소비자 집합 |
| position / committed position | 다음에 읽을 위치 / 복구 시 쓸 저장 위치 |
| lag | 선택한 끝 위치와 소비 위치의 offset 차이; 시간 단위 아님 |
| leader / ISR | partition의 주도 replica / 충분히 동기화된 replica 집합 |
| HW / LSO | high watermark(성공적으로 복제된 마지막 메시지의 offset + 1) / transaction 가시성을 고려한 last stable offset |
| KRaft controller | Raft 기반 metadata 관리·제어 역할; broker 데이터 처리와 구분 |

각 값의 정확한 경계는 아래 API·운영 정의를 따릅니다. [Kafka 설계](https://kafka.apache.org/43/design/design/), [Consumer API](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html)

## 로그와 파티션

Kafka의 topic은 partition으로 나뉘고 각 partition은 순서가 있는 로그를 제공합니다. 복제는 partition의 가용성과 내구성에 관여합니다. 여러 partition을 하나의 전역 순서로 간주하지 않습니다. [Kafka Design](https://kafka.apache.org/43/design/design/)

관측 키에는 클러스터, topic, partition, consumer group과 client 범위를 구분하도록 제안합니다. topic 전체 평균만 보면 한 partition에 작업이 몰리는 현상이 가려질 수 있습니다.

## 서로 다른 offset

용어표의 ISR에는 **leader 자신도 포함**됩니다. HW·LSO의 경계는 [KafkaConsumer endOffsets API](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/KafkaConsumer.html), ISR 범위는 [min.insync.replicas 정의](https://kafka.apache.org/43/configuration/topic-configs/#min.insync.replicas)를 근거로 읽습니다.

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

가상 예시에서 처리 대기 작업을 직접 센 값이 60,000건이고 지속 유입이 800건/s, 완료가 1,000건/s로 일정하면 순감소는 200건/s입니다. 같은 조건이 계속되면 300초가 필요합니다. 이 계산은 offset 차이를 무조건 실제 건수로 간주한 것이 아니라 실제 작업 수가 알려진 모델입니다.

완료율이 유입률보다 낮으면 잔량이 늘어납니다. consumer 개수를 늘리는 선택은 partition 수, 할당, 병목과 처리 순서 제약을 확인한 뒤 평가합니다. consumer 개수만 늘면 언제나 처리율이 비례 증가한다는 보장은 없습니다.

## producer 확인과 업무 완료

producer의 acks와 idempotence 설정은 기록 확인과 재시도 중복 처리에 영향을 줍니다. idempotence와 관련 설정에는 함께 만족해야 하는 조건이 있으므로 옵션 이름 하나만으로 보장을 설명하지 않습니다. [Kafka Producer Configs](https://kafka.apache.org/43/configuration/producer-configs/)

Kafka 트랜잭션으로 관련 Kafka 작업을 묶는 보장과 외부 DB·HTTP 부작용까지 정확히 한 번 수행하는 보장은 범위가 다릅니다. 제품에서는 broker 기록 성공, 읽기 성공, consumer의 업무 성공을 분리해 관측하도록 제안합니다. 외부 시스템과의 원자성이 필요한 경우에는 별도 프로토콜과 중복 처리 설계를 확인합니다.

## 가상 진단

lag가 증가하고 broker는 여유롭다면 consumer 처리 시간, DB 호출, 재시도와 할당 변화를 봅니다. 반대로 producer 지연과 복제 상태 변화가 함께 나타나면 broker·저장소·복제 경로를 조사합니다. 네트워크 byte rate만으로 어느 단계인지 단정하지 않습니다.

## broker와 controller의 건강을 따로 관측한다

소비자 lag가 늘었을 때 소비 코드가 느린 것인지, 복제·leader 문제로 데이터를 읽거나 쓰지 못하는지 구분해야 합니다. **Kafka 4.3 공식 문서, 2026-10-05 확인** 기준의 주요 gauge는 다음과 같습니다. [monitoring 정의](https://kafka.apache.org/43/operations/monitoring/)

| MBean의 name | 수집 위치·단위 | 의미와 해석 |
| --- | --- | --- |
| `UnderReplicatedPartitions` | broker `ReplicaManager`, partition 수 | ISR 수가 전체 replica 수보다 적음; 곧바로 쓰기 불가라는 뜻은 아님 |
| `UnderMinIsrPartitionCount` | broker `ReplicaManager`, partition 수 | ISR 수가 `min.insync.replicas`보다 적음; `acks=all` 쓰기 조건과 함께 해석 |
| `ActiveControllerCount` | `KafkaController`, 노드별 0/1 | active controller 여부; 정상 안정 상태에서 해당 controller 집합의 합이 1인지 확인 |
| `OfflinePartitionsCount` | `KafkaController`, partition 수 | controller가 관측한 offline partition; broker의 offline replica 수와 구분 |

앞 두 이름의 prefix는 `kafka.server:type=ReplicaManager,name=`, 뒤 두 이름은 `kafka.controller:type=KafkaController,name=`입니다. KRaft에서 controller 전용 노드를 구성하면 broker만 scrape해서 controller 지표가 안 보일 수 있습니다. 이 이름들이 모두 KRaft 전용이라는 뜻도 아닙니다. 4.0부터 ZooKeeper 모드는 제거됐지만 이전 계열에서 존재하던 지표와 새로운 KRaft metadata/quorum 지표를 구분합니다. [4.0 업그레이드](https://kafka.apache.org/40/getting-started/upgrade/)

**가상 예시:** replication factor=3, min ISR=2, 현재 ISR=2인 partition은 under-replicated지만 under-min-ISR은 아닙니다. ISR=1로 줄면 두 조건에 모두 해당합니다. 두 gauge를 더해 “장애 partition 총수”를 만들면 중복됩니다. 단발적인 controller 0 관측은 leader 전환·수집 시차·누락과 함께 조사합니다. [UnderMinIsr 도입 정의](https://cwiki.apache.org/confluence/spaces/KAFKA/pages/70257093/KIP-164-%2BAdd%2BUnderMinIsrPartitionCount%2Band%2Bper-partition%2BUnderMinIsr%2Bmetrics)

**버전 메모 — 중복 계수 주의:** Kafka 4.3.0 KRaft의 `ControllerServer`는 각 controller에 metadata 지표 publisher를 등록합니다. `OfflinePartitionsCount`는 각 controller가 적용한 metadata의 클러스터 전체 offline partition 수이므로 controller별 값을 더하면 중복됩니다. **제품 적용 제안:** 같은 클러스터의 active controller 값을 우선 사용하고, 여러 replica의 최댓값을 보조 신호로 표시할 때도 수집 시각·metadata 적용 지연을 남깁니다. 최댓값이 언제나 최신 상태라는 보장은 없습니다. [publisher 등록](https://github.com/apache/kafka/blob/4.3.0/core/src/main/scala/kafka/server/ControllerServer.scala#L378), [offline 계정](https://github.com/apache/kafka/blob/4.3.0/metadata/src/main/java/org/apache/kafka/controller/metrics/ControllerMetadataMetricsPublisher.java)

## share group은 committed offset 한 개로 설명하지 않는다

KIP-932의 share group은 한 partition을 여러 consumer가 협력해 읽고 개별 record를 acknowledge할 수 있는 모델입니다. 공식 릴리스는 **4.2에서 production-ready**라고 명시하며, 4.0의 early access 설명을 4.3의 상태로 사용하지 않습니다. record를 가져오면 시간 제한 acquisition lock이 생기고, 처리 결과의 acknowledge·release·재전달을 구분합니다. [4.2 릴리스](https://kafka.apache.org/blog/2026/02/17/apache-kafka-4.2.0-release-announcement/), [KafkaShareConsumer](https://kafka.apache.org/43/javadoc/org/apache/kafka/clients/consumer/KafkaShareConsumer.html)

일반 consumer group의 연속 committed offset과 달리 share partition 안에는 available·acquired·acknowledged·archived 상태가 섞입니다. KIP-1226의 lag 모델은 시작 offset 이후의 범위에서 이미 terminal 상태로 처리된 항목을 제외합니다. 따라서 단순 `끝 offset−start offset`만으로 계산하면 이미 처리한 항목까지 남은 것으로 셀 수 있습니다. compacted/control record의 간극은 확인 전에는 lag에 포함될 수 있으므로 이것도 정확한 남은 업무 건수와 항상 같지는 않습니다. [Share partition lag 설계](https://cwiki.apache.org/confluence/spaces/KAFKA/pages/390761228/KIP-1226%2BIntroducing%2BShare%2BPartition%2BLag%2BPersistence%2Band%2BRetrieval), [4.3 운영 조회](https://kafka.apache.org/43/operations/basic-kafka-operations/)

제품 적용 제안은 `group type`, lag 원천 API·버전·start offset, acquisition·acknowledge·release 관측을 함께 저장하는 것입니다. Kafka의 acknowledge도 외부 DB 업무 결과와 원자적으로 연결했는지까지 증명하지 않습니다. JMX·Admin API 조회에는 대상 인증·인가가 필요하고 전체 topic/partition의 고빈도 조회는 비용이 커집니다. 이 절에서는 broker·JMX·CLI를 실행하거나 원격 JMX를 활성화하지 않았습니다.

## 이해 확인

1. position 기준 lag와 commit 기준 lag는 같은가? **참조 위치가 다릅니다.**
2. 최대 lag를 더하면 모든 partition의 합계인가? **집계 의미가 다릅니다.**
3. broker 기록 성공이면 후속 업무가 완료됐는가? **소비와 업무 결과를 따로 확인해야 합니다.**
4. UnderReplicated와 UnderMinIsr를 더하면 장애 partition 총수인가? **두 조건이 겹칠 수 있습니다.**
5. share group lag를 consumer committed offset 차이로 대체해도 되는가? **개별 획득·확인·terminal 상태를 다루는 별도 모델입니다.**

이전: [캐시와 Redis: 적중, 메모리, 만료와 지속성](cache-redis.md) · 다음: [메시지 큐: 발행 확인, 전달, 처리와 재전달](message-queues.md) · [분야 목차](README.md)
