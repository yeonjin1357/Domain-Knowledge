"""A deliberately narrow, two-sample cumulative-counter teaching contract.

This is not Prometheus rate(): no extrapolation and no hidden reset recovery.
Timestamps must come from the same monotonic clock epoch.
"""

from fractions import Fraction
import math

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
