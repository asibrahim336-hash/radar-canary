# radar-canary

Synthetic test store for [RadarLedger](https://github.com/asibrahim336-hash/RadarLedger) pipeline validation.

## Purpose

This public repo hosts a static HTML store on GitHub Pages. The RadarLedger pipeline treats it as a real watchlist entry (vertical=canary), running the same crawler, extractor, diff, severity, and routing code paths as production clients.

## Tracked Values

- Product A: €49.00
- Product B: €120.00 (with stock badge)
- Product C: €19.99
- Promo banner text

## Mutation Rotation

Automated by the custodian workflow (daily at 06:00 UTC):

| Day | Mutation | Expected Severity |
|-----|----------|-------------------|
| Mon | Product A price -12% | 9 (alert) |
| Tue | Promo text change | 8 (alert) |
| Wed | Product C price +5% | 5 (brief only) |
| Thu | Product B stockout | 8 (alert) |
| Fri | New Product D appears | 7 |
| Sat | Restore baseline | — |
| Sun | No change | Empty ledger |

## Acceptance

7/7 correct classifications per week, including Sunday silence. Any miss = red build.
