"""Independently recalculate documented synthetic examples.

The inputs below are hand-transcribed from the book, not measurements. This
checks arithmetic and a few interpretation counterexamples, not vendor behavior
or live PromQL/SQL. Source paragraphs still require editorial review.
"""

from fractions import Fraction as F
from math import ceil, floor, isclose, log2, sqrt
import re

from doc_utils import ROOT

CHECKS = []
KiB, MiB, GiB = 1024, 1024 ** 2, 1024 ** 3


def case(document, label, actual, expected):
    path = ROOT / "docs" / (document + ".md")
    if not path.is_file():
        raise AssertionError(f"Missing example source: {path}")
    if isinstance(expected, (int, float, F)):
        good = isclose(float(actual), float(expected), rel_tol=1e-10, abs_tol=1e-10)
    else:
        good = actual == expected
    if not good:
        raise AssertionError(f"{document}: {label}: {actual!r} != {expected!r}")
    CHECKS.append((document, label))


def main():
    p = "foundations/time-series"
    case(p, "counter rate", F(12500 - 12000, 20), 25)
    case(p, "delta sum", sum([30, 50, 20]), 100)
    case(p, "series combinations", 40 * 30 * 4, 4800)
    p = "foundations/distributions"
    case(p, "weighted mean ms", F(900 * 10 + 100 * 1000, 1000), 109)
    case(p, "unweighted mean ms", F(10 + 1000, 2), 505)
    ordered = [10] * 900 + [1000] * 100
    case(p, "nearest-rank p95 ms", ordered[ceil(.95 * len(ordered)) - 1], 1000)
    case(p, "bucket-only count", 950 - 800, 150)
    case(p, "explicitly assumed interpolation", 800 + F(20 - 10, 25 - 10) * 150, 900)
    case(p, "pooled error percent", F(10 + 9, 100 + 900) * 100, F(19, 10))
    case(p, "mean of percents", F(10 + 1, 2), F(11, 2))
    p = "foundations/service-level-objectives"
    case(p, "allowed errors", 2_000_000 * F(5, 1000), 10000)
    case(p, "budget consumed percent", F(2500, 10000) * 100, 25)
    case(p, "success percent", F(2_000_000 - 2500, 2_000_000) * 100, F(799, 8))
    case(p, "burn ratio", F(2, 100) / F(5, 1000), 4)
    p = "foundations/time-and-data-quality"
    case(p, "clock skew example seconds", 1 - 5, -4)
    case(p, "whole interval average per second", F(600, 60), 10)
    p = "foundations/traces-logs-profiles"
    intervals = [(20, 220), (50, 250)]
    # Count covered integer milliseconds independently of the stated union formula.
    covered = {t for start, end in intervals for t in range(start, end)}
    case(p, "sum of child lengths", sum(end - start for start, end in intervals), 400)
    case(p, "child union ms", len(covered), 230)
    case(p, "uncovered parent ms", 300 - len(covered), 70)
    case(p, "true error percent", F(100, 10000) * 100, 1)
    case(p, "sampled error percent", round(100 / 199 * 100, 2), 50.25)
    text = (ROOT / "docs" / (p + ".md")).read_text(encoding="utf-8")
    matches = re.findall(r"(?m)^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$", text)
    case(p, "traceparent v00 literal length and nonzero IDs", len(matches) == 1 and all(int(x, 16) > 0 for x in matches[0][:2]), True)

    p = "host/cpu"
    case(p, "CPU seconds", sum([12, 4, 1, 20, 2, 1]), 40)
    case(p, "execution percent", F(17, 40) * 100, 42.5)
    case(p, "non-idle percent", F(40 - 20, 40) * 100, 50)
    case(p, "process CPU count", F(25, 10), 2.5)
    case(p, "one CPU percent", F(25, 10) * 100, 250)
    case(p, "eight CPU percent", F(25, 10 * 8) * 100, 31.25)
    case(p, "one of eight CPU", F(1, 8) * 100, 12.5)
    p = "host/memory"
    case(p, "RSS sum MiB", (100 + 50) + (100 + 80), 330)
    case(p, "PSS sum MiB", (50 + 50) + (50 + 80), 230)
    case(p, "nonavailable percent", F(16 - 6, 16) * 100, 62.5)
    p = "host/disk-io"
    case(p, "read IOPS", F(2000, 10), 200)
    case(p, "sectors to MiB", F(32768 * 512, MiB), 16)
    case(p, "MiB per second", F(32768 * 512, MiB * 10), 1.6)
    case(p, "mean I/O KiB", F(32768 * 512, 2000 * KiB), 8.192)
    disk_text = (ROOT / "docs" / (p + ".md")).read_text(encoding="utf-8")
    case(p, "documented mean I/O size matches the calculation", "| 평균 읽기 크기 | 8.192 KiB |" in disk_text, True)
    case(p, "mean latency ms", F(6000, 2000), 3)
    case(p, "busy time percent", F(8000, 10000) * 100, 80)
    case(p, "used over total percent", F(800, 1000) * 100, 80)
    case(p, "df-like percent", round(800 / (800 + 150) * 100, 2), 84.21)
    p = "host/windows"
    case(p, "system non-idle percent", F(28 + 12 - 20, 28 + 12) * 100, 50)
    case(p, "100ns units to CPU seconds", F(60_000_000, 10_000_000), 6)
    case(p, "process CPU count", F(6, 4), 1.5)
    p = "host/virtualization"
    case(p, "VM used CPU count", F(20_000_000_000, 1_000_000_000 * 10), 2)
    case(p, "VM vCPU percent", F(2, 4) * 100, 50)
    p = "host/gpu"
    case(p, "VRAM occupancy percent", F(60, 80) * 100, 75)
    p = "containers/resource-control"
    case(p, "quota CPU count", F(150000, 100000), 1.5)
    case(p, "used CPU count", F(12_000_000, 1_000_000 * 10), 1.2)
    case(p, "quota percent", F(12, 10) / F(15, 10) * 100, 80)
    case(p, "host percent", F(12, 10 * 8) * 100, 15)
    case(p, "throttled period percent", F(30, 100) * 100, 30)
    p = "containers/filesystems"
    case(p, "shared image storage MiB", 1024 + 10 * 100, 2024)
    case(p, "double-counted storage MiB", 10 * (1024 + 100), 11240)

    p = "network/tcp-and-udp"
    case(p, "window over RTT MiB/s", F(512 * KiB, MiB) / F(8, 100), 6.25)
    case(p, "BDP MiB", 100 * F(8, 100), 8)
    p = "network/tls-http"
    cumulative = [10, 40, 90, 240, 300]
    segments = [cumulative[0]] + [b - a for a, b in zip(cumulative, cumulative[1:])]
    case(p, "nonoverlapping curl segments", segments, [10, 30, 50, 150, 60])
    case(p, "segments total", sum(segments), 300)
    case(p, "wrong sum of cumulative fields", sum(cumulative), 680)
    p = "network/network-metrics"
    case(p, "bytes to bit/s", F(1_250_000_000 * 8, 10), 1_000_000_000)
    case(p, "link percent", F(1_000_000_000, 10_000_000_000) * 100, 10)
    case(p, "32-bit wrap seconds", round(2 ** 32 / 1_250_000_000, 2), 3.44)
    p = "network/layers-and-routing"
    case(p, "inner IP MTU bytes", 1500 - 20 - 8 - 8 - 14, 1450)

    p = "kubernetes/objects-and-control-loops"
    case(p, "available percent", F(3, 5) * 100, 60)
    case(p, "ready percent", F(4, 5) * 100, 80)
    p = "kubernetes/pod-lifecycle"
    case(p, "created to ready seconds", 47 - 0, 47)
    p = "kubernetes/resources-and-scheduling"
    case(p, "usage over request percent", F(750, 500) * 100, 150)
    case(p, "usage over limit percent", F(750, 2000) * 100, 37.5)
    case(p, "remaining schedulable CPU", F(7) - F(65, 10), .5)
    case(p, "init effective CPU request", max(F(7, 10), F(15, 10)), 1.5)
    case(p, "basic HPA replicas", ceil(3 * F(80, 50)), 5)
    p = "kubernetes/workloads-and-control-plane"
    case(p, "DaemonSet Ready percent", round(11 / 12 * 100, 2), 91.67)
    case(p, "scheduled-to-finish seconds", 8 + 30 + 240, 278)
    case(p, "three member quorum", floor(3 / 2) + 1, 2)
    case(p, "five member quorum", floor(5 / 2) + 1, 3)

    p = "application/requests-and-concurrency"
    case(p, "inflight conservation", 50 + 1200 - 1100, 150)
    case(p, "Little law", 200 * F(25, 100), 50)
    case(p, "pool ideal throughput", 20 / F(1, 10), 200)
    p = "application/timeouts-and-retries"
    case(p, "remaining budget ms", 1000 - 300, 700)
    case(p, "nested maximum attempts", 3 * 3, 9)
    p = "application/managed-runtimes"
    case(p, "used over committed percent", round(600 / 1024 * 100, 2), 58.59)
    case(p, "used over max percent", round(600 / 2048 * 100, 2), 29.30)
    case(p, "GC worker CPU ms", 4 * 20, 80)
    p = "application/async-runtimes"
    case(p, "nanoseconds to ms", F(25_000_000, 1_000_000), 25)
    p = "application/user-experience"
    case(p, "observed population ratio", F(6000, 10000), .6)
    p = "database/queries-and-indexes"
    case(p, "rows across loops", 4 * 500, 2000)
    case(p, "query A total seconds", F(10 * 1000, 1000), 10)
    case(p, "query B total seconds", F(10000 * 5, 1000), 50)
    case(p, "N+1 ms", 200 * 2, 400)
    p = "database/postgresql"
    case(p, "interval mean ms", F(15000 - 12000, 1200 - 1000), 15)
    p = "database/mysql-mariadb"
    case(p, "picoseconds to average ms", F(2_500_000_000_000, 1_000_000_000 * 500), 5)
    case(p, "nonoverflow coverage percent", 100 - 40, 60)
    p = "database/sqlserver-oracle"
    case(p, "nonsignal wait ms", 12000 - 2000, 10000)
    case(p, "parallel elapsed sum seconds", 1 + 1 + 1, 3)
    p = "database/replication-and-recovery"
    case(p, "conditional catchup seconds", F(8 * 1024, 40 - 24), 512)
    p = "database/distributed-and-analytical"
    case(p, "examined per returned", F(100000, 10), 10000)
    case(p, "RF3 quorum", floor(3 / 2) + 1, 2)

    p = "middleware/cache-redis"
    case(p, "hit percent", F(9000, 10000) * 100, 90)
    case(p, "origin lookups", 10000 * F(1, 10), 1000)
    p = "middleware/kafka"
    case(p, "position difference", 1000 - 950, 50)
    case(p, "commit difference", 1000 - 900, 100)
    case(p, "actual work catchup seconds", F(60000, 1000 - 800), 300)
    p = "middleware/message-queues"
    case(p, "ready plus unacked", 800 + 200, 1000)
    case(p, "prefetch ceiling", 4 * 50, 200)
    p = "middleware/search-engines"
    case(p, "shard copies", 6 * (1 + 1), 12)
    p = "middleware/proxies-and-mesh"
    case(p, "upstream attempts", 100 + 20, 120)
    p = "storage/models-and-performance"
    case(p, "4KiB IOPS MiB/s", F(10000 * 4 * KiB, MiB), 39.0625)
    case(p, "throughput IOPS ceiling", F(250 * MiB, 32 * KiB), 8000)
    p = "storage/capacity-and-protection"
    case(p, "three copies TiB", 12 * 3, 36)
    case(p, "EC6+3 TiB", 12 * F(6 + 3, 6), 18)
    case(p, "conditional days left", F(600, 20), 30)
    p = "cloud/resources-and-apis"
    case(p, "pagination count", 1000 + 1000 + 300, 2300)
    case(p, "API calls per minute", 20 * 5 * 10, 1000)
    p = "cloud/provider-metrics"
    case(p, "period sum rate", F(1200, 60), 20)
    case(p, "pooled mean ms", F(900 * 10 + 100 * 100, 1000), 19)
    case(p, "wrong mean of means", F(10 + 100, 2), 55)
    p = "cloud/managed-and-serverless"
    case(p, "invocation error percent", F(9, 900) * 100, 1)
    case(p, "throttle attempt percent", F(100, 1000) * 100, 10)
    case(p, "Lambda mean concurrency", 100 * F(2, 10), 20)
    case(p, "event total seconds", 30 + F(2, 10), 30.2)

    p = "product/collection-pipelines"
    case(p, "buffer fill seconds", F(900, 8 - 5), 300)
    case(p, "buffer drain seconds", F(900, 14 - 8), 150)
    p = "product/storage-and-query"
    case(p, "samples per day", 200000 * (86400 // 15), 1152000000)
    case(p, "body GB per day", F(1152000000 * 4, 10 ** 9), 4.608)
    case(p, "body GB per 30 days", F(1152000000 * 4 * 30, 10 ** 9), 138.24)
    case(p, "Gauge sample mean", F(sum([0, 0, 0, 100]), 4), 25)
    p = "product/alerts-and-incidents"
    case(p, "burn ratio", F(1, 100) / F(1, 1000), 10)
    p = "product/self-observation-and-access"
    case(p, "expected observations", 100 * 10, 1000)
    case(p, "completeness percent", F(970, 1000) * 100, 97)
    p = "cross-domain/slow-requests"
    case(p, "baseline request ms", 2 + 30 + 68, 100)
    case(p, "slow request ms", 700 + 400 + 100, 1200)
    case(p, "one second connection capacity", 20 / 1, 20)
    p = "cross-domain/resource-failures"
    case(p, "conditional capacity hours", F(120, 6), 20)
    p = "cross-domain/backlogs-and-retries"
    case(p, "origin baseline per second", 1200 * F(5, 100), 60)
    case(p, "origin multiplier", F(1200, 60), 20)
    case(p, "cohort max attempts", 1200 * 3, 3600)
    case(p, "backlog at 60 seconds", (1000 - 800) * 60, 12000)
    case(p, "conditional drain seconds", F(12000, 900 - 600), 40)
    p = "cross-domain/missing-observations"
    case(p, "expected observations", 50 * 20, 1000)
    case(p, "completeness percent", F(940, 1000) * 100, 94)
    p = "metric-catalog"
    case(p, "Mbit/s to MB/s", F(100, 8), 12.5)

    # Round 2b examples: check both arithmetic and the reviewed printed result.
    # These are synthetic explanations, not replayed vendor metrics or queries.
    r2_examples = [
        ("network/linux-stack-counters", "180 / 12000 × 100 = 1.5%", F(180, 12000) * 100, 1.5),
        ("network/linux-stack-counters", "180 / 60 = 3회/초", F(180, 60), 3),
        ("kubernetes/pressure-and-termination", "78.125% → 39.0625%", F(400, 512) * 100, 78.125),
        ("kubernetes/pressure-and-termination", "78.125% → 39.0625%", F(400, 1024) * 100, 39.0625),
        ("database/postgresql-operations", "`75%`", F(150_000_000, 200_000_000) * 100, 75),
        ("database/postgresql-operations", "차이는 5000만 XID", 200_000_000 - 150_000_000, 50_000_000),
        ("database/postgresql-operations", "50000초 ≈ 13.89시간", F(50_000_000, 1000), 50000),
        ("database/postgresql-operations", "50000초 ≈ 13.89시간", round(F(50000, 3600), 2), F(1389, 100)),
        ("foundations/metric-context-and-start-time", "12−7=5건", 12 - 7, 5),
        ("foundations/metric-context-and-start-time", "0.5건/초", F(12 - 7, 20 - 10), .5),
        ("foundations/metric-context-and-start-time", "0.6건/초", F(12, 20), .6),
        ("application/trace-sampling-and-context", "90/0.1 + 20/0.5 = 940건", 90 / F(1, 10) + 20 / F(1, 2), 940),
        ("application/trace-sampling-and-context", "표본 110개", 90 + 20, 110),
        ("application/semantic-conventions", "250 / 1000 = 0.25", F(250, 1000), .25),
        ("host/windows", "75%", F(12, 16) * 100, 75),
        ("cloud/provider-metrics", "(10+20)/2=15", F(10 + 20, 2), 15),
        ("cloud/provider-metrics", "(10+0+20)/3=10", F(10 + 0 + 20, 3), 10),
        ("product/alerts-and-incidents", "180초", 10 + 20 + 120 + 30, 180),
        ("network/tls-http", "약 60 ms와 30 ms", 2 * 30, 60),
        ("network/tls-http", "약 60 ms와 30 ms", 1 * 30, 30),
        ("storage/capacity-and-protection", "`4+min(1,1)=5`", 4 + min(1, 2 - 1), 5),
    ]
    for index, (p, token, actual, expected) in enumerate(r2_examples, 1):
        assert token in (ROOT / "docs" / (p + ".md")).read_text(encoding="utf-8"), (p, token)
        case(p, f"round 2b printed example {index}", actual, expected)
    p = "application/trace-sampling-and-context"
    case(p, "half-space threshold has probability one half", F(2**56 - 2**55, 2**56), F(1, 2))
    case(p, "adjusted count at probability one half", 1 / F(1, 2), 2)
    # Same used bytes, different limit: changed percentage is not freed memory.
    p = "kubernetes/pressure-and-termination"
    case(p, "doubling limit halves ratio without changing numerator", F(400, 1024) / F(400, 512), F(1, 2))

    # Round 3b manuscript arithmetic only. Do not import or modify active lab inputs.
    sample_seconds = [F(5, 4), F(7, 4), F(5, 2), F(7, 2)]
    r3_examples = [
        ("host/reclaim-and-oom", "2,500 / 10,000 = 25%", F(2500, 10000) * 100, 25),
        ("host/reclaim-and-oom", "2 MiB", F(512 * 4 * KiB, MiB), 2),
        ("host/reclaim-and-oom", "0.2 MiB/s", F(512 * 4 * KiB, MiB * 10), .2),
        ("host/numa-and-pressure", "2초 window 안의 누적 some stall 200 ms", F(200000, 1000), 200),
        ("foundations/histogram-storage", "scale=0 → base=2", 2 ** (2 ** 0), 2),
        ("foundations/histogram-storage", "base=√2 ≈ 1.414214", round(2 ** (2 ** -1), 6), 1.414214),
        ("foundations/histogram-storage", "count=4", len(sample_seconds), 4),
        ("foundations/histogram-storage", "sum=9초", sum(sample_seconds), 9),
        ("foundations/histogram-storage", "**1.5초**", 1 + F(2 - 1, 2), 1.5),
        ("foundations/histogram-storage", "**√2 ≈ 1.414214초**", round(sqrt(2), 6), 1.414214),
        ("foundations/histogram-storage", "**0.25**", F(2, 4) * F(3 - 2, 2) / (2 - 1), .25),
        ("foundations/histogram-storage", "**0.292481**", round(F(2, 4) * log2(1.5), 6), .292481),
        ("foundations/histogram-storage", "비율은 1/4", F(sum(1 < x <= F(3, 2) for x in sample_seconds), len(sample_seconds)), .25),
        ("foundations/histogram-storage", "99~101 ms", 100 * (1 - F(1, 100)), 99),
        ("foundations/histogram-storage", "99~101 ms", 100 * (1 + F(1, 100)), 101),
    ]
    for index, (p, token, actual, expected) in enumerate(r3_examples, 1):
        assert token in (ROOT / "docs" / (p + ".md")).read_text(encoding="utf-8"), (p, token)
        case(p, f"round 3b printed example {index}", actual, expected)

    # Boundary checks: these make the limitations in the text explicit.
    p = "foundations/time-series"
    case(p, "reset must not become a negative request rate", 80 < 12500, True)
    case(p, "missing delta cannot be reconstructed by summing received intervals", 30 + 20 != 100, True)
    p = "foundations/distributions"
    undefined = False
    try:
        F(0, 0)
    except ZeroDivisionError:
        undefined = True
    case(p, "zero population has no defined error ratio", undefined, True)
    # Same bucket counts, different number of observations below 0.20 seconds.
    low = [F(5, 100)] * 500 + [F(1, 10)] * 300
    lower = low + [F(15, 100)] * 150 + [F(1)] * 50
    upper = low + [F(24, 100)] * 150 + [F(1)] * 50
    limits = [F(5, 100), F(1, 10), F(25, 100), F(1)]
    case(p, "same histogram", [sum(x <= b for x in lower) for b in limits], [sum(x <= b for x in upper) for b in limits])
    case(p, "different interior count despite same histogram", (sum(x <= F(1, 5) for x in lower), sum(x <= F(1, 5) for x in upper)), (950, 800))
    print(f"PASS: {len(CHECKS)} arithmetic/interpretation checks across {len({p for p, _ in CHECKS})} source documents")
    print("No production diagnostic command or database query was executed")


if __name__ == "__main__":
    main()
