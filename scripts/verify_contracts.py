"""Exercise consequential telemetry edge cases and tie assertions to book examples."""

import hashlib
import json
import math
from pathlib import Path

from adapter_contract import transform

ROOT = Path(__file__).resolve().parents[1]


def main():
    base = {"identity": "host-a/cpu", "epoch": "boot-1", "clock_epoch": "collector-1",
            "definition": "cpu-v1", "unit": "us", "time": 0, "value": 1000000,
            "collection_status": "ok"}
    cases = [
        ("first sample is not zero", None, base, "first", None),
        ("microseconds become CPU seconds", base, dict(base, time=10, value=3000000), "ok", .2),
        ("zero increment is known zero", base, dict(base, time=10), "ok", 0),
        ("counter reset", base, dict(base, time=10, value=12), "reset", None),
        ("new boot with larger counter", base, dict(base, time=10, value=9000000, epoch="boot-2"), "reset", None),
        ("collector clock epoch changed", base, dict(base, time=10, clock_epoch="collector-2"), "reset", None),
        ("identity changed", base, dict(base, time=10, identity="host-b/cpu"), "identity_changed", None),
        ("definition changed", base, dict(base, time=10, definition="cpu-v2"), "definition_changed", None),
        ("unit changed", base, dict(base, time=10, unit="ns"), "definition_changed", None),
        ("duplicate sample", base, base.copy(), "duplicate", None),
        ("conflicting duplicate", base, dict(base, value=1000001), "conflicting_duplicate", None),
        ("out of order", base, dict(base, time=-1), "out_of_order", None),
        ("configured excessive gap", base, dict(base, time=121), "gap", None),
        ("access failure is missing", base, dict(base, time=10, value=0, collection_status="forbidden"), "unavailable", None),
        ("unsupported unit", base, dict(base, unit="ticks"), "unsupported_unit", None),
        ("negative counter", base, dict(base, value=-1), "invalid", None),
        ("boolean is not a counter", base, dict(base, value=True), "invalid", None),
        ("fractional counter outside this contract", base, dict(base, value=1.5), "invalid", None),
        ("missing identity", base, dict(base, identity=""), "invalid", None),
        ("non-finite time", base, dict(base, time=float("nan")), "invalid", None),
        ("nanosecond conversion", dict(base, unit="ns"), dict(base, unit="ns", value=2001000000, time=10), "ok", .2),
        ("large integer precision", dict(base, unit="count", value=2**60), dict(base, unit="count", value=2**60+10, time=10), "ok", 1),
    ]
    for name, previous, current, quality, expected in cases:
        actual = transform(previous, current)
        assert actual["quality"] == quality, (name, actual)
        if expected is None:
            assert actual["rate"] is None, (name, actual)
        else:
            assert math.isclose(actual["rate"], expected, rel_tol=1e-12), (name, actual)
    # Recorded evidence must still correspond to the executed script and fixtures.
    record = json.loads((ROOT / "labs/results/2026-10-04.json").read_text())
    assert record["script_sha256"] == hashlib.sha256((ROOT / "scripts/run_labs.py").read_bytes()).hexdigest()
    for name, digest in record["fixture_sha256"].items():
        assert digest == hashlib.sha256((ROOT / "labs/prometheus" / name).read_bytes()).hexdigest()
    assert all(e["status"] == "passed" for e in record["experiments"].values())
    examples = [
        ("docs/foundations/performance-and-statistics.md", "70건", 20+500-450, 70),
        ("docs/host/numa-and-pressure.md", "20%", 2000000/1000000/10*100, 20),
        ("docs/storage/raid-lvm-and-paths.md", "16TiB", (6-2)*4, 16),
        ("docs/network/snmp-and-device-models.md", "34.36초", 2**32*8/10**9, 34.359738368),
        ("docs/network/snmp-and-device-models.md", "497.1일", 2**32/100/86400, 497.1026962962963),
        ("docs/application/servers-and-pools.md", "425ms", 300+150/2+50, 425),
        ("docs/database/specialized-data-models.md", "1,110", 10+100+1000, 1110),
        ("docs/product/capacity-and-loss-budgets.md", "34,560,000", 6000/15*86400, 34560000),
        ("docs/foundations/system-map.md", "25%", 2/8*100, 25),
        ("docs/foundations/performance-and-statistics.md", "20건", 100*.2, 20),
        ("docs/foundations/performance-and-statistics.md", "20`번째", math.ceil(.99*20), 20),
        ("docs/foundations/distributed-systems.md", "과반은 3개", 5//2+1, 3),
        ("docs/host/numa-and-pressure.md", "IPC 2", 200000000/100000000, 2),
        ("docs/host/collection-contracts.md", "4/초", (160-100)/15, 4),
        ("docs/host/collection-contracts.md", "3ms", 9000/3000, 3),
        ("docs/network/snmp-and-device-models.md", "200,000,000bit/s", 500000000*8/20, 200000000),
        ("docs/network/snmp-and-device-models.md", "20%", 200000000/(1000*1000000)*100, 20),
        ("docs/network/routing-convergence-and-qos.md", "1Gbit/s", .1*10/1, 1),
        ("docs/application/servers-and-pools.md", "600개", 20*30, 600),
        ("docs/database/high-availability.md", "25초", 5+8+12, 25),
        ("docs/database/collection-contracts.md", "5ms", 2500000000000/500/1000000000, 5),
        ("docs/cloud/quotas-cost-and-capacity.md", "20요청/초", 1200/60, 20),
        ("docs/cloud/quotas-cost-and-capacity.md", "사용료는 3", .1*3*10, 3),
        ("docs/product/capacity-and-loss-budgets.md", "552,960,000B", 34560000*16, 552960000),
        ("docs/product/capacity-and-loss-budgets.md", "112.5초", 900/8, 112.5),
        ("docs/product/capacity-and-loss-budgets.md", "150초", 900/(14-8), 150),
        ("docs/cross-domain/capstone-investigation.md", "96%", 4.8/10/.5*100, 96),
        ("docs/cross-domain/capstone-investigation.md", "6%", 4.8/10/8*100, 6),
    ]
    for path, token, actual, expected in examples:
        assert token in (ROOT / path).read_text(encoding="utf-8"), (path, token)
        assert math.isclose(actual, expected, rel_tol=1e-12), (path, actual)
    print(f"PASS: {len(cases)} adapter edge cases; {len(examples)} source-bound calculations; recorded lab hashes and statuses")


if __name__ == "__main__":
    main()
