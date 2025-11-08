# jira.py
from __future__ import annotations
import os
from typing import Any, Dict, List, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")  # e.g. https://your-domain.atlassian.net
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")


class JiraClient:
    """
    Minimal Jira client using the ENHANCED search endpoint:
      GET /rest/api/3/search/jql  (with nextPageToken)
    """

    def __init__(self, base_url: Optional[str] = None, email: Optional[str] = None, api_token: Optional[str] = None):
        base = (base_url or JIRA_BASE_URL or "").rstrip("/")
        self.base_url = f"{base}/rest/api/3/"
        self.auth = (email or JIRA_EMAIL, api_token or JIRA_API_TOKEN)
        if not all(self.auth) or not base.startswith("http"):
            raise RuntimeError("JiraClient: missing or invalid JIRA_BASE_URL / JIRA_EMAIL / JIRA_API_TOKEN")

        self.sess = requests.Session()
        retry = Retry(total=5, backoff_factor=0.6, status_forcelist=(429, 500, 502, 503, 504), allowed_methods=False)
        self.sess.mount("https://", HTTPAdapter(max_retries=retry))
        self.sess.headers.update({"Accept": "application/json"})

    @staticmethod
    def _merge_filters(extra_filters: str) -> str:
        """
        Accepts strings that might already begin with 'AND ' or 'OR ' (as created by the config builder).
        Returns a prefix-safe clause to concatenate to the main JQL.
        """
        f = (extra_filters or "").strip()
        if not f:
            return ""
        up = f.upper()
        if up.startswith("AND ") or up.startswith("OR "):
            return " " + f  # already has logical operator
        return " AND " + f  # add AND by default

    # ---------- New explicit JQL builders (3 independent queries) ----------

    @staticmethod
    def build_jql_created(
        project_key: str,
        *,
        start: Optional[str] = None,
        end: Optional[str] = None,
        interval: Optional[str] = None,
        extra_filters: str = "",
    ) -> str:
        """
        Created in window.
        If interval provided (e.g. '7d'): created >= -interval
        Else inclusive dates: created >= "start" AND created <= "end"
        """
        if interval and (start or end):
            raise ValueError("Provide either (start & end) OR interval, not both.")

        if interval:
            term = f"created >= -{interval}"
        else:
            if not (start and end):
                raise ValueError("When interval is not given, 'start' and 'end' (YYYY-MM-DD) are required.")
            term = f'created >= "{start}" AND created <= "{end}"'

        return f"project = {project_key} AND {term}{JiraClient._merge_filters(extra_filters)}"

    @staticmethod
    def build_jql_resolved(
        project_key: str,
        *,
        start: Optional[str] = None,
        end: Optional[str] = None,
        interval: Optional[str] = None,
        extra_filters: str = "",
    ) -> str:
        """
        Resolved in window (uses the 'resolved' date; requires it to be not empty).
        If interval: resolved >= -interval AND resolved IS NOT EMPTY
        Else: resolved between start/end inclusive AND resolved IS NOT EMPTY
        """
        if interval and (start or end):
            raise ValueError("Provide either (start & end) OR interval, not both.")

        if interval:
            term = f"resolved >= -{interval} AND resolved IS NOT EMPTY"
        else:
            if not (start and end):
                raise ValueError("When interval is not given, 'start' and 'end' (YYYY-MM-DD) are required.")
            term = f'resolved >= "{start}" AND resolved <= "{end}" AND resolved IS NOT EMPTY'

        return f"project = {project_key} AND {term}{JiraClient._merge_filters(extra_filters)}"

    @staticmethod
    def build_jql_open_asof_end(
        project_key: str,
        *,
        end: str,
        extra_filters: str = "",
    ) -> str:
        """
        Still open at END of window (closing backlog snapshot):
          created <= "end" AND (resolved IS EMPTY OR resolved > "end")
        Always uses a concrete end date (works with any window mode because main.py computes end).
        """
        term = f'created <= "{end}" AND (resolved IS EMPTY OR resolved > "{end}")'
        return f"project = {project_key} AND {term}{JiraClient._merge_filters(extra_filters)}"

    # ---------- Enhanced search with nextPageToken ----------

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
        page_guard = 0
        wanted_fields = "summary,issuetype,status,assignee,created,resolved,updated,key"
        while True:
            data = self._search_enhanced(jql, fields=wanted_fields, next_page_token=token)
            issues.extend(data.get("issues", []))
            token = data.get("nextPageToken")
            if not token:
                break
            page_guard += 1
            if page_guard > 200:
                break
        return issues
