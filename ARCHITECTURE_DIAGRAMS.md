# Architecture Diagram (Mermaid)

## System Architecture

```mermaid
graph TB
    subgraph "Trigger Layer"
        A[GitHub Actions<br/>Cron: Mon 10:00 Berlin] 
        B[AWS EventBridge<br/>Cron: Mon 10:00 Berlin]
    end
    
    subgraph "Execution Layer"
        C[Python Application<br/>Ubuntu 22.04 / Python 3.11]
        D[main.py<br/>Orchestrator]
        E[jira.py<br/>API Client]
        F[report.py<br/>Tagging & Counting]
        G[mailer.py<br/>Email Generator]
        H[config.json<br/>Configuration]
    end
    
    subgraph "External APIs"
        I[Jira Cloud API<br/>REST v3]
        J[SMTP Server<br/>Gmail/SendGrid/SES]
    end
    
    subgraph "Output"
        K[Email Report<br/>HTML + CSV]
    end
    
    A -->|Trigger| C
    B -->|Trigger| C
    C --> D
    D --> H
    D --> E
    E -->|JQL Query| I
    I -->|Issues JSON| E
    E --> F
    F -->|Tagged Issues| G
    G -->|SMTP| J
    J -->|Deliver| K
    
    style A fill:#4CAF50,stroke:#2E7D32,color:#fff
    style B fill:#4CAF50,stroke:#2E7D32,color:#fff
    style C fill:#2196F3,stroke:#1565C0,color:#fff
    style I fill:#FF9800,stroke:#E65100,color:#fff
    style J fill:#FF9800,stroke:#E65100,color:#fff
    style K fill:#9C27B0,stroke:#6A1B9A,color:#fff
```

## Data Flow Sequence

```mermaid
sequenceDiagram
    participant Scheduler as GitHub Actions/EventBridge
    participant Main as main.py
    participant Config as config.json
    participant Jira as jira.py
    participant JiraAPI as Jira Cloud API
    participant Report as report.py
    participant Mailer as mailer.py
    participant SMTP as SMTP Server
    participant Lead as Project Lead
    
    Scheduler->>Main: Trigger (Monday 10:00 AM)
    Main->>Config: Load configuration
    Config-->>Main: Projects, window, filters
    
    loop For each project
        Main->>Jira: build_jql_union_window()
        Jira-->>Main: JQL query string
        Main->>Jira: get_issues(jql)
        Jira->>JiraAPI: GET /rest/api/3/search/jql
        
        alt Success
            JiraAPI-->>Jira: Issues JSON
            Jira-->>Main: List of issues
        else API Error (429/500/502/503/504)
            JiraAPI-->>Jira: Error
            Jira->>Jira: Retry with backoff (5x)
            Jira->>JiraAPI: Retry request
            JiraAPI-->>Jira: Success or fail
        end
        
        Main->>Report: tag_issues(issues, start, end)
        Report-->>Main: Tagged issues + counts
        
        Main->>Mailer: send_report(email, project, window, rows, counts)
        Mailer->>Mailer: Generate HTML
        Mailer->>Mailer: Generate CSV
        Mailer->>SMTP: Send email with attachment
        SMTP->>Lead: Deliver email
    end
    
    Main-->>Scheduler: Success/Failure status
```

## Deployment Options

```mermaid
graph LR
    subgraph "Option 1: GitHub Actions"
        A1[GitHub Repo] --> B1[Workflow File<br/>.github/workflows/report.yml]
        B1 --> C1[Scheduled Execution<br/>2,000 min/month free]
        C1 --> D1[Ubuntu Runner<br/>7 GB RAM, 2 CPU]
    end
    
    subgraph "Option 2: AWS Lambda"
        A2[Lambda Function<br/>512 MB, Python 3.11] --> B2[EventBridge Scheduler<br/>Timezone-aware cron]
        B2 --> C2[Execution<br/>~$0.10/month]
        C2 --> D2[CloudWatch Logs<br/>Monitoring]
    end
    
    D1 --> E[Jira API + SMTP]
    D2 --> E
    
    style A1 fill:#4CAF50,stroke:#2E7D32,color:#fff
    style A2 fill:#FF9800,stroke:#E65100,color:#fff
```

## Security Architecture

```mermaid
graph TB
    subgraph "Secrets Management"
        A[Environment Variables<br/>or GitHub Secrets]
        B[JIRA_API_TOKEN]
        C[SMTP_PASSWORD]
        D[Other Credentials]
    end
    
    subgraph "Application"
        E[Python App<br/>Read-only access]
    end
    
    subgraph "External Services"
        F[Jira Cloud<br/>HTTPS + Basic Auth]
        G[SMTP Server<br/>TLS 1.2+ STARTTLS]
    end
    
    A --> B
    A --> C
    A --> D
    B --> E
    C --> E
    D --> E
    E -->|Encrypted Connection| F
    E -->|Encrypted Connection| G
    
    style A fill:#F44336,stroke:#C62828,color:#fff
    style E fill:#2196F3,stroke:#1565C0,color:#fff
    style F fill:#4CAF50,stroke:#2E7D32,color:#fff
    style G fill:#4CAF50,stroke:#2E7D32,color:#fff
```

## JQL Query Optimization

```mermaid
graph LR
    subgraph "Traditional Approach (3 queries)"
        A1[Query 1:<br/>Created in window] --> D1[Issue Set 1]
        A2[Query 2:<br/>Resolved in window] --> D2[Issue Set 2]
        A3[Query 3:<br/>Open at end] --> D3[Issue Set 3]
        D1 --> E1[Merge + Deduplicate]
        D2 --> E1
        D3 --> E1
        E1 --> F1[Final Result]
    end
    
    subgraph "Optimized Approach (1 query)"
        B1[Union Query:<br/>Created OR Resolved OR Open] --> C1[Single Issue Set<br/>No duplicates]
        C1 --> C2[Tag issues<br/>in-memory]
        C2 --> F2[Final Result]
    end
    
    style A1 fill:#FF5722,stroke:#D84315,color:#fff
    style A2 fill:#FF5722,stroke:#D84315,color:#fff
    style A3 fill:#FF5722,stroke:#D84315,color:#fff
    style B1 fill:#4CAF50,stroke:#2E7D32,color:#fff
    style C1 fill:#4CAF50,stroke:#2E7D32,color:#fff
    
    G[3 API calls<br/>More network overhead] -.->|vs| H[1 API call<br/>3x faster]
```

---

## How to View Diagrams

These Mermaid diagrams can be viewed by:

1. **GitHub**: Automatically rendered in GitHub README.md
2. **VS Code**: Install "Markdown Preview Mermaid Support" extension
3. **Online**: Paste code into https://mermaid.live
4. **Export**: Use Mermaid CLI to generate PNG/SVG images

Example command to export:
```bash
npm install -g @mermaid-js/mermaid-cli
mmdc -i architecture.md -o architecture.png
```
