# 제1.1판 검증 기록

검증 기준일은 **2026-10-04**입니다. 공식 원천의 의미 검토, 자동 문서 검사, 실제 실행, 화면 확인의 범위를 나누어 기록합니다. 사용자 제품이나 운영 환경 전체의 지원 인증을 뜻하지 않습니다.

## 문서·계산·화면 검사

| 검사 | 확인 결과 | 확인하지 않는 것 |
| --- | --- | --- |
| 문서 구조·연결 | Markdown 116개, 상세 장 92개, 로컬 파일·앵커·목차 검사 | 모든 문장의 자동 사실 판정 |
| 통합본 | 원문 114개에서 BOOK.md·BOOK.html 생성·일치 확인 | 외부 원천의 미래 유지 |
| 기존 예시 | 51개 원문의 대표 검사 146개 | 모든 식의 자동 추출 |
| 제1.0판 계산·계약 | 본문과 연결한 계산 28개, 어댑터 사례 22개 | 사용자 제품의 어댑터 실행 |
| 제1.1판 계산·근거 | 추가 계산 12개·시간-값 쌍 정렬, 31개 실행 시나리오의 저장 결과·입력 hash 대조 | 검증 명령만으로 실험을 재실행하거나 사실을 자동 판정하는 것 |
| 수집 SQL | 본문의 PostgreSQL SQL과 실제 실행 입력 일치 | 다른 엔진 SQL 실행 |
| HTML | 화면·장 이동 6곳, 1440px·390px 폭, 그림 17개·내부 앵커·목차 검색 확인 | 모든 브라우저 조합 |

자동 문서·계산 검사는 Windows Python 3.11.9, HTML 생성은 markdown-it-py 4.0.0과 Mermaid 11.4.1 고정 bundle을 사용했습니다. Node 22.17.1과 별도 headless Chrome profile의 offline 모드에서 렌더링했습니다. 새 PostgreSQL 그림과 좁은 화면의 필드 계약표도 확인 대상에 포함했습니다. [화면 검사 기록](../review/html-check.json), [renderer 출처와 hash](../assets/mermaid-provenance.json)

숫자를 코드에 옮긴 대표 산술 검사는 전체 문장의 검증과 다릅니다. 공식 원천과 대조한 주요 주장·수정 이유는 [검토 기록](review.md)과 [사실 대조 기록](../review/fact-review-1.1.json)에 있습니다.

## 이번에 추가한 실제 실행 31개

실행 환경은 Ubuntu 24.04.3, WSL2 Linux 6.18.33.2-microsoft-standard-WSL2, Python 3.12.3, amd64입니다. Docker daemon을 사용할 수 없어 WSL의 일반 사용자와 로컬 추출 실행 파일을 이용했습니다. 시스템 패키지 설치, 기존 DB·클러스터 접속, cloud 계정 호출 없이 수행했습니다.

| 묶음 | 수 | 주요 확인 | 원시 기록 |
| --- | ---: | --- | --- |
| Linux | 4 | comm 파싱, CPU 원천 계정, 32MiB 매핑, 1MiB 파일 I/O | [JSON](../labs/results/1.1-linux.json) |
| PostgreSQL 18.6 | 11 | 격리 수준 2종, 잠금·timeout·실패·savepoint·deadlock·권한·통계 snapshot·수집 SQL | [JSON](../labs/results/1.1-postgresql.json) |
| Kubernetes API server 1.34.1·etcd 3.6.4 | 7 | 페이지 snapshot·watch·UID 교체·409·RBAC·selector 이탈·410 | [JSON](../labs/results/1.1-kubernetes.json) |
| OTel Collector 0.137.0 | 7 | HTTP JSON 성공·503 재시도·400·500·부분 성공·응답 유실·재시도 소진 | [JSON](../labs/results/1.1-otel.json) |
| HTTP/1.1 | 2 | 두 GET의 연결 재사용, HTTP 200 뒤 불완전 본문 | [JSON](../labs/results/1.1-http11.json) |

Linux의 기존 cgroup 읽기는 `observed`로 따로 기록했으며 31개 통과 시나리오에 더하지 않았습니다. CPU 검사의 통과는 파싱·원천 계정·산술의 확인입니다. 1초·2초 구간의 약 1.06 CPU초/경과초 차이는 원인 미해결로 남겼으며, 시계의 정확도 인증을 의미하지 않습니다.

Kubernetes 실험은 API server·etcd만 띄웠습니다. 실제 업무 Pod·kubelet·CNI·CSI는 없습니다. 410 재현에는 watch cache 비활성화와 전용 etcd의 physical compaction을 사용했습니다. Collector 실험은 sending queue를 끄고 목적지 응답을 통제했으며 gRPC·영속 저장·검색을 검증하지 않았습니다.

실행이 끝난 뒤 자기 임시 서버·연결을 종료하고 임시 인증서·DB·작업 파일을 정리했습니다. 추출한 고정 도구는 무시 경로 `.tools/`에 남겨 재실행에 사용합니다. 각 결과에는 실행 코드·입력 hash가 있어 이후 수정과 출판 증거의 불일치를 확인할 수 있습니다.

## 이전 판의 실제 실행 기록

| 실험 | 환경·입력 | 관측 |
| --- | --- | --- |
| SQLite | 3.45.1, WAL, 임시 DB 두 연결 | 10→10→20 snapshot, SQLITE_BUSY, 문장 오류 후 명시 rollback |
| HTTP/1.0 | Windows Python 3.11.9, loopback | client timeout 뒤 서버 처리, 재시도 2회·멱등 업무 효과 1회 |
| Windows API | 읽기 전용 시간 API, 짧은 자기 CPU 작업 | system idle·kernel·user와 process CPU 원천값 |
| PromQL | 공식 promtool 3.5.0, 합성 입력 | 표현식 8개·alert 5개 평가 성공 |

[제1.0판 결과 JSON](../labs/results/2026-10-04.json)과 [실습 해설](cross-domain/reproducible-labs.md)을 유지했습니다. 이번에는 저장 증거와 코드·입력의 일치를 다시 검사했으며 네 실험을 새로 실행한 기록으로 바꾸지 않았습니다.

## 외부 주소와 사실 확인

본문의 고유 URL **314개**를 HTTP로 조회했습니다. **307개는 200, 7개는 403**이며 404는 없었습니다. [source-status.json](../review/source-status.json)은 주소 접근 결과입니다. fragment의 정확성이나 모든 문장의 사실성을 자동 판정한 결과가 아닙니다.

403은 이전 판과 같은 MySQL 공식 문서 6개와 Little 논문 출판사 페이지 1개입니다. 이전 판에서 별도 웹 열람으로 내용을 확인한 기록을 유지했고, 이번 직접 요청에서도 접근이 제한된 사실을 따로 보존했습니다. 주소 조회일이 모든 주장을 새로 사실 검토한 날짜라는 뜻은 아닙니다.

## 실행하지 않은 범위

물리 Linux 장비 전체와 모든 procfs 필드, cgroup 제한·OOM·eviction, Kubernetes 1.35 서버·업무 workload·CNI·CSI, MySQL·SQL Server·Oracle 서버 질의, JVM·.NET 등 runtime agent 전수, 실제 DNS·TLS·HTTP/2, 상용 SNMP 장비, cloud 계정·비용 API, 분산 장애 전환·전원 장애·복구는 실행하지 않았습니다. 본문에서는 연결한 공식 원천의 적용 범위로 설명하며 해당 환경을 검증했다고 표시하지 않습니다.

## 문서 검사 재현

저장소 루트에서 실행합니다. HTML 생성 의존성만 별도 설치합니다.

```powershell
python -m pip install -r requirements-docs.txt
python scripts/build_book.py
python scripts/build_html.py
python scripts/check_docs.py
python scripts/verify_examples.py
python scripts/verify_contracts.py
python scripts/verify_revision.py
python scripts/build_book.py --check
python scripts/build_html.py --check
python scripts/check_html.py
```

`check_html.py`는 Node 22 이상과 Chrome을 사용합니다. Windows 기본 경로 외의 Chromium은 `--browser`로 지정합니다. URL 상태를 다시 확인하려면 `python scripts/check_sources.py`를 실행합니다. 상태는 출판 때와 달라질 수 있습니다.

## Linux 실습 재현

WSL을 포함한 Ubuntu 24.04 amd64의 일반 사용자로 **이 저장소의 Linux 경로**에서 실행합니다. Python 3, OpenSSL, dpkg-deb와 실행 파일의 공유 라이브러리가 필요합니다. PostgreSQL 도구는 Ubuntu 24.04 패키지의 의존성을 전제로 하므로 다른 배포판의 범용 설치기로 취급하지 않습니다. 다운로드 목록과 SHA256은 [PostgreSQL 패키지](../labs/postgresql/packages.json), [runtime archive](../labs/runtime-assets.json)에 고정했습니다.

```bash
python3 scripts/run_linux_lab.py
python3 scripts/run_http_lab.py
python3 scripts/get_postgres_lab.py
python3 scripts/run_postgres_lab.py
python3 scripts/get_runtime_lab_assets.py --which envtest
python3 scripts/run_kubernetes_lab.py
python3 scripts/get_runtime_lab_assets.py --which otelcol
python3 scripts/run_otel_lab.py
```

다운로드·실습은 별도 작업입니다. 기본 출력은 출판 기록을 덮지 않는 `.lab-runs/`입니다. `.tools/`, `.lab-runs/`, `.render-cache/`는 Git에서 제외합니다. 공식 archive·패키지와 기록된 checksum을 대조했으며 별도의 공급망 서명 검증을 수행한 것으로 표시하지 않습니다.

이전 Windows 실습은 `python scripts/get_promtool.py` 후 `python scripts/run_labs.py --promtool .tools/prometheus-3.5.0/promtool.exe`로 재현합니다. 재실행 때 시각·PID·UID·지연·일부 통계·재시도 횟수는 달라질 수 있습니다. 현재 문서와 연결한 출판 결과를 바꿀 때는 실행·원문 해석·검토 기록을 함께 갱신합니다.
