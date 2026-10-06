# 제1.2판 검증 기록

판 기준일은 **2026-10-06**입니다. 제1.2판은 상세 100장·통합 원문 122개로 구성됩니다. 과거 실행·원천 확인·화면 기록은 각각의 날짜와 적용 파일을 보존합니다. 아래 발행 검사와 이어지는 라운드별 이력을 구분하며 사용자 제품의 운영 지원 인증을 뜻하지 않습니다.

## 제1.2판 발행 검사 — 2026-10-06

발행 작업은 현재 판 표기·변경 요약·검증 안내를 갱신하고 BOOK.md·BOOK.html을 재생성했습니다. 제1.1판의 기존 31개 시나리오와 세 라운드에서 출판한 실행 결과·verdict·입력 hash는 변경하지 않았습니다. [판별 변경 요약과 라운드별 묶음 수](review.md#제12판에서-달라진-내용), [보존 근거 연결](../review/evidence-provenance.json)

| 기본 검사 | 1.2판 결과와 범위 |
| --- | --- |
| `check_docs.py` | PASS: 상세 100장, UTF-8·구조·목차·로컬 링크·장별 검토 hash |
| `verify_examples.py` | PASS: 60개 원문에 연결한 산술·해석 185개 |
| `verify_contracts.py` | PASS: 어댑터 경계 22개·본문 계산 28개·저장 실습 hash |
| `verify_revision.py` | PASS: 기존 31개 시나리오·추가 계산 12개·1라운드 시계·2라운드 36개 판정·3라운드 27개 판정/525 gzip의 저장 근거 |
| `build_book.py --check` | PASS: 제1.2판·2026-10-06 표기의 BOOK.md가 원문 122개와 일치 |
| `build_html.py --check` | PASS: BOOK.html이 동일 원문·판 정보·고정 renderer와 일치 |

Windows Python에서 아래 여섯 기본 검사를 실행했습니다. 판 표기·장 수를 목차와 대조했고 보존 실습 파일 및 상세 라운드 기록이 변경되지 않았음도 확인했습니다. 검증 스크립트의 성공을 새 실습 실행이나 모든 문장의 자동 사실 판정으로 해석하지 않습니다.

이번 발행에서는 Linux/DB 실습·외부 URL 전수 조회·브라우저 화면 검사를 새로 실행하지 않았습니다. 기존 [화면 검사 기록](../review/html-check.json)은 이전 3f 통합본의 hash에 해당하며 1.2판 생성본의 화면 PASS가 아닙니다. HTML 자동 생성 일치와 브라우저 표시 검사를 구분합니다. 아래 3f·3e 등의 절은 당시 결과와 제한의 이력입니다.

## 3f MySQL r2 출판과 3라운드 검증

Claude가 2026-10-06 KST(원문 UTC 10월 5일)에 실행한 [8.4.11 r2](../labs/results/1.1-r3/mysql-8.4.11-r2.json)·[9.7.2 r2](../labs/results/1.1-r3/mysql-9.7.2-r2.json)를 각각 **supported 5, gzip 132개** 그대로 출판했습니다. 입력 hash·압축 전후 hash·SQL/XML·NULL·정리 완료를 검사했습니다. r1의 반증 4개는 판정 설계 결함의 이력으로 보존했으며 최종 r2 숫자로 덮지 않았습니다.

두 버전 모두 next-key sys 행의 0→1 전이와 blocker 해제 뒤 삽입을 확인했습니다. GTID 직후 SBS 12/14와 coordinator 위치 일치 뒤 0을 함께 검사하고, 재개 직후에는 SBS=0이어도 위치가 다른 표본이 있었음을 보존했습니다. 최종 복제 값은 baseline 0·IO 중지 NULL·SQL 중지 NULL·재개 0입니다. [본문의 조건·전후 값](database/mysql-operations.md)

3라운드 출판 누계는 **7묶음·27개 판정(supported 23·refuted 4), gzip 525개**입니다. 이 중 최종 채택 실행은 메모리·분포·시계와 MySQL r2의 17개 supported 조건이며, 27에는 이전 r1 반복 실행을 포함합니다. 범용 제품 지원 인증으로 해석하지 않습니다.

| 검사 | 3f 범위·결과 |
| --- | --- |
| `check_docs` | PASS: 상세 100장·구조·목차·로컬 링크·검토 hash |
| `verify_examples` | PASS: 60개 원문의 산술·해석 185개 |
| `verify_contracts` | PASS: 어댑터 경계 22개·원문 연결 계산 28개·과거 실습 hash |
| `verify_revision` | PASS: 기존 근거와 3라운드 27개 판정·525개 gzip·입력·전후 SQL·본문 관측 |
| `build_book --check`, `build_html --check` | PASS: 원문 122개의 BOOK.md·BOOK.html과 생성 일치 |
| `verify_review_r3 --result …`·`--published` | PASS: r2 두 입력 및 출판 일곱 묶음, r1 verdict 유지·r2 가시성/위치 전이 |

3f의 Codex 검사는 저장 근거·코드와 생성 결과를 대조한 것입니다. WSL DB 실행은 Claude가 수행했습니다. 실행기·manifest·자산을 다시 고치지 않았으므로 이번 결과를 반영하기 위한 추가 DB 재실행은 필요하지 않습니다. [provenance](../review/evidence-provenance.json), [3f 기록](../review/claude-codex-r3.md)

Claude가 전달한 3e BOOK.html 화면 PASS는 수신 당시 HTML hash와 일치함을 확인하고 [receipt](../review/html-check-r3e-incoming.json)를 보존했습니다. 새 3f 생성본의 화면 검사 상태는 [검토 기록](../review/claude-codex-r3.md)에 별도로 남깁니다.

## 3e 당시 MySQL 결과 출판과 관측 조건 재검사

Claude가 2026-10-05 실행한 [MySQL 8.4.11](../labs/results/1.1-r3/mysql-8.4.11-r1.json)·[9.7.2](../labs/results/1.1-r3/mysql-9.7.2-r1.json)의 r1 JSON을 byte 그대로 복사하고 gzip 원자료 **200개 전체**를 보존했습니다. 각 supported 3·refuted 2를 유지합니다. 3e 당시 3라운드 누계는 요약 JSON **5개**, gzip **261개**, 판정 **17개(supported 13·refuted 4)**입니다. 이전 blocked 시도는 실행 이력으로 남기며 DB 관측 근거와 구분합니다.

원자료 재검사에서 next-key의 직접 잠금 관계와 rollback 뒤 INSERT 완료를 확인했지만 sys 행은 비어 있었습니다. 복제는 목표 GTID 실행을 기다렸지만 coordinator 위치가 뒤처져 SBS=0/NULL이라는 즉시 관측 조건을 만족하지 않았습니다. 9.7.2 재개 표본은 실제 SBS=1입니다. [분석 JSON](../review/mysql-r3e-analysis.json)·[본문 해석](database/mysql-operations.md)에 원천 SQL 참조와 코드 근거를 연결했습니다.

| 검사 | 3e 범위 |
| --- | --- |
| `check_docs` | 상세 100장의 구조·목차·로컬 링크·검토 hash |
| `verify_examples` | 기존 60개 원문의 산술·해석 185개 |
| `verify_contracts` | 어댑터 경계 22개·원문 연결 계산 28개·과거 실습 hash |
| `verify_revision` | 기존 근거와 3라운드 17개 판정·261개 gzip·실행 당시 입력 사본·본문의 핵심 관측 |
| `build_book --check`, `build_html --check` | 원문 122개로 재생성한 BOOK.md·BOOK.html과 일치 |
| `verify_review_r3 --published` | 다섯 묶음의 gzip·SQL 원문/요약·NULL 보존·판정·분석 수치·입력 hash; Linux 실행 없음 |
| `verify_review_r3` | 실제 r1에서 도출한 회귀 조건: sys 세션 일치·100 ms cache 경계·GTID와 coordinator 위치 분리·SBS로 대기하지 않음; 기존 parser·경로·정리 실패 검사 포함 |

6개 기본 검사와 두 추가 검사에서 PASS를 확인했습니다. **이는 저장 근거와 수정한 관측 코드의 오프라인 검사입니다.** 당시에는 sys view 재조회·coordinator 위치 대기를 보완한 r2 실행 전이었으며, 이후 실행·검증은 위 3f 절에 반영했습니다. 원래 runner는 [보존 사본](../labs/archive/review_r3_2026_10_05/mysql_r1/run_mysql_r3_lab.py)에 두고 [provenance](../review/evidence-provenance.json)로 연결했으므로 현재 입력 hash를 옛 결과에 소급 적용하지 않습니다.

Claude가 보낸 3d BOOK.html 화면 PASS는 [당시 receipt](../review/html-check-r3d-incoming.json)와 수신 당시 HTML hash를 대조했습니다. **당시 3e 생성본의 화면 검사는 후속 작업**이었으며, Claude가 전달한 PASS receipt를 3f에서 확인했습니다. 과거 화면 PASS를 새 생성본에 적용하지 않습니다. [새 실행·화면 검사 명령](../review/claude-codex-r3.md)

## 3d 당시 결과 출판과 재검사

2026-10-05 Claude 실행의 Linux 메모리·histogram·시계 상태를 [세 요약 JSON](cross-domain/reproducible-labs.md#3라운드-메모리분포시계의-작은-실험)과 gzip 원자료 61개로 출판했습니다. supported는 각각 4·2·1개입니다. 요약 파일은 전달 파일과 byte 단위로 같고, gzip 전후 hash·입력 hash·정리 완료·단위 환산·비용 중앙값·실제 promtool 출력을 검사합니다. 현재 manifest와 달라진 실행 입력은 당시 사본을 보존해 [provenance](../review/evidence-provenance.json)에 연결했습니다.

| 검사 | 3d 범위 |
| --- | --- |
| `check_docs` | 상세 100장의 구조·목차·로컬 링크·검토 hash |
| `verify_examples` | 기존 60개 원문의 산술·해석 185개 |
| `verify_contracts` | 기존 어댑터 경계 22개·원문 연결 계산 28개·과거 실습 hash |
| `verify_revision` | 과거 출판 근거에 3라운드 7개 판정·61개 gzip·입력 사본·본문 관측 계산 추가 |
| `build_book --check`, `build_html --check` | 원문 122개로 다시 생성한 BOOK.md·BOOK.html과 일치 |
| `verify_review_r3 --published` | 위 세 출판 묶음의 독립 검사; 실습·다운로드 없음 |
| `verify_review_r3 --assets` | 준비 입력·NULL/proc/PSI parser·원자료 무결성·경로/정리 실패·deb 경로/링크·ELF 경계, 공식 자산 receipt·파일 hash |

위 6개 기본 검사와 추가 검사에서 PASS를 확인했습니다. 이번 작업은 Windows Python에서의 저장 근거·준비 코드 검사이며 WSL 메모리·시계·promtool을 재실행하지 않았습니다. 조회 비용은 실제 30개 표본에서 다시 계산했으나 다른 프로세스·커널의 고정 비용으로 쓰지 않습니다. 강제 OOM·전역 압박·cgroup 생성 성공을 주장하지 않습니다.

MySQL 8.4.10·9.7.2의 이전 preflight blocked 기록은 성공 근거로 출판하지 않았습니다. **8.4.11의 공식 서명 검증·압축 해제·파일 hash**, libaio/libnuma의 고정 패키지·파일 대조와 AMD64 ABI 소스 검토까지 수행했습니다. 3d 당시에는 private alias 생성·Linux loader·두 MySQL 인스턴스 실행이 후속 작업이었습니다. **그때는 실제 잠금·복제 숫자를 적지 않았으며, 이후 실행 결과를 위 3e 절에 반영했습니다.** 3a의 준비 hash는 당시 기록으로 보존하고, 변경한 3d 준비 입력과 혼동하지 않습니다. [상세 판정·실행 명령](../review/claude-codex-r3.md)

이번 BOOK.html의 브라우저 화면 검사는 Claude가 수행합니다. 이전 `html-check`는 새 생성본의 시각적 검사를 대신하지 않습니다. 이번 사실 검토의 개별 공식 원천은 확인했으며 전체 외부 URL 상태 파일을 전수 재조회한 것은 아닙니다.

## 3b 당시 원고 보강의 검사 범위

2026-10-05에 새 3장과 기존 장의 Tier 3 설명을 보강했습니다. 상세 본문은 **100장**, 통합본의 원문은 **122개**입니다. 판 번호와 기준일은 유지했습니다. 주제별 공식 자료·고정 소스 확인, 채택하지 않은 단서와 이유는 [3라운드 기록](../review/claude-codex-r3.md), 검토한 원문 hash는 [장별 기록](../review/chapter-review.json)에 있습니다.

| 검사 | 3b 범위 |
| --- | --- |
| `check_docs` | 상세 100장, UTF-8·구조·로컬 링크·목차·검토 hash |
| `verify_examples` | 60개 원문의 산술·해석 185개; 새 15개는 본문 결과 문자열과 계산을 함께 대조 |
| `verify_contracts` | 기존 어댑터 경계 22개·원문 연결 계산 28개·보존 실습 hash |
| `verify_revision` | 기존 출판 근거와 1라운드 시계·2라운드 결과의 입력 hash·핵심 값 대조 |
| `build_book --check`, `build_html --check` | 원문 122개로 재생성한 BOOK.md·BOOK.html과 생성 일치 |

위 6개 명령을 Windows Python에서 `python -X utf8 -B scripts/<명령>.py` 형태로 실행해 모두 PASS를 확인했습니다. 문서 검사는 Markdown 124개·상세 100장·로컬 링크 2,241개를 검사했고, 외부 URL 546개는 목록화했습니다. 이 숫자가 모든 외부 URL의 재검증을 뜻하지는 않습니다.

**실행과 원고의 경계:** 3b 당시에는 Linux·MySQL·promtool·시계 실습을 실행하거나 새 결과를 출판하지 않았습니다. SQL Server·Oracle·runtime·GPU·로그 수집 명령도 실행하지 않았습니다. 당시 3a 준비 파일 16개의 저장 hash는 모두 일치했고 실행기·manifest·`.tools/`·`.lab-runs/`는 변경하지 않았습니다. 이후 3d에서 위와 같이 결과와 재준비를 반영했습니다.

새 HTML의 브라우저 화면 검사는 수행하지 않았습니다. 이전 `html-check` 기록은 이전 생성본에 해당하며 이번 생성본의 시각적 검증을 대신하지 않습니다. 외부 링크는 해당 사실을 검토할 때 열람했으며, 전체 URL 상태 목록의 전수 재검증은 하지 않았습니다.

## 2d 결과 출판과 재검사

Claude가 WSL Ubuntu 24.04·Linux 6.18.33.2·Python 3.12.3에서 실행한 네 최종 JSON을 byte 단위로 복사했습니다. 입력 hash와 원시 응답·로그·지표·SQL 결과를 대조했으며, 과거 1.1 실행 결과는 덮어쓰지 않았습니다. [출판·입력 연결](../review/evidence-provenance.json), [항목별 사실 판정](../review/claude-codex-r2.md)

| 실행 근거 | 판정 | 확인한 범위 |
| --- | --- | --- |
| [Kubernetes 1.34.1·1.37.0](../labs/results/1.1-r2-kubernetes.json) | supported 14·refuted 2 | 각 버전 cache true/false. cache-on Exact RV=1 LIST의 200·빈 목록 때문에 410 가설 2개 반증; 최신 patch·gate 인과는 미검증 |
| [Collector 0.162.0](../labs/results/1.1-r2-otel.json) | supported 14 | 내부 로그의 부분 거절, 재시도 소진 뒤 send_failed 증가, 메모리 queue의 upstream 수락 경계, exporter 이름 두 개의 구성 수용 |
| [PostgreSQL 18.6](../labs/results/1.1-r2-postgresql.json) | supported 4 | prepared transaction·logical catalog_xmin·slot 없는 standby feedback·단절 뒤 physical slot xmin의 회수 지연과 해제 |
| [promtool 3.13.4·3.15.0](../labs/results/1.1-r2-prometheus.json) | supported 2 | 각 버전에서 기존 규칙·합성 테스트 평가; 서버의 exemplar·WAL 기능 실행 아님 |

36개 판정 중 지지 34개·반증 2개입니다. `supported`는 실행기의 좁은 가설이 관측과 부합했다는 뜻이며 보편적 지원 인증이 아닙니다. 2d의 Codex 작업은 저장 근거 검사와 원천 대조이며 이 샌드박스에서 Linux 서버를 재실행하지 않았습니다.

| 검사 | 2d 확인 범위 |
| --- | --- |
| `check_docs` | 상세 97장의 UTF-8·구조·로컬 링크·목차·검토 hash |
| `verify_examples` | 57개 원문의 산술·해석 170개; Ceph EC 4+2의 기본 min_size=5 예시 추가 |
| `verify_contracts` | 기존 어댑터 경계 22개·원문 연결 계산 28개·보존 실습 hash |
| `verify_revision` | 기존 31개 시나리오·12개 계산·Linux 시계 추가 근거에 새 36개 출판 판정의 hash·핵심 값 검사 추가 |
| `verify_review_r2 --published` | 네 최종 결과의 입력·실행기·파일 hash, cache/queue/회수 경계 값과 판정 수; 도구 설치나 서버 실행 없음 |
| `verify_lab_r2_cleanup` | 저장소 안의 합성 fixture로 resolve/chmod/mode·삭제·로그·프로세스 종료 실패의 여섯 경로 검사 |
| 통합본 | 원문 119개에서 BOOK.md·BOOK.html 재생성, 두 `--check`로 생성 일치 검사 |

PostgreSQL의 성공한 실행은 DrvFs 권한 제약 때문에 Linux native tempdir의 **전용 0700 디렉터리**를 사용했고 결과에 삭제 완료를 기록했습니다. 이 실행 당시 [공통 모듈](../labs/archive/lab_r2_common_2026_10_05.py)을 보존한 뒤 실패 경로를 보완했습니다. 수정 helper의 Linux native 성공 경로 smoke와 이번 BOOK.html의 **화면 검사**는 Claude에게 넘깁니다. 자동 생성 일치 검사가 화면 검사를 대신하지 않습니다. [재현 명령·정리 범위](cross-domain/reproducible-labs.md)

새 문서의 SQL 예시·PDH·cloud·SNMP·kubelet workload·runtime 계측 전체를 실행한 것은 아닙니다. 2c의 버전 소스·명세를 개별 확인했지만 전체 외부 URL 상태 파일을 전수 재조회하지 않았습니다. 중간 실패·입력 hash 불일치 실행은 존재 이력만 남기고 출판에서 제외했습니다.

## 2b 원고 보강의 검사 범위

새 5장을 포함한 상세 97장을 목차·학습 안내·용어집·지표 참조표에 연결했습니다. G1–G12의 원천 확인·자체 수정·채택하지 않은 해석은 [2라운드 기록](../review/claude-codex-r2.md), 변경·추가 상세 21장의 검토 초점과 본문 hash는 [장별 기록](../review/chapter-review.json)에 있습니다.

| 검사 | 2026-10-05 확인 범위 |
| --- | --- |
| `check_docs` | Markdown 121개, 상세 97장, UTF-8·구조·로컬 링크·목차·장별 hash |
| `verify_examples` | 57개 원문의 산술·해석 169개; 이번 23개 추가 중 20개는 본문 결과 문자열도 대조 |
| `verify_contracts` | 기존 어댑터 경계 22개·원문 연결 계산 28개·보존 실습 hash |
| `verify_revision` | 기존 31개 시나리오·입력 hash·계산 12개, Linux 시계 추가 근거 4구간·idle 61표본 |
| 통합본 | 원문 119개에서 BOOK.md·BOOK.html 재생성; 두 `--check`로 생성 일치 검사 |
| Kubernetes 준비 | 1.34.1·1.37.0 전용 manifest·16개 조건 계획·receipt·binary hash·ELF 형식 확인; Linux 서버 실행 없음 |

위 표는 **2b 당시 기록**입니다. 당시 새 실습 결과는 출판하지 않았습니다. 새 SQL·PDH·cloud·SNMP·kubelet workload·runtime 계측 명령도 실행하지 않았고, HTML 화면 검사를 다시 하지 않았습니다. 기존 HTML 화면 기록의 hash는 이전 파일에 해당하므로 이번 생성본의 표시 검증을 대신하지 않습니다. 새 외부 링크는 관련 사실을 직접 열람했지만 전체 URL 상태 파일을 갱신한 전수 재조회는 하지 않았습니다.

공통 2a 실습 입력을 보존하기 위해 Kubernetes 전용 manifest를 분리했습니다. `.lab-runs/` 임시 fixture를 쓰는 `verify_review_r2.py`는 2b의 Codex 턴에 실행하지 않았으며 Claude의 결과 검증 명령으로 넘겼습니다. 2d에서 추가한 `--published`는 위 출판 파일을 읽기 전용으로 검사합니다. 준비와 결과 반영의 이력은 [Kubernetes 계획](../review/claude-codex-r2.md)에 있습니다.

## 1라운드 당시 문서·계산·화면 검사

| 검사 | 확인 결과 | 확인하지 않는 것 |
| --- | --- | --- |
| 문서 구조·연결 | Markdown 116개, 상세 장 92개, 로컬 파일·앵커·목차 검사 | 모든 문장의 자동 사실 판정 |
| 통합본 | 원문 114개에서 BOOK.md·BOOK.html 생성·일치 확인 | 외부 원천의 미래 유지 |
| 기존 예시 | 51개 원문의 대표 검사 146개 | 모든 식의 자동 추출 |
| 제1.0판 계산·계약 | 본문과 연결한 계산 28개, 어댑터 사례 22개 | 사용자 제품의 어댑터 실행 |
| 제1.1판 계산·근거 | 추가 계산 12개·시간-값 쌍 정렬, 31개 실행 시나리오의 저장 결과·입력 hash 대조 | 검증 명령만으로 실험을 재실행하거나 사실을 자동 판정하는 것 |
| Linux 시계 추가 근거 | busy 3개·sleep 1개 구간과 idle 61개 표본의 원시값·계산·hash·본문 수치 확인 | 외부 시간 교정, 조정 주체, 과거 1.06 표본의 원인 확정 |
| 수집 SQL | 본문의 PostgreSQL SQL과 실제 실행 입력 일치 | 다른 엔진 SQL 실행 |
| HTML | Claude가 전달한 1차 수정본: 화면·장 이동 6곳, 1440px·390px 폭, 그림 17개 통과. 1b 생성본: 생성 일치 통과, 화면 검사는 시간 초과로 미완료 | 1b 생성본의 화면 표시, 모든 브라우저 조합 |

자동 문서·계산 검사는 Windows Python 3.11.9, HTML 생성은 markdown-it-py 4.0.0과 Mermaid 11.4.1 고정 bundle을 사용했습니다. Claude가 2026-10-04 04:12:13 UTC에 Node 22.17.1·Chrome 154.0.8037.58로 실행한 offline 화면 검사는 통과했으며, 전달 당시 BOOK.html의 hash와 일치했습니다. 그 [전달 시점 화면 기록](../review/html-check-r1b-incoming.json)을 보존했습니다. 이후 A1 본문을 바꾼 1b HTML의 화면 검사를 한 번 시도했으나 `Page.enable` 시간 초과로 완료하지 못했습니다. 이 한계를 기록한 뒤 재생성한 통합본도 화면 검증 완료로 표시하지 않습니다. [최신 화면 검사 기록](../review/html-check.json)의 hash와 실제 파일을 대조하며, 결과의 적용 범위와 시간 초과 이력은 [교차 검토 화면 기록](../review/html-check-r1.json)에 적습니다. [renderer 출처와 hash](../assets/mermaid-provenance.json)도 고정했습니다.

교차 검토용 `verify_review_r1.py`는 합성 clock 품질 입력 11개, 구조체 배치 검사 2개, counter·wrap 구분 검사 5개를 확인합니다. 구조체 배치 검사 자체는 Linux syscall 실행이 아닙니다. 기본 실행은 출판한 Linux 시계 JSON의 파일·실행기 hash, busy·sleep 구간, idle 61개 표본, 산술·품질 표시와 본문 수치를 대조합니다. freq 변환·RAW 중간 시각·idle 순서를 메모리에서 잘못 바꾼 3개 입력이 거절되는지도 검사하며 출판 파일은 바꾸지 않습니다. `verify_revision.py`에도 같은 출판 근거 검사를 연결했습니다. 선택 인자 `--linux-result`는 별도 재실행 JSON을 추가로 검사합니다. 저장된 증거의 정합성을 검사하는 명령이며 실제 시계 교정을 인증하지 않습니다.

숫자를 코드에 옮긴 대표 산술 검사는 전체 문장의 검증과 다릅니다. 공식 원천과 대조한 주요 주장·수정 이유는 [검토 기록](review.md)과 [사실 대조 기록](../review/fact-review-1.1.json)에 있습니다.

## 제1.1판에 보존한 실제 실행 31개

실행 환경은 Ubuntu 24.04.3, WSL2 Linux 6.18.33.2-microsoft-standard-WSL2, Python 3.12.3, amd64입니다. Docker daemon을 사용할 수 없어 WSL의 일반 사용자와 로컬 추출 실행 파일을 이용했습니다. 시스템 패키지 설치, 기존 DB·클러스터 접속, cloud 계정 호출 없이 수행했습니다.

| 묶음 | 수 | 주요 확인 | 원시 기록 |
| --- | ---: | --- | --- |
| Linux | 4 | comm 파싱, CPU 원천 계정, 32MiB 매핑, 1MiB 파일 I/O | [JSON](../labs/results/1.1-linux.json) |
| PostgreSQL 18.6 | 11 | 격리 수준 2종, 잠금·timeout·실패·savepoint·deadlock·권한·통계 snapshot·수집 SQL | [JSON](../labs/results/1.1-postgresql.json) |
| Kubernetes API server 1.34.1·etcd 3.6.4 | 7 | 페이지 snapshot·watch·UID 교체·409·RBAC·selector 이탈·410 | [JSON](../labs/results/1.1-kubernetes.json) |
| OTel Collector 0.137.0 | 7 | HTTP JSON 성공·503 재시도·400·500·부분 성공·응답 유실·재시도 소진 | [JSON](../labs/results/1.1-otel.json) |
| HTTP/1.1 | 2 | 두 GET의 연결 재사용, HTTP 200 뒤 불완전 본문 | [JSON](../labs/results/1.1-http11.json) |

Linux의 기존 cgroup 읽기는 `observed`로 따로 기록했으며 31개 통과 시나리오에 더하지 않았습니다. 기존 CPU 검사의 통과는 두 CPU 계정의 근접성 확인이며 경과 시간 교정 검사가 아닙니다. 원래 Linux 실행기와 결과는 byte 단위로 보존하고 [입력 연결](../review/evidence-provenance.json)을 검사합니다.

**1b에서 추가한 실행 근거:** Claude가 2026-10-04 04:10:49 UTC에 현재 Linux 실행기를 실행한 [별도 결과](../labs/results/1.1-linux-clock-r1.json)를 출판했습니다. Linux 6.18.33.2-microsoft-standard-WSL2·Python 3.12.3에서 busy 3개·sleep 1개 구간과 idle 61개 표본을 기록했고, Codex가 JSON과 실행기 hash·계산·품질 표시를 확인했습니다. busy 구간의 프로세스 CPU clock/RAW는 약 0.99992–0.99995, MONOTONIC/RAW는 약 0.937입니다. sleep·idle의 시계 차이와 adjtimex 값도 분모 주파수 조정 설명과 부합합니다. CPU 진단은 `observed`이며 기존 31개 통과 시나리오에 새 정상 인증으로 더하지 않습니다. 최초 1.06 표본에는 RAW·tick이 없어 같은 원인을 소급 확정하지 않으며, 조정 주체나 RAW의 외부 정확도도 확인하지 않았습니다. 원시값과 반올림·표본 평균의 한계는 [Linux 실습 본문](host/linux-observation-lab.md)에 있습니다.

Kubernetes 실험은 API server·etcd만 띄웠습니다. 실제 업무 Pod·kubelet·CNI·CSI는 없습니다. 7개 모두 watch cache를 껐고, 410 재현에는 전용 etcd의 physical compaction도 사용했습니다. Collector 실험은 sending queue를 끄고 목적지 응답을 통제했습니다. 내부 로그는 error, 내부 지표는 none이므로 부분 거절을 Collector가 내부에서 인지·계수했는지는 관측하지 않았습니다. gRPC·영속 저장·검색도 검증하지 않았습니다.

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

교차 검토에서 본문의 고유 URL **348개**를 HTTP로 다시 조회했습니다. **338개는 200, 10개는 403**이며 404는 없었습니다. [source-status.json](../review/source-status.json)은 주소 접근 결과입니다. fragment의 정확성이나 모든 문장의 사실성을 자동 판정한 결과가 아닙니다.

403은 MySQL 공식 문서 9개와 Little 논문 출판사 페이지 1개입니다. 기존 7개에 MySQL 9.7의 정책·릴리스 문서 3개가 추가되었습니다. 새 문서의 내용은 별도 웹 열람으로 확인했으며 직접 HTTP 요청의 접근 제한 상태와 구분했습니다. 주소 조회일이 모든 주장을 새로 사실 검토한 날짜라는 뜻은 아닙니다.

## 실행하지 않은 범위

물리 Linux 장비 전체와 모든 procfs 필드, cgroup 제한·OOM·eviction, Kubernetes 최신 patch·1.35/1.36 서버·업무 workload·CNI·CSI, SQL Server·Oracle 서버 질의, JVM·.NET 등 runtime agent 전수, 실제 DNS·TLS·HTTP/2, 상용 SNMP 장비, cloud 계정·비용 API, 분산 장애 전환·전원 장애·복구는 실행하지 않았습니다. 본문에서는 연결한 공식 원천의 적용 범위로 설명하며 해당 환경을 검증했다고 표시하지 않습니다.

MySQL은 위 8.4.11·9.7.2 r1·r2의 소유 임시 인스턴스에서 실행했습니다. 운영 계정의 최소 권한과 crash 복구·전원 장애 지속성은 실행 검증하지 않았습니다.

## 문서 검사 재현

저장소 루트에서 실행합니다. HTML 생성에는 `requirements-docs.txt`의 고정 의존성이 필요하며 이미 설치되어 있으면 설치를 반복하지 않습니다. 다음은 1.2판 발행에서 실행한 재생성 두 명령과 기본 검사 여섯 명령입니다. 실습 서버를 띄우거나 기존 결과를 덮어쓰지 않습니다.

```powershell
python -X utf8 -B scripts/build_book.py
python -X utf8 -B scripts/build_html.py
python -X utf8 -B scripts/check_docs.py
python -X utf8 -B scripts/verify_examples.py
python -X utf8 -B scripts/verify_contracts.py
python -X utf8 -B scripts/verify_revision.py
python -X utf8 -B scripts/build_book.py --check
python -X utf8 -B scripts/build_html.py --check
```

저장된 라운드별 증거만 별도로 확인하려면 아래 명령을 사용합니다. `verify_revision.py`의 출판 근거 검사에도 이 범위가 포함됩니다.

```powershell
python -X utf8 -B scripts/verify_review_r2.py --published
python -X utf8 -B scripts/verify_review_r3.py --published
```

선택적인 화면 검사는 `python -X utf8 -B scripts/check_html.py`이며 Node 22 이상과 Chrome을 사용합니다. Windows 기본 경로 외 Chromium은 `--browser`로 지정합니다. URL 접근 상태 재조회는 `python -X utf8 -B scripts/check_sources.py`입니다. 두 작업은 이번 발행에서 실행하지 않았으며, URL 접근 성공이 문장의 사실성을 판정하지 않습니다.

## Linux 실습 재현

1b의 Linux CPU 진단은 Claude가 아래 첫 두 명령으로 실행·검증한 결과를 전달했고, 출판 경로에 보존한 뒤 다시 검사했습니다. 아래는 과거 고정 버전의 후속 재현 방법입니다. 2d에서 출판한 별도 서버 실행의 명령·입력은 [2라운드 실습](cross-domain/reproducible-labs.md)에 있습니다.

WSL을 포함한 Ubuntu 24.04 amd64의 일반 사용자로 **이 저장소의 Linux 경로**에서 실행합니다. Python 3, OpenSSL, dpkg-deb와 실행 파일의 공유 라이브러리가 필요합니다. PostgreSQL 도구는 Ubuntu 24.04 패키지의 의존성을 전제로 하므로 다른 배포판의 범용 설치기로 취급하지 않습니다. 다운로드 목록과 SHA256은 [PostgreSQL 패키지](../labs/postgresql/packages.json), [runtime archive](../labs/runtime-assets.json)에 고정했습니다.

```bash
python3 -B scripts/run_linux_lab.py --clock-observation-seconds 60 --output .lab-runs/linux-clock-r1.json
python3 -B scripts/verify_review_r1.py --linux-result .lab-runs/linux-clock-r1.json
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
