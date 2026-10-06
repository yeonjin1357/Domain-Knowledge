"""Executable reference contracts, not a production monitoring implementation.

transform() retains the original 22-case two-sample teaching contract. Round-4
functions below preserve missing values, identity and observation boundaries.
They are deliberately limited to the formats stated in catalog/README.md.
This is not Prometheus rate(): no extrapolation or hidden reset recovery.
"""

from fractions import Fraction
from decimal import Decimal
import math
import re
import xml.etree.ElementTree as ET

SCALE = {"count": Fraction(1), "By": Fraction(1), "ns": Fraction(1, 10**9),
         "us": Fraction(1, 10**6), "ms": Fraction(1, 1000), "s": Fraction(1)}


def transform(previous, current, max_gap_seconds=120):
    def result(quality, rate=None):
        return {"quality": quality, "rate": rate}

    if current.get("collection_status") != "ok":
        return result("unavailable")
    if current.get("unit") not in SCALE:
        return result("unsupported_unit")
    value, stamp = current.get("value"), current.get("time")
    if (type(value) is not int or value < 0 or type(stamp) not in (int, float)
            or not math.isfinite(stamp)):
        return result("invalid")
    if any(not isinstance(current.get(key), str) or not current[key]
           for key in ("identity", "epoch", "clock_epoch", "definition")):
        return result("invalid")
    if previous is None:
        return result("first")
    # A caller must only retain previous observations that passed validation.
    if current["identity"] != previous["identity"]:
        return result("identity_changed")
    if current["definition"] != previous["definition"] or current["unit"] != previous["unit"]:
        return result("definition_changed")
    if current["epoch"] != previous["epoch"] or current["clock_epoch"] != previous["clock_epoch"]:
        return result("reset")
    elapsed = current["time"] - previous["time"]
    if elapsed == 0:
        return result("duplicate" if value == previous["value"] else "conflicting_duplicate")
    if elapsed < 0:
        return result("out_of_order")
    if elapsed > max_gap_seconds:
        return result("gap")
    if value < previous["value"]:
        # A decrease alone cannot distinguish wrap, reset or a bad sample.
        return result("decrease")
    # Difference is computed as an integer BEFORE conversion, preserving small
    # increments of counters larger than 2**53.
    rate = Fraction(value - previous["value"]) * SCALE[current["unit"]] / Fraction(str(elapsed))
    return result("ok", float(rate))


def bounded_counter_delta(previous, current, bits, continuity_proven,
                          reset_changed=False, max_increment=None):
    """Modulo recovery is conditional on externally proven lifetime and bound.

    A missing reset marker does NOT prove continuity. max_increment must bound
    the *accounted quantity*, not wall time (parallel disk I/O may overlap).
    """
    if type(bits) is not int or not 1 <= bits <= 64:
        raise ValueError("unsupported counter width")
    modulus = 1 << bits
    if any(type(v) is not int or not 0 <= v < modulus for v in (previous, current)):
        return {"quality": "invalid", "delta": None}
    if reset_changed:
        return {"quality": "reset", "delta": None}
    if not continuity_proven:
        return {"quality": "continuity_unknown", "delta": None}
    if type(max_increment) is not int or not 0 <= max_increment < modulus:
        return {"quality": "wrap_count_unknown", "delta": None}
    delta = (current - previous) % modulus
    if delta > max_increment:
        return {"quality": "bound_violated", "delta": None}
    return {"quality": "wrap_candidate" if current < previous else "ok", "delta": delta}


def cpu_clock_quality(before, after, thread_counts, tolerance=0.01):
    """tolerance is a reference policy, not a kernel guarantee/calibration."""
    if not 0 < tolerance < 1:
        raise ValueError("invalid tolerance")
    elapsed = (after["monotonic_ns"] - before["monotonic_ns"]) / 1e9
    cpu = (after["process_cpu_ns"] - before["process_cpu_ns"]) / 1e9
    raw = (after["raw_midpoint_ns"] - before["raw_midpoint_ns"]) / 1e9
    if elapsed <= 0 or raw <= 0 or cpu < 0:
        raise ValueError("invalid or changed clock epoch")
    flags = []
    if thread_counts == [1, 1] and cpu / elapsed > 1 + tolerance:
        flags.append("single_thread_cpu_over_monotonic")
    if abs(elapsed / raw - 1) > tolerance:
        flags.append("monotonic_raw_rate_difference")
    if "single_thread_cpu_over_monotonic" in flags and abs(cpu / raw - 1) <= tolerance:
        flags.append("clock_slew_suspected")
    return {"quality_flags": flags, "cpu_over_monotonic": cpu / elapsed,
            "cpu_over_raw": cpu / raw, "monotonic_over_raw": elapsed / raw}


def nullable_number(value, present=True):
    if not present:
        return {"quality": "absent", "value": None}
    if value is None:
        return {"quality": "null", "value": None}
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError("not a numeric scalar")
    if isinstance(value, str) and not re.fullmatch(r"[+-]?\d+(?:\.\d+)?", value):
        raise ValueError("not a decimal value")
    number = int(value) if isinstance(value, (str, int)) and "." not in str(value) else float(value)
    if isinstance(number, float) and not math.isfinite(number):
        raise ValueError("non-finite number")
    return {"quality": "known", "value": number}


def pg_activity_visibility(row):
    # Null alone is insufficient to diagnose permissions.
    if row.get("query") == "<insufficient privilege>":
        return {"visibility": "restricted", "state": None}
    return {"visibility": "unknown" if row.get("state") is None else "visible",
            "state": row.get("state")}


def mysql_replica_xml(text):
    """Select SHOW REPLICA STATUS from mysql --xml multi-result output.

    The recorded client also emitted a separate completion-marker SELECT.
    Never interpret that marker resultset as a replica row.
    """
    try:
        envelope = ET.fromstring("<results>" + re.sub(r"<\?xml[^>]*\?>", "", text) + "</results>")
    except ET.ParseError as exc:
        raise ValueError("malformed mysql XML") from exc
    matches = [node for node in envelope.findall("resultset")
               if node.get("statement", "").strip().upper() == "SHOW REPLICA STATUS"]
    if len(matches) != 1:
        raise ValueError("expected one SHOW REPLICA STATUS resultset")
    root = matches[0]
    rows = root.findall("row")
    if len(rows) != 1:
        raise ValueError("expected one selected replication channel")
    row = {}
    for field in rows[0].findall("field"):
        name = field.attrib["name"]
        if name in row:
            raise ValueError("duplicate column")
        nil = field.get("{http://www.w3.org/2001/XMLSchema-instance}nil")
        row[name] = None if nil in ("true", "1") else (field.text or "")
    required = ("Source_Log_File", "Relay_Source_Log_File", "Read_Source_Log_Pos",
                "Exec_Source_Log_Pos", "Replica_IO_Running", "Replica_SQL_Running",
                "Seconds_Behind_Source")
    if any(k not in row for k in required):
        raise ValueError("incomplete replica status")
    read = nullable_number(row["Read_Source_Log_Pos"])["value"]
    executed = nullable_number(row["Exec_Source_Log_Pos"])["value"]
    positions_match = (bool(row["Source_Log_File"]) and
                       row["Source_Log_File"] == row["Relay_Source_Log_File"] and
                       read is not None and executed is not None and read == executed)
    return {"lag": nullable_number(row["Seconds_Behind_Source"]),
            "io": row["Replica_IO_Running"], "sql": row["Replica_SQL_Running"],
            "positions_match": positions_match,
            "source_freshness_proven": False}


def selected_watch_delete(event_type, get_status):
    if event_type != "DELETED":
        raise ValueError("this contract handles a selected watch DELETED only")
    # Recheck outcomes are point observations. 404 does not prove deletion cause.
    state = {200: "present_at_recheck", 404: "absent_at_recheck"}.get(get_status, "unknown")
    return {"selected_membership": "removed", "object_state": state,
            "physical_deletion_proven": False}


def uid_transition(previous_uid, current_uid, deleted_event_uid=None):
    if not previous_uid or not current_uid:
        raise ValueError("UIDs required")
    return {"identity": "same" if previous_uid == current_uid else "replaced",
            "remove_current": deleted_event_uid is not None and deleted_event_uid == current_uid}


def cloudwatch_page(response):
    results = []
    for item in response.get("MetricDataResults", []):
        stamps, values = item.get("Timestamps", []), item.get("Values", [])
        if len(stamps) != len(values):
            raise ValueError("timestamp/value cardinality mismatch")
        status = item.get("StatusCode")
        if status not in ("Complete", "PartialData", "InternalError", "Forbidden"):
            raise ValueError("unknown result status")
        results.append({"id": item["Id"], "status": status,
                        "points": [list(p) for p in sorted(zip(stamps, values))],
                        "complete": status == "Complete",
                        "messages": item.get("Messages", [])})
    return {"results": results, "next_token": response.get("NextToken")}


def azure_sample(value, present=True):
    observation = nullable_number(value, present)
    observation["zero_proves_no_activity"] = False
    return observation


def otlp_http_response(status, body):
    """Decoded OTLP/HTTP traces JSON only; acceptance is this hop.

    HTTP 200 is the specified success code, not any arbitrary 2xx. ProtoJSON
    null leaves a field unset; this does not generalize to SQL/cloud NULL.
    Counts must be nonnegative int64. This is not a complete wire decoder.
    """
    if status != 200:
        return {"outcome": "failure", "retryable": status in (429, 502, 503, 504),
                "rejected_spans": None, "end_to_end_stored": None,
                "warning": False, "error_message": None}
    if not isinstance(body, dict):
        raise ValueError("expected decoded ExportTraceServiceResponse")
    partial = body.get("partialSuccess")
    if partial is None:
        partial = {}
    if not isinstance(partial, dict):
        raise ValueError("invalid partialSuccess")
    raw = partial.get("rejectedSpans")
    if raw is None:
        raw = 0
    if (type(raw) not in (str, int, float)
            or not re.fullmatch(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?", str(raw))
            or (type(raw) is float and abs(raw) > 2**53)):
        raise ValueError("invalid or imprecisely decoded rejectedSpans")
    number = Decimal(str(raw))
    if number < 0 or number > 2**63-1 or number != number.to_integral_value():
        raise ValueError("invalid rejectedSpans")
    rejected = int(number)
    message = partial.get("errorMessage")
    if message is None:
        message = ""
    if not isinstance(message, str):
        raise ValueError("invalid errorMessage")
    partial_present = rejected != 0 or bool(message)
    return {"outcome": "partial_success" if partial_present else "hop_success",
            "retryable": False, "rejected_spans": rejected, "end_to_end_stored": None,
            "warning": rejected == 0 and bool(message), "error_message": message}


def repeated_receipts(attempts):
    """Keys are (tenant, trace_id, span_id); does not implement storage dedup."""
    keys = [tuple(key) for attempt in attempts for key in attempt]
    if any(len(k) != 3 or not all(isinstance(v, str) and v for v in k) for k in keys):
        raise ValueError("scoped identity required")
    return {"received_items": len(keys), "unique_keys": len(set(keys)),
            "repeated_items": len(keys) - len(set(keys))}


def collector_failure_samples(snapshots, metric="otelcol_exporter_send_failed_spans_total"):
    """One exporter lifetime; sum disjoint error label series, not requests."""
    values = []
    for text in snapshots:
        rows = []
        for line in text.splitlines():
            if re.match(re.escape(metric) + r"(?:\{|\s)", line):
                token = line.rsplit(" ", 1)[-1]
                rows.append(float(token))
        if not rows or any(not math.isfinite(x) or x < 0 for x in rows):
            raise ValueError("metric missing or invalid; do not synthesize zero")
        values.append(sum(rows))
    if len(values) < 2 or any(b < a for a, b in zip(values, values[1:])):
        raise ValueError("insufficient samples or reset")
    return {"values": values, "delta": values[-1] - values[0],
            "first_increase_index": next((i for i, v in enumerate(values) if v > values[0]), None)}


def named_proc_pairs(text):
    lines = [s.split() for s in text.splitlines() if s.strip()]
    if len(lines) % 2:
        raise ValueError("unpaired proc header")
    result = {}
    for header, row in zip(lines[::2], lines[1::2]):
        if header[0] != row[0] or len(header) != len(row) or len(set(header[1:])) != len(header[1:]):
            raise ValueError("mismatched proc header/value row")
        prefix = header[0].removesuffix(":")
        for name, value in zip(header[1:], row[1:]):
            key = prefix + "." + name
            if key in result:
                raise ValueError("duplicate proc key")
            result[key] = int(value)
    return result


def diskstats_row(text):
    fields = text.split()
    # Narrow modern Linux format: 11 mandatory + optional discard(4)/flush(2).
    if len(fields) not in (14, 18, 20):
        raise ValueError("unsupported diskstats layout")
    major, minor = int(fields[0]), int(fields[1])
    stats = [int(v) for v in fields[3:]]
    if any(v < 0 for v in stats):
        raise ValueError("negative disk counter")
    return {"major": major, "minor": minor, "device": fields[2],
            "reads_completed": stats[0], "sectors_read": stats[2],
            "read_time_ms": stats[3], "in_flight": stats[8], "io_time_ms": stats[9]}


def psi_rows(text):
    result = {}
    for line in text.splitlines():
        tokens = line.split()
        if not tokens:
            continue
        kind = tokens[0]
        if kind not in ("some", "full") or kind in result:
            raise ValueError("unknown/duplicate PSI row")
        pairs = [token.split("=", 1) for token in tokens[1:]]
        row = dict(pairs)
        if len(row) != len(pairs) or set(row) != {"avg10", "avg60", "avg300", "total"}:
            raise ValueError("unexpected PSI fields")
        result[kind] = {k: int(v) if k == "total" else float(v) for k,v in row.items()}
        if any(not math.isfinite(v) or v < 0 for v in result[kind].values()):
            raise ValueError("invalid PSI value")
    return result


def histogram_interpolation(buckets, quantile, threshold, mode):
    """Finite positive buckets only; counts are per-bucket, not cumulative.

    linear: classic/custom native; exponential: standard native positive bucket.
    Zero/negative/+Inf/NaN buckets and mixed-schema merge need separate contracts.
    """
    if mode not in ("linear", "exponential") or not 0 < quantile < 1:
        raise ValueError("unsupported histogram mode/quantile")
    total = sum(n for _, _, n in buckets)
    if total <= 0 or not math.isfinite(threshold):
        raise ValueError("empty/invalid histogram")
    previous_high = None
    cumulative, fraction_count, answer = 0, 0.0, None
    for low, high, count in buckets:
        if not (0 < low < high and math.isfinite(high) and type(count) is int and count >= 0):
            raise ValueError("unsupported bucket")
        if previous_high is not None and low < previous_high:
            raise ValueError("overlapping buckets")
        previous_high = high
        if answer is None and count and cumulative < quantile * total <= cumulative + count:
            f = (quantile * total - cumulative) / count
            answer = low + f * (high-low) if mode == "linear" else low * (high/low)**f
        if threshold >= high:
            fraction_count += count
        elif threshold > low:
            f = ((threshold-low)/(high-low) if mode == "linear" else
                 math.log(threshold/low)/math.log(high/low))
            fraction_count += count*f
        cumulative += count
    return {"count": total, "quantile": answer, "fraction": fraction_count / total}
