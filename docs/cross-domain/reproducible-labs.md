# 재현 실습: 계산, 실제 엔진, 운영 검증의 경계

> 상태: 검토됨 · 적용 범위: Windows·WSL 로컬 실습과 아래 고정 버전·입력 · 기존 실행일: 2026-10-04 · WSL 2라운드 추가 실행: 2026-10-05

버전 상태: promtool 3.5.0은 기존 기록의 고정 실행 파일입니다. Prometheus 3.5 LTS는 2026-07-31 지원이 끝났고, 검토 시점 LTS 3.13.4와 최신 안정 3.15.0의 별도 실행을 이번에 추가했습니다. [릴리스·지원 표](../coverage.md#교차-검토-시점의-버전-상태)를 참고하며 과거 재현 버전을 현재 권장 설치 버전으로 읽지 않습니다.

공식 설명을 읽는 것과 실제 프로그램에서 같은 동작을 보는 것은 서로 보완합니다. 이 장은 작성 환경에서 직접 실행한 실습입니다. 운영 서버나 사용자의 DB를 사용하지 않았고, 로컬 임시 DB와 loopback HTTP, 읽기 전용 Win32 API, 합성 PromQL 입력을 사용했습니다.

## 제1.1판에서 추가한 실습

이 장은 제1.0판의 네 가지 실행 기록을 유지합니다. 제1.1판에서는 WSL2의 독립된 로컬 환경을 사용해 다음 다섯 묶음의 시나리오 31개를 추가했습니다. Docker daemon에 의존하지 않으며 각 장에 실제 버전·격리 범위·재현 명령을 적었습니다.

| 실습 | 시나리오 | 확인한 질문 |
| --- | ---: | --- |
| [Linux 원천 관측](../host/linux-observation-lab.md) | 4 | 주소 공간·상주량·I/O 계정·CPU 시계는 어떻게 다른가? |
| [PostgreSQL 동시성](../database/postgresql-concurrency-lab.md) | 11 | 읽기 시점·잠금·오류·권한이 조회 결과를 어떻게 바꾸는가? |
| [Kubernetes 인벤토리](../kubernetes/inventory-consistency.md) | 7 | 부분 목록·객체 수명·선택 집합과 삭제를 어떻게 구분하는가? |
| [OTLP 전송](../product/telemetry-delivery-contracts.md) | 7 | 재시도·부분 성공·응답 유실에서 무엇이 관측되는가? |
| [HTTP/1.1 연결](../network/dns-and-connection-lifecycle.md) | 2 | 요청 수·연결 수·본문 완료가 어떻게 다른가? |

Linux의 기존 cgroup 읽기는 별도 관측으로 기록했으며 위 4개 실험 수에 추가하지 않았습니다. [검증 기록](../validation.md)은 두 판의 근거와 실행하지 않은 범위를 함께 정리합니다.

## 2라운드에서 출판한 별도 실행

2026-10-05 Claude가 WSL Ubuntu 24.04·Linux 6.18.33.2·Python 3.12.3에서 실행한 최종 JSON 네 개를 바이트 그대로 출판했습니다. Codex는 원시값·입력 hash·판정 조건을 대조했으며 이 샌드박스에서 Linux 서버를 다시 실행하지 않았습니다. [provenance](../../review/evidence-provenance.json)가 당시 입력과 출판 파일을 연결합니다. `supported`는 명시한 가설·버전·구성의 관측이고 제품 전체의 보장이 아닙니다.

| 실습 | 고정 실행과 판정 | 출판 결과 |
| --- | --- | --- |
| Kubernetes | 1.34.1·1.37.0 × cache true/false, 16조건 중 supported 14·refuted 2 | [JSON](../../labs/results/1.1-r2-kubernetes.json) |
| promtool | 3.13.4·3.15.0, 두 버전 모두 check rules·test rules 성공 | [JSON](../../labs/results/1.1-r2-prometheus.json) |
| Collector | 0.162.0, 내부 관측·queue 경계·이름 수용 14조건 supported | [JSON](../../labs/results/1.1-r2-otel.json) |
| PostgreSQL | 18.6, prepared·catalog_xmin·feedback·physical xmin 네 조건 supported | [JSON](../../labs/results/1.1-r2-postgresql.json) |

Kubernetes 실행 patch는 검토 시 최신 1.34.12·1.37.1이 아닙니다. cache-on의 과거 Exact LIST 200은 “compaction 뒤 반드시 410” 가설을 반박하며 오류 결과를 숨기기 위해 통과로 고치지 않았습니다. Collector는 내부 거절 로그·최종 실패 계수·비동기 응답 경계를, PostgreSQL은 회수 기준점을 해제하기 전후의 실제 행 회수를 관측했습니다. [Kubernetes 해석](../kubernetes/inventory-consistency.md), [Collector 해석](../product/telemetry-delivery-contracts.md), [PostgreSQL 해석](../database/postgresql-operations.md)

promtool 두 버전은 기존 `labs/prometheus/rules.yml`·`tests.yml`을 변경 없이 다시 평가했습니다. 각 버전에서 기존 표현식 8개·알림 5개의 fixture가 성공했으며, 최초 3.5.0 결과와 새 실행을 모두 보존합니다. exemplar·created timestamp·TSDB 저장·Alertmanager 전송은 이 규칙 검사에 포함되지 않습니다.

### 경로·권한·정리 범위

공식 자산과 추출 도구는 `.tools/`, 출력 JSON·일반 작업 파일은 `.lab-runs/`에 제한합니다. 시스템 패키지 설치·sudo·서비스 등록·cloud 호출 없이 일반 Linux 사용자의 일회성 loopback 프로세스만 사용합니다. 다운로드 URL·공식 SHA256 pin은 [공통 manifest](../../labs/review-r2/assets.json)와 [Kubernetes manifest](../../labs/review-r2/kubernetes-assets.json)에 있습니다. `.tools/pg18`은 기존 검증 도구를 재사용합니다.

**PostgreSQL 데이터 디렉터리 예외:** metadata 옵션 없는 WSL DrvFs에서는 필요한 0700 권한이 유지되지 않아 최초 initdb가 실패했습니다. 최종 실행은 `mkdtemp`가 만든 Linux native 임시 디렉터리(해당 기록에서는 `/tmp/dk-r2-pgdata-*`)의 실제 mode 0700을 검사하고 primary·standby 데이터를 그 아래에 뒀습니다. 경로·사유·mode·정리 완료가 JSON에 남으며, 소유 프로세스를 멈춘 뒤 그 디렉터리만 제거합니다. 미리 존재한 DB나 사용자가 지정한 외부 경로로 연결하지 않습니다. PostgreSQL 실습 자체는 fixture·slot·prepared transaction·VACUUM 등 상태를 변경하므로 운영 DB에서 실행하는 수집 명령과 다릅니다. [실행기](../../scripts/run_postgres_r2_lab.py)

2d 검토에서는 native 디렉터리의 resolve/chmod/stat 검사 **이전**에 소유권을 등록하도록 보완했습니다. 삭제 실패를 exit code·status에도 반영하고 로그 읽기 실패가 데이터 정리 시도까지 막지 않게 했습니다. 프로세스 종료에 실패하면 사용 중일 수 있는 디렉터리는 보존합니다. 성공한 네 실행에 쓰인 [당시 공통 모듈](../../labs/archive/lab_r2_common_2026_10_05.py)은 그대로 보존했으므로 새 helper의 실패 경로 보완 때문에 옛 수치를 현재 코드의 실행 결과로 바꿔 쓰지 않습니다. Windows에서는 저장소 내부 fixture로 여섯 실패 경로를 검사했으며, 수정한 native 성공 경로의 Linux 재실행은 아래 smoke 명령으로 별도 확인합니다.

최초 initdb 실패 `postgresql.json`, 입력 hash 변경으로 대체한 `prometheus.json`·`otel.json`·`postgresql-2.json`·`prometheus-2.json`·`otel-2.json`이 있었다는 사실은 기록에 남깁니다. 해당 중간 실행은 출판 근거로 채택하지 않았습니다. [2d 검토 기록](../../review/claude-codex-r2.md)

### 2라운드 후속 재현 명령

PowerShell의 저장소 루트에서 실행하는 **후속 재현 예시**입니다. 이미 존재하는 출력은 덮어쓰지 않으므로 같은 명령을 반복할 때는 새 파일명을 사용합니다. 아래는 2d에서 실행한 명령 목록이 아닙니다. Linux 서버 재현에는 해당 배포판 공유 라이브러리와 기존 PostgreSQL 도구가 필요합니다.

```powershell
python -X utf8 -B scripts/get_review_r2_assets.py --which all
python -X utf8 -B scripts/run_kubernetes_r2_lab.py --prepare-assets
wsl -d Ubuntu --cd /mnt/c/project/Domain-Knowledge -- python3 -B scripts/run_kubernetes_r2_lab.py --output .lab-runs/r2/repeat-kubernetes.json
wsl -d Ubuntu --cd /mnt/c/project/Domain-Knowledge -- python3 -B scripts/run_prometheus_r2_lab.py --output .lab-runs/r2/repeat-prometheus.json
wsl -d Ubuntu --cd /mnt/c/project/Domain-Knowledge -- python3 -B scripts/run_otel_r2_lab.py --output .lab-runs/r2/repeat-otel.json
wsl -d Ubuntu --cd /mnt/c/project/Domain-Knowledge -- python3 -B scripts/run_postgres_r2_lab.py --output .lab-runs/r2/repeat-postgresql.json
python -X utf8 -B scripts/verify_review_r2.py --result .lab-runs/r2/repeat-kubernetes.json --result .lab-runs/r2/repeat-prometheus.json --result .lab-runs/r2/repeat-otel.json --result .lab-runs/r2/repeat-postgresql.json
```

실행 부하는 전용 API server·etcd 또는 Collector, 작은 primary·standby의 CPU·메모리·디스크와 로컬 요청입니다. 원시 JSON에 자원 최고 사용량은 없어 메모리 실측치를 주장하지 않습니다. 새 실습 없이 출판 증거만 확인하는 명령은 도구 cache 없이도 동작합니다. native smoke는 DB를 띄우지 않고 작은 임시 파일만 만들며, 이 Linux 명령은 Claude의 후속 실행 대상으로 남깁니다.

```powershell
python -X utf8 -B scripts/verify_review_r2.py --published
python -X utf8 -B scripts/verify_lab_r2_cleanup.py
wsl -d Ubuntu --cd /mnt/c/project/Domain-Knowledge -- python3 -B scripts/verify_lab_r2_cleanup.py --native-output .lab-runs/r2/native-cleanup-r2d.json
```

## 실행 자료와 재현

실행 코드는 [run_labs.py](../../scripts/run_labs.py), 원시 결과는 [2026-10-04.json](../../labs/results/2026-10-04.json), Prometheus 입력은 [tests.yml](../../labs/prometheus/tests.yml)과 [rules.yml](../../labs/prometheus/rules.yml)에 있습니다. 결과 파일은 실행 시각, 실제 버전, 원천 값, 스크립트·입력 SHA-256을 포함합니다.

Windows에서 다음 명령으로 같은 실험을 실행할 수 있습니다. 첫 명령은 고정된 공식 Prometheus 3.5.0 배포에서 promtool을 다운로드하고 공개 SHA-256과 대조합니다. 최신 버전 추천이 아니라 재현 버전 고정입니다. 실행 파일은 Git에 포함하지 않습니다. [공식 배포](https://github.com/prometheus/prometheus/releases/tag/v3.5.0)

```powershell
python scripts/get_promtool.py
python scripts/run_labs.py --promtool .tools/prometheus-3.5.0/promtool.exe
python scripts/verify_contracts.py
```

재실행 결과는 기본적으로 `.lab-runs/latest.json`에 저장되어 출판 당시 결과를 덮지 않습니다. Python 표준 라이브러리를 사용하며 관리자 권한이나 기존 DB 접속은 필요하지 않습니다. 짧은 CPU 작업, 임시 파일 쓰기, `127.0.0.1`의 임의 포트가 사용됩니다. SQLite 임시 파일과 HTTP 서버는 종료 시 정리됩니다. Windows 외에서는 Win32 실험을 skipped로 기록하고, promtool 경로가 없으면 해당 실험도 skipped로 기록합니다.

## 실습 1: SQLite의 읽기 시점과 쓰기 충돌

설정은 WAL 모드, 독립된 두 연결, `timeout=0`, 명시적 transaction입니다. 실행은 다음 순서로 진행했습니다.

| 순서 | 동작 | 실제 관측 |
| --- | --- | --- |
| 1 | 값 10인 행 생성 | 10 |
| 2 | A가 transaction을 시작하고 SELECT | 10 |
| 3 | B가 값을 20으로 변경·commit | 성공 |
| 4 | A가 같은 transaction에서 SELECT | 10 |
| 5 | A가 transaction을 끝내고 SELECT | 20 |
| 6 | A가 BEGIN IMMEDIATE 후 B가 쓰기 시도 | SQLITE_BUSY |

이는 SQLite WAL의 snapshot isolation과 한 번에 하나의 writer라는 동작을 보여 줍니다. PostgreSQL Read Committed의 문장별 snapshot 예시를 검증한 결과로 옮겨 쓰지 않습니다. [SQLite isolation](https://www.sqlite.org/isolation.html), [SQLite WAL](https://www.sqlite.org/wal.html)

같은 실습에서 값 20을 40으로 변경한 뒤 CHECK를 위반하는 문장을 실행했습니다. 실패한 문장 뒤 transaction 안에서는 40이 남았고, **명시적 ROLLBACK 뒤에 20으로 돌아왔습니다.** 따라서 “SQL 한 문장이 실패하면 모든 엔진에서 transaction 전체가 자동 취소된다”는 설명은 부정확합니다. SQLite의 기본 ABORT는 현재 문장의 변경을 취소하되 이전 문장의 변경과 transaction을 유지할 수 있습니다. [SQLite conflict 처리](https://www.sqlite.org/lang_conflict.html)

이 실습은 전원 장애·디스크 손상·장기 WAL 운용·백업 복원을 검증하지 않습니다. SQLite 3.45.1은 이 Python 환경에 포함된 실제 실행 버전이며 신규 배포의 버전 추천이 아닙니다.

## 실습 2: HTTP timeout 뒤 업무 효과

로컬 서버의 첫 요청 처리를 event로 잠시 멈추고 클라이언트에 50ms timeout을 설정했습니다. 클라이언트가 timeout을 관측한 뒤에 서버 처리를 진행시켰습니다. 그러므로 서버 처리가 client timeout 이전에 완료되었다고 추측할 필요 없이 사건 순서를 코드로 제어했습니다.

출판 실행에서 클라이언트 경과 시간은 약 56ms였습니다. 실제 값은 scheduler와 실행 환경에 따라 달라지며 50ms를 정확한 실행 시각 보장으로 해석하지 않습니다. 이후 같은 업무 key로 재시도해 HTTP 200을 받았고, **전송 시도 2회·업무 효과 1회**를 기록했습니다.

이 결과는 클라이언트의 timeout이 서버 작업 취소를 보장하지 않는다는 예시입니다. 중복 억제는 실습의 메모리 내 key 집합으로 구현했으므로 프로세스 재시작, 여러 서버, 동시 장애에서도 효과가 한 번이라고 보장하는 운영 구현은 아닙니다. 실제 멱등 처리는 업무 결과와 key의 저장·충돌·보존 범위를 설계해야 합니다. [멱등 API 설계](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)

## 실습 3: Windows CPU의 원천값

`GetSystemTimes`와 현재 Python 프로세스의 `GetProcessTimes`를 두 번 읽고, 그 사이 0.2초 대기와 약 0.2초의 짧은 계산을 수행했습니다. 해당 API는 100ns 단위를 사용하며 system kernel 값에는 idle이 포함됩니다. [GetSystemTimes](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getsystemtimes), [GetProcessTimes](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocesstimes)

출판 실행의 실제 증가량입니다.

| 항목 | 값 |
| --- | ---: |
| system idle | 80,000,000 × 100ns |
| system kernel, idle 포함 | 82,031,250 × 100ns |
| system user | 2,187,500 × 100ns |
| 관측 경과 | 약 0.400785초 |
| 프로세스 CPU 시간 | 0.203125초 |

system 비 idle 비율은 `(82,031,250 + 2,187,500 − 80,000,000) / (82,031,250 + 2,187,500) ≈ 5.009%`입니다. 프로세스는 평균 약 `0.203125 / 0.400785 = 0.507 CPU`를 사용했습니다. 두 값은 분모·대상이 다르므로 같을 필요가 없습니다.

현재 시스템의 다른 작업도 system 계정에 포함됩니다. 이 결과로 장비 성능을 평가하거나 64개 초과 processor group 구성 전체를 검증했다고 표시하지 않습니다. 짧은 관측에서 경과 시간×CPU 개수와 API 계정 총합이 정확히 일치해야 한다는 검사를 넣지도 않았습니다.

## 실습 4: 실제 PromQL 평가

공식 promtool 3.5.0에서 **표현식 검사 8개와 알림 검사 5개**를 실행했고 `SUCCESS`를 받았습니다. 입력 숫자는 합성이지만 식과 규칙은 실제 Prometheus 평가기로 실행했습니다. [promtool rule testing](https://prometheus.io/docs/prometheus/latest/configuration/unit_testing_rules/)

| 검사 | 결과와 의미 |
| --- | --- |
| 리셋 후 rate를 먼저 계산하고 합산 | 약 1.6667/초 |
| 원천을 먼저 합친 unsafe counter에 rate 적용 | 약 1.3333/초; 개별 reset을 숨김 |
| reset 수 | 해당 fixture에서 1 |
| classic histogram의 p90 | 약 0.166667초; bucket 내 선형 보간 |
| 전체 오류 비율 | 19/1,000=1.9% |
| 인스턴스 오류율 단순 평균 | 5.5%; 다른 질문에 답함 |
| 2분 for | 1분에는 firing 아님, 2분에 firing |
| stale 입력 | up은 사라짐; up=0과 다른 상태 |
| absent의 1분 for | 누락 관측 뒤 정해진 평가에 firing |

알림 이름·label과 정확한 평가 시각은 fixture에 있습니다. 실제 서버 scrape, 저장 보존, Alertmanager 전달이나 모든 PromQL 예제를 검증한 결과는 아닙니다. 원래 본문의 `rate` 설명에는 범위 경계·외삽·표본 조건이 있으므로 이 두 표본 차분과 혼동하지 않습니다.

## 실습 5: 수집 계약의 입력 경계

[어댑터 계약](../product/adapter-contracts.md)은 정상 증가뿐 아니라 첫 표본, 알려진 0, 수집 실패, 정의 변경, 큰 정수 정밀도 등 22개 사례를 검사합니다. 이는 원천을 직접 수집하는 실험과 구분한 참조 코드 검사입니다. 저장된 실습 결과의 스크립트·fixture hash도 함께 대조해 코드가 바뀌었는데 옛 결과를 현재 검증으로 표시하는 일을 막습니다.

## 이해 확인

1. 합성 PromQL 입력이면 실행 검증이 아닌가? **입력은 합성이지만 실제 평가기의 동작을 실행해 확인했습니다. 운영 scrape 검증과는 다릅니다.**
2. SQLite 실습으로 모든 DB의 격리 수준을 확인했는가? **SQLite 해당 버전·설정의 결과입니다.**
3. 모든 검사 통과가 모든 운영 환경의 보장인가? **명시한 입력·버전·경계의 증거이며 범위를 넘겨 해석하지 않습니다.**
