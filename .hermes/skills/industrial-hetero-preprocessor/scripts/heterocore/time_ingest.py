"""time_ingest.py — E-1H's own time parser (plan v1.1 §4 time_ingest block).

R4 lesson: the repo's `_normalize_cn_datetime` silently drops HH:MM:SS for
`2026/10/15 08:30`, `2026-10-15 08:30:00`, `2026.10.15 08:30:00` while
`_parses_as_time` still reports 1.0 — a "parse-rate" gate built on it looks
perfect and loses the time of day. This module never reuses it: parsing is by
an explicit format catalog, ambiguity is refused (not guessed), Excel serials
and epoch values are detected explicitly, and timezone offsets are stripped to
naive anchor-local time with the original offset recorded.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%Y.%m.%d %H:%M:%S",
    "%Y.%m.%d %H:%M",
    "%Y年%m月%d日 %H:%M:%S",
    "%Y年%m月%d日 %H:%M",
    "%Y%m%d_%H%M%S",
    "%Y%m%d-%H%M%S",
    "%Y-%m-%d",
]
_TZ_RE = re.compile(r"(?:(Z)|([+-])(\d{2}):?(\d{2}))$")
_FILENAME_TS_RE = re.compile(r"(20\d{2})[_-]?(\d{2})[_-]?(\d{2})[_-]?(\d{2})?(\d{2})?(\d{2})?")
_EXCEL_EPOCH = datetime(1899, 12, 30)


class TimeValue:
    __slots__ = ("ts", "fmt", "flags", "tz_original")

    def __init__(self, ts, fmt, flags, tz_original=None):
        self.ts = ts                  # naive datetime | None
        self.fmt = fmt                # str | None
        self.flags = flags            # set[str]
        self.tz_original = tz_original

    def __repr__(self):  # pragma: no cover - debug aid
        return f"TimeValue({self.ts!r}, {self.fmt!r}, {sorted(self.flags)})"


def _strip_tz(text: str) -> tuple[str, str | None]:
    m = _TZ_RE.search(text)
    if not m:
        return text, None
    if m.group(1):
        return text[: m.start()], "UTC"
    sign = -1 if m.group(2) == "-" else 1
    off = sign * (int(m.group(3)) * 60 + int(m.group(4)))
    return text[: m.start()], f"UTC{'+' if off >= 0 else '-'}{abs(off) // 60:02d}:{abs(off) % 60:02d}"


def parse_ts(value) -> TimeValue:
    """Parse one scalar value. Never guesses ambiguous D/M vs M/D."""
    if value is None or (isinstance(value, float) and value != value):  # NaN
        return TimeValue(None, None, {"empty"})
    # numeric-ish paths
    if isinstance(value, (int, float)):
        return _parse_numeric(float(value))
    text = str(value).strip()
    if not text:
        return TimeValue(None, None, {"empty"})
    if re.fullmatch(r"-?\d+", text):
        return _parse_numeric(float(text))
    if re.fullmatch(r"-?\d+\.\d+", text):
        return _parse_numeric(float(text))
    body, tz = _strip_tz(text)
    flags: set = set()
    for fmt in FORMATS:
        try:
            ts = datetime.strptime(body, fmt)
        except ValueError:
            continue
        if tz:
            flags.add("tz_stripped")
        if "%d" in fmt and "%m" in fmt and "/" in fmt or "/" in fmt:
            # slash formats: check D/M vs M/D ambiguity (both fields <= 12 and different)
            parts = re.split(r"[./]", body.split(" ")[0])
            if len(parts) == 3:
                a, b = int(parts[1]), int(parts[2])
                if a <= 12 and b <= 12 and a != b:
                    flags.add("ambiguous_date_order")
        return TimeValue(ts, fmt, flags, tz)
    return TimeValue(None, None, {"unparsed"})


def _parse_numeric(v: float) -> TimeValue:
    """Excel serial (days since 1899-12-30, plausible range) or epoch s/ms."""
    if 20000 <= v <= 80000:  # 1954..2119 as excel serial
        ts = _EXCEL_EPOCH + timedelta(days=v)
        return TimeValue(ts, "excel_serial", {"excel_serial"})
    digits = int(v)
    if 10**12 <= digits < 10**14:  # epoch ms
        return TimeValue(datetime.fromtimestamp(v / 1000, tz=timezone.utc).replace(tzinfo=None), "epoch_ms", {"epoch"})
    if 10**9 <= digits < 10**11:  # epoch s (2001..5138)
        return TimeValue(datetime.fromtimestamp(v, tz=timezone.utc).replace(tzinfo=None), "epoch_s", {"epoch"})
    return TimeValue(None, None, {"unparsed"})


def parse_series(values) -> dict:
    """Parse a whole column. Returns {parsed:[TimeValue], ok_rate, format,
    ambiguous:int, midnight_only:bool, flags:set, tz_originals:set}."""
    parsed = [parse_ts(v) for v in values]
    non_empty = [p for p in parsed if "empty" not in p.flags]
    ok = [p for p in non_empty if p.ts is not None]
    ok_rate = (len(ok) / len(non_empty)) if non_empty else 0.0
    fmts = sorted({p.fmt for p in ok if p.fmt})
    fmt = fmts[0] if len(fmts) == 1 else ("|".join(fmts) if fmts else None)
    ambiguous = sum(1 for p in ok if "ambiguous_date_order" in p.flags)
    # H6b helper: any value with a non-midnight time of day?
    midnight_only = all(p.ts.hour == 0 and p.ts.minute == 0 and p.ts.second == 0 for p in ok) if ok else True
    flags: set = set()
    for p in parsed:
        flags |= p.flags
    tz_orig = {p.tz_original for p in parsed if p.tz_original}
    return {
        "parsed": parsed,
        "ok_rate": ok_rate,
        "format": fmt,
        "ambiguous": ambiguous,
        "midnight_only": midnight_only,
        "flags": flags,
        "tz_originals": tz_orig,
    }


def extract_filename_timestamp(name: str):
    """Extract `YYYYMMDD[-_]HHMM[SS]`-style timestamps from a file name."""
    m = _FILENAME_TS_RE.search(Path(name).stem)
    if not m:
        return None
    try:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        hh = int(m.group(4) or 0)
        mi = int(m.group(5) or 0)
        ss = int(m.group(6) or 0)
        return datetime(y, mo, d, hh, mi, ss)
    except ValueError:
        return None


def bucket_stats(parsed, cadence_hint_s=None) -> dict:
    """cadence/span/timestamps summary used by manifest sources[] blocks."""
    ts = sorted(p.ts for p in parsed if p.ts is not None)
    if not ts:
        return {"n": 0, "cadence_s": None, "span_s": None, "timestamps": []}
    gaps = [(b - a).total_seconds() for a, b in zip(ts, ts[1:]) if b > a]
    cadence = sorted(gaps)[len(gaps) // 2] if gaps else (cadence_hint_s or 0.0)
    return {
        "n": len(ts),
        "cadence_s": float(cadence) if cadence else None,
        "span_s": float((ts[-1] - ts[0]).total_seconds()),
        "timestamps": ts,
    }
