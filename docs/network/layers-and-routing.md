# 링크, 오버레이, MTU와 경로 제어

> 상태: 검토됨 · 적용 범위: Ethernet의 주소 해석, IPv6 ND·PMTUD, VXLAN, 기본 BGP 관측 · 원천 확인일: 2026-10-06 · 실습 여부: 원천·가상 예시 중심; 연결 실습의 범위는 본문

## 먼저 이해할 것

같은 망의 다음 장치에 전달하는 문제와 멀리 있는 목적지까지 경로를 찾는 문제는 다릅니다. ARP·ND는 가까운 링크의 이웃 정보를, 라우팅은 다음 경로를 다룹니다. 터널은 원래 패킷에 바깥 포장을 추가하므로 보낼 수 있는 내부 크기도 달라집니다.

IP 주소가 맞고 서버 포트가 열려 있어도 통신이 실패할 수 있습니다. 실제 패킷은 다음 홉의 링크 주소를 찾고, 터널 헤더를 포함한 크기 제한을 지키며, 설치된 경로를 따라 이동해야 합니다. 이 장에서는 네트워크 지표를 해석할 때 필요한 계층별 경계를 설명합니다.

## 계층과 전달 단위부터 구분하기

| 계층 | 전달 단위·주소 | 이 장에서 묻는 질문 |
| --- | --- | --- |
| L2 링크 | Ethernet frame·MAC | 같은 링크의 다음 장치에 어떻게 넘기는가 |
| L3 인터넷 | IP packet·IP 주소 | 어느 다음 홉으로 보낼 것인가 |
| L4 전송 | TCP segment / UDP datagram·port | 어느 통신 끝점에 전달하고 어떤 전송 규약을 쓰는가 |

한 요청의 데이터가 TCP segment, IP packet, 링크 frame에 차례로 담깁니다. **MTU**는 여기서는 링크가 운반할 IP packet 크기의 경계이며 애플리케이션 payload 한도가 아닙니다. [인터넷 호스트 계층, RFC 1122](https://www.rfc-editor.org/rfc/rfc1122.html#section-1.3.3), [TCP, RFC 9293](https://www.rfc-editor.org/rfc/rfc9293.html#section-3.1)

전달을 네 단계로 읽습니다: **① 목적지 IP의 경로 선택 → ② 다음 홉 링크 주소 해석 → ③ frame으로 전달 → ④ 수신 측에서 헤더를 해석해 IP·전송 끝점으로 전달**. 라우터를 지나면 링크 frame은 바뀔 수 있으며 목적지까지 같은 MAC으로 이동한다고 가정하지 않습니다. [RFC 1122의 링크·IP 경계](https://www.rfc-editor.org/rfc/rfc1122.html#section-2)

## 다음 홉의 주소 해석

Ethernet의 IPv4 통신에서 ARP는 프로토콜 주소와 링크 주소의 대응을 구하는 데 사용됩니다. 라우팅이 선택한 다음 홉의 주소를 해석하는 것이므로 목적지가 원격 네트워크에 있으면 일반적으로 원격 서버 자체가 아니라 로컬 다음 홉의 MAC 주소가 필요합니다. [RFC 826](https://www.rfc-editor.org/rfc/rfc826.txt)

IPv6 Neighbor Discovery는 이웃의 링크 주소 확인, 라우터 발견, 이웃 도달 가능성 확인 등의 기능을 정의합니다. IPv4의 ARP 자료를 IPv6 관측에 그대로 적용할 수 없습니다. [RFC 4861](https://www.rfc-editor.org/rfc/rfc4861.txt)

| 관측 | 가능한 해석 | 추가 확인 |
| --- | --- | --- |
| 경로가 없음 | 패킷 전달 경로 선택 실패 | 올바른 network namespace와 routing table인지 |
| 다음 홉 해석 실패 | 링크·이웃·주소 설정 문제 후보 | VLAN·서브넷·다음 홉 상태 |
| 이웃 항목이 있음 | 과거 또는 현재 대응 정보를 알고 있음 | 실제 도달성·항목 상태·유효 시간 |
| 링크는 Up | 링크 수준 상태가 성립 | IP 경로·정책·업무 요청 성공은 별도 |

제품이 호스트의 이웃 표를 보여준다면 수집한 네트워크 범위를 붙여야 합니다. 컨테이너의 이웃 표와 호스트의 이웃 표가 같은 관측 대상이라고 가정하지 않습니다.

## 오버레이와 실제 운반 경로

VXLAN은 L2 프레임을 UDP/IP 위에 캡슐화하고 VNI로 오버레이 네트워크를 구분합니다. VTEP는 터널의 끝점입니다. 내부 주소가 나타내는 통신과 외부 터널 주소가 나타내는 통신을 구분해야 합니다. [RFC 7348](https://www.rfc-editor.org/rfc/rfc7348.txt)

```mermaid
flowchart LR
    A["내부 송신 대상"] --> V1["VTEP A"]
    V1 -->|외부 IP와 UDP로 운반| V2["VTEP B"]
    V2 --> B["내부 수신 대상"]
```

내부 대상 100쌍의 통신이 외부 터널 몇 개로 합쳐질 수 있습니다. 물리 NIC에서 본 흐름 수와 내부 업무 연결 수가 다르다고 해서 반드시 누락은 아닙니다. 또한 가상 NIC·터널·물리 NIC의 바이트를 모두 더하면 같은 데이터를 중복 계산할 수 있습니다.

## MTU와 헤더 비용

MTU는 해당 계층에서 한 번에 운반하는 패킷 크기의 제한입니다. VXLAN은 캡슐화 헤더 때문에 내부 패킷보다 큰 외부 패킷을 만듭니다. RFC는 캡슐화 크기를 수용하도록 하부 네트워크 MTU를 구성하는 등의 처리를 설명합니다. [VXLAN frame format과 MTU](https://www.rfc-editor.org/rfc/rfc7348.txt)

**외부 IPv4 옵션 없음, VLAN 태그 없음, 내부 Ethernet 헤더 14 B, FCS를 터널 내부에 넣지 않는 경우**의 설명용 계산입니다.

```text
외부 IP MTU = 1,500 B
외부 IPv4 = 20 B
UDP = 8 B
VXLAN = 8 B
내부 Ethernet = 14 B

내부 IP 패킷의 최대 크기 = 1,500 - 20 - 8 - 8 - 14
                       = 1,450 B
```

이 1,450 B는 애플리케이션 payload 크기가 아닙니다. 내부 IP와 TCP·UDP 헤더가 더 들어갑니다. IPv6 외부 헤더, 다른 터널, 추가 태그·암호화가 있으면 다시 계산해야 합니다. 모든 Kubernetes Pod의 MTU가 1,450이라는 뜻도 아닙니다.

**가상 예시를 TCP까지 확장하면:** 내부 IPv4와 TCP에 옵션이 없고 상대 MSS 등 다른 제한이 더 작지 않을 때 payload 상한은 `1,450 − 20 − 20 = 1,410 B`입니다. MSS(Maximum Segment Size)는 TCP 데이터 크기의 제한이며 옵션·경로·상대 수신 제한을 더 확인합니다. [RFC 9293 §3.7.1](https://www.rfc-editor.org/rfc/rfc9293.html#section-3.7.1)

IPv6 PMTUD는 경로의 더 작은 MTU를 Packet Too Big 메시지 등을 통해 알아내도록 정의합니다. 필요한 메시지가 전달되지 않는 경로에서는 작은 요청은 성공하지만 큰 패킷 전송이 멈추는 문제를 조사해야 합니다. [RFC 8201](https://www.rfc-editor.org/rfc/rfc8201.txt)

## 심화: IPv4 PMTUD와 탐색 패킷을 쓰는 방법

IPv4의 전통적인 PMTUD는 DF(Don't Fragment)를 설정한 패킷과 라우터의 ICMP fragmentation needed 응답을 이용합니다. 더 작은 경로 MTU를 알게 되면 송신 크기를 조절합니다. 필요한 ICMP가 차단되면 TCP 연결이나 작은 요청은 성공한 뒤 큰 데이터만 멈추는 black hole 현상이 생길 수 있습니다. IPv6의 Packet Too Big과 같은 이름·형식의 메시지로 저장하지 않습니다. [IPv4 PMTUD, RFC 1191](https://www.rfc-editor.org/rfc/rfc1191.html), [black hole 장애 양상, RFC 2923 §2.1](https://www.rfc-editor.org/rfc/rfc2923.html#section-2.1)

PLPMTUD는 packetization layer가 탐색 크기와 전달 성공의 피드백을 이용해 경로 MTU를 찾는 방법입니다. 유효한 ICMP 오류의 도착에만 의존하지 않지만, 구현의 탐색·확인·손실 구분 절차가 필요합니다. RFC 4821의 일반 방법과 RFC 8899의 **datagram용 DPLPMTUD**를 구분합니다. RFC 8899를 모든 TCP 구현의 동작 명세로 인용하지 않습니다. [PLPMTUD, RFC 4821](https://www.rfc-editor.org/rfc/rfc4821.html), [DPLPMTUD, RFC 8899](https://www.rfc-editor.org/rfc/rfc8899.html)

**제품 적용 제안:** 작은 요청과 큰 응답의 성공 차이, 경로 MTU·터널 헤더, ICMP 오류, TCP 재전송 또는 datagram probe 결과를 같은 관측 구간에 연결합니다. 이것들은 원인 후보를 좁히는 증거이며 ICMP 차단의 단독 증명은 아닙니다. 이 장에서는 능동 probe나 패킷 캡처를 실행하지 않았습니다. 실제 진단에는 대상 경로에 대한 권한과 probe 부하·캡처 권한을 확인하고, MTU·방화벽을 수집기가 자동 변경하지 않도록 합니다.

## 경로 제어와 실제 전달

BGP는 경로 정보를 교환하며, 받은 경로·로컬에서 선택한 경로·이웃에게 광고하는 경로의 논리적 구분을 둡니다. 정책과 next-hop 도달성 등이 경로 선택·광고에 영향을 줍니다. [RFC 4271](https://www.rfc-editor.org/rfc/rfc4271.txt)

따라서 `BGP session Established`는 이웃과의 제어 연결 상태를 보여주는 증거입니다. 원하는 목적지 prefix가 수신·선택·설치되었는지, 실제 패킷이 전달되는지까지 모두 증명하지 않습니다. 라우터별 추가 경로 선택 규칙은 해당 OS·버전의 명세가 필요합니다.

**관측 모델 제안:** peer 상태와 지속 시간, prefix 수 변화, route withdrawal, 선택한 next hop, 전달 표, 해당 경로의 능동 검사 결과를 함께 저장합니다. 경로의 변경 시각도 보존해야 과거 장애를 현재 경로로 설명하는 오류를 줄일 수 있습니다.

## 조사 순서 예시

큰 응답에서만 timeout이 난다는 가상 증상이라면 다음 가설을 비교합니다.

1. DNS·연결·TLS 단계 중 어느 단계까지 실제 성공했는지 확인합니다.
2. 같은 출발·목적지에서 패킷 크기와 성공 여부의 관계를 확인합니다.
3. 실제 경로의 터널과 인터페이스 MTU, ICMP 오류 관측을 확인합니다.
4. 재전송·서버 처리 지연·클라이언트 수신 지연도 비교합니다.

큰 응답에서만 느리다는 사실 하나로 MTU 문제를 확정하지 않습니다. 압축·메모리·응답 생성 비용도 응답 크기에 따라 달라질 수 있습니다.

## 이해 확인

1. 원격 서버 IP의 ARP 항목이 없으면 통신할 수 없는가? **Ethernet의 로컬 다음 홉 주소가 필요한 경로일 수 있다.**
2. BGP 연결이 정상이면 모든 prefix가 정상인가? **수신·선택·설치·실제 전달은 따로 확인해야 한다.**
3. 내부 IP MTU 1,450 B를 업무 payload 1,450 B로 사용해도 되는가? **내부 전송·IP 헤더 크기를 추가로 고려해야 한다.**
4. RFC 8899는 모든 TCP의 MTU 탐색 규약인가? **datagram용 DPLPMTUD이며 적용 전송과 구현을 확인해야 한다.**

관련: [주소와 DNS](addressing-routing-dns.md), [인터페이스·흐름 지표](network-metrics.md), [Kubernetes 네트워크](../kubernetes/network-and-storage.md)

이전: [주소, 경로, 이름 해석](addressing-routing-dns.md) · 다음: [TCP, UDP, 연결과 전송 속도](tcp-and-udp.md) · [분야 목차](README.md)
