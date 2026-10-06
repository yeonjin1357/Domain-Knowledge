# Kubernetes 인벤토리의 정확성: 목록, watch와 삭제의 의미

> 상태: 검토됨 · 적용 범위: Kubernetes 1.35 이상과 이전 규약, 1.34.1·1.37.0 API server의 cache true/false 실습 · 원천 확인일: 2026-10-06 · 실습 여부: 저장된 로컬 실행 근거 포함; 구성·한계는 본문

## 먼저 이해할 것

**envtest**는 API server·etcd를 로컬 실행해 API 동작을 시험하는 환경입니다. 실제 workload가 실행되는 완전한 클러스터와 관측 범위가 다릅니다.

인벤토리는 “현재 어떤 대상이 존재하는가”를 정리한 목록입니다. 큰 사진을 여러 조각으로 받아 오는 list와 그 뒤 바뀐 부분을 받는 watch를 결합한다고 생각하면 됩니다. 사진 몇 조각을 받지 못했다는 이유로 그 부분의 대상이 없어졌다고 판단하면 안 됩니다.

이 장의 실험은 실제 kube-apiserver와 etcd를 사용합니다. **기존 1.1 기록의 7개 시나리오는 모두 `--watch-cache=false`**이며, 2026-10-05 실행에서는 cache true/false를 별도로 비교했습니다. scheduler·controller-manager·kubelet·CNI·업무 Pod는 실행하지 않습니다. 따라서 API 관측·권한·수명 실험이며 컨테이너 실행이나 클러스터 네트워크 검증은 아닙니다. [envtest 구성 범위](https://github.com/kubernetes-sigs/controller-runtime/blob/v0.22.3/pkg/envtest/server.go)

**실행 조건(2026-10-05):** 공식 envtest의 1.34.1·etcd 3.6.4와 1.37.0·etcd 3.7.0을 각각 cache true/false로 실행했습니다. 실행 버전은 각 minor의 최신 patch가 아닙니다(검토 시 최신 1.34.12·1.37.1). 아래 기존 실험과 새 비교 결과를 구분하며, 다른 patch·확장 API의 동작까지 보장하지 않습니다. [출판 결과](../../labs/results/1.1-r2-kubernetes.json), [전용 manifest](../../labs/review-r2/kubernetes-assets.json), [공식 patch 일정](https://kubernetes.io/releases/patch-releases/)

## 첫 목록은 언제 완성되는가

Kubernetes list를 `limit`으로 나누면 응답의 `continue` 값을 다음 호출에 전달합니다. 동일한 목록의 페이지는 일관된 snapshot을 이어 받습니다. 처음 조회한 뒤 만들어진 객체는 그 목록의 다음 페이지에 섞이는 대신 이후 목록이나 watch에서 확인합니다. [1.34 API 목록 조회](https://v1-34.docs.kubernetes.io/docs/reference/using-api/api-concepts/#retrieving-large-results-sets-in-chunks)

**기존 1.34.1 실험:** ConfigMap 세 개를 만든 뒤 한 페이지에 하나씩 조회했습니다. 첫 페이지를 받은 직후 `cm-late`를 추가했습니다.

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

이번 실험에서 watch는 `suite=domain-book`인 객체만 보도록 설정했습니다. `cm-0`의 label을 `suite=other`로 바꾸자 `DELETED` 이벤트가 왔습니다. 그러나 같은 객체를 직접 GET하면 **HTTP 200**이었고 UID도 같았습니다. 객체가 선택된 집합에서 빠진 것입니다. 실행 경로는 watch cache를 끈 etcd 직접 watch입니다. Kubernetes 1.34.1의 `watchChan.transform()`은 이전 객체만 selector를 만족하면 Deleted를 구성하며, cache 경로의 `cacheWatcher.convertToWatchEvent()`에도 같은 분기가 있습니다. cache 활성화 구성의 실제 결과는 아래 비교 표에 있습니다. [etcd watcher 코드](https://github.com/kubernetes/kubernetes/blob/v1.34.1/staging/src/k8s.io/apiserver/pkg/storage/etcd3/watcher.go#L617-L634), [cache watcher 코드](https://github.com/kubernetes/kubernetes/blob/v1.34.1/staging/src/k8s.io/apiserver/pkg/storage/cacher/cache_watcher.go#L374-L397)

이는 [실행 코드](../../scripts/run_kubernetes_lab.py)와 [결과 기록](../../labs/results/1.1-kubernetes.json)의 `selector_exit`에 있는 실제 관측입니다. 이 결과를 모든 watch의 DELETED가 단순 label 변경이라는 뜻으로 뒤집어 해석하지 않습니다.

모니터링 제품은 “현재 수집 대상 집합에서 제외됨”과 “원천에서 삭제됨”을 구분할 수 있어야 합니다. 여러 selector의 watch를 합치는 제품은 한 경로의 제외 이벤트로 다른 경로의 대상을 전역 삭제하지 않도록 정책을 정합니다.

## 403, 409, 410은 다른 문제다

| 응답 | 실제 실험 | 수집 측에서의 의미 |
| --- | --- | --- |
| 403 Forbidden | 권한 없는 목록 조회 | 목록이 비었다는 성공 응답이 아님 |
| 409 Conflict | 오래된 resourceVersion을 가진 PUT | 동시 변경 충돌; 최신 상태와 갱신 의도를 재검토 |
| HTTP 410(reason `Expired`) | cache-off에서 보존되지 않은 Exact list; cache-on은 아래 조건에서 200 | 요청 의미를 확인하고 현재 기준을 다시 확보 |

실험에서 reader 역할에는 한 namespace의 ConfigMap get/list/watch만 부여했습니다. 해당 목록은 성공했지만 Secret 목록과 다른 namespace 조회는 계속 403이었습니다. [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)

Exact 조회의 결과는 요청 버전과 cache 구성에 따라 다릅니다. 아래 표는 etcd compaction 뒤 같은 요청을 비교한 저장 증거이며, 시간 기반 token 만료 실험과 구분합니다.

## watch cache가 있는 경우와 없는 경우

| API server·cache | etcd compaction 뒤 Exact RV=1 LIST | 기존 첫 continue token 재사용 | selector 이탈 |
| --- | --- | --- | --- |
| 1.34.1·true | 200, 목록 RV=`1`, 빈 items | 200 | DELETED 뒤 같은 UID GET 200 |
| 1.34.1·false | HTTP 410(reason `Expired`) | HTTP 410(reason `Expired`) | DELETED 뒤 같은 UID GET 200 |
| 1.37.0·true | 200, 목록 RV=`1`, 빈 items | 200 | DELETED 뒤 같은 UID GET 200 |
| 1.37.0·false | HTTP 410(reason `Expired`) | HTTP 410(reason `Expired`) | DELETED 뒤 같은 UID GET 200 |

**1.34.1과 1.37.0의 이 실행에서는 watch cache를 켜면 etcd compaction 뒤 Exact RV=1 LIST가 HTTP 200·resourceVersion="1"·빈 items로 반환됐고, cache를 끄면 410이었습니다.** 따라서 “etcd compaction만 하면 이 요청이 반드시 410”이라는 가설은 cache-on 두 조건에서 반증됐습니다. 원시 verdict `refuted`는 이 가설의 반증이며 API 규약 위반 판정이 아닙니다. 네 조건 모두 fresh LIST는 성공했고, pagination은 최초 snapshot의 세 객체만 반환한 뒤 새 LIST에 `cm-late`가 나타났습니다. [원시 요청·응답](../../labs/results/1.1-r2-kubernetes.json)

**제품 적용 제안:** 과거 RV의 Exact 조회가 HTTP 200·빈 목록을 반환해도 현재 전체 대상을 삭제하지 않습니다. 요청한 snapshot과 수집 범위, 현재 목록 동기화의 완료 여부를 먼저 확인합니다.

네 서버 모두 `kubernetes_feature_enabled{name="ListFromCacheSnapshot",stage="BETA"} 1`을 기록했고 명시적 gate override는 없었습니다. **gate 활성 상태는 관측했지만 인과는 분리하지 않았습니다.** cache를 켠 채 해당 gate만 바꾸는 대조군이 없으므로 특정 기능이 이 200의 단독 원인이라고 확정하지 않습니다. continue 결과도 이 실행의 compaction 뒤 관측이며 token의 시간 만료를 기다린 실험은 아닙니다.

RV=1의 빈 목록은 새 etcd의 빈 저장소와 양립하는 결과로 해석합니다. 실행기는 조건마다 새 data directory를 사용하고 API 시작 뒤 namespace·ConfigMap을 생성합니다. etcd 3.6.4·3.7.0의 새 MVCC store는 revision 1에서 시작합니다. 다만 당시 RV=1 저장소를 별도로 덤프하거나 namespace 생성 응답을 결과에 보존하지 않아 **namespace 부재까지 독립 실측한 근거는 아닙니다**. 이 설명은 실행기와 초기화 코드에 근거한 추론입니다. [실행 순서](../../scripts/run_kubernetes_r2_lab.py), [etcd 3.6.4 초기화](https://github.com/etcd-io/etcd/blob/v3.6.4/server/storage/mvcc/kvstore.go#L103), [3.7.0 초기화](https://github.com/etcd-io/etcd/blob/v3.7.0/server/storage/mvcc/kvstore.go#L104)

## resourceVersion: 1.35 이상과 이전 버전의 경계

순서 비교의 기준은 **응답한 API server의 버전·종류와 그 서버가 보장하는 규약**입니다. kubectl·클라이언트 라이브러리의 버전만으로 결정하지 않습니다.

Kubernetes 1.35 이상에서는 같은 클러스터의 같은 API group·resource type에서 규약을 만족하는 resourceVersion을 순서 비교할 수 있습니다. 검토 시점의 최신 3개 브랜치인 1.35–1.37에 해당하며, 1.37 문서에도 이 규약이 유지됩니다. 첫 글자는 1–9, 나머지는 0–9인 십진수 문자열이어야 하고 임의 정밀도 정수로 비교합니다. 고정 64bit 크기나 벽시계로 해석하지 않습니다. 1.34 이하의 규약을 대상으로 하는 클라이언트와 이 순서 규약을 보장하지 않는 확장 API server는 동일성 비교만 사용합니다. 서버 버전 숫자만 보고 모든 확장 API에 순서 보장이 있다고 추정하지 않습니다. [현재 API 규약](https://kubernetes.io/docs/reference/using-api/api-concepts/#resource-versions), [이전 1.34 규약](https://v1-34.docs.kubernetes.io/docs/reference/using-api/api-concepts/#resource-versions)

순서 비교의 형식 조건은 첫 글자가 `1`~`9`이고 나머지가 `0`~`9`인 문자열입니다. 조건을 만족한다면 임의 정밀도 정수로 비교하거나 **길이를 먼저 비교하고 같은 길이일 때 사전식으로 비교**할 수 있습니다. 예를 들어 `"10"`은 `"9"`보다 큽니다. 길이를 무시한 단순 문자열 비교는 이 순서를 잘못 판단할 수 있습니다. 이 예시의 숫자는 형식 설명용입니다.

조회 매개변수의 `resourceVersion="0"`은 별도의 조회 의미가 있는 값입니다. 위의 객체 버전 순서 비교와 혼동하지 않습니다. 같은 resource type이면 namespace가 다르더라도 규약에 따라 비교할 수 있지만, 다른 클러스터의 값을 연결하는 전역 순서로 사용하지 않습니다.

2026-10-05 실행에서 같은 ConfigMap 생성·두 번 수정에서 1.37.0은 cache true에서 `218→219→220`, false에서 `217→218→219`를 반환했습니다. 같은 cluster·core API·resource type의 좁은 범위에서 증가 순서를 관측한 것이며 규약 전체의 증명이 아닙니다. 1.34.1도 숫자가 증가했지만 그 관측을 이전 규약의 순서 비교 보장으로 바꾸지 않습니다. 1.34 계열은 최신 3개 브랜치 밖이지만 2026-10-27까지 유지보수 기간이며 1.34.1 자체는 최신 패치가 아닙니다. [실행 근거](../../labs/results/1.1-r2-kubernetes.json), [일정](https://kubernetes.io/releases/patch-releases/), [버전 표](../coverage.md#교차-검토-시점의-버전-상태)

### LIST 조회 옵션을 읽는 표

| 요청 | 의미 | 현재 상태 동기화에서의 주의 |
| --- | --- | --- |
| RV 미지정 | Most Recent 규약의 목록 | 반환 collection RV부터 변경 추적 |
| `resourceVersion="0"` | Any: 사용 가능한 버전의 목록 | 더 오래된 상태를 받을 수 있음 |
| 양의 RV + match 미지정, limit 미지정 | NotOlderThan: 지정 버전보다 오래되지 않은 목록 | 아래 Exact와 다름 |
| 양의 RV + match 미지정, 양수 limit, continue 미지정 | Exact: 첫 페이지는 지정 RV의 snapshot | 후속 페이지는 반환 continue token 사용 |
| 양의 RV + `resourceVersionMatch=Exact` | 지정한 버전의 정확한 snapshot | 과거 상태를 현재 전체 목록으로 대체하지 않음 |
| 양의 RV + `resourceVersionMatch=NotOlderThan` | 지정 버전보다 오래되지 않은 snapshot | 반드시 그 RV와 같다는 뜻 아님 |

이는 첫 LIST 요청의 요약이며 GET·watch의 옵션 의미를 그대로 대입하지 않습니다. 후속 페이지의 continue token에 양의 RV를 함께 지정하는 조합은 유효하지 않습니다. RV와 match 조합의 유효성도 원천 규약을 따릅니다. [GET/LIST semantics](https://kubernetes.io/docs/reference/using-api/api-concepts/#semantics-for-get-and-list)

## streaming list와 초기 동기화 완료

기존 list → watch 외에 watch 요청에 `sendInitialEvents=true`를 넣는 streaming list가 있습니다. `resourceVersionMatch=NotOlderThan`이 필요하며 `allowWatchBookmarks=true`로 초기 상태의 끝을 나타내는 bookmark를 요청합니다. 초기 객체들은 합성 `ADDED`로 오므로 이들을 “방금 생성된 객체”로 기록하지 않습니다. 완료 bookmark 전 단절되면 완전한 초기 목록을 확보한 것으로 처리하지 않습니다. [API streaming lists](https://kubernetes.io/docs/reference/using-api/api-concepts/#streaming-lists)

`WatchList` 서버 gate는 1.32 Beta 기본 true, 1.33 기본 false, **1.34 이후 Beta 기본 true**로 변경됐습니다. client-go의 `WatchListClient` 기본값은 1.35부터 true입니다. 서버 지원과 client의 사용 여부는 별개이며, 실제 설정을 보존해야 합니다. 큰 LIST 응답의 JSON/Protobuf streaming encoding과 `sendInitialEvents` 프로토콜도 다른 기능입니다. [feature gate 이력](https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/), [v1.37.0 client 기본값](https://github.com/kubernetes/kubernetes/blob/v1.37.0/staging/src/k8s.io/client-go/features/known_features.go)

pagination의 continue token도 무기한 재사용할 수 없습니다. HTTP 410(reason `Expired`) 뒤 동일 snapshot이 필요하면 처음부터 다시 목록을 얻습니다. 응답의 새 continue token으로 이어 가면 최신 snapshot을 사용하므로 앞 페이지와 일관성이 깨집니다. [ListOptions.continue 주석](https://github.com/kubernetes/apimachinery/blob/v0.37.0/pkg/apis/meta/v1/types.go#L426)이 이 차이를 명시합니다. API 개요는 watch history와 continue token 만료에 기본 5분을 설명합니다. **제품 적용 제안:** 이 설명을 모든 cache·서버 설정에서 두 보존 기간이 같다는 보장으로 확대하지 말고 요청 종류별 만료 응답과 재동기화 절차를 관리합니다. [API pagination](https://kubernetes.io/docs/reference/using-api/api-concepts/#retrieving-large-results-sets-in-chunks)

### 초기 목록과 일반 watch의 완료 표식

| 방법 | 초기 동기화 완료 기준 | 주의 |
| --- | --- | --- |
| 페이지 LIST | 모든 페이지 수신 성공, `metadata.continue`가 비어 있음 | 도중 실패는 미완료 |
| streaming list | `k8s.io/initial-events-end: "true"` annotation의 BOOKMARK 수신 | 완료 표식 전에 끊기면 미완료 |
| 초기 동기화 뒤 일반 watch | 개별 변경·진행 BOOKMARK | 주기적 BOOKMARK 도착을 보장하지 않음 |

완료 표식을 요청한다는 사실과 이미 받았다는 사실을 구분합니다. annotation 이름과 초기 완료 BOOKMARK의 규칙은 [apimachinery v0.37.0 ListOptions](https://github.com/kubernetes/apimachinery/blob/v0.37.0/pkg/apis/meta/v1/types.go#L448)와 [initial-events-end 상수](https://github.com/kubernetes/apimachinery/blob/v0.37.0/pkg/apis/meta/v1/types.go#L508)를 따릅니다. [Streaming lists](https://kubernetes.io/docs/reference/using-api/api-concepts/#streaming-lists)

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

고정 자산 검증·새 출력 경로·재현 명령은 [공통 재현 절차](../cross-domain/reproducible-labs.md)에 있습니다. 옛 실행기와 결과를 덮어쓰지 않습니다.

## 이해 확인

1. 첫 페이지에 없으면 삭제된 객체인가? **다음 페이지 또는 수집 실패 여부부터 확인합니다.**
2. 이름이 같은 새 Pod를 이전 Pod와 같은 실행으로 저장하는가? **UID 등 생성 수명을 구분합니다. 실험은 ConfigMap으로 그 원리를 확인했습니다.**
3. selector watch의 DELETED 하나로 전역 삭제를 확정하는가? **선택 집합 이탈인지 원천 삭제인지 구분해야 합니다.**
4. 1.35 이상의 비교 규칙을 1.34 서버나 규약 미확인 확장 API에도 자동 적용하는가? **규약과 지원 버전을 맞춰야 합니다.**

이전: [Kubernetes 수집 경로와 데이터의 의미](collection.md) · 다음: [Kubernetes 네트워크와 저장소의 연결 관계](network-and-storage.md) · [분야 목차](README.md)
