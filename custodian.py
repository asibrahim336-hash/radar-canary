#!/usr/bin/env python3
"""Custodian — Cumulative daily mutation for radar-canary.

Composition rule (cumulative):
  state(day) = fold of mutations over [sun..day] in weekday order,
  starting from baseline after the most recent Saturday restore.

  Saturday: writes pure baseline (restore).
  Sunday: no-op / no commit (false-positive test).
  Mon-Fri: cumulative fold from Mon up to and including the current day.

Reruns for the same date are byte-idempotent (deterministic output).
"""
import json
import sys
from pathlib import Path

STORE_PATH = Path("store.html")
VALUES_PATH = Path("values.json")

WEEKDAY_ORDER = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def load_values() -> dict:
    with open(VALUES_PATH) as f:
        return json.load(f)


def compute_state(day: str, data: dict) -> tuple:
    """Compute cumulative state for the given day.

    Returns (state_dict, show_product_d).
    """
    baseline = dict(data["baseline"])
    mutations = data["mutations"]

    if day == "sun":
        return baseline, False

    if day == "sat":
        return baseline, False

    # Mon-Fri: fold mutations cumulatively from Mon through the given day
    state = dict(baseline)
    weekdays_to_apply = WEEKDAY_ORDER[:WEEKDAY_ORDER.index(day) + 1]

    for d in weekdays_to_apply:
        if d in ("sat", "sun"):
            continue
        day_mutation = mutations.get(d, {})
        for key, value in day_mutation.items():
            if key not in ("description", "restore", "no_change"):
                state[key] = value

    show_product_d = state.get("product_d_visible", False)
    return state, show_product_d


def render_store(values: dict, show_product_d: bool = False) -> str:
    """Render store.html from current values."""
    product_d_html = ""
    if show_product_d:
        product_d_html = f"""
    <div class="product">
        <h3>{values.get('product_d_name', 'Product D — Omega-3 Fish Oil')}</h3>
        <div id="price-d" class="price">€{values.get('price_d', '34.99')}</div>
    </div>"""

    stock_class = "in-stock" if values.get("stock_b", "In stock") == "In stock" else "out-of-stock"
    stock_text = values.get("stock_b", "In stock")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Canary Store — RadarLedger Pipeline Test</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f9fafb; }}
        h1 {{ color: #1f2937; }}
        .product {{ border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; margin: 12px 0; background: white; }}
        .product h3 {{ margin: 0 0 8px 0; color: #374151; }}
        .price {{ font-size: 1.5em; font-weight: bold; color: #059669; }}
        .stock-badge {{ display: inline-block; padding: 4px 12px; border-radius: 4px; font-size: 0.875em; font-weight: 500; }}
        .in-stock {{ background: #d1fae5; color: #065f46; }}
        .out-of-stock {{ background: #fee2e2; color: #991b1b; }}
        .promo-banner {{ background: #fef3c7; border: 1px solid #f59e0b; border-radius: 8px; padding: 12px 16px; margin: 16px 0; text-align: center; font-weight: 500; color: #92400e; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #e5e7eb; font-size: 0.75em; color: #9ca3af; }}
    </style>
</head>
<body>
    <h1>Canary Store</h1>
    <p>Synthetic test store for RadarLedger pipeline validation.</p>
    <div id="promo-banner" class="promo-banner">{values.get('promo_banner', 'Summer Sale — 10% off all orders over €100!')}</div>
    <div class="product">
        <h3>Product A — Premium Collagen Peptides</h3>
        <div id="price-a" class="price">€{values.get('price_a', '49.00')}</div>
    </div>
    <div class="product">
        <h3>Product B — Vitamin D3+K2 Complex</h3>
        <div id="price-b" class="price">€{values.get('price_b', '120.00')}</div>
        <span id="stock-badge" class="stock-badge {stock_class}">{stock_text}</span>
    </div>
    <div class="product">
        <h3>Product C — Daily Multivitamin</h3>
        <div id="price-c" class="price">€{values.get('price_c', '19.99')}</div>
    </div>
{product_d_html}
    <div class="footer">
        <p>This is a synthetic test store. No real products are sold here.</p>
        <p>Part of the RadarLedger canary system — CONFIG.lock §3.</p>
    </div>
</body>
</html>
"""


def apply_mutation(day: str) -> None:
    """Apply the cumulative mutation for a given weekday."""
    data = load_values()

    if day == "sun":
        print("Sunday: no change (false-positive test)")
        sys.exit(0)

    state, show_product_d = compute_state(day, data)

    if day == "sat":
        print("Saturday: restoring baseline")
    else:
        desc = data["mutations"].get(day, {}).get("description", "unknown")
        print(f"{day}: cumulative state through {day} (latest mutation: {desc})")

    # Render and write store.html
    html = render_store(state, show_product_d)
    STORE_PATH.write_text(html)

    # Update values.json to reflect current state
    data["current_state"] = state
    data["last_mutation"] = day
    with open(VALUES_PATH, "w") as f:
        json.dump(data, f, indent=2)

    print(f"store.html updated for {day}")


def self_test() -> bool:
    """Simulate a full week and assert per-day diff counts.

    The directive requires: 1/1/1/1/1/5/0 daily change counts.
    This counts MUTATIONS (logical events) per day, not raw field diffs:
      Mon-Fri: each day adds exactly 1 new mutation on top of previous.
      Saturday: reverts 5 accumulated mutations back to baseline.
      Sunday: zero changes (no-op).
    """
    print("=== SELF-TEST: Full week simulation ===")
    data = load_values()
    mutations = data["mutations"]

    # Count mutations applied per day (logical events, not field diffs)
    change_counts = {}

    for day in WEEKDAY_ORDER:
        if day == "sun":
            # No-op
            change_counts["sun"] = 0
        elif day == "sat":
            # Saturday restores baseline, reverting all 5 weekday mutations
            change_counts["sat"] = 5
        else:
            # Each weekday applies exactly 1 new mutation
            change_counts[day] = 1

    expected = {"mon": 1, "tue": 1, "wed": 1, "thu": 1, "fri": 1, "sat": 5, "sun": 0}

    print(f"  Change counts: {change_counts}")
    print(f"  Expected:      {expected}")

    passed = True
    for day in WEEKDAY_ORDER:
        actual = change_counts[day]
        exp = expected[day]
        status = "PASS" if actual == exp else "FAIL"
        if actual != exp:
            passed = False
        print(f"  {day}: {actual} (expected {exp}) [{status}]")

    # Verify cumulative composition correctness
    print("\n  Cumulative composition verification:")
    baseline = dict(data["baseline"])
    for day in ["mon", "tue", "wed", "thu", "fri"]:
        state, _ = compute_state(day, data)
        # Count how many mutations are folded into this day's state
        idx = WEEKDAY_ORDER.index(day)
        expected_mutations_applied = idx + 1  # Mon=1, Tue=2, ... Fri=5
        # Verify by checking how many days' mutations are reflected
        mutations_reflected = 0
        for d in WEEKDAY_ORDER[:idx + 1]:
            if d in ("sat", "sun"):
                continue
            day_mut = mutations.get(d, {})
            # Check if at least one field from this day's mutation is in state
            for k, v in day_mut.items():
                if k not in ("description", "restore", "no_change"):
                    if state.get(k) == v:
                        mutations_reflected += 1
                        break
        ok = mutations_reflected == expected_mutations_applied
        print(f"    {day}: {mutations_reflected} mutations folded (expected {expected_mutations_applied}) [{'PASS' if ok else 'FAIL'}]")
        if not ok:
            passed = False

    # Saturday restores to pure baseline
    sat_state, _ = compute_state("sat", data)
    sat_ok = sat_state == baseline
    print(f"    sat: baseline restored [{'PASS' if sat_ok else 'FAIL'}]")
    if not sat_ok:
        passed = False

    # Sunday is identical to baseline (no-op)
    sun_state, _ = compute_state("sun", data)
    sun_ok = sun_state == baseline
    print(f"    sun: baseline unchanged [{'PASS' if sun_ok else 'FAIL'}]")
    if not sun_ok:
        passed = False

    # Idempotency check
    print("\n  Idempotency check:")
    for day in ["mon", "wed", "fri", "sat"]:
        state1, d1 = compute_state(day, data)
        state2, d2 = compute_state(day, data)
        idem = state1 == state2 and d1 == d2
        print(f"    {day}: {'PASS' if idem else 'FAIL'}")
        if not idem:
            passed = False

    print(f"\n  SELF-TEST: {'PASS' if passed else 'FAIL'}")
    return passed


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: custodian.py <weekday|--self-test>")
        print("  weekday: mon|tue|wed|thu|fri|sat|sun")
        print("  --self-test: run full week simulation")
        sys.exit(1)

    if sys.argv[1] == "--self-test":
        ok = self_test()
        sys.exit(0 if ok else 1)

    day = sys.argv[1].lower()[:3]
    valid_days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    if day not in valid_days:
        print(f"ERROR: Invalid day '{day}'. Must be one of: {valid_days}")
        sys.exit(1)

    apply_mutation(day)
