# 시계열·그래프·문서·열 지향 DB를 비교하는 기준

> 상태: 검토됨 · 적용 범위: 데이터 모델의 비교, InfluxDB OSS 2·Neo4j 문서 사례 · 원천 확인일: 2026-10-04 · 실습 여부: 원천·가상 예시 중심; 연결 실습의 범위는 본문

DB 종류를 배울 때 제품 이름을 먼저 외우기보다 “어떤 형태의 데이터를 어떤 질의로 읽는가”를 질문하면 이해하기 쉽습니다. 같은 1억 건이어도 시간 구간 집계, 한 주문 조회, 친구 관계 탐색은 다른 접근 패턴입니다. 어떤 모델이 항상 더 빠르다는 순위로 정리하지 않습니다.

## 모델과 작업을 연결하기

| 모델 | 대표적인 접근 | 모니터링에서 확인할 경계 |
| --- | --- | --- |
| 관계형 | 테이블·제약·조인·트랜잭션 | 실행 계획, 잠금, 로그, 연결 |
| 문서형 | 구조를 가진 문서와 필드 조회 | index, 문서 크기, shard 편중 |
| key-value | key로 값 읽기·쓰기 | key 분포, 요청 크기, eviction·지속성 정책 |
| 시계열 | 시간 범위와 차원별 집계 | 수집률, series 수, 시간 분할, 보존 |
| 그래프 | 정점과 관계를 따라 탐색 | 탐색 확장량, index 시작점, transaction 메모리 |
| 열 지향 분석 | 일부 열을 대량 스캔·집계 | 읽은 행·byte, pruning, merge·압축 |

표는 관측 설계를 위한 비교입니다. 실제 제품은 여러 모델을 제공하거나 기능을 겹쳐 지원할 수 있습니다. SQL 지원 여부만으로 내부 저장이 행 지향인지 열 지향인지 확정하지 않습니다.

## 시계열의 고유성

InfluxDB OSS 2는 measurement, tag set, field, timestamp 등의 데이터 요소를 정의합니다. tag와 field는 저장·질의 의미가 다르므로 바꿔 써도 동일하다고 가정하지 않습니다. 같은 measurement·tag set·timestamp의 point를 다시 쓰는 동작도 해당 엔진의 규칙을 확인합니다. [InfluxDB 2 데이터 요소](https://docs.influxdata.com/influxdb/v2/reference/key-concepts/data-elements/)

이 정의를 모든 TSDB에 일반화하지 않습니다. Prometheus는 metric 이름과 label set으로 시계열을 식별하고 sample timestamp와 값을 기록합니다. 같은 “메모리 사용량”이라도 entity 속성 변경을 label 변경으로 내보내면 새로운 series가 만들어질 수 있습니다. [Prometheus 데이터 모델](https://prometheus.io/docs/concepts/data_model/)

가상으로 host 100개×process 종류 20개×상태 4개가 모두 조합되면 8,000개 조합입니다. 여기에 재사용하지 않는 요청 ID를 label로 넣으면 이 고정 상한 모델이 무너집니다. 대량 적재에서 series 생성률, 활성 series, 삭제·보존 비용을 따로 봅니다.

## 그래프 탐색의 비용

그래프는 정점과 관계를 중심으로 연결을 표현합니다. 시작 정점 하나를 빠르게 찾더라도 이후 관계를 몇 단계 확장하는지가 작업량을 크게 바꿀 수 있습니다. 예시로 매 단계 새 이웃 10개를 만나고 중복이 없다고 가정하면 3단계 확장 후보는 `10+100+1,000=1,110`개입니다. 실제 planner의 비용이나 결과 행 수와 같다는 뜻은 아닙니다.

연결한 Neo4j Operations Manual의 metrics 기능은 **Enterprise Edition 전용**입니다. 그 안에서도 transaction, query, page cache, store, clustering 등의 가용 항목은 설정·버전에 따라 확인해야 하므로 문서에 이름이 있다는 것만으로 대상에서 수집된다고 가정하지 않습니다. [Neo4j metrics](https://neo4j.com/docs/operations-manual/current/monitoring/metrics/)

그래프 DB가 느리다는 보고에는 요청 개수뿐 아니라 출발점 선택, 확장 깊이·분기, 실제 결과 크기, 캐시, transaction 메모리 등의 가설을 세웁니다. 관계 수 증가와 지연이 함께 나타나도 동일한 질의 구성이었는지 확인해야 합니다.

## 쓰기 경로와 정리 작업

새 데이터를 빨리 수용한 뒤 나중에 merge·compaction으로 저장 구조를 정리하는 엔진에서는 foreground 성공만 보아서는 장기 부하를 알기 어렵습니다. 배경 작업 적체가 저장 공간·읽기 비용에 영향을 줄 수 있습니다. 엔진마다 의미가 달라 공통 “정리 지연”으로 무리하게 하나의 수치를 만들지 않습니다. [ClickHouse MergeTree](https://clickhouse.com/docs/engines/table-engines/mergetree-family/mergetree), [Cassandra compaction](https://cassandra.apache.org/doc/latest/cassandra/managing/operating/compaction/overview.html)

분산·분석 DB의 복제와 주요 엔진별 지표 해석은 [분산형과 분석형 DB](distributed-and-analytical.md)로 연결합니다. 이 장의 범주는 adapter를 설계할 출발점이며 완전한 엔진별 view 사전은 아닙니다.

## 제품 적용 제안과 이해 확인

공통 화면에는 요청 성공·지연·저장 사용·가시성 상태를 제공하되, 각 모델의 고유한 작업량 단위를 함께 유지합니다. “조회 1회”끼리만 비교하면 한 key 조회와 10억 행 스캔이 같은 작업으로 보이는 문제가 생깁니다.

1. SQL을 쓰면 모두 행 지향 저장인가? **질의 언어와 저장 모델은 다릅니다.**
2. 시계열에 label 하나를 추가해도 비용은 일정한가? **값의 종류와 조합 수가 중요합니다.**
3. 그래프 시작점이 1개이면 읽는 관계도 1개인가? **확장 깊이와 분기에 따라 커질 수 있습니다.**

이전: [문서형, 분산형, 분석형 DB의 관측](distributed-and-analytical.md) · 다음: [로그, 지속성, 복제와 복구](replication-and-recovery.md) · [분야 목차](README.md)
