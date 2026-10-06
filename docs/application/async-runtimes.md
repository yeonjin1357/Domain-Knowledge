# Go, Node.js, Python의 동시성과 관측

> 상태: 검토됨 · 적용 범위: Go 런타임 API, Node.js 26.10.0·24.19.0 이벤트 루프, CPython 3.14 · 원천 확인일: 2026-10-06 · 실습 여부: 원천·가상 예시 중심; 연결 실습의 범위는 본문

## 먼저 이해할 것

비동기 처리는 응답을 기다리는 동안 다른 일을 진행할 수 있게 만드는 방식입니다. 모든 작업이 동시에 CPU에서 실행된다는 뜻은 아닙니다. event loop에서 오래 계산하거나 동기 호출로 막히면 다른 작업의 시작도 늦어질 수 있습니다. Go·Node.js·Python은 실행 모델과 관측 원천을 따로 확인합니다.

동시 작업 수, OS 스레드 수, CPU에서 실제 실행 중인 작업 수는 서로 다릅니다. 언어 이름만으로 실행 모델을 확정하지 말고 런타임·빌드·프레임워크 설정을 확인합니다.

## Go의 작업과 메모리

Go의 `runtime/metrics`는 런타임 지표의 이름·단위·종류를 설명하며 지원 지표 집합을 조회할 수 있습니다. goroutine 수, 스케줄러 지연, heap·GC 관련 자료를 목적에 맞게 사용할 수 있지만 버전별 지원 여부를 확인해야 합니다. [Go runtime/metrics](https://pkg.go.dev/runtime/metrics)

goroutine 수를 요청 수로 해석하지 않는 모델을 제안합니다. 한 요청이 여러 goroutine을 만들 수 있고 요청과 무관한 배경 작업도 있습니다. 수가 증가하면 상태별 스택, 대기 대상, 생성·종료 패턴을 추가로 조사합니다.

Go GC의 `GOGC`와 메모리 제한은 GC의 자원 사용에 영향을 줍니다. 런타임의 메모리 제한은 soft limit이며 모든 상황에서 프로세스 RSS가 그 값 아래에 머무는 보장은 아닙니다. Go가 관리하지 않는 메모리도 따로 고려해야 합니다. [Go GC Guide](https://go.dev/doc/gc-guide)

가상으로 컨테이너 제한 1 GiB와 런타임 제한 900 MiB를 설정했다고 해서 항상 124 MiB의 물리 여유가 보장되는 것은 아닙니다. 두 값의 회계 범위와 native 메모리, 현재 사용량을 확인합니다.

## Node.js의 이벤트 루프와 worker pool

Node.js에서는 이벤트 루프의 callback 처리와 libuv worker pool의 작업을 구분해야 합니다. 오래 걸리는 callback은 같은 이벤트 루프의 다른 작업을 지연시킬 수 있고, worker pool의 긴 작업도 풀을 사용하는 다른 작업에 영향을 줄 수 있습니다. 모든 비동기 API가 같은 방식으로 worker pool을 쓰는 것은 아닙니다. [Node.js: Don't Block the Event Loop](https://nodejs.org/learn/asynchronous-work/dont-block-the-event-loop)

제품에서는 이벤트 루프 지연, 프로세스 CPU, 작업 유형, 의존 호출을 같이 관측하도록 제안합니다. 8 CPU 호스트에서 하나의 실행 스레드가 계속 CPU를 써도 호스트 전체 대비 사용률은 약 12.5%로 보일 수 있습니다. 낮은 전체 CPU만으로 해당 루프의 여유를 판단할 수 없습니다.

`monitorEventLoopDelay()`는 이벤트 루프 지연의 히스토그램을 제공하며 지연의 단위는 nanoseconds입니다. 샘플링 방식과 간격에 따라 관측 결과가 달라질 수 있으므로 수집 설정도 기록합니다. [Node.js perf_hooks](https://nodejs.org/api/perf_hooks.html#perf_hooksmonitoreventloopdelayoptions)

```text
합성 표본 25,000,000 ns = 25 ms = 0.025 s
```

이벤트 루프 지연 25 ms를 그대로 요청의 p99 25 ms로 부르지 않습니다. 표본 대상과 분포가 다릅니다.

### ELU는 프로세스 CPU 비율이 아니다

**Node.js v26.10.0·v24.19.0 문서 확인: 2026-10-06.** `performance.eventLoopUtilization()`은 이벤트 루프의 누적 active·idle 시간을 고해상도 ms로 제공하고 그 비율을 계산합니다. 이전 호출 결과를 인자로 주면 구간 값을 얻을 수 있습니다. 직접 만든 객체를 전달하거나 utilization 비율끼리 뺄셈하지 않습니다. active는 event provider(예: epoll_wait) 밖의 시간이라 동기 블로킹에도 높아질 수 있습니다. OS CPU 사용률과 나란히 보아야 “계산 중”과 “루프 진행이 막힘”을 구분할 수 있습니다. [고정 버전 perf_hooks 원천](https://github.com/nodejs/node/blob/v26.10.0/doc/api/perf_hooks.md)

같은 문서에서 `monitorEventLoopDelay`의 **버전 메모:** `samplePerIteration`은 **26.5.0에 추가되고 24.19.0 LTS에도 backport**됐습니다. v25.9.0 문서에는 이 옵션이 없으므로 단순한 major 버전 대소 비교로 지원 여부를 판정하지 않습니다. 기본 false에서는 `resolution`(기본 10 ms) timer로 표본을 얻습니다. true에서는 루프 iteration마다 prepare/check hook으로 표본을 얻으며 resolution은 무시합니다. true 모드는 유휴 상태에서 루프를 살려 두거나 추가 iteration을 강제하지 않습니다. 두 모드의 결과는 상당히 달라 직접 비교하지 말라는 API 설명을 따릅니다. 같은 지표 이름이라도 모드 변경 전후를 연속 분포로 합치지 않습니다. [v26.10.0 API](https://github.com/nodejs/node/blob/v26.10.0/doc/api/perf_hooks.md#perf_hooksmonitoreventloopdelayoptions), [24.19.0 추가 기록](https://github.com/nodejs/node/blob/v24.19.0/doc/api/perf_hooks.md#perf_hooksmonitoreventloopdelayoptions), [25.9.0 원천](https://github.com/nodejs/node/blob/v25.9.0/doc/api/perf_hooks.md)

제품 적용 제안: runtime·worker 수명, 측정 모드, resolution, histogram reset 시각을 보존합니다. histogram의 enable/disable·reset은 계측 상태 변경이며 반복 관측 비용이 있습니다. 애플리케이션 또는 허용된 계측 코드에 추가해야 하며 외부에서 PID만 알면 읽을 수 있는 파일은 아닙니다. 이 절에서는 Node 프로세스에 계측을 설치하거나 실행하지 않았습니다.

## Python: GIL과 asyncio는 다른 축이다

CPython에는 GIL이 있는 일반 실행과 free-threaded 빌드가 있습니다. 3.13부터 도입된 free-threading 지원에서는 빌드가 이를 지원하는지와 현재 GIL이 실제로 꺼져 있는지가 별도 문제이며, 확장 모듈에 의해 GIL이 다시 활성화될 수도 있습니다. 따라서 “Python은 언제나 한 코어만 쓴다”는 일반화는 피해야 합니다. [CPython 3.14 free threading](https://docs.python.org/3.14/howto/free-threading-python.html)

asyncio의 이벤트 루프는 자신이 실행되는 스레드에서 task와 callback을 처리합니다. 그 스레드에서 긴 CPU 연산이나 블로킹 작업을 수행하면 다른 task의 진행을 늦출 수 있습니다. executor 등으로 작업을 옮기는 선택은 작업 성격과 구현에 따라 판단합니다. [CPython 3.14 asyncio 개발](https://docs.python.org/3.14/library/asyncio-dev.html)

따라서 Python 모니터링에는 프로세스 수, 스레드 수, 이벤트 루프, task, GIL 상태와 확장 모듈의 실행을 구분할 필요가 있습니다. `async def`라는 문법만으로 내부 작업이 비블로킹임을 보장하지 않습니다.

## 공통 비교표

다음은 통합 화면에 연결할 관측 질문이며 서로 다른 런타임의 지표가 완전히 같은 뜻이라는 매핑은 아닙니다.

| 질문 | Go 예 | Node.js 예 | Python 예 |
| --- | --- | --- | --- |
| 실행 기회를 기다리는가 | 스케줄러 지연·스택 | 루프 지연·callback | task 지연·callback |
| 작업이 쌓이는가 | goroutine 상태 | 큐·대기 요청 | task·executor 큐 |
| 어디에 메모리를 쓰는가 | heap·런타임·native | V8 heap·외부 메모리·RSS | 객체·확장 할당·RSS |
| 회수가 요청에 영향을 주는가 | GC 시간과 요청 시간 | GC 이벤트와 루프 지연 | GC·할당과 요청 시간 |

## 가상 진단 절차

동시 요청이 증가하고 전체 CPU는 낮다면 런타임별 대기 지점을 확인합니다. 그 결과 원격 호출 대기라면 네트워크·DB로, callback의 긴 연산이라면 프로파일로, 풀 획득 대기라면 [연결 풀](requests-and-concurrency.md)로 이어집니다. 언어 이름만으로 원인이나 최적화 방법을 지정하지 않습니다.

## 이해 확인

1. goroutine 10,000개는 요청 10,000개인가? **일대일 관계가 보장되지 않습니다.**
2. 이벤트 루프 지연과 요청 지연은 같은 분포인가? **표본 대상이 다릅니다.**
3. CPython 버전만으로 GIL 상태를 확정할 수 있는가? **빌드와 실제 실행 상태를 확인해야 합니다.**
4. ELU가 높은데 CPU가 낮을 수 있는가? **동기 블로킹으로 루프가 진행하지 못하면 가능합니다.**
5. Node의 timer 모드와 iteration 모드 지연 p99를 바로 비교해도 되는가? **표본 방식이 달라 모드·설정을 함께 구분해야 합니다.**

이전: [OpenTelemetry 이름·단위·안정성으로 의미 연결하기](semantic-conventions.md) · 다음: [브라우저, 실제 사용자 관측과 합성 검사(synthetic monitoring)](user-experience.md) · [분야 목차](README.md)
