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
        "rows": [
          {
            "key": str,
            "fields": dict,
            "created_in_window": bool,
            "resolved_in_window": bool,
            "open_at_end": bool
          }, ...
        ],
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

        if created_in_window:
            c_count += 1
        if resolved_in_window:
            r_count += 1
        if open_at_end:
            o_count += 1

        rows.append(
            {
                "key": it.get("key"),
                "fields": f,
                "created_in_window": created_in_window,
                "resolved_in_window": resolved_in_window,
                "open_at_end": open_at_end,
            }
        )

    return {"rows": rows, "counts": {"created": c_count, "resolved": r_count, "open": o_count}}


# ---- Back-compat shim for existing tests ----
def format_report(issues: List[dict], start: str, end: str) -> Dict[str, List[dict]]:
    """
    Legacy API used by tests: return buckets as lists of issues.
    Uses the flags produced by tag_issues to derive:
      - "created":  issues created within [start, end]
      - "resolved": issues resolved within [start, end]
      - "open":     issues still open at end of window
    Each item is a minimal {"key": ..., "fields": {...}} dict (matching the tests' expectations).
    """
    tagged = tag_issues(issues, start, end)["rows"]

    def _minimal(row: dict) -> dict:
        return {"key": row["key"], "fields": row["fields"]}

    created = [_minimal(r) if r["created_in_window"] else None for r in tagged]
    created = [x for x in created if x is not None]

    resolved = [_minimal(r) if r["resolved_in_window"] else None for r in tagged]
    resolved = [x for x in resolved if x is not None]

    open_in_window = [_minimal(r) if r["open_at_end"] else None for r in tagged]
    open_in_window = [x for x in open_in_window if x is not None]

    return {"created": created, "resolved": resolved, "open": open_in_window}
