import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import requests
from typing import List, Dict, Any

# ---------------------------
# HTTP / Jira helpers
# ---------------------------

def make_auth_headers(email: str, api_token: str) -> Dict[str, str]:
    import base64
    token = base64.b64encode(f"{email}:{api_token}".encode("utf-8")).decode("utf-8")
    return {
        "Authorization": f"Basic {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

def jira_get(base_url: str, path: str, headers: Dict[str, str],
             params: Dict[str, Any] = None, timeout: int = 30):
    url = base_url.rstrip("/") + path
    resp = requests.get(url, headers=headers, params=params or {}, timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(f"GET {path} failed [{resp.status_code}]: {resp.text[:400]}")
    return resp.json()

def fetch_projects(base_url: str, headers: Dict[str, str]) -> List[Dict[str, Any]]:
    projects = []
    start_at = 0
    max_results = 50
    while True:
        data = jira_get(base_url, "/rest/api/3/project/search", headers, params={"startAt": start_at, "maxResults": max_results})
        values = data.get("values", [])
        projects.extend(values)
        if len(values) < max_results:
            break
        start_at += max_results
    out = [{"key": p.get("key"), "name": p.get("name")} for p in projects if p.get("key")]
    out.sort(key=lambda x: x["key"])
    return out

def fetch_issue_types(base_url: str, headers: Dict[str, str]) -> List[str]:
    data = jira_get(base_url, "/rest/api/3/issuetype", headers)
    names = [it.get("name") for it in data if it.get("name")]
    return sorted(set(names))

def fetch_priorities(base_url: str, headers: Dict[str, str]) -> List[str]:
    data = jira_get(base_url, "/rest/api/3/priority", headers)
    names = [p.get("name") for p in data if p.get("name")]
    return sorted(set(names))

def jql_quote_list(values: List[str]) -> str:
        """
        Convert list of values to JQL IN clause format.
        Jira JQL expects: ("value1", "value2", "value3")
        We use Python's string literal with regular double quotes.
        """
        safe = ['"{}"'.format(v) for v in values]
        return ", ".join(safe)

def build_global_jql(issue_types: List[str], priorities: List[str], extra_freeform: str) -> str:
    parts = []
    if issue_types:
        parts.append(f"AND issuetype in ({jql_quote_list(issue_types)})")
    if priorities:
        parts.append(f"AND priority in ({jql_quote_list(priorities)})")
    if extra_freeform and extra_freeform.strip():
        s = extra_freeform.strip()
        if not s.upper().startswith(("AND ", "OR ")):
            s = "AND " + s
        parts.append(s)
    return " ".join(parts)

def validate_date(s: str) -> bool:
    import datetime as dt
    try:
        dt.date.fromisoformat(s)
        return True
    except Exception:
        return False


# ---------------------------
# Tooltip Helper Class
# ---------------------------

class ToolTip:
    """Create a tooltip for a given widget"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        if self.tooltip_window or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert") if hasattr(self.widget, 'bbox') else (0, 0, 0, 0)
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                        background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                        font=("Arial", 9))
        label.pack()

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


# ---------------------------
# GUI
# ---------------------------

class ConfigBuilderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Jira Report Config Builder")
        self.geometry("1050x800")
        
        # Configure colors
        self.colors = {
            "success": "#28a745",
            "error": "#dc3545",
            "warning": "#ffc107",
            "info": "#17a2b8",
            "selected": "#e3f2fd",
            "bg_light": "#f8f9fa"
        }
        
        # state
        self.available_projects: List[Dict[str, Any]] = []
        self.issue_types: List[str] = []
        self.priorities: List[str] = []
        self.selected_projects: List[Dict[str, str]] = []
        self.selected_issue_types: List[str] = []
        self.selected_priorities: List[str] = []
        
        # connection vars
        self.base_url_var = tk.StringVar()
        self.email_var = tk.StringVar()
        self.token_var = tk.StringVar()
        
        # selected project form
        self.pkey_var = tk.StringVar()
        self.plead_var = tk.StringVar()
        
        # extra JQL
        self.extra_jql_var = tk.StringVar()
        
        # window options
        self.range_mode_var = tk.StringVar(value="last_week")
        self.rolling_n_var = tk.StringVar(value="7")
        self.custom_start_var = tk.StringVar()
        self.custom_end_var = tk.StringVar()
        
        # output
        self.top_n_var = tk.StringVar(value="10")
        self.include_csv_var = tk.BooleanVar(value=True)
        self.alerts_email_var = tk.StringVar()
        
        # Status tracking
        self.connection_status = False
        
        self._build_layout()
        self._create_tooltips()

    def _build_layout(self):
        # Add main container with padding
        main_container = ttk.Frame(self, padding="10")
        main_container.pack(fill="both", expand=True)
        
        # Add scrollbar for the whole window
        canvas = tk.Canvas(main_container)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # ============ STEP 1: Connection ============
        conn = ttk.LabelFrame(scrollable_frame, text="📡 Step 1: Jira Connection", padding="15")
        conn.pack(fill="x", padx=5, pady=8)
        
        # Help text
        help_text = ttk.Label(conn, text="Enter your Jira credentials to connect. API token can be generated from Jira profile settings.",
                             foreground="gray", font=("Arial", 9))
        help_text.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0,10))
        
        # Connection fields
        ttk.Label(conn, text="Base URL:", font=("Arial", 9, "bold")).grid(row=1, column=0, sticky="w", pady=5)
        self.base_url_entry = ttk.Entry(conn, textvariable=self.base_url_var, width=55)
        self.base_url_entry.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        ttk.Label(conn, text="e.g., https://your-domain.atlassian.net", foreground="gray", font=("Arial", 8)).grid(row=1, column=2, sticky="w")
        
        ttk.Label(conn, text="Email:", font=("Arial", 9, "bold")).grid(row=2, column=0, sticky="w", pady=5)
        self.email_entry = ttk.Entry(conn, textvariable=self.email_var, width=40)
        self.email_entry.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        
        ttk.Label(conn, text="API Token:", font=("Arial", 9, "bold")).grid(row=3, column=0, sticky="w", pady=5)
        self.token_entry = ttk.Entry(conn, textvariable=self.token_var, width=40, show="•")
        self.token_entry.grid(row=3, column=1, padx=10, pady=5, sticky="w")
        
        # Status indicator and button
        status_frame = ttk.Frame(conn)
        status_frame.grid(row=4, column=0, columnspan=3, pady=10, sticky="w")
        
        self.test_btn = ttk.Button(status_frame, text="🔌 Test Connection & Fetch Metadata", command=self.on_test)
        self.test_btn.pack(side="left", padx=(0,10))
        
        self.status_indicator = tk.Canvas(status_frame, width=16, height=16, highlightthickness=0)
        self.status_indicator.pack(side="left", padx=(0,5))
        self.status_circle = self.status_indicator.create_oval(2, 2, 14, 14, fill="gray", outline="darkgray")
        
        self.test_msg = ttk.Label(status_frame, text="Not connected", foreground="gray", font=("Arial", 9))
        self.test_msg.pack(side="left")
        
        # ============ STEP 2: Filters ============
        meta = ttk.LabelFrame(scrollable_frame, text="🔍 Step 2: Choose Filters (Optional)", padding="15")
        meta.pack(fill="x", padx=5, pady=8)
        
        # Help text
        help_filter = ttk.Label(meta, text="Select projects, issue types, and priorities to include in your report. Leave empty to include all.",
                               foreground="gray", font=("Arial", 9))
        help_filter.pack(anchor="w", pady=(0,10))
        
        # Projects section
        proj_container = ttk.LabelFrame(meta, text="Projects", padding="10")
        proj_container.pack(fill="x", pady=8)
        
        proj_layout = ttk.Frame(proj_container)
        proj_layout.pack(fill="x")
        
        # Left: Available projects
        left_proj = ttk.Frame(proj_layout)
        left_proj.pack(side="left", fill="both", expand=True, padx=(0,10))
        
        ttk.Label(left_proj, text="Available Projects:", font=("Arial", 9, "bold")).pack(anchor="w", pady=(0,5))
        
        proj_scroll = ttk.Scrollbar(left_proj)
        proj_scroll.pack(side="right", fill="y")
        
        self.projects_list = tk.Listbox(left_proj, width=40, height=8, exportselection=False,
                                       yscrollcommand=proj_scroll.set, font=("Arial", 9))
        self.projects_list.pack(side="left", fill="both", expand=True)
        proj_scroll.config(command=self.projects_list.yview)
        self.projects_list.bind("<<ListboxSelect>>", self.on_project_select)
        
        # Right: Selected projects
        right_proj = ttk.Frame(proj_layout)
        right_proj.pack(side="left", fill="both", expand=True, padx=(10,0))
        
        # Add/Update form
        form_frame = ttk.LabelFrame(right_proj, text="Add Project", padding="8")
        form_frame.pack(fill="x", pady=(0,10))
        
        ttk.Label(form_frame, text="Project Key:", font=("Arial", 9)).grid(row=0, column=0, sticky="w", pady=3)
        self.pkey_entry = ttk.Entry(form_frame, textvariable=self.pkey_var, width=15)
        self.pkey_entry.grid(row=0, column=1, padx=5, pady=3)
        
        ttk.Label(form_frame, text="Lead Email:", font=("Arial", 9)).grid(row=1, column=0, sticky="w", pady=3)
        self.plead_entry = ttk.Entry(form_frame, textvariable=self.plead_var, width=30)
        self.plead_entry.grid(row=1, column=1, padx=5, pady=3)
        
        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=8)
        
        self.add_btn = ttk.Button(btn_frame, text="➕ Add/Update", command=self.on_add_update)
        self.add_btn.pack(side="left", padx=3)
        
        self.remove_btn = ttk.Button(btn_frame, text="➖ Remove", command=self.on_remove_selected)
        self.remove_btn.pack(side="left", padx=3)
        
        # Selected projects list
        ttk.Label(right_proj, text="Selected Projects:", font=("Arial", 9, "bold")).pack(anchor="w", pady=(0,5))
        
        sel_scroll = ttk.Scrollbar(right_proj)
        sel_scroll.pack(side="right", fill="y")
        
        self.selected_list = tk.Listbox(right_proj, width=40, height=8, exportselection=False,
                                       yscrollcommand=sel_scroll.set, font=("Arial", 9))
        self.selected_list.pack(side="left", fill="both", expand=True)
        sel_scroll.config(command=self.selected_list.yview)
        self.selected_list.bind("<<ListboxSelect>>", self.on_selected_click)
        
        # Issue Types and Priorities
        types_container = ttk.LabelFrame(meta, text="Issue Filters", padding="10")
        types_container.pack(fill="x", pady=8)
        
        # Info message about default behavior
        info_msg = ttk.Label(types_container, 
                            text="💡 Tip: If nothing is selected, all issue types and priorities will be included in the report.",
                            foreground="gray", font=("Arial", 9, "italic"))
        info_msg.pack(anchor="w", pady=(0,10))
        
        types_layout = ttk.Frame(types_container)
        types_layout.pack(fill="x")
        
        # Issue Types
        left_types = ttk.Frame(types_layout)
        left_types.pack(side="left", fill="both", expand=True, padx=(0,10))
        
        header_frame = ttk.Frame(left_types)
        header_frame.pack(fill="x", pady=(0,5))
        ttk.Label(header_frame, text="Issue Types:", font=("Arial", 9, "bold")).pack(side="left")
        ttk.Label(header_frame, text="(Click to toggle)", foreground="gray", font=("Arial", 8)).pack(side="left", padx=(5,0))
        
        # Action buttons for issue types
        types_btn_frame = ttk.Frame(left_types)
        types_btn_frame.pack(fill="x", pady=(0,5))
        ttk.Button(types_btn_frame, text="Select All", command=self.select_all_issue_types, width=12).pack(side="left", padx=(0,3))
        ttk.Button(types_btn_frame, text="Clear All", command=self.clear_all_issue_types, width=12).pack(side="left")
        
        # Scrollable frame for checkboxes
        types_canvas = tk.Canvas(left_types, height=150, highlightthickness=1, highlightbackground="lightgray")
        types_scroll = ttk.Scrollbar(left_types, orient="vertical", command=types_canvas.yview)
        self.types_checkbox_frame = ttk.Frame(types_canvas)
        
        self.types_checkbox_frame.bind(
            "<Configure>",
            lambda e: types_canvas.configure(scrollregion=types_canvas.bbox("all"))
        )
        
        types_canvas.create_window((0, 0), window=self.types_checkbox_frame, anchor="nw")
        types_canvas.configure(yscrollcommand=types_scroll.set)
        
        types_canvas.pack(side="left", fill="both", expand=True)
        types_scroll.pack(side="right", fill="y")
        
        # Store checkbox variables
        self.issue_type_vars = {}
        
        # Priorities
        right_priorities = ttk.Frame(types_layout)
        right_priorities.pack(side="left", fill="both", expand=True, padx=(10,0))
        
        header_frame2 = ttk.Frame(right_priorities)
        header_frame2.pack(fill="x", pady=(0,5))
        ttk.Label(header_frame2, text="Priorities:", font=("Arial", 9, "bold")).pack(side="left")
        ttk.Label(header_frame2, text="(Click to toggle)", foreground="gray", font=("Arial", 8)).pack(side="left", padx=(5,0))
        
        # Action buttons for priorities
        pri_btn_frame = ttk.Frame(right_priorities)
        pri_btn_frame.pack(fill="x", pady=(0,5))
        ttk.Button(pri_btn_frame, text="Select All", command=self.select_all_priorities, width=12).pack(side="left", padx=(0,3))
        ttk.Button(pri_btn_frame, text="Clear All", command=self.clear_all_priorities, width=12).pack(side="left")
        
        # Scrollable frame for checkboxes
        pri_canvas = tk.Canvas(right_priorities, height=150, highlightthickness=1, highlightbackground="lightgray")
        pri_scroll = ttk.Scrollbar(right_priorities, orient="vertical", command=pri_canvas.yview)
        self.priorities_checkbox_frame = ttk.Frame(pri_canvas)
        
        self.priorities_checkbox_frame.bind(
            "<Configure>",
            lambda e: pri_canvas.configure(scrollregion=pri_canvas.bbox("all"))
        )
        
        pri_canvas.create_window((0, 0), window=self.priorities_checkbox_frame, anchor="nw")
        pri_canvas.configure(yscrollcommand=pri_scroll.set)
        
        pri_canvas.pack(side="left", fill="both", expand=True)
        pri_scroll.pack(side="right", fill="y")
        
        # Store checkbox variables
        self.priority_vars = {}
        
        # Selection summary
        self.selection_summary = ttk.Label(types_container, text="", foreground=self.colors["info"], font=("Arial", 9))
        self.selection_summary.pack(anchor="w", pady=(8,0))
        
        # Extra JQL
        jql_container = ttk.LabelFrame(meta, text="Advanced JQL Filter (Optional)", padding="10")
        jql_container.pack(fill="x", pady=8)
        
        ttk.Label(jql_container, text='Add custom JQL conditions, e.g., labels = "Important" OR assignee = currentUser()',
                 foreground="gray", font=("Arial", 9)).pack(anchor="w", pady=(0,5))
        self.extra_jql_entry = ttk.Entry(jql_container, textvariable=self.extra_jql_var, width=90, font=("Arial", 9))
        self.extra_jql_entry.pack(fill="x")
        
        # ============ STEP 3: Report Configuration ============
        report_frame = ttk.LabelFrame(scrollable_frame, text="📊 Step 3: Report Configuration", padding="15")
        report_frame.pack(fill="x", padx=5, pady=8)
        
        # Date Range
        date_container = ttk.LabelFrame(report_frame, text="Date Range", padding="10")
        date_container.pack(fill="x", pady=(0,10))
        
        # Last Week option
        lw_frame = ttk.Frame(date_container)
        lw_frame.pack(fill="x", pady=3)
        self.rb_lastweek = ttk.Radiobutton(lw_frame, text="📅 Last week (Monday–Sunday)",
                                          variable=self.range_mode_var, value="last_week",
                                          command=self.on_date_mode_change)
        self.rb_lastweek.pack(side="left")
        
        # Rolling days option
        rd_frame = ttk.Frame(date_container)
        rd_frame.pack(fill="x", pady=3)
        self.rb_rolling = ttk.Radiobutton(rd_frame, text="🔄 Rolling last",
                                         variable=self.range_mode_var, value="rolling_days",
                                         command=self.on_date_mode_change)
        self.rb_rolling.pack(side="left")
        self.rolling_n_entry = ttk.Entry(rd_frame, textvariable=self.rolling_n_var, width=6)
        self.rolling_n_entry.pack(side="left", padx=(5,3))
        ttk.Label(rd_frame, text="days").pack(side="left")
        
        # Custom range option
        cr_frame = ttk.Frame(date_container)
        cr_frame.pack(fill="x", pady=3)
        self.rb_custom = ttk.Radiobutton(cr_frame, text="📆 Custom date range:",
                                        variable=self.range_mode_var, value="custom_range",
                                        command=self.on_date_mode_change)
        self.rb_custom.pack(side="left")
        ttk.Label(cr_frame, text="Start:").pack(side="left", padx=(10,3))
        self.custom_start_entry = ttk.Entry(cr_frame, textvariable=self.custom_start_var, width=12)
        self.custom_start_entry.pack(side="left", padx=(0,10))
        ttk.Label(cr_frame, text="End:").pack(side="left", padx=(0,3))
        self.custom_end_entry = ttk.Entry(cr_frame, textvariable=self.custom_end_var, width=12)
        self.custom_end_entry.pack(side="left")
        ttk.Label(cr_frame, text="(YYYY-MM-DD)", foreground="gray", font=("Arial", 8)).pack(side="left", padx=(5,0))
        
        # Output Options
        output_container = ttk.LabelFrame(report_frame, text="Output Options", padding="10")
        output_container.pack(fill="x", pady=(0,10))
        
        opt_row1 = ttk.Frame(output_container)
        opt_row1.pack(fill="x", pady=3)
        
        ttk.Label(opt_row1, text="Top N issues in email:", font=("Arial", 9)).pack(side="left")
        self.top_n_entry = ttk.Entry(opt_row1, textvariable=self.top_n_var, width=6)
        self.top_n_entry.pack(side="left", padx=(5,15))
        
        self.include_csv_chk = ttk.Checkbutton(opt_row1, text="📎 Include CSV attachments",
                                              variable=self.include_csv_var)
        self.include_csv_chk.pack(side="left")
        
        opt_row2 = ttk.Frame(output_container)
        opt_row2.pack(fill="x", pady=3)
        
        ttk.Label(opt_row2, text="Alert email (for errors):", font=("Arial", 9)).pack(side="left")
        self.alerts_email_entry = ttk.Entry(opt_row2, textvariable=self.alerts_email_var, width=35)
        self.alerts_email_entry.pack(side="left", padx=(5,0))
        
        # ============ STEP 4: Generate Config ============
        gen_frame = ttk.LabelFrame(scrollable_frame, text="✅ Step 4: Generate Configuration", padding="15")
        gen_frame.pack(fill="x", padx=5, pady=8)
        
        ttk.Label(gen_frame, text="Click below to create your config.json file with all the settings above.",
                 foreground="gray", font=("Arial", 9)).pack(anchor="w", pady=(0,10))
        
        gen_btn_frame = ttk.Frame(gen_frame)
        gen_btn_frame.pack(fill="x")
        
        self.gen_btn = ttk.Button(gen_btn_frame, text="💾 Generate config.json",
                                 command=self.on_generate)
        self.gen_btn.pack(side="left", padx=(0,10))
        
        self.gen_status_indicator = tk.Canvas(gen_btn_frame, width=16, height=16, highlightthickness=0)
        self.gen_status_indicator.pack(side="left", padx=(0,5))
        self.gen_status_circle = self.gen_status_indicator.create_oval(2, 2, 14, 14, fill="gray", outline="darkgray")
        
        self.gen_msg = ttk.Label(gen_btn_frame, text="", font=("Arial", 9))
        self.gen_msg.pack(side="left")
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Enable mousewheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Initial state
        self.on_date_mode_change()

    def _create_tooltips(self):
        """Create helpful tooltips for UI elements"""
        ToolTip(self.base_url_entry, "Enter your Jira instance URL\nExample: https://yourcompany.atlassian.net")
        ToolTip(self.email_entry, "The email address associated with your Jira account")
        ToolTip(self.token_entry, "API token from Jira Account Settings → Security → API tokens")
        ToolTip(self.pkey_entry, "The project key (e.g., PROJ, ENG, MKTG)")
        ToolTip(self.plead_entry, "Email address of the project lead who will receive reports")
        ToolTip(self.extra_jql_entry, "Advanced: Add custom JQL conditions\nExample: labels = 'Important' AND status != 'Closed'")
        ToolTip(self.top_n_entry, "Number of top issues to display in email body (rest in CSV)")
        ToolTip(self.rolling_n_entry, "Number of days to look back from today")

    def on_date_mode_change(self):
        """Enable/disable date inputs based on selected mode"""
        mode = self.range_mode_var.get()
        
        # Disable all first
        self.rolling_n_entry.config(state="disabled")
        self.custom_start_entry.config(state="disabled")
        self.custom_end_entry.config(state="disabled")
        
        # Enable based on selection
        if mode == "rolling_days":
            self.rolling_n_entry.config(state="normal")
        elif mode == "custom_range":
            self.custom_start_entry.config(state="normal")
            self.custom_end_entry.config(state="normal")

    def update_selection_summary(self):
        """Update the summary text showing what's selected"""
        it_count = sum(1 for var in self.issue_type_vars.values() if var.get())
        pr_count = sum(1 for var in self.priority_vars.values() if var.get())
        
        parts = []
        if it_count > 0:
            parts.append(f"{it_count} issue type(s) selected")
        else:
            parts.append("All issue types")
            
        if pr_count > 0:
            parts.append(f"{pr_count} priority/priorities selected")
        else:
            parts.append("All priorities")
        
        summary = "✓ " + ", ".join(parts)
        
        # Color based on whether anything is selected
        if it_count > 0 or pr_count > 0:
            self.selection_summary.config(text=summary, foreground=self.colors["success"])
        else:
            self.selection_summary.config(text=summary, foreground=self.colors["info"])
    
    def select_all_issue_types(self):
        """Select all issue type checkboxes"""
        for var in self.issue_type_vars.values():
            var.set(True)
        self.update_selection_summary()
    
    def clear_all_issue_types(self):
        """Clear all issue type checkboxes"""
        for var in self.issue_type_vars.values():
            var.set(False)
        self.update_selection_summary()
    
    def select_all_priorities(self):
        """Select all priority checkboxes"""
        for var in self.priority_vars.values():
            var.set(True)
        self.update_selection_summary()
    
    def clear_all_priorities(self):
        """Clear all priority checkboxes"""
        for var in self.priority_vars.values():
            var.set(False)
        self.update_selection_summary()

    def on_issue_type_select(self, event=None):
        """Handle issue type selection"""
        self.update_selection_summary()

    def on_priority_select(self, event=None):
        """Handle priority selection"""
        self.update_selection_summary()

    def update_status_indicator(self, canvas, circle, success: bool):
        """Update a status indicator circle"""
        if success:
            canvas.itemconfig(circle, fill=self.colors["success"], outline="darkgreen")
        else:
            canvas.itemconfig(circle, fill=self.colors["error"], outline="darkred")

    def on_test(self):
        """Test Jira connection and fetch metadata"""
        base = self.base_url_var.get().strip()
        email = self.email_var.get().strip()
        token = self.token_var.get().strip()
        
        if not base or not email or not token:
            self.test_msg.config(text="⚠ Please fill all connection fields", foreground=self.colors["warning"])
            self.status_indicator.itemconfig(self.status_circle, fill=self.colors["warning"], outline="darkorange")
            return
        
        # Show loading state
        self.test_btn.config(state="disabled", text="🔄 Connecting...")
        self.test_msg.config(text="Connecting to Jira...", foreground=self.colors["info"])
        self.update()
        
        try:
            headers = make_auth_headers(email, token)
            _ = jira_get(base, "/rest/api/3/myself", headers)
            
            # Fetch metadata
            self.available_projects = fetch_projects(base, headers)
            self.projects_list.delete(0, tk.END)
            for p in self.available_projects:
                self.projects_list.insert(tk.END, f"{p['key']} — {p['name']}")
            
            self.issue_types = fetch_issue_types(base, headers)
            self.priorities = fetch_priorities(base, headers)
            
            # Clear existing checkboxes
            for widget in self.types_checkbox_frame.winfo_children():
                widget.destroy()
            for widget in self.priorities_checkbox_frame.winfo_children():
                widget.destroy()
            
            self.issue_type_vars.clear()
            self.priority_vars.clear()
            
            # Create checkboxes for issue types
            for it in self.issue_types:
                var = tk.BooleanVar(value=False)
                self.issue_type_vars[it] = var
                cb = ttk.Checkbutton(self.types_checkbox_frame, text=it, variable=var,
                                    command=self.update_selection_summary)
                cb.pack(anchor="w", pady=2, padx=5)
            
            # Create checkboxes for priorities
            for pr in self.priorities:
                var = tk.BooleanVar(value=False)
                self.priority_vars[pr] = var
                cb = ttk.Checkbutton(self.priorities_checkbox_frame, text=pr, variable=var,
                                    command=self.update_selection_summary)
                cb.pack(anchor="w", pady=2, padx=5)
            
            # Success
            self.connection_status = True
            self.test_msg.config(text=f"✓ Connected! Found {len(self.available_projects)} projects",
                               foreground=self.colors["success"])
            self.update_status_indicator(self.status_indicator, self.status_circle, True)
            
        except Exception as e:
            self.connection_status = False
            error_msg = str(e)
            if len(error_msg) > 100:
                error_msg = error_msg[:100] + "..."
            self.test_msg.config(text=f"✗ Connection failed: {error_msg}",
                               foreground=self.colors["error"])
            self.update_status_indicator(self.status_indicator, self.status_circle, False)
        
        finally:
            self.test_btn.config(state="normal", text="🔌 Test Connection & Fetch Metadata")

    def on_project_select(self, event=None):
        """Handle project selection from available list"""
        sel = self.projects_list.curselection()
        if not sel:
            return
        line = self.projects_list.get(sel[0])
        key = line.split(" — ")[0].strip()
        self.pkey_var.set(key)
        self.plead_var.set("")

    def on_selected_click(self, event=None):
        """Handle click on selected project"""
        sel = self.selected_list.curselection()
        if not sel:
            return
        line = self.selected_list.get(sel[0])
        key = line.split(" → ")[0].strip()
        email = line.split(" → ")[1].strip()
        self.pkey_var.set(key)
        self.plead_var.set(email)

    def on_add_update(self):
        """Add or update a project"""
        pkey = self.pkey_var.get().strip()
        plead = self.plead_var.get().strip()
        
        if not pkey or not plead:
            messagebox.showwarning("Missing Information", "Please enter both Project Key and Lead Email.")
            return
        
        # Basic email validation
        if "@" not in plead or "." not in plead:
            messagebox.showwarning("Invalid Email", "Please enter a valid email address.")
            return
        
        # Check if updating existing
        updated = False
        for item in self.selected_projects:
            if item["key"] == pkey:
                item["lead_email"] = plead
                updated = True
                break
        
        if not updated:
            self.selected_projects.append({"key": pkey, "lead_email": plead})
        
        self.refresh_selected_listbox()
        
        # Clear form
        self.pkey_var.set("")
        self.plead_var.set("")
        
        # Show feedback
        action = "updated" if updated else "added"
        messagebox.showinfo("Success", f"Project {pkey} {action} successfully!")

    def on_remove_selected(self):
        """Remove selected project"""
        sel = self.selected_list.curselection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select a project to remove.")
            return
        
        line = self.selected_list.get(sel[0])
        key = line.split(" → ")[0].strip()
        
        if messagebox.askyesno("Confirm Removal", f"Remove project {key}?"):
            self.selected_projects = [p for p in self.selected_projects if p["key"] != key]
            self.refresh_selected_listbox()
            self.pkey_var.set("")
            self.plead_var.set("")

    def refresh_selected_listbox(self):
        """Refresh the selected projects listbox"""
        self.selected_list.delete(0, tk.END)
        for p in self.selected_projects:
            self.selected_list.insert(tk.END, f"{p['key']} → {p['lead_email']}")

    def on_generate(self):
        """Generate config.json file"""
        # Check connection
        if not self.connection_status:
            messagebox.showwarning("Connection Required",
                                 "Please test your Jira connection first (Step 1).")
            return
        
        # Check for projects
        if not self.selected_projects:
            if not messagebox.askyesno("No Projects Selected",
                                      "No projects are selected. This will create a config with no project filters.\n\nContinue anyway?"):
                return
        
        # Gather selected filters from checkboxes
        it_sel = [name for name, var in self.issue_type_vars.items() if var.get()]
        pr_sel = [name for name, var in self.priority_vars.items() if var.get()]
        extra = self.extra_jql_var.get().strip()
        global_jql = build_global_jql(it_sel, pr_sel, extra)
        
        # Window mode
        mode = self.range_mode_var.get()
        if mode == "last_week":
            window_cfg = {"mode": "last_week"}
        elif mode == "rolling_days":
            n_str = self.rolling_n_var.get().strip() or "7"
            try:
                n = max(1, int(n_str))
            except ValueError:
                messagebox.showerror("Invalid Input", "Rolling N must be a positive integer.")
                return
            window_cfg = {"mode": "rolling_days", "rolling_days": n}
        else:
            cstart = self.custom_start_var.get().strip()
            cend = self.custom_end_var.get().strip()
            if not (validate_date(cstart) and validate_date(cend)):
                messagebox.showerror("Invalid Date", "Custom dates must be in YYYY-MM-DD format.")
                return
            window_cfg = {"mode": "custom_range", "start": cstart, "end": cend}
        
        # Top N, CSV, alerts
        topn_str = self.top_n_var.get().strip() or "10"
        try:
            topn = max(1, int(topn_str))
        except ValueError:
            messagebox.showerror("Invalid Input", "Top N must be a positive integer.")
            return
        
        include_csv = bool(self.include_csv_var.get())
        alerts_email = self.alerts_email_var.get().strip()
        
        # Build config
        cfg = {
            "report": {
                "timezone_label": "Europe/Berlin",
                "window": window_cfg,
                "show_top_n": topn,
                "include_csv_attachment": include_csv,
                "alerts_email": alerts_email,
            },
            "global_jql_extra": global_jql,
            "projects": self.selected_projects,
        }
        
        # Ask where to save
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="config.json",
            title="Save Configuration File"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
            
            self.gen_msg.config(text=f"✓ Config saved: {file_path}",
                              foreground=self.colors["success"])
            self.update_status_indicator(self.gen_status_indicator, self.gen_status_circle, True)
            
            messagebox.showinfo("Success!",
                              f"Configuration file created successfully!\n\n{file_path}\n\n"
                              f"Projects: {len(self.selected_projects)}\n"
                              f"Issue Types: {len(it_sel) if it_sel else 'All'}\n"
                              f"Priorities: {len(pr_sel) if pr_sel else 'All'}")
            
        except Exception as e:
            self.gen_msg.config(text=f"✗ Failed to save: {e}",
                              foreground=self.colors["error"])
            self.update_status_indicator(self.gen_status_indicator, self.gen_status_circle, False)
            messagebox.showerror("Error", f"Failed to create config file:\n{e}")


if __name__ == "__main__":
    app = ConfigBuilderApp()
    app.mainloop()