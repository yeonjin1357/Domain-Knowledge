"""Extract small immutable fixtures. No servers, source edits or new lab runs.

--check compares a deterministic extraction, including provenance, with the
committed fixture. Expected outcomes below are reviewed assertions, never the
output of adapter_contract.py. No reference adapter is imported here.
"""

import argparse
import json

from r4_support import EvidenceReader, bind, canonical, json_text, pointer, sha, write_or_check

OUTPUT = "labs/fixtures/adapter-r4.json"
CPU = "labs/results/1.1-linux-clock-r1.json"
PG = "labs/results/1.1-postgresql.json"
PG2 = "labs/results/1.1-r2-postgresql.json"
KUBE = "labs/results/1.1-kubernetes.json"
OTEL = "labs/results/1.1-r2-otel.json"
OTEL1 = "labs/results/1.1-otel.json"
MEM = "labs/results/1.1-r3/linux-memory.json"
HIST = "labs/results/1.1-r3/histograms.json"


def build():
    reader, cases = EvidenceReader(), []

    def add(name, contract, expected, bindings=None, parameters=None,
            origin=None, fields=None, book="docs/product/adapter-contracts.md", limitation=""):
        bindings, parameters = bindings or {}, parameters or {}
        if set(bindings) & set(parameters):
            raise ValueError("binding/parameter collision")
        values = {k: reader.extract(v) for k,v in bindings.items()}
        data = dict(parameters, **values)
        cases.append({"id": name, "contract": contract,
                      "origin": origin or ("measured" if bindings else "synthetic"),
                      "field_ids": fields or [], "book": book,
                      "limitation": limitation or "Reference policy at the recorded boundary; not a production certification.",
                      "bindings": bindings, "parameters": parameters,
                      "extracted_sha256": {k: sha(canonical(v)) for k,v in values.items()},
                      "input": data, "expected": expected})

    for i in range(4):
        prefix = f"/experiments/cpu_accounting/intervals/{i}"
        flags = ["single_thread_cpu_over_monotonic", "monotonic_raw_rate_difference", "clock_slew_suspected"] if i < 3 else ["monotonic_raw_rate_difference"]
        add(f"cpu-clock-{i}", "cpu_clock", {"quality_flags": flags},
            {k: bind(CPU, prefix + "/" + k) for k in ("before", "after", "thread_counts")},
            fields=["linux.process.utime"], book="docs/host/linux-observation-lab.md",
            limitation="WSL single-thread samples; 1% quality threshold is reference policy; RAW external accuracy is not certified.")

    wrap = dict(previous=2**32-4, current=6, bits=32, continuity_proven=True, max_increment=20)
    for name, changes, expected in [
        ("one-wrap", {}, {"quality":"wrap_candidate", "delta":10}),
        ("reset-marker", {"reset_changed":True}, {"quality":"reset", "delta":None}),
        ("unknown-lifetime", {"continuity_proven":False}, {"quality":"continuity_unknown", "delta":None}),
        ("multiple-wrap-possible", {"max_increment":2**32}, {"quality":"wrap_count_unknown", "delta":None}),
        ("bound-violation", {"max_increment":9}, {"quality":"bound_violated", "delta":None}),
        ("increasing-still-ambiguous", {"previous":1,"current":2,"max_increment":None}, {"quality":"wrap_count_unknown", "delta":None}),
        ("snmp-counter64", {"bits":64,"previous":2**64-4}, {"quality":"wrap_candidate", "delta":10}),
    ]:
        add(name, "bounded_counter", expected, parameters=dict(wrap, **changes),
            fields=[] if name.startswith("snmp") else ["linux.disk.read_time"],
            book="docs/network/snmp-and-device-models.md" if name.startswith("snmp") else "docs/host/collection-contracts.md",
            limitation="Synthetic boundary; no observed diskstats/SNMP wrap. Continuity and maximum increment are explicit premises.")
    add("diskstats-modern-layout", "diskstats", {"major":8,"minor":0,"device":"sda","reads_completed":100,"sectors_read":200,"read_time_ms":4294967292,"in_flight":0,"io_time_ms":10},
        parameters={"text":"8 0 sda 100 0 200 4294967292 10 0 50 20 0 10 20 0 0 0 0 0 0"},
        fields=["linux.disk.read_time"], book="docs/host/collection-contracts.md")
    add("diskstats-incomplete", "diskstats", {"raises":"ValueError"}, parameters={"text":"8 0 sda 1 2 3"})
    add("snmp-header-order", "snmp", {"Tcp.CurrEstab":3,"Tcp.OutSegs":100,"Tcp.RetransSegs":2},
        parameters={"text":"Tcp: OutSegs CurrEstab RetransSegs\nTcp: 100 3 2\n"},
        fields=["linux.tcp.curr_estab","linux.tcp.retrans_segs"], book="docs/network/linux-stack-counters.md")
    add("snmp-header-mismatch", "snmp", {"raises":"ValueError"}, parameters={"text":"Tcp: CurrEstab OutSegs\nTcp: 2\n"})

    for version in ("8.4.11", "9.7.2"):
        manifest = f"labs/results/1.1-r3/mysql-{version}-r2.json"
        record = reader.read(manifest)
        for stage, lag, io, sql, match in [("baseline",0,"Yes","Yes",True), ("io_stopped",None,"No","Yes",True),
                                         ("sql_stopped",None,"Yes","No",False), ("resumed",0,"Yes","Yes",True)]:
            obs = record["scenarios"][version+"/replication"]["observations"][stage]
            raw = reader.artifact(manifest, obs["query_refs"][0]+".xml")
            add(f"mysql-{version}-{stage}", "mysql_replica", {"lag":{"quality":"null" if lag is None else "known","value":lag},
                "io":io,"sql":sql,"positions_match":match,"source_freshness_proven":False}, {"text":raw},
                fields=["mysql.replica.seconds_behind","mysql.replica.io_running","mysql.replica.sql_running"],
                book="docs/database/mysql-operations.md", limitation="Parse actual gzip XML, preserving xsi:nil; matching receiver/coordinator positions does not prove source freshness.")

    for phase, expected in (("before",{"visibility":"restricted","state":None}), ("after",{"visibility":"visible","state":"idle"})):
        add("pg-visibility-"+phase,"pg_visibility",expected,{"row":bind(PG,"/experiments/statistics_privilege/"+phase)},
            fields=["pg.activity.state"],book="docs/database/postgresql-concurrency-lab.md")
    add("pg-null-does-not-prove-permission", "pg_visibility", {"visibility":"unknown","state":None}, parameters={"row":{"state":None,"query":None}})
    for scenario, value in (("standby_feedback",813),("physical_slot_xmin",None)):
        add("pg-feedback-"+scenario,"nullable",{"quality":"null" if value is None else "known","value":value},
            {"value":bind(PG2,"/scenarios/"+scenario+"/observations/before_delete/replication/0/backend_xmin")},
            fields=["pg.replication.backend_xmin"],book="docs/database/postgresql-operations.md",
            limitation="Recorded backend_xmin only; replay_lag was not selected in this lab and remains synthetic below.")
    add("pg-idle-replay-lag-null", "nullable", {"quality":"null","value":None}, parameters={"value":None},
        fields=["pg.replication.replay_lag"],book="docs/database/replication-and-recovery.md")
    add("kube-selector-exit", "watch", {"selected_membership":"removed","object_state":"present_at_recheck","physical_deletion_proven":False},
        {"event_type":bind(KUBE,"/experiments/selector_exit/watch_event"),"get_status":bind(KUBE,"/experiments/selector_exit/get_after_event")},
        fields=["k8s.object.uid"],book="docs/kubernetes/inventory-consistency.md")
    add("kube-name-reuse", "uid", {"identity":"replaced","remove_current":False},
        {"previous_uid":bind(KUBE,"/experiments/name_reuse/old_uid"),"current_uid":bind(KUBE,"/experiments/name_reuse/new_uid")},
        fields=["k8s.object.uid"],book="docs/kubernetes/inventory-consistency.md")
    add("kube-404-recheck", "watch", {"selected_membership":"removed","object_state":"absent_at_recheck","physical_deletion_proven":False},
        parameters={"event_type":"DELETED","get_status":404},book="docs/kubernetes/inventory-consistency.md")
    add("kube-stale-delete", "uid", {"identity":"replaced","remove_current":False},
        parameters={"previous_uid":"old","current_uid":"new","deleted_event_uid":"old"},book="docs/kubernetes/inventory-consistency.md")

    cloud = {"MetricDataResults":[{"Id":"requests","StatusCode":"PartialData","Timestamps":["10:02","10:00","10:01"],"Values":[30,10,20]}]}
    for token in (None,"next-page"):
        response = dict(cloud)
        if token is not None: response["NextToken"] = token
        add("cloud-partial-"+("no-token" if token is None else "token"),"cloudwatch",
            {"results":[{"id":"requests","status":"PartialData","points":[["10:00",10],["10:01",20],["10:02",30]],"complete":False,"messages":[]}],"next_token":token},
            parameters={"response":response},fields=["cloudwatch.result.status","cloudwatch.response.next_token"],book="docs/cloud/late-data-and-reconciliation.md")
    add("cloud-mismatched-arrays","cloudwatch",{"raises":"ValueError"},parameters={"response":{"MetricDataResults":[{"Id":"x","StatusCode":"Complete","Timestamps":[1],"Values":[]}]}})
    add("cloud-forbidden-not-zero","cloudwatch",{"results":[{"id":"x","status":"Forbidden","points":[],"complete":False,"messages":[]}],"next_token":None},
        parameters={"response":{"MetricDataResults":[{"Id":"x","StatusCode":"Forbidden"}]}},book="docs/cloud/late-data-and-reconciliation.md")
    for name,value,present,quality in (("null",None,True,"null"),("zero",0,True,"known"),("absent",None,False,"absent")):
        add("azure-"+name,"azure",{"quality":quality,"value":value,"zero_proves_no_activity":False},parameters={"value":value,"present":present},book="docs/cloud/provider-metrics.md")

    otel = reader.read(OTEL)
    for queue in ("false","true"):
        name = "partial_success-queue-"+queue
        prefix = "/raw_cases/"+name+"/backend_attempts/1"
        add("otlp-destination-partial-"+queue,"otlp",{"outcome":"partial_success","retryable":False,"rejected_spans":1,"end_to_end_stored":None,"warning":False,"error_message":"r2-partial-rejected-one"},
            {"status":bind(OTEL,prefix+"/response_code"),"body":bind(OTEL,prefix+"/response_body")},
            fields=["otlp.response.rejected_spans"],book="docs/product/telemetry-delivery-contracts.md")
        prefix = "/scenarios/"+name+"/observations/upstream"
        add("otlp-upstream-success-"+queue,"otlp_json",{"outcome":"hop_success","retryable":False,"rejected_spans":0,"end_to_end_stored":None,"warning":False,"error_message":""},
            {"status":bind(OTEL,prefix+"/status"),"body_text":bind(OTEL,prefix+"/body")},book="docs/product/telemetry-delivery-contracts.md")
        for scenario in ("retry_success", "retry_exhausted"):
            name=scenario+"-queue-"+queue
            samples=otel["raw_cases"][name]["metric_samples"]
            held=next(i for i,s in enumerate(samples) if s.get("phase")=="held")
            bindings={
                "baseline":bind(OTEL,"/raw_cases/"+name+"/baseline_metrics/metrics"),
                "held":bind(OTEL,f"/raw_cases/{name}/metric_samples/{held}/metrics"),
                "final":bind(OTEL,"/scenarios/"+name+"/observations/final_metrics/metrics")}
            for b in bindings.values(): b["metric_lines"]="otelcol_exporter_send_failed_spans"
            add("collector-"+name,"collector",{"values":[2.0,2.0,4.0 if scenario=="retry_exhausted" else 2.0],
                "delta":2.0 if scenario=="retry_exhausted" else 0.0,"first_increase_index":2 if scenario=="retry_exhausted" else None},
                bindings,fields=["otlp.collector.send_failed_spans"],book="docs/product/telemetry-delivery-contracts.md",
                limitation="Baseline, held retry and final snapshots in one exporter lifetime; exact increase instant and end-to-end loss not inferred.")
    for status in (500,503):
        add("otlp-http-"+str(status),"otlp",{"outcome":"failure","retryable":status==503,"rejected_spans":None,"end_to_end_stored":None,"warning":False,"error_message":None},
            parameters={"status":status,"body":{}},book="docs/product/telemetry-delivery-contracts.md")
    # Protocol defaults are conditional, not a global rule to fill absence with 0.
    for name,partial,rejected,message in [
        ("warning-string-zero",{"rejectedSpans":"0","errorMessage":"advice"},0,"advice"),
        ("warning-default-zero",{"errorMessage":"advice"},0,"advice"),
        ("numeric-count",{"rejectedSpans":1},1,""),
        ("int64-max",{"rejectedSpans":"9223372036854775807"},9223372036854775807,""),
        ("exponent-count",{"rejectedSpans":"1e2"},100,""),
        ("null-partial",None,0,""),
        ("null-count",{"rejectedSpans":None},0,""),
    ]:
        add("otlp-"+name,"otlp",{"outcome":"partial_success" if rejected or message else "hop_success",
            "retryable":False,"rejected_spans":rejected,"end_to_end_stored":None,
            "warning":rejected==0 and bool(message),"error_message":message},
            parameters={"status":200,"body":{"partialSuccess":partial}},
            fields=["otlp.response.rejected_spans"],book="docs/product/telemetry-delivery-contracts.md",
            limitation="Synthetic OTLP 1.11/ProtoJSON response contract; no receiver execution.")
    for name,body in [
        ("invalid-envelope",[]),("invalid-partial",{"partialSuccess":[]}),
        ("negative-count",{"partialSuccess":{"rejectedSpans":"-1"}}),
        ("fractional-count",{"partialSuccess":{"rejectedSpans":"1.5"}}),
        ("overflow-count",{"partialSuccess":{"rejectedSpans":"9223372036854775808"}}),
        ("boolean-count",{"partialSuccess":{"rejectedSpans":True}}),
        ("non-string-message",{"partialSuccess":{"errorMessage":False}}),
    ]:
        add("otlp-"+name,"otlp",{"raises":"ValueError"},parameters={"status":200,"body":body},
            fields=["otlp.response.rejected_spans"],book="docs/product/telemetry-delivery-contracts.md")
    add("otlp-201-is-not-full-success","otlp",{"outcome":"failure","retryable":False,
        "rejected_spans":None,"end_to_end_stored":None,"warning":False,"error_message":None},
        parameters={"status":201,"body":{}},fields=["otlp.response.rejected_spans"],
        book="docs/product/telemetry-delivery-contracts.md")
    add("collector-default-prometheus-name","collector_named",{"values":[2.0,2.0,4.0],"delta":2.0,"first_increase_index":2},
        parameters={"snapshots":[f'otelcol_exporter_send_failed_spans_total{{exporter="otlp"}} {n}' for n in (2,2,4)]},
        fields=["otlp.collector.send_failed_spans"],book="docs/product/telemetry-delivery-contracts.md",
        limitation="Synthetic default naming; measured fixtures retain the lab's without_type_suffix setting.")
    previous={"collection_status":"ok","unit":"count","value":8,"time":10,"identity":"cluster/backend/object/context",
              "epoch":"stats-reset-1","clock_epoch":"collector-boot-1","definition":"reads-blocks-pg16-17"}
    add("pg-io-definition-change","transform",{"quality":"definition_changed","rate":None},
        parameters={"previous":previous,"current":dict(previous,value=9,time=20,definition="reads-requests-pg18")},
        fields=["pg.io.reads","pg.io.read_requests"],book="docs/database/postgresql-operations.md")
    add("pg-undefined-state-not-permission-proof","pg_visibility",{"visibility":"unknown","state":None},
        parameters={"row":{"state":None,"backend_type":"checkpointer","query":""}},
        fields=["pg.activity.state"],book="docs/database/postgresql-operations.md")
    add("otlp-repeated-span-ids", "receipt_ids", {"received_items":4,"unique_keys":2,"repeated_items":2},
        {"attempts":bind(OTEL1,"/experiments/response_lost/backend_attempts")},
        parameters={"tenant":"local-lab","trace_scope":"single-fixed-trace-in-original-experiment"},origin="mixed",
        book="docs/product/telemetry-delivery-contracts.md",
        limitation="Raw run preserved span IDs but not full trace IDs at receiver. Fixed single-trace experiment context supplies scope; not a general dedup proof.")
    add("otlp-same-span-other-trace","receipts",{"received_items":2,"unique_keys":2,"repeated_items":0},
        parameters={"attempts":[[["tenant","trace-a","span-1"],["tenant","trace-b","span-1"]]]})
    for version,key in (("3.13.4","command-003"),("3.15.0","command-006")):
        add("histogram-"+version,"histogram_debug",{"linear":{"count":4,"quantile":1.5,"fraction":0.25},
            "exponential":{"count":4,"quantile":1.4142135623730951,"fraction":0.2924812503605781}},
            {"text":reader.artifact(HIST,key)},book="docs/foundations/histogram-storage.md",
            limitation="Actual promtool debug output for synthetic input distribution, not measured request latencies; finite positive buckets only.")
    add("psi-recorded-zero", "psi", {"some":{"avg10":0.0,"avg60":0.0,"avg300":0.0,"total":0},"full":{"avg10":0.0,"avg60":0.0,"avg300":0.0,"total":0}},
        {"text":reader.artifact(MEM,"psi-memory")},fields=["linux.psi.memory.some_total","linux.psi.memory.some_avg10"],book="docs/host/numa-and-pressure.md")
    add("nullable-nan", "nullable", {"raises":"ValueError"}, parameters={"value":"NaN"})
    return {"format_version":1,"scope":"Extracted observations and explicitly synthetic reference contracts; no new live collection.",
            "sources":reader.sources,"cases":cases}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    data=build()
    write_or_check(OUTPUT,json_text(data),args.check)
    print(f"{'PASS' if args.check else 'BUILT'}: {len(data['cases'])} fixtures, {len(data['sources'])} hashed source files")


if __name__ == "__main__":
    main()
