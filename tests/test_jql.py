# tests/test_jql.py
from jira import JiraClient

def test_jql_created_interval_build():
    j = JiraClient.build_jql_created("SUP", interval="7d")
    assert "project = SUP" in j
    assert "created >=" in j

def test_jql_created_date_build():
    j = JiraClient.build_jql_created("SUP", start="2025-11-01", end="2025-11-07")
    assert 'created >= "2025-11-01"' in j and 'created <= "2025-11-07"' in j

def test_jql_resolved_interval_build():
    j = JiraClient.build_jql_resolved("SUP", interval="7d")
    assert "resolved >=" in j and "resolved IS NOT EMPTY" in j

def test_jql_resolved_date_build():
    j = JiraClient.build_jql_resolved("SUP", start="2025-11-01", end="2025-11-07")
    assert 'resolved >= "2025-11-01"' in j and 'resolved <= "2025-11-07"' in j and "IS NOT EMPTY" in j

def test_jql_open_asof_end_build():
    j = JiraClient.build_jql_open_asof_end("SUP", end="2025-11-07")
    assert 'created <= "2025-11-07"' in j and 'resolved > "2025-11-07"' in j
