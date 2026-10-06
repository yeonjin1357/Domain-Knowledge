# JVM과 .NET: 메모리, GC, 실행 자원

> 상태: 검토됨 · 적용 범위: JDK 25 API·HotSpot/G1 사례, .NET 공식 진단 원리·.NET 10+ collect-linux preview · 원천 확인일: 2026-10-06 · 실습 여부: 원천·가상 예시 중심; 연결 실습의 범위는 본문

## 먼저 이해할 것

JVM과 .NET runtime은 코드 실행과 메모리 관리를 지원합니다. 객체를 만드는 영역인 heap은 프로세스 메모리의 일부이며, 사용하지 않게 된 객체를 회수하는 GC도 자원을 씁니다. heap 크기·프로세스 메모리·GC 정지 시간은 서로 다른 값이므로 각각의 경계를 확인합니다.

런타임 내부 지표와 OS 프로세스 지표를 함께 읽어야 합니다. heap이 작아도 프로세스 메모리가 클 수 있고, CPU가 낮아도 작업 실행을 기다리는 요청이 많을 수 있습니다.

## JVM 메모리의 네 값

Java `MemoryUsage`는 init, used, committed, max를 구분합니다. committed는 JVM이 사용 가능하도록 확보한 메모리이며 used 이상입니다. max는 정의되지 않을 수 있고, max 이하여도 추가 확보에 실패할 수 있습니다. [JDK 25 MemoryUsage](https://docs.oracle.com/en/java/javase/25/docs/api/java.management/java/lang/management/MemoryUsage.html)

가상 예시로 heap used 600 MiB, committed 1 GiB, max 2 GiB라면 다음 두 비율을 얻습니다.

```text
확보한 heap 대비 = 600 / 1024 = 58.59%
최대 heap 대비   = 600 / 2048 = 29.30%
```

두 값을 “메모리 사용률” 한 이름으로 표시하면 의미가 사라집니다. max가 정의되지 않은 경우에도 임의의 0이나 무한대 분모를 넣지 않습니다.

heap 외에도 클래스 메타데이터, 코드, 스레드, 런타임 내부 메모리 등이 존재합니다. HotSpot의 Native Memory Tracking은 내부 메모리 범주를 조사하는 도구이지만 모든 네이티브 라이브러리 할당을 포괄하는 OS 메모리 회계와 같지는 않습니다. 지원 도구와 옵션은 JVM 구현·버전에 의존합니다. [JDK 25 Diagnostic Tools](https://docs.oracle.com/en/java/javase/25/troubleshoot/diagnostic-tools.html)

## GC는 여러 축으로 관측한다

G1은 선택한 영역의 살아 있는 객체를 옮기며 공간을 회수하고 정지 시간 목표를 추구하지만 실시간 상한을 보장하는 GC가 아니므로 모든 개별 정지의 상한을 보장하지 않습니다. 이를 모든 JVM GC의 동작으로 일반화하지 않습니다. [JDK 25 G1](https://docs.oracle.com/en/java/javase/25/gctuning/garbage-first-g1-garbage-collector1.html)

진단용으로 다음 축을 함께 보는 것을 제안합니다.

| 축 | 답하려는 질문 |
| --- | --- |
| 할당 속도 | 새 객체를 얼마나 빠르게 만드는가 |
| 회수 뒤 살아 있는 크기 | 비슷한 부하·회수 단계 뒤에도 기준선이 자라는가 |
| 정지 시간 분포 | 요청 지연에 영향을 줄 긴 정지가 있는가 |
| GC CPU 시간 | 동시·병렬 작업에 CPU를 얼마나 쓰는가 |
| 회수 횟수·원인 | 어떤 작업이 어떤 이유로 실행됐는가 |

병렬 GC 작업자 CPU 시간을 모두 더한 값은 벽시계 정지 시간보다 클 수 있습니다. 가상 예시에서 4개 작업자가 각각 20 ms를 사용하면 CPU 합은 80 ms지만 같은 구간에서 병렬로 수행됐다면 정지 시간은 20 ms 규모일 수 있습니다. CPU 시간과 정지 시간을 같은 카운터로 합치지 않습니다.

한 번의 heap 증가만으로 누수를 확정하지 않습니다. 워밍업, 캐시 성장, 부하 변화, 수집기 정책을 구분하고 비슷한 조건에서 살아 있는 객체와 참조 관계가 어떻게 변하는지 조사합니다.

## JVM: 합계에서 pool·event로 내려간다

**JMX(Java Management Extensions)**는 JVM의 관리 인터페이스이고 **MBean**은 그 인터페이스에 노출되는 관리 객체입니다. 먼저 전체 사용량·정지·할당을 보고 필요한 pool과 이벤트로 내려갑니다.

heap은 안정적인데 RSS가 증가한다면 heap 합계만 반복해서 읽어서는 원인을 찾기 어렵습니다. JMX 관리 인터페이스에서 pool별 상태를 보고, 변화 구간의 JFR 이벤트로 할당·GC·대기의 위치를 좁힙니다.

| 원천 | 단위·관측 범위 | 함정 |
| --- | --- | --- |
| `java.lang:type=MemoryPool,name=...` | `Usage`·`PeakUsage`·`CollectionUsage`의 바이트 값 | pool을 이름으로 열거; CollectionUsage는 최근 회수 후 값이며 현재 RSS가 아님 |
| `java.lang:type=GarbageCollector,name=...` | CollectionCount, CollectionTime(ms) | 미정의 시 −1; 대략적인 누적 collection 시간이지 모든 stop-the-world 구간의 정확한 합이 아님 |
| `java.nio:type=BufferPool,name=...` | direct·mapped 등의 Count, TotalCapacity, MemoryUsed(bytes) | capacity와 실제 메모리 추정은 정렬·할당자 때문에 다를 수 있음; 미지원 추정 −1 |

pool의 지원 threshold·유효성·max 미정의 상태는 API 결과로 확인합니다. HotSpot의 Metaspace 같은 non-heap pool, direct/mapped buffer와 OS의 RSS는 회계 범위가 다릅니다. mapped buffer의 capacity 전체를 현재 RAM 상주량으로 더하지 않습니다. [MemoryPoolMXBean](https://docs.oracle.com/en/java/javase/25/docs/api/java.management/java/lang/management/MemoryPoolMXBean.html), [GarbageCollectorMXBean](https://docs.oracle.com/en/java/javase/25/docs/api/java.management/java/lang/management/GarbageCollectorMXBean.html), [BufferPoolMXBean](https://docs.oracle.com/en/java/javase/25/docs/api/java.management/java/lang/management/BufferPoolMXBean.html), [HotSpot 클래스 메타데이터](https://docs.oracle.com/en/java/javase/25/gctuning/other-considerations.html)

JFR은 `jdk.GarbageCollection`, `jdk.GCPhasePause`, `jdk.ExecutionSample`, 파일·소켓·monitor 대기 등의 이벤트를 통해 시간과 원인을 연결합니다. 켜진 이벤트, threshold, 주기, stack trace 설정을 기록해야 합니다. 임계 시간보다 짧은 작업이 기록되지 않았다면 “그 작업이 전혀 없었다”가 아닙니다. 기록 템플릿·실제 JDK가 제공하는 이벤트를 먼저 확인합니다. [JDK 25 JFR 분석](https://docs.oracle.com/en/java/javase/25/troubleshoot/troubleshoot-performance-issues-using-jfr.html), [JFR EventSettings](https://docs.oracle.com/en/java/javase/25/docs/api/jdk.jfr/jdk/jfr/EventSettings.html)

`default.jfc`와 `profile.jfc`는 서로 다른 비용·상세도 선택입니다. 어떤 workload에서도 고정된 낮은 오버헤드라는 보증으로 쓰지 않습니다. 특히 heap statistics를 켜는 진단은 추가 GC와 정지 시간을 유발할 수 있습니다. 제품은 기본 지표와 제한된 기간의 상세 recording을 분리하고 recording 설정·용량·종료 조건을 보존하도록 제안합니다. [jcmd JFR 설정](https://docs.oracle.com/en/java/javase/25/docs/specs/man/jcmd.html), [JFR 비용 설명](https://docs.oracle.com/en/java/javase/25/troubleshoot/troubleshoot-performance-issues-using-jfr.html)

JMX attribute 읽기는 읽기 전용이지만 MBean operation에는 GC·설정 변경이 포함될 수 있습니다. JFR 시작·종료는 계측 상태를 바꾸고 파일·CPU 비용을 발생시킵니다. 이 장에서는 둘 다 실행하지 않았습니다. local attach 또는 인증·접근 제어가 설정된 관리 경로를 전제로 하며 공개 무인증 JMX endpoint를 수집 전제로 삼지 않습니다. [JMX 원격 관측과 보안](https://docs.oracle.com/en/java/javase/25/management/monitoring-and-management-using-jmx-technology.html)

## .NET의 세대와 메모리

.NET GC는 관리 객체의 생존 기간에 따라 세대를 사용하며 큰 객체의 처리는 일반 작은 객체와 다른 경로를 가집니다. 관리 heap의 회수와 OS 프로세스 working set은 서로 다른 관측입니다. 실행 환경의 GC 모드와 버전을 함께 기록해야 합니다. [Microsoft: GC Fundamentals](https://learn.microsoft.com/en-us/dotnet/standard/garbage-collection/fundamentals)

런타임 간 공통 화면의 관측 축은 [GC 관측 표](#gc는-여러-축으로-관측한다)를 따릅니다. JVM pool과 .NET 세대를 같은 이름으로 치환하지 않고 각 원천의 정의를 보존합니다.

## CPU가 낮은 ThreadPool 부족

.NET의 ThreadPool starvation 조사에서는 큐·완료 작업·스레드 수와 호출 스택을 비교합니다. 작업자가 블로킹된 상황에서는 CPU가 충분히 사용되지 않아도 요청이 지연될 수 있습니다. 스레드가 점진적으로 늘면서 CPU가 낮은 패턴은 조사 단서이지 모든 환경에 대한 단독 판정식은 아닙니다. [Microsoft: Debug ThreadPool Starvation](https://learn.microsoft.com/en-us/dotnet/core/diagnostics/debug-threadpool-starvation)

가상 사례에서 스레드 수가 40→100, 대기 작업이 0→500, CPU가 20%라면 스레드가 어디에서 기다리는지 확인합니다. DB 풀 대기, 동기적 I/O, 잠금이 후보입니다. 스레드 수 증가 자체를 처리 능력 증가로 해석하지 않습니다.

## .NET: 지표 수집과 EventPipe 세션을 구분한다

EventPipe는 .NET runtime·EventSource 이벤트를 프로세스 밖 진단 도구로 보내거나 `.nettrace`로 기록하는 경로입니다. **일반 `dotnet-trace collect` 기준**으로는 커널·native 이벤트와 native frame을 함께 수집하는 OS 전체 profiler로 설명하지 않습니다. `dotnet-counters`는 EventCounter와 Meter API의 값을 관측하고, 상세 trace는 `dotnet-trace` 같은 도구를 사용합니다. [EventPipe](https://learn.microsoft.com/en-us/dotnet/core/diagnostics/eventpipe), [dotnet-counters](https://learn.microsoft.com/en-us/dotnet/core/diagnostics/dotnet-counters)

**버전 메모(2026-10-06 확인):** 공식 문서는 별도 **preview `dotnet-trace collect-linux`** 경로를 제공합니다. .NET 10+, Linux kernel 6.4+의 `CONFIG_USER_EVENTS=y`, tracefs, root 권한 등이 필요하며 perf_events·user_events를 통해 관리 이벤트와 native/커널 이벤트·스택을 함께 기록합니다. Linux x64/Arm64 및 glibc 조건, 새 nettrace 형식을 읽을 분석 도구의 지원도 확인합니다. 기본 설정은 시스템의 여러 프로세스를 수집하므로 대상 제한을 별도로 설계합니다. 일반 collect의 권한·범위로 이 모드를 실행할 수 있다고 가정하지 않으며, 이 장에서는 실행하지 않았습니다. [두 수집 방식과 collect-linux 전제](https://learn.microsoft.com/en-us/dotnet/core/diagnostics/dotnet-trace#dotnet-trace-collect-linux)

도구 버전·runtime 버전·provider/meter·interval·단위를 수집 계약에 남깁니다. `dotnet-counters --counters System.Runtime`도 대상이 .NET 8 이하이면 System.Runtime Meter가 없으므로 구형 EventCounter 표시로 fallback합니다. 같은 명령으로 얻었다는 이유로 이름·단위·집계 의미가 같은 것으로 매핑하지 않습니다. 구형 EventCounter와 새로운 Meter 또는 [OTel 안정 이름](semantic-conventions.md)은 각각 정의를 확인합니다. 이벤트가 꺼졌거나 구독에 실패한 상태도 0으로 저장하지 않습니다. [대상 runtime별 fallback](https://learn.microsoft.com/en-us/dotnet/core/diagnostics/dotnet-counters)

설명용 명령 `dotnet-counters monitor --process-id 1234 --counters System.Runtime`는 **여기서 실행하지 않았습니다**. 대상 프로세스의 진단 endpoint 접근 권한이 필요하며 Linux/macOS에서는 도구와 대상의 TMPDIR도 맞아야 합니다. 진단 세션과 주기적 계측에 비용이 발생하고, 세션 종료 시 수집을 해제해야 합니다. 이 명령은 단순 기존 파일 읽기와 달리 대상의 진단 세션을 활성화합니다. [도구의 연결 조건](https://learn.microsoft.com/en-us/dotnet/core/diagnostics/dotnet-counters), [진단 포트의 보안](https://learn.microsoft.com/en-us/dotnet/core/diagnostics/diagnostic-port)

## 수집 설계

런타임 버전, GC 종류, 설정 상한, CPU·메모리의 컨테이너 제한을 인벤토리에 연결합니다. 스택과 heap 덤프는 정보량과 비용이 큰 별도 진단 자료로 다루고, 정기 지표 수집과 같은 빈도로 실행하지 않는 설계를 제안합니다. 이 저장소에서는 대상 JVM·.NET 프로세스에 진단 명령을 실행하지 않았습니다.

실제 OTel 필드로 연결할 때는 [HTTP·JVM·.NET의 안정 이름과 단위](semantic-conventions.md)를 이어 읽습니다. 런타임 간 공통 분류가 원천 지표의 시점·집계 형태까지 같게 만들지는 않습니다.

## 이해 확인

1. JVM committed가 OS RSS와 같은가? **관측 범위와 의미가 다릅니다.**
2. 정지 시간 목표는 모든 정지의 보장 상한인가? **G1에서는 목표이며 절대 보장이 아닙니다.**
3. CPU가 낮으면 ThreadPool 대기가 없는가? **블로킹으로 대기가 늘 수 있습니다.**
4. BufferPool TotalCapacity를 RSS에 더하면 native 메모리 총량인가? **예약·할당·상주의 범위가 다르고 중복될 수 있습니다.**
5. JFR에 짧은 소켓 대기 이벤트가 없으면 대기 자체가 없었는가? **이벤트 활성화와 threshold·표본 조건부터 확인해야 합니다.**

이전: [시간 제한, 취소, 재시도와 과부하](timeouts-and-retries.md) · 다음: [OpenTelemetry 이름·단위·안정성으로 의미 연결하기](semantic-conventions.md) · [분야 목차](README.md)
