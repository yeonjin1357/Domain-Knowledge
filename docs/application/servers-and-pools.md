# 웹 서버와 연결 풀: 요청이 기다리는 여러 장소

> 상태: 검토됨 · 적용 범위: Tomcat 10.1, HikariCP·Spring Boot 공식 문서의 개념 · 검토일: 2026-10-04 · 실제 JVM 서버 실험 없음

웹 서버가 요청을 받았다고 즉시 업무 코드가 실행되는 것은 아닙니다. 실행 스레드, DB 연결, 외부 HTTP 연결 등을 기다릴 수 있습니다. 대기 장소를 하나로 뭉쳐 “서버 처리 시간”이라고 표시하면 어디에서 시간을 줄여야 하는지 알기 어렵습니다.

## 한 요청의 가상 시간표

```text
연결 수락 → 요청 처리 시작 → DB 연결 획득 → 쿼리 실행 → 응답 전송
              └ 작업 실행 대기 ┘   └ DB 내부 대기·실행 ┘
```

그림의 각 구간은 계측 위치에 따라 다르게 보입니다. DB 드라이버 span이 연결 풀 대기를 포함하는지 실제 계측 라이브러리의 정의를 확인해야 합니다. 가상 요청의 전체 500ms 중 pool 대기 300ms, DB 호출 150ms, 나머지 50ms라면 DB 내부를 2배 빠르게 만들어도 pool 대기를 그대로 둘 때 전체는 425ms입니다. 더 나아가 pool 대기 자체가 DB 지연에서 유발되었다면 독립적인 상수로 남지 않을 수 있으므로 이 산술은 고정 조건 예시입니다.

## Tomcat의 세 가지 한도

Tomcat HTTP connector의 `maxThreads`, `maxConnections`, `acceptCount`는 같은 개수를 다른 이름으로 부르는 것이 아닙니다. 처리 스레드, 서버의 연결 처리 한도, OS 연결 대기열과 관련된 경계가 다릅니다. 해당 connector에 Executor를 연결하면 connector의 `maxThreads`는 무시되고 Executor가 스레드를 관리합니다. 설정값은 보존되더라도 JMX 등에는 사용되지 않음을 뜻하는 `-1`로 보고됩니다. [Tomcat 10.1 HTTP Connector](https://tomcat.apache.org/tomcat-10.1-doc/config/http.html)

keep-alive 연결이 많다는 사실만으로 같은 수의 업무 요청이 CPU에서 실행 중이라고 계산하지 않습니다. 비동기 Servlet이나 가상 스레드 사용 등 실행 방식이 달라지면 스레드 수의 의미도 확인합니다. 제품은 연결 수, 현재 처리 요청, executor 작업 수, 거절·timeout을 서로 다른 지표로 둡니다.

## DB 연결 풀의 의미

연결 풀은 DB 연결을 매번 새로 만들지 않고 재사용하도록 관리합니다. HikariCP의 `maximumPoolSize`는 idle과 사용 중 연결을 합친 최대 크기이며, 풀이 한도에 도달해 사용할 연결이 없으면 `getConnection()`이 최대 `connectionTimeout` 동안 대기합니다. 이 timeout은 SQL 문장의 실행 시간 제한과 다릅니다. [HikariCP 설정](https://github.com/brettwooldridge/HikariCP#gear-configuration-knobs-baby)

| 상태 | 입문용 뜻 | 중요한 후속 질문 |
| --- | --- | --- |
| active | 애플리케이션이 빌려 간 연결 | 실제 SQL 실행 중인가, 앱이 다른 작업을 기다리는가? |
| idle | 풀 안에서 대기하는 연결 | 다음 요청이 재사용할 수 있는 유효 연결인가? |
| pending | 연결을 빌리려고 기다리는 작업 | 얼마나 오래 기다리고, 결국 성공·실패하는가? |
| acquisition time | 연결을 얻기까지의 시간 | 생성·검증·대기 등 실제 계측 범위는 무엇인가? |
| usage time | 빌려 간 뒤 반환하기까지의 시간 | 트랜잭션과 외부 호출이 포함되는가? |

active의 구체적인 정의와 지원 항목은 풀 구현마다 확인합니다. Spring Boot는 지원 DataSource에 `jdbc.connections` 계열의 active·idle·max·min gauge를 제공하고 Hikari 전용 지표도 연동할 수 있습니다. 내보내는 backend에 따라 이름 표현이 달라질 수 있어 내부 meter 이름과 최종 지표 이름을 동일하다고 하드코딩하지 않습니다. [Spring Boot DataSource metrics](https://docs.spring.io/spring-boot/reference/actuator/metrics.html#actuator.metrics.supported.jdbc)

## 풀 크기를 늘릴 때의 조건

가상으로 인스턴스 10개가 각각 최대 30개 DB 연결을 사용하면 설정상 최대 합계는 300개입니다. DB의 접속 한도에는 관리·복제·다른 앱도 사용할 몫이 있으므로 300개를 전부 사용해도 안전한지는 별도 검토입니다. autoscaling으로 인스턴스가 20개가 되면 같은 설정으로 최대 600개가 됩니다.

큰 풀은 대기를 줄일 수 있지만 DB 내부 경합과 메모리 사용을 늘릴 수도 있습니다. 먼저 연결 보유 시간이 왜 긴지 확인합니다. 트랜잭션 중 외부 HTTP 응답을 기다리거나 연결을 반환하지 않은 상황이라면 pool 크기만 변경해 원인을 해결했다고 판단하지 않습니다.

## 가상 조사 절차

1. 요청 지연·오류·유입률에서 영향을 확인합니다.
2. 풀 pending과 acquisition 분포를 봅니다.
3. active가 높으면 DB 세션 state·wait·트랜잭션 나이를 연결합니다.
4. DB가 한가하면 연결 반환 누락·앱 외부 대기·스레드 상태 가설을 확인합니다.
5. 설정·배포·인스턴스 수 변경 시점을 비교합니다.

이 절차는 진단 순서 예시입니다. active=max라는 조건만으로 DB CPU 부족이나 연결 누수를 확정하지 않습니다. leak detector의 긴 보유 경고도 의도된 긴 트랜잭션인지 추가 해석이 필요합니다.

## 제품 적용 제안과 이해 확인

풀은 서비스·실행 인스턴스·풀 이름·대상 DB의 관계로 관리합니다. 접속 URL의 비밀번호와 토큰을 label로 내보내지 않습니다. 업무 요청별 대기와 DB 전체 부하를 같은 시간창에서 탐색하도록 연결합니다.

1. pool active 30이면 SQL 30개가 실행 중인가? **빌려 간 연결과 현재 실행 중인 문장은 다릅니다.**
2. connectionTimeout은 쿼리 timeout인가? **연결 획득 대기 한도입니다.**
3. 앱 인스턴스만 늘리면 DB 연결 부담도 그대로인가? **인스턴스별 pool 한도가 합쳐질 수 있습니다.**
