# Jira Weekly Report (Python)

Generate and email a weekly Jira report that shows:

- **Opening backlog** (open at start of window)
- **Created (in window)**
- **Resolved (in window)**
- **Open (at end)** (closing backlog)

Runs automatically **every Monday at 10:00 Europe/Berlin** via GitHub Actions, and can also be run locally or manually from the Actions UI.

---

## Features

- **Single JQL per project (optimized)** — one union query returns everything needed
- **Robust date windows**
  - `custom_range` (inclusive), `last_week` (smart Monday logic), `rolling_days`
  - Inclusive windows implemented with the reliable **`< end+1 day`** pattern
- **Email**: HTML summary + CSV attachment (sorted by status)
- **Resolution name** in both email + CSV
- **Identity check** shown in email:
  - `Closing = Opening + Created − Resolved`
- **Config builder GUI** (`config_builder_tk.py`) to create `config.json`
- **CI/QA**: pytest, black, flake8, mypy
- **GitHub Actions**: weekly schedule + manual runs

---

## Repository Structure

.
├─ main.py # Entry point: window selection, JQL build, fetch, tag, email
├─ jira.py # Jira client + JQL builders (union + simple builders for tests)
├─ report.py # Flag tagging (created/resolved/open), counts, identity math
├─ mailer.py # HTML email + CSV generation
├─ config_builder_tk.py # Optional GUI to build config.json
├─ config.json # Runtime configuration (window, projects, options)
├─ requirements.txt # Dependencies
├─ pyproject.toml # Tooling config (black/flake8/mypy)
└─ tests/ # Unit tests (JQL & identity checks)

sql
Copy code

---

## How It Works (JQL + Tagging)

To avoid duplicates and extra HTTP calls, the app runs **one union JQL** per project that returns the full set of issues relevant to the window:

1) **Created in window**  
   `created >= "start" AND created < "end_plus_1"`

2) **Resolved in window**  
   `resolved >= "start" AND resolved < "end_plus_1" AND resolved IS NOT EMPTY`

3) **Open at end (snapshot)**  
   `created < "end_plus_1" AND (resolved IS EMPTY OR resolved >= "end_plus_1")`

> Using **`< end_plus_1`** (instead of `<= endOfDay(end)`) makes the end date truly inclusive and is robust across timezones.

Each issue is **tagged** with:
- `created_in_window`, `resolved_in_window`, `open_at_start`, `open_at_end`

Counts used in the report:

Opening backlog (open_start) = count(open_at_start)
Created (in window) = count(created_in_window)
Resolved (in window) = count(resolved_in_window)
Closing backlog (open) = count(open_at_end)

Identity: Closing = Opening + Created − Resolved

yaml
Copy code

---

## Configuration

### `config.json` (example)

```json
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
    { "key": "SUP", "lead_email": "lead@example.com" }
  ]
}
Window Modes
custom_range — exact start / end (inclusive via < end+1d)

last_week — if today is Monday (in configured timezone), use last 7 days; otherwise use previous ISO week (Mon–Sun)

rolling_days — last N days up to yesterday (e.g., rolling_days: 7)

Environment Variables
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
REPORT_MOCK_TODAY	(optional) YYYY-MM-DD, to simulate “today” for testing Monday logic

Running Locally
bash
Copy code
# 1) install dependencies
pip install -r requirements.txt
# (or) make install

# 2) set environment variables (bash example)
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

# Optional: simulate Monday logic for `last_week` mode
REPORT_MOCK_TODAY=2025-11-10 python main.py
Build a Config via GUI (optional)
bash
Copy code
python config_builder_tk.py
The GUI helps you create a config.json that matches the current app schema.

Output
Email (HTML)
Four tiles: Opening, Created, Resolved, Open (at end)

Identity line: Closing = Opening + Created − Resolved (validated)

Table (Top N issues):

Key (linked), Summary, Status, Assignee, Created, Resolved, Resolution

CSV (Attachment)
Columns:

css
Copy code
Key, Summary, Status, Assignee, Created, Resolved, Resolution,
Created_in_window, Resolved_in_window, Open_at_start, Open_at_end
Rows are filtered to issues that matched the selected window and sorted by Status.

GitHub Actions
Scheduled Weekly Report
Create .github/workflows/report.yml like:

yaml
Copy code
name: Weekly Jira Report

on:
  # 10:00 Europe/Berlin all year (DST safe via two crons)
  schedule:
    - cron: '0 9 * 11,12,1,2,3 MON'    # 09:00 UTC in Nov–Mar → 10:00 CET
    - cron: '0 8 * 4,5,6,7,8,9,10 MON' # 08:00 UTC in Apr–Oct → 10:00 CEST
  workflow_dispatch:
    inputs:
      start:
        description: 'Start YYYY-MM-DD (optional)'
        required: false
      end:
        description: 'End YYYY-MM-DD (optional)'
        required: false
      mock_today:
        description: 'Mock today YYYY-MM-DD (optional)'
        required: false

jobs:
  report:
    runs-on: ubuntu-latest
    env:
      CONFIG_PATH: config.json
      JIRA_BASE_URL: ${{ secrets.JIRA_BASE_URL }}
      JIRA_EMAIL: ${{ secrets.JIRA_EMAIL }}
      JIRA_API_TOKEN: ${{ secrets.JIRA_API_TOKEN }}
      EMAIL_FROM: ${{ secrets.EMAIL_FROM }}
      SMTP_HOST: ${{ secrets.SMTP_HOST }}
      SMTP_PORT: ${{ secrets.SMTP_PORT }}
      SMTP_USERNAME: ${{ secrets.SMTP_USERNAME }}
      SMTP_PASSWORD: ${{ secrets.SMTP_PASSWORD }}
      REPORT_MOCK_TODAY: ${{ github.event.inputs.mock_today }}

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - name: Run report
        run: |
          if [ -n "${{ github.event.inputs.start }}" ] && [ -n "${{ github.event.inputs.end }}" ]; then
            echo "Manual window: ${{ github.event.inputs.start }} → ${{ github.event.inputs.end }}"
            python main.py --start "${{ github.event.inputs.start }}" --end "${{ github.event.inputs.end }}"
          else
            python main.py
          fi
Note: Scheduled workflows must be on the default branch (usually main). If a repo is inactive for a long time, scheduled runs can pause—consider enabling Dependabot or adding a tiny “keepalive” workflow.

Testing & Quality
bash
Copy code
# unit tests
pytest -q

# format
black .

# lint
pflake8

# type check
mypy .
The test suite includes:

a check that union JQL uses the < end+1 day pattern

an identity test that ensures Closing = Opening + Created − Resolved

Jira Permissions
Minimal read scope is sufficient:

Browse projects

Read issues/fields: summary, issuetype, status, assignee, created, resolutiondate, resolution, updated, key

No admin permissions required.

Troubleshooting
Counts look off
Verify the window. For custom_range, the end date is inclusive via < end+1d. The email prints the window in the header.

Email not sent
Recheck SMTP env vars, firewall blocks, or provider restrictions.

No scheduled runs
Ensure the workflow is on main. To prevent dormancy, enable Dependabot (weekly) or add a tiny scheduled keepalive workflow.