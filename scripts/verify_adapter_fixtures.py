"""Replay measured/synthetic fixtures offline against reference contracts."""

from collections import Counter
import json
import math
import re

import adapter_contract as adapter
from build_adapter_fixtures import OUTPUT, build
from r4_support import ROOT, json_text, local_path


def same(actual, expected, name):
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise AssertionError((name, actual, expected))
        for key in expected:
            same(actual[key], expected[key], name + "/" + key)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise AssertionError((name, actual, expected))
        for i,(a,e) in enumerate(zip(actual,expected)):
            same(a,e,name + "/" + str(i))
    elif type(expected) in (int,float):
        if type(actual) not in (int,float) or not math.isclose(actual,expected,rel_tol=1e-12,abs_tol=1e-15):
            raise AssertionError((name, actual, expected))
    elif actual != expected or type(actual) is not type(expected):
        raise AssertionError((name, actual, expected))


def histogram_debug(text):
    # Read actual debug values, not the expectation fields in the lab summary.
    observed={name:float(value) for name,value in re.findall(
        r'\{__name__="r3:([a-z0-9_]+)"\} =>\s*([-+.0-9eE]+) @\[60000\]',text)}
    expected_keys={f"{kind}_{suffix}" for kind in ("classic","native","custom") for suffix in ("count","fraction","q25")} | {"classic_count_ignored"}
    if set(observed) != expected_keys or "SUCCESS" not in text:
        raise ValueError("unrecognized/incomplete promtool output")
    encoded=re.search(r'\{__name__="native"\} =>\s*\{count:(\d+), sum:[^,]+, (.*?)\}',text)
    if not encoded:
        raise ValueError("missing recorded native histogram")
    buckets=[[float(lo),float(hi),int(n)] for lo,hi,n in re.findall(r'\(([^,]+),([^\]]+)\]:(\d+)',encoded[2])]
    if sum(n for _,_,n in buckets) != int(encoded[1]):
        raise ValueError("incomplete population")
    results={}
    for kind,mode in (("classic","linear"),("native","exponential"),("custom","linear")):
        calculated=adapter.histogram_interpolation(buckets,.25,1.5,mode)
        measured={"count":observed[kind+"_count"],"quantile":observed[kind+"_q25"],"fraction":observed[kind+"_fraction"]}
        same(calculated,measured,"promtool/"+kind)
        results[mode]=calculated
    if observed["classic_count_ignored"] != 0:
        raise AssertionError("classic counter was unexpectedly accepted as native")
    return results


def execute(contract, data):
    functions={"bounded_counter":adapter.bounded_counter_delta,"nullable":adapter.nullable_number,
               "transform":adapter.transform,"collector_named":adapter.collector_failure_samples,
               "pg_visibility":adapter.pg_activity_visibility,"mysql_replica":adapter.mysql_replica_xml,
               "watch":adapter.selected_watch_delete,"uid":adapter.uid_transition,
               "cloudwatch":adapter.cloudwatch_page,"azure":adapter.azure_sample,
               "otlp":adapter.otlp_http_response,"receipts":adapter.repeated_receipts,
               "snmp":adapter.named_proc_pairs,"diskstats":adapter.diskstats_row,
               "psi":adapter.psi_rows,"histogram_debug":histogram_debug}
    if contract == "cpu_clock":
        result=adapter.cpu_clock_quality(**data)
        if data["thread_counts"] == [1,1] and "single_thread_cpu_over_monotonic" in result["quality_flags"]:
            assert result["cpu_over_monotonic"] > 1, "do not clamp CPU to 100%"
            assert .99 < result["cpu_over_raw"] <= 1.01
        return {"quality_flags":result["quality_flags"]}
    if contract == "collector":
        # Recorded lab explicitly disabled Prometheus type suffixes.
        return adapter.collector_failure_samples([data[k] for k in ("baseline","held","final")],
                                                 metric="otelcol_exporter_send_failed_spans")
    if contract == "otlp_json":
        return adapter.otlp_http_response(data["status"],json.loads(data["body_text"]))
    if contract == "receipt_ids":
        return adapter.repeated_receipts([[[data["tenant"],data["trace_scope"],s] for s in attempt["span_ids"]] for attempt in data["attempts"]])
    if contract not in functions:
        raise ValueError("unknown contract: " + contract)
    return functions[contract](**data)


def verify():
    # Re-extraction verifies compressed/uncompressed hashes and JSON pointers.
    fixture=build()
    if local_path(OUTPUT).read_bytes() != json_text(fixture).encode("utf-8"):
        raise AssertionError("fixture/provenance drift; inspect before regenerating")
    ids=set()
    catalog_path=ROOT/"catalog/field-catalog.json"
    catalog_ids={f["id"] for f in json.loads(catalog_path.read_text(encoding="utf-8"))["fields"]}
    for case in fixture["cases"]:
        assert case["id"] not in ids, case["id"]
        ids.add(case["id"])
        assert local_path(case["book"]).is_file(), case["book"]
        assert set(case["field_ids"]) <= catalog_ids, (case["id"],case["field_ids"])
        expected=case["expected"]
        if "raises" in expected:
            try:
                execute(case["contract"],case["input"])
            except ValueError:
                continue
            raise AssertionError((case["id"],"expected ValueError"))
        same(execute(case["contract"],case["input"]),expected,case["id"])
    origins=Counter(c["origin"] for c in fixture["cases"])
    print(f"PASS: {len(fixture['cases'])} round-4 adapter cases {dict(origins)}; {len(fixture['sources'])} hashed sources")
    print("No live collection; synthetic format/wrap/cloud cases are not measured device/API evidence.")
    return len(fixture["cases"])


if __name__ == "__main__":
    verify()
