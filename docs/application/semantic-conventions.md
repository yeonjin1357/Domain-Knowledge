# OpenTelemetry 이름·단위·안정성으로 의미 연결하기

> 상태: 검토됨 · 적용 범위: 공식 웹 Semantic Conventions 1.44.0, HTTP·JVM·.NET의 아래 항목 · 원천 확인일: 2026-10-05 · 실습 여부: 원천·가상 예시 중심; 연결 실습의 범위는 본문

> **선수 안내:** [계측과 프로파일링](instrumentation-and-profiling.md), [시계열 종류](../foundations/time-series.md)를 먼저 읽어도 됩니다. `By`는 byte, `{collection}`은 회수 사건 수라는 단위 표기입니다. **UpDownCounter**는 증가·감소를 누적하는 계측 종류로, 현재량을 읽는 gauge와 생성 방식이 다릅니다. [OTel metric API](https://opentelemetry.io/docs/specs/otel/metrics/api/)

## 먼저 이해할 상황

새 계측기를 붙였더니 요청 지연이 천 배 작아 보일 수 있습니다. 실제 성능 개선보다 먼저 이름·단위·집계 형태가 바뀌었는지 봐야 합니다. 같은 “GC 시간”도 한 원천은 동작별 histogram, 다른 원천은 프로세스 시작 이후의 누적 정지 시간일 수 있습니다. semantic conventions는 이런 의미를 공유하기 위한 규약입니다.

이 장의 Stable 표시는 **해당 이름의 규약 상태**입니다. 사용 중인 모든 SDK·agent가 이미 그 이름을 출력하거나 모든 선택 attribute까지 Stable이라는 뜻은 아닙니다. 실제 계측 라이브러리 버전, instrumentation scope, schema URL, 출력 단위를 함께 남깁니다. [안정성 정책](https://opentelemetry.io/docs/specs/semconv/general/semantic-convention-groups/)

## HTTP의 안정 이름

아래 항목은 확인 시점 Stable입니다. metric 이름과 attribute key를 같은 종류로 취급하지 않습니다. [HTTP metric 정의](https://opentelemetry.io/docs/specs/semconv/http/http-metrics/), [HTTP attribute registry](https://opentelemetry.io/docs/specs/semconv/registry/attributes/http/)

| 항목 | 종류·단위 | 의미와 함정 |
| --- | --- | --- |
| `http.request.method` | 문자열 attribute | 요청 method; 무제한 임의 값을 지표 차원에 그대로 늘리지 않음 |
| `http.response.status_code` | 정수 attribute | 응답 status; 응답을 받지 못한 경우 임의의 0/500으로 만들지 않음 |
| `http.route` | 문자열 attribute | framework의 낮은 cardinality route template; 실제 URI path로 대신 채우지 않음 |
| `http.server.request.duration` | Histogram, `s` | 서버 HTTP 요청 처리 시간의 분포 |

**가상 예시:** 같은 관측이 구 HTTP 규약의 `http.server.duration`에서 250 ms이고 안정 이름 `http.server.request.duration`에서는 0.25 s이면 같은 시간입니다. `250 / 1000 = 0.25`로 값뿐 아니라 histogram bucket 경계·합계도 함께 변환해야 합니다. 기존 bucket 계정의 의미를 확인하지 않고 이름만 교체하면 잘못된 분포를 만듭니다.

[구 이름과 안정 이름의 대응](https://opentelemetry.io/docs/specs/semconv/non-normative/http-migration/)을 함께 확인합니다.

이전 규약을 출력하던 instrumentation의 전환 규칙에는 `OTEL_SEMCONV_STABILITY_OPT_IN=http`와 `http/dup`이 있습니다. 전자는 안정 HTTP/networking 규약으로 전환하고, 후자는 구·신 규약을 함께 내보내 단계적으로 바꾸는 용도입니다. 모든 SDK의 모든 major에서 반드시 필요한 전역 switch라고 단정하지 않습니다. [HTTP migration](https://opentelemetry.io/docs/specs/semconv/non-normative/http-migration/)

제품 적용 제안은 migration 기간의 원천 이름과 설정을 보존하고 같은 요청의 구·신 metric을 중복 합산하지 않는 것입니다. `http.route`를 지원하지 않으면 실제 `/users/고유ID`를 route 대신 넣지 말고 누락 이유를 기록합니다. 업무 성공 여부도 HTTP status 하나와 동일하지 않을 수 있습니다.

SemConv 1.44.0의 HTTP duration은 초 단위 경계 `[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1, 2.5, 5, 7.5, 10]`을 `ExplicitBucketBoundaries` advice로 지정하도록 권고합니다. SDK가 이 advice를 반영하지 않고 별도 View 설정도 없다면 실제 경계를 확인해야 합니다. Metrics SDK의 일반 기본 권고 `[0, 5, 10, 25, 50, 75, 100, 250, 500, 750, 1000, 2500, 5000, 7500, 10000]`을 초에 그대로 쓰면 0초 초과·5초 이하 요청이 하나의 bucket에 모여 짧은 지연의 구분이 거칠어집니다. 모든 SDK가 반드시 이 기본값을 쓴다는 뜻은 아닙니다. [HTTP 경계 권고](https://opentelemetry.io/docs/specs/semconv/http/http-metrics/#metric-httpserverrequestduration), [SDK 기본 aggregation](https://opentelemetry.io/docs/specs/otel/metrics/sdk/#explicit-bucket-histogram-aggregation)

## JVM: 확보·사용·최대와 GC 동작

아래 네 이름은 Stable입니다. 메모리 세 항목은 **UpDownCounter**, 단위는 `By`이며 pool·heap/non_heap 범위를 확인합니다. 이름에 Counter가 있어도 단조 증가 Counter가 아니므로 사용량에 `rate()`를 적용하지 않습니다. [JVM metric 정의](https://opentelemetry.io/docs/specs/semconv/runtime/jvm-metrics/)

| 이름 | 의미·형태 | 함께 보존할 문맥 |
| --- | --- | --- |
| `jvm.memory.used` | 사용 중 메모리 | `jvm.memory.pool.name`, `jvm.memory.type` |
| `jvm.memory.committed` | JVM이 사용 가능하도록 확보한 메모리 | OS RSS와 구분 |
| `jvm.memory.limit` | 얻을 수 있는 최대 메모리 | 원천 max의 정의·가용 여부; cgroup 한도와 구분 |
| `jvm.gc.duration` | Histogram, `s`: JVM GC action의 지속 시간 | `jvm.gc.name`, `jvm.gc.action` |

JVM memory 원천은 `MemoryPoolMXBean.getUsage()`이고, GC duration은 GC 알림의 `GcInfo`에서 옵니다. Java `MemoryUsage.max`는 정의되지 않을 수 있으므로 음수·누락 값을 임의의 정상 한도로 나누지 않습니다. GC action의 duration을 모든 collector에서 동일한 애플리케이션 정지 시간으로 간주하지 않습니다. [JDK MemoryUsage](https://docs.oracle.com/en/java/javase/25/docs/api/java.management/java/lang/management/MemoryUsage.html), [GcInfo](https://docs.oracle.com/en/java/javase/25/docs/api/jdk.management/com/sun/management/GcInfo.html)

`jvm.gc.duration`이 Stable이어도 선택 attribute `jvm.gc.cause`는 확인 시점 **Development**입니다. metric·attribute·열거 값 각각의 stability를 따로 기록합니다. [JVM GC 규약](https://opentelemetry.io/docs/specs/semconv/runtime/jvm-metrics/#metric-jvmgcduration)

## .NET: 현재값과 마지막 GC 시점의 값

다음 이름은 SemConv에서 Stable이며 공식 표의 기본 제공 Meter는 `System.Runtime`, 추가된 runtime 버전은 **.NET 9.0**입니다. 이전 runtime이나 별도 OTel instrumentation package의 이름까지 같다고 가정하지 않습니다. [CLR metric 정의](https://opentelemetry.io/docs/specs/semconv/runtime/dotnet-metrics/)

| 이름 | 형태·단위 | 의미 |
| --- | --- | --- |
| `dotnet.process.memory.working_set` | UpDownCounter, `By` | 프로세스에 매핑된 물리 메모리 |
| `dotnet.gc.heap.total_allocated` | Counter, `By` | 시작 이후 관리 heap 누적 할당의 근삿값; native 할당 제외 |
| `dotnet.gc.last_collection.heap.size` | UpDownCounter, `By` | 마지막 GC에서 본 fragmentation 포함 heap 크기 |
| `dotnet.gc.last_collection.memory.committed_size` | UpDownCounter, `By` | 마지막 GC에서 본 GC용 committed virtual memory |
| `dotnet.gc.collections` | Counter, `{collection}` | 세대별로 중복을 제거해 계산한 GC 횟수 |
| `dotnet.gc.pause.time` | Counter, `s` | 시작 이후 GC로 멈춘 시간의 누적 합 |

`dotnet.gc.last_collection.heap.size`와 `dotnet.gc.collections`에는 `dotnet.gc.heap.generation` attribute가 필수입니다. heap 합계는 같은 프로세스·시점에서 `gen0/gen1/gen2/loh/poh` 중 실제 수집한 범위를 명시하며 중복 시계열을 제거합니다. collections는 상위 세대 수집에 포함된 하위 세대 작업을 중복하지 않도록 정의된 세대별 횟수이므로 원시 `GC.CollectionCount()` 값을 무조건 더하는 계산과 구분합니다. [세대 attribute와 횟수 정의](https://opentelemetry.io/docs/specs/semconv/runtime/dotnet-metrics/)

`last_collection`은 수집 순간의 실시간 heap 표본이 아닙니다. `dotnet.gc.pause.time`의 구간 차분과 `jvm.gc.duration` histogram의 합계가 이름이 비슷하다고 같은 사건 집합이라고 주장하지 않습니다. [Microsoft System.Runtime metrics](https://learn.microsoft.com/en-us/dotnet/core/diagnostics/built-in-metrics-runtime)

## 제품 적용 제안

[런타임 간 매핑](managed-runtimes.md)의 “할당·메모리·회수·정지” 축은 탐색 분류로 사용합니다. 원천의 `현재/마지막 GC`, `누적/분포`, `GC action/정지`, `관리 heap/프로세스` 차이를 지운 단일 표준값으로 합치지 않습니다. 알려진 안정 이름을 registry로 관리하되 필드가 없으면 agent 버전·기능 설정·runtime 지원을 먼저 판별합니다.

이 장에서는 환경변수 변경, JVM/.NET 계측기 설치, exporter 호출을 실행하지 않았습니다. 실제 적용 시에는 대상 프로세스의 계측 설정 변경 권한과 재시작 필요 여부를 확인하고, histogram·attribute 추가에 따른 집계·전송 비용을 측정합니다.

## 이해 확인

1. Stable metric이면 부속 attribute도 모두 Stable인가? **아니다. 각각 확인한다.**
2. HTTP 지연 값이 250에서 0.25로 바뀌면 성능이 천 배 좋아졌는가? **ms에서 s로 바뀐 같은 시간일 수 있다.**
3. JVM used와 .NET last_collection heap size를 같은 순간의 heap으로 비교해도 되는가? **관측 시점과 포함 범위가 다르다.**
4. `http/dup`의 두 metric을 합하면 더 정확한가? **같은 요청을 중복 집계할 수 있다.**

## 함께 읽기

[런타임 메모리와 GC](managed-runtimes.md) · [계측](instrumentation-and-profiling.md) · [시계열 문맥](../foundations/metric-context-and-start-time.md)

이전: [JVM과 .NET: 메모리, GC, 실행 자원](managed-runtimes.md) · 다음: [Go, Node.js, Python의 동시성과 관측](async-runtimes.md) · [분야 목차](README.md)
