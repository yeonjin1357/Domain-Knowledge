"""Check published observations, historical input hashes and example arithmetic.

This reads saved evidence; it does not rerun servers or automatically fact-check prose.
"""

import hashlib
import json
import math
from pathlib import Path
import re

from verify_review_r1 import verify_published_linux
from verify_review_r2 import verify_published_review_r2
from verify_review_r3 import verify_published_review_r3

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return (ROOT / name).read_text(encoding="utf-8")


def digest(name):
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()


def main():
    records = {}
    provenance = json.loads(read('review/evidence-provenance.json'))['archives']
    archives = {(a['evidence'], a['original_path']): a for a in provenance}
    assert len(archives) == len(provenance), 'duplicate archive mapping'
    expected = {"linux": 4, "postgresql": 11, "kubernetes": 7, "otel": 7, "http11": 2}
    for name, count in expected.items():
        record = json.loads(read(f"labs/results/1.1-{name}.json"))
        records[name] = record
        inputs = record.get("input_sha256", {})
        if "script_sha256" in record:
            script = "http" if name == "http11" else name
            inputs = {f"scripts/run_{script}_lab.py": record["script_sha256"]}
        assert inputs, name
        for filename, sha in inputs.items():
            archive = archives.get((f'labs/results/1.1-{name}.json', filename))
            if archive:
                assert archive['sha256'] == sha, (name, 'archive hash differs from execution record')
                filename = archive['archived_path']
            assert digest(filename) == sha, (name, "evidence input changed", filename)
        experiments = {k: v for k, v in record["experiments"].items() if isinstance(v, dict)}
        assert sum(v["status"] == "passed" for v in experiments.values()) == count, name
        assert all(v["status"] == "passed" or
                   (name == "linux" and k == "cgroup_read_only" and v["status"] == "observed")
                   for k, v in experiments.items()), name

    linux = records["linux"]["experiments"]
    assert records["linux"]["kernel"] == "6.18.33.2-microsoft-standard-WSL2"
    assert linux["process_name_parsing"]["observed_comm"] == "dk ) worker"
    cpu = linux["cpu_accounting"]
    hz = cpu["clock_ticks_per_second"]
    assert hz == 100
    assert cpu["delta_ticks"] == sum(cpu["second"][k] - cpu["first"][k]
                                     for k in ("utime_ticks", "stime_ticks"))
    assert math.isclose(cpu["cpu_seconds"], cpu["delta_ticks"] / hz)
    intervals = cpu["additional_intervals"]
    assert [v["delta_ticks"] for v in intervals] == [106, 212]
    for interval in intervals:
        assert math.isclose(interval["accounting_ratio"], interval["delta_ticks"] / hz / interval["wall_seconds"])
        # Preserve the surprising observation instead of treating it as calibration success.
        assert interval["accounting_ratio"] > 1
    memory = linux["virtual_vs_resident"]
    assert memory["requested_bytes"] == 32 * 1024**2
    for key in ("Rss_KiB", "Pss_KiB", "Private_Dirty_KiB"):
        assert memory["after_mapping_before_touch"][key] == 0
        assert memory["after_touch"][key] == 32768
    io = linux["logical_vs_storage_io"]
    assert io["after_write_and_fsync"]["wchar"] - io["before"]["wchar"] == 1048576
    assert io["after_two_reads"]["read_bytes"] == io["after_write_and_fsync"]["read_bytes"]
    assert io["after_two_reads"]["rchar"] > io["after_write_and_fsync"]["rchar"]
    assert linux["cgroup_read_only"]["fields"]["cpuset.cpus.effective"]["unavailable"] == "FileNotFoundError"

    pg = records["postgresql"]["experiments"]
    assert pg["server_version_num"] == 180006
    assert pg["read_committed"]["observations"] == [10, 20, 20]
    assert pg["repeatable_read"]["observations"] == [10, 10, 20]
    assert pg["lock_wait"]["waiter"]["state"] == "active"
    assert pg["lock_wait"]["waiter"]["wait_event_type"] == "Lock"
    assert pg["lock_wait"]["holder"]["state"] == "idle in transaction"
    assert pg["lock_wait"]["final_value"] == 12
    for name, code in (("lock_timeout", "55P03"), ("statement_timeout", "57014"), ("failed_transaction", "23514")):
        assert (pg[name]["first_sqlstate"], pg[name]["next_sqlstate"]) == (code, "25P02")
    assert pg["failed_transaction"]["after_rollback"] == 10
    assert pg["savepoint"]["retained_earlier_update"] == 40
    assert sorted(pg["deadlock"]["two_sqlstates"]) == ["00000", "40P01"]
    assert pg["statistics_privilege"]["before"]["state"] is None
    assert pg["statistics_privilege"]["after"]["state"] == "idle"
    assert [pg["statistics_snapshot"][k] for k in ("initial", "same_transaction_cached", "after_clear")] == [4, 4, 10]
    assert any(row["stats_reset"] is None and int(row["xact_commit"]) > 0
               for row in pg["collector_query"]["result_sets"][1])
    sql = re.search(r"```sql\n(.*?)\n```", read("docs/database/collection-contracts.md"), re.S).group(1)
    assert " ".join(sql.split()) == " ".join(read("labs/postgresql/collect-database.sql").split()), "SQL excerpt differs from executed input"

    kube = records["kubernetes"]["experiments"]
    assert records["kubernetes"]["server_version"]["gitVersion"] == "v1.34.1"
    assert set(kube["pagination"]["collection_versions"]) == {"202"}
    assert kube["pagination"]["original_list_names"] == ["cm-0", "cm-1", "cm-2"]
    assert kube["list_then_watch"]["watch_from"] == "202"
    assert kube["list_then_watch"]["event_type"] == "ADDED"
    assert kube["name_reuse"]["old_uid"] != kube["name_reuse"]["new_uid"]
    assert kube["optimistic_conflict"]["http_status"] == 409
    assert all(kube["rbac_scope"][k] == 403 for k in ("before_grant", "secrets_status", "other_namespace_status"))
    assert (kube["selector_exit"]["watch_event"], kube["selector_exit"]["get_after_event"]) == ("DELETED", 200)
    assert kube["expired_history"]["expired_http_status"] == 410

    otel = records["otel"]["experiments"]
    assert records["otel"]["collector_version"] == "otelcol version 0.137.0"
    outcomes = {"success": (1, 200), "retry_503": (2, 200), "permanent_400": (1, 400),
                "permanent_500": (1, 500), "partial_success": (1, 200),
                "response_lost": (2, 200), "retry_exhausted": (6, 503)}
    for name, (attempts, status) in outcomes.items():
        assert len(otel[name]["backend_attempts"]) == attempts, "published run differs; future run counts may vary"
        assert otel[name]["receiver_http_status"] == status
        assert otel[name]["sending_queue_enabled"] is False
    assert json.loads(otel["partial_success"]["receiver_body"]) == {"partialSuccess": {}}
    duplicate = [sid for attempt in otel["response_lost"]["backend_attempts"] for sid in attempt["span_ids"]]
    assert len(duplicate) == 4 and len(set(duplicate)) == 2

    http = records["http11"]["experiments"]
    assert (http["connection_reuse"]["requests"], http["connection_reuse"]["accepted_tcp_connections"]) == (2, 1)
    body = http["incomplete_body"]
    assert (body["response_status"], body["client_error"]) == (200, "IncompleteRead")
    assert body["received_bytes"] == body["missing_bytes"] == 5
    assert body["received_bytes"] + body["missing_bytes"] == body["declared_bytes"] == 10

    examples = [
        ("foundations/measurement-and-comparability", "약 8.33%", 5/60*100, 8.333333333333334),
        ("foundations/measurement-and-comparability", "120/12=10/초", (220-100)/12, 10),
        ("application/trace-sampling-and-context", "= 10%", 1000/10000*100, 10),
        ("application/trace-sampling-and-context", "≈ 52.63%", 1000/1900*100, 52.63157894736842),
        ("application/trace-sampling-and-context", "20,000개", 2000*10, 20000),
        ("containers/memory-accounting-and-oom", "= 400MiB", 600-200, 400),
        ("containers/memory-accounting-and-oom", "= 78.125%", 600/768*100, 78.125),
        ("containers/memory-accounting-and-oom", "≈ 52.08%", 400/768*100, 52.083333333333336),
        ("storage/write-path-and-durability", "= 50MiB/s", 1/.020, 50),
        ("cloud/late-data-and-reconciliation", "=1,800", 1200+600, 1800),
        ("cloud/late-data-and-reconciliation", "=3,300", 900+600+1200+600, 3300),
        ("cloud/late-data-and-reconciliation", "=15/초", 1800/120, 15),
    ]
    for chapter, token, actual, result in examples:
        assert token in read(f"docs/{chapter}.md"), (chapter, token)
        assert math.isclose(actual, result, rel_tol=1e-12), chapter
    pairs = sorted(zip(["10:02", "10:00", "10:01"], [30, 10, 20]))
    assert pairs == [("10:00", 10), ("10:01", 20), ("10:02", 30)]
    verify_published_linux()
    verify_published_review_r2()
    verify_published_review_r3()
    print(f"PASS: {sum(expected.values())} recorded scenarios in 5 suites; all evidence input hashes; SQL excerpt; {len(examples)} calculations and timestamp-value pairing")
    print("Historical inputs include the byte-identical archived Linux runner. Its CPU passed flag did not validate wall-clock calibration.")
    print("Saved execution evidence was checked; servers and source facts were not re-executed by this command")


if __name__ == "__main__":
    main()
