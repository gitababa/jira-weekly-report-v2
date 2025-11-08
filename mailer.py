# mailer.py
from __future__ import annotations
import os, io, csv, smtplib
from typing import List, Tuple, Dict
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

EMAIL_FROM = os.getenv("EMAIL_FROM")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", "").rstrip("/")


def _table(issues: List[dict], title: str) -> str:
    if not issues:
        return f"<h3>{title}</h3><p>No issues.</p>"
    rows = []
    for it in issues:
        f = it.get("fields", {})
        key = it.get("key")
        url = f"{JIRA_BASE_URL}/browse/{key}" if JIRA_BASE_URL else "#"
        summary = (f.get("summary") or "").replace("&", "&amp;").replace("<", "&lt;")
        status = (f.get("status", {}) or {}).get("name", "—")
        assignee = (f.get("assignee", {}) or {}).get("displayName", "—")
        created = (f.get("created") or "—")[:10]
        resolved = (f.get("resolved") or "—")[:10] if f.get("resolved") else "—"
        rows.append(
            f"<tr>"
            f"<td><a href='{url}'>{key}</a></td>"
            f"<td>{summary}</td>"
            f"<td>{status}</td>"
            f"<td>{assignee}</td>"
            f"<td>{created}</td>"
            f"<td>{resolved}</td>"
            f"</tr>"
        )
    return (
        f"<h3>{title}</h3>"
        "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse'>"
        "<thead><tr><th>Key</th><th>Summary</th><th>Status</th><th>Assignee</th><th>Created</th><th>Resolved</th></tr></thead>"
        "<tbody>" + "".join(rows) + "</tbody></table>"
    )


def _csv_bytes(groups: List[Tuple[str, List[dict]]]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Bucket", "Key", "Summary", "Status", "Assignee", "Created", "Resolved"])
    for bucket, issues in groups:
        for it in issues:
            f = it.get("fields", {})
            w.writerow(
                [
                    bucket,
                    it.get("key"),
                    f.get("summary") or "",
                    (f.get("status", {}) or {}).get("name", ""),
                    (f.get("assignee", {}) or {}).get("displayName", ""),
                    (f.get("created") or "")[:10],
                    (f.get("resolved") or "")[:10],
                ]
            )
    return buf.getvalue().encode("utf-8")


def send_report(to_email: str, project_key: str, window_label: str, buckets: Dict[str, List[dict]], show_top_n: int = 20):
    created = buckets["created"]
    resolved = buckets["resolved"]
    open_ = buckets["open"]

    html = f"""
    <html><body style="font-family:Arial,Helvetica,sans-serif">
      <h2>Jira Report — Project {project_key} — {window_label}</h2>
      <div style="display:flex;gap:16px;margin:10px 0;">
        <div style="padding:12px;border:1px solid #ddd;border-radius:8px;"><b>Created</b><div style="font-size:28px;">{len(created)}</div></div>
        <div style="padding:12px;border:1px solid #ddd;border-radius:8px;"><b>Resolved</b><div style="font-size:28px;">{len(resolved)}</div></div>
        <div style="padding:12px;border:1px solid #ddd;border-radius:8px;"><b>Open</b><div style="font-size:28px;">{len(open_)}</div></div>
      </div>
      {_table(created[:show_top_n], f"Top {min(len(created), show_top_n)} created in window")}
      <br/>
      {_table(resolved[:show_top_n], f"Top {min(len(resolved), show_top_n)} resolved in window")}
      <br/>
      {_table(open_[:show_top_n], f"Top {min(len(open_), show_top_n)} open in window")}
      <p style="color:#777;margin-top:16px;">Open = Created − Resolved (in this window).</p>
    </body></html>
    """

    attachments = []
    csv_bytes = _csv_bytes(
        [("Created in window", created), ("Resolved in window", resolved), ("Open in window", open_)]
    )
    csv_name = f"{project_key}_report_{window_label.replace(' ', '_').replace('/', '-')}.csv"
    attachments.append((csv_name, csv_bytes))

    msg = MIMEMultipart("mixed")
    msg["Subject"] = f"Jira Report — {project_key} — {window_label}"
    msg["From"] = EMAIL_FROM
    msg["To"] = to_email
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(html, "html"))
    msg.attach(alt)

    for filename, content in attachments:
        part = MIMEApplication(content, Name=filename)
        part["Content-Disposition"] = f'attachment; filename="{filename}"'
        msg.attach(part)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(EMAIL_FROM, [to_email], msg.as_string())
