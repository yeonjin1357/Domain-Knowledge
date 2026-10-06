# 시간과 관측 데이터의 품질

> 상태: 검토됨 · 적용 범위: 수집 시각, 지연, 누락, 중복, 시계 · 원천 확인일: 2026-10-06 · 실습 여부: 저장된 로컬 실행 근거 포함; 구성·한계는 본문

## 먼저 이해할 것

사진을 찍은 시각과 사진을 받은 시각은 다를 수 있습니다. 모니터링 데이터도 발생·관측·수신·조회 시각이 다를 수 있습니다. 늦게 도착한 과거 값을 지금의 상태처럼 보여 주거나, 기록이 없는 구간을 0으로 채우면 장애 분석이 달라집니다. 이 장은 숫자 자체보다 먼저 확인해야 할 시간과 품질을 설명합니다.

관측 데이터는 사건 그 자체가 아니라 사건의 일부를 특정 위치와 시각에서 기록한 결과입니다. 장애 분석에서는 값뿐 아니라 기록이 어떻게 도착했는지도 알아야 합니다.

## 사건 시각과 수집 시각

OpenTelemetry 로그 모델은 사건이 발생한 시각인 `Timestamp`와 수집 체계가 그 사건을 관측한 시각인 `ObservedTimestamp`를 구분합니다. 원천 사건 시각을 모르면 해당 값이 없을 수도 있습니다. [OpenTelemetry Logs Data Model](https://opentelemetry.io/docs/specs/otel/logs/data-model/)

가상 예시는 다음과 같습니다.

| 사건 | 원천 시각 | 수집기가 읽은 시각 | 조회 가능 시각 |
| --- | --- | --- | --- |
| 요청 실패 | 10:00:00 | 10:00:02 | 10:00:04 |
| 처리 지연 로그 | 10:00:01 | 10:00:08 | 10:00:09 |

도착 순서만으로 사건 순서를 정하면 늦게 도착한 기록을 뒤의 사건으로 잘못 볼 수 있습니다. 반대로 여러 호스트의 원천 시계가 어긋나 있다면 원천 시각만으로 정확한 인과 순서를 정할 수도 없습니다.

제품 설계에서는 원천 시각을 보존하고, 수집·저장·조회 시각을 별도 진단 정보로 기록하는 방식을 검토합니다. 모든 데이터에 같은 필드가 있다고 가정하지 말고 실제 확보한 시각의 의미를 명시합니다.

## 벽시계와 경과 시간

Linux의 `CLOCK_REALTIME`은 시스템의 실제 시각을 나타내며 설정 변경의 영향을 받을 수 있습니다. `CLOCK_MONOTONIC`은 벽시계의 불연속 변경으로 역행하지 않는 시간 기준입니다. 시스템 일시 정지의 포함 여부 등은 시계 종류에 따라 다릅니다. [Linux clock_gettime](https://man7.org/linux/man-pages/man2/clock_gettime.2.html)

역행하지 않는다는 것은 속도가 항상 일정하거나 실제 시간과 완전히 일치한다는 뜻은 아닙니다. `CLOCK_MONOTONIC`은 NTP 등의 주파수 조정을 받으며 `CLOCK_MONOTONIC_RAW`는 이 조정을 받지 않습니다. 둘 다 Linux에서는 suspend 시간을 포함하지 않습니다. RAW는 조정하지 않은 비교 기준이지, 별도 교정 없이 정확한 외부 시간으로 간주할 기준은 아닙니다. [시계별 규약](https://man7.org/linux/man-pages/man2/clock_gettime.2.html)

**제품 적용 제안:** VM·WSL에서 CPU rate 등의 분모가 예상과 다르면 사용한 시계 종류, 같은 구간의 MONOTONIC·RAW, 스레드 수와 시간 조정 상태를 보존합니다. [Linux 시계 실습](../host/linux-observation-lab.md)은 분모 시계의 주파수 조정으로 CPU/MONOTONIC > 1이 나올 수 있음을 보여 줍니다. 시계 차이를 CPU 계정 오류나 특정 동기화 서비스의 책임으로 바로 바꾸지 않습니다.

같은 프로세스에서 작업 시간을 재는 코드에는 경과 시간 측정에 적합한 시계를 사용하고, 사건을 다른 시스템과 연결할 때는 원천 시각과 시간 동기화 상태를 고려합니다. 이것은 OS 시계의 성질에 근거한 구현 제안입니다.

가상 예시로 원천 시계가 수집기보다 5초 빠르면, 실제 전송에 1초가 걸려도 `수집 시각 - 원천 시각 = -4초`로 보일 수 있습니다. 음수 차이는 곧바로 전송 로직의 오류를 뜻하지 않습니다. 시계 차이와 필드 정의부터 확인합니다.

## 0과 데이터 없음은 다르다

| 관측 상태 | 의미 | 표시 제안 |
| --- | --- | --- |
| 정상 수집된 0 | 정의한 측정에서 값이 실제 0 | 0과 관측 시각 표시 |
| 수집 실패 | 대상의 실제 값은 모름 | 수집 실패 표시 |
| 미지원 | 그 방식으로 해당 항목을 제공하지 않음 | 지원 범위 표시 |
| 권한 부족 | 제공 가능하나 조회할 수 없음 | 권한 상태 표시 |
| 대상 종료 | 해당 실행 대상의 수명이 끝남 | 종료 시각과 과거 이력 유지 |
| 오래된 값 | 새 표본을 얻지 못했지만 이전 값이 남음 | 값의 나이와 최신성 표시 |

Prometheus의 즉시 조회에는 Lookback과 Staleness 규칙이 있습니다. 특정 시각의 조회 결과가 반드시 그 시각에 새로 수집된 표본은 아닙니다. 조회 엔진의 규칙과 실제 표본 시각을 함께 이해해야 합니다. [Prometheus Staleness](https://prometheus.io/docs/prometheus/latest/querying/basics/#staleness)

화면에서 마지막 값을 계속 유지하는 동작은 사용성상 선택할 수 있으나, 언제까지 유효한지 숨기지 않는 편이 좋습니다. 이 정책은 제품마다 정해야 하며 도구의 기본 동작을 다른 시스템에 그대로 일반화하지 않습니다.

## 수집 간격과 평가 구간

수집 간격은 새 값을 얻는 빈도이고, 평가 구간은 계산에 사용하는 시간 범위입니다. 15초마다 읽은 누적값으로 5분 평균 증가율을 계산할 수 있습니다. 그래프 표시 간격은 다시 별개의 선택입니다.

다음은 원리 설명용 가상 예시입니다. 60초 동안 총 600건이 발생했다면 평균은 10건/초입니다. 그러나 첫 1초에 600건이 몰렸는지, 매초 10건씩 들어왔는지는 총량만으로 알 수 없습니다. 장기 평균만 보관한 데이터로 짧은 과부하를 복원할 수 없습니다.

동일한 평균 지표도 수집 시점, 구간 경계, 반올림, 누락 정책이 다르면 숫자가 다르게 보일 수 있습니다. 먼저 두 지표의 정의를 맞춘 뒤 제품 오류 여부를 조사합니다.

## 중복과 늦은 데이터

수집기가 실패 후 재전송할 때 같은 이벤트가 중복 도착할 수 있는지는 실제 전송 계약에 달려 있습니다. 한 번만 도착한다고 가정해서는 안 되며, 재전송된 데이터가 이미 처리된 것인지 판단할 근거를 설계해야 합니다.

| 데이터 | 중복 판단을 설계할 때 볼 정보 |
| --- | --- |
| 구간 메트릭 | 대상·지표·속성·구간·생산자 수명 |
| 로그 | 원천 식별자, 파일 위치 또는 이벤트 식별 정보 |
| 트레이스 | Trace ID, Span ID, 갱신 의미 |

이 표는 범용 식별자를 확정한 명세가 아니라 설계 질문입니다. 같은 시각과 메시지를 가진 서로 다른 정상 로그도 있으므로 문자열과 시각만으로 무조건 제거하지 않습니다. 중복 제거 범위와 원천의 보장 수준을 먼저 정합니다.

늦은 데이터가 도착하면 과거 그래프가 갱신될 수 있습니다. 알림을 다시 평가할지, 보고서를 확정한 뒤 수정할지, 허용 지연을 넘긴 데이터를 어떻게 다룰지도 저장·조회 정책에 포함합니다.

## 분석에서 확인할 순서

1. 대상과 지표 정의가 일치하는지 확인합니다.
2. 원천 시각, 최신성, 수집 성공 여부를 봅니다.
3. 같은 단위·조회 구간·집계 방식으로 비교합니다.
4. 데이터가 누락·중복·지연되었는지 조사합니다.
5. 그 다음 시스템의 실제 변화에 대한 가설을 세웁니다.

## 심화: 시계 동기화 진단

서버 A의 로그가 서버 B보다 먼저 찍혔다는 이유만으로 A의 사건이 먼저였다고 할 수는 없습니다. 시계의 현재 차이인 **offset**과 시계가 빠르거나 느리게 흐르는 정도인 **frequency**를 구분해야 합니다. 이 절은 chrony 4.9·systemd 문서와 LinuxPTP v4.4 코드를 2026-10-06 확인했습니다. chrony·PTP 진단은 실행하지 않았고, timesyncd의 읽기 전용 상태 조회는 아래 저장 실습으로 구분합니다. [chrony 릴리스](https://chrony-project.org/news.html)

| 원천 | 값·단위 | 해석 |
| --- | --- | --- |
| `chronyc tracking`: System time | 초, fast/slow 방향 | chronyd가 유지하는 NTP 시계와 시스템 시계 사이에 남은 차이 |
| Last offset / RMS offset | 초 | 마지막 갱신의 추정 offset / 장기 offset 통계; System time과 같은 기준으로 혼합하지 않음 |
| Frequency | ppm | 보정하지 않았다면 시스템 시계가 얼마나 빨리·느리게 갈지의 추정 |
| Skew | ppm | 주파수 추정의 오차 범위; 현재 시각의 오차를 초로 나타낸 값이 아님 |
| Root delay / dispersion, Leap status | 초 / 상태 | 기준 시계까지 경로·불확실성과 동기화 상태를 함께 확인 |

`tracking`의 모든 offset이 곧 현재 시스템 시계 오차는 아닙니다. 참조 시계의 정확성·네트워크 비대칭·측정 경과 시간도 있어, “동기화됨”을 외부 정확도의 교정 증명으로 쓰지 않습니다. [chrony 4.9 tracking](https://chrony-project.org/doc/4.9/chronyc.html#tracking)

`timedatectl timesync-status`와 `show-timesync`는 systemd-timesyncd의 상태를 읽습니다. chronyd나 외부 VM 시계 관리자의 상태를 모두 설명하는 공통 API가 아닙니다. 서비스 부재·D-Bus 접근 실패는 offset 0으로 저장하지 않습니다. [systemd timedatectl](https://www.freedesktop.org/software/systemd/man/latest/timedatectl.html)

PTP 환경은 하드웨어 시계(PHC)와 시스템 시계의 경로를 구분합니다. LinuxPTP v4.4의 `ptp4l` slave 경로는 local 수신 시각 t2−master 전송 시각 t1에서 경로 delay를 뺀 값을 master_offset으로 계산해 offsetFromMaster와 로그에 사용합니다. 하드웨어 timestamp 모드에서는 해당 PHC 경로의 값이며, `phc2sys`는 시계 사이를 동기화합니다. 한쪽 offset이 작다고 다른 쪽도 정확하다고 볼 수 없습니다. phc2sys 요약의 offset·읽기 delay는 ns, frequency는 ppb입니다. UTC/PTP 시간 척도와 source→sink 방향도 남깁니다. [ptp4l 설정](https://www.linuxptp.org/documentation/ptp4l/), [v4.4 offset 계산](https://github.com/richardcochran/linuxptp/blob/v4.4/tsproc.c), [clock_synchronize·로그](https://github.com/richardcochran/linuxptp/blob/v4.4/clock.c), [phc2sys](https://www.linuxptp.org/documentation/phc2sys/)

### Step·slew·leap smear

step은 시계 값을 불연속적으로 바꾸고 slew는 시계 속도를 조정하여 차이를 줄입니다. `CLOCK_REALTIME`은 두 영향을 받을 수 있으며 REALTIME 두 시각의 차이를 무조건 경과 시간으로 쓰지 않습니다. leap smear는 윤초를 일정 구간에 분산해 시간 척도를 부드럽게 조정하는 정책입니다. 서로 다른 smear 정책이나 smear·비smear source를 섞으면 의도된 시각 차이를 장애로 오인할 수 있습니다. smear를 모든 NTP 동기화의 기본 동작으로 가정하지 않습니다. [clock_gettime](https://man7.org/linux/man-pages/man2/clock_gettime.2.html), [chrony 4.9 leap 정책](https://chrony-project.org/doc/4.9/chrony.conf.html#leapsecmode)

읽기 전용 수집 예시는 `chronyc tracking`, `chronyc sources -v`, `timedatectl show-timesync --all`입니다. 해당 daemon·조회 socket 접근이 필요하며 상태 조회 자체는 시계를 조정하지 않습니다. 빈번한 호출 비용은 수집 주기로 제한합니다. PTP는 이미 동작 중인 서비스의 로그·관리 인터페이스 읽기를 설계하며, 모니터링 목적으로 ptp4l/phc2sys를 새로 실행하면 시계 제어가 발생할 수 있으므로 이 절의 읽기 예시에 포함하지 않습니다.

**제품 적용 제안:** offset·frequency·불확실성·최근 갱신 시각·참조원·시간 척도·가용성을 데이터 품질에 연결합니다. 서로 다른 호스트의 시각 차이가 불확실성 범위 안이면 사건 순서를 확정하지 않습니다. MONOTONIC/RAW 관측은 경과 시계의 속도 차이를 보여 주며 NTP offset 하나와 같은 값이 아닙니다. tick을 설정한 주체는 그 근거 없이는 지정하지 않습니다.

**저장된 실습 결과(2026-10-05 WSL2 Linux 6.18.33.2):** 2초 sleep 구간의 MONOTONIC은 2.000092274초, RAW는 2.076169165초로 비율은 약 0.963357이었습니다. 전후 adjtimex는 tick 9,634 µs, freq −42.834381 ppm으로 같았습니다. 이어진 timedatectl show는 NTPSynchronized=yes, timesync-status는 offset +873.315 ms를 보고했습니다. 서로 다른 시점·원천의 값이며, 동기화 상태 yes가 현재 offset 0이나 외부 정확도 인증을 의미하지 않습니다. 이 결과도 tick 설정 주체를 식별하지는 않습니다. [시계 요약과 원자료 hash](../../labs/results/1.1-r3/clock-state.json), [timesync-status 원문 gzip](../../labs/results/1.1-r3/clock-state.raw/command-003.gz)

2026-10-04의 MONOTONIC/RAW 약 0.937과 이 실행의 약 0.963357은 다른 날짜·조정 상태의 표본입니다. 앞 실행의 idle tick은 9,353–9,371 µs, 뒤 실행은 9,634 µs였으므로 두 비율을 같은 조건의 상수로 비교하지 않습니다. 앞 실행의 세부 수치는 [Linux 시계 실습](../host/linux-observation-lab.md)에 모았습니다.

## 이해 확인

- chrony Skew가 1 ppm이면 현재 시각이 1 ms 어긋났는가? **주파수 추정의 불확실성과 현재 시각 차이는 다른 값입니다.**
- ptp4l의 offset만 작으면 시스템 CLOCK_REALTIME도 정확한가? **PHC·시스템 시계의 연결과 기준원·시간 척도를 함께 확인해야 합니다.**
- 전송 지연을 계산했더니 음수이면 데이터가 시간을 거슬러 이동했는가? **서로 다른 시계의 오차와 timestamp의 의미를 먼저 확인해야 한다.**
- 60초 동안 600건이면 매초 10건씩 처리했는가? **구간 평균은 10건/초지만 내부의 발생 분포는 알 수 없다.**
- 마지막 값이 화면에 보이면 최근에도 수집에 성공했는가? **조회 시각과 마지막 실제 표본 시각을 구분해야 한다.**

관련: [시계열](time-series.md), [도메인 간 분석](../cross-domain/README.md), [제품 자체의 관측](../product/README.md)

이전: [서비스 수준 지표와 오류 예산](service-level-objectives.md) · 다음: [숫자가 다를 때: 측정 경계, 시간 구간과 오차](measurement-and-comparability.md) · [분야 목차](README.md)
