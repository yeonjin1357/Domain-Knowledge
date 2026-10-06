# 미들웨어 도메인

> 상태: 검토됨 · 적용 범위: 캐시·메시징·검색·프록시·스트림의 관측 개요, Kafka 4.3 문서 예시 · 원천 확인일: 2026-10-06 · 실습 여부: 각 상세 장에 명시

## 적체처럼 보여도 세는 단위가 다르다

| 원천 | 표시하는 적체 | 같게 취급하면 안 되는 값 |
| --- | --- | --- |
| Kafka consumer lag | 지정한 끝·소비 위치의 offset 차이 | 남은 시간, 항상 정확한 업무 건수 |
| RabbitMQ ready / unacked | 전달 대기 / 전달 후 소비자 확인 대기 메시지 | broker의 한 종류의 대기열 길이 |
| Pulsar backlog | 해당 subscription의 backlog; batching 사용 시 메시지 개수가 아니라 batch(entry) 수 | 모든 구독이 공유하는 전역 lag나 개별 메시지 수로 환산하지 않음 |

Pulsar의 이 단위는 메시징 문서의 backlog size 설명에 따른 것입니다. 모든 Pulsar 지표가 batch 단위라는 뜻은 아닙니다. [Pulsar 4.1 batching](https://pulsar.apache.org/docs/4.1.x/concepts-messaging/#batching)

정확한 범위와 확인 경계는 [Kafka](kafka.md), [메시지 큐·Pulsar](message-queues.md)를 따릅니다. Redis·Memcached는 [캐시](cache-redis.md), 계산 진행과 역압은 [스트림 처리](stream-processing.md)로 구분합니다.

미들웨어 영역에서는 애플리케이션 사이에서 데이터를 보관·전달·검색하는 시스템을 다룹니다. 요청이 성공했는지와 함께 데이터가 어느 단계까지 처리됐는지 이해하는 것이 목적입니다.

## 기본 구성과 관측 질문

| 영역 | 이해할 개념 | 우선 관측할 항목 |
| --- | --- | --- |
| 캐시 | 적중·미적중, 만료·제거, 메모리 한도 | 요청·지연, 적중 비율, 메모리, 제거된 항목 |
| 메시징 | 생산·저장·소비, 확인·재시도, 파티션 | 유입·처리량, 대기량, 소비 진척, 실패 |
| 검색 | 색인, 샤드, 검색·색인 요청 | 검색·색인 지연, 거부된 작업, 샤드 상태 |
| 프록시·mesh | 세션·요청·upstream·재시도 | 큐, 연결, 오류·응답 단계 |
| 스트림 처리 | 상태·checkpoint·역압 | 처리 진행·복구·유입 조절 |

표는 공통 관측 모델 제안입니다. Redis·Memcached, Kafka·RabbitMQ·Pulsar, Elasticsearch·OpenSearch 등을 상세 문서의 대상으로 포함하고 각 제품의 용어와 처리 보장을 따로 설명합니다.

## Kafka에서 확인할 수 있는 예시

Kafka 4.3 문서의 소비자 지표 `records-lag-max`는 관측 구간에서 파티션별 lag(offset 차이)의 최댓값이며, 커밋된 오프셋이 아닌 현재 오프셋 기준입니다. 따라서 지표 이름에 lag가 있다는 이유만으로 모든 소비 지연 지표를 같은 값으로 취급하면 안 됩니다. [Apache Kafka Monitoring](https://kafka.apache.org/43/operations/monitoring/)

이 사례를 바탕으로 지연 지표에는 기준 위치, 집계 단위, 단위가 레코드 수인지 시간인지 명시하는 방식을 제안합니다.

## 장애 분석 예시

| 증상 | 가능한 가설 | 확인할 증거 |
| --- | --- | --- |
| 캐시 사용 이후 DB 부하 증가 | 요청 구성·적중 결과·만료 패턴 변화 | 캐시 결과와 DB 호출량의 같은 시간대 변화 |
| 메시지 처리 지연 증가 | 생산량 증가, 소비 정체, 특정 파티션 집중 | 유입·처리량과 파티션·소비자별 진척 |
| 검색 응답 지연 증가 | 요청 변화, 작업 대기, 저장 계층 지연 | 요청별 특성, 작업 큐, 샤드와 호스트 상태 |

표는 검증할 가설입니다. 큐나 지연의 크기만으로 업무 완료 시각을 단정하지 않고, 실제 처리 완료 지점의 관측값과 비교합니다.

## 제품 적용 제안

생산자·브로커·소비자 또는 호출자·캐시·DB를 연결하는 탐색을 검토합니다. 공통 지표 이름을 사용하더라도 원천 지표의 의미와 제품별 차이를 확인할 수 있게 합니다.

## 상세 본문

1. [캐시와 Redis: 적중, 메모리, 만료와 지속성](cache-redis.md)
2. [Kafka: 파티션, offset, lag와 처리 보장](kafka.md)
3. [메시지 큐: 발행 확인, 전달, 처리와 재전달](message-queues.md)
4. [검색 엔진: 색인, 가시성, shard와 요청 지연](search-engines.md)
5. [프록시, 로드밸런서와 서비스 메시](proxies-and-mesh.md)
6. [스트림 처리: event time, watermark, checkpoint와 역압](stream-processing.md)

관련 문서: [애플리케이션](../application/README.md), [DB](../database/README.md), [스토리지](../storage/README.md)

이전: [PostgreSQL 실제 실습: 같은 값, 잠금 대기와 실패한 트랜잭션](../database/postgresql-concurrency-lab.md) · 다음: [캐시와 Redis: 적중, 메모리, 만료와 지속성](cache-redis.md)
