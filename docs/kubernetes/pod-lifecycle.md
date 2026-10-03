# Pod 수명, 컨테이너 상태와 건강 검사

> 상태: 본문 초안 · 적용 범위: 일반 Pod와 컨테이너의 상태 해석 · 출처 확인일: 2026-10-03

Pod의 phase, 컨테이너 state, condition, `kubectl`의 표시 문자열은 서로 다른 정보입니다. 모니터링 제품에서 하나의 상태 필드로 합치면 진단에 필요한 근거가 사라집니다.

## 상태의 층

| 층 | 예 | 해석 질문 |
| --- | --- | --- |
| Pod phase | Pending, Running, Succeeded, Failed, Unknown | Pod 수명의 큰 단계는 무엇인가 |
| 컨테이너 state | Waiting, Running, Terminated | 개별 컨테이너는 무엇을 하는가 |
| reason과 종료 기록 | CrashLoopBackOff, 종료 코드, 마지막 상태 | 현재 대기나 종료의 보고 사유는 무엇인가 |
| Pod condition | Ready 등 | 특정 조건이 충족됐는가 |

`Running`은 Pod가 노드에 배치되고 컨테이너 실행이 진행되는 큰 범주이며 모든 요청을 처리할 준비가 됐다는 뜻이 아닙니다. `CrashLoopBackOff`는 Pod phase가 아니라 반복 실패 뒤 재시도 대기를 설명하는 표시입니다. Pod가 대체되면 같은 Pod가 다른 노드로 이동하는 것이 아니라 새 UID의 Pod가 생성됩니다. [Pod Lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)

위 차이에 따라 수집기는 원천의 phase, conditions, containerStatuses를 보존하고 사용자용 요약 상태를 별도 파생값으로 제공하는 방식을 제안합니다.

## 세 가지 probe

readiness는 트래픽을 받을 준비를 확인하고, liveness는 재시작을 통한 복구가 필요한지를 확인합니다. startup probe가 설정되어 있으면 성공하기 전까지 liveness와 readiness의 실행을 늦춰 느린 시작을 처리할 수 있습니다. 반복적인 liveness 또는 startup 실패는 설정된 임계 조건에 따라 컨테이너 재시작으로 이어질 수 있습니다. readiness 실패 자체는 같은 재시작 동작을 뜻하지 않습니다. [Probe 설정](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)

| 가상의 검사 목적 | 사용할 의미 | 관측해야 할 후속 영향 |
| --- | --- | --- |
| 초기 데이터 적재가 끝났는지 | startup | 시작 소요 시간, 실패 후 재시작 |
| 요청 수용 준비가 되었는지 | readiness | 사용 가능한 서비스 대상 변화 |
| 프로세스가 복구 불가능한 정지 상태인지 | liveness | 재시작 전후 상태와 원인 |

모든 probe에서 같은 `/health`를 호출하면 편리할 수 있지만, 그 응답이 각각의 질문에 적합한지는 애플리케이션 설계 문제입니다. 예를 들어 공통 DB 장애에 liveness가 실패하도록 만들면 여러 Pod가 동시에 재시작하면서 복구를 더 어렵게 만들 수 있다는 가설을 검토해야 합니다.

readiness 상태가 바뀌었다고 모든 실제 패킷이 같은 순간에 멈췄다고 가정하지 않습니다. 서비스 설정, 전파 지연, 기존 연결을 별도로 관측합니다.

## 재시작 수가 알려 주지 않는 것

재시작 증가에는 애플리케이션 종료, probe 실패, 자원 문제 등 여러 원인이 있을 수 있습니다. 종료 코드 하나를 모든 런타임과 OS에 대한 원인 분류로 사용하지 않고 보고된 reason, 이벤트, 이전 컨테이너 로그와 노드 상태를 함께 확인합니다.

모니터링의 재시작 차분에는 `(클러스터, Pod UID, 컨테이너 이름)`의 수명이 필요합니다. 새 Pod의 카운터를 이전 Pod에 이어 붙이면 새 배포와 장애 재시작을 혼동할 수 있습니다. 이는 [시계열 초기화](../foundations/time-series.md) 원리의 적용입니다.

## init 컨테이너와 시작 지연

일반 init 컨테이너는 애플리케이션 컨테이너 전에 순서대로 완료됩니다. init 컨테이너가 끝나지 않으면 애플리케이션이 실행될 단계에 도달하지 못할 수 있습니다. 계속 실행되는 sidecar 방식의 init 컨테이너는 별도 수명 규칙이 있으므로 일반 init과 혼동하지 않습니다. [Init Containers](https://kubernetes.io/docs/concepts/workloads/pods/init-containers/)

시작 지연을 조사하는 순서는 다음과 같이 제안합니다.

1. 배치되지 않았다면 스케줄러의 판단 근거를 확인합니다.
2. 배치 뒤 대기한다면 이미지·볼륨·네트워크 준비와 init 상태를 확인합니다.
3. 실행은 됐지만 준비되지 않았다면 probe 결과와 애플리케이션 초기화를 봅니다.
4. 반복 종료라면 마지막 종료 사유와 이전 실행의 로그를 봅니다.

## 가상 사건 재구성

```text
10:00:00  Pod 생성
10:00:02  노드 배치
10:00:05  init 실행 시작
10:00:25  init 완료
10:00:27  애플리케이션 실행
10:00:47  Ready=True
```

전체 준비 시간은 47초입니다. 배치 2초, init 실행 20초, 앱 실행 뒤 준비 20초를 구분할 수 있지만 남은 구간의 원인을 이벤트 없이 임의로 이미지 다운로드라고 지정해서는 안 됩니다. 서로 다른 컴포넌트의 시계로 얻은 시각이라면 [시간 오차](../foundations/time-and-data-quality.md)도 고려합니다.

## 읽기 전용 확인 예시

다음은 `kubectl`과 해당 namespace의 조회 권한이 필요한 예시이며 실제 클러스터에서 실행하지 않았습니다. `POD_NAME`, `NAMESPACE`, `CONTAINER_NAME`을 조사 대상으로 바꿉니다.

```sh
kubectl get pod POD_NAME -n NAMESPACE -o yaml
kubectl describe pod POD_NAME -n NAMESPACE
kubectl logs POD_NAME -n NAMESPACE -c CONTAINER_NAME --previous --tail=100
```

이전 실행 로그의 보존 여부와 접근 권한에 따라 마지막 명령의 결과가 없을 수 있습니다. 로그에 민감한 값이 포함될 수 있으므로 제품 저장 정책에 맞춰 필드를 제한합니다.

## 이해 확인

1. Running이면 Ready인가? **아닙니다. 서로 다른 필드입니다.**
2. readiness 실패는 바로 컨테이너 재시작인가? **readiness 자체의 의미는 준비 상태입니다.**
3. 시작 시간 중 설명되지 않은 3초를 이미지 다운로드로 분류해도 되는가? **해당 단계의 증거가 필요합니다.**

다음: [자원과 스케줄링](resources-and-scheduling.md) · [Kubernetes 목차](README.md)
