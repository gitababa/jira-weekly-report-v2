# report.py
from __future__ import annotations
from typing import Dict, List


def _day(s: str | None) -> str:
    """Return YYYY-MM-DD from an ISO datetime string (or '' if missing)."""
    return (s or "")[:10]


def _resolved_day(fields: dict) -> str:
    """
    Tests may provide 'resolved'; Jira REST provides 'resolutiondate'.
    Support both, preferring the real REST field when present.
    """
    return _day(fields.get("resolutiondate") or fields.get("resolved"))


def tag_issues(issues: List[dict], start: str, end: str) -> Dict[str, object]:
    """
    For each issue, compute boolean flags:
      - created_in_window     : start <= created <= end
      - resolved_in_window    : start <= (resolutiondate|resolved) <= end
      - open_at_end           : created <= end AND (no resolution OR resolution > end)

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
        r = _resolved_day(f)

        created_in_window = (start <= c <= end) if c else False
        resolved_in_window = (start <= r <= end) if r else False
        open_at_end = (c <= end) and (not r or r > end) if c else False

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

    created = [_minimal(r) for r in tagged if r["created_in_window"]]
    resolved = [_minimal(r) for r in tagged if r["resolved_in_window"]]
    open_in_window = [_minimal(r) for r in tagged if r["open_at_end"]]

    return {"created": created, "resolved": resolved, "open": open_in_window}
