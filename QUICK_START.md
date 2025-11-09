# Quick Start Guide - Jira Weekly Report

**Time to first report: ~20 minutes**

---

## Prerequisites Checklist

Before starting, ensure you have:

- [ ] Jira Cloud account with project access
- [ ] Gmail account (or other SMTP email)
- [ ] Python 3.11+ installed (`python3 --version`)
- [ ] Git installed (`git --version`)

---

## Step 1: Get Jira API Token (5 minutes)

1. Go to: https://id.atlassian.com/manage-profile/security/api-tokens
2. Click **Create API token**
3. Label it: `Jira Weekly Report`
4. Click **Create**
5. **Copy the token** (you won't see it again!)
6. Save it somewhere safe

---

## Step 2: Get Gmail App Password (5 minutes)

1. Go to: https://myaccount.google.com/security
2. Enable **2-Step Verification** (if not already enabled)
3. Go back to Security → **App passwords**
4. Select app: **Mail**, device: **Other** (type: "Jira Report")
5. Click **Generate**
6. **Copy the 16-character password**
7. Save it somewhere safe

---

## Step 3: Clone and Setup (3 minutes)

```bash
# Clone repository
git clone https://github.com/gitababa/jira-weekly-report-v2.git
cd jira-weekly-report-v2

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Step 4: Configure (2 minutes)

### Create `config.json`:

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
    {
      "key": "YOUR_PROJECT_KEY",
      "lead_email": "your-email@example.com"
    }
  ]
}
```

**Replace:**
- `YOUR_PROJECT_KEY` with your Jira project key (e.g., "WRT", "SUP")
- `your-email@example.com` with the email that should receive the report
- `start` and `end` dates to a recent week where you have issues

---

## Step 5: Set Environment Variables (2 minutes)

### Linux/Mac:

```bash
export JIRA_BASE_URL="https://your-domain.atlassian.net"
export JIRA_EMAIL="your-email@example.com"
export JIRA_API_TOKEN="paste-your-api-token-here"
export EMAIL_FROM="your-email@gmail.com"
export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT="587"
export SMTP_USERNAME="your-email@gmail.com"
export SMTP_PASSWORD="paste-your-app-password-here"
```

### Windows PowerShell:

```powershell
$env:JIRA_BASE_URL="https://your-domain.atlassian.net"
$env:JIRA_EMAIL="your-email@example.com"
$env:JIRA_API_TOKEN="paste-your-api-token-here"
$env:EMAIL_FROM="your-email@gmail.com"
$env:SMTP_HOST="smtp.gmail.com"
$env:SMTP_PORT="587"
$env:SMTP_USERNAME="your-email@gmail.com"
$env:SMTP_PASSWORD="paste-your-app-password-here"
```

**Replace:**
- `your-domain` with your Jira Cloud subdomain
- `your-email@example.com` with your Jira account email
- `paste-your-api-token-here` with the API token from Step 1
- `paste-your-app-password-here` with the app password from Step 2

---

## Step 6: Run! (3 minutes)

```bash
# Make sure virtual environment is activated (you should see (venv) in prompt)
python main.py
```

**Expected output:**
```
Window mode: custom_range | start=2025-11-01 | end=2025-11-08 | ...
Project WRT — Window 2025-11-01 to 2025-11-08  [union: start+end]
JQL (union): ...
Fetched 5 issues (union)
Counts — created=2 resolved=1 open@end=4
Total unique issues in union: 5
```

**Check your email!** You should receive a report within 1-2 minutes.

---

## Troubleshooting

### "Authentication failed" error
- Double-check `JIRA_EMAIL` matches your Jira account exactly
- Regenerate API token and try again
- Verify `JIRA_BASE_URL` format: `https://domain.atlassian.net` (no trailing slash)

### "SMTP authentication failed" error
- For Gmail, ensure you're using the **App Password**, not your regular password
- Verify 2-Step Verification is enabled in Google Account
- Try regenerating the App Password

### "No issues fetched" error
- Verify project key exists: Go to Jira and check the project key (e.g., "WRT")
- Adjust the date range to when you know issues exist
- Test the JQL in Jira: Filters → Advanced issue search

### "No module named 'requests'" error
- Virtual environment not activated: `source venv/bin/activate`
- Dependencies not installed: `pip install -r requirements.txt`

---

## Next Steps

### Schedule Automated Reports (GitHub Actions)

1. **Create GitHub repository** (private recommended)

2. **Push code:**
   ```bash
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR-USERNAME/jira-report.git
   git push -u origin main
   ```

3. **Add secrets** in GitHub:
   - Repository → Settings → Secrets and variables → Actions
   - Add all 8 environment variables as secrets

4. **Create workflow file:**
   ```bash
   mkdir -p .github/workflows
   # Copy the workflow file from the repository
   ```

5. **Test manually:**
   - Go to Actions tab → Select workflow → Run workflow

6. **Wait for Monday 10:00 AM** or keep the schedule disabled and run manually when needed

---

## Configuration Options

### Change to "last week" mode (automatic Monday detection):

```json
{
  "report": {
    "window": {
      "mode": "last_week"
    }
  }
}
```

### Add filters (e.g., only bugs):

```json
{
  "global_jql_extra": "AND issuetype = \"Bug\""
}
```

### Monitor multiple projects:

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
    }
  ]
}
```

---

## Getting Help

**Email:** cloud-application-administrator@scalable.capital

**Include in your message:**
- Error message (copy/paste from terminal)
- Your `config.json` (remove sensitive data)
- Output from `python main.py`

---

## Full Documentation

For complete documentation including:
- Detailed setup instructions
- AWS Lambda deployment
- Architecture diagrams
- Troubleshooting guide
- API reference

See: **JIRA_ASSIGNMENT_DELIVERABLES.md**

---

**Estimated total setup time: 20 minutes**

✅ If you've completed all steps, you should now have:
- ✅ A working Jira weekly report system
- ✅ Email reports sent automatically or on-demand
- ✅ Full customization capability via config.json
