# Linux 네트워크 스택 카운터 읽기

> 상태: 검토됨 · 적용 범위: Linux 6.12 procfs·TCP/UDP 코드, iproute2 `ss` 문서 · 원천 확인일: 2026-10-05 · 실습 여부: 원천·가상 예시 중심; 연결 실습의 범위는 본문

선수: [TCP 상태와 서버 대기열](tcp-and-udp.md#tcp-상태와-서버의-두-대기열). 표에서는 무엇을 세는지 먼저 읽고, 코드 경로·backport는 구현 근거로 확인합니다.

## 먼저 이해할 상황

웹 서버가 연결을 놓치는데 NIC의 오류 카운터는 증가하지 않을 수 있습니다. NIC가 패킷을 정상 수신한 뒤 TCP의 연결 대기열이나 UDP의 소켓 버퍼에서 처리가 막힐 수 있기 때문입니다. [인터페이스 지표](network-metrics.md)는 링크 경계, 이 장의 카운터는 커널 프로토콜 처리 경계를 설명합니다. 어느 쪽도 단독으로 업무 요청의 성공 수를 세지는 않습니다.

`/proc/net/snmp`라는 이름이 있어도 SNMP agent를 설치하거나 UDP 161번 포트를 열어야 읽을 수 있는 파일은 아닙니다. `/proc/net`은 현재 프로세스의 network namespace에 해당하는 `/proc/self/net`을 가리킵니다. `/proc/PID/net`도 **그 PID만의 트래픽**이 아니라 그 프로세스가 속한 network namespace의 통계입니다. [proc_pid_net(5)](https://man7.org/linux/man-pages/man5/proc_pid_net.5.html)

따라서 호스트 namespace와 별도 Pod namespace의 값은 범위가 다릅니다. 같은 namespace를 공유하는 여러 컨테이너에서 읽은 값을 더하면 중복될 수 있습니다. 제품은 호스트 ID·부팅 수명·network namespace 식별자와 그 수명을 함께 보존해야 합니다. 프로세스가 바뀌었다는 이유만으로 namespace 카운터를 재시작된 프로세스 카운터처럼 처리하지 않습니다.

## TCP: 시도, 연결, 세그먼트를 구분한다

연결 시작·현재 연결·세그먼트 수는 서로 다른 단위입니다. `PassiveOpens`를 SYN 도착률로 쓰지 않고, `CurrEstab`의 CLOSE-WAIT 포함은 Linux 6.10 변경과 배포판 backport 여부를 확인합니다. 커널 함수와 예외는 아래 심화에 모았습니다.

다음은 `/proc/net/snmp`의 `Tcp:` 블록입니다. `CurrEstab` 이외의 아래 항목은 누적 횟수이며, 구간 발생률은 같은 수명의 두 표본 차이를 초 단위 간격으로 나눕니다. 표의 연결 상태 전이는 [TCP-MIB 정의](https://www.rfc-editor.org/rfc/rfc4022.html#section-3), Linux 구현상 차이는 [커널 설명](https://docs.kernel.org/networking/snmp_counter.html)을 기준으로 합니다.

| 필드 | 단위·정의 | 읽을 때 주의할 점 |
| --- | --- | --- |
| `ActiveOpens` | 회: CLOSED → SYN-SENT의 능동 연결 시작 | 연결 성공 횟수 아님 |
| `PassiveOpens` | 회: Linux 6.12에서 수동 연결의 child 소켓 생성 | SYN 도착 수·애플리케이션의 `accept()` 완료 수 아님 |
| `AttemptFails` | 회: TCP-MIB의 추상 정의는 SYN-SENT/SYN-RCVD → CLOSED 및 SYN-RCVD → LISTEN | Linux request socket 만료의 예외는 아래 설명; 연결 실패의 전수 아님 |
| `EstabResets` | 회: ESTABLISHED/CLOSE-WAIT → CLOSED | 정상 FIN 종료 수와 구분 |
| `CurrEstab` | 연결 수, **gauge**: 이 장의 6.12에서는 ESTABLISHED 또는 CLOSE-WAIT | 아래 커널 수정 조건 확인; 전체 소켓 수 아님 |
| `InSegs` | 수신 세그먼트 수, 오류가 있는 세그먼트도 포함 | GRO 병합의 영향을 받으므로 NIC 패킷 수와 다를 수 있음 |
| `OutSegs` | 송신 세그먼트 계정, ACK·SYN·RST도 포함 | 원래 데이터 전송량이나 wire에서 실제 전달된 수가 아님 |
| `RetransSegs` | 재전송 세그먼트 수 | 손실된 고유 세그먼트 수 아님; 같은 데이터가 여러 번 재전송될 수 있음 |
| `InErrs` | 수신 TCP 오류 세그먼트 수 | 지연·애플리케이션 오류의 포괄 지표 아님 |
| `OutRsts` | RST 송신 시도 수 | Linux에서는 실제 송신 이전 실패도 가능 |

`AttemptFails`도 모든 실패 handshake를 세지는 않습니다. Linux 6.12의 일반 IPv4 request socket이 SYN/ACK 재시도를 소진하는 timer 경로는 `TCPTimeouts`를 증가시키고 요청을 제거하며, 이 경로에서 `AttemptFails`를 올리지 않습니다. 따라서 이 카운터와 `PassiveOpens`만으로 서버의 전체 연결 실패율을 계산하지 않습니다. 이는 고정 버전 코드 대조이며 패킷 손실 실험은 실행하지 않았습니다. [request timer·제거 경로](https://github.com/torvalds/linux/blob/v6.12/net/ipv4/inet_connection_sock.c#L1149), [timeout 계수](https://github.com/torvalds/linux/blob/v6.12/net/ipv4/tcp_timer.c#L732), [IPv4 request 해제](https://github.com/torvalds/linux/blob/v6.12/net/ipv4/tcp_ipv4.c#L1218)

## UDP와 확장 TCP 카운터

UDP는 TCP처럼 재전송·연결 수립을 커널이 보장하지 않습니다. 아래 UDP 값은 `/proc/net/snmp`의 `Udp:` 블록을 대상으로 하며 IPv6용 `Udp6*`는 `/proc/net/snmp6`에서 별도로 확인합니다. 파일 전체를 동일한 주소 family의 통계라고 가정하지 말고 프로토콜별 원천을 명세합니다. [IPv4 UDP 코드](https://github.com/torvalds/linux/blob/v6.12/net/ipv4/udp.c), [IPv6 proc 출력](https://github.com/torvalds/linux/blob/v6.12/net/ipv6/proc.c)

| 필드 | 누적 단위와 의미 | 가설을 좁힐 추가 증거 |
| --- | --- | --- |
| `InDatagrams` | 애플리케이션에 전달된 UDP datagram 수 | 수신 프로그램의 처리·업무 성공 카운터 |
| `NoPorts` | 받을 소켓/포트가 없는 datagram 수 | 목적지·리스너 수명·배포 시각 |
| `InErrors` | 포트 부재 이외의 수신 오류 수 | checksum·버퍼 관련 세부 필드 |
| `RcvbufErrors` | 주 수신 큐 경로의 소켓 수신 버퍼 초과(`-ENOMEM`) 등 | 소비 속도·`sk_rcvbuf`; multicast 복제 실패 경로도 있음 |
| `MemErrors` | 주 수신 큐 경로의 프로토콜 메모리 확보 실패(`-ENOBUFS`) | 전역 UDP 메모리 압박·`udp_mem` 등; 소켓 한도와 구분 |
| `SndbufErrors` | 송신 실패 경로의 `-ENOBUFS` 또는 `SOCK_NOSPACE` 등 | kernel 메모리와 소켓 송신 버퍼를 구분 |

`/proc/net/netstat`의 `TcpExt:`에는 Linux 확장 계정이 있습니다. `ListenOverflows`는 accept queue 포화 관련 경로를, `ListenDrops`는 LISTEN 소켓에서의 더 넓은 drop 경로를 관측합니다. 두 값은 겹치므로 합하지 않습니다. `TCPSynRetrans`는 SYN 및 SYN/ACK 재전송, `TCPTimeouts`는 TCP 재전송 timeout 경로를 셉니다. `TCPTimeouts`를 애플리케이션 timeout이나 실패 연결 수와 일대일 대응시키지 않습니다. [확장 카운터 설명](https://docs.kernel.org/networking/snmp_counter.html), [6.12 TCP timer](https://github.com/torvalds/linux/blob/v6.12/net/ipv4/tcp_timer.c)

## 계산 예시: 재전송 비율은 손실 확률이 아니다

**가상 예시:** 같은 namespace·수명·60초 구간에서 `ΔOutSegs=12000`, `ΔRetransSegs=180`이면 송신 계정 대비 재전송 비율은 `180 / 12000 × 100 = 1.5%`, 재전송 발생률은 `180 / 60 = 3회/초`입니다. 이는 가상 입력이며 권장 임계값이 아닙니다.

이 비율을 “패킷 손실률 1.5%”로 표시하지 않습니다. 제어 세그먼트가 분모에 있고, 반복 재전송과 구간 이전에 보낸 데이터의 재전송이 분자에 들어올 수 있습니다. 수신 ACK 유실·순서 변경·spurious 재전송도 확인해야 합니다. 분모가 0이면 비율은 미정이며, 값이 100%를 넘었다고 자동으로 잘라내지 않습니다. 데이터만의 다른 비율을 정의하려면 `TCPOrigDataSent` 등으로 분모를 바꾼 **별도 지표**로 명명하고 SYN 재전송 포함 여부도 맞춥니다. [커널의 재전송·원본 데이터 구분](https://docs.kernel.org/networking/snmp_counter.html)

## 연결 하나를 더 자세히 읽기

다음은 **실행하지 않은 읽기 전용 예시**입니다. 현재 Linux network namespace에서 실행하며, 보통 일반 사용자로 통계 조회가 가능하지만 procfs 접근 정책·보안 설정에 따라 제한될 수 있습니다. 프로세스 소유자 표시나 다른 namespace 진입은 별도 권한이 필요합니다. `ss -K`처럼 소켓을 종료하는 옵션은 사용하지 않습니다. 전체 소켓 조회 비용은 소켓 수에 따라 커지므로 제품에서는 대상 필터와 주기를 둡니다.

```sh
cat /proc/net/snmp
cat /proc/net/netstat
ss -tin
```

`ss -ti`의 `rtt`는 평활 RTT와 편차(ms), `rto`는 재전송 timeout(ms), `cwnd`는 혼잡 윈도 크기(세그먼트 단위)입니다. 이들은 연결의 현재 상태이지 같은 길이의 구간 평균이 아닙니다. `retrans` 출력의 값도 단순한 비율이 아닙니다. iproute2의 `retrans:현재/누적` 표현은 `tcpi_retrans`와 `tcpi_total_retrans`에서 나오므로 해당 버전의 출력 형식과 소켓 수명을 확인합니다. [ss(8)](https://man7.org/linux/man-pages/man8/ss.8.html), [iproute2 v6.12.0 ss 출력 코드](https://git.kernel.org/pub/scm/network/iproute2/iproute2.git/tree/misc/ss.c?h=v6.12.0)

## 제품 적용 제안

헤더의 이름 목록과 다음 값 목록을 짝지어 파싱하고 열 번호를 고정하지 않습니다. 필드 추가·누락·행 길이 불일치를 별도로 기록합니다. `snmp6`의 이름-값 행 형식은 다른 parser로 취급합니다. Linux 출력은 [SNMP 출력 코드](https://github.com/torvalds/linux/blob/v6.12/net/ipv4/proc.c)에서 확인할 수 있으며, RFC의 Counter32 표기를 Linux proc 파일의 실제 저장 폭에 그대로 대입하지 않습니다.

재부팅·namespace 교체·관측 수명 불연속이면 새 기준점을 만듭니다. 값 감소 시 폭·연속성이 확인되지 않으면 wrap 보정을 추측하지 않습니다. 없는 필드를 0으로 채우지 않고 지원 여부와 수집 실패를 분리합니다. namespace 전체 이상에서 시작해 포트·소켓·프로세스로 좁혀 가되, 살아남은 소켓의 `ss` 표본만으로 이미 종료된 연결의 실패를 복원하지 않습니다.

카운터 감소만으로 wrap·reset을 구분하지 않습니다. 폭과 같은 namespace 수명, reset 부재, 구간 최대 증가량을 입증할 때만 [호스트 차분 계약](../host/collection-contracts.md)의 조건부 wrap 처리를 검토합니다. 그렇지 않으면 rate를 보류합니다.

## 심화: 커널 계수 지점과 버전 경계

`OutSegs`는 일반적인 데이터 재전송을 제외하는 계정이지만 “원본 데이터 패킷만”을 뜻하지 않습니다. Linux 6.12의 `__tcp_transmit_skb()`는 sequence 진행과 제어 세그먼트 조건으로 증가시키고, SYN/ACK 작성 경로는 별도로 증가시킵니다. offload의 GSO 분할 수를 반영하는 경로도 있습니다. RFC의 추상 정의를 커널 전체의 모든 경로에서 동일한 패킷 집합으로 단순화하지 않습니다. [고정 버전 송신 코드](https://github.com/torvalds/linux/blob/v6.12/net/ipv4/tcp_output.c)

`PassiveOpens`의 증가 지점은 `tcp_create_openreq_child()`입니다. 일반 handshake에서는 마지막 ACK를 처리하는 경로에서, TCP Fast Open에서는 더 일찍 child를 만들 수 있습니다. accept queue 포화로 child 생성 전에 빠지는 경로에서는 증가하지 않습니다. 커널 설명 문서의 SYN 수신 중심 설명보다 이 장의 고정 버전 구현을 우선하며 SYN 도착률로 사용하지 않습니다. [6.12 child 생성](https://github.com/torvalds/linux/blob/v6.12/net/ipv4/tcp_minisocks.c#L629), [accept queue 검사](https://github.com/torvalds/linux/blob/v6.12/net/ipv4/tcp_ipv4.c#L1757)

`CurrEstab`에 CLOSE-WAIT를 포함하는 수정은 upstream 6.10에 들어갔습니다. 수정 전 구현은 ESTABLISHED만 계정하며, 이전 stable 계열에도 backport되므로 minor 번호 하나로 의미를 결정하지 않습니다. 배포 커널의 수정 포함 여부를 확인합니다. [원 수정](https://github.com/torvalds/linux/commit/a46d0ea5c94205f40ecf912d1bb7806a8a64704f), [6.9 구현](https://github.com/torvalds/linux/blob/v6.9/net/ipv4/tcp.c#L2635), [6.10 구현](https://github.com/torvalds/linux/blob/v6.10/net/ipv4/tcp.c#L2647), [6.6 stable 구현](https://github.com/gregkh/linux/blob/linux-6.6.y/net/ipv4/tcp.c)

Linux 6.12의 주 수신 큐 실패 경로는 `RcvbufErrors` 또는 `MemErrors`와 함께 `InErrors`도 증가시킵니다. 이를 더해 “전체 오류”를 만들면 중복됩니다. 다만 multicast의 `skb_clone()` 실패도 `RcvbufErrors`를 증가시키므로 이 필드를 소켓 한도 초과의 전용 증거로 보지는 않습니다. 송신에서는 `ip_send_skb()`의 `-ENOBUFS`를 `IP_RECVERR` 비활성 조건에서 호출자에게 숨기면서 `SndbufErrors`만 올리는 경로도 있습니다. 반환 오류 수와 커널 계정 수가 항상 같지는 않습니다. [수신 큐 분기](https://github.com/torvalds/linux/blob/v6.12/net/ipv4/udp.c#L2065), [multicast 예외](https://github.com/torvalds/linux/blob/v6.12/net/ipv4/udp.c#L2284), [송신 분기](https://github.com/torvalds/linux/blob/v6.12/net/ipv4/udp.c#L983)

## 이해 확인

1. `CurrEstab`가 줄었으면 카운터 리셋인가? **아니다. 현재 연결 수 gauge다. CLOSE-WAIT 포함 여부는 upstream 6.10의 수정과 backport 여부를 확인한다.**
2. `RcvbufErrors`와 `InErrors`를 더해도 되는가? **같은 실패가 겹칠 수 있어 합산하면 안 된다.**
3. 재전송 비율 1.5%는 업무 요청의 실패율인가? **아니다. namespace의 세그먼트 계정 비율이며 요청과 대응하지 않는다.**
4. 같은 Pod의 두 컨테이너에서 읽은 namespace 카운터가 같으면 수집 오류인가? **namespace 공유로 같은 원천을 두 번 읽었을 수 있다.**

## 함께 읽기

[TCP와 UDP](tcp-and-udp.md) · [네트워크 지표](network-metrics.md) · [호스트 수집 계약](../host/collection-contracts.md) · [컨테이너 격리](../containers/isolation-and-lifecycle.md)

이전: [인터페이스, 장비, 흐름과 능동 검사](network-metrics.md) · 다음: [네트워크 장비 수집: SNMP, MIB와 인터페이스 수명](snmp-and-device-models.md) · [분야 목차](README.md)
