# report.py
from __future__ import annotations
from typing import Dict, List


def _day(s: str | None) -> str:
    """Return YYYY-MM-DD from an ISO datetime string (or '' if missing)."""
    return (s or "").strip()[:10]


def _resolved_day(fields: dict) -> str:
    """
    Prefer Jira REST 'resolutiondate'; fall back to 'resolved' for test fixtures / exports.
    """
    return _day(fields.get("resolutiondate") or fields.get("resolved"))


def _has_resolution(fields: dict) -> bool:
    """
    True if the issue is resolved (resolution object present) OR a resolution date exists.
    """
    return bool(fields.get("resolution")) or bool(fields.get("resolutiondate") or fields.get("resolved"))


def tag_issues(issues: List[dict], start: str, end: str) -> Dict[str, object]:
    """
    Flags per issue:
      - created_in_window  : start <= created <= end
      - resolved_in_window : (has resolution) AND (start <= resolutiondate <= end)
      - open_at_end        : created <= end AND (no resolution OR resolutiondate > end)
    """
    rows: List[dict] = []
    c_count = r_count = o_count = 0

    for it in issues:
        f = it.get("fields", {}) or {}
        c = _day(f.get("created"))
        r = _resolved_day(f)
        has_res = _has_resolution(f)

        created_in_window = bool(c and (start <= c <= end))
        resolved_in_window = bool(has_res and r and (start <= r <= end))
        open_at_end = bool(c and (c <= end) and (not has_res or (r and r > end)))

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
    Legacy API: return buckets as lists of issues using the new flags.
    """
    tagged = tag_issues(issues, start, end)["rows"]

    def _minimal(row: dict) -> dict:
        return {"key": row["key"], "fields": row["fields"]}

    created = [_minimal(r) for r in tagged if r["created_in_window"]]
    resolved = [_minimal(r) for r in tagged if r["resolved_in_window"]]
    open_in_window = [_minimal(r) for r in tagged if r["open_at_end"]]

    return {"created": created, "resolved": resolved, "open": open_in_window}
