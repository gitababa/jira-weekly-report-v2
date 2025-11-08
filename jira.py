# jira.py
from __future__ import annotations
import os
from typing import Any, Dict, List, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")


class JiraClient:
    def __init__(self, base_url: Optional[str] = None, email: Optional[str] = None, api_token: Optional[str] = None):
        base = (base_url or JIRA_BASE_URL or "").rstrip("/")
        self.base_url = f"{base}/rest/api/3/"
        self.auth = (email or JIRA_EMAIL, api_token or JIRA_API_TOKEN)
        if not all(self.auth) or not base.startswith("http"):
            raise RuntimeError("JiraClient: missing or invalid JIRA_BASE_URL / JIRA_EMAIL / JIRA_API_TOKEN")

        self.sess = requests.Session()
        retry = Retry(total=5, backoff_factor=0.6, status_forcelist=(429, 500, 502, 503, 504), allowed_methods=None)
        self.sess.mount("https://", HTTPAdapter(max_retries=retry))
        self.sess.headers.update({"Accept": "application/json"})

    @staticmethod
    def _merge_filters(extra_filters: str) -> str:
        f = (extra_filters or "").strip()
        if not f:
            return ""
        up = f.upper()
        if up.startswith("AND ") or up.startswith("OR "):
            return " " + f
        return " AND " + f

    # -------- simple builders kept for tests/back-compat (unchanged) --------
    @staticmethod
    def build_jql_created(project_key: str, *, start: Optional[str] = None, end: Optional[str] = None,
                          interval: Optional[str] = None, extra_filters: str = "") -> str:
        if interval and (start or end):
            raise ValueError("Provide either (start & end) OR interval, not both.")
        if interval:
            term = f"created >= -{interval}"
        else:
            if not (start and end):
                raise ValueError("When interval is not given, 'start' and 'end' are required (YYYY-MM-DD).")
            term = f'created >= "{start}" AND created <= "{end}"'
        return f"project = {project_key} AND {term}{JiraClient._merge_filters(extra_filters)}"

    @staticmethod
    def build_jql_resolved(project_key: str, *, start: Optional[str] = None, end: Optional[str] = None,
                           interval: Optional[str] = None, extra_filters: str = "") -> str:
        if interval and (start or end):
            raise ValueError("Provide either (start & end) OR interval, not both.")
        if interval:
            term = f"resolved >= -{interval} AND resolved IS NOT EMPTY"
        else:
            if not (start and end):
                raise ValueError("When interval is not given, 'start' and 'end' are required (YYYY-MM-DD).")
            term = f'resolved >= "{start}" AND resolved <= "{end}" AND resolved IS NOT EMPTY'
        return f"project = {project_key} AND {term}{JiraClient._merge_filters(extra_filters)}"

    @staticmethod
    def build_jql_open_asof_end(project_key: str, *, end: str, extra_filters: str = "") -> str:
        term = f'created <= "{end}" AND (resolved IS EMPTY OR resolved > "{end}")'
        return f"project = {project_key} AND {term}{JiraClient._merge_filters(extra_filters)}"

    # ------------------------ unified union builder used at runtime ------------------------
    @staticmethod
    def build_jql_union_window(
        project_key: str,
        *,
        start: Optional[str] = None,
        end: Optional[str] = None,
        interval: Optional[str] = None,
        extra_filters: str = "",
    ) -> str:
        """
        Union of:
          - Created in window
          - Resolved in window (via 'resolved' alias + IS NOT EMPTY)
          - Open as-of end (created <= end AND (resolved IS EMPTY OR resolved > end))

        Rolling-days: created/resolved use interval; snapshot still needs a concrete end.
        Custom/last-week: wrap dates with startOfDay()/endOfDay() for inclusive edges.
        """
        # Allow interval + end (snapshot), but not interval + start
        if interval and start:
            raise ValueError("When using 'interval', do not pass 'start'; provide 'end' only for the snapshot.")

        if interval:
            if not end:
                raise ValueError("Union JQL with 'interval' also requires a concrete 'end' date for open-as-of-end.")
            end_expr = f'endOfDay("{end}")'
            created_term = f"created >= -{interval}"
            resolved_term = f"resolved >= -{interval} AND resolved IS NOT EMPTY"
            open_term = f"(created <= {end_expr} AND (resolved IS EMPTY OR resolved > {end_expr}))"
        else:
            if not (start and end):
                raise ValueError("Union JQL requires 'start' and 'end' (YYYY-MM-DD) when 'interval' is not used.")
            start_expr = f'startOfDay("{start}")'
            end_expr = f'endOfDay("{end}")'
            created_term = f"(created >= {start_expr} AND created <= {end_expr})"
            # **Back to 'resolved' alias here** — more reliable in JQL date comparisons
            resolved_term = f"(resolved >= {start_expr} AND resolved <= {end_expr} AND resolved IS NOT EMPTY)"
            open_term = f"(created <= {end_expr} AND (resolved IS EMPTY OR resolved > {end_expr}))"

        filters = JiraClient._merge_filters(extra_filters)
        core = f"( {created_term} OR {resolved_term} OR {open_term} )"
        return f"project = {project_key} AND {core}{filters}"

    # ------------------------ enhanced search ------------------------
    def _search_enhanced(self, jql: str, fields: str = "*all", next_page_token: Optional[str] = None) -> Dict[str, Any]:
        url = self.base_url + "search/jql"
        params = {"jql": jql, "maxResults": 100}
        if fields:
            params["fields"] = fields
        if next_page_token:
            params["nextPageToken"] = next_page_token
        resp = self.sess.get(url, params=params, auth=self.auth, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def get_issues(self, jql: str) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        token: Optional[str] = None
        wanted_fields = "summary,issuetype,status,assignee,created,resolutiondate,resolution,updated,key"
        guard = 0
        while True:
            data = self._search_enhanced(jql, fields=wanted_fields, next_page_token=token)
            issues.extend(data.get("issues", []))
            token = data.get("nextPageToken")
            if not token:
                break
            guard += 1
            if guard > 500:
                break
        return issues
