# 프록시, 로드밸런서와 서비스 메시

> 상태: 본문 초안 · 적용 범위: NGINX·Envoy·Istio의 관측 경계 · 출처 확인일: 2026-10-03

프록시는 클라이언트에 대해서는 서버이고 뒤의 애플리케이션에 대해서는 클라이언트입니다. 들어온 요청, 뒤로 보낸 시도, 최종 응답을 나눠야 지표가 맞습니다.

## 연결과 요청

NGINX stub_status의 Active connections에는 다음 요청을 기다리는 Waiting 연결도 포함됩니다. accepts·handled는 연결 누적량이고 requests는 요청 누적량입니다. 따라서 active 연결 수를 현재 실행 중인 업무 요청 수로 바꾸어 읽으면 안 됩니다. [NGINX stub_status](https://nginx.org/en/docs/http/ngx_http_stub_status_module.html)

합성 예에서 100개 연결이 각각 요청 10개를 처리했다면 연결 100과 요청 1,000은 모두 올바른 관측입니다. HTTP 다중화와 재사용은 [HTTP 장](../network/tls-http.md)에서 설명합니다.

## upstream 연결 풀

NGINX upstream의 keepalive는 worker가 유지하는 유휴 연결 캐시와 관련되며 열 수 있는 upstream 연결 전체 수의 제한이 아닙니다. `max_conns`도 공유 영역 여부에 따라 범위를 확인해야 합니다. [NGINX Upstream Module](https://nginx.org/en/docs/http/ngx_http_upstream_module.html)

제품에서는 설정값을 표시할 때 `유휴 캐시`, `활성 연결 제한`, `worker별/공유` 범위를 붙이도록 제안합니다. keepalive 32라는 값만 보고 upstream 최대 동시 연결이 32라고 설명하지 않습니다.

## 재시도는 뒤쪽 요청 수를 늘린다

Envoy는 upstream 연결 풀 대기, timeout, retry와 retry 제한 초과 등을 별도 통계로 제공합니다. 이름과 지원 범위는 배포된 Envoy 버전의 API를 확인합니다. [Envoy Cluster Statistics](https://www.envoyproxy.io/docs/envoy/latest/configuration/upstream/cluster_manager/cluster_stats)

합성 예에서 들어온 요청 100개 중 20개가 한 번씩 재시도되면 upstream 시도는 120개입니다. 100+120을 사용자 요청 220개로 보고하면 중복입니다. 재시도 실패와 최종 사용자 실패의 비율도 다릅니다.

## 서비스 메시의 추가 관측

Istio는 서비스·프록시·제어 평면의 지표와 로그·트레이스를 제공합니다. 프록시가 span을 생성하더라도 서비스 사이 context 연결을 위해 애플리케이션의 적절한 전파가 필요합니다. [Istio Observability](https://istio.io/latest/docs/concepts/observability/)

제품은 출발지·목적지 프록시와 앱 계측의 같은 요청을 중복 합산하지 않도록 관측자와 경계를 기록해야 합니다. 두 관측이 다르면 수집 누락, 재시도, 중간 거부, 다른 시간 경계인지 비교합니다.

## 가상 장애 분석

클라이언트가 503을 받았는데 앱 오류 로그가 없다면 요청이 앱에 도달했는지 확인합니다. upstream 대상이 없었거나 연결 풀·정책·시간 제한 단계에서 프록시가 결과를 만들었을 수 있습니다. 반대로 앱이 503을 반환했을 수도 있으므로 응답 코드만으로 생성 주체를 확정하지 않습니다.

관측 필드에는 원래 경로의 템플릿, 선택된 대상, 연결·응답 시간, 시도 번호, 원천 종료 사유와 최종 결과를 두는 설계를 제안합니다. 원문 헤더 전체 수집은 필수 조건이 아닙니다.

## 이해 확인

1. Active connections가 업무 동시 요청 수인가? **유휴 연결 등이 포함될 수 있습니다.**
2. keepalive 값이 전체 upstream 연결 상한인가? **NGINX의 해당 설정은 그런 의미가 아닙니다.**
3. 프록시와 앱이 각각 요청 1건을 세면 사용자 요청 2건인가? **같은 요청의 다른 관측일 수 있습니다.**

관련: [재시도](../application/timeouts-and-retries.md) · [미들웨어 목차](README.md)
