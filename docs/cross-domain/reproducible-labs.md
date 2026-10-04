# 재현 실습: 계산, 실제 엔진, 운영 검증의 경계

> 상태: 검토됨 · 적용 범위: Windows 로컬 실행, Python 3.11.9·SQLite 3.45.1·promtool 3.5.0 · 실행일: 2026-10-04

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
