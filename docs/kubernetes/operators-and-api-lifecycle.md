# API 변경, CRD와 Operator를 관측하는 방법

> 상태: 검토됨 · 적용 범위: Kubernetes 공식 API·CRD·admission·Operator 문서 · 원천 확인일: 2026-10-04 · 실습 여부: 원천·가상 예시 중심; 연결 실습의 범위는 본문

Kubernetes의 제어 루프는 “원하는 상태를 저장하고, 현재 상태를 그쪽으로 바꾸는 작업”입니다. Operator는 이 패턴으로 특정 애플리케이션의 운영 지식을 코드에 담습니다. DB Operator가 있다는 사실만으로 백업·복제·장애 전환이 모두 성공했다는 뜻은 아닙니다. 원하는 상태와 실제 작업 결과를 각각 봐야 합니다. [Operator 패턴](https://kubernetes.io/docs/concepts/extend-kubernetes/operator/)

## CRD, 객체, controller의 역할

CRD는 새로운 API 종류와 schema 등을 등록하고, custom resource는 그 종류로 생성한 개별 객체입니다. Controller는 객체를 관측하고 필요한 조치를 수행하는 프로그램입니다. CRD만 등록했다고 실제 복제 서버를 생성하는 로직까지 생기지는 않습니다. [CustomResourceDefinition](https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/)

가상 `DatabaseCluster` 객체에서 `spec.replicas=3`은 희망 수일 수 있습니다. 어떤 구현이 `status.readyReplicas=2`를 제공한다면 그 필드의 정의에 따라 준비 상태를 해석합니다. 이 이름은 설명용이며 모든 Operator에 공통으로 있는 Kubernetes 표준 필드라고 수집기에 고정하지 않습니다.

## 요청을 저장하기 전에도 실패할 수 있다

API 요청은 인증·인가·admission 등의 경계를 거칩니다. Mutating admission은 허용된 범위에서 객체를 바꿀 수 있고, validating admission은 객체 허용 여부를 판단합니다. Admission webhook의 지연·실패는 객체 생성과 변경의 가용성에 영향을 줄 수 있습니다. `failurePolicy`에 따른 동작도 함께 확인해야 합니다. [Admission webhook](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/)

가상 예로 Deployment 생성 요청이 admission에서 거절되었다면 Pod가 Pending인 문제와 다릅니다. 아직 생성되지 않은 객체의 Pod 지표를 찾는 대신 API 응답 코드·거절 이유·해당 admission 경계를 조사합니다. API 처리의 성공과 이후 controller의 수렴 성공도 구분합니다.

## generation과 resourceVersion

`resourceVersion`의 동일성·순서 비교는 서버 버전과 API 규약에 맞춥니다. 1.34 이하의 불투명 문자열 규약과 1.35 이상의 제한된 순서 비교 규약을 구분하며, 순서 규약이 확인되지 않은 확장 API server에는 동일성 비교만 사용합니다. resourceVersion을 여러 종류 자원의 전역 시각으로 계산하지 않습니다. [버전별 비교](objects-and-control-loops.md)

`generation`과 controller가 제공하는 `observedGeneration`의 관계는 해당 API 규약을 확인합니다. 원하는 변경을 아직 관측하지 않은 상태와 관측했지만 실패한 상태를 구분하는 단서가 될 수 있습니다. [Kubernetes API 규약](https://github.com/kubernetes/community/blob/master/contributors/devel/sig-architecture/api-conventions.md)

Conditions의 `True`, `False`, `Unknown`, reason, message, lastTransitionTime을 원형대로 보존합니다. `lastTransitionTime`을 마지막 수집 시각으로 덮으면 실제 상태 전환 시점을 잃습니다. 모든 custom resource가 동일한 Conditions 규약을 충실히 구현한다고 가정하지 않습니다.

## API 버전 변경과 변환

CRD는 여러 served version과 저장 버전을 다룰 수 있으며, 버전 사이에 conversion이 필요할 수 있습니다. 같은 객체를 API 버전별로 읽었다고 서로 다른 실제 자원 두 개로 생성하지 않도록 UID와 scope를 유지합니다. 필드 이름 변경은 metric 명세 버전과 parser 테스트에 반영합니다. [CRD 버전 관리](https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definition-versioning/)

수집 시작 때 discovery 결과로 group/version/resource와 namespaced 여부를 확인합니다. 객체 목록 수집 권한, status 가시성, watch 가능 여부를 각각 capability로 기록합니다. 403은 “자원이 0개”와 다르고, 사라진 API 버전은 “모든 객체가 삭제됨”과 다릅니다.

## finalizer와 삭제 지연

finalizer가 남은 객체는 삭제 요청 뒤에도 정리 절차를 기다릴 수 있습니다. 그때 삭제 의도와 실제 리소스 제거 완료는 다른 상태입니다. [Finalizers](https://kubernetes.io/docs/concepts/overview/working-with-objects/finalizers/)

제품은 `deletionTimestamp`, finalizer 종류, controller 관측·실패 기록을 연결합니다. “오래 남았다”는 사실만으로 finalizer 제거를 자동 실행하지 않습니다. 외부 볼륨·DNS·계정 같은 정리 대상이 있는지 확인할 근거를 제공합니다.

## 제품 적용 제안과 이해 확인

API 상태, controller의 reconcile 성공·실패·재시도, 실제 업무 상태를 구분한 화면을 제안합니다. reconcile 횟수는 사용자의 업무 요청 횟수가 아니며 같은 desired state를 여러 번 처리할 수 있습니다. Operator마다 metric 이름과 semantics가 다르므로 공통 모델로 변환한 근거를 남깁니다.

1. CRD 설치만으로 DB 장애 전환이 동작하는가? **실제 controller와 그 설정·상태가 필요합니다.**
2. API 생성 성공이 workload 준비 완료인가? **비동기 수렴이 남아 있습니다.**
3. resourceVersion을 정수로 빼서 객체 나이를 계산하는가? **순서 비교를 지원하는 버전에서도 값의 차이가 시간 단위는 아닙니다.**

관련: [객체와 제어 루프](objects-and-control-loops.md) · [수집](collection.md)

이전: [CNI와 CSI: Pod 연결과 볼륨 준비가 실패하는 위치](cni-csi-and-data-paths.md) · 다음: [애플리케이션 도메인](../application/README.md) · [분야 목차](README.md)
