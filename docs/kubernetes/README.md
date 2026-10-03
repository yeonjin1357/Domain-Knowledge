# 쿠버네티스 도메인

> 상태: 초안 · 적용 범위: Kubernetes 공통 개념 · 출처 확인일: 2026-10-03

쿠버네티스 영역에서는 클러스터의 구성, 워크로드 실행 상태, 자원 사용 및 변경 이력을 연결합니다. 원하는 상태가 실제로 실현되고 있는지, 문제가 어느 계층에서 시작됐는지 이해하는 것이 목적입니다.

## 기본 구성

클러스터는 제어 평면과 노드로 구성됩니다. API 서버는 Kubernetes API를 제공하고, 스케줄러는 아직 노드가 정해지지 않은 Pod의 배치를 결정합니다. 컨트롤러는 리소스의 상태를 조정하며, 노드의 kubelet과 컨테이너 런타임은 Pod와 컨테이너 실행을 담당합니다. [Kubernetes Components](https://kubernetes.io/docs/concepts/overview/components/)

| 관측 계층 | 정리할 대상 | 답하려는 질문 |
| --- | --- | --- |
| 클러스터 | 제어 평면과 전체 용량 | 클러스터의 관리 기능이 동작하는가? |
| 노드 | 상태, 자원, 배치된 워크로드 | 특정 노드에 문제가 집중되는가? |
| 워크로드 | Deployment·StatefulSet·DaemonSet·Job 등 | 의도한 수와 상태로 실행되는가? |
| Pod와 컨테이너 | 생명주기, 재시작, 종료 이유, 사용량 | 실행·준비·종료 과정 중 어디에 문제가 있는가? |
| 통신과 저장 | Service, 통신 경로, 볼륨 | 외부 의존 자원에 접근할 수 있는가? |

표는 문서 범위와 관측 설계를 위한 제안입니다. 리소스 종류별 상세 동작은 별도 문서에서 다룹니다.

## 상태를 해석할 때의 주의점

Pod의 `Running` 단계는 모든 요청이 정상 처리되고 있다는 보장이 아닙니다. 단계, 컨테이너 상태, 준비 상태와 실제 요청 결과를 구분해서 읽어야 합니다. Pod는 고유 UID를 가지며, 교체된 Pod는 같은 이름을 사용하더라도 이전 Pod와 다른 대상입니다. [Kubernetes Pod Lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)

## 장애 분석 예시

| 증상 | 조사할 자료 | 다음 분석 방향 |
| --- | --- | --- |
| Pod가 실행 준비를 마치지 못함 | Pod 상태·이유·이벤트, 배치 여부 | 배치 조건, 이미지 준비, 볼륨과 설정 확인 |
| 컨테이너 재시작 증가 | 종료 이유·종료 코드, 이전 실행 로그, 같은 시각의 자원 상태 | 애플리케이션 종료와 자원 문제의 가설 검증 |
| 특정 노드의 여러 워크로드가 느림 | 노드 자원과 조건, 배치 목록, 통신 상태 | 호스트·네트워크 분석으로 연결 |
| 배포 이후 요청 실패 증가 | 변경 시각, 대상 버전, 준비 상태, 요청 오류 | 배포 영향과 외부 의존성 문제 비교 |

이는 조사 가설의 예시입니다. 재시작 횟수나 상태 하나만으로 원인을 확정하지 않습니다.

## 제품 적용 제안

클러스터·네임스페이스·워크로드·Pod·컨테이너 사이를 이동하면서 같은 시간대의 상태와 지표를 확인할 수 있게 합니다. 이름과 UID를 함께 관리하고, 종료된 대상도 과거 사건 분석에서 찾을 수 있도록 수명 정보를 검토합니다.

API에서 얻는 리소스 상태, 런타임에서 얻는 사용량, 애플리케이션이 보고하는 요청 결과는 수집 원천을 표시합니다. 관리형 클러스터의 접근 가능한 범위는 공급자와 권한별로 확인합니다.

## 상세 본문

1. [객체와 제어 루프](objects-and-control-loops.md): desired·observed 상태, UID, owner, 삭제
2. [Pod 수명과 건강 검사](pod-lifecycle.md): phase·reason·condition, probe, 재시작
3. [자원·배치·확장](resources-and-scheduling.md): requests·limits, 스케줄링, HPA, eviction
4. [수집 경로](collection.md): API·kube-state-metrics·Resource Metrics의 차이
5. [네트워크와 저장소](network-and-storage.md): Service·EndpointSlice·NetworkPolicy·PV/PVC
6. [워크로드와 제어 평면](workloads-and-control-plane.md): StatefulSet·DaemonSet·Job·CronJob, etcd

버전별 feature gate, CNI·CSI별 세부 구현과 operator별 제어 로직은 실제 기술을 정해 추가 검증할 범위입니다.

관련 문서: [호스트](../host/README.md), [애플리케이션](../application/README.md), [도메인 간 분석](../cross-domain/README.md)
