#!/usr/bin/env python3
"""Canary Custodian — deterministic mutation of store.html based on weekday.

Pure function of (baseline, weekday) so reruns are idempotent.
Saturday restores values.json to baseline; Sunday exits 0 without committing.
"""

import json
import sys
from pathlib import Path

STORE_PATH = Path("store.html")
VALUES_PATH = Path("values.json")


def load_values() -> dict:
    with open(VALUES_PATH) as f:
        return json.load(f)


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
    """Apply the mutation for a given weekday."""
    data = load_values()
    baseline = data["baseline"]
    mutations = data["mutations"]

    if day == "sun":
        # Sunday: no change — exit without modifying anything
        print("Sunday: no change (false-positive test)")
        sys.exit(0)

    if day == "sat":
        # Saturday: restore baseline
        current_values = dict(baseline)
        show_product_d = False
        print("Saturday: restoring baseline")
    else:
        # Apply the day's mutation on top of baseline
        current_values = dict(baseline)
        day_mutation = mutations.get(day, {})

        for key, value in day_mutation.items():
            if key not in ("description", "restore", "no_change"):
                current_values[key] = value

        show_product_d = current_values.get("product_d_visible", False)
        print(f"{day}: {day_mutation.get('description', 'unknown mutation')}")

    # Render and write store.html
    html = render_store(current_values, show_product_d)
    STORE_PATH.write_text(html)

    # Update values.json to reflect current state (for idempotency tracking)
    if day == "sat":
        # Reset to pure baseline state
        data["current_state"] = dict(baseline)
    else:
        data["current_state"] = current_values
    data["last_mutation"] = day

    with open(VALUES_PATH, "w") as f:
        json.dump(data, f, indent=2)

    print(f"store.html updated for {day}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: custodian.py <weekday>")
        print("  weekday: mon|tue|wed|thu|fri|sat|sun")
        sys.exit(1)

    day = sys.argv[1].lower()[:3]
    valid_days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    if day not in valid_days:
        print(f"ERROR: Invalid day '{day}'. Must be one of: {valid_days}")
        sys.exit(1)

    apply_mutation(day)
