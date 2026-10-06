# CNI와 CSI: Pod 연결과 볼륨 준비가 실패하는 위치

> 상태: 검토됨 · 적용 범위: CNI 1.1.0, CSI 1.11.0과 Kubernetes 개념 · 원천 확인일: 2026-10-04 · 실습 여부: 원천·가상 예시 중심; 연결 실습의 범위는 본문

선수 용어: **sandbox**는 Pod의 공유 실행 환경을 관리하는 런타임 경계입니다. [자원 설정·cgroup 계층](../kubernetes/resources-and-scheduling.md#설정이-linux-cgroup으로-이어지는-경로)에서 컨테이너와의 차이를 먼저 확인합니다.

CNI와 CSI는 특정 제품 이름이 아니라 플러그인과 실행 환경 사이의 약속입니다. CNI는 컨테이너 네트워크 설정, CSI는 스토리지 작업의 인터페이스를 다룹니다. “CNI를 쓴다”만으로 패킷이 터널을 지나는지, BGP 경로를 쓰는지, eBPF로 Service를 처리하는지는 알 수 없습니다.

## Pod가 연결되기까지

개념적인 흐름은 Pod가 Node에 배치되고, 런타임이 sandbox를 준비하고, 네트워크 플러그인이 연결을 구성한 뒤 컨테이너가 실행되는 것입니다. 세부 호출 순서와 구현은 런타임·플러그인에 따라 확인합니다. CNI 규약의 핵심 작업에는 `ADD`, `DEL`, `CHECK`가 있고 1.1.0에는 `STATUS`, `GC`도 정의됩니다. 지원 규약 버전과 플러그인 제품 버전은 서로 다른 값입니다. [CNI 규약](https://www.cni.dev/docs/spec/)

IPAM은 주소 할당을 담당합니다. IP 주소를 받지 못하면 앱 코드가 시작되기도 전에 Pod 준비가 멈출 수 있습니다. `ADD` 성공은 네트워크 설정 결과를 의미하며, DB 자격 증명이나 HTTP 업무 성공을 검사한 결과는 아닙니다.

## 네 가지 네트워크 질문

| 질문 | 관측 위치 | 실패 가설 예시 |
| --- | --- | --- |
| Pod 네트워크가 생성되었는가? | 런타임·kubelet 사건, CNI 로그·상태 | 주소 고갈, 플러그인 호출 실패 |
| 같은 Node의 Pod에 도달하는가? | namespace·인터페이스·정책 | 인터페이스·정책 설정 |
| 다른 Node의 Pod에 도달하는가? | 노드 경로·터널·MTU·방화벽 | 노드 간 경로 또는 캡슐화 문제 |
| Service 이름으로 도달하는가? | DNS·Service·EndpointSlice·전달 구현 | 이름 조회, endpoint 선택, 전달 규칙 |

이는 조사 분해안이며 테스트 결과 하나로 원인을 확정하는 표가 아닙니다. Kubernetes 네트워크 모델과 Service 구현을 확인한 뒤 실제 플러그인의 자료를 연결합니다. [클러스터 네트워크](https://kubernetes.io/docs/concepts/cluster-administration/networking/)

가상 예로 Pod IP 직접 접속은 되고 Service DNS 이름만 실패한다면 DNS 응답을 확인합니다. DNS가 올바른 Service IP를 반환한 뒤 연결이 실패한다면 Service 전달·endpoint·정책 경계를 조사합니다. 이 구분 없이 모두 “CNI 장애”로 묶으면 원인을 좁히기 어렵습니다.

## 구현 차이를 수집기에 보존하기

overlay는 원래 패킷을 다른 패킷 안에 넣어 노드 간 전달할 수 있고, 직접 라우팅 방식은 해당 Pod 대역으로 가는 경로를 사용합니다. 프록시·eBPF 등 Service 전달 구현도 별개 선택입니다. 원천에 없는 경로·정책 정보를 추측해서 topology에 확정 관계로 넣지 않습니다.

예를 들어 VXLAN 경로의 유효 MTU는 [링크와 라우팅](../network/layers-and-routing.md)의 헤더 계산과 함께 조사합니다. 작은 ping이 된다고 큰 HTTP 응답까지 문제없다는 결론은 성립하지 않습니다. 실제 경로, 패킷 크기, 단편화 관련 동작을 확인합니다.

## CSI의 준비 단계

CSI는 Identity, Controller, Node 서비스와 capability를 정의합니다. 모든 드라이버가 모든 호출 단계를 지원·요구하는 것은 아닙니다. 특히 controller publish와 staging의 필요 여부는 드라이버 capability에 따라 다룹니다. [CSI 1.11.0 규약](https://github.com/container-storage-interface/spec/blob/v1.11.0/spec.md)

| 단계 | 입문용 의미 | 대표 관측 |
| --- | --- | --- |
| CreateVolume | 사용할 저장 자원을 만듦 | provisioning 요청·결과·용량·시간 |
| ControllerPublishVolume | 대상 Node에서 사용 가능하도록 연결 준비 | attachment 처리 상태·오류 |
| NodeStageVolume | Node의 준비 위치에 볼륨을 준비 | staging 작업·파일시스템 관련 실패 |
| NodePublishVolume | 워크로드가 사용할 대상 경로로 제공 | publish 작업·mount 관련 실패 |
| 실제 앱 I/O | 앱이 파일을 읽고 씀 | 파일 접근 오류·지연·용량·inode |

표는 지원되는 경우의 개념적인 단계입니다. 한 단계가 성공해도 다음 단계의 성공을 보장하지 않습니다. PVC `Bound`는 바인딩 상태이며 앱의 파일 권한이나 I/O 지연을 검증하지 않습니다. [영구 볼륨](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)

## 조사 예시와 제품 적용 제안

가상 사례에서 PVC는 Bound, Pod는 시작하지 못하고 `FailedMount` 사건이 보인다고 합시다. PVC를 새로 만드는 조치부터 시작하지 않고, Pod UID·Node·PVC/PV·드라이버·volume handle을 연결합니다. capability에 맞는 호출 단계의 오류와 스토리지 접근 상태를 확인합니다.

한 Node에서만 실패하면 그 Node의 플러그인·경로·권한 가설을, 여러 Node에서 같은 volume에 실패하면 공유 저장 자원 가설을 먼저 비교할 수 있습니다. 이는 범위를 좁히는 추론이지 확정된 원인 판정은 아닙니다.

제품에서는 Pod 준비 시간을 “스케줄링 전”, “네트워크·sandbox 준비”, “볼륨 준비”, “이미지·컨테이너 시작”, “readiness”의 관측 가능한 경계로 표시합니다. 사건이 없거나 시각이 충분하지 않으면 시간을 억지로 분배하지 않고 미확인 구간으로 남깁니다.

## 이해 확인

1. CNI 1.1.0이면 모든 plugin의 기능이 같은가? **규약 버전과 구현·지원 기능은 다릅니다.**
2. 모든 CSI 드라이버가 staging 단계를 수행하는가? **capability에 따라 다릅니다.**
3. PVC Bound면 mount도 성공했는가? **바인딩과 Node의 실제 준비 단계는 구분합니다.**

이전: [워크로드 종류와 제어 평면의 가용성](workloads-and-control-plane.md) · 다음: [API 변경, CRD와 Operator를 관측하는 방법](operators-and-api-lifecycle.md) · [분야 목차](README.md)
