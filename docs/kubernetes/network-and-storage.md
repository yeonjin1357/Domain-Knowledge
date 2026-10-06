# Kubernetes 네트워크와 저장소의 연결 관계

> 상태: 검토됨 · 적용 범위: Service·EndpointSlice·NetworkPolicy·PV/PVC 공통 원리 · 원천 확인일: 2026-10-03 · 실습 여부: 원천·가상 예시 중심; 연결 실습의 범위는 본문

## 먼저 이해할 것

Service는 바뀌는 Pod 집합에 접근하는 방법을 제공하고, 볼륨 자원은 데이터 제공과 수명을 관리합니다. 논리 주소가 존재한다는 것과 실제 endpoint가 준비된 것은 다릅니다. 저장 요청이 연결되었다는 상태도 앱이 파일을 성공적으로 썼다는 뜻은 아닙니다. 제품은 실행 객체에서 실제 트래픽 경로와 저장소 연결까지 추적할 수 있어야 합니다.

## Service와 실제 대상

Service는 접근 대상의 집합을 추상화합니다. selector가 있는 일반 Service에서는 해당 Pod 집합과 EndpointSlice가 연결되고, selector가 없는 Service는 외부 대상 등을 별도로 연결할 수 있습니다. 따라서 모든 Service가 반드시 Pod를 선택한다고 가정하면 안 됩니다. [Service](https://kubernetes.io/docs/concepts/services-networking/service/)

다음은 조사에 사용할 관계의 예입니다.

```mermaid
flowchart LR
    C[클라이언트] --> S[Service 주소와 포트]
    S --> E[EndpointSlice의 대상]
    E --> P[Pod 주소와 포트]
    P --> A[컨테이너의 리스너]
```

이 그림은 논리 관계입니다. 패킷이 반드시 독립된 Service 프로세스를 통과한다는 의미가 아닙니다. 실제 전달 방식은 클러스터 네트워크 구현을 확인해야 합니다.

가상 장애로 Service는 존재하지만 연결이 안 된다면 selector의 일치 여부, EndpointSlice 대상과 준비 상태, 포트 매핑, 컨테이너의 실제 리스너를 차례로 비교합니다. 이름 해석 성공만으로 이 모든 단계가 정상이라고 결론 낼 수 없습니다.

## NetworkPolicy의 판단 단위

NetworkPolicy는 이를 구현하는 네트워크 플러그인이 필요합니다. 표준 정책의 허용 규칙은 적용되는 방향별로 합집합이며, 송신측 egress와 수신측 ingress가 모두 허용해야 하는 상황을 구분해야 합니다. 정책 객체를 만들었다는 사실과 실제 네트워크 구현이 적용했다는 사실을 분리해 관측합니다. [Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)

제품에는 정책 목록뿐 아니라 선택되는 Pod·namespace, 방향, 프로토콜과 포트, 실제 관측 경로를 연결하는 것을 제안합니다. 실제 CNI 구현의 확장 정책이나 L7 정책은 표준 NetworkPolicy와 별도의 규칙으로 표시합니다.

## 저장소를 표현하는 객체

PersistentVolume(PV)은 저장 자원을, PersistentVolumeClaim(PVC)은 그 자원에 대한 요청을 나타냅니다. 바인딩은 요청과 자원의 연결이고 컨테이너 내부 마운트 완료나 업무의 읽기 성공까지 의미하지는 않습니다. 접근 모드 `ReadWriteOnce`는 한 노드에서의 읽기·쓰기를 뜻하며 같은 노드의 여러 Pod 사용과 구별해야 합니다. `ReadWriteOncePod`는 한 Pod에 대한 제약이며 지원 범위를 확인해야 합니다. [Persistent Volumes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)

관계 모델의 예는 다음과 같습니다.

```text
Pod volume 참조 → PVC → PV → CSI driver / 공급자 볼륨
Pod 배치 노드 → 연결·마운트 작업 → 컨테이너 경로
```

이 관계에서 PVC 요청 용량, PV 용량, 파일시스템 사용량, 백엔드의 물리 사용량은 서로 다른 값입니다. 얇은 할당, 스냅샷, 복제와 파일시스템 메타데이터까지 고려하면 하나의 숫자로 대체할 수 없습니다.

## 장애를 단계별로 구분한다

| 가상 증상 | 확인할 단계 | 비교할 근거 |
| --- | --- | --- |
| PVC가 Pending | 프로비저닝·바인딩 | StorageClass, 요구 조건, 관련 이벤트 |
| Pod가 볼륨을 기다림 | 연결·마운트 | 노드, 드라이버, 볼륨의 현재 연결 |
| 파일 생성이 실패 | 파일시스템·권한·용량 | bytes와 inode 여유, 마운트 옵션, 오류 |
| 읽기·쓰기가 느림 | 앱→파일시스템→저장 장치 | I/O 크기, 대기, 경로와 백엔드 성능 |

표는 조사 순서이며 특정 오류 메시지를 모든 드라이버의 공통 원인으로 정한 분류표가 아닙니다. [호스트 I/O](../host/disk-io.md)와 [스토리지](../storage/README.md)를 함께 읽습니다.

## 제품의 연결 정보 설계

관계에는 원천, 확인 시각과 유효 기간을 보관하도록 제안합니다. Service 대상이 바뀌거나 Pod가 대체될 때 과거 요청을 현재 대상에 잘못 붙이지 않기 위해서입니다. 이름만 같은 새 PVC나 Pod와 이전 장애를 연결할 때도 UID와 시점을 사용합니다.

## 이해 확인

1. Service에는 항상 selector가 있는가? **selector 없는 Service도 있습니다.**
2. ReadWriteOnce는 정확히 한 Pod만 쓴다는 뜻인가? **한 노드 기준이며 ReadWriteOncePod와 다릅니다.**
3. PVC Bound면 앱의 파일 쓰기가 성공하는가? **마운트, 권한, 파일시스템과 실제 I/O를 더 확인해야 합니다.**

관련: [네트워크](../network/README.md) · [스토리지](../storage/README.md) · [Kubernetes 목차](README.md)

이전: [Kubernetes 인벤토리의 정확성: 목록, watch와 삭제의 의미](inventory-consistency.md) · 다음: [워크로드 종류와 제어 평면의 가용성](workloads-and-control-plane.md) · [분야 목차](README.md)
