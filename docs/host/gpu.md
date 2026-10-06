# GPU와 가속기: 활동, 메모리와 분할

> 상태: 검토됨 · 적용 범위: NVML R550의 활용률 정의, NVIDIA MIG·DCGM, AMD SMI API · 출처 확인일: 2026-10-03 · 편집 검토일: 2026-10-04 · 3d 원천·저장 증거 확인: 2026-10-06

## 먼저 이해할 것

GPU는 많은 연산을 병렬로 처리하도록 구성된 장치입니다. GPU가 활동한 시간, 장치 메모리 용량, 메모리 전송 활동은 다른 값입니다. 가득 찬 책상이 항상 바쁜 작업자를 뜻하지 않듯이 VRAM 점유율이 높다고 GPU 계산량도 높다고 알 수 없습니다. 장치·분할 방식과 원천 지표의 정의를 먼저 확인합니다.

GPU 사용률 100%는 이론 최대 연산량의 100%를 달성했다는 뜻으로 일반화할 수 없습니다. 먼저 어떤 엔진과 어느 시간 구간의 활동을 측정했는지 확인합니다.

## 활동 시간과 처리 효율

NVML R550의 `nvmlUtilization_t.gpu`는 표본 기간에 하나 이상의 kernel이 실행된 시간 비율입니다. `memory`는 device memory가 읽히거나 쓰인 시간 비율이며 사용 중인 메모리 용량의 비율이 아닙니다. 이 장은 해당 릴리스의 정의를 명시적으로 사용합니다. [NVML R550 utilization structure](https://docs.nvidia.com/deploy/nvml-api/latest/api/structnvmlUtilization__t.html)

합성 예에서 1초 동안 어떤 kernel이 계속 실행됐더라도 연산 유닛을 얼마나 효율적으로 사용했는지는 이 시간 비율만으로 알 수 없습니다. 반대로 VRAM 80 GiB 중 60 GiB를 사용했다면 용량 비율은 75%이며 memory activity 75%와 다른 값입니다.

| 관측 축 | 단위 예 | 질문 |
| --- | --- | --- |
| 엔진 활동 | % 또는 비율 | 관측 기간 중 얼마나 활동했는가 |
| 메모리 용량 | bytes | 얼마나 확보·사용했는가 |
| 메모리·링크 처리량 | bytes/s | 데이터가 얼마나 이동했는가 |
| 전력·온도 | W, °C | 자원·열 조건은 어떠한가 |
| 작업 성능 | samples/s, tokens/s 등 | 실제 업무를 얼마나 처리했는가 |

표의 업무 단위는 제품과 애플리케이션이 정의해야 합니다. 서로 다른 모델·batch·입력 길이의 처리율을 같은 조건의 성능처럼 비교하지 않습니다.

## 분할 장치와 물리 장치

MIG는 지원되는 GPU의 계산·메모리 자원을 여러 GPU 인스턴스로 나누는 기능입니다. 물리 장치 전체와 분할 인스턴스의 자원 범위를 구분해야 합니다. [NVIDIA MIG Introduction](https://docs.nvidia.com/datacenter/tesla/mig-user-guide/latest/introduction.html)

제품에는 물리 GPU 식별, 인스턴스 식별, 프로파일과 유효 시점을 별도로 보관하도록 제안합니다. 분할을 재구성했을 때 이전 인스턴스의 사용률을 새 인스턴스에 이어 붙이지 않습니다. 전체 장치와 하위 인스턴스 값을 단순 합산하는 것도 피합니다.

## 자세한 프로파일링과 가용성

DCGM의 profiling은 하드웨어 카운터로 더 자세한 활동을 관측합니다. 지원 조합에는 하드웨어·소프트웨어 제약이 있고 다른 NVIDIA 개발 도구의 프로파일링과 충돌할 수 있습니다. 기본 상태 수집과 고급 프로파일링을 같은 가용성으로 취급하지 않습니다. [NVIDIA DCGM Profiling](https://docs.nvidia.com/datacenter/dcgm/latest/learn/modules/profiling.html)

AMD SMI의 `amdsmi_get_gpu_activity`도 graphics·memory·multimedia 엔진 활동을 구분하며 지원되지 않는 경우를 반환할 수 있습니다. 연결한 공식 Python API 문서는 이 함수가 **virtual machine guest에서 지원되지 않는다**고 명시합니다. 해당 조건의 미지원을 0% 활동으로 변환하지 않습니다. NVIDIA 지표와 단순 이름 치환을 하지 않습니다. [AMD SMI Python API](https://rocm.docs.amd.com/projects/amdsmi/en/latest/reference/amdsmi-py-api.html#amdsmi-get-gpu-activity)

## DCGM 프로파일링: 활동 시간과 warp 점유는 다르다

**보강 확인: 2026-10-05.** 다음 필드 이름·ID는 DCGM v4.0.0 header에 고정했습니다. SM은 GPU의 연산 실행 단위, warp는 함께 실행하도록 묶인 스레드 집합입니다. 아래 ratio는 측정 구간 평균이며 순간값이나 요청별 trace가 아닙니다. [고정 header](https://github.com/NVIDIA/DCGM/blob/v4.0.0/dcgmlib/dcgm_fields.h), [DCGM profiling 정의](https://docs.nvidia.com/datacenter/dcgm/latest/learn/modules/profiling.html)

| 필드·ID | 무엇을 나누어 계산하는가 | 혼동하지 않을 것 |
| --- | --- | --- |
| `DCGM_FI_PROF_SM_ACTIVE`·1002 | SM에 적어도 하나의 warp가 active인 시간 비율을 SM 전체에 평균 | active에는 메모리 요청을 기다리는 warp도 포함; 실제 연산 발행률과 다름 |
| `DCGM_FI_PROF_SM_OCCUPANCY`·1003 | resident warp 수 / 하드웨어가 지원하는 최대 동시 warp 수의 시간 평균 | 점유가 높다고 반드시 처리율이 높은 것은 아님 |
| `DCGM_FI_PROF_PIPE_TENSOR_ACTIVE`·1004 | tensor pipe 활동 cycle의 비율 | tensor 연산 활동이며 모든 종류의 연산 성능이 아님 |
| `DCGM_FI_PROF_DRAM_ACTIVE`·1005 | 장치 메모리 interface가 송수신 중인 cycle의 비율 | VRAM 할당 용량도 실제 byte/s도 아님 |

확인일의 공식 latest 문서는 같은 ID를 SM_UTIL_RATIO·SM_OCCUPANCY_RATIO·TENSOR_UTIL_RATIO·DRAM_UTIL_RATIO 이름으로도 설명합니다. 공식 header에는 기존 이름의 alias가 있으나, 이름 변경의 최초 릴리스를 이 장에서 확정하지 않습니다. adapter는 설치된 DCGM header·버전·field metadata로 이름과 단위를 확인해야 합니다. [공식 header의 alias](https://github.com/NVIDIA/DCGM/blob/master/dcgmlib/dcgm_fields.h)

NVML GPU utilization은 측정 구간에 kernel이 하나라도 실행된 시간의 비율입니다. 이를 모든 SM이 얼마나 채워졌는지를 보여 주는 위 지표와 동일시하지 않습니다. 활동률·occupancy가 높아도 메모리 대기·명령 조합·동기화로 업무 처리율이 낮을 수 있습니다. [NVML utilization 정의](https://docs.nvidia.com/deploy/nvml-api/group__nvmlDeviceQueries.html)

프로파일링은 지원 GPU·권한·동시에 수집 가능한 counter group을 확인해야 합니다. Nsight 등과 counter 자원이 충돌할 수 있고, pause 동안의 blank는 활동 0이 아닙니다. 조회·watch도 측정 비용이 있으며 profiler pause/resume은 다른 수집기에 영향을 주는 상태 변경입니다. 이 장에서는 GPU 조회·프로파일링·부하 생성 명령을 실행하지 않았습니다.

## Xid, ECC, row remapping과 클럭 제한

Xid는 NVIDIA driver가 kernel/event log에 남기는 오류 보고 코드입니다. 하드웨어·driver·애플리케이션 문제의 단서이지, 모든 Xid가 GPU 물리 고장이라는 판정은 아닙니다. 로그 시각·GPU UUID/PCI 주소·driver·프로세스 수명과 코드별 조사를 연결합니다. 동일 코드의 반복과 서로 다른 오류 수를 구분하며 누락된 로그를 정상으로 보지 않습니다. [Xid 소개](https://docs.nvidia.com/deploy/xid-errors/latest/introduction.html), [로그 식별](https://docs.nvidia.com/deploy/xid-errors/latest/working-with-xid-errors.html)

ECC는 correctable/uncorrectable, DRAM/SRAM 등의 위치, volatile/aggregate 범위를 함께 봅니다. volatile은 driver load 이후 수명이며 단순 호스트 부팅 이후로 고정하면 안 됩니다. aggregate도 초기화 기능·지원 조건을 확인합니다. row remapping은 문제가 있는 메모리 행을 예비 행으로 대체하는 기능으로, 오류 수와 교체된 행 수는 다른 값입니다. 지원 장치에서 pending·실패 여부·예비 행 가용성을 함께 읽고 reset 필요 상태를 표시합니다. 모니터링이 자동으로 GPU reset을 실행하는 의미는 아닙니다. [nvidia-smi ECC·Row Remapper](https://docs.nvidia.com/deploy/nvidia-smi/index.html)

Clock event reason(구 throttle reason)은 GPU idle, software power cap, thermal slowdown, external power brake, sync boost 등 클럭이 제한되는 조건을 구분합니다. idle도 이유가 될 수 있으므로 모든 활성 bit를 과열로 표시하지 않습니다. 현재 bitmask와 이유별 누적 지속 시간은 다른 형태이며 여러 이유의 시간이 겹칠 수 있습니다. 또한 nvidia-smi 문서의 reason counter는 µs, 최신 NVML Field Value Enums의 해당 시간 필드는 ns로 정의되므로 원천 API별 단위를 확인합니다. [nvidia-smi Clock Event Reasons](https://docs.nvidia.com/deploy/nvidia-smi/index.html), [NVML field 단위](https://docs.nvidia.com/deploy/nvml-api/latest/api/group__nvmlFieldValueEnums.html)

제품 적용 제안: 용량·activity·occupancy·처리율·오류·clock reason을 다른 화면 축으로 두고, 지원 상태·실제 field ID·단위·계정 수명·GPU/MIG 범위를 보존합니다. ECC나 Xid 한 숫자만으로 원인·교체 결정을 자동 확정하지 않습니다.

## 가상 분석

GPU 활동은 낮고 업무 지연은 높다면 CPU 전처리, 데이터 읽기, batch 형성 대기와 장치로의 복사를 조사합니다. GPU 활동이 높은데 처리율이 낮다면 메모리 대역폭·연산 유형·통신·실행 구성을 비교합니다. 높은 온도나 전력 제한과 성능 변화가 함께 보인다면 장치가 보고한 제한 사유를 확인하고 추측과 사실을 구분합니다.

## 제품 설계

값마다 장치 모델, 드라이버·라이브러리 버전, 단위, 표본 기간, 물리·분할·프로세스 범위를 명시합니다. 지원 안 함과 실제 활동 0을 구별합니다. GPU를 사용하는 프로세스와 컨테이너·Pod를 연결할 때는 [프로세스 식별 수명](processes.md)과 [컨테이너 격리](../containers/isolation-and-lifecycle.md)를 함께 확인합니다.

## 이해 확인

1. GPU 활동 100%는 최대 FLOPS 달성인가? **그 지표만으로는 알 수 없습니다.**
2. memory activity는 VRAM 용량 사용률인가? **NVML의 해당 필드에서는 다른 의미입니다.**
3. 미지원 지표를 0으로 채워도 되는가? **관측 불가를 유휴 상태로 잘못 표현합니다.**
4. SM_ACTIVE와 SM_OCCUPANCY는 같은 값인가? **warp가 하나라도 active인 시간과 최대 대비 resident warp 비율은 다릅니다.**
5. clock reason이 켜져 있으면 과열인가? **idle·전력 등 다른 사유도 있으므로 bit별 의미를 봐야 합니다.**

관련: [호스트 목차](README.md) · [애플리케이션](../application/README.md)
