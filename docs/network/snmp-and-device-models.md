# 네트워크 장비 수집: SNMP, MIB와 인터페이스 수명

> 상태: 검토됨 · 적용 범위: SNMPv3·IF-MIB·SNMPv2-MIB 표준, 수집기 설계 · 원천 확인일: 2026-10-06 · 실습 여부: 원천·가상 예시 중심; 연결 실습의 범위는 본문

SNMP는 장비의 관리 정보를 질의하는 프로토콜이고, MIB는 그 정보의 이름·타입·의미를 정의한 모음입니다. OID는 그 정의를 계층적인 숫자 주소로 식별합니다. 장비 이름이 같다고 모든 제조사의 CPU 지표가 같은 OID에 있는 것은 아닙니다. 표준 MIB와 제조사별 확장을 구분해야 합니다.

| 버전 | 먼저 구분할 기능 |
| --- | --- |
| v1 | Counter64 표현 불가; GETNEXT 순회에서 해당 객체가 빠질 수 있음 |
| v2c | Counter64·GETBULK 사용 가능; community 기반 접근 |
| v3 | 보안 모델·인증·프라이버시 설정을 별도로 확인; Counter64 가능 |

버전과 권한, 장비가 구현한 MIB는 각각 확인합니다. [SNMP 공존 규약](https://www.rfc-editor.org/rfc/rfc3584.html)

## 먼저 식별하고 그다음 수집하기

장비 관리 주소는 이동하거나 재사용될 수 있습니다. 수집 대상 키에는 테넌트·관리 영역·장비 정체성을 넣고, 접속 주소는 속성으로 관리하도록 제안합니다. `sysObjectID`는 제조사가 관리 하위 시스템·장비 종류를 식별하도록 할당한 OID이며 개별 장비의 전역 고유 일련번호가 아닙니다. `sysName`도 운영자가 바꿀 수 있는 이름입니다. [SNMPv2-MIB RFC 3418](https://www.rfc-editor.org/rfc/rfc3418.html)

`sysUpTime.0`은 **네트워크 관리 부분이 마지막으로 초기화된 뒤의 시간**이며 1/100초 단위입니다. 장비의 물리 전원 켜짐 이후 시간과 항상 같다고 표시하지 않습니다. 32bit TimeTicks는 약 497.1일에 순환할 수 있으므로 감소를 모두 장비 재부팅으로 분류하지 않습니다.

## 인터페이스 필드 계약

아래 OID는 인덱스가 붙기 전의 열 주소입니다. 예를 들어 인터페이스 인덱스 7의 입력 octet은 `1.3.6.1.2.1.31.1.1.1.6.7`입니다.

| 필드 | 열 OID | 의미·단위 | 수집 규칙 |
| --- | --- | --- | --- |
| ifIndex | 1.3.6.1.2.1.2.2.1.1 | 인터페이스 인덱스 | 장비·관리 수명 범위에서 식별 |
| ifAdminStatus | 1.3.6.1.2.1.2.2.1.7 | 운영자가 원하는 상태 | up/down/testing 코드 보존 |
| ifOperStatus | 1.3.6.1.2.1.2.2.1.8 | 실제 동작 상태 | down 외 dormant·lowerLayerDown 등 구분 |
| ifHCInOctets | 1.3.6.1.2.1.31.1.1.1.6 | Counter64, 수신 octet | 프레이밍 문자 포함이라는 정의 보존 |
| ifHCOutOctets | 1.3.6.1.2.1.31.1.1.1.10 | Counter64, 송신 octet | 수신과 별도 증가율 |
| ifHighSpeed | 1.3.6.1.2.1.31.1.1.1.15 | 1,000,000bit/s 단위 속도 추정 | 비율 분모; 0·미지원 처리 |
| ifCounterDiscontinuityTime | 1.3.6.1.2.1.31.1.1.1.19 | 마지막 카운터 불연속의 sysUpTime | 변경 시 차분 연결 중단 |

정의와 OID는 [IF-MIB RFC 2863](https://www.rfc-editor.org/rfc/rfc2863.html)에 근거합니다. `ifDescr`, `ifName`, `ifAlias`는 정체성 보조 정보이며 독립된 영구 UUID처럼 사용하지 않습니다. 관리 상태가 의도적으로 down인 포트와, up을 원하지만 실제로 down인 포트의 알림 정책을 분리합니다.

## 속도 계산 예시

동일 인터페이스·연속 카운터에서 20초 동안 수신 값이 500,000,000octet 늘고 `ifHighSpeed=1000`이라면 수신은 200,000,000bit/s, 표의 분모 기준 20%입니다. 송신 30%를 더해 “full duplex 사용률 50%”로 만들지 않습니다. 각 방향에 독립된 용량이 있는지 인터페이스 특성을 확인합니다.

32bit Counter를 사용할 때는 수집 사이 여러 번 순환하면 단순 차분으로 복원할 수 없습니다. 각 링크 속도에 해당하는 octet이 계속 계정된다는 가상 예시에서 한 바퀴 도는 시간은 **10 Gbit/s면 약 3.44초, 1 Gbit/s면 약 34.4초**입니다. Counter64 지원 여부를 확인하고 32bit fallback에서는 가능한 최대 증가량과 수집 간격을 함께 다룹니다.

**제품 적용 제안 — wrap 보정 조건:** 같은 장비·인터페이스·관리 수명이고 reset이 없다는 근거를 먼저 확보합니다. `sysUpTime`의 역행·초기화와 `ifCounterDiscontinuityTime`의 변경은 불연속 단서입니다. 정상적인 uptime 증가나 표식이 유지된다는 사실만으로 연속성을 입증하지는 않습니다. 그 구간의 신뢰할 수 있는 최대 증가량이 `2^32`보다 작고 관측 차이와 양립할 때만 감소에 1회 wrap 보정을 검토합니다. `ifHighSpeed × 10^6 / 8 × 간격`은 속도·계층·방향이 실제 상한이라는 조건에서만 그 근거가 됩니다. 조건을 모르면 `decrease`로 남기고 rate를 보류합니다. [차분·wrap 계약](../host/collection-contracts.md), [조건부 참조 구현](../product/adapter-contracts.md)

## 조회와 알림은 서로 보완한다

GET은 지정한 객체를 읽고, GETNEXT·GETBULK는 테이블을 순회하는 데 사용합니다. GETBULK의 반복 수를 크게 하면 패킷 크기·장비 부하·응답 절단이 문제가 될 수 있습니다. 마지막 응답의 일부 행만으로 전체 인터페이스가 삭제되었다고 처리하지 않고, walk 완료 상태를 기록합니다. [SNMP 프로토콜 연산 RFC 3416](https://www.rfc-editor.org/rfc/rfc3416.html)

Trap은 비확인 통지이고 Inform은 응답을 사용하는 통지입니다. 그러나 Inform을 썼다는 사실만으로 제품 저장소에 영구 반영되었다고 보장되지는 않습니다. 장애 발생 시각·수신 시각·중복·유실을 다루고, 주기 조회로 현재 상태를 재확인합니다.

SNMPv3에서는 보안 모델과 인증·프라이버시 수준을 명시합니다. USM의 인증과 암호화 선택은 별도이며, “v3”라는 문자열만으로 암호화가 활성화됐다고 판단하지 않습니다. 키·암호는 지표 label이나 로그에 기록하지 않습니다. [SNMPv3 USM RFC 3414](https://www.rfc-editor.org/rfc/rfc3414.html)

## Counter64는 SNMPv3만의 기능이 아니다

SNMPv1은 Counter64를 표현하지 못합니다. RFC 3584 §4.2.2.1은 여러 SNMP 버전을 지원하는 responder가 **v1 메시지를 받은 경우**를 규정합니다. Counter64 객체의 GET에는 `noSuchName`을 반환하고, GETNEXT에서는 그 객체를 건너뜁니다. 따라서 v1 walk가 진행돼도 `ifHC*`가 빠질 수 있으며 이를 장비 자체의 고용량 카운터 미지원으로 확정하지 않습니다. SNMPv2c와 v3에서는 Counter64를 사용할 수 있지만 실제 MIB 구현·접근 권한도 확인해야 합니다. 암호화·인증과 카운터 폭은 별개입니다. [공존 규칙](https://www.rfc-editor.org/rfc/rfc3584.html#section-4.2.2.1)

RFC 2863 §3.1.6의 속도별 카운터 요구 설명은 다음과 같습니다. 여기서 octet은 byte 단위이며 packet 카운터와 구분됩니다. [IF-MIB 고용량 카운터](https://www.rfc-editor.org/rfc/rfc2863.html#section-3.1.6)

| 인터페이스 속도 | §3.1.6이 요구하는 카운터 |
| --- | --- |
| 20,000,000 bit/s 이하 | 32bit octet·packet |
| 20,000,000 초과, 650,000,000 bit/s 미만 | 64bit octet·32bit packet |
| 650,000,000 bit/s 이상 | 64bit octet·packet |

단, 같은 RFC 뒤의 MIB conformance group 문구는 packet 카운터의 경계를 `greater than 650,000,000`으로 표현합니다. **정확히 650 Mbit/s인 장비의 구현 의무를 이 요약 표만으로 판정하지 않습니다.** 어댑터는 실제 지원 OID와 Counter64 반환 타입을 확인하고 미지원은 명시합니다. 64bit 카운터를 지원하더라도 불연속 시각·재시작 검사는 필요합니다.

`ifSpeed`는 bit/s 단위의 Gauge32이며 표현 범위를 넘으면 최대값 `4,294,967,295`를 보고합니다. 고속 인터페이스에서는 `ifHighSpeed`의 1,000,000 bit/s 단위 속도 추정값을 사용합니다. 포화된 ifSpeed를 실제 링크 속도로 사용하면 이용률 분모가 작아집니다. [ifSpeed·ifHighSpeed 정의](https://www.rfc-editor.org/rfc/rfc2863.html)

장비 조회는 이 장에서 실행하지 않았습니다. 실제 수집에는 읽기용 SNMP view·자격 증명·관리 경로가 필요하며, 대규모 walk는 장비 CPU와 관리 대역폭을 사용합니다. 지원 확인을 위해 설정을 변경하는 SET을 자동 실행하지 않는 수집 계약을 제안합니다.

## 제조사 확장과 장비 상태

전원·팬·온도·광 송수신·무선 품질 등은 제조사 MIB 또는 별도 API와 적용 모델을 확인합니다. 원천 단위가 0.1℃인지 ℃인지, optical power가 mW인지 dBm인지, 경보 한계가 장치에서 제공되는지부터 명세합니다. 수집되지 않는 온도를 0℃로 채우지 않습니다.

표준으로 확인한 범위와 실제 모델별 검증 범위를 어댑터 capability에 따로 표시합니다. 동일 MIB 이름이 있다는 이유만으로 모든 모델의 센서·카운터를 검증했다고 광고하지 않습니다.

## 이해 확인

1. sysUpTime 감소는 항상 호스트 재부팅인가? **관리 프로세스 초기화나 wrap 등을 구분해야 합니다.**
2. ifIndex=7은 모든 장비의 같은 포트인가? **장비와 관리 범위가 필요한 지역 식별자입니다.**
3. SNMP 응답 timeout이면 포트가 down인가? **관리 경로·자격 증명·부하를 먼저 구분합니다.**
4. Counter64를 읽으려면 반드시 SNMPv3이어야 하는가? **v2c도 표현할 수 있고, 장비 구현·권한은 따로 확인합니다.**
5. 포화된 ifSpeed를 분모로 삼아도 되는가? **ifHighSpeed 등 올바른 속도 근거를 확인해야 합니다.**

관련: [네트워크 지표](network-metrics.md) · [수집 계약](../product/adapter-contracts.md)

이전: [Linux 네트워크 스택 카운터 읽기](linux-stack-counters.md) · 다음: [경로 수렴과 QoS: 연결은 살아 있는데 통신이 느린 이유](routing-convergence-and-qos.md) · [분야 목차](README.md)
