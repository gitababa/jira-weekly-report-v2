# main.py
import json
import os
from typing import Tuple
from jira import JiraClient
from report import format_report
from mailer import send_report  # renamed from email.py -> mailer.py


CONFIG_PATH = os.getenv("CONFIG_PATH", "config.json")


def _window_from_config(cfg: dict) -> Tuple[str, str, str]:
    w = cfg["report"]["window"]
    mode = w.get("mode", "custom_range")
    if mode != "custom_range":
        raise ValueError("For the simplified app, please use window.mode = 'custom_range' with start/end.")
    start = w["start"]  # YYYY-MM-DD
    end = w["end"]      # YYYY-MM-DD
    return start, end, f"{start} to {end}"


def run():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    start, end, window_label = _window_from_config(cfg)
    projects = cfg.get("projects", [])
    global_extra = (cfg.get("global_jql_extra") or "").strip()

    jc = JiraClient()

    for p in projects:
        key = p["key"]
        lead_email = p["lead_email"]
        project_extra = (p.get("jql_extra") or "").strip()
        extra = (" ".join(x for x in [global_extra, project_extra] if x)).strip()

        jql = JiraClient.build_jql(key, start=start, end=end, extra_filters=extra)
        print("Running JQL:\n", jql)

        issues = jc.get_issues(jql)
        buckets = format_report(issues, start, end)
        print(f"Counts — created={len(buckets['created'])} resolved={len(buckets['resolved'])} open={len(buckets['open'])}")

        send_report(lead_email, key, window_label, buckets, show_top_n=int(cfg["report"].get("show_top_n", 20)))


if __name__ == "__main__":
    run()
