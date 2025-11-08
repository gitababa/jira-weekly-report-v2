# report.py
from __future__ import annotations
from typing import Dict, List


def _day(s: str | None) -> str:
    return (s or "")[:10]


def format_report(issues: List[dict], start: str, end: str) -> Dict[str, List[dict]]:
    """
    Bucketing rules (inclusive dates by day):
      - created:   issue.fields.created in [start,end]
      - resolved:  issue.fields.resolved in [start,end]
      - open:      created minus resolved (by key)  => ensures created - resolved = open
    """
    created: List[dict] = []
    resolved: List[dict] = []

    for it in issues:
        f = it.get("fields", {})
        c = _day(f.get("created"))
        r = _day(f.get("resolved"))
        if start <= c <= end:
            created.append(it)
        if r and (start <= r <= end):
            resolved.append(it)

    resolved_keys = {it.get("key") for it in resolved}
    open_in_window = [it for it in created if it.get("key") not in resolved_keys]

    return {"created": created, "resolved": resolved, "open": open_in_window}
