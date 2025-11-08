# main.py
import json
import os
from typing import Tuple, Optional
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo  # Python 3.9+

from jira import JiraClient
from report import tag_issues
from mailer import send_report

CONFIG_PATH = os.getenv("CONFIG_PATH", "config.json")

def _today_in_tz(tz_label: str) -> date:
    try:
        tz = ZoneInfo(tz_label)
        return datetime.now(tz).date()
    except Exception:
        return date.today()

def _last_week_window(tz_label: str) -> Tuple[str, str, str]:
    today = _today_in_tz(tz_label)
    this_monday = today - timedelta(days=today.weekday())
    last_monday = this_monday - timedelta(days=7)
    last_sunday = last_monday + timedelta(days=6)
    return last_monday.isoformat(), last_sunday.isoformat(), f"{last_monday} to {last_sunday} (last_week)"

def _rolling_days_window(tz_label: str, days: int) -> Tuple[str, str, str, str]:
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
    Returns: (mode, start, end, interval, label)
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

    print(f"Window mode: {mode} | start={start} | end={end} | interval={interval} | label={window_label}")

    jc = JiraClient()

    for p in projects:
        key = p["key"]
        lead_email = p["lead_email"]
        project_extra = (p.get("jql_extra") or "").strip()
        extra = " ".join(x for x in [global_extra, project_extra] if x).strip()

        # Build ONE union JQL (mode-aware)
        if mode == "rolling_days" and interval:
            jql = JiraClient.build_jql_union_window(key, interval=interval, end=end, extra_filters=extra)
        else:
            jql = JiraClient.build_jql_union_window(key, start=start, end=end, extra_filters=extra)

        print(f"\nProject {key} — Window {window_label}")
        print("JQL (union):\n", jql)

        # Fetch ONCE
        issues = jc.get_issues(jql)

        # Tag issues & compute counts
        tagged = tag_issues(issues, start, end)
        rows = tagged["rows"]
        counts = tagged["counts"]

        print(f"Counts — created={counts['created']} resolved={counts['resolved']} open@end={counts['open']}")
        print(f"Total unique issues in union: {len(rows)}")

        # Send (one table, one CSV, no duplicates)
        send_report(
            lead_email,
            key,
            window_label,
            rows,
            counts,
            show_top_n=int(cfg["report"].get("show_top_n", 20)),
        )

if __name__ == "__main__":
    run()
