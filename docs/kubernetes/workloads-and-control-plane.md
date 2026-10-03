# 워크로드 종류와 제어 평면의 가용성

> 상태: 본문 초안 · 범위: Kubernetes workload controllers, etcd 3.6 문서 · 공식 자료 확인: 2026-10-03

Pod가 몇 개 실행 중인지 세는 것만으로 워크로드의 건강을 판단할 수 없습니다. 계속 실행되어야 하는 서버와 한 번 완료되어야 하는 배치의 성공 조건이 다르기 때문입니다. 또한 기존 Pod가 요청을 처리하는 능력과 새로운 Pod를 생성·배치하는 제어 평면의 능력을 구분해야 합니다.

## 컨트롤러별 원하는 결과

| 종류 | 원하는 결과 | 모니터링 질문 |
| --- | --- | --- |
| Deployment | 교체 가능한 복제본과 배포 상태 관리 | 원하는 버전이 충분히 Available한가? |
| StatefulSet | 순서 있는 이름·식별과 저장 문맥을 가진 Pod 관리 | 각 ordinal과 볼륨, 업데이트 상태가 맞는가? |
| DaemonSet | 대상 Node마다 필요한 Pod 배치 | 실행 대상 Node 중 빠진 곳이 있는가? |
| Job | 지정한 작업의 완료 | 성공한 작업과 실패·재시도·미완료가 무엇인가? |
| CronJob | 일정에 따라 Job 생성 | 예정 시각, 실제 생성·시작·성공 시각이 맞는가? |

Deployment는 [객체와 제어 루프](objects-and-control-loops.md)에서 설명합니다. 다른 컨트롤러도 동일한 Pod 개수 지표로 정상 조건을 고정하면 의미를 잃습니다.

## StatefulSet의 안정적인 이름과 실제 실행 수명

StatefulSet은 Pod마다 ordinal 기반 식별과 안정적인 네트워크·저장 문맥을 제공합니다. 기본 `OrderedReady`와 `Parallel` 관리 정책은 생성·종료의 순서 보장에 차이가 있습니다. PVC 보존·삭제는 관련 정책과 버전을 확인해야 합니다. [StatefulSets](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)

안정적인 `db-0` 이름이 프로세스의 무중단 실행이나 DB 데이터 복제의 정확성을 보장하지는 않습니다. 교체된 Pod는 새 실행 수명으로 관측하고, `db-0`이라는 논리 슬롯과 실행 UID를 둘 다 남깁니다. DB의 primary 선출·데이터 동기화는 사용하는 DB 또는 operator의 동작을 확인해야 합니다.

예를 들어 `db-0`이 Pending이면 앞 순서 Pod의 readiness, PVC의 바인딩·마운트, 배치 조건을 조사합니다. `db-0`이 Ready이어도 follower 복제 지연은 DB 자료로 확인해야 합니다.

## DaemonSet의 분모

DaemonSet은 모든 Node 또는 선택한 Node에서 Pod가 실행되도록 관리합니다. Node 선택 조건에 따라 대상 집합이 달라지고, 컨트롤러는 일부 Node 상태에 대한 toleration을 자동 추가합니다. [DaemonSet](https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/)

클러스터 Node 20개 중 이 DaemonSet이 대상으로 삼는 Node가 12개이며 Ready가 11개라는 가상 예시에서는 대상 대비 Ready 비율이 `11 / 12 ≈ 91.67%`입니다. 전체 20을 분모로 사용한 55%는 다른 질문의 답입니다. 자동으로 추가된 toleration이 있다는 사실과 모든 Node에서 반드시 정상 실행된다는 보장도 구분합니다.

## Job은 실행 시도와 업무 완료를 나누어 센다

Job은 Pod 실패 시 다시 실행할 수 있습니다. `parallelism=1`, `completions=1`, `restartPolicy=Never`라도 같은 프로그램이 두 번 시작되는 경우가 가능하다고 공식 문서는 설명합니다. 따라서 업무의 중복 실행 대응은 별도 설계 대상입니다. [Jobs](https://kubernetes.io/docs/concepts/workloads/controllers/job/)

수집에서는 Job UID, Pod별 시도, 성공·실패 조건, 완료 시각과 실패 이유를 연결합니다. 업무 처리 건수는 애플리케이션이 보고한 자료로 보완합니다. Pod가 성공 종료했다는 정보만으로 송금·파일 전달 같은 외부 업무가 한 번만 완료되었다고 증명할 수 없습니다.

## CronJob의 일정과 실행

CronJob은 예정된 시각마다 Job 생성을 시도하지만 두 Job이 생기거나 생성되지 않는 경우를 완전히 막지는 않습니다. 일정, time zone, 시작 기한, 동시 실행 정책과 suspend를 함께 확인해야 합니다. [CronJob](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/)

아래는 설명용 시간표입니다.

```text
예정 = 02:00:00
Job 생성 = 02:00:08
Pod 작업 시작 = 02:00:38
성공 완료 = 02:04:38

예정 대비 생성 지연 = 8초
생성부터 시작까지 = 30초
작업 실행 = 240초
예정부터 완료까지 = 278초
```

작업 실행 시간 240초만 표시하면 스케줄·배치 지연 38초를 숨깁니다. 매일 성공해야 하는 백업이라면 현재 Running Pod가 0이라는 이유로 장애로 만들지 않고, 예정 회차의 성공과 결과물 검증 상태를 관측합니다.

## etcd와 제어 평면

etcd의 상태 변경 합의에는 voting member의 과반수가 필요합니다. 3개 voting member에서는 2개, 5개에서는 3개가 필요합니다. 서버 프로세스 개수에 learner까지 단순히 더한 값으로 quorum을 계산하지 않습니다. [etcd 3.6 FAQ](https://etcd.io/docs/v3.6/faq/)

```text
고정된 voting member N의 quorum = floor(N / 2) + 1
3개 구성: 최대 1개 장애에서도 나머지 2개가 통신하면 과반수
5개 구성: 최대 2개 장애에서도 나머지 3개가 통신하면 과반수
```

이는 변경 없는 구성에서의 단순 장애 수 계산입니다. 살아 있는 멤버 간 네트워크 단절이나 디스크 지연을 무시한 가용성 보장이 아닙니다. etcd의 합의 지연에는 멤버 간 네트워크와 영속 기록의 지연이 영향을 줍니다. 문서에 실린 과거 벤치마크 수치를 모든 클러스터의 처리량으로 적용하지 않습니다. [etcd performance](https://etcd.io/docs/v3.6/op-guide/performance/)

모니터링에서는 API 요청의 오류·지연, 제어 루프의 진척, 스케줄 대기, etcd leader·quorum 상태와 디스크·네트워크 증거를 연결하는 방식을 사용합니다. 클라우드 관리형 제어 평면에서 노출되지 않는 항목은 미지원으로 표시하고 임의로 0을 채우지 않습니다.

## 이해 확인

1. `db-0` 이름이 같으면 이전 CPU Counter와 이어도 되는가? **실행 UID·시작 수명은 바뀔 수 있다.**
2. CronJob의 실행 시간이 짧으면 일정도 지켰는가? **예정·생성·시작·완료 시각을 따로 비교해야 한다.**
3. etcd 3대 중 2대가 켜져 있으면 항상 상태 변경이 가능한가? **서로 통신하며 합의를 수행할 수 있는 등 추가 조건이 필요하다.**

관련: [Pod 수명](pod-lifecycle.md), [수집 경로](collection.md), [DB 복제](../database/replication-and-recovery.md)
