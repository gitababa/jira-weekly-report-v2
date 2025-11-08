# tests/test_jql.py
from jira import JiraClient

def test_jql_interval_build():
    j = JiraClient.build_jql("SUP", interval="7d")
    assert "project = SUP" in j
    assert "created >=" in j and "resolved >=" in j
    assert "statusCategory != Done" in j

def test_jql_date_build():
    j = JiraClient.build_jql("SUP", start="2025-11-01", end="2025-11-07")
    assert 'created >= "2025-11-01"' in j and 'created <= "2025-11-07"' in j
    assert 'resolved >= "2025-11-01"' in j and 'resolved <= "2025-11-07"' in j
    assert 'updated >=' in j and 'statusCategory != Done' in j
