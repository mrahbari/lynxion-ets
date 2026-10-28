# Phase 6 · Step 5 — Funding-Positioning (Carry) Hypotheses

_Funding-crowding → reversion. 1-year funding (BTC/ETH/SOL) forward-filled onto 15m bars (lookahead-safe: settlement ≤ bar). Horizons [16, 96, 384] (4h/1d/4d). Aligned funding coverage: {'BTC-USDT': 34968, 'ETH-USDT': 34981, 'SOL-USDT': 34981}. **Cumulative** family = 183, BH-FDR, default REJECT. Signal quality only._

## Verdicts

| hypothesis | overall | best IC (sym@h) | monotonicity@best | per-symbol |
|---|---|---|---|---|
| funding_revert | **ARCHIVE** | BTC-USDT@384: +0.183 (p=0.002) | +0.84 | BTC-USDT:ARCH, ETH-USDT:ARCH, SOL-USDT:ARCH |
| funding_z_revert | **ARCHIVE** | BTC-USDT@384: +0.082 (p=0.114) | +0.30 | BTC-USDT:ARCH, ETH-USDT:ARCH, SOL-USDT:ARCH |
| xs_funding_revert | **ARCHIVE** | SOL-USDT@384: -0.100 (p=0.071) | -0.85 | BTC-USDT:ARCH, ETH-USDT:ARCH, SOL-USDT:ARCH |

**PROMOTE: 0** — none
**PROVISIONAL: 0** — none
**ARCHIVE: 3**

**Strongest lead so far (archived, not promoted):** `funding_revert` at the **4-day
horizon for BTC** shows **IC +0.183 (p=0.002 HAC), decile monotonicity +0.84** — the
hypothesis *direction* is confirmed (high funding → forward reversion) and the
relationship is strongly monotonic, unlike the batch-1/2 reversion leads. It
archives because: (1) a 4-day horizon over 1 year gives only **~91 non-overlapping
windows**, so under the conservative **cumulative 183-test BH family** a single
p=0.002 does not survive; (2) it is **not cross-symbol robust** (ETH/SOL weaker).
This is sample-starvation, not absence of edge. **What it needs to be confirmable:**
**multi-year funding history** (more independent 4-day windows) and a **wider perp
universe** (cross-sectional breadth) — both achievable with the existing ingestion
pipeline. This is the highest-priority direction for the next discovery round.

_Caveat: only 3 highly-correlated majors over 1 year (~1095 funding points each) →
low cross-sectional breadth and limited independent samples; treat any signal as
provisional pending a wider universe + longer history. No tuning, no execution
simulation._
