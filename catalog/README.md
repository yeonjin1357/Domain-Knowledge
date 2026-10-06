# 수집 필드 카탈로그와 실행 가능한 계약

수집 계약 참조, 기준 원고 제1.2판, 확인일 2026-10-06. **제품 구현이 아니라 원천 필드의 의미와 수용 경계를 실행 가능한 형태로 표현한 참조**입니다. 책의 [어댑터 계약](../docs/product/adapter-contracts.md)과 [수용 기준](../docs/product/compatibility-and-acceptance.md)에 연결되어 있습니다.

## 파일과 시작 명령

| 파일 | 역할 |
| --- | --- |
| [field-catalog.json](field-catalog.json) | 사람이 검토하는 기준 데이터. 안정적인 자체 ID를 가진 87개 필드 |
| [field-catalog.schema.json](field-catalog.schema.json) | JSON Schema 2020-12의 제한된 키워드로 표현한 구조·허용값 |
| [verify_field_catalog.py](../scripts/verify_field_catalog.py) | 표준 라이브러리 검증기: 구조, 의미 조합, 링크·hash, 본문 연결, 잘못된 입력 거부 |
| [adapter-r4.json](../labs/fixtures/adapter-r4.json) | 작은 추출 fixture와 합성 사례, 출처·추출 규칙·hash·기대 결과 |
| [build_adapter_fixtures.py](../scripts/build_adapter_fixtures.py) | 원시 증거에서 deterministic fixture 생성 또는 `--check` 비교 |
| [adapter_contract.py](../scripts/adapter_contract.py) | 기존 `transform()`과 새 경계별 참조 함수 |
| [verify_adapter_fixtures.py](../scripts/verify_adapter_fixtures.py) | 고정 입력 재생. 기존 `verify_contracts.py`에서도 호출 |
| [4라운드 기록](../review/claude-codex-r4.md) | 설계 판단, 4b 수정 후보, 검사 결과 |

저장소 루트에서 실행합니다. 모두 표준 라이브러리만 사용하며 DB·cloud·커널을 조회하지 않습니다. 관리자 권한이나 패키지 설치가 필요하지 않고, 저장된 자료를 읽는 CPU·메모리 비용만 발생합니다.

```powershell
python -X utf8 -B scripts/verify_field_catalog.py
python -X utf8 -B scripts/build_adapter_fixtures.py --check
python -X utf8 -B scripts/verify_adapter_fixtures.py
python -X utf8 -B scripts/verify_contracts.py
```

의도적으로 추출 규칙을 바꾸고 검토한 경우에만 `python -X utf8 -B scripts/build_adapter_fixtures.py`로 **fixture 파일**을 갱신합니다. 이 명령은 `labs/results/`를 수정하지 않습니다. `--check`는 쓰지 않습니다. 카탈로그 JSON은 직접 편집하며 임시 작성 도구에 의존하지 않습니다.

## 범위와 모델

| 영역 | 필드 수 | 포함한 원천 |
| --- | ---: | --- |
| Linux | 29 | stat·PID stat, meminfo, diskstats, vmstat, PSI, snmp/netstat |
| cgroup v2 | 10 | cpu.stat, memory.current/max/events/stat |
| Kubernetes | 9 | Summary CPU·메모리, 적용 자원·종료·재시작, UID·resourceVersion |
| PostgreSQL | 20 | DB·table·activity·replication·slot·I/O·checkpointer·statement 통계 |
| MySQL | 8 | SHOW REPLICA STATUS, 잠금·복제·digest Performance Schema |
| OTLP | 6 | 부분 거절, Collector 실패 계수, metric 시작 시각·Sum·Histogram |
| CloudWatch | 5 | 결과별 상태, 요청 token, 시간-값, 기간 Sum 계약 예시 |

전수 exporter 목록이 아닙니다. Azure는 NULL/0의 합성 계약만 있고 필드 카탈로그 대상에는 포함하지 않았습니다. SNMP wrap도 합성 사례만 있습니다. 상용 DB·GPU 신규 실측, 실제 cloud 호출, 전체 버전 조합, 네트워크 listener·인증 구현·저장소·전체 histogram 엔진은 제외합니다.

각 필드는 다음을 따릅니다.

- `source`: 인터페이스, 위치, 열/필드, 관측 범위. SQL locator는 **원천 식별용 projection**이며 identity 열·필터·조회 비용까지 갖춘 운영 SQL이 아닙니다. 이 SQL을 이번 라운드에 실행하지 않았습니다.
- `kind`와 `temporality`: counter/gauge/histogram과 누적/구간/순간을 다른 축으로 저장합니다. UID·상태·시각에는 별도 종류를 사용합니다. `dynamic`은 CloudWatch 반환 값처럼 조회 정의 없이는 종류를 결정할 수 없다는 뜻이며, 그대로 rate를 계산할 수 없습니다.
- `unit`와 `normalization`: 원천·정규화 단위를 구분합니다. `proc_kB`는 해당 procfs의 1024 byte 단위, `sector512`는 512 byte sector입니다. 페이지는 page로 보존하며 byte 환산 때 실제 페이지 크기가 추가로 필요합니다. `runtime_parameter`는 설명용 식별자이며 `eval`할 코드가 아닙니다.
- `value_type`: 성공적으로 읽은 값의 의미상 자료형입니다. SQL NULL·JSON 누락·접근 실패는 이 숫자형에 넣지 않고 `missing`의 별도 상태로 처리합니다. MySQL XML의 숫자 문자열과 `xsi:nil`을 구분하는 참조를 제공합니다.
- `identity`와 `reset`: 대상·수명·정의 문맥을 보존합니다. `wrap_bits=null`은 wrap이 없다는 뜻이 아니라 폭을 고정하지 않았다는 뜻입니다. 재시작을 모든 통계의 reset과 동일시하지 않습니다.
- `availability`: `min_inclusive/max_exclusive`는 **이 계약의 검토 범위**입니다. `introduced_in/removed_in`은 확인한 원천 필드 도입·제거, `stable_since`는 기능 안정화 시점입니다. 예를 들어 PG 범위 끝 19는 19에서 삭제됐다는 뜻이 아닙니다. 실제 column·extension·backport·feature gate 확인이 버전 숫자보다 우선합니다.
- `permissions`: 필요한 읽기 범위·비용·상태 변경 여부. 자동 권한 부여나 운영 환경에서의 실행 승인을 의미하지 않습니다.
- `references`와 `evidence`: 본문·1차 원천 링크, 저장 증거 경로·SHA256·선택 위치·입증 범위. 증거가 비어 있으면 실측으로 검증했다고 표시하지 않습니다. `format_and_value_only`는 파일 읽기 표본이며 OOM·회수·한도 강제 실험이 아닙니다.
- `record_basis=scoped_example`: CloudWatch의 기간 요청 수 Sum처럼 특정 원천 정의를 전제로 한 예시입니다. 모든 `Values` 배열에 동일한 종류를 적용하지 않습니다.

PostgreSQL I/O는 `pg.io.reads`(16–17의 고정 크기 블록 수)와 `pg.io.read_requests`(18의 요청 수)를 별도 정의로 보존합니다. 업그레이드 때 `definition_changed`로 차분을 끊는 가상 사례를 제공합니다. OTLP의 거절 0 기본값·경고·int64 JSON 표현과 Collector의 기본 `_total` 이름도 명시한 입력으로 검사합니다. 이 추가 사례들은 새 live 실측이 아닙니다.

필드 ID는 이 저장소의 참조 ID이며 exporter의 공식 이름이 아닙니다. 자동 discovery나 지원 매트릭스의 허용 목록으로 바로 사용하지 않습니다.

## 검증이 확인하는 것

구조 검사기는 제공한 JSON Schema에 사용된 키워드만 지원하고, 모르는 키워드가 추가되면 실패합니다. 범용 JSON Schema 구현이라고 부르지 않습니다. 종류/temporality, 단위 환산, 수명/버전 경계를 추가 검사합니다. 필수값 누락·오타·잘못된 조합·경로 이탈·hash 변경 등 **16개 거부 사례**도 실행합니다.

**38개 본문 연결**은 특정 필드 값·버전·환산 수와 본문의 문구를 함께 검사합니다. 모든 문장의 뜻을 자동으로 검증하지 않으며, 문구가 바뀌면 사람이 같은 의미인지 확인하고 연결을 갱신해야 합니다. 상세 장 전체의 내용 hash 검사는 기존 `check_docs.py`가 맡습니다.

로컬 파일과 Markdown anchor, 증거 hash와 JSON pointer는 실제로 확인합니다. 외부 URL은 기본 검증에서 HTTPS·공식 호스트·형식을 검사하고 네트워크 요청을 하지 않습니다. [별도 접근 기록](../review/field-catalog-source-links.json)에는 초기 39개 주소의 실제 HTTP 조회 결과와 추가 원천의 개별 조회 기록을 보존했습니다. 초기 Python 직접 조회는 32개 200·MySQL 7개 403이었고, 후자는 웹 도구로 공식 페이지 내용을 별도로 열었습니다. 추가 기록은 각 행의 확인 시각과 status를 따릅니다. 403을 200으로 바꾸지 않았습니다. HTTP 성공이나 본문 앞부분 hash는 사실성 인증 또는 완전한 원천 보존이 아닙니다.

## fixture의 입증 범위

**74개**는 실측 입력 29개, 합성 입력 44개, 실측+제한된 실습 문맥 1개입니다. 기존 `transform()`의 22개와 합치면 96개 어댑터 사례이며, 기존 본문 산술 28개는 별도입니다. 저장 증거 21개 파일을 참조하며, MySQL XML 8개와 promtool debug 2개·PSI 1개는 gzip을 풀어 사용합니다.

`sources`에는 원본 경로·byte 길이·SHA256이 있습니다. gzip에는 압축/비압축 hash와 원래 artifact manifest를 함께 연결합니다. 각 사례의 `bindings`는 JSON pointer 또는 metric 원문 행 선택 규칙이고 `extracted_sha256`은 추출 값의 정규 JSON hash입니다. JSON hash는 UTF-8, 키 정렬, compact separators, NaN 불허로 계산합니다. `parameters`는 관측된 값이 아니라 명시한 정책/문맥이며, `expected`는 참조 함수의 출력으로 자동 생성하지 않습니다.

중복 전송 실험의 옛 원시 결과에는 span ID만 있습니다. 해당 실습이 고정 단일 trace라는 제한을 더한 1개를 `mixed`로 표시했습니다. 일반 제품의 중복 키는 인증된 tenant·trace ID·span ID 등을 사용해야 하며, span ID 단독 전역 중복 제거를 입증하지 않습니다.

다음 제한을 그대로 유지합니다.

- diskstats·SNMP 형식과 wrap은 합성 입력입니다. 실제 wrap을 관측하지 않았습니다. 같은 수명과 최대 증가량이 modulus 미만이라는 별도 증거가 없으면 값 증가·감소 모두 wrap 횟수를 확정하지 않습니다.
- PG 실측 NULL은 `backend_xmin`입니다. 기존 실습 SQL에 `replay_lag`가 없어 그 필드의 NULL 사례는 합성입니다.
- Collector 테스트는 한 exporter 수명의 기준값·held retry 표본·최종 표본 세 시점을 재생합니다. 모든 순간을 계측하거나 지표 증가의 정확한 순간·종단 유실량을 증명하지 않습니다.
- histogram은 합성 분포를 실제 promtool 두 버전으로 평가한 debug 출력입니다. 참조 보간은 유한한 양수 bucket만 다루며, 음수·zero bucket·NaN/+Inf·혼합 schema 병합·저장 엔진 구현은 없습니다.
- `DELETED`, 후속 GET 200/404, UID 교체는 다른 관측입니다. 404 하나로 삭제 원인이나 정확한 삭제 시각을 확정하지 않습니다.
- 1% CPU clock 품질 허용차는 참조 정책입니다. CLOCK_MONOTONIC_RAW의 외부 정확도를 보증하거나 시계 조정 주체를 단정하지 않습니다.

## 제품으로 가져갈 때

카탈로그에서 원천 정의를 선택하고, 실제 대상의 capability·인증된 범위·수명을 연결한 뒤 값을 읽습니다. 정상 숫자와 `absent`/`null`/`restricted` 등의 상태를 나누어 저장합니다. 이후 단위 변환과 차분을 적용하고, 이 저장소의 fixture를 제품 언어의 테스트 입력으로 재사용할 수 있습니다. 네트워크 수집·timeout·재연결·인증·저장소 멱등성과 실제 버전 수용 검사는 제품 구현에서 별도로 필요합니다.
