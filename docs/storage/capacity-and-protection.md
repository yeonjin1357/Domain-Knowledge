# 저장 용량, 복제, 스냅샷과 복구 가능성

> 상태: 검토됨 · 적용 범위: 공통 용량 모델, Ceph Squid erasure coding·EBS snapshot 사례 · 출처 확인일: 2026-10-03 · 편집 검토일: 2026-10-04 · 2라운드 보강 확인: 2026-10-05 (Ceph Squid min_size·PG 상태)

버전 상태: Ceph 설명은 Squid 문서에 고정했습니다. 공식 표의 Squid 예상 종료일은 2026-10-31이며 검토 시점 최신 계열은 Tentacle 20.2.x입니다. 확정 보증일과 예상 일정을 구분합니다. [버전 상태와 공식 근거](../coverage.md#교차-검토-시점의-버전-상태)

## 먼저 이해할 것

데이터를 여러 사본으로 보관하면 물리 사용량이 늘 수 있고, snapshot은 원본과 블록을 공유할 수 있습니다. 사용자가 보는 논리 크기와 실제 저장 소비량을 따로 계산해야 하는 이유입니다. 보호 기능의 존재와 실제로 원하는 시점으로 복구할 수 있다는 증거도 구분합니다.

논리 데이터 용량, 할당 용량, 물리 사용량, 보호 복제본과 복구 가능성은 서로 다른 축입니다. TB 하나만 표시하면 어떤 값을 합했는지 알 수 없습니다.

## 용량의 여러 의미

제품에서는 다음 값을 분리하도록 제안합니다.

| 값 | 정의할 내용 |
| --- | --- |
| 논리 데이터 | 앱이 저장한 내용의 크기 |
| 프로비저닝 용량 | 볼륨·계정에 제공한 크기 |
| 파일시스템 사용량 | 해당 파일시스템이 사용하는 공간 |
| 백엔드 물리량 | 복제·압축·메타데이터까지 포함하는 실제 점유 |
| 복구용 보존량 | snapshot·backup·버전과 로그의 추가 보존 |

압축·중복 제거·얇은 할당이 있으면 위 값의 관계는 단순 일대일이 아닙니다. 각 저장 시스템의 계상 범위를 확인하고 합산 가능한 계층만 더합니다.

## 복제와 erasure coding

Ceph의 replicated pool은 객체 복사본을 유지하고 erasure-coded pool은 data chunk와 coding chunk를 사용합니다. `k`개 데이터와 `m`개 coding chunk 구성의 저장 비율은 조건에 따라 `(k+m)/k`로 계산할 수 있습니다. 실제 장애 허용은 배치와 failure domain까지 고려해야 합니다. [Ceph Squid Erasure Code](https://docs.ceph.com/en/squid/rados/operations/erasure-code/)

메타데이터·여유·정렬·복구 공간을 제외한 합성 예입니다.

```text
논리 데이터 12 TiB, 3개 복사본 → 36 TiB
논리 데이터 12 TiB, k=6, m=3 → 12 × 9/6 = 18 TiB
```

후자가 이 계산에서 적은 공간을 쓰더라도 지연·복구 비용·작은 쓰기 특성까지 동일한 것은 아닙니다. “chunk 3개 손실 대응”과 “임의의 물리 호스트 3개 장애 대응”도 배치 조건 없이 같은 보장으로 바꾸지 않습니다.

## Ceph의 복제 목표와 I/O 가능 기준

복제본이 목표보다 줄어든 것과 I/O를 못 하는 것은 다릅니다. **Squid 문서, 2026-10-05 확인:** replicated pool의 `size`는 목표 복사본 수, `min_size`는 degraded 상태에서 I/O를 허용할 최소 복사본 수입니다. PG는 객체들을 함께 배치·복구하는 placement group입니다. `undersized`는 목표보다 사본이 적은 상태, `peered`이지만 active가 아닌 경우에는 min_size 부족으로 **읽기를 포함한 client I/O**를 제공하지 못하면서 복구가 진행될 수 있습니다. [pool](https://docs.ceph.com/en/squid/rados/operations/pools/), [PG 상태](https://docs.ceph.com/en/squid/rados/operations/pg-states/)

**예시:** size=3, min_size=2인 replicated pool에서 유효 사본 2개라면 다른 조건이 충족될 때 degraded I/O가 가능하지만, 1개라면 min_size에 미달합니다. “OSD가 한 개 죽었으므로 모든 PG가 inactive”라는 결론도, “사본이 하나 있으므로 읽기는 항상 가능”이라는 결론도 나오지 않습니다. PG별 acting set·peering·다른 상태와 장애 영역을 확인합니다.

Squid 19.2.3의 EC pool 생성 기본 계산은 `min_size = k + min(1, m−1)`입니다. **예시:** k=4, m=2이면 기본 min_size는 `4+min(1,1)=5`입니다. 복원에 필요한 k개 chunk가 남는 것과 client I/O 허용 조건은 다릅니다. 실제 pool에서 명시적으로 바꾼 `min_size`를 우선 읽으며, 이 식을 모든 Ceph 버전·복제 pool에 적용하지 않습니다. [고정 버전 생성 코드](https://github.com/ceph/ceph/blob/v19.2.3/src/mon/OSDMonitor.cc#L7773)

제품 적용 제안은 목표 복제 수·최소 수·PG 상태·가용성 영향을 분리하는 것입니다. `min_size`를 낮추는 변경은 보호 수준을 바꾸므로 자동 복구용 수집 동작에 포함하지 않습니다. Ceph 명령이나 장애 주입은 이번에 실행하지 않았습니다.

## 스냅샷과 백업

EBS snapshot은 증분 방식으로 이전 snapshot 이후 변경된 블록을 보존합니다. 이용자는 복원에 필요한 전체 논리 볼륨을 얻지만 snapshot별 실제 저장량을 볼륨 논리 크기의 단순 합으로 계산하면 안 됩니다. [EBS Snapshots](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-snapshots.html)

실행 중 볼륨의 snapshot은 애플리케이션의 메모리·캐시까지 자동으로 일관된 상태로 만드는 작업이 아닙니다. EBS 문서도 필요한 경우 쓰기를 멈추거나 볼륨 상태를 정리하는 절차를 구분합니다. [Create EBS Snapshots](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-creating-snapshot.html)

제품에서는 snapshot 작업 성공, 데이터 일관성 절차, 별도 장애 영역 보관, 복원 검증을 각각 관측하도록 제안합니다. snapshot이라는 명칭만으로 삭제·계정 장애·지역 장애까지 보호한다고 단정하지 않습니다.

## 복구 작업이 성능과 용량을 사용한다

복제본 복구·재균형 작업과 애플리케이션 I/O가 같은 장치를 사용할 수 있습니다. 이때 보호 상태, 복구 진행률, 사용 가능한 공간과 요청 지연을 함께 보는 모델을 제안합니다. 용량이 가득 차기 직전이면 정상 쓰기뿐 아니라 복구용 임시 여유도 부족할 수 있습니다.

## 용량 예측의 조건

합성 예에서 사용 가능한 여유가 600 GiB이고 매일 순증가가 20 GiB로 유지된다면 단순 선형 예상은 30일입니다. 다음 조건이 바뀌면 예상도 달라집니다.

- 보존 기간 만료로 삭제가 시작되는 시점
- 압축·복제 설정이나 데이터 유형의 변화
- snapshot과 로그의 보존 증가
- 임시 병합·재구축 작업의 공간 요구

예상 30일을 보장 날짜로 표시하지 않고, 관측 구간·증가율·모델과 오차를 표시하는 것이 좋습니다.

## 이해 확인

추가 질문: Ceph에서 size=3 중 두 사본만 남으면 반드시 I/O가 멈추는가? **min_size와 PG의 peering·active 상태 등 조건을 함께 봐야 합니다.**

1. k=4, m=2의 이상화된 보호 공간 비율은? **1.5배입니다.**
2. snapshot 10개가 논리 볼륨 10배의 실제 저장량인가? **증분·중복 구조를 확인해야 합니다.**
3. 저장 성공과 복구 시험 성공은 같은가? **복구 가능성은 별도 검증 대상입니다.**

관련: [DB 복구](../database/replication-and-recovery.md) · [스토리지 목차](README.md)
