# 검색 엔진: 색인, 가시성, shard와 요청 지연

> 상태: 검토됨 · 적용 범위: Elasticsearch·OpenSearch 공식 API의 주요 의미 · 출처 확인일: 2026-10-03 · 편집 검토일: 2026-10-04

## 먼저 이해할 것

검색 엔진은 문서를 빠르게 찾도록 index를 만들고 shard 단위로 나누어 보관할 수 있습니다. 쓰기 성공 뒤 검색에 보일 때까지의 경계와 장애 시 데이터 보존은 다릅니다. 클러스터 색상은 shard 상태 요약이므로 실제 검색 지연과 정확한 결과까지 함께 확인합니다.

문서를 쓰는 성공, 검색에 보이는 시점, 디스크에 보존되는 시점은 구분해야 합니다. 검색 품질과 클러스터 배치 상태 역시 다른 지표입니다.

## refresh와 검색 가시성

Elasticsearch의 refresh는 새 segment를 열어 최근 변경을 검색에 보이게 하는 과정입니다. 이는 완전한 디스크 commit과 동일한 작업이 아닙니다. refresh 정책에 따라 쓰기 응답 직후의 검색 결과가 달라질 수 있습니다. [Elasticsearch Near Real-Time Search](https://www.elastic.co/docs/manage-data/data-store/near-real-time-search)

가상으로 문서 쓰기 응답을 10:00:00.100에 받고 검색에 10:00:01.000에 보였다면 900 ms의 가시성 지연을 관측한 것입니다. 이를 단순 쓰기 API 지연과 합치지 않습니다. 본문에서는 모든 배포의 고정 refresh 간격이나 가시성 보장 시간을 가정하지 않습니다.

## shard 배치의 건강 상태

Elasticsearch와 OpenSearch의 cluster health에서 green은 primary와 replica shard가 할당된 상태, yellow는 primary는 할당됐지만 일부 replica가 할당되지 않은 상태, red는 일부 primary가 할당되지 않은 상태를 표현합니다. 이 상태는 모든 쿼리의 지연이나 검색 결과의 업무 정확도를 보증하지 않습니다. [Elasticsearch Cluster Health](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-cluster-health), [OpenSearch Cluster Health](https://docs.opensearch.org/latest/api-reference/cluster-api/cluster-health/)

가상 계산으로 primary shard 6개에 replica를 각각 1개 두면 배치 대상 복제본은 총 12개입니다. 집계 저장량을 볼 때 primary만 센 값과 replica까지 포함한 값을 구분해야 합니다. 둘을 다시 더하면 primary를 중복 셀 수 있습니다.

## 검색 요청의 시간

Elasticsearch 응답의 `took`은 coordinating node가 요청을 받은 뒤 응답을 보낼 준비까지 측정한 ms입니다. 클라이언트에서 본 전체 왕복 시간과 같은 경계가 아닙니다. [Elasticsearch Search API](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-search)

따라서 클라이언트 300 ms, took 100 ms라는 합성 사례에서 나머지 200 ms를 모두 네트워크 지연으로 확정하지 않습니다. 풀 대기, 요청 직렬화, 전송, 응답 크기와 소비, 프록시를 조사해야 합니다.

## 색인과 검색은 자원을 공유한다

제품 관측 설계에는 다음을 구분하도록 제안합니다.

| 작업 | 관측 질문 |
| --- | --- |
| 문서 수집·색인 | 도착률, 성공·거부, 문서·배치 크기 |
| refresh·merge | 작업 빈도·시간, 메모리·I/O 영향 |
| 검색 | 쿼리 지연, 읽은 범위, 응답 크기, 실패 shard |
| 배치·복구 | 할당되지 않은 shard와 이동·복구 진행 |
| JVM·OS | GC, CPU, 디스크 여유·I/O, 파일 핸들 |

정확한 원천 필드는 엔진별로 확인하며 Elasticsearch API를 OpenSearch에 모두 동일하게 적용한다고 가정하지 않습니다.

## 가상 장애 해석

클러스터는 green인데 검색 p99가 증가하면 요청 분포, 고비용 집계, 특정 shard 집중, JVM 정지와 I/O를 조사합니다. green 상태를 이유로 검색 장애를 배제하지 않습니다.

검색 응답의 HTTP 상태가 성공이어도 부분 결과나 timeout 관련 필드가 업무 요구에 맞는지 확인하는 결과 모델을 제안합니다. 실패 shard를 허용하는 검색과 전체 결과가 필수인 검색은 서로 다른 SLI를 가질 수 있습니다.

## 이해 확인

1. 쓰기 응답 성공과 검색 가시성은 같은 시점인가? **refresh 등 별도 단계가 있습니다.**
2. green이면 모든 검색이 빠른가? **배치 상태와 성능은 다릅니다.**
3. took 밖의 시간은 모두 네트워크 시간인가? **클라이언트와 중계의 여러 단계가 포함될 수 있습니다.**

관련: [JVM](../application/managed-runtimes.md) · [스토리지](../storage/README.md) · [미들웨어 목차](README.md)
