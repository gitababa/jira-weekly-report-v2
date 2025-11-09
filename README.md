Jira Weekly Report (Python)

Generate and email a weekly Jira report that shows:

Opening backlog (open at start of window)

Created (in window)

Resolved (in window)

Open (at end) (aka closing backlog)

The report runs automatically every Monday at 10:00 Europe/Berlin (configurable) via GitHub Actions, and can also be run locally or manually from the Actions UI.

Features

✅ Single JQL per project (optimized): returns all issues you need in one query

✅ Robust date windows:

custom_range (inclusive), last_week (smart Monday logic), rolling_days

Inclusive windows implemented via the reliable < end+1 day pattern

✅ Email: HTML summary + CSV attachment (sorted by status)

✅ Resolution name included (CSV & email)

✅ Identity check in the email:

Closing = Opening + Created − Resolved (shown & validated)

✅ Config builder GUI (config_builder_tk.py) to create config.json

✅ CI: unit tests with pytest, formatting (black), linting (flake8), typing (mypy)

✅ GitHub Actions workflow for weekly scheduling + manual runs

Architecture
.
├─ main.py                # Entry point: computes window, builds JQL, fetches, tags, emails
├─ jira.py                # JiraClient + JQL builders (union query & simple builders for tests)
├─ report.py              # Flag tagging, counts, identity math; legacy format shim
├─ mailer.py              # HTML email + CSV generation
├─ config_builder_tk.py   # Optional GUI to build config.json
├─ config.json            # Runtime configuration (window, projects, options)
├─ requirements.txt       # Dependencies
├─ pyproject.toml         # Tooling config (black, flake8, mypy)
└─ tests/                 # pytest unit tests (including union JQL + identity)

How the JQL works (why results are correct)

To avoid duplicates and extra HTTP calls, we run one JQL per project that unions three logical sets:

Created in window: created >= "start" AND created < "end+1d"

Resolved in window: resolved >= "start" AND resolved < "end+1d" AND resolved IS NOT EMPTY

Open at end (snapshot): created < "end+1d" AND (resolved IS EMPTY OR resolved >= "end+1d")

Using < end+1d makes the end date inclusive without relying on instance timezones or startOfDay/endOfDay.

Then we tag each issue with flags:

created_in_window, resolved_in_window, open_at_start, open_at_end

And compute:

Opening backlog (open_start) = count(open_at_start)
Created (in window)          = count(created_in_window)
Resolved (in window)         = count(resolved_in_window)
Closing backlog (open)       = count(open_at_end)

Identity: Closing = Opening + Created − Resolved


The email shows these numbers and validates the identity.

Configuration
config.json

Example (matches your working setup) 

config

:

{
  "report": {
    "timezone_label": "Europe/Berlin",
    "window": {
      "mode": "custom_range",
      "start": "2025-11-01",
      "end": "2025-11-08"
    },
    "show_top_n": 10,
    "include_csv_attachment": true,
    "alerts_email": ""
  },
  "global_jql_extra": "",
  "projects": [
    { "key": "SUP", "lead_email": "allenramezani@gmail.com" }
  ]
}

Window modes (handled in main.py) 

main

custom_range: exact start, end (inclusive via < end+1d)

last_week:

If today is Monday (in the configured timezone), use last 7 days up to Sunday

Otherwise, use previous ISO calendar week (Mon..Sun)

rolling_days: last N days up to yesterday (interval mode)

Environment variables
Name	Purpose
JIRA_BASE_URL	e.g., https://your-domain.atlassian.net
JIRA_EMAIL	Jira account email
JIRA_API_TOKEN	Jira API token
EMAIL_FROM	From address
SMTP_HOST	SMTP host
SMTP_PORT	SMTP port (e.g., 587)
SMTP_USERNAME	SMTP username
SMTP_PASSWORD	SMTP password
CONFIG_PATH	(optional) path to config.json
REPORT_MOCK_TODAY	(optional) YYYY-MM-DD, for testing Monday logic
Running locally
# 1) install
pip install -r requirements.txt

# or with Makefile:
make install

# 2) set env vars (Unix shell example)
export JIRA_BASE_URL="https://your-domain.atlassian.net"
export JIRA_EMAIL="you@example.com"
export JIRA_API_TOKEN="***"
export EMAIL_FROM="reports@example.com"
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USERNAME="smtp-user"
export SMTP_PASSWORD="smtp-pass"

# 3) run
python main.py

# Optional: override the 'today' (e.g., simulate Monday for last_week)
REPORT_MOCK_TODAY=2025-11-10 python main.py

Build a config via GUI (optional)
python config_builder_tk.py


Connect with Jira creds (for metadata).

Choose window mode, projects, optional filters.

Save as config.json. (The builder produces a config compatible with the current code.) 

config_builder_tk

Output
Email (HTML)

Header tiles: Opening, Created, Resolved, Open (at end)

Identity line (Closing = Opening + Created − Resolved) with ✅ check

Table of top N issues (configurable), including:

Key (linked), Summary, Status, Assignee, Created, Resolved, Resolution (name) 

mailer

CSV (attachment)

Columns:

Key, Summary, Status, Assignee, Created, Resolved, Resolution,
Created_in_window, Resolved_in_window, Open_at_start, Open_at_end


CSV rows are filtered to issues that matched the window (at least one flag true) and sorted by status. 

mailer

GitHub Actions
Weekly scheduled workflow

The workflow file (e.g., .github/workflows/report.yml) runs every Monday 10:00 Europe/Berlin using dual cron to handle DST.

It also supports manual runs (workflow_dispatch) with optional start, end, mock_today inputs.

Tip: add a tiny keepalive workflow if you’re worried about “repo inactivity” pausing schedules.

Manual runs

Open Actions → Weekly Jira Report → Run workflow. You can:

Leave inputs empty to use config.json

Provide start/end to override the window once

Provide mock_today to simulate “today” for Monday logic tests

Testing & Quality
# unit tests
pytest -q

# format
black .

# lint
pflake8

# type check
mypy .


Tests cover JQL union end+1 pattern and identity math (Closing = Opening + Created − Resolved).

CI runs these on PRs and main.

Jira permissions

Minimal read access is enough:

Browse projects

Read issues (fields: summary, issuetype, status, assignee, created, resolutiondate, resolution, updated, key) 

jira

No admin scopes required.

Troubleshooting

Counts don’t match visible issues
Ensure the window is what you expect. For custom ranges, we include the end date via < end+1d.
The email shows the exact window label printed by main.py.

No email / SMTP errors
Check SMTP creds & network blocks. SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, EMAIL_FROM.

No scheduled runs
Workflow must be on the default branch (main). Repo inactivity can pause schedules—enable Dependabot or keepalive.

Timezone questions
All window logic uses your timezone_label (default Europe/Berlin) for “today/Monday” decisions.

Contributing

PRs welcome. Please run black, flake8, mypy, and pytest before pushing.

Keep JQL changes synchronized with tests; the < end+1d pattern is intentionally locked in.