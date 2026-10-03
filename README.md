# 통합 모니터링 도메인 지식

통합 모니터링 제품을 설계·구현하는 개발자를 위한 한국어 지식서입니다. 시스템이 동작하는 원리부터 관측 대상, 지표의 단위·계산·한계, 도메인 간 장애 분석과 제품 설계까지 연결합니다.

**[한 파일로 전체 읽기 — BOOK.md](BOOK.md)** · [학습 안내](docs/reading-guide.md) · [용어집](docs/glossary.md) · [지표 참조표](docs/metric-catalog.md)

현재 12개 분야에 상세 본문 58장을 작성했습니다. 각 장에는 공식 자료의 근거와 적용 범위, 계산 또는 분석 예시, 이해 확인을 담았습니다. 예시 수치는 가상 입력이며 실측 결과와 구분합니다. 실제 작성 범위와 추가 주제는 [집필 현황](docs/coverage.md), 수행한 점검은 [검증 기록](docs/validation.md)에 적습니다.

## 분야별 목차

| 분야 | 주요 내용 | 상세 본문 |
| --- | --- | ---: |
| [공통 관측](docs/foundations/README.md) | 시계열·분포·SLO·시간·추적·로그·프로파일 | 5장 |
| [호스트](docs/host/README.md) | CPU·메모리·I/O·프로세스·Windows·가상화·GPU | 7장 |
| [네트워크](docs/network/README.md) | 주소·DNS·TCP·UDP·TLS·HTTP·흐름·MTU·경로 | 5장 |
| [스토리지](docs/storage/README.md) | 블록·파일·객체, 성능·용량·복제·복구 | 2장 |
| [컨테이너](docs/containers/README.md) | 격리·수명·cgroup·이미지·파일시스템 | 3장 |
| [Kubernetes](docs/kubernetes/README.md) | 객체·Pod·배치·수집·통신·저장·워크로드·etcd | 6장 |
| [애플리케이션](docs/application/README.md) | 요청·동시성·풀·재시도·주요 런타임·사용자 경험 | 5장 |
| [데이터베이스](docs/database/README.md) | 트랜잭션·계획·엔진별 통계·복제·분산 DB | 7장 |
| [미들웨어](docs/middleware/README.md) | Redis·Kafka·RabbitMQ·검색·프록시·메시 | 5장 |
| [클라우드](docs/cloud/README.md) | 자원·API·집계·관리형·서버리스·네트워크 | 4장 |
| [도메인 간 분석](docs/cross-domain/README.md) | 느린 요청·자원 장애·적체·관측 중단 | 4장 |
| [제품 설계](docs/product/README.md) | 대상·관계·수집·저장·조회·알림·자체 관측 | 5장 |

본문은 특정 스택으로 제한하지 않습니다. 기술별 의미가 다르면 차이를 보존하고, 확인한 버전의 설명을 모든 제품·버전으로 확대하지 않습니다. 범위와 사실 확인 원칙은 [문서 범위](docs/scope.md)를 참고합니다.

## 수정과 검증

원문은 `docs/`에서 수정합니다. 통합본의 순서는 [book.json](book.json)에 정의합니다. 외부 패키지 없이 Python 3.11 이상에서 다음 명령을 실행할 수 있습니다.

```powershell
python scripts/build_book.py
python scripts/check_docs.py
python scripts/verify_examples.py
python scripts/build_book.py --check
```

이 명령은 문서 생성·검사와 가상 예시의 산술 검증만 수행합니다. 본문에 실린 OS 명령·DB 쿼리를 대상 시스템에 실행하지 않습니다.

새 주제는 [작성 가이드](CONTRIBUTING.md), [주제 템플릿](templates/topic.md), [지표 템플릿](templates/metric.md)에 따라 추가하고 분야별 목차와 집필 현황을 함께 갱신합니다.
