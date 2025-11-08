# main.py
import json
import os
from typing import Tuple, Optional
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo  # Python 3.9+

from jira import JiraClient
from report import format_report
from mailer import send_report  # was email.py

CONFIG_PATH = os.getenv("CONFIG_PATH", "config.json")


def _today_in_tz(tz_label: str) -> date:
    try:
        tz = ZoneInfo(tz_label)
        return datetime.now(tz).date()
    except Exception:
        # Fallback if tz db not available
        return date.today()


def _last_week_window(tz_label: str) -> Tuple[str, str, str]:
    """
    Previous Monday..Sunday in tz_label. Returns (start_YYYY-MM-DD, end_YYYY-MM-DD, label)
    """
    today = _today_in_tz(tz_label)
    this_monday = today - timedelta(days=today.weekday())
    last_monday = this_monday - timedelta(days=7)
    last_sunday = last_monday + timedelta(days=6)
    return last_monday.isoformat(), last_sunday.isoformat(), f"{last_monday} to {last_sunday} (last_week)"


def _rolling_days_window(tz_label: str, days: int) -> Tuple[str, str, str, str]:
    """
    Rolling window as dates and interval string.
    Returns (start_YYYY-MM-DD, end_YYYY-MM-DD, label, interval_str)
    """
    if days < 1:
        days = 1
    today = _today_in_tz(tz_label)
    start = (today - timedelta(days=days)).isoformat()
    end = (today - timedelta(days=1)).isoformat()
    label = f"Last {days} days ({start} to {end})"
    interval = f"{days}d"
    return start, end, label, interval


def _window_from_config(cfg: dict) -> Tuple[str, Optional[str], Optional[str], Optional[str], str]:
    """
    Returns a normalized tuple:
      (mode, start, end, interval, label)
    For custom_range / last_week -> start/end populated.
    For rolling_days -> interval populated (start/end also provided for display).
    """
    w = cfg["report"]["window"]
    tz_label = cfg["report"].get("timezone_label", "Europe/Berlin")
    mode = w.get("mode", "custom_range")

    if mode == "custom_range":
        start = w["start"]
        end = w["end"]
        return mode, start, end, None, f"{start} to {end}"

    if mode == "last_week":
        start, end, label = _last_week_window(tz_label)
        return mode, start, end, None, label

    if mode == "rolling_days":
        days = int(w.get("rolling_days", 7))
        start, end, label, interval = _rolling_days_window(tz_label, days)
        return mode, start, end, interval, label

    raise ValueError(f"Unsupported window mode: {mode}")


def run():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    mode, start, end, interval, window_label = _window_from_config(cfg)
    projects = cfg.get("projects", [])
    global_extra = (cfg.get("global_jql_extra") or "").strip()

    jc = JiraClient()

    for p in projects:
        key = p["key"]
        lead_email = p["lead_email"]
        project_extra = (p.get("jql_extra") or "").strip()

        # Merge extras (they may already start with AND/OR — JiraClient handles that safely)
        extra = " ".join(x for x in [global_extra, project_extra] if x).strip()

        # Build JQL using either start/end or interval
        if mode == "rolling_days" and interval:
            jql = JiraClient.build_jql(key, interval=interval, extra_filters=extra)
        else:
            jql = JiraClient.build_jql(key, start=start, end=end, extra_filters=extra)

        print("Running JQL:\n", jql)

        issues = jc.get_issues(jql)
        # Always bucket by explicit dates so Open = Created − Resolved holds for the display window
        buckets = format_report(issues, start, end)

        print(
            f"Counts — created={len(buckets['created'])} "
            f"resolved={len(buckets['resolved'])} "
            f"open={len(buckets['open'])}"
        )

        send_report(
            lead_email,
            key,
            window_label,
            buckets,
            show_top_n=int(cfg["report"].get("show_top_n", 20)),
        )


if __name__ == "__main__":
    run()
