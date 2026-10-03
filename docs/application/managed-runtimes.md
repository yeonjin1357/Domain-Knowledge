# JVM과 .NET: 메모리, GC, 실행 자원

> 상태: 본문 초안 · 적용 범위: JDK 25 API·HotSpot/G1 사례, .NET 공식 진단 원리 · 출처 확인일: 2026-10-03

런타임 내부 지표와 OS 프로세스 지표를 함께 읽어야 합니다. heap이 작아도 프로세스 메모리가 클 수 있고, CPU가 낮아도 작업 실행을 기다리는 요청이 많을 수 있습니다.

## JVM 메모리의 네 값

Java `MemoryUsage`는 init, used, committed, max를 구분합니다. committed는 JVM이 사용 가능하도록 확보한 메모리이며 used 이상입니다. max는 정의되지 않을 수 있고, max 이하여도 추가 확보에 실패할 수 있습니다. [JDK 25 MemoryUsage](https://docs.oracle.com/en/java/javase/25/docs/api/java.management/java/lang/management/MemoryUsage.html)

합성 예로 heap used 600 MiB, committed 1 GiB, max 2 GiB라면 다음 두 비율을 얻습니다.

```text
확보한 heap 대비 = 600 / 1024 = 58.59%
최대 heap 대비   = 600 / 2048 = 29.30%
```

두 값을 “메모리 사용률” 한 이름으로 표시하면 의미가 사라집니다. max가 정의되지 않은 경우에도 임의의 0이나 무한대 분모를 넣지 않습니다.

heap 외에도 클래스 메타데이터, 코드, 스레드, 런타임 내부 메모리 등이 존재합니다. HotSpot의 Native Memory Tracking은 내부 메모리 범주를 조사하는 도구이지만 모든 네이티브 라이브러리 할당을 포괄하는 OS 메모리 회계와 같지는 않습니다. 지원 도구와 옵션은 JVM 구현·버전에 의존합니다. [JDK 25 Diagnostic Tools](https://docs.oracle.com/en/java/javase/25/troubleshoot/diagnostic-tools.html)

## GC는 여러 축으로 관측한다

G1은 선택한 영역의 살아 있는 객체를 옮기며 공간을 회수하고 정지 시간 목표를 추구하지만 실시간 수집기가 아니므로 모든 개별 정지의 상한을 보장하지 않습니다. 이를 모든 JVM 수집기의 동작으로 일반화하지 않습니다. [JDK 25 G1](https://docs.oracle.com/en/java/javase/25/gctuning/garbage-first-g1-garbage-collector1.html)

진단용으로 다음 축을 함께 보는 것을 제안합니다.

| 축 | 답하려는 질문 |
| --- | --- |
| 할당 속도 | 새 객체를 얼마나 빠르게 만드는가 |
| 회수 뒤 살아 있는 크기 | 비슷한 부하·회수 단계 뒤에도 기준선이 자라는가 |
| 정지 시간 분포 | 요청 지연에 영향을 줄 긴 정지가 있는가 |
| GC CPU 시간 | 동시·병렬 작업에 CPU를 얼마나 쓰는가 |
| 회수 횟수·원인 | 어떤 작업이 어떤 이유로 실행됐는가 |

병렬 GC 작업자 CPU 시간을 모두 더한 값은 벽시계 정지 시간보다 클 수 있습니다. 합성 예에서 4개 작업자가 각각 20 ms를 사용하면 CPU 합은 80 ms지만 같은 구간에서 병렬로 수행됐다면 정지 시간은 20 ms 규모일 수 있습니다. CPU 시간과 정지 시간을 같은 카운터로 합치지 않습니다.

한 번의 heap 증가만으로 누수를 확정하지 않습니다. 워밍업, 캐시 성장, 부하 변화, 수집기 정책을 구분하고 비슷한 조건에서 살아 있는 객체와 참조 관계가 어떻게 변하는지 조사합니다.

## .NET의 세대와 메모리

.NET GC는 관리 객체의 생존 기간에 따라 세대를 사용하며 큰 객체의 처리는 일반 작은 객체와 다른 경로를 가집니다. 관리 heap의 회수와 OS 프로세스 working set은 서로 다른 관측입니다. 실행 환경의 GC 모드와 버전을 함께 기록해야 합니다. [Microsoft: GC Fundamentals](https://learn.microsoft.com/en-us/dotnet/standard/garbage-collection/fundamentals)

JVM의 특정 pool 이름을 .NET 세대에 일대일 매핑하는 대신, 공통 화면에는 관측 목적을 두고 세부 원천 이름을 보존하는 설계를 제안합니다. `할당`, `살아 있는 메모리`, `회수`, `정지`처럼 의미가 대응하는 축과 실제 엔진의 지표를 연결합니다.

## CPU가 낮은 ThreadPool 부족

.NET의 ThreadPool starvation 조사에서는 큐·완료 작업·스레드 수와 호출 스택을 비교합니다. 작업자가 블로킹된 상황에서는 CPU가 충분히 사용되지 않아도 요청이 지연될 수 있습니다. 스레드가 점진적으로 늘면서 CPU가 낮은 패턴은 조사 단서이지 모든 환경에 대한 단독 판정식은 아닙니다. [Microsoft: Debug ThreadPool Starvation](https://learn.microsoft.com/en-us/dotnet/core/diagnostics/debug-threadpool-starvation)

가상 사례에서 스레드 수가 40→100, 대기 작업이 0→500, CPU가 20%라면 스레드가 어디에서 기다리는지 확인합니다. DB 풀 대기, 동기적 I/O, 잠금이 후보입니다. 스레드 수 증가 자체를 처리 능력 증가로 해석하지 않습니다.

## 수집 설계

런타임 버전, GC 종류, 설정 상한, CPU·메모리의 컨테이너 제한을 인벤토리에 연결합니다. 스택과 heap 덤프는 정보량과 비용이 큰 별도 진단 자료로 다루고, 정기 지표 수집과 같은 빈도로 실행하지 않는 설계를 제안합니다. 이 저장소에서는 대상 JVM·.NET 프로세스에 진단 명령을 실행하지 않았습니다.

## 이해 확인

1. JVM committed가 OS RSS와 같은가? **관측 범위와 의미가 다릅니다.**
2. 정지 시간 목표 100 ms는 모든 정지의 보장 상한인가? **G1에서는 목표이며 절대 보장이 아닙니다.**
3. CPU가 낮으면 ThreadPool 대기가 없는가? **블로킹으로 대기가 늘 수 있습니다.**

다음: [Go·Node.js·Python](async-runtimes.md) · [애플리케이션 목차](README.md)
