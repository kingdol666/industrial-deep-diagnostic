---
name: cnc-temperature-range-underreport
description: CNC simulateData report claimed spindle_temp 35-65C(dT=30C) but actual data was 32.5-76.3C(dT=43.8C); temperature range approximation error in physical verification
metadata:
  type: feedback
---

CNC simulateData (endorsed diagnosis): Report stated spindle_temp range ~35-65C (dT=30C) in Section 3.2, but actual cleaned data range was 32.5-76.3C (dT=43.8C). The 46% understatement of dT was caught by independent verification. Interestingly, correcting dT to 43.8C makes the thermal expansion prediction closer to observation (ratio 1.22x instead of 1.74x), strengthening rather than weakening H2.

**Why:** Physical verification steps that approximate trend endpoints may systematically understate actual ranges when data has significant intra-day variation (first-day means can differ from absolute minimums).

**How to apply:** When verifying physical magnitude claims (deltaL = alpha * L0 * dT), always check against actual data quantiles (5th-95th percentile) rather than visual trend estimates. Report "~X to ~Y" ranges alongside actual min/max values for transparency.

Related memory: [[pg32d-w1c81-regime-shift-hidden]] — both cases involve claim-reality mismatch in temperature/magnitude ranges.
