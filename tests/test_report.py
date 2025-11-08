# tests/test_report.py
from report import format_report

def _issue(key: str, created: str, resolved: str | None):
    return {"key": key, "fields": {"created": created, "resolved": resolved}}

def test_format_report_identity_simple():
    issues = [
        _issue("A-1", "2025-11-01T10:00:00.000+0000", None),
        _issue("A-2", "2025-11-02T10:00:00.000+0000", "2025-11-05T09:00:00.000+0000"),
        _issue("A-3", "2025-11-03T10:00:00.000+0000", None),
        _issue("A-4", "2025-10-30T10:00:00.000+0000", "2025-11-02T09:00:00.000+0000"),
    ]
    buckets = format_report(issues, "2025-11-01", "2025-11-07")
    assert len(buckets["created"]) == 3     # A-1,A-2,A-3
    assert len(buckets["resolved"]) == 2    # A-2, A-4 (resolved in window)
    assert len(buckets["open"]) == 2        # A-1,A-3

def test_format_report_inclusive_edges():
    issues = [
        _issue("B-1", "2025-11-01T00:00:01.000+0000", None),
        _issue("B-2", "2025-11-07T23:59:59.000+0000", None),
        _issue("B-3", "2025-11-06T01:00:00.000+0000", "2025-11-07T08:00:00.000+0000"),
    ]
    b = format_report(issues, "2025-11-01", "2025-11-07")
    assert {i["key"] for i in b["created"]} == {"B-1", "B-2", "B-3"}
    assert {i["key"] for i in b["resolved"]} == {"B-3"}
    assert {i["key"] for i in b["open"]} == {"B-1", "B-2"}
