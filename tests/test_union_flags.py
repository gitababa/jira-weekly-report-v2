# tests/test_union_flags.py
from jira import JiraClient
from report import tag_issues

def test_union_jql_contains_end_plus_one_pattern():
    j = JiraClient.build_jql_union_window(
        "SUP", start="2025-11-01", end="2025-11-07"
    )
    # created < "2025-11-08" and resolved < "2025-11-08" should appear
    assert 'created < "2025-11-08"' in j
    assert 'resolved < "2025-11-08"' in j
    # snapshot uses resolved >= "2025-11-08"
    assert 'resolved >= "2025-11-08"' in j

def _issue(key, created, resolved=None):
    f = {"created": created}
    if resolved:
        f["resolved"] = resolved
    return {"key": key, "fields": f}

def test_flag_identity_equation():
    # Window 01..07
    start, end = "2025-11-01", "2025-11-07"

    issues = [
        _issue("IN", "2025-10-31T12:00:00.000+0000"),  # open before start -> counts in opening backlog
        _issue("C1", "2025-11-01T09:00:00.000+0000"),  # created in window
        _issue("C2", "2025-11-07T10:00:00.000+0000"),  # created on end day
        _issue("R1", "2025-10-30T10:00:00.000+0000", "2025-11-02T08:00:00.000+0000"),  # resolved in window
        _issue("R2", "2025-11-01T10:00:00.000+0000", "2025-11-05T08:00:00.000+0000"),  # created+resolved in window
        _issue("NEXT", "2025-11-07T11:00:00.000+0000", "2025-11-08T08:00:00.000+0000"), # created in window, resolved after end
    ]

    t = tag_issues(issues, start, end)
    c = t["counts"]
    # Opening backlog: IN (1)
    assert c["open_start"] == 1
    # Created in window: C1, C2, R2, NEXT (4)
    assert c["created"] == 4
    # Resolved in window: R1, R2 (2)
    assert c["resolved"] == 2
    # Closing backlog (open at end): IN, C1, C2, NEXT (4)
    assert c["open"] == 4
    # Identity holds
    assert c["open"] == c["open_start"] + c["created"] - c["resolved"]
