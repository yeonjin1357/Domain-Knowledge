# 통합 모니터링 도메인 지식서

**제1.0판 · 2026-10-04 · 12개 분야 · 상세 본문 80장**

통합 모니터링 제품을 설계·구현하는 개발자를 위한 한국어 지식서입니다. 도메인을 처음 배우는 독자가 시스템의 구조부터 원천 지표, 계산, 장애 분석, 제품 설계까지 한 권으로 연결해 읽을 수 있게 구성했습니다.

## 바로 읽기

가장 편한 방법은 **[BOOK.html](BOOK.html)을 브라우저로 여는 것**입니다. 파일을 더블클릭하면 됩니다. 목차 검색과 그림이 포함되어 있고 본문과 그림은 인터넷 없이 읽을 수 있습니다. 출처를 열거나 연결된 실행 코드를 보려면 해당 자료에 접근해야 합니다.

```powershell
Start-Process .\BOOK.html
```

- [BOOK.md](BOOK.md): GitHub·Markdown 뷰어용 통합본
- [학습 안내](docs/reading-guide.md): 처음 읽는 순서와 목적별 경로
- [시스템 지도](docs/foundations/system-map.md): 호스트·프로세스·컨테이너·Pod·서비스의 관계
- [용어집](docs/glossary.md), [지표 참조표](docs/metric-catalog.md)
- [실제 재현 실습](docs/cross-domain/reproducible-labs.md), [종합 분석 연습](docs/cross-domain/capstone-investigation.md)

## 분야별 본문

| 분야 | 상세 장 | 배우는 내용 |
| --- | ---: | --- |
| [공통 관측](docs/foundations/README.md) | 8 | 시스템 지도, 시계열·분포·SLO·시간·추적, 성능과 분산 시스템 |
| [호스트](docs/host/README.md) | 9 | CPU·메모리·I/O·프로세스, Windows·VM·GPU, NUMA와 수집 계약 |
| [네트워크](docs/network/README.md) | 7 | DNS·TCP·TLS·HTTP, 라우팅·MTU, SNMP·OSPF·EVPN·QoS |
| [스토리지](docs/storage/README.md) | 3 | 저장 모델·성능·용량·복구, RAID·LVM·SAN·NAS |
| [컨테이너](docs/containers/README.md) | 4 | 격리·수명·파일 계층, cgroup v1/v2와 Windows 차이 |
| [Kubernetes](docs/kubernetes/README.md) | 8 | 객체·Pod·배치·수집·workload·etcd, CNI·CSI·Operator |
| [애플리케이션](docs/application/README.md) | 7 | 요청·연결 풀·재시도·런타임·사용자 경험·계측 |
| [DB](docs/database/README.md) | 10 | 트랜잭션·질의·주요 엔진·복제·HA·특수 모델·수집 SQL |
| [미들웨어](docs/middleware/README.md) | 6 | 캐시·로그·메시지·검색·프록시·스트림 처리 |
| [클라우드](docs/cloud/README.md) | 5 | 자원·API·지표·서버리스·네트워크·quota·비용 |
| [도메인 간 분석](docs/cross-domain/README.md) | 6 | 장애 가설과 증거, 실제 로컬 실습, 종합 연습 |
| [제품 설계](docs/product/README.md) | 7 | 대상·관계·수집·저장·알림·접근·어댑터·용량 |

## 근거와 검증

공식 문서·명세·API·연구 원문에 근거를 연결하고, 가상 계산·설계 제안·실제 실행 결과를 구분했습니다. **[검토·수정 기록](docs/review.md)**과 **[검증 기록](docs/validation.md)**에 확인한 내용과 적용 범위가 있습니다.

제1판은 읽을 수 있는 완성 원고입니다. 모든 제조사·모든 버전의 API 전수나 사용자 제품의 실제 지원 인증을 뜻하지 않습니다. 정확한 범위는 [범위 원칙](docs/scope.md)과 [분야별 범위](docs/coverage.md)를 따릅니다.

## 원문 수정과 재생성

원문은 `docs/`, 순서는 `book.json`에서 관리합니다. `BOOK.md`와 `BOOK.html`은 생성 결과입니다. Markdown과 계산 검사는 Python 표준 라이브러리만 사용하고, HTML 생성은 고정된 renderer 의존성을 사용합니다.

```powershell
python -m pip install -r requirements-docs.txt
python scripts/build_book.py
python scripts/build_html.py
python scripts/check_docs.py
python scripts/verify_examples.py
python scripts/verify_contracts.py
python scripts/build_book.py --check
python scripts/build_html.py --check
```

외부 URL 상태 조회와 실험 재실행은 [검증 기록](docs/validation.md)에 있습니다. 작성 규칙은 [CONTRIBUTING.md](CONTRIBUTING.md)를 참고합니다.
