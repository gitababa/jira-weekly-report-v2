# mailer.py
from __future__ import annotations
import os, io, csv, smtplib
from typing import List, Dict
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

EMAIL_FROM = os.getenv("EMAIL_FROM")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", "").rstrip("/")


def _status_name(fields: dict) -> str:
    return ((fields.get("status") or {}).get("name") or "").strip()


def _table(rows: List[dict], title: str) -> str:
    if not rows:
        return f"<h3>{title}</h3><p>No issues.</p>"
    tr = []
    for row in rows:
        f = row["fields"]
        key = row["key"]
        url = f"{JIRA_BASE_URL}/browse/{key}" if JIRA_BASE_URL else "#"
        summary = (f.get("summary") or "").replace("&", "&amp;").replace("<", "&lt;")
        status = _status_name(f) or "—"
        assignee = (f.get("assignee", {}) or {}).get("displayName", "—")
        created = (f.get("created") or "—")[:10]
        resolutiondate = (f.get("resolutiondate") or f.get("resolved") or "")[:10] or "—"
        flags = []
        if row["created_in_window"]: flags.append("Created")
        if row["resolved_in_window"]: flags.append("Resolved")
        if row["open_at_end"]: flags.append("Open@End")
        flag_str = ", ".join(flags) if flags else "—"
        tr.append(
            f"<tr>"
            f"<td><a href='{url}'>{key}</a></td>"
            f"<td>{summary}</td>"
            f"<td>{status}</td>"
            f"<td>{assignee}</td>"
            f"<td>{created}</td>"
            f"<td>{resolutiondate}</td>"
            f"<td>{flag_str}</td>"
            f"</tr>"
        )
    return (
        f"<h3>{title}</h3>"
        "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse'>"
        "<thead><tr><th>Key</th><th>Summary</th><th>Status</th><th>Assignee</th><th>Created</th><th>Resolved</th><th>Tags</th></tr></thead>"
        "<tbody>" + "".join(tr) + "</tbody></table>"
    )


def _csv_bytes(rows: List[dict]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Key", "Summary", "Status", "Assignee", "Created", "Resolved",
                "Created_in_window", "Resolved_in_window", "Open_at_end"])
    rows_sorted = sorted(
        rows,
        key=lambda r: (_status_name(r["fields"]).lower(), (r["key"] or "").lower())
    )
    for row in rows_sorted:
        f = row["fields"]
        w.writerow([
            row["key"],
            f.get("summary") or "",
            _status_name(f),
            (f.get("assignee", {}) or {}).get("displayName", ""),
            (f.get("created") or "")[:10],
            (f.get("resolutiondate") or f.get("resolved") or "")[:10],
            "1" if row["created_in_window"] else "0",
            "1" if row["resolved_in_window"] else "0",
            "1" if row["open_at_end"] else "0",
        ])
    return buf.getvalue().encode("utf-8")


def send_report(to_email: str, project_key: str, window_label: str,
                rows: List[dict], counts: Dict[str, int], show_top_n: int = 20):
    # Only include issues that actually matched the window (at least one flag true)
    rows_in_window = [r for r in rows if r["created_in_window"] or r["resolved_in_window"] or r["open_at_end"]]

    html = f"""
    <html><body style="font-family:Arial,Helvetica,sans-serif">
      <h2>Jira Report — Project {project_key} — {window_label}</h2>
      <div style="display:flex;gap:16px;margin:10px 0;">
        <div style="padding:12px;border:1px solid #ddd;border-radius:8px;"><b>Created (in window)</b><div style="font-size:28px;">{counts['created']}</div></div>
        <div style="padding:12px;border:1px solid #ddd;border-radius:8px;"><b>Resolved (in window)</b><div style="font-size:28px;">{counts['resolved']}</div></div>
        <div style="padding:12px;border:1px solid #ddd;border-radius:8px;"><b>Open (at end)</b><div style="font-size:28px;">{counts['open']}</div></div>
      </div>
      {_table(rows_in_window[:show_top_n], f"Top {min(len(rows_in_window), show_top_n)} issues matched in this window")}
      <p style="color:#777;margin-top:16px;">Flags: Created = created in window; Resolved = resolution set in window; Open@End = still open at the end of the window.</p>
    </body></html>
    """

    csv_bytes = _csv_bytes(rows_in_window)
    csv_name = f"{project_key}_report_{window_label.replace(' ', '_').replace('/', '-')}.csv"

    msg = MIMEMultipart("mixed")
    msg["Subject"] = f"Jira Report — {project_key} — {window_label}"
    msg["From"] = EMAIL_FROM
    msg["To"] = to_email
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(html, "html"))
    msg.attach(alt)

    part = MIMEApplication(csv_bytes, Name=csv_name)
    part["Content-Disposition"] = f'attachment; filename="{csv_name}"'
    msg.attach(part)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(EMAIL_FROM, [to_email], msg.as_string())
