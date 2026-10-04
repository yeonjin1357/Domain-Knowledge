# 제1판 검증 기록

검증 기준일은 **2026-10-04**입니다. 원문 작성·사실 검토·자동 검사·실제 실행·화면 확인의 범위를 구분합니다. 사용자 제품이나 운영 환경 전체의 인증을 뜻하지 않습니다.

## 문서와 계산

| 검사 | 확인 결과 | 확인하지 않는 것 |
| --- | --- | --- |
| 문서 구조·연결 | Markdown 104개, 상세 장 80개, 원문 목차와 로컬 파일·앵커 검사 통과 | 모든 문장의 자동 사실 판정 |
| 통합본 | 원문 102개에서 BOOK.md·BOOK.html 재생성 및 일치 검사 | 외부 링크의 미래 유지 |
| 기존 예시 | 51개 원문의 산술·단위·해석 반례 146개 통과 | 모든 식을 원문에서 자동 추출하는 기능 |
| 새 예시 | 본문의 기대 표현과 연결한 계산 28개 통과 | 모든 현실 상황의 수치 보장 |
| 어댑터 계약 | 정상·0·reset·누락·중복·큰 정수 등 22개 사례 통과 | 모든 제품 어댑터의 구현 검증 |
| 실습 근거 | 저장된 script·fixture hash와 실제 성공 결과 대조 | 과거 실행 환경의 영구 재현 보장 |
| HTML | desktop·장 이동·좁은 화면 확인, 그림 13개 렌더링, 내부 앵커 검사 | 모든 브라우저 조합의 인증 |

문서 구조·산술·계약 검사는 Python 3.11.9에서 실행했습니다. HTML 생성에는 markdown-it-py 4.0.0과 Mermaid 11.4.1의 고정 bundle을 사용했습니다. 브라우저 확인은 Node 22.17.1과 독립된 headless Chrome profile을 사용하고, DevTools의 offline 모드에서 그림을 렌더링했습니다. 1440px와 실제 390px 폭, 장 이동, 목차 검색을 확인했습니다. [화면 검사 기록](../review/html-check.json), [renderer 출처와 hash](../assets/mermaid-provenance.json)

산술 검사는 일부 입력을 코드에 옮긴 대표 검사입니다. 직접 원문과 결합한 검사를 추가했지만 모든 문장의 수식을 자동 검증한다고 표시하지 않습니다. 기술 내용의 검토 결과와 중요한 수정은 [검토 기록](review.md)에 따로 있습니다.

## 실제 실행한 네 가지 실험

| 실험 | 입력·환경 | 관측 결과 |
| --- | --- | --- |
| SQLite | 3.45.1, WAL, 두 연결, 임시 DB | snapshot 읽기 10→10→20, 두 번째 writer SQLITE_BUSY, 실패 문장 후 명시 rollback |
| HTTP | Python 3.11.9, 127.0.0.1, HTTP/1.0 | client timeout 뒤 서버 처리, 같은 key 재시도 2회·업무 효과 1회 |
| Windows API | 현재 PC, 읽기 전용 시간 API와 짧은 CPU 작업 | system idle·kernel·user와 process CPU 원천값 및 계산 |
| PromQL | 공식 promtool 3.5.0, 합성 fixture | 표현식 8개·alert 5개, SUCCESS |

자세한 순서와 해설은 [재현 실습](cross-domain/reproducible-labs.md), 원시 증거는 [결과 JSON](../labs/results/2026-10-04.json)에 있습니다. 실제 프로그램을 실행했어도 합성 입력은 실제 고객 트래픽이라고 부르지 않습니다. 단기 CPU 관측은 장비 성능 benchmark가 아닙니다.

Docker 실행 파일은 있었지만 daemon에 연결할 수 없는 환경이었습니다. 이 때문에 Docker 기반 PostgreSQL·Kubernetes 실험이 수행된 것으로 표시하지 않았고, 사용할 수 있는 로컬 SQLite와 독립된 promtool·HTTP·Win32 실습을 실행했습니다.

## 외부 원문 확인

본문에 인용한 고유 URL **291개**를 직접 HTTP 조회했습니다. **284개는 200**, **7개는 403**이었습니다. 최종 조회에서 404는 없었습니다. 원시 결과는 [source-status.json](../review/source-status.json)에 있습니다. 이는 링크 fragment의 유효성이나 본문 사실 전체를 자동 인증한 결과가 아닙니다.

403은 MySQL 공식 문서 6개와 Little 논문의 출판사 페이지 1개입니다. 이 페이지들은 별도 웹 열람으로 공식 내용을 확인했으며 자동 요청의 접근 제한과 구분했습니다. 독자의 접속 환경에 따라 웹페이지 접근 상태가 달라질 수 있습니다. 확인 과정에서 NUMA 문서의 잘못된 경로를 수정하고 CAP 논문은 접근 가능한 MIT 원문으로 연결했습니다.

## 실행하지 않은 범위

Linux 진단 명령·procfs 수집, 실제 Kubernetes 조회·CNI·CSI, 서버 PostgreSQL·MySQL·SQL Server·Oracle 질의, 상용 SNMP 장비, 실제 cloud 계정·비용 API, 분산 장애 전환·복구는 이 판에서 실행하지 않았습니다. JVM·.NET 등 runtime별 agent와 모든 PromQL 예제도 전수 실행한 것이 아닙니다. 해당 본문은 명시된 공식 자료의 설명이며 실제 배포의 권한·설정·부하·버전 검증은 별도입니다.

## 재현 명령

저장소 루트에서 실행합니다. HTML 생성 의존성만 별도 설치가 필요합니다.

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

로컬 실습과 HTTP 상태 조회는 다음과 같습니다. 네트워크 상태는 출판 당시와 달라질 수 있습니다. 기본 결과 경로는 출판 기록을 덮지 않는 `.lab-runs/`입니다.

```powershell
python scripts/get_promtool.py
python scripts/run_labs.py --promtool .tools/prometheus-3.5.0/promtool.exe
python scripts/check_sources.py
python scripts/check_html.py
```

`check_html.py`는 Node 22 이상과 Chrome을 사용합니다. Windows의 Chrome 기본 경로 외에 다른 Chromium 실행 파일은 `--browser`로 지정합니다. `.tools/`, `.lab-runs/`, `.render-cache/`는 Git에서 제외합니다. 원문 변경 후에는 해당 내용과 결과의 검토를 마친 뒤 통합본과 [장별 기록](../review/chapter-review.json)을 갱신합니다.
