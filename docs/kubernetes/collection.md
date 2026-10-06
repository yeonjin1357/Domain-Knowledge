# Kubernetes 수집 경로와 데이터의 의미

> 상태: 검토됨 · 적용 범위: API 객체, kube-state-metrics, Resource Metrics API, 컴포넌트 지표 · 원천 확인일: 2026-10-05 · 실습 여부: 원천·가상 예시 중심; 연결 실습의 범위는 본문

## 먼저 이해할 것

Kubernetes의 객체 상태는 API에서, 실제 자원 사용량은 다른 계측 경로에서 얻을 수 있습니다. 같은 Pod를 설명해도 어느 원천을 읽었는지에 따라 업데이트 시점과 필드 의미가 다릅니다. 목록과 watch는 대상 발견·변경을 다루며, 모든 과거 사건의 완전한 기록을 보장하는 저장소로 사용하지 않습니다. 제품은 객체 상태·자원 사용·컴포넌트 성능·업무 계측의 수집 경로를 분리합니다.

## 수집 경로 비교

| 경로 | 얻으려는 정보 | 이것만으로 알 수 없는 정보 |
| --- | --- | --- |
| Kubernetes API | 객체 설정·상태·관계 | 요청의 실제 사용자 지연 |
| kube-state-metrics | API 객체 상태의 지표 표현 | 컨테이너 CPU 실행량 자체 |
| Resource Metrics API | CPU와 메모리 사용 측정 | 모든 성능·오류 지표와 장기 이력 |
| 컴포넌트 metrics | API server 등 자체 처리 상태 | 업무 성공 여부 |
| 로그·트레이스·애플리케이션 지표 | 코드와 요청의 실행 증거 | 독립적인 전체 인벤토리 |

kube-state-metrics는 API 객체 상태를 지표로 제공하며 `kubectl`이 적용하는 표시용 해석과 결과가 다를 수 있습니다. 객체가 삭제되면 현재 노출 지표에서도 사라집니다. 이 때문에 과거 인벤토리 이력을 보존하려면 수집 측의 저장 모델이 필요합니다. [kube-state-metrics README](https://github.com/kubernetes/kube-state-metrics/blob/main/README.md)

## CPU와 메모리의 측정 범위

Resource Metrics API에서 CPU는 누적 CPU 카운터로부터 계산한 구간 평균 CPU 사용량이며 측정 window를 확인해야 합니다. 메모리는 관측 시점의 working set으로 제공되고 OS별 추정 방식에 차이가 있습니다. working set은 단순히 애플리케이션 heap이나 완전히 회수 불가능한 메모리와 같지 않습니다. metrics-server는 kubelet에서 지표를 가져와 이 API 경로로 제공합니다. [Resource metrics pipeline](https://kubernetes.io/docs/tasks/debug/debug-cluster/resource-metrics-pipeline/)

예를 들어 한 도구는 15초 평균 CPU를, 다른 도구는 5분 평균을 보여 주면 같은 시각에 값이 다를 수 있습니다. 서로 다른 계산 구간을 맞추지 않고 수집기 오류라고 판단하지 않습니다. 메모리는 [working set의 계산과 범위](../containers/memory-accounting-and-oom.md)의 관측 범위와 함께 비교합니다.

## kubelet의 통계 endpoint

| kubelet 경로 | 관측 목적 | 호환성 경계 |
| --- | --- | --- |
| `/stats/summary` | node·Pod·container 자원 통계 JSON | runtime/CRI 통계와 cAdvisor 경로, OS에 따라 제공 범위 확인 |
| `/metrics/resource` | CPU·메모리 등 resource metrics용 제한된 지표 | 전체 cAdvisor 지표의 별칭 아님; metrics-server 0.6+의 사용 경로 |
| `/metrics/cadvisor` | cAdvisor의 자세한 컨테이너 지표 | 지표 수명·label·OS·runtime 범위 별도 확인 |
| `/metrics/probes` | kubelet probe 관련 지표 | 자원 사용량 endpoint와 구분 |

Prometheus endpoint 구분은 [System Metrics](https://kubernetes.io/docs/concepts/cluster-administration/system-metrics/), Summary API와 metrics-server 경로는 [Node Metrics Data](https://kubernetes.io/docs/reference/instrumentation/node-metrics/)를 따릅니다. PSI는 `KubeletPSI`가 1.34 Beta 기본 활성, **1.36 GA**이며 Linux PSI·cgroup v2 전제가 필요합니다. Summary API와 `/metrics/cadvisor`에 노출되며 Windows에는 제공되지 않습니다. 1.36에서는 OS가 지원하지 않을 때 거짓 0 대신 생략하도록 개선됐습니다. endpoint 존재만으로 PSI 지원을 인정하지 않습니다. [PSI GA 설명](https://kubernetes.io/blog/2026/05/12/kubernetes-v1-36-psi-metrics-ga/)

**kubelet**은 노드의 Pod 실행을 관리합니다. **cAdvisor**는 컨테이너 자원 통계의 한 제공 경로이고, **Summary API**는 kubelet이 묶어 내는 node·Pod·container 통계 JSON입니다. metrics-server 0.6+의 경로는 다음처럼 분리합니다. [Node Metrics Data](https://kubernetes.io/docs/reference/instrumentation/node-metrics/)

```text
kubelet(cAdvisor 또는 지원되는 CRI 통계)
  ├─ /stats/summary → Summary JSON 소비자
  ├─ /metrics/resource → metrics-server(0.6+) → Resource Metrics API
  └─ /metrics/cadvisor → 세부 컨테이너 지표 소비자
```

이 그림은 모든 endpoint의 필드가 같다는 뜻이 아닙니다. metrics-server는 자동 확장용 집계 경로이며 장기 모니터링 저장소가 아닙니다.

## list와 watch로 현재 상태 유지하기

초기 목록을 완성한 뒤 해당 버전에서 변경 watch를 이어 갑니다. 권한 거부·페이지 누락·재동기화 실패를 전체 삭제로 해석하지 않습니다. resourceVersion 비교, 완료 표식, HTTP 410의 복구 규칙은 [인벤토리 정본](inventory-consistency.md)에 모았습니다. [API 규약](https://kubernetes.io/docs/reference/using-api/api-concepts/)

streaming list는 초기 상태를 watch 이벤트로 받는 방법입니다. 완료 기준과 일반 BOOKMARK의 차이는 [초기 동기화 규칙](inventory-consistency.md#streaming-list와-초기-동기화-완료)을 따릅니다.

## 수집기 권한과 범위

제품은 어떤 클러스터·namespace·리소스 종류를 수집하도록 설정했는지 명시해야 합니다. 권한이 없는 namespace에서 객체가 보이지 않는 것을 “대상 없음”으로 해석하면 안 됩니다. 수집 결과에 `성공`, `권한 거부`, `연결 실패`, `지원 안 함`, `부분 결과`를 구분하는 상태 모델을 제안합니다.

로그나 Secret 본문 등 내용 데이터의 수집은 인벤토리 메타데이터 수집과 별도로 설정합니다. 이 지식서의 예시는 모니터링 구현에 필요한 범위의 관측 설계이며 관리자 권한 일괄 부여를 전제로 하지 않습니다.

## 지표도 버전에 따라 변한다

컴포넌트 지표에는 안정성 단계와 폐기·숨김·삭제 수명이 있습니다. Alpha 지표에 stable 지표와 같은 호환성 보장을 적용하면 안 됩니다. 지표 이름, 유형과 label의 호환성은 해당 단계와 버전의 정책을 확인해야 합니다. [Kubernetes System Metrics](https://kubernetes.io/docs/concepts/cluster-administration/system-metrics/)

수집기 호환성 표에는 다음을 넣도록 제안합니다.

- Kubernetes·수집 도구·런타임 버전
- endpoint와 필요한 권한
- 필수·선택 지표, 각 단위와 유형
- 누락 시 지원 안 함인지 일시 실패인지 판정하는 근거
- 원천 label을 제품 대상 ID로 연결하는 규칙

## 가상 데이터 불일치 조사

Pod가 API에는 있고 자원 지표에는 없다면 생성 직후 아직 측정되지 않았는지, kubelet 접근이 실패했는지, 이미 종료됐는지, 해당 실행의 지표 지원이 없는지 확인합니다. 빈 값을 CPU 0으로 채우면 이런 차이가 모두 사라집니다.

반대로 과거 시계열에만 Pod가 보이면 그 시계열은 과거 관측이고 API는 현재 상태일 수 있습니다. 조회 시각의 객체 관계를 복원하는 문제는 [대상 모델](../product/README.md)로 이어집니다.

## 이해 확인

1. kube-state-metrics가 모든 CPU 사용량을 측정하는가? **주 목적은 API 객체 상태의 지표화입니다.**
2. watch가 끊기면 모든 객체가 삭제된 것인가? **수집 연결의 실패와 대상의 삭제는 다릅니다.**
3. working set이 앱 heap인가? **관측 범위와 계산 방식이 다릅니다.**
4. streaming list의 초기 ADDED는 모두 방금 생성된 객체인가? **현재 상태를 전달하는 합성 이벤트이며 초기 동기화 완료도 확인해야 합니다.**
5. Summary API와 모든 cAdvisor 지표가 같은 목록인가? **[kubelet 경로별 범위와 PSI 지원](#kubelet의-통계-endpoint)을 확인합니다.**

이전: [Kubernetes 자원 압박과 종료 원인](pressure-and-termination.md) · 다음: [Kubernetes 인벤토리의 정확성: 목록, watch와 삭제의 의미](inventory-consistency.md) · [분야 목차](README.md)
