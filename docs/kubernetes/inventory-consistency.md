# Kubernetes 인벤토리의 정확성: 목록, watch와 삭제의 의미

> 상태: 검토됨 · 적용 범위: Kubernetes 1.35 이상과 이전 버전의 규약 구분, API server 1.34.1·etcd 3.6.4, 모든 7개 시나리오에서 watch cache 비활성화 · 검토일: 2026-10-04

## 먼저 이해할 것

인벤토리는 “현재 어떤 대상이 존재하는가”를 정리한 목록입니다. 큰 사진을 여러 조각으로 받아 오는 list와 그 뒤 바뀐 부분을 받는 watch를 결합한다고 생각하면 됩니다. 사진 몇 조각을 받지 못했다는 이유로 그 부분의 대상이 없어졌다고 판단하면 안 됩니다.

이 장의 실험은 실제 kube-apiserver와 etcd를 사용합니다. **7개 시나리오 모두 `--watch-cache=false`인 비기본 구성**이며 410 실험에만 적용한 설정이 아닙니다. cache를 켠 경로의 실행 검증은 이번 기록에 포함되지 않습니다. scheduler·controller-manager·kubelet·CNI·업무 Pod는 실행하지 않습니다. 따라서 **API의 관측·권한·수명 실험**이며 컨테이너 실행이나 클러스터 네트워크 검증은 아닙니다. [envtest 구성의 범위](https://github.com/kubernetes-sigs/controller-runtime/blob/v0.22.3/pkg/envtest/server.go)

## 첫 목록은 언제 완성되는가

Kubernetes list를 `limit`으로 나누면 응답의 `continue` 값을 다음 호출에 전달합니다. 동일한 목록의 페이지는 일관된 snapshot을 이어 받습니다. 처음 조회한 뒤 만들어진 객체는 그 목록의 다음 페이지에 섞이는 대신 이후 목록이나 watch에서 확인합니다. [1.34 API 목록 조회](https://v1-34.docs.kubernetes.io/docs/reference/using-api/api-concepts/#retrieving-large-results-sets-in-chunks)

**실제 실험:** ConfigMap 세 개를 만든 뒤 한 페이지에 하나씩 조회했습니다. 첫 페이지를 받은 직후 `cm-late`를 추가했습니다.

| 확인 | 결과 |
| --- | --- |
| 기존 목록의 세 페이지 | `cm-0`, `cm-1`, `cm-2` |
| 각 페이지 collection resourceVersion | 모두 `202` |
| 새로 시작한 목록 | 네 개 |
| 기존 목록 버전부터 watch | `cm-late`의 `ADDED` 수신 |

`202`는 이번 실행에서 얻은 버전 문자열입니다. 다음 실행에서 같은 숫자를 기대하지 않습니다. 객체별 resourceVersion과 목록 전체의 resourceVersion도 구분합니다.

## 제품에서 현재 목록을 교체하는 시점

다음은 **제품 설계 제안**입니다. 실제 client-go의 내부 구현을 그대로 옮긴 코드는 아닙니다.

```text
동일한 수집 범위의 새 scan 시작
  각 페이지를 임시 목록에 축적
  다음 페이지가 있으면 계속 수신
  timeout/403/이력 만료이면 임시 목록을 완료 처리하지 않음
  모든 페이지 수신 성공 → 현재 목록의 새 기준으로 반영
  기준 버전부터 watch 적용
```

이때 수집 범위에는 클러스터·API group/resource·namespace·label/field selector·권한 문맥을 포함합니다. 이전에는 모든 namespace, 지금은 하나의 namespace만 읽는다면 단순히 같은 전체 목록의 감소로 처리할 수 없습니다.

재동기화 중 화면에 이전 목록을 남긴다면 **과거의 마지막 확인 상태**로 표시합니다. 오래된 캐시를 현재의 확정된 상태라고 표시하는 문제와, 원천 객체를 삭제 처리하는 문제를 각각 다룹니다.

## 이름이 같아도 다른 대상일 수 있다

실험에서 `cm-1`을 삭제한 뒤 같은 이름으로 다시 만들자 UID가 달라졌습니다. Kubernetes의 이름은 자원 범위 안에서 대상을 찾는 값이고 UID는 객체의 생성 수명을 구분합니다. [객체 이름과 UID](https://kubernetes.io/docs/concepts/overview/working-with-objects/names/)

시계열·이벤트·관계를 name에만 연결하면 삭제 전 객체의 상태를 새 객체에 이어 붙일 수 있습니다. 이름 검색은 편리하게 제공하되 이력의 정체성에는 UID와 클러스터 식별을 보존하도록 제안합니다.

## DELETED가 반드시 원천 삭제인 것은 아니다

이번 실험에서 watch는 `suite=domain-book`인 객체만 보도록 설정했습니다. `cm-0`의 label을 `suite=other`로 바꾸자 `DELETED` 이벤트가 왔습니다. 그러나 같은 객체를 직접 GET하면 **HTTP 200**이었고 UID도 같았습니다. 객체가 선택된 집합에서 빠진 것입니다. 실행 경로는 watch cache를 끈 etcd 직접 watch입니다. Kubernetes 1.34.1의 `watchChan.transform()`은 이전 객체만 selector를 만족하면 Deleted를 구성하며, cache 경로의 `cacheWatcher.convertToWatchEvent()`에도 같은 분기가 있습니다. 후자는 코드 대조 결과이며 cache 활성화 상태로 재실행했다는 뜻은 아닙니다. [etcd watcher 코드](https://github.com/kubernetes/kubernetes/blob/v1.34.1/staging/src/k8s.io/apiserver/pkg/storage/etcd3/watcher.go#L617-L634), [cache watcher 코드](https://github.com/kubernetes/kubernetes/blob/v1.34.1/staging/src/k8s.io/apiserver/pkg/storage/cacher/cache_watcher.go#L374-L397)

이는 [실행 코드](../../scripts/run_kubernetes_lab.py)와 [결과 기록](../../labs/results/1.1-kubernetes.json)의 `selector_exit`에 있는 실제 관측입니다. 이 결과를 모든 watch의 DELETED가 단순 label 변경이라는 뜻으로 뒤집어 해석하지 않습니다.

모니터링 제품은 “현재 수집 대상 집합에서 제외됨”과 “원천에서 삭제됨”을 구분할 수 있어야 합니다. 여러 selector의 watch를 합치는 제품은 한 경로의 제외 이벤트로 다른 경로의 대상을 전역 삭제하지 않도록 정책을 정합니다.

## 403, 409, 410은 다른 문제다

| 응답 | 실제 실험 | 수집 측에서의 의미 |
| --- | --- | --- |
| 403 Forbidden | 권한 없는 목록 조회 | 목록이 비었다는 성공 응답이 아님 |
| 409 Conflict | 오래된 resourceVersion을 가진 PUT | 동시 변경 충돌; 최신 상태와 갱신 의도를 재검토 |
| 410 Gone | 보존되지 않은 과거 버전의 Exact list | 현재 기준을 다시 확보해야 함 |

실험에서 reader 역할에는 한 namespace의 ConfigMap get/list/watch만 부여했습니다. 해당 목록은 성공했지만 Secret 목록과 다른 namespace 조회는 계속 403이었습니다. [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)

410 실험은 **전용 etcd만 압축하고 API server watch cache를 꺼서** 과거 버전의 만료를 명확히 재현했습니다. 저장된 증거는 watch cache 비활성화와 physical compaction 완료 요청을 함께 적용한 최종 실행입니다. 이전 원고의 “예비 시도에서 200” 설명은 재검토 가능한 원시 결과가 보존되지 않아 검증 근거에서 제외했습니다. `ListFromCacheSnapshot`이 그 예비 응답의 원인이었다고도 판정하지 않습니다. etcd 압축 직후 모든 API 조회가 반드시 410이 된다고 일반화하지 않습니다. 응답은 요청 조건과 서버가 보유한 이력에 따라 확인합니다.

## resourceVersion: 1.35 이상과 이전 버전의 경계

Kubernetes 1.35 이상에서는 같은 클러스터의 같은 API group·resource type에서 규약을 만족하는 resourceVersion을 순서 비교할 수 있습니다. 검토 시점의 최신 3개 브랜치인 1.35–1.37에 해당하며, 1.37 문서에도 이 규약이 유지됩니다. 첫 글자는 1–9, 나머지는 0–9인 십진수 문자열이어야 하고 임의 정밀도 정수로 비교합니다. 고정 64bit 크기나 벽시계로 해석하지 않습니다. 1.34 이하의 규약을 대상으로 하는 클라이언트와 이 순서 규약을 보장하지 않는 확장 API server는 동일성 비교만 사용합니다. 서버 버전 숫자만 보고 모든 확장 API에 순서 보장이 있다고 추정하지 않습니다. [현재 API 규약](https://kubernetes.io/docs/reference/using-api/api-concepts/#resource-versions), [이전 1.34 규약](https://v1-34.docs.kubernetes.io/docs/reference/using-api/api-concepts/#resource-versions)

순서 비교의 형식 조건은 첫 글자가 `1`~`9`이고 나머지가 `0`~`9`인 문자열입니다. 조건을 만족한다면 임의 정밀도 정수로 비교하거나 **길이를 먼저 비교하고 같은 길이일 때 사전식으로 비교**할 수 있습니다. 예를 들어 `"10"`은 `"9"`보다 큽니다. 길이를 무시한 단순 문자열 비교는 이 순서를 잘못 판단할 수 있습니다. 이 예시의 숫자는 형식 설명용입니다.

조회 매개변수의 `resourceVersion="0"`은 별도의 조회 의미가 있는 값입니다. 위의 객체 버전 순서 비교와 혼동하지 않습니다. 같은 resource type이면 namespace가 다르더라도 규약에 따라 비교할 수 있지만, 다른 클러스터의 값을 연결하는 전역 순서로 사용하지 않습니다.

이 책의 실행 실험은 1.34.1로 고정했습니다. 1.35 이상 비교 규약은 공식 문서 대조이며 1.35–1.37 서버를 실행한 결과가 아닙니다. 1.34 계열은 최신 3개 브랜치에서는 빠졌지만 2026-10-27까지 유지보수 기간이며, 1.34.1 자체가 최신 패치는 아닙니다. [릴리스·종료 일정](https://kubernetes.io/releases/patch-releases/), [고정·최신 버전 표](../coverage.md#교차-검토-시점의-버전-상태)

## watch를 사건의 완전한 기록으로 사용하지 않기

watch 이력은 영구 보존이 아닙니다. BOOKMARK를 요청해도 특정 주기마다 반드시 온다고 기대하지 않으며, 연결 종료와 실제 대상 종료를 구분합니다. 오래된 버전을 잃으면 새 목록을 확보하고 다시 추적합니다. [효율적인 변경 감지](https://v1-34.docs.kubernetes.io/docs/reference/using-api/api-concepts/#efficient-detection-of-changes)

제품이 장기 사건 이력을 제공하려면 관측한 이벤트, 재동기화 구간, 확인하지 못한 구간을 자체 저장해야 합니다. 재목록 조회가 성공해 현재 상태를 복구했다고 그 사이의 모든 중간 변경까지 복원되는 것은 아닙니다.

## 실험 재현

Ubuntu 24.04 amd64에서 다음을 실행합니다. 고정된 공식 release archive의 SHA256을 확인하고 로컬에 추출합니다. kubeconfig를 읽거나 기존 클러스터에 요청하지 않습니다.

```bash
python3 scripts/get_runtime_lab_assets.py --which envtest
python3 scripts/run_kubernetes_lab.py
```

일곱 시나리오가 끝나면 private API server·etcd를 종료하고 임시 인증서·데이터를 제거합니다. 결과는 `.lab-runs/kubernetes.json`입니다.

## 이해 확인

1. 첫 페이지에 없으면 삭제된 객체인가? **다음 페이지 또는 수집 실패 여부부터 확인합니다.**
2. 이름이 같은 새 Pod를 이전 Pod와 같은 실행으로 저장하는가? **UID 등 생성 수명을 구분합니다. 실험은 ConfigMap으로 그 원리를 확인했습니다.**
3. selector watch의 DELETED 하나로 전역 삭제를 확정하는가? **선택 집합 이탈인지 원천 삭제인지 구분해야 합니다.**
4. 1.35 이상의 비교 규칙을 1.34 서버나 규약 미확인 확장 API에도 자동 적용하는가? **규약과 지원 버전을 맞춰야 합니다.**
