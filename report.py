# report.py
from __future__ import annotations
from typing import Dict, List

def _day(s: str | None) -> str:
    return (s or "")[:10]

def tag_issues(issues: List[dict], start: str, end: str) -> Dict[str, object]:
    """
    For each issue, compute boolean flags:
      - created_in_window
      - resolved_in_window  (uses resolutiondate)
      - open_at_end        (created <= end AND (no resolutiondate OR resolutiondate > end))
    Returns:
      {
        "rows": [ { "key": ..., "fields": {...}, "created_in_window": bool, "resolved_in_window": bool, "open_at_end": bool }, ... ],
        "counts": { "created": int, "resolved": int, "open": int }
      }
    """
    rows: List[dict] = []
    c_count = r_count = o_count = 0

    for it in issues:
        f = it.get("fields", {})
        c = _day(f.get("created"))
        r = _day(f.get("resolutiondate"))
        created_in_window = (start <= c <= end)
        resolved_in_window = (bool(r) and (start <= r <= end))
        open_at_end = (c <= end) and (not r or r > end)

        if created_in_window: c_count += 1
        if resolved_in_window: r_count += 1
        if open_at_end: o_count += 1

        rows.append({
            "key": it.get("key"),
            "fields": f,
            "created_in_window": created_in_window,
            "resolved_in_window": resolved_in_window,
            "open_at_end": open_at_end,
        })

    return {"rows": rows, "counts": {"created": c_count, "resolved": r_count, "open": o_count}}
