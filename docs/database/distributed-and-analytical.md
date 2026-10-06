# 문서형, 분산형, 분석형 DB의 관측

> 상태: 검토됨 · 적용 범위: MongoDB 8.0, Cassandra 공식 구조, DynamoDB 읽기, ClickHouse MergeTree · 원천 확인일: 2026-10-03 · 실습 여부: 원천·가상 예시 중심; 연결 실습의 범위는 본문

## 먼저 이해할 것

분산 DB는 데이터를 여러 노드에 나누거나 복제하고, 분석 DB는 많은 데이터를 읽어 집계하는 작업에 맞춘 구조를 사용할 수 있습니다. 한 노드가 정상이어도 특정 shard나 replica에 문제가 있을 수 있습니다. 클러스터 합계와 각 데이터 분할의 진행을 함께 보는 이유입니다.

SQL 사용 여부만으로 DB의 성능과 일관성을 분류하기는 어렵습니다. 데이터 모델, 분할, 복제, 읽기·쓰기 보장과 백그라운드 작업을 나눠 이해해야 합니다.

## MongoDB: 라우터와 저장 노드

MongoDB의 샤딩 배치는 데이터 분할을 담당하는 shard, 라우팅을 담당하는 mongos, 클러스터 메타데이터를 관리하는 config server 역할을 구분합니다. 하나의 클라이언트 요청이 여러 shard에 작업을 유발할 수 있습니다. [MongoDB 8.0 Sharding](https://www.mongodb.com/docs/v8.0/sharding/)

따라서 mongos 요청 수와 각 mongod 실행 수를 모두 합쳐 사용자 요청 수로 표시하지 않는 설계를 제안합니다. 요청→라우터→대상 shard의 관계와 각 시간 경계를 보관합니다.

MongoDB의 읽기는 read preference, read concern, 세션과 write concern의 조합에 따라 보장이 달라집니다. 비동기 복제본에서 읽으면 원본보다 오래된 데이터를 볼 수 있고, majority 읽기는 모든 상황에서 전역 최신 읽기라는 뜻으로 일반화할 수 없습니다. [MongoDB Read Isolation and Consistency](https://www.mongodb.com/docs/v8.0/core/read-isolation-consistency-recency/)

## MongoDB 지표의 범위

`serverStatus`의 `opLatencies`는 인스턴스 단위 작업 지연을 제공하고 mongos의 값에는 저장 노드와의 통신이 포함됩니다. `opWorkingTime`은 별도 작업 시간 관측이며 잠금·flow control 대기 등을 같은 방식으로 포함하지 않습니다. 서로 다른 정의를 동일한 지연 시계열로 합치지 않습니다. [MongoDB serverStatus](https://www.mongodb.com/docs/v8.0/reference/command/serverstatus/)

실행 계획에서는 반환 문서 수와 검사한 문서·인덱스 키 수를 비교할 수 있습니다. 이 값은 서로 다른 작업량이며 하나의 사용률로 대체하지 않습니다. [MongoDB Explain Results](https://www.mongodb.com/docs/v8.0/reference/explain-results/)

가상 예시로 문서 100,000개를 검사해 10개를 반환했다면 `10,000 검사 문서/반환 문서`입니다. 비용이 클 가능성을 조사할 단서지만 쿼리의 목적, 인덱스와 데이터 분포를 확인해야 하며 이 비율에 보편적인 장애 임계값을 두지 않습니다.

## Cassandra: 복제 수와 응답 수

Cassandra는 요청별 consistency level로 필요한 복제본 응답 수를 정합니다. 일반 쓰기는 consistency level과 관계없이 관련 복제본에 보내며 성공 응답에 필요한 수가 달라집니다. RF(replication factor, 복제본 수)=3에서 QUORUM은 2개 응답을 요구합니다. [Cassandra Dynamo Architecture](https://cassandra.apache.org/doc/stable/cassandra/architecture/dynamo)

가상 집합 `{A,B,C}`에서 쓰기 응답 `{A,B}`와 읽기 응답 `{B,C}`는 B에서 겹칩니다. 여기서 N은 복제본 수, R은 읽기 응답 수, W는 쓰기 응답 수입니다. `R+W>N`은 이러한 교집합을 설명하지만 동시 쓰기, 실패한 쓰기, 시간표와 전체 트랜잭션의 모든 보장을 대신하지 않습니다. 원자적 조건부 변경에 쓰는 lightweight transaction은 별도 일관성 경로입니다. [Cassandra Guarantees](https://cassandra.apache.org/doc/latest/cassandra/architecture/guarantees.html)

제품에는 coordinator와 replica의 지연, consistency level, 오류 종류, 대상 partition의 편중을 함께 기록하도록 제안합니다. 클러스터 평균만 보면 특정 partition의 과부하가 가려질 수 있습니다.

## 저장 구조의 백그라운드 비용

Cassandra compaction은 SSTable을 병합하고 오래된 자료를 정리하는 저장소 작업입니다. 삭제 표식인 tombstone도 관련 조건을 만족할 때 정리되므로 삭제 요청과 즉시 공간 회수는 같은 사건이 아닙니다. [Cassandra Compaction](https://cassandra.apache.org/doc/latest/cassandra/managing/operating/compaction/overview.html)

관측 설계에는 전면 요청 지연뿐 아니라 compaction 진행·대기, 디스크 여유, 읽기 증폭과 정리 지연을 포함합니다. 쓰기 요청이 줄어도 백그라운드 I/O가 계속되는 원인을 설명할 수 있어야 합니다.

## DynamoDB의 읽기 경계

DynamoDB에서 테이블과 local secondary index는 강한 일관성 읽기를 선택할 수 있지만 global secondary index와 stream 읽기는 같은 지원 범위가 아닙니다. 따라서 “DynamoDB 읽기”라는 이름만으로 동일한 신선도 보장을 지정하지 않습니다. [DynamoDB Read Consistency](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.ReadConsistency.html)

제품은 기본 테이블·인덱스·리전·요청 설정을 분리하고 제한·재시도·지연을 그 범위에 맞춰 관측하도록 제안합니다.

## ClickHouse: 분석 작업의 다른 단위

MergeTree는 정렬된 데이터 part와 백그라운드 병합을 사용하는 테이블 엔진입니다. primary key는 희소 인덱스로 검색 범위를 줄이는 역할을 하며 일반적인 관계형 PK처럼 유일성을 강제하는 의미는 아닙니다. [ClickHouse MergeTree](https://clickhouse.com/docs/reference/engines/table-engines/mergetree-family/mergetree)

가상 분석에서 요청 수가 같아도 읽는 행이 100만→1억으로 늘면 처리량 부담은 달라집니다. 제품은 쿼리 수뿐 아니라 읽은 행·바이트, 메모리, spill, part와 병합 작업을 관측 대상으로 명세하는 것이 좋습니다. 엔진마다 실제 지원 필드와 집계 범위는 별도 검증합니다.

## 이해 확인

1. RF=3, QUORUM이면 데이터를 정확히 2곳에만 보내는가? **성공에 필요한 응답 수와 전송 대상 수는 다릅니다.**
2. 삭제 성공이면 즉시 저장 공간이 줄어드는가? **정리·병합 등의 후속 작업이 있을 수 있습니다.**
3. MergeTree primary key는 일반적인 유일성 제약인가? **같은 의미가 아닙니다.**

관련: [캐시·메시징·검색](../middleware/README.md) · [스토리지](../storage/README.md) · [DB 목차](README.md)

이전: [SQL Server와 Oracle: 대기와 실행 통계](sqlserver-oracle.md) · 다음: [시계열·그래프·문서·열 지향 DB를 비교하는 기준](specialized-data-models.md) · [분야 목차](README.md)
