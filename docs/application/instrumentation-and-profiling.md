# 계측을 넣는 위치: 자동 계측, 수동 span, eBPF와 프로파일

> 상태: 검토됨 · 적용 범위: OpenTelemetry·Linux BPF·런타임 프로파일의 개념 · 검토일: 2026-10-04

계측은 시스템의 동작을 기록하도록 측정 지점을 넣는 일입니다. 계측 위치가 다르면 같은 요청도 다르게 보입니다. 현관에서 잰 체류 시간과 계산대에서 잰 업무 시간이 다르듯이, HTTP client span과 server span의 시간은 원래 동일할 필요가 없습니다.

## 자동 계측과 업무 계측

OpenTelemetry Java agent는 애플리케이션 시작 시 부착해 지원하는 라이브러리 경계에 계측을 적용합니다. 라이브러리·버전·설정에 따라 지원 범위가 다르며, 설치했다는 이유만으로 모든 내부 함수와 업무 사건이 보이는 것은 아닙니다. [Java agent](https://opentelemetry.io/docs/zero-code/java/agent/)

수동 span은 예를 들어 “가격 계산”, “재고 예약” 같은 업무 경계를 표현할 수 있습니다. 모든 작은 함수를 span으로 만들면 비용과 데이터 양이 커지므로 분석에 의미 있는 경계를 선정합니다. 자동 계측이 이미 만든 같은 경계에 수동 계측을 겹치면 중복 기록이 생길 수 있어 실제 trace를 확인해야 합니다.

## HTTP 계측에서 필요한 분리

| 구분 | 예시 | 해석 |
| --- | --- | --- |
| client와 server | 앱 A의 HTTP client, 앱 B의 HTTP server | 관측 위치와 시간 범위가 다름 |
| route와 raw URL | `/orders/{id}`와 `/orders/123` | route는 집계용 낮은 cardinality에 유리 |
| HTTP status와 span status | 404와 Error 여부 | client/server 문맥과 규약을 확인 |
| 논리 요청과 attempt | 재시도되는 하나의 호출 | 몇 번의 시도를 기록했는지 구분 |

HTTP semantic conventions는 메서드·상태 코드·route·오류 등의 속성과 span의 경계를 정의합니다. server와 client의 오류 분류가 같다고 단정하지 않습니다. 구현에 적용한 semantic convention 버전과 안정성 전환 옵션도 기록합니다. [HTTP spans 규약](https://opentelemetry.io/docs/specs/semconv/http/http-spans/)

예시로 사용자가 주문 1건을 만들고 내부 결제 호출이 3번 시도되었다면, 서비스 간 attempt 수는 3이어도 주문 수는 1입니다. 모든 span 수를 요청 처리량으로 합산하지 않습니다.

## 문맥이 끊기는 위치

Trace ID와 parent 관계는 프로세스 경계를 지나 전달되어야 이어집니다. HTTP header가 프록시에서 제거되거나 비동기 작업의 문맥 연결이 누락되면 같은 업무가 여러 trace로 보일 수 있습니다. 메시지 처리는 생산 시점과 소비 시점의 관계를 parent 또는 link로 표현하는 규약과 실제 구현을 확인합니다. [OpenTelemetry context propagation](https://opentelemetry.io/docs/concepts/context-propagation/)

수집기가 같은 IP와 비슷한 시각을 봤다는 이유만으로 두 trace를 확정적으로 합치지 않습니다. 추정 관계를 제공한다면 어떤 증거를 사용했는지와 신뢰도를 표시하도록 제안합니다.

## eBPF가 보여 주는 것

BPF는 커널의 허용된 지점 등에서 프로그램을 실행하는 메커니즘이며 verifier·map·program type·부착 지점을 갖습니다. 관측 도구는 이를 활용해 시스템 호출·스케줄링·네트워크 등의 사건을 수집할 수 있습니다. 지원되는 지점과 권한은 커널·설정에 따라 다릅니다. [Linux BPF 문서](https://docs.kernel.org/bpf/)

eBPF를 사용한다는 말만으로 암호화된 모든 업무 payload나 DB 트랜잭션의 의미가 자동으로 보이는 것은 아닙니다. TLS 복호화 지점, 사용자 공간 함수 계측, 심볼·런타임 지원 등 실제 관측 경계를 확인해야 합니다. 커널에서 본 송신 byte와 업무상 전송 완료는 같은 사건이 아닙니다.

## 프로파일을 읽는 질문

CPU 프로파일은 CPU 실행 비용을 조사하고, allocation 프로파일은 할당이 발생한 위치를, heap 프로파일은 도구가 정의한 메모리 상태를 조사합니다. wall 또는 off-CPU 관련 프로파일이 필요할 때 CPU 프로파일을 그대로 대신 쓰지 않습니다. Go의 pprof는 여러 profile 종류를 제공하며 각 표본의 단위와 수집 방식이 다릅니다. [Go diagnostics](https://go.dev/doc/diagnostics)

가상 flame graph에서 함수 F가 CPU 표본의 40%를 차지했다면 측정 구간 CPU 표본의 분포를 설명합니다. 요청 경과 시간 40%가 F에서 쓰였다고 자동으로 바꾸지 않습니다. 대기와 병렬 실행이 있기 때문입니다. 인라이닝·심볼·스택 누락·표본 주기도 해석에 영향을 줍니다.

## 비용을 검증하는 방법

계측을 껐을 때와 켰을 때 같은 작업 구성·유입에서 CPU, 메모리, 지연, 손실을 비교합니다. 단일한 “오버헤드 1%”를 모든 환경의 보장으로 적지 않습니다. 계측량에 따라 비용이 달라지고 샘플링이 저장량을 줄여도 모든 수집 비용을 같은 비율로 줄이지는 않을 수 있습니다.

제품은 agent 버전, 계측 라이브러리, 수집 설정, 샘플링 정책, symbol 처리 상태를 함께 저장합니다. 사용자가 “아무 trace도 없다”를 실제 요청 없음과 계측 실패 중 어느 쪽으로 해석해야 하는지 확인할 수 있어야 합니다.

## 이해 확인

1. span이 100개면 사용자 요청도 100개인가? **한 요청이 여러 span과 재시도를 포함할 수 있습니다.**
2. CPU flame graph가 전체 지연 원인을 보여 주는가? **CPU를 사용하지 않은 대기가 빠질 수 있습니다.**
3. 자동 agent 설치면 모든 프레임워크가 계측되는가? **지원 버전과 실제 출력 확인이 필요합니다.**
