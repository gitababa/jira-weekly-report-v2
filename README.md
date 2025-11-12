# Jira Weekly Report Automation

**Automated weekly Jira reports delivered to your inbox every Monday morning via GitHub Actions.**

Generate and email comprehensive weekly reports showing issues created, resolved, and currently open in your Jira projects. Set it up once, runs automatically forever with zero maintenance.


## 📊 What You Get

Every Monday at 10:00 AM (configurable timezone), receive an email with:

- **📈 Summary Metrics**: Opening backlog, created, resolved, and closing backlog counts
- **📋 Issue Table**: Top N issues with clickable links directly to Jira
- **📎 CSV Attachment**: Complete dataset with all issue details for further analysis
- **✅ Data Validation**: Automatic identity check to ensure accuracy
- **🎯 Smart Filtering**: Customizable by project, issue type, priority, assignee, and more

**Perfect for:** Project managers, team leads, stakeholders who need weekly insights without manual work.

---

## ✨ Key Features

- **🤖 Fully Automated**: Runs via GitHub Actions, no servers to maintain
- **🚀 Optimized**: Single union JQL query per project (3x faster than traditional approaches)
- **📅 Flexible Windows**: Last week, custom date range, or rolling N days
- **🎨 GUI Setup Tool**: Visual configuration builder, no manual JSON editing required
- **🌍 Timezone-Aware**: Respects your configured timezone for accurate date calculations
- **🛡️ Robust**: Automatic retry with exponential backoff for transient failures
- **🔐 Secure**: All credentials stored in GitHub Secrets, never in code
- **💰 Free**: Uses GitHub Actions free tier (2,000 minutes/month)

---

## 🚀 Quick Setup (5 Steps)

### Step 1: Fork or Clone the Repository

Click the **Fork** button at the top of this page, or clone directly:

```bash
git clone https://github.com/gitababa/jira-weekly-report-v2.git
cd jira-weekly-report-v2
```

### Step 2: Generate Your Configuration

Use the included GUI configuration builder to easily create your `config.json`:

**On Windows:**
```powershell
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Launch config builder
python config_builder_tk.py
```

**On Mac/Linux:**
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Launch config builder
python config_builder_tk.py
```

**In the Config Builder GUI:**

1. **Test Jira Connection**:
   - Enter your Jira URL: `https://your-domain.atlassian.net`
   - Enter your Jira email
   - Enter your Jira API token ([Generate one here](https://id.atlassian.com/manage-profile/security/api-tokens))
   - Click **🔌 Test Connection & Fetch Metadata**

2. **Select Projects**:
   - Click on projects in the left list
   - Enter the project lead's email address
   - Click **➕ Add/Update Project**

3. **Configure Filters** (Optional):
   - Check issue types to include (Bug, Task, etc.)
   - Check priorities to include (High, Critical, etc.)
   - Add custom JQL filters if needed

4. **Choose Window Mode**:
   - **Last Week (Smart)** - Recommended for Monday automation
   - **Rolling N Days** - Last 7, 14, or 30 days
   - **Custom Range** - Specific start/end dates

5. **Save Configuration**:
   - Click **💾 Generate config.json**
   - Save it as `config.json` in the project root (replace the sample file)

### Step 3: Commit Your Configuration

```bash
# Add your generated config
git add config.json

# Commit changes
git commit -m "Add my Jira report configuration"

# Push to your fork/repository
git push origin main
```

### Step 4: Set Up GitHub Secrets

1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** for each of the following:

| Secret Name | Description | Example |
|------------|-------------|---------|
| `JIRA_BASE_URL` | Your Jira Cloud URL | `https://your-domain.atlassian.net` |
| `JIRA_EMAIL` | Your Jira account email | `admin@example.com` |
| `JIRA_API_TOKEN` | Your Jira API token | Generate at [id.atlassian.com](https://id.atlassian.com/manage-profile/security/api-tokens) |
| `EMAIL_FROM` | Sender email address | `reports@example.com` |
| `SMTP_HOST` | SMTP server hostname | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP port (usually 587) | `587` |
| `SMTP_USERNAME` | SMTP username | `your-email@gmail.com` |
| `SMTP_PASSWORD` | SMTP password/app password | For Gmail: [Generate App Password](https://support.google.com/accounts/answer/185833) |

**Gmail Users**: Make sure to:
- Enable 2-Step Verification on your Google Account
- Generate an App Password (not your regular password)
- Use the 16-character app password in `SMTP_PASSWORD`

### Step 5: Run Your First Report

**Option A: Manual Run (Test Immediately)**

1. Go to the **Actions** tab in your repository
2. Click on **Weekly Jira Report** workflow
3. Click **Run workflow** button
4. Click the green **Run workflow** button
5. Wait 30-60 seconds
6. Check your email! 🎉

**Option B: Wait for Schedule**

The workflow runs automatically every **Monday at 10:00 AM** (Europe/Berlin timezone).

You're done! The report will be sent automatically every Monday morning.

---

## 📖 Configuration Guide

### Window Modes Explained

The configuration file (`config.json`) supports three window modes:

#### Last Week (Recommended)

```json
{
  "report": {
    "window": {
      "mode": "last_week"
    }
  }
}
```

**Smart behavior:**
- If today is Monday: Uses last 7 days (previous Monday through Sunday)
- Otherwise: Uses previous ISO calendar week

Perfect for Monday automation!

#### Custom Range

```json
{
  "report": {
    "window": {
      "mode": "custom_range",
      "start": "2025-11-01",
      "end": "2025-11-08"
    }
  }
}
```

Specify exact dates (both inclusive). Useful for one-off reports or specific time periods.

#### Rolling Days

```json
{
  "report": {
    "window": {
      "mode": "rolling_days",
      "rolling_days": 7
    }
  }
}
```

Look back N days from yesterday. Great for weekly, bi-weekly, or monthly reports.

### Filtering Options

#### Global Filters (Applied to All Projects)

```json
{
  "global_jql_extra": "AND issuetype IN (\"Bug\", \"Task\") AND priority = \"High\""
}
```

Common use cases:
- Filter by issue type: `AND issuetype = "Bug"`
- Filter by priority: `AND priority IN ("High", "Critical")`
- Filter by assignee: `AND assignee = currentUser()`
- Filter by status: `AND status NOT IN ("Done", "Cancelled")`

#### Per-Project Filters

```json
{
  "projects": [
    {
      "key": "BACKEND",
      "lead_email": "backend-lead@example.com",
      "jql_extra": "AND component = \"API\""
    },
    {
      "key": "FRONTEND",
      "lead_email": "frontend-lead@example.com",
      "jql_extra": "AND priority = \"Critical\""
    }
  ]
}
```

Each project can have its own additional filters.

### Multiple Projects

Monitor multiple projects with different recipients:

```json
{
  "projects": [
    {
      "key": "PROJECT1",
      "lead_email": "lead1@example.com"
    },
    {
      "key": "PROJECT2",
      "lead_email": "lead2@example.com"
    },
    {
      "key": "PROJECT3",
      "lead_email": "lead3@example.com"
    }
  ]
}
```

Each project lead receives their own personalized report.

### Report Options

```json
{
  "report": {
    "timezone_label": "Europe/Berlin",
    "show_top_n": 10,
    "include_csv_attachment": true
  }
}
```

- `timezone_label`: Any IANA timezone (e.g., "America/New_York", "Asia/Tokyo")
- `show_top_n`: Number of issues to display in email body (1-100)
- `include_csv_attachment`: Set to `false` to skip CSV attachment

---

## 📧 Email Report Structure

### Subject Line
```
Jira Report — PROJECT — 2025-11-04 to 2025-11-10
```

### Email Body (HTML)

**Summary Cards:**
```
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ Opening backlog  │  │ Created (window) │  │ Resolved (window)│  │ Open (at end)    │
│       5          │  │       2          │  │       1          │  │       6          │
└──────────────────┘  └──────────────────┘  └──────────────────┘  └──────────────────┘
```

**Identity Validation:**
```
Identity: Closing = Opening + Created − Resolved → 6 = 5 + 2 − 1 ✅
```

**Issue Table:**
| Key | Summary | Status | Assignee | Created | Resolved | Resolution |
|-----|---------|--------|----------|---------|----------|------------|
| [PROJ-123](link) | Fix login bug | Done | John Doe | 2025-11-02 | 2025-11-05 | Done |
| [PROJ-124](link) | Add API endpoint | In Progress | Jane Smith | 2025-11-03 | — | — |

All issue keys are clickable links that open directly in Jira.

### CSV Attachment

Complete dataset with additional columns:
- Standard fields: Key, Summary, Status, Assignee, Created, Resolved, Resolution
- Flag columns: Created_in_window, Resolved_in_window, Open_at_start, Open_at_end

Perfect for importing into Excel, Google Sheets, or BI tools for further analysis.

---

## 🔧 Customizing the Schedule

The workflow runs every Monday at 10:00 AM Europe/Berlin time by default. To change this:

**Edit `.github/workflows/report.yml`:**

```yaml
schedule:
  # Change to your preferred time
  - cron: '0 9 * 11,12,1,2,3 1'    # Winter months (CET)
  - cron: '0 8 * 4,5,6,7,8,9,10 1' # Summer months (CEST)
```

**Cron Format:** `minute hour day month weekday`

**Examples:**
- `0 9 * * 1` - Every Monday at 9:00 AM UTC
- `0 14 * * 5` - Every Friday at 2:00 PM UTC
- `0 8 1 * *` - First day of every month at 8:00 AM UTC

**Note:** GitHub Actions uses UTC. Adjust for your timezone:
- Europe/Berlin: UTC+1 (winter) / UTC+2 (summer)
- US Eastern: UTC-5 (winter) / UTC-4 (summer)
- Asia/Tokyo: UTC+9

---

## 🛠️ Troubleshooting

### "Workflow not running on schedule"

**Solutions:**
1. Ensure workflow is on the `main` branch (or your default branch)
2. Check if repository is active (workflows pause after 60 days of inactivity)
3. Go to Actions → Select workflow → Ensure it's enabled
4. Try running manually first to verify setup

### "Authentication failed" Error

**Solutions:**
1. Verify `JIRA_EMAIL` matches your Jira account exactly
2. Regenerate Jira API token and update GitHub secret
3. Check `JIRA_BASE_URL` format: `https://domain.atlassian.net` (no trailing slash)
4. Ensure API token has not expired

### "SMTP authentication failed" Error

**For Gmail:**
1. Enable 2-Step Verification in Google Account settings
2. Generate a new App Password
3. Update `SMTP_PASSWORD` secret with the 16-character app password
4. Use `smtp.gmail.com` as SMTP_HOST and `587` as SMTP_PORT

**For Other Providers:**
1. Verify SMTP hostname and port are correct
2. Check if "less secure app access" needs to be enabled
3. Test credentials with an email client first

### "No issues fetched"

**Solutions:**
1. Verify project key exists in Jira
2. Test JQL manually in Jira: Filters → Advanced issue search
3. Check date range includes issues you know exist
4. Verify user has permission to view the project
5. Check if filters are too restrictive

### Config Builder Issues

**"Module not found" Error:**
```bash
# Activate virtual environment first
source venv/bin/activate  # Mac/Linux
# or
.\venv\Scripts\Activate.ps1  # Windows

# Then run
python config_builder_tk.py
```

**Connection Failed in GUI:**
1. Verify URL format: `https://domain.atlassian.net` (no trailing slash)
2. Check API token is correct
3. Ensure internet connection is stable
4. Test manually with curl:
   ```bash
   curl -u "email:token" "https://domain.atlassian.net/rest/api/3/myself"
   ```

---

## 📊 Understanding the Report Logic

### How Issues are Categorized

The report uses a single optimized JQL query to fetch all relevant issues, then categorizes each issue:

1. **Opening Backlog**: Issues created before the window and still open at start
2. **Created**: Issues created during the window (regardless of current status)
3. **Resolved**: Issues resolved during the window (regardless of when created)
4. **Open (Closing Backlog)**: Issues still open at the end of the window

### The Identity Equation

Every report includes validation:

```
Closing Backlog = Opening Backlog + Created − Resolved
```

Example:
```
6 = 5 + 2 − 1 ✅
```

If the equation doesn't balance, the report shows the calculated value to help debug.

### Date Handling

The system uses a robust **`< end+1 day`** pattern for inclusive end dates:

```
Window: 2025-11-01 to 2025-11-07

Query logic:
- Created: >= "2025-11-01" AND < "2025-11-08"
- Resolved: >= "2025-11-01" AND < "2025-11-08"
- Open: created < "2025-11-08" AND (resolved IS EMPTY OR resolved >= "2025-11-08")
```

This approach is timezone-independent and always accurate.

---

## 🧪 Testing & Development

### Project Structure

```
jira-weekly-report-v2/
├── .github/
│   └── workflows/
│       └── report.yml          # GitHub Actions workflow
├── tests/
│   ├── test_jql.py             # JQL query tests
│   ├── test_report.py          # Report logic tests
│   └── test_union_flags.py     # Integration tests
├── main.py                     # Entry point
├── jira.py                     # Jira API client
├── report.py                   # Issue tagging logic
├── mailer.py                   # Email generation
├── config_builder_tk.py        # GUI configuration tool
├── config.json                 # Configuration file
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

### Running Tests

```bash
# Activate virtual environment
source venv/bin/activate  # or .\venv\Scripts\Activate.ps1 on Windows

# Run all tests
pytest -v

# Run specific test file
pytest tests/test_jql.py -v

# Run with coverage
pytest --cov=. --cov-report=html

# Type checking
mypy main.py jira.py report.py mailer.py

# Linting
flake8 --max-line-length=120

# Code formatting
black .
```

### Architecture Overview

```
GitHub Actions Trigger (Monday 10 AM)
          ↓
main.py: Load config, calculate date window
          ↓
jira.py: Build optimized union JQL, fetch all relevant issues
          ↓
report.py: Tag each issue (created/resolved/open flags)
          ↓
report.py: Calculate counts and validate identity equation
          ↓
mailer.py: Generate HTML email + CSV attachment
          ↓
mailer.py: Send via SMTP to project leads
```

---

## 🎯 Advanced Usage

### Manual Local Testing

If you want to test the report locally before deploying:

```bash
# Set up virtual environment (if not done already)
python -m venv venv
source venv/bin/activate  # or .\venv\Scripts\Activate.ps1 on Windows
pip install -r requirements.txt

# Set environment variables
export JIRA_BASE_URL="https://your-domain.atlassian.net"
export JIRA_EMAIL="your-email@example.com"
export JIRA_API_TOKEN="your-api-token"
export EMAIL_FROM="reports@example.com"
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USERNAME="your-email@gmail.com"
export SMTP_PASSWORD="your-app-password"

# Run the report
python main.py
```

**On Windows (PowerShell):**
```powershell
$env:JIRA_BASE_URL="https://your-domain.atlassian.net"
$env:JIRA_EMAIL="your-email@example.com"
# ... (set all other variables)

python main.py
```

### Testing Monday Logic

To test the `last_week` mode behavior without waiting for Monday:

```bash
# Simulate that today is Monday 2025-11-10
export REPORT_MOCK_TODAY="2025-11-10"
python main.py
```

This is useful for testing the automatic week calculation.

---

## 🤝 Contributing

Contributions are welcome! Here's how:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Run tests: `pytest`
5. Format code: `black .`
6. Commit: `git commit -m 'Add amazing feature'`
7. Push: `git push origin feature/amazing-feature`
8. Open a Pull Request

### Code Quality Standards

- Follow PEP 8 style guide
- Format with Black
- Pass all tests (pytest)
- Pass type checking (mypy)
- Pass linting (flake8)

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built with [Jira REST API v3](https://developer.atlassian.com/cloud/jira/platform/rest/v3/)
- Powered by [GitHub Actions](https://github.com/features/actions)
- Inspired by the need for automated project reporting

---

## 📧 Support & Feedback

- **Issues**: [GitHub Issues](https://github.com/gitababa/jira-weekly-report-v2/issues)
- **Discussions**: [GitHub Discussions](https://github.com/gitababa/jira-weekly-report-v2/discussions)
- **Pull Requests**: Always welcome!

---

## ⭐ Star This Repository

If you find this project useful, please consider giving it a star! It helps others discover the project.

---

**Made with ❤️ for teams who value automation and data-driven insights**
