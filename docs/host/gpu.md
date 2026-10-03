# GPU와 가속기: 활동, 메모리와 분할

> 상태: 본문 초안 · 적용 범위: NVML R550의 활용률 정의, NVIDIA MIG·DCGM, AMD SMI API · 출처 확인일: 2026-10-03

GPU 사용률 100%는 이론 최대 연산량의 100%를 달성했다는 뜻으로 일반화할 수 없습니다. 먼저 어떤 엔진과 어느 시간 구간의 활동을 측정했는지 확인합니다.

## 활동 시간과 처리 효율

NVML R550의 `nvmlUtilization_t.gpu`는 표본 기간에 하나 이상의 kernel이 실행된 시간 비율입니다. `memory`는 device memory가 읽히거나 쓰인 시간 비율이며 사용 중인 메모리 용량의 비율이 아닙니다. 이 장은 해당 릴리스의 정의를 명시적으로 사용합니다. [NVML R550 utilization structure](https://docs.nvidia.com/deploy/archive/R550/nvml-api/structnvmlUtilization__t.html)

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

AMD SMI의 `amdsmi_get_gpu_activity`도 graphics·memory·multimedia 엔진 활동을 구분하며 지원되지 않는 경우를 반환할 수 있습니다. 이 API의 VM guest 지원 범위는 공식 설명을 확인해야 합니다. NVIDIA 지표와 단순 이름 치환을 하지 않습니다. [AMD SMI Python API](https://rocm.docs.amd.com/projects/amdsmi/en/latest/reference/amdsmi-py-api.html#amdsmi_get_gpu_activity)

## 가상 분석

GPU 활동은 낮고 업무 지연은 높다면 CPU 전처리, 데이터 읽기, batch 형성 대기와 장치로의 복사를 조사합니다. GPU 활동이 높은데 처리율이 낮다면 메모리 대역폭·연산 유형·통신·실행 구성을 비교합니다. 높은 온도나 전력 제한과 성능 변화가 함께 보인다면 장치가 보고한 제한 사유를 확인하고 추측과 사실을 구분합니다.

## 제품 설계

값마다 장치 모델, 드라이버·라이브러리 버전, 단위, 표본 기간, 물리·분할·프로세스 범위를 명시합니다. 지원 안 함과 실제 활동 0을 구별합니다. GPU를 사용하는 프로세스와 컨테이너·Pod를 연결할 때는 [프로세스 식별 수명](processes.md)과 [컨테이너 격리](../containers/isolation-and-lifecycle.md)를 함께 확인합니다.

## 이해 확인

1. GPU 활동 100%는 최대 FLOPS 달성인가? **그 지표만으로는 알 수 없습니다.**
2. memory activity는 VRAM 용량 사용률인가? **NVML의 해당 필드에서는 다른 의미입니다.**
3. 미지원 지표를 0으로 채워도 되는가? **관측 불가를 유휴 상태로 잘못 표현합니다.**

관련: [호스트 목차](README.md) · [애플리케이션](../application/README.md)
