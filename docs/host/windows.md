# Windows의 CPU와 메모리 관측

> 상태: 검토됨 · 범위: Windows Win32 성능 API와 PDH · 공식 자료 확인: 2026-10-03 · 편집 검토일: 2026-10-04 · 2라운드 보강 확인: 2026-10-05 (PDH 실명과 Task Manager 빌드 차이)

## 먼저 이해할 것

Windows와 Linux는 CPU·메모리를 관측할 수 있지만 원천 이름과 계정이 다릅니다. 같은 CPU 50%라도 API가 어느 CPU 집합을 합쳤는지, idle을 어디에 포함했는지 알아야 합니다. Windows의 working set과 commit도 서로 다른 질문에 답합니다. 이 장은 Linux 필드명을 그대로 치환하지 않고 API 정의에서 계산을 시작합니다.

운영체제마다 CPU 시간과 메모리 사용을 노출하는 방식이 다릅니다. 통합 모니터링 제품은 화면의 공통 개념을 제공하되 원천 API의 의미를 보존해야 합니다. 이 장은 Windows에서 자주 혼동하는 계산을 설명합니다.

## 시스템 CPU 시간

`GetSystemTimes`는 Idle·Kernel·User 시간을 100 ns 단위로 제공합니다. **Kernel 시간에는 Idle 시간이 포함됩니다.** 또한 64개를 넘는 프로세서가 있는 시스템에서는 호출 스레드의 주 Processor Group 범위라는 제약이 있으므로 반환값을 무조건 시스템 전체로 취급하지 않습니다. [Microsoft GetSystemTimes](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getsystemtimes)

같은 수집 범위가 유지되고 카운터가 유효하다는 전제에서 계산합니다.

```text
총 시간 증가량 = ΔKernel + ΔUser
비 Idle 시간 증가량 = ΔKernel + ΔUser - ΔIdle
비 Idle CPU 비율 = 비 Idle 시간 증가량 / 총 시간 증가량
```

설명을 위해 단위를 초로 바꾼 가상 입력이 `ΔKernel=28`, `ΔUser=12`, `ΔIdle=20`이면 총량은 40 CPU초이고 비 Idle 비율은 50%입니다. Kernel 28초를 모두 실제 커널 실행으로 읽거나 총량에 Idle 20초를 다시 더하면 잘못된 계산입니다.

이 비율은 해당 API의 시간 회계를 바탕으로 한 값입니다. 주파수·터보 동작 등을 반영하는 다른 성능 카운터와 숫자가 같다고 가정하지 않습니다. 제품 간 비교는 같은 카운터 정의와 수집 범위에서 수행합니다.

## 프로세스 CPU 시간과 수명

`GetProcessTimes`는 생성·종료 시각 및 프로세스 스레드들의 Kernel·User 시간 합계를 제공합니다. 시간 단위는 100 ns이며 여러 코어에서 실행하면 CPU 시간 합계가 벽시계 경과 시간을 넘을 수 있습니다. 조회에는 적절한 프로세스 정보 접근 권한이 필요합니다. [Microsoft GetProcessTimes](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocesstimes)

```text
사용 CPU초 = Δ(Kernel + User) × 10⁻⁷
평균 사용 CPU 수 = 사용 CPU초 / 실제 경과 초
```

가상 예시에서 4초 동안 60,000,000 단위가 증가했다면 6 CPU초, 평균 1.5 CPU입니다. 한 CPU를 100%로 표시하면 150%입니다. 전체 기준으로 정규화하려면 프로세서 집합과 분모를 추가로 정의합니다.

**제품 적용 제안:** 프로세스 번호와 생성 시각을 함께 관측해 실행 수명을 식별합니다. 수집 중 종료되거나 권한이 부족해 정보를 읽지 못한 경우를 CPU 사용량 0으로 바꾸지 않습니다.

## 물리 메모리와 Commit

`GetPerformanceInfo`가 반환하는 `PERFORMANCE_INFORMATION`에는 물리 메모리와 Commit 관련 필드가 있습니다. 크기 필드 중 다수는 페이지 수이고 `PageSize`는 바이트 수입니다. [Microsoft PERFORMANCE_INFORMATION](https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-performance_information)

| 필드 | 의미 |
| --- | --- |
| PhysicalTotal | 물리 메모리의 페이지 수 |
| PhysicalAvailable | 바로 재사용할 수 있는 물리 페이지 수 |
| CommitTotal | 현재 약속된 메모리의 페이지 수 |
| CommitLimit | 현재 Commit 한도에 해당하는 페이지 수 |
| PageSize | 페이지 하나의 바이트 수 |

Commit은 RAM 상주량과 다릅니다. 페이지를 Commit하면 CommitTotal에 반영되지만 실제 물리 메모리 부과는 접근 시점과 관련됩니다. CommitLimit은 페이지 파일 확장 등의 조건에 따라 변할 수 있습니다. [Microsoft PERFORMANCE_INFORMATION 필드 정의](https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-performance_information)

```text
물리 가용 바이트 = PhysicalAvailable × PageSize
Commit 비율 = CommitTotal / CommitLimit
```

Commit 비율과 물리 메모리 비율을 두 개의 지표로 제공합니다. 한쪽을 다른 쪽의 대체값으로 사용하지 않습니다.

## Working Set과 PrivateUsage

`PROCESS_MEMORY_COUNTERS_EX`의 `WorkingSetSize`는 현재 Working Set의 바이트 수입니다. `PrivateUsage`는 프로세스의 Commit Charge를 나타냅니다. `PagefileUsage`라는 이름도 해당 구조에서는 Commit Charge 의미이므로 실제 페이지 파일에 쓰인 바이트 수라고 읽으면 안 됩니다. [Microsoft PROCESS_MEMORY_COUNTERS_EX](https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-process_memory_counters_ex)

가상의 프로세스가 Working Set 400 MiB, PrivateUsage 1 GiB를 보고해도 모순이 아닙니다. 서로 다른 양을 측정하기 때문입니다. 정확히 어떤 페이지가 상주·공유·개인 상태인지는 추가 관측이 필요합니다.

## 성능 카운터 수집

PDH는 Windows 성능 카운터를 조회하고 기록을 다루는 API입니다. 카운터 제공자에서 내보낸 데이터를 소비하는 기능이며, 모든 카운터를 동일한 산식으로 계산하는 계층은 아닙니다. [Microsoft PDH 사용](https://learn.microsoft.com/en-us/windows/win32/perfctrs/using-the-pdh-functions-to-consume-counter-data)

제품 수집기에서 다음을 명세하는 방식을 제안합니다.

- 카운터 경로와 제공자, 인스턴스 식별 방식
- 원천값과 계산된 값 중 무엇을 사용하는지
- 단위, 카운터 유형, 필요한 표본 수와 간격
- 인스턴스 생성·종료와 시스템 재부팅 처리
- OS 버전·언어·권한에 따른 검색과 조회 결과

카운터 이름의 번역 여부, 프로세서 그룹 범위, 제공자의 설치 여부는 대상 환경에서 검증합니다. PDH 수집과 메모리 API는 이 판에서 실행하지 않았습니다. `GetSystemTimes`와 현재 프로세스의 `GetProcessTimes`는 [로컬 실습](../cross-domain/reproducible-labs.md)에서 실제 표본과 계산을 확인했습니다.

## 성능 카운터의 실제 이름과 분모

다음은 **2026-10-05 공식 자료 확인** 기준의 영문 카운터 경로입니다. OS 언어·제공자·instance 범위는 별도 확인하며 이 경로를 이번에 실제 조회하지 않았습니다. 각 행의 이름·의미를 뒷받침하는 원천을 구분했습니다. 인용 문서의 특정 서비스용 임계값을 Windows 전체의 기본 경보값으로 사용하지 않습니다.

| 영문 경로 | 단위·의미 | 해석 함정 |
| --- | --- | --- |
| `\Processor Information(_Total)\% Processor Time` | %: 관측 구간의 비 idle 시간 기준 | 주파수 반영 작업량·프로세스별 CPU 합과 다름. [Time/Utility 정의](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/cpu-usage-exceeds-100) |
| `\Processor Information(_Total)\% Processor Utility` | %: 기준 성능 대비 작업 능력의 사용, 주파수 변화를 반영 | nominal 성능 기준이므로 turbo에서 100%를 넘을 수 있음. [Microsoft 설명](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/cpu-usage-exceeds-100) |
| `\Memory\Available MBytes` | MBytes: 즉시 할당 가능한 물리 메모리 | free 목록만이 아니라 standby 등 재사용 가능한 메모리도 포함. [Windows 성능 진단](https://learn.microsoft.com/en-us/troubleshoot/windows-server/performance/troubleshoot-performance-problems-in-windows), [가용량 정의](https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-performance_information) |
| `\Memory\Committed Bytes` | byte: 시스템 commit charge | 실제 RAM 상주량·페이지 파일 쓰기량 아님. [commit와 카운터](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/introduction-to-the-page-file) |
| `\Memory\% Committed Bytes In Use` | %: Committed Bytes / Commit Limit | 물리 메모리 사용률 아님; 한도 변경도 영향. [commit 비율 정의](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/introduction-to-the-page-file) |
| `\System\Processor Queue Length` | 실행을 기다리는 ready thread 수, 현재 표본 | 실행 중인 thread는 제외; I/O 대기나 전체 thread 수 아님. [Microsoft의 해당 System 카운터 정의](https://learn.microsoft.com/en-us/exchange/exchange-2013-performance-counters-exchange-2013-help) |

Utility와 Time은 같은 100% 척도가 아닙니다. 주파수 반영 비율이 100%를 넘었다고 값을 잘라내거나 불가능한 CPU 시간이라고 판정하지 않습니다. 반대로 GetProcessTimes의 다중 CPU 시간 합이 100%를 넘는 이유와도 구분합니다. [Microsoft Utility 설명](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/cpu-usage-exceeds-100)

**Task Manager와의 비교에는 Windows build·탭·열도 필요합니다.** Windows 8을 설명한 위 KB는 Utility 사용을 말하지만, Windows 11의 2025년 업데이트 문서는 CPU 계산을 바꾸고 기존 값을 Details의 선택적 `CPU Utility` 열로 남겼다고 설명합니다. 따라서 “현재 모든 Task Manager의 CPU는 항상 Utility”라고 쓰지 않습니다. 해당 공지는 새 계산의 모든 PDH 대응을 명세하지도 않습니다. [Windows 11 KB5064081](https://support.microsoft.com/en-au/servicing/os/windows-11/2025/08/august-29-2025-kb5064081-os-build-26100-5074-preview)

PDH의 rate 계열 등 두 표본이 필요한 카운터는 `PdhCollectQueryData`로 첫 기준점을 얻고 간격 뒤 다시 수집한 다음 formatted 값을 계산합니다. 첫 응답의 미완성 상태를 0%로 출력하지 않습니다. 모든 gauge까지 무조건 두 점 차분하는 것도 잘못입니다. 원천 counter type, 반환 `CStatus`, instance 수명과 계산 구간을 확인합니다. [PDH 표본 수집](https://learn.microsoft.com/en-us/windows/win32/perfctrs/collecting-performance-data)

**예시:** Committed Bytes=12 GiB, Commit Limit=16 GiB이면 `75%`입니다. 동시에 Available MBytes가 보고하는 물리 여유는 별도 값이며 이 식으로 역산하지 않습니다. 제품에는 원천 counter path·OS build·표본 간격·원래 단위를 남기고 범용 임계값을 임의로 붙이지 않습니다. 실제 조회에는 제공자별 읽기 권한이 필요하고 많은 instance의 고빈도 수집은 부하를 늘립니다.

## Linux와 비교할 때

| 질문 | Linux에서 읽을 개념 | Windows에서 읽을 개념 |
| --- | --- | --- |
| CPU 시간을 얼마나 사용했는가? | CPU·프로세스 시간 회계 | System·Process 시간 회계 |
| 물리 메모리 여유는 있는가? | MemAvailable의 추정 의미 | PhysicalAvailable의 정의 |
| 프로세스가 무엇을 보유하는가? | RSS·PSS·매핑 | Working Set·PrivateUsage |
| 메모리 약속이 얼마나 남았는가? | Overcommit 정책과 Commit 항목 | CommitTotal·CommitLimit |

공통 질문을 연결하는 표이며 값의 완전한 동등성을 의미하지 않습니다.

## 이해 확인

- GetSystemTimes의 Kernel+User+Idle을 총량으로 쓰는가? **Idle이 Kernel에 포함되므로 중복이다.**
- PrivateUsage가 1 GiB면 페이지 파일에 1 GiB가 쓰여 있는가? **Commit Charge이므로 그렇게 해석할 수 없다.**
- 프로세서 128개 시스템에서 한 번 호출한 GetSystemTimes가 전체를 대표하는가? **문서의 Processor Group 범위를 먼저 확인해야 한다.**
- Task Manager와 수집기 CPU가 다르면 수집기가 틀린가? **Time/Utility·build·표본 구간·instance 범위를 먼저 맞춘다.**

관련: [CPU](cpu.md), [메모리](memory.md), [시계열](../foundations/time-series.md)
