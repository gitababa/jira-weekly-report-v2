# main.py
import json
import os
from typing import Tuple, Optional
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

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


def _prev_calendar_week_window(tz_label: str) -> Tuple[str, str, str]:
    """
    Previous ISO calendar week (Mon..Sun) in tz_label.
    Returns (start, end, label).
    """
    today = _today_in_tz(tz_label)
    this_monday = today - timedelta(days=today.weekday())  # Monday of this week
    last_monday = this_monday - timedelta(days=7)
    last_sunday = last_monday + timedelta(days=6)
    return last_monday.isoformat(), last_sunday.isoformat(), f"{last_monday} to {last_sunday} (last_week)"


def _last_7_days_up_to_yesterday(tz_label: str) -> Tuple[str, str, str]:
    """
    A 7-day window ending yesterday in tz_label.
    If today is Monday, this becomes Mon-1..Sun-1 (the previous full week by days, not ISO).
    """
    today = _today_in_tz(tz_label)
    end = today - timedelta(days=1)       # yesterday
    start = end - timedelta(days=6)       # 7 days inclusive
    return start.isoformat(), end.isoformat(), f"{start} to {end} (last_7_days)"


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
    Returns (mode, start, end, interval, label).

    Modes:
      - custom_range: uses explicit start/end
      - last_week:
          * If today is Monday in tz -> last 7 days (Mon-1 .. Sun-1)
          * Else -> previous calendar week (Mon..Sun)
      - rolling_days: uses interval like '7d' and computes start/end for display
    """
    w = cfg["report"]["window"]
    tz_label = cfg["report"].get("timezone_label", "Europe/Berlin")
    mode = w.get("mode", "custom_range")

    if mode == "custom_range":
        start = w["start"]
        end = w["end"]
        return mode, start, end, None, f"{start} to {end}"

    if mode == "last_week":
        today = _today_in_tz(tz_label)
        if today.weekday() == 0:  # Monday
            start, end, label = _last_7_days_up_to_yesterday(tz_label)
            # Clarify in label that Monday logic used
            label = f"{start} to {end} (last_week via last_7_days)"
        else:
            start, end, label = _prev_calendar_week_window(tz_label)
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
        if mode == "rolling_days":
            if not interval:
                raise ValueError("rolling_days selected but no interval computed.")
            # interval + end are BOTH required here (end used for snapshot)
            jql = JiraClient.build_jql_union_window(key, interval=interval, end=end, extra_filters=extra)
            branch = "union: interval+end"
        else:
            # custom_range / last_week: use explicit start & end
            if not (start and end):
                raise ValueError(f"{mode} selected but start/end not available.")
            jql = JiraClient.build_jql_union_window(key, start=start, end=end, extra_filters=extra)
            branch = "union: start+end"

        print(f"\nProject {key} — Window {window_label}  [{branch}]")
        print("JQL (union):\n", jql)

        issues = jc.get_issues(jql)
        print(f"Fetched {len(issues)} issues (union)")

        tagged = tag_issues(issues, start, end)
        rows = tagged["rows"]
        counts = tagged["counts"]
        print(f"Counts — created={counts['created']} resolved={counts['resolved']} open@end={counts['open']}")
        print(f"Total unique issues in union: {len(rows)}")

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
