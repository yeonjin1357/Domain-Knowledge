# Kubernetes 수집 경로와 데이터의 의미

> 상태: 본문 초안 · 적용 범위: API 객체, kube-state-metrics, Resource Metrics API, 컴포넌트 지표 · 출처 확인일: 2026-10-03

Kubernetes 수집은 하나의 API를 읽는 작업으로 끝나지 않습니다. 상태, 자원 사용, 컴포넌트 처리 성능, 애플리케이션 동작은 각각 다른 관측 경로가 있습니다.

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

예를 들어 한 도구는 15초 평균 CPU를, 다른 도구는 5분 평균을 보여 주면 같은 시각에 값이 다를 수 있습니다. 서로 다른 계산 구간을 맞추지 않고 수집기 오류라고 판단하지 않습니다. 메모리는 [호스트 메모리](../host/memory.md), [cgroup](../containers/resource-control.md)의 관측 범위와 함께 비교합니다.

## list와 watch로 현재 상태 유지하기

API는 객체 목록 조회와 변경 watch를 지원합니다. 오래된 `resourceVersion`의 변경 이력이 더 이상 없으면 `410 Gone`이 반환될 수 있고, 클라이언트는 목록을 새로 가져와 watch를 다시 시작하는 복구가 필요합니다. `resourceVersion`은 일반 클라이언트가 숫자 순서를 임의로 비교하는 대상이 아닙니다. [Kubernetes API Concepts](https://kubernetes.io/docs/reference/using-api/api-concepts/)

다음은 제품 수집기의 설계 예입니다.

```text
초기 목록 조회 → 캐시 구축 → 반환된 버전에서 watch
  연결 단절 → 재연결과 변경 연속성 확인
  이력 만료 → 재목록 조회 → 캐시 재동기화
```

재목록 조회에 실패한 상태에서 이전 캐시의 모든 객체를 삭제 처리하지 않습니다. 목록을 다 받기 전에는 아직 관측하지 않은 객체와 삭제된 객체를 구분할 수 없기 때문입니다. 페이지를 나눠 받은 경우에도 수집 범위의 완료 여부가 필요합니다.

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

다음: [네트워크와 저장소 연결](network-and-storage.md) · [Kubernetes 목차](README.md)
