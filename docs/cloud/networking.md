# 클라우드 네트워크: 경로, 정책과 흐름 로그

> 상태: 검토됨 · 적용 범위: 공통 조사 모델과 AWS VPC 사례 · 출처 확인일: 2026-10-03 · 편집 검토일: 2026-10-04 · 2라운드 보강 확인: 2026-10-05 (VPC Flow Logs 집계·예외)

## 먼저 이해할 것

클라우드 네트워크에는 주소·경로 외에 보안 정책과 주소 변환 같은 경계가 있습니다. 방화벽에서 허용한 패킷이 앱까지 성공적으로 처리되었다는 뜻은 아닙니다. flow log의 허용·거절과 실제 사용자 요청 결과를 서로 다른 증거로 읽습니다.

클라우드 네트워크에서는 주소·라우팅·정책·주소 변환·서비스 endpoint의 설정을 함께 확인합니다. 설정상 허용과 실제 애플리케이션 성공은 같은 결과가 아닙니다.

## 연결 경로의 모델

다음은 제품의 논리 관계 모델입니다.

```text
워크로드 → 네트워크 인터페이스 → subnet/route
         → 정책 경계 → NAT/중계/서비스 endpoint → 목적지
```

실제 배치는 직접 연결, peering, VPN, 전용 연결 등으로 달라질 수 있습니다. 그림의 모든 요소가 반드시 존재하는 것은 아닙니다. [주소와 NAT](../network/addressing-routing-dns.md), [TLS 종단](../network/tls-http.md)을 함께 읽습니다.

## stateful과 stateless 정책

AWS security group은 stateful입니다. 허용된 요청의 응답은 반대 방향 규칙만으로 새로 판단하는 단순 stateless 모델과 다르게 처리됩니다. [AWS Security Groups](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html)

AWS network ACL은 subnet 경계의 stateless 규칙이며 응답도 관련 규칙을 통과해야 합니다. 동일한 이름의 방화벽 기능이라고 해서 두 정책을 같은 방식으로 평가하면 안 됩니다. [AWS Network ACLs](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html)

가상의 클라이언트 출발지 포트가 51000이고 서버 목적지 포트가 443이면 응답은 반대 방향의 포트 조합입니다. 조사에서는 요청 방향 443 허용만 확인하지 않고 실제 응답 경로와 정책을 비교합니다. 모든 공급자의 방화벽 동작을 이 AWS 사례로 일반화하지 않습니다.

## flow log가 알려 주는 범위

VPC Flow Logs는 ACCEPT·REJECT 같은 흐름 결과와 로그 상태를 제공합니다. NODATA는 기록할 트래픽이 없는 구간을, SKIPDATA는 캡처하지 못한 기록이 있음을 나타낼 수 있습니다. SKIPDATA 한 기록이 여러 누락 흐름을 대표할 수도 있습니다. [AWS Flow Log Examples](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs-records-examples.html)

따라서 로그가 없다는 사실을 언제나 트래픽 0으로 바꾸지 않습니다. ACCEPT도 HTTP 성공이나 업무 완료를 의미하지 않으며 실제 상위 계층 결과를 추가 확인해야 합니다.

## 흐름 로그의 집계 간격과 사각지대

2026-10-05 확인한 VPC Flow Logs의 최대 집계 간격 기본값은 10분이며 1분을 선택할 수 있습니다. Nitro 기반 인스턴스에 연결된 네트워크 인터페이스는 설정과 관계없이 1분 이하로 집계합니다. 이는 로그가 그 시간 안에 목적지에 도착한다는 보장이 아닙니다. 집계와 게시 지연을 구분해야 합니다. [흐름 로그 레코드와 집계](https://docs.aws.amazon.com/vpc/latest/userguide/flow-log-records.html)

다음은 기록되지 않는 트래픽의 **주요 예**입니다. 전체 예외는 공식 목록을 적용 대상별로 확인합니다. [Flow Logs 제한](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs-limitations.html)

| 예외 | 관측상 주의점 |
| --- | --- |
| Amazon 제공 DNS 서버와의 통신 | 자체 DNS 서버와의 통신까지 모두 제외된다는 뜻은 아님 |
| 인스턴스 메타데이터 `169.254.169.254` | 로그 부재로 metadata 접근이 없었다고 증명하지 못함 |
| Amazon Time Sync `169.254.169.123`, DHCP, ARP | 시간 동기화·주소 설정·인접 탐색의 성공을 flow log만으로 판단하지 않음 |
| Windows 라이선스 활성화, VPC 예약 라우터 주소 관련 트래픽 | 일반 앱 흐름과 수집 범위가 다름 |
| traffic mirroring의 원본 트래픽 | mirror 대상에서 관측한 기록과 혼동하지 않음 |
| endpoint ENI와 Network Load Balancer ENI 사이 | 다른 구간의 기록으로 그 구간을 보았다고 단정하지 않음 |

제품 적용 제안은 “패킷을 모두 기록한 증거”가 아니라 **정해진 범위에서 집계한 흐름 증거**로 표시하는 것입니다. flow log 구독·저장 비용, IAM 조회 권한, 집계 설정을 수집 명세에 남깁니다. 이 장에서 flow log를 활성화하거나 cloud 질의를 실행하지 않았습니다.

## 가상 장애 분석

특정 subnet에서만 DB 접속이 실패한다고 가정합니다. 먼저 클라이언트가 선택한 주소와 경로를 확인하고, 양쪽 정책·변환과 실제 flow 기록을 비교합니다. 연결이 성립했다면 TLS·DB 인증과 쿼리 단계로 이동합니다.

“설정 변경 뒤 장애가 발생했다”는 시간 상관만으로 그 설정을 원인으로 확정하지 않습니다. 해당 트래픽이 변경된 규칙의 범위를 지나갔는지, 실패 단계와 정책 결과가 일치하는지 확인합니다.

## 제품의 토폴로지 정보

원천 인터페이스 ID, 계정·리전, 사설 네트워크 범위, 주소 유효 기간, 실제 관측자와 정책의 적용 범위를 저장하도록 제안합니다. NAT 전후 주소를 근거 없이 동일 대상으로 합치지 않습니다. 다른 VPC에 같은 사설 IP가 있을 수 있으므로 IP 문자열만으로 간선을 만들지 않습니다.

## 이해 확인

1. security group과 NACL은 모두 같은 상태 추적을 하는가? **AWS에서는 stateful과 stateless 차이가 있습니다.**
2. ACCEPT 로그면 DB 쿼리가 성공했는가? **전송·인증·업무 결과를 더 확인해야 합니다.**
3. SKIPDATA를 트래픽 0으로 저장해도 되는가? **관측 누락을 잘못 표현합니다.**
4. 최대 집계 간격이 1분이면 1분 내 조회가 보장되는가? **게시·전달 지연은 별도입니다.**

관련: [네트워크 관측](../network/network-metrics.md) · [클라우드 목차](README.md)
