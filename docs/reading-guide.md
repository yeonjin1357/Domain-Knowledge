# 이 지식서를 읽는 방법

이 책은 통합 모니터링 제품을 만드는 개발자가 도메인 지식을 처음부터 익히도록 구성한 제1판입니다. 낯선 용어가 나와도 외부 문서를 모두 읽어야 다음으로 넘어가도록 구성하지 않았습니다. 핵심 설명은 본문에 두고 출처는 그 설명을 확인할 근거로 연결했습니다.

## 한 파일로 읽기

**[BOOK.html](../BOOK.html)을 브라우저에서 열면** 목차 검색·표·그림을 포함한 전체를 읽을 수 있습니다. 본문 검색은 Ctrl+F를 사용합니다. Markdown을 선호하면 [BOOK.md](../BOOK.md), 작은 파일별 탐색은 [분야별 목차](../README.md)를 사용합니다. 내용의 원본은 `docs/`이며 두 통합본은 같은 원문에서 생성됩니다.

## 처음 읽는 순서

처음에는 [시스템 지도](foundations/system-map.md)부터 읽습니다. 호스트·프로세스·서비스·컨테이너·Pod가 어떻게 다른지 이해한 뒤 개별 지표로 들어가면 용어를 외우는 부담이 줄어듭니다.

| 단계 | 읽을 내용 | 스스로 설명해 볼 질문 |
| --- | --- | --- |
| 1 | 시스템 지도 → 시계열 → 분포 → 성능과 통계 | 현재값·누적값·평균·p95는 어떤 질문에 답하는가? |
| 2 | CPU → 메모리 → I/O → 주소·DNS → TCP → TLS·HTTP | 실행과 대기는 어떻게 다르고 어느 경계에서 시간이 걸리는가? |
| 3 | 컨테이너 격리 → cgroup → Pod 수명 → 배치 → CNI·CSI | 호스트가 한가한데 컨테이너가 제한되거나 Pod가 준비되지 않을 수 있는가? |
| 4 | 요청 → 연결 풀 → transaction·잠금 → 쿼리 → 복제·HA | 요청이 어떤 자원을 기다리고 언제 성공했다고 말할 수 있는가? |
| 5 | 캐시·Kafka·메시지·검색·스트림 → 클라우드 | 처리 진행과 실제 업무 완료를 어떻게 구분하는가? |
| 6 | 실제 실습 → 종합 분석 연습 → 제품 설계 | 원천의 뜻과 불확실성을 수집·저장·화면까지 보존할 수 있는가? |

모든 분야를 한 번에 암기할 필요는 없습니다. 첫 번째로 읽을 때는 개념과 계산 예시를 따라가고, 두 번째에는 자신의 제품에서 사용할 원천 필드·권한·수명·결측 처리를 확인합니다. Windows·GPU·특정 DB처럼 당장 필요하지 않은 구현 사례도 공통 개념을 익힌 뒤 찾아볼 수 있습니다.

## 각 장을 읽는 방법

기존 58장에는 선수 개념을 풀어 쓴 “먼저 이해할 것”을 추가했습니다. 새 장도 상황과 쉬운 설명에서 시작합니다. 이어서 동작·원천·예시·한계·제품 적용·이해 확인을 읽습니다. 예시의 숫자를 한 번 직접 계산하면 어떤 분모와 시간 범위를 사용하는지 확인할 수 있습니다.

낯선 약어는 [용어집](glossary.md)에서 짧은 정의를 보고 연결된 장으로 돌아옵니다. 표에 있는 수치가 임계값인지, 가상의 계산 입력인지, 실제 측정값인지도 확인합니다.

## 목적별 찾아보기

| 목적 | 경로 |
| --- | --- |
| 새 수집기 구현 | [시계열](foundations/time-series.md) → [호스트 계약](host/collection-contracts.md) / [SNMP](network/snmp-and-device-models.md) / [DB 계약](database/collection-contracts.md) → [어댑터 계약](product/adapter-contracts.md) |
| 느린 요청 조사 | [trace](foundations/traces-logs-profiles.md) → [연결 풀](application/servers-and-pools.md) → [잠금](database/transactions-and-locks.md) → [사례](cross-domain/slow-requests.md) |
| 실행·자원 장애 조사 | CPU·메모리 → cgroup·Pod → [자원 장애](cross-domain/resource-failures.md) |
| 대상·관계 설계 | 프로세스·Pod·cloud ID → [entity와 topology](product/entities-and-topology.md) |
| 알림 구현 | [데이터 품질](foundations/time-and-data-quality.md) → [SLO](foundations/service-level-objectives.md) → [알림](product/alerts-and-incidents.md) → [PromQL 실습](cross-domain/reproducible-labs.md) |
| 용량 계획 | [성능과 통계](foundations/performance-and-statistics.md) → [보존과 질의](product/storage-and-query.md) → [용량과 손실 예산](product/capacity-and-loss-budgets.md) |

## 문장의 종류

| 표시 | 읽는 방법 |
| --- | --- |
| 공식 출처·적용 버전 | 그 범위의 정의와 동작 |
| 가상·합성·설명용 | 학습을 위한 입력과 상황; 실제 성능 수치 아님 |
| 실제 실행·실습 | 기록한 버전과 설정에서 얻은 결과 |
| 제품 적용 제안 | 사용자의 현재 구현을 확인한 사실이 아닌 설계 제안 |
| 가설·가능성 | 더 확인할 설명 후보 |
| 실행 미검증 | 공식 설명은 있지만 이 환경에서 실행하지 않은 예제 |

장의 `검토됨`을 모든 환경의 실행 인증으로 읽지 않습니다. [검토 기록](review.md)과 [검증 기록](validation.md)에 범위를 분리했습니다.

## 끝까지 유지할 질문

어떤 수치에도 **누구의 값인지, 어디서 쟀는지, 단위와 분모가 무엇인지, 어느 시간의 값인지, 어떻게 집계했는지, 수집이 성공했는지**를 묻습니다. 이 질문들을 설명할 수 있으면 기술 이름이 바뀌어도 원천을 읽고 새 도메인을 제품에 연결할 출발점을 갖게 됩니다.
