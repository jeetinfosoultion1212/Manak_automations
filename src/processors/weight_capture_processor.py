#!/usr/bin/env python3
"""
Weight Capture Processor Module
Handles automated weight entry from huid_data table to MANAK portal
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from datetime import datetime, timedelta
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import base64

from config import DB_CONFIG
from portal_config import portal_base, build_portal_url


class WeightCaptureProcessor:
    """Handles automated weight capture from database to portal"""
    
    def __init__(self, driver, log_callback, license_check_callback, app_context=None):
        self.driver = driver
        self.main_log_callback = log_callback
        self.check_license_before_action = license_check_callback
        self.app_context = app_context
        self.notebook = None
        self.log_text = None
        
        # Database connection details
        self.db_config = DB_CONFIG.copy()
        
        # Get firm ID from app context
        self.current_firm_id = self.get_firm_id_from_settings()
        
        # Jobs data
        self.jobs_data = []
        self.selected_jobs = set()
        self.weights_cache = {}  # Cache for fast lookup
        
        # Material type tracking (Gold or Silver)
        self.current_material_type = "Gold"  # Default to Gold
        
        # Scan controls
        self.is_scanning = False
        self.scan_cancelled = False
        self.start_page_var = None
        self.end_page_var = None
        self.date_from_var = None
        self.date_to_var = None
        self.defer_db_fetch_var = None
        self.gold_btn = None
        self.silver_btn = None
        self.stop_scan_btn = None
        self.stop_requested_logged = False
        
    def get_firm_id_from_settings(self):
        """Get Firm ID from settings page only. Do not use default."""
        try:
            if self.app_context and hasattr(self.app_context, 'firm_id_var'):
                firm_id = self.app_context.firm_id_var.get().strip()
                if firm_id:
                    return firm_id
        except Exception as e:
            print(f"Warning: Could not get Firm ID from settings: {e}")
        # If not found, return None or raise error
        return None
    
    def refresh_firm_id(self):
        """Refresh firm_id from settings and update display"""
        old_firm_id = self.current_firm_id
        self.current_firm_id = self.get_firm_id_from_settings()
        
        if hasattr(self, 'firm_id_label'):
            self.firm_id_label.config(text=f"Firm {self.current_firm_id}")
        
        if old_firm_id != self.current_firm_id:
            self.log_weight(f"🏢 Firm ID updated from {old_firm_id} to {self.current_firm_id}")
    
    def populate_weight_capture_tab(self, capture_frame):
        """Populate Weight Capture tab with RIGHT SIDEBAR LOG"""
        self.notebook = capture_frame.master
        
        # === MAIN HORIZONTAL LAYOUT ===
        main_horizontal = ttk.Frame(capture_frame)
        main_horizontal.pack(fill='both', expand=True, padx=5, pady=5)
        
        # LEFT PANEL - Main content
        left_panel = ttk.Frame(main_horizontal)
        left_panel.pack(side='left', fill='both', expand=True, padx=(0, 5))
        
        # Header
        header_frame = ttk.Frame(left_panel)
        header_frame.pack(fill='x', pady=(0, 5))
        
        ttk.Label(header_frame, text="⚖️ Weight Capture", 
                 font=('Segoe UI', 10, 'bold')).pack(side='left')
        
        info_frame = ttk.Frame(header_frame)
        info_frame.pack(side='right')
        
        self.material_type_label = tk.Label(info_frame, text="📦 Gold", 
                                           font=('Segoe UI', 8, 'bold'),
                                           bg='#FFF3CD', fg='#856404',
                                           padx=5, pady=1, relief='flat')
        self.material_type_label.pack(side='left', padx=(0, 3))
        
        self.firm_id_label = tk.Label(info_frame, text=f"Firm {self.current_firm_id}", 
                                     font=('Segoe UI', 8),
                                     bg='#D1ECF1', fg='#0C5460',
                                     padx=5, pady=1, relief='flat')
        self.firm_id_label.pack(side='left')
        
        # Controls
        controls_frame = ttk.Frame(left_panel)
        controls_frame.pack(fill='x', pady=(0, 5))
        
        load_btn_frame = ttk.Frame(controls_frame)
        load_btn_frame.pack(side='left')
        
        self.gold_btn = tk.Button(load_btn_frame, text="🔄 Gold", 
                                  font=('Segoe UI', 8, 'bold'),
                                  bg='#17A2B8', fg='white', 
                                  activebackground='#138496', activeforeground='white',
                                  relief='flat', padx=8, pady=2,
                                  cursor='hand2', command=self.load_gold_jobs)
        self.gold_btn.pack(side='left', padx=(0, 3))
        
        self.silver_btn = tk.Button(load_btn_frame, text="🥈 Silver", 
                                    font=('Segoe UI', 8, 'bold'),
                                    bg='#6C757D', fg='white',
                                    activebackground='#5A6268', activeforeground='white',
                                    relief='flat', padx=8, pady=2,
                                    cursor='hand2', command=self.load_silver_jobs)
        self.silver_btn.pack(side='left')
        
        self.stop_scan_btn = tk.Button(load_btn_frame, text="⏹ Stop Scan", 
                                       font=('Segoe UI', 8, 'bold'),
                                       bg='#DC3545', fg='white',
                                       activebackground='#C82333', activeforeground='white',
                                       relief='flat', padx=8, pady=2,
                                       cursor='hand2', command=self.stop_loading_jobs,
                                       state='disabled')
        self.stop_scan_btn.pack(side='left', padx=(3, 0))
        
        scan_filter_frame = ttk.Frame(controls_frame)
        scan_filter_frame.pack(side='left', padx=(10, 0))
        
        self.start_page_var = tk.StringVar(value="1")
        self.end_page_var = tk.StringVar(value="")
        self.date_from_var = tk.StringVar(value="")
        self.date_to_var = tk.StringVar(value="")
        
        ttk.Label(scan_filter_frame, text="Page", font=('Segoe UI', 8)).pack(side='left', padx=(0, 2))
        ttk.Entry(scan_filter_frame, textvariable=self.start_page_var, width=4).pack(side='left')
        ttk.Label(scan_filter_frame, text="to", font=('Segoe UI', 8)).pack(side='left', padx=(2, 2))
        ttk.Entry(scan_filter_frame, textvariable=self.end_page_var, width=4).pack(side='left')
        
        ttk.Label(scan_filter_frame, text="  Date", font=('Segoe UI', 8)).pack(side='left', padx=(8, 2))
        ttk.Entry(scan_filter_frame, textvariable=self.date_from_var, width=10).pack(side='left')
        ttk.Label(scan_filter_frame, text="to", font=('Segoe UI', 8)).pack(side='left', padx=(2, 2))
        ttk.Entry(scan_filter_frame, textvariable=self.date_to_var, width=10).pack(side='left')
        ttk.Label(scan_filter_frame, text="(DD-MM-YYYY)", font=('Segoe UI', 7)).pack(side='left', padx=(4, 0))
        
        self.defer_db_fetch_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            scan_filter_frame,
            text="API Load",
            variable=self.defer_db_fetch_var,
            font=('Segoe UI', 8),
            bg='#F0F0F0',
            activebackground='#F0F0F0'
        ).pack(side='left', padx=(8, 0))
        
        speed_frame = ttk.Frame(controls_frame)
        speed_frame.pack(side='right')
        
        ttk.Label(speed_frame, text="⚡", font=('Segoe UI', 9)).pack(side='left', padx=(0, 2))
        self.speed_var = tk.StringVar(value="0.3")
        ttk.Combobox(speed_frame, textvariable=self.speed_var, 
                    values=['0.3', '0.5', '1.0'], width=4, state='readonly',
                    font=('Segoe UI', 8)).pack(side='left', padx=(0, 2))
        ttk.Label(speed_frame, text="s", font=('Segoe UI', 8)).pack(side='left')
        
        # Table label
        ttk.Label(left_panel, text="📋 Jobs", font=('Segoe UI', 8, 'bold')).pack(anchor='w', pady=(0, 2))
        
        # Table
        tree_container = ttk.Frame(left_panel, relief='solid', borderwidth=1)
        tree_container.pack(fill='both', expand=True, pady=(0, 5))
        
        v_scroll = ttk.Scrollbar(tree_container, orient="vertical")
        v_scroll.pack(side='right', fill='y')
        
        h_scroll = ttk.Scrollbar(tree_container, orient="horizontal")
        h_scroll.pack(side='bottom', fill='x')
        
        columns = ('Select', 'Request No', 'Job No', 'Material', 'PCS', 'Weight', 'Tags', 'Filled', 'Status')
        
        self.jobs_tree = ttk.Treeview(tree_container, columns=columns, show='headings',
                                      yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set,
                                      height=12)
        
        v_scroll.config(command=self.jobs_tree.yview)
        h_scroll.config(command=self.jobs_tree.xview)
        
        self.jobs_tree.heading('Select', text='☑')
        self.jobs_tree.heading('Request No', text='Request')
        self.jobs_tree.heading('Job No', text='Job No')
        self.jobs_tree.heading('Material', text='Type')
        self.jobs_tree.heading('PCS', text='PCS')
        self.jobs_tree.heading('Weight', text='Weight (gms)')
        self.jobs_tree.heading('Tags', text='Tags')
        self.jobs_tree.heading('Filled', text='Done')
        self.jobs_tree.heading('Status', text='Status')
        
        self.jobs_tree.column('Select', width=35, anchor='center', minwidth=35)
        self.jobs_tree.column('Request No', width=100, minwidth=80)
        self.jobs_tree.column('Job No', width=100, minwidth=80)
        self.jobs_tree.column('Material', width=60, anchor='center', minwidth=50)
        self.jobs_tree.column('PCS', width=60, anchor='center', minwidth=50)
        self.jobs_tree.column('Weight', width=100, anchor='e', minwidth=80)
        self.jobs_tree.column('Tags', width=50, anchor='center', minwidth=40)
        self.jobs_tree.column('Filled', width=50, anchor='center', minwidth=40)
        self.jobs_tree.column('Status', width=260, minwidth=200)
        
        self.jobs_tree.pack(fill='both', expand=True)
        
        self.jobs_tree.tag_configure('ready', background='#D4EDDA')
        self.jobs_tree.tag_configure('skip', background='#F8F9FA')
        self.jobs_tree.tag_configure('filled', background='#D1ECF1')
        self.jobs_tree.tag_configure('error', background='#F8D7DA')
        
        self.jobs_tree.bind('<Button-1>', self.on_tree_click)
        
        # Actions
        action_frame = ttk.Frame(left_panel)
        action_frame.pack(fill='x', pady=(0, 5))
        
        select_frame = ttk.Frame(action_frame)
        select_frame.pack(side='left')
        
        tk.Button(select_frame, text="☑", font=('Segoe UI', 8),
                 bg='#E9ECEF', fg='#495057', relief='flat', padx=6, pady=2,
                 cursor='hand2', command=self.select_all_jobs).pack(side='left', padx=(0, 2))
        
        tk.Button(select_frame, text="☐", font=('Segoe UI', 8),
                 bg='#E9ECEF', fg='#495057', relief='flat', padx=6, pady=2,
                 cursor='hand2', command=self.deselect_all_jobs).pack(side='left')
        
        btn_frame = ttk.Frame(action_frame)
        btn_frame.pack(side='right')
        
        tk.Button(btn_frame, text="⚡ Auto-Fill Weights", font=('Segoe UI', 9, 'bold'),
                 bg='#28A745', fg='white', relief='flat', padx=12, pady=4,
                 cursor='hand2', command=self.autofill_selected_weights).pack(side='left')
        
        # Progress
        prog_frame = ttk.Frame(left_panel)
        prog_frame.pack(fill='x')
        
        ttk.Label(prog_frame, text="📊", font=('Segoe UI', 8)).pack(side='left', padx=(0, 3))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(prog_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        self.progress_label = ttk.Label(prog_frame, text="Ready", font=('Segoe UI', 8))
        self.progress_label.pack(side='left')
        
        # === RIGHT SIDEBAR - LOG ===
        # Toggle button is in a separate frame so it stays visible when log is hidden
        self.log_toggle_frame = ttk.Frame(main_horizontal)
        self.log_toggle_frame.pack(side='right', fill='y', padx=(0, 0))
        
        self.log_visible = tk.BooleanVar(value=True)
        self.log_toggle_btn = tk.Button(self.log_toggle_frame, text="◀", 
                                        font=('Segoe UI', 9, 'bold'),
                                        bg='#6C757D', fg='white',
                                        relief='flat', width=2, pady=2,
                                        cursor='hand2', command=self.toggle_log_sidebar)
        self.log_toggle_btn.pack(side='top', pady=(0, 5))
        
        self.right_panel = ttk.Frame(main_horizontal, width=350)
        self.right_panel.pack(side='right', fill='both')
        
        log_header = ttk.Frame(self.right_panel)
        log_header.pack(fill='x', pady=(0, 2))
        
        ttk.Label(log_header, text="📝 Log", font=('Segoe UI', 9, 'bold')).pack(side='left')
        
        log_container = ttk.Frame(self.right_panel, relief='solid', borderwidth=1)
        log_container.pack(fill='both', expand=True)
        
        log_scroll = ttk.Scrollbar(log_container)
        log_scroll.pack(side='right', fill='y')
        
        self.log_text = tk.Text(log_container, wrap='word', 
                               font=('Consolas', 8),
                               yscrollcommand=log_scroll.set,
                               bg='#F8F9FA')
        self.log_text.pack(fill='both', expand=True)
        log_scroll.config(command=self.log_text.yview)
        
        self.log_weight("✅ Weight Capture initialized")
        self.log_weight("📌 Click 'Gold' or 'Silver' to load jobs")
        self.log_weight("📌 Use page/date filters to reduce scan time")
    
    def toggle_log_sidebar(self):
        """Toggle right sidebar log visibility"""
        if self.log_visible.get():
            self.right_panel.pack_forget()
            self.log_toggle_btn.config(text="▶")
            self.log_visible.set(False)
        else:
            self.right_panel.pack(side='right', fill='both')
            self.log_toggle_btn.config(text="◀")
            self.log_visible.set(True)


    def on_tree_click(self, event):
        """Handle tree item click for checkbox toggle"""
        region = self.jobs_tree.identify_region(event.x, event.y)
        if region == "cell":
            column = self.jobs_tree.identify_column(event.x)
            if column == '#1':  # Select column
                item = self.jobs_tree.identify_row(event.y)
                if item:
                    self.toggle_selection(item)
    
    def toggle_selection(self, item):
        """Toggle job selection"""
        values = list(self.jobs_tree.item(item, 'values'))
        if values:
            job_no = values[2]  # Job No column (updated index after removing Material)
            
            if values[0] == '☑':
                values[0] = '☐'
                self.selected_jobs.discard(job_no)
            else:
                values[0] = '☑'
                self.selected_jobs.add(job_no)
            
            self.jobs_tree.item(item, values=values)
    
    def select_all_jobs(self):
        """Select all jobs with available weights"""
        for item in self.jobs_tree.get_children():
            values = list(self.jobs_tree.item(item, 'values'))
            # Only select jobs that have weights (Tags Available > 0)
            # Columns: 0=Sel, 1=Req, 2=Job, 3=Mat, 4=PCS, 5=Wgt, 6=Tags
            try:
                tags_count = int(values[6])
            except:
                tags_count = -1
                
            # In fast-scan mode, tags are unknown at scan time -> allow selecting all.
            if tags_count > 0 or tags_count == -1:
                values[0] = '☑'
                self.jobs_tree.item(item, values=values)
                self.selected_jobs.add(values[2])  # Job No
        
        self.log_weight(f"✅ Selected all {len(self.selected_jobs)} jobs")
    
    def deselect_all_jobs(self):
        """Deselect all jobs"""
        for item in self.jobs_tree.get_children():
            values = list(self.jobs_tree.item(item, 'values'))
            values[0] = '☐'
            self.jobs_tree.item(item, values=values)
        
        self.selected_jobs.clear()
        self.log_weight("☐ Deselected all jobs")
    
    def log_weight(self, message):
        """Log message to weight capture log"""
        if self.log_text:
            timestamp = time.strftime("%H:%M:%S")
            self.log_text.insert('end', f"[{timestamp}] {message}\n")
            self.log_text.see('end')
            self.log_text.update()
    
    def load_gold_jobs(self):
        """Load Gold jobs from portal"""
        self.current_material_type = "Gold"
        # Update badge style
        if hasattr(self, 'material_type_label'):
            self.material_type_label.config(text="📦 Gold", bg='#FFF3CD', fg='#856404')
        threading.Thread(target=self._load_jobs_worker, daemon=True).start()
    
    def load_silver_jobs(self):
        """Load Silver jobs from portal"""
        self.current_material_type = "Silver"
        # Update badge style
        if hasattr(self, 'material_type_label'):
            self.material_type_label.config(text="🥈 Silver", bg='#E2E3E5', fg='#383D41')
        threading.Thread(target=self._load_jobs_worker, daemon=True).start()
    
    def load_weight_capture_jobs(self):
        """Load jobs from portal weight capture page (backward compatibility)"""
        self.load_gold_jobs()
    
    def stop_loading_jobs(self):
        """Request stop for running scan"""
        if self.is_scanning:
            self.scan_cancelled = True
            if not self.stop_requested_logged:
                self.log_weight("🛑 Stop requested. Will stop after current page...")
                self.stop_requested_logged = True
            self._set_progress_label("Stopping scan...")
        else:
            self.log_weight("ℹ️ No active scan to stop")
    
    def _run_on_ui_thread(self, callback):
        """Run callback safely on Tk UI thread"""
        try:
            if self.app_context and hasattr(self.app_context, 'root') and self.app_context.root:
                self.app_context.root.after(0, callback)
            else:
                callback()
        except Exception:
            try:
                callback()
            except Exception:
                pass
    
    def _set_progress_label(self, text):
        """Update progress label safely"""
        self._run_on_ui_thread(lambda: self.progress_label.config(text=text))
    
    def _clear_jobs_table(self, clear_data=True):
        """Clear jobs table safely"""
        def _clear():
            self.jobs_tree.delete(*self.jobs_tree.get_children())
            if clear_data:
                self.jobs_data = []
                self.selected_jobs.clear()
        self._run_on_ui_thread(_clear)
    
    def _add_scanned_job_to_table(self, job):
        """Show scanned jobs immediately while scan is running"""
        def _add():
            self.jobs_tree.insert('', 'end', values=(
                '☐',
                job.get('request_no', ''),
                job.get('job_no', ''),
                job.get('material', 'Unknown'),
                '-',
                '-',
                0,
                0,
                "⏳ Scanned (fetching DB...)"
            ), tags=('skip',))
            self.jobs_tree.update_idletasks()
        self._run_on_ui_thread(_add)
    
    def _set_scan_ui_state(self, scanning):
        """Enable/disable controls while scanning"""
        def _update():
            if self.gold_btn:
                self.gold_btn.config(state='disabled' if scanning else 'normal')
            if self.silver_btn:
                self.silver_btn.config(state='disabled' if scanning else 'normal')
            if self.stop_scan_btn:
                self.stop_scan_btn.config(state='normal' if scanning else 'disabled')
        self._run_on_ui_thread(_update)
    
    def _parse_user_date(self, date_text):
        """Parse user date filter text into date object"""
        text = (date_text or "").strip()
        if not text:
            return None
        for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d.%m.%Y"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Invalid date '{text}'. Use DD-MM-YYYY")
    
    def _parse_portal_date(self, date_text):
        """Parse date text coming from portal table"""
        text = (date_text or "").strip()
        if not text:
            return None
        for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d.%m.%Y", "%d %b %Y", "%d-%b-%Y", "%d %B %Y"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        return None
    
    def _get_scan_filters(self):
        """Read and validate page/date filters from UI"""
        start_text = self.start_page_var.get().strip() if self.start_page_var else "1"
        end_text = self.end_page_var.get().strip() if self.end_page_var else ""
        from_text = self.date_from_var.get().strip() if self.date_from_var else ""
        to_text = self.date_to_var.get().strip() if self.date_to_var else ""
        
        start_page = int(start_text) if start_text else 1
        if start_page < 1:
            raise ValueError("Start page must be 1 or greater")
        
        end_page = int(end_text) if end_text else None
        if end_page is not None and end_page < start_page:
            raise ValueError("End page must be greater than or equal to start page")
        
        date_from = self._parse_user_date(from_text) if from_text else None
        date_to = self._parse_user_date(to_text) if to_text else None
        if date_from and date_to and date_to < date_from:
            raise ValueError("Date To must be greater than or equal to Date From")
        
        return {
            'start_page': start_page,
            'end_page': end_page,
            'date_from': date_from,
            'date_to': date_to
        }
    
    def _get_date_range_list(self, date_from, date_to):
        """Build inclusive date range list"""
        if not date_from and not date_to:
            return []
        start_date = date_from or date_to
        end_date = date_to or date_from
        total_days = (end_date - start_date).days
        if total_days < 0:
            return []
        return [start_date + timedelta(days=i) for i in range(total_days + 1)]
    
    def _apply_portal_date_search(self, date_obj):
        """Use portal search box (single date) for a specific day"""
        try:
            date_text = date_obj.strftime("%d/%m/%Y")
            search_input = None
            selectors = [
                "input[type='search']",
                "input[aria-controls]",
                "input.form-control.input-sm",
                "#myTable_filter input",
                "#weightTable_filter input",
                "div.dataTables_filter input",
                "label input[type='text']"
            ]
            for selector in selectors:
                try:
                    elems = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elems:
                        search_input = elems[0]
                        break
                except Exception:
                    continue
            
            if not search_input:
                # Fallback with xpath around visible Search label.
                xpath_candidates = [
                    "//label[contains(translate(normalize-space(.), 'SEARCH', 'search'), 'search')]/input",
                    "//div[contains(@id,'filter')]//input",
                    "//input[contains(@placeholder,'Search') or contains(@placeholder,'search')]"
                ]
                for xp in xpath_candidates:
                    try:
                        elems = self.driver.find_elements(By.XPATH, xp)
                        if elems:
                            search_input = elems[0]
                            break
                    except Exception:
                        continue
            
            if not search_input:
                self.log_weight("⚠️ Date search box not found on portal")
                return False
            
            self.driver.execute_script(
                "arguments[0].value='';"
                "arguments[0].dispatchEvent(new Event('input', {bubbles:true}));",
                search_input
            )
            search_input.clear()
            search_input.send_keys(date_text)
            self.driver.execute_script(
                "arguments[0].dispatchEvent(new Event('input', {bubbles:true}));"
                "arguments[0].dispatchEvent(new Event('keyup', {bubbles:true}));"
                "arguments[0].dispatchEvent(new Event('change', {bubbles:true}));",
                search_input
            )
            time.sleep(1.2)
            self.log_weight(f"🔎 Applied portal date search: {date_text}")
            return True
        except Exception as e:
            self.log_weight(f"⚠️ Could not apply date search: {str(e)}")
            return False
    
    def _resolve_get_jobs_api_urls(self):
        """Resolve possible get_jobs_api.php URLs from settings/config and local defaults"""
        urls = []
        
        def _collect_urls(value):
            """Collect one or many URLs from setting value"""
            if not value:
                return
            raw = str(value).strip()
            if not raw:
                return
            # Support comma/newline/semicolon separated values accidentally saved in settings.
            for part in re.split(r'[\s,;]+', raw):
                p = part.strip()
                if p:
                    urls.append(p)
        
        try:
            if self.app_context:
                if hasattr(self.app_context, 'settings') and isinstance(self.app_context.settings, dict):
                    u = self.app_context.settings.get('get_jobs_api_url')
                    _collect_urls(u)
                if hasattr(self.app_context, 'config_vars') and isinstance(self.app_context.config_vars, dict):
                    var = self.app_context.config_vars.get('get_jobs_api_url')
                    if var:
                        u = var.get() if hasattr(var, 'get') else str(var)
                        _collect_urls(u)
        except Exception:
            pass
        
        try:
            import config
            if hasattr(config, 'GET_JOBS_API_URL'):
                _collect_urls(config.GET_JOBS_API_URL)
        except Exception:
            pass
        
        # Fallback local URLs
        urls.extend([
            "http://localhost/manak-automation/server_scripts/get_jobs_api.php",
            "http://localhost/manak_automation/server_scripts/get_jobs_api.php",
            "http://localhost/server_scripts/get_jobs_api.php"
        ])
        
        # Keep only valid get_jobs_api URLs, deduplicate while preserving order
        seen = set()
        unique_urls = []
        for u in urls:
            if (
                u
                and u.startswith("http")
                and "get_jobs_api.php" in u
                and u not in seen
            ):
                unique_urls.append(u)
                seen.add(u)
        return unique_urls
    
    def _fetch_weight_capture_jobs_from_api(self, scan_filters):
        """Load weight-capture jobs from API using job_cards status instead of portal scan"""
        try:
            import requests
            
            firm_id = str(self.current_firm_id or "").strip()
            if not firm_id:
                self.log_weight("❌ Firm ID is required for API load")
                return []
            
            urls = self._resolve_get_jobs_api_urls()
            if not urls:
                self.log_weight("❌ No get_jobs_api URL configured")
                return []
            
            payload = {
                'action': 'get_weight_capture_jobs',
                'firm_id': firm_id,
                'material': self.current_material_type,
                'with_huid_only': 1,
                'date_from': scan_filters['date_from'].strftime("%Y-%m-%d") if scan_filters.get('date_from') else '',
                'date_to': scan_filters['date_to'].strftime("%Y-%m-%d") if scan_filters.get('date_to') else '',
                'page': int(scan_filters.get('start_page') or 1),
                'page_to': int(scan_filters.get('end_page') or scan_filters.get('start_page') or 1)
            }
            
            for url in urls:
                try:
                    if not url or not str(url).strip():
                        continue
                    self.log_weight(f"🌐 API load attempt: {url}")
                    resp = requests.post(url, json=payload, timeout=20)
                    if resp.status_code != 200:
                        body = (resp.text or "").strip()
                        snippet = body[:180] if body else ""
                        self.log_weight(f"⚠️ API HTTP {resp.status_code}: {url}")
                        if "Invalid action: get_weight_capture_jobs" in body:
                            self.log_weight("❌ Server API is old. Upload latest get_jobs_api.php with action get_weight_capture_jobs.")
                        elif snippet:
                            self.log_weight(f"   Response: {snippet}")
                        continue
                    data = resp.json()
                    if data.get('status') != 'success':
                        self.log_weight(f"⚠️ API rejected action at {url}: {data.get('message', 'Unknown')}")
                        continue
                    rows = data.get('data', []) or []
                    self.log_weight(f"✅ API returned {len(rows)} jobs")
                    return rows
                except Exception as e:
                    self.log_weight(f"⚠️ API load failed at {url}: {str(e)}")
                    continue
            
            return []
        except Exception as e:
            self.log_weight(f"❌ API load error: {str(e)}")
            return []
    
    def _load_jobs_from_api_only(self, scan_filters):
        """Populate table from API list (Weight Capture status), no portal scanning"""
        api_jobs = self._fetch_weight_capture_jobs_from_api(scan_filters)
        if not api_jobs:
            self.log_weight("⚠️ No jobs returned from API for Weight Capture status")
            return
        
        self._clear_jobs_table()
        self.jobs_data = []
        self.selected_jobs.clear()
        
        for row in api_jobs:
            request_no = str(row.get('request_no', '')).strip()
            job_no = str(row.get('job_no', '')).strip()
            if not request_no or not job_no:
                continue
            
            material = str(row.get('material', self.current_material_type)).strip() or self.current_material_type
            pcs = int(row.get('pcs', 0) or 0)
            total_weight = float(row.get('weight', 0) or 0)
            tags_available = int(row.get('tags_available', 0) or 0)
            
            if tags_available > 0:
                status_text = f"✅ Ready ({tags_available} weights in DB)"
                row_tag = 'ready'
            else:
                status_text = "⚠️ No HUID Weights"
                row_tag = 'skip'
            
            def _add_row(req=request_no, jno=job_no, mat=material, p=pcs, w=total_weight, t=tags_available, st=status_text, rt=row_tag):
                self.jobs_tree.insert('', 'end', values=(
                    '☐',
                    req,
                    jno,
                    mat,
                    p if p > 0 else '-',
                    f"{w:.3f}" if w > 0 else '-',
                    t,
                    0,
                    st
                ), tags=(rt,))
            self._run_on_ui_thread(_add_row)
            
            self.jobs_data.append({
                'request_no': request_no,
                'job_no': job_no,
                'material': material,
                'tags_available': tags_available,
                'pcs': pcs,
                'weight': total_weight
            })
        
        ready_count = len([j for j in self.jobs_data if int(j.get('tags_available', 0)) > 0])
        self.log_weight(f"✅ Loaded {len(self.jobs_data)} jobs from API: {ready_count} ready, {len(self.jobs_data)-ready_count} skipped")
        self._set_progress_label(f"Loaded {len(self.jobs_data)} API jobs")
    
    def _load_jobs_worker(self):
        """Worker thread to load jobs"""
        self.is_scanning = True
        self.scan_cancelled = False
        self.stop_requested_logged = False
        self._set_scan_ui_state(True)
        try:
            self.refresh_firm_id()
            scan_filters = self._get_scan_filters()
            
            # API-first load mode (no portal scanning)
            if self.defer_db_fetch_var and self.defer_db_fetch_var.get():
                self.log_weight("⚡ API Load enabled: loading Weight Capture jobs from API")
                self._load_jobs_from_api_only(scan_filters)
                return
            
            if not self.driver:
                self.log_weight("❌ Browser not available. Please login first.")
                return
            
            # Determine the correct URL based on material type
            if self.current_material_type == "Silver":
                list_url = "{portal_base()}/MANAK/NewArticlesListForWeighingSilver"
                self.log_weight("🥈 Navigating to Silver weight capture list...")
            else:
                list_url = "{portal_base()}/MANAK/NewArticlesListForWeighing"
                self.log_weight("🌐 Navigating to Gold weight capture list...")
            
            # Navigate to weight capture page
            self.driver.get(list_url)
            
            # Wait for page load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(2)
            self._clear_jobs_table()
            
            self.log_weight(
                f"🔍 Scan setup: pages {scan_filters['start_page']} to "
                f"{scan_filters['end_page'] if scan_filters['end_page'] else 'last'}"
            )
            if scan_filters['date_from'] or scan_filters['date_to']:
                from_txt = scan_filters['date_from'].strftime("%d-%m-%Y") if scan_filters['date_from'] else "start"
                to_txt = scan_filters['date_to'].strftime("%d-%m-%Y") if scan_filters['date_to'] else "today"
                self.log_weight(f"📅 Date filter: {from_txt} to {to_txt}")
            
            all_portal_jobs = []
            seen_jobs = set()
            page_count = 0
            
            # If date filter is provided, iterate date-by-date using portal search box.
            scan_dates = self._get_date_range_list(scan_filters['date_from'], scan_filters['date_to'])
            if scan_dates:
                self.log_weight(f"📅 Scanning {len(scan_dates)} date(s) through portal search")
            else:
                scan_dates = [None]
            
            for scan_date in scan_dates:
                if self.scan_cancelled:
                    self.log_weight("🛑 Scan cancelled by user")
                    break
                
                # Re-open list page before each date scan for stable pagination state.
                self.driver.get(list_url)
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                time.sleep(1)
                
                if scan_date:
                    self._apply_portal_date_search(scan_date)
                
                # Jump to requested start page
                current_page = 1
                start_page_reached = True
                while current_page < scan_filters['start_page']:
                    if self.scan_cancelled:
                        self.log_weight("🛑 Scan cancelled before start page")
                        start_page_reached = False
                        break
                    if not self._go_to_next_page():
                        self.log_weight(f"⚠️ Could not reach start page {scan_filters['start_page']}.")
                        start_page_reached = False
                        break
                    current_page += 1
                
                if not start_page_reached:
                    continue
                
                while not self.scan_cancelled:
                    page_count += 1
                    date_label = scan_date.strftime("%d-%m-%Y") if scan_date else "all-dates"
                    self.log_weight(f"📄 Processing page {current_page} ({date_label})...")
                    
                    # Extract jobs from current page
                    if scan_date:
                        page_jobs = self.extract_jobs_from_portal(date_from=scan_date, date_to=scan_date)
                    else:
                        page_jobs = self.extract_jobs_from_portal()
                    
                    new_count = 0
                    for job in page_jobs:
                        if self.scan_cancelled:
                            break
                        key = (job.get('request_no'), job.get('job_no'))
                        if key in seen_jobs:
                            continue
                        seen_jobs.add(key)
                        all_portal_jobs.append(job)
                        self._add_scanned_job_to_table(job)
                        new_count += 1
                    
                    self.log_weight(f"✅ Added {new_count} new job(s) from page {current_page}")
                    self._set_progress_label(f"Scanned {len(all_portal_jobs)} jobs...")
                    
                    # Stop on configured end page
                    if scan_filters['end_page'] and current_page >= scan_filters['end_page']:
                        self.log_weight(f"⏹️ Reached configured end page {scan_filters['end_page']}")
                        break
                    
                    # Try to go to next page
                    if not self._go_to_next_page():
                        break
                    current_page += 1
                    time.sleep(0.8)
            
            if not all_portal_jobs:
                if self.scan_cancelled:
                    self.log_weight("ℹ️ Scan stopped before collecting jobs")
                else:
                    self.log_weight("⚠️ No jobs found for selected filters")
                return
            
            self.log_weight(f"✅ Found {len(all_portal_jobs)} total jobs across {page_count} page(s)")
            
            # Keep scanned jobs first; DB/API enrichment can be deferred for speed.
            self.jobs_data = []
            for job in all_portal_jobs:
                self.jobs_data.append({
                    'request_no': job.get('request_no'),
                    'job_no': job.get('job_no'),
                    'material': job.get('material', 'Unknown'),
                    'tags_available': -1,  # unknown until DB fetch
                    'pcs': 0,
                    'weight': 0
                })
            
            if self.defer_db_fetch_var and self.defer_db_fetch_var.get():
                self.log_weight("⚡ Fast Scan enabled: DB fetch deferred until Auto-Fill")
                self.log_weight(f"✅ Loaded {len(all_portal_jobs)} scanned jobs (status pending DB check)")
                return
            
            # Pre-load ALL weights from database for these jobs
            self.log_weight("💾 Loading weights from database...")
            job_numbers = [job['job_no'] for job in all_portal_jobs]
            self.log_weight(f"🔑 Job numbers to query: {job_numbers[:5]}...")
            self.preload_weights_cache(job_numbers)
            self.fetch_job_details_cache(job_numbers)
            self.apply_db_details_to_table()
            
            ready_count = len([j for j in self.jobs_data if j['tags_available'] > 0])
            self.log_weight(f"✅ Loaded {len(all_portal_jobs)} jobs: {ready_count} ready, {len(all_portal_jobs)-ready_count} skipped")
            
        except ValueError as e:
            self.log_weight(f"❌ Filter error: {str(e)}")
            self._run_on_ui_thread(lambda: messagebox.showerror("Invalid Filter", str(e)))
        except Exception as e:
            self.log_weight(f"❌ Error loading jobs: {str(e)}")
        finally:
            self.is_scanning = False
            self._set_scan_ui_state(False)
            if self.scan_cancelled:
                self._set_progress_label("Stopped")
            else:
                self._set_progress_label("Ready")
    
    def extract_jobs_from_portal(self, date_from=None, date_to=None):
        """Extract jobs from weight capture portal page"""
        try:
            jobs = []
            
            # Prefer visible data rows only (faster than scanning all <tr> on page).
            rows = []
            row_selectors = [
                "table.dataTable tbody tr",
                "#myTable tbody tr",
                "#weightTable tbody tr",
                "tbody tr[role='row']",
                "tr.odd, tr.even"
            ]
            for selector in row_selectors:
                try:
                    rows = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if rows:
                        break
                except Exception:
                    continue
            
            if not rows:
                rows = self.driver.find_elements(By.TAG_NAME, "tr")
            
            for row in rows:
                try:
                    if self.scan_cancelled:
                        break
                    
                    cells = row.find_elements(By.TAG_NAME, "td")
                    
                    if len(cells) < 5:
                        continue
                    
                    # Table structure (based on portal):
                    # Column 0: S.No
                    # Column 1: Request No
                    # Column 2: Job No
                    # Column 3: Job Date
                    # Column 4: Material Category
                    # Column 5: Weight (Enter Weight link)
                    
                    # Try direct column extraction first
                    request_no = cells[1].text.strip() if len(cells) > 1 else ""
                    job_no = cells[2].text.strip() if len(cells) > 2 else ""
                    job_date_text = cells[3].text.strip() if len(cells) > 3 else ""
                    material = cells[4].text.strip() if len(cells) > 4 else ""
                    
                    # Lightweight fallback extraction from row text (faster than scanning each cell).
                    if not (request_no.isdigit() and len(request_no) >= 8):
                        request_match = re.search(r'\b11\d{6,}\b', row.text or "")
                        request_no = request_match.group(0) if request_match else request_no
                    
                    if not (job_no.isdigit() and len(job_no) >= 8):
                        job_match = re.search(r'\b12\d{6,}\b', row.text or "")
                        job_no = job_match.group(0) if job_match else job_no
                    
                    # Material validation
                    if material not in ['Gold', 'Silver', 'Platinum']:
                        # Fallback: search all cells
                        for cell in cells:
                            text = cell.text.strip()
                            if text in ['Gold', 'Silver', 'Platinum']:
                                material = text
                                break
                    
                    if request_no and job_no:
                        parsed_job_date = self._parse_portal_date(job_date_text)
                        if date_from or date_to:
                            if not parsed_job_date:
                                continue
                            if date_from and parsed_job_date < date_from:
                                continue
                            if date_to and parsed_job_date > date_to:
                                continue
                        
                        jobs.append({
                            'request_no': request_no,
                            'job_no': job_no,
                            'material': material or 'Unknown',
                            'job_date': job_date_text
                        })
                        self.log_weight(
                            f"  📋 Found: Request={request_no}, Job={job_no}, "
                            f"Date={job_date_text}, Material={material}"
                        )
                
                except Exception as e:
                    continue
            
            return jobs
            
        except Exception as e:
            self.log_weight(f"❌ Error extracting jobs: {str(e)}")
            return []
    
    def _go_to_next_page(self):
        """Navigate to next page if available"""
        try:
            # Method 1: Try to detect current page number from multiple sources
            current_page_before = 1
            
            # Try different selectors for active page
            active_page_selectors = [
                "li.active a",
                "li.paginate_button.active a", 
                "a.active",
                "li.active",
                ".pagination li.active a",
                ".dataTables_paginate .active a"
            ]
            
            for selector in active_page_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        text = elements[0].text.strip()
                        if text.isdigit():
                            current_page_before = int(text)
                            self.log_weight(f"  📍 Detected current page: {current_page_before}")
                            break
                except:
                    continue
            
            # If still on page 1, try to detect from URL or other indicators
            if current_page_before == 1:
                try:
                    current_url = self.driver.current_url
                    if 'page=' in current_url:
                        import re
                        match = re.search(r'page=(\d+)', current_url)
                        if match:
                            current_page_before = int(match.group(1))
                            self.log_weight(f"  📍 Detected page from URL: {current_page_before}")
                except:
                    pass
            
            # Method 2: Look for "Next" button first (most reliable)
            next_buttons = self.driver.find_elements(By.XPATH, "//a[contains(text(), 'Next') or contains(text(), '›') or contains(text(), '»')]")
            for button in next_buttons:
                try:
                    if button.is_enabled() and button.is_displayed():
                        # Check if button is not disabled
                        classes = button.get_attribute('class') or ''
                        if 'disabled' not in classes.lower():
                            self.log_weight(f"  ➡️ Clicking Next button...")
                            button.click()
                            time.sleep(2)  # Wait for page to load
                            
                            # Verify we actually moved to a new page
                            current_page_after = 1
                            for selector in active_page_selectors:
                                try:
                                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                                    if elements:
                                        text = elements[0].text.strip()
                                        if text.isdigit():
                                            current_page_after = int(text)
                                            break
                                except:
                                    continue
                            
                            # Check if page actually changed
                            if current_page_after == current_page_before:
                                self.log_weight(f"  ⚠️ Still on page {current_page_before} after clicking Next - reached last page")
                                return False
                            else:
                                self.log_weight(f"  ✅ Moved from page {current_page_before} to page {current_page_after}")
                                return True
                except:
                    continue
            
            # Method 3: Look for specific next page number
            next_page = current_page_before + 1
            self.log_weight(f"  🔍 Looking for page {next_page} link...")
            
            # Try multiple XPath patterns to find the next page link
            page_link_xpaths = [
                f"//a[text()='{next_page}']",
                f"//a[contains(text(), '{next_page}')]",
                f"//li/a[text()='{next_page}']",
                f"//div[@class='dataTables_paginate']//a[text()='{next_page}']",
                f"//ul[@class='pagination']//a[text()='{next_page}']"
            ]
            
            for xpath in page_link_xpaths:
                try:
                    page_links = self.driver.find_elements(By.XPATH, xpath)
                    for link in page_links:
                        try:
                            if link.is_displayed() and link.is_enabled():
                                # Check if not disabled
                                parent_classes = ''
                                try:
                                    parent = link.find_element(By.XPATH, '..')
                                    parent_classes = parent.get_attribute('class') or ''
                                except:
                                    pass
                                
                                if 'disabled' not in parent_classes.lower():
                                    self.log_weight(f"  ➡️ Clicking page {next_page}...")
                                    link.click()
                                    time.sleep(2)  # Wait for page to load
                                    
                                    # Verify we actually moved to the next page
                                    current_page_after = 1
                                    for selector in active_page_selectors:
                                        try:
                                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                                            if elements:
                                                text = elements[0].text.strip()
                                                if text.isdigit():
                                                    current_page_after = int(text)
                                                    break
                                        except:
                                            continue
                                    
                                    # Check if we moved to the expected page
                                    if current_page_after == next_page:
                                        self.log_weight(f"  ✅ Successfully moved to page {next_page}")
                                        return True
                                    else:
                                        self.log_weight(f"  ⚠️ Expected page {next_page} but on page {current_page_after} - stopping")
                                        return False
                        except:
                            continue
                except:
                    continue
            
            # No next page found
            self.log_weight(f"  ⏹️ No next page found (current: {current_page_before})")
            return False
            
        except Exception as e:
            self.log_weight(f"⚠️ Error navigating to next page: {str(e)}")
            return False
    
    def preload_weights_cache(self, job_numbers):
        """Pre-load all weights from API into memory cache for fast lookup"""
        try:
            if not job_numbers:
                return
            
            import requests
            urls = self._resolve_get_jobs_api_urls()
            if not urls:
                self.log_weight("❌ No get_jobs_api URL configured for weights fetch")
                return
            
            # Clean job numbers
            clean_job_numbers = [str(j).strip() for j in job_numbers if j]
            
            self.log_weight(f"🌐 Fetching weights via API for {len(job_numbers)} jobs...")
            
            # Prepare payload
            payload = {
                'action': 'get_weights',
                'job_numbers': clean_job_numbers
            }
            
            response = None
            used_url = None
            for url in urls:
                try:
                    response = requests.post(url, json=payload, timeout=15)
                    if response.status_code != 200:
                        self.log_weight(f"⚠️ Weights API HTTP {response.status_code}: {url}")
                        continue
                    results = response.json()
                    if results.get('status') != 'success':
                        self.log_weight(f"⚠️ Weights API rejected at {url}: {results.get('message', 'Unknown error')}")
                        continue
                    used_url = url
                    data = results.get('data', [])
                    
                    # Build cache dictionary
                    self.weights_cache = {}
                    for row in data:
                        job_no = str(row.get('job_no'))
                        tag_no = str(row.get('tag_no'))
                        weight = float(row.get('weight', 0))
                        huid_code = row.get('huid_code', '')
                        if job_no not in self.weights_cache:
                            self.weights_cache[job_no] = {}
                        self.weights_cache[job_no][tag_no] = {'weight': weight, 'huid': huid_code}
                    
                    total_weights = sum(len(tags) for tags in self.weights_cache.values())
                    self.log_weight(f"✅ Cached {total_weights} weights for {len(self.weights_cache)} jobs via API ({url})")
                    return
                except Exception as api_err:
                    self.log_weight(f"⚠️ Weights API failed at {url}: {api_err}")
                    continue
            
            if not used_url:
                self.log_weight("❌ Could not fetch weights from any configured API URL")
                
        except Exception as e:
            self.log_weight(f"❌ Error loading weights cache: {str(e)}")
    
    def fetch_job_details_cache(self, job_numbers):
        """Fetch PCS and total weight details for job numbers"""
        self.job_details_cache = {}
        try:
            if not job_numbers:
                return
            import requests as req_lib
            urls = self._resolve_get_jobs_api_urls()
            if not urls:
                self.log_weight("❌ No get_jobs_api URL configured for job details fetch")
                return
            clean_job_numbers = [str(j).strip() for j in job_numbers if j]
            if not clean_job_numbers:
                return
            
            self.log_weight("📊 Fetching PCS/Weight from job_cards...")
            for url in urls:
                try:
                    r = req_lib.post(url, json={
                        'action': 'get_job_details',
                        'job_numbers': clean_job_numbers
                    }, timeout=30)
                    if r.status_code != 200:
                        self.log_weight(f"⚠️ Job details API HTTP {r.status_code}: {url}")
                        continue
                    res = r.json()
                    if res.get('status') != 'success':
                        self.log_weight(f"⚠️ Job details API rejected at {url}: {res.get('message', 'Unknown')}")
                        continue
                    for jd in res.get('data', []):
                        self.job_details_cache[str(jd['job_no'])] = {
                            'pcs': int(jd.get('pcs', 0)),
                            'weight': float(jd.get('weight', 0))
                        }
                    self.log_weight(f"✅ Got PCS/Weight for {len(self.job_details_cache)} jobs ({url})")
                    return
                except Exception as api_err:
                    self.log_weight(f"⚠️ Job details API failed at {url}: {api_err}")
                    continue
            
            self.log_weight(f"✅ Got PCS/Weight for {len(self.job_details_cache)} jobs")
        except Exception as e:
            self.log_weight(f"⚠️ Could not fetch job details: {e}")
    
    def apply_db_details_to_table(self):
        """Rebuild table rows with DB-backed readiness details"""
        self._clear_jobs_table(clear_data=False)
        self.selected_jobs.clear()
        for job in self.jobs_data:
            job_no = job['job_no']
            request_no = job['request_no']
            material = job.get('material', 'Unknown')
            
            tags_in_db = self.weights_cache.get(job_no, {})
            tags_available = len([w for w in tags_in_db.values() if w['weight'] > 0])
            jd = self.job_details_cache.get(job_no, {})
            job_pcs = jd.get('pcs', 0)
            job_weight = jd.get('weight', 0)
            
            job['tags_available'] = tags_available
            job['pcs'] = job_pcs
            job['weight'] = job_weight
            
            if tags_available == 0:
                status_text = "⚠️ No DB Weights (Will Auto-Avg)"
                row_tag = 'skip'
            else:
                status_text = f"✅ Ready ({tags_available} weights in DB)"
                row_tag = 'ready'
            
            def _add_row(req=request_no, jno=job_no, mat=material, pcs=job_pcs, jw=job_weight, t=tags_available, st=status_text, rtag=row_tag):
                self.jobs_tree.insert('', 'end', values=(
                    '☐',
                    req,
                    jno,
                    mat,
                    pcs if pcs > 0 else '-',
                    f"{jw:.3f}" if jw > 0 else '-',
                    t,
                    0,
                    st
                ), tags=(rtag,))
            self._run_on_ui_thread(_add_row)
    
    def prepare_selected_jobs_for_autofill(self, selected_data):
        """Fetch DB weights/details for selected jobs before autofill"""
        selected_job_numbers = [job.get('job_no') for job in selected_data if job.get('job_no')]
        if not selected_job_numbers:
            return
        self.log_weight("💾 Fetching DB weights for selected jobs...")
        self.preload_weights_cache(selected_job_numbers)
        self.fetch_job_details_cache(selected_job_numbers)
        
        # Update jobs_data entries with latest DB details for selected jobs
        selected_set = set(str(j) for j in selected_job_numbers)
        for job in self.jobs_data:
            if str(job.get('job_no')) in selected_set:
                tags_in_db = self.weights_cache.get(str(job.get('job_no')), {})
                job['tags_available'] = len([w for w in tags_in_db.values() if w['weight'] > 0])
                jd = self.job_details_cache.get(str(job.get('job_no')), {})
                job['pcs'] = jd.get('pcs', 0)
                job['weight'] = jd.get('weight', 0)
    
    def autofill_selected_weights(self):
        """Auto-fill weights for selected jobs"""
        if not self.selected_jobs:
            messagebox.showwarning("No Selection", "Please select at least one job")
            return
        
        # Fast-scan mode: fetch DB data only for selected jobs before starting autofill.
        selected_data = [job for job in self.jobs_data if job['job_no'] in self.selected_jobs]
        if self.defer_db_fetch_var and self.defer_db_fetch_var.get():
            self.prepare_selected_jobs_for_autofill(selected_data)
            self.apply_db_details_to_table()
            # Re-apply current selection after table rebuild
            selected_now = set(str(j['job_no']) for j in selected_data)
            for item in self.jobs_tree.get_children():
                values = list(self.jobs_tree.item(item, 'values'))
                if values and str(values[2]) in selected_now:
                    values[0] = '☑'
                    self.jobs_tree.item(item, values=values)
            self.selected_jobs = selected_now
        
        count = len(self.selected_jobs)
        selected_data = [job for job in self.jobs_data if job['job_no'] in self.selected_jobs]
        ready_count = len([j for j in selected_data if int(j.get('tags_available', 0)) > 0])
        if ready_count == 0:
            messagebox.showwarning("No DB Weights", "Selected jobs do not have DB weights available.")
            return
        
        if not messagebox.askyesno("Confirm Auto-Fill", 
                                   f"Auto-fill weights for {count} selected job(s)?\n"
                                   f"Ready with DB weights: {ready_count}"):
            return
        
        threading.Thread(target=self._autofill_worker, daemon=True).start()
    
    def _autofill_worker(self):
        """Worker thread to auto-fill weights"""
        try:
            selected_data = [
                job for job in self.jobs_data
                if job['job_no'] in self.selected_jobs and int(job.get('tags_available', 0)) > 0
            ]
            
            total_jobs = len(selected_data)
            self.log_weight(f"🚀 Starting auto-fill for {total_jobs} jobs...")
            
            success_jobs = 0
            fail_jobs = 0
            total_tags_filled = 0
            
            for i, job in enumerate(selected_data, 1):
                try:
                    self.log_weight(f"\n{'='*60}")
                    self.log_weight(f"📦 Processing {i}/{total_jobs}: Job {job['job_no']} ({job.get('material', 'Gold')})")
                    
                    # Update progress
                    progress = (i / total_jobs) * 100
                    self.progress_var.set(progress)
                    self.progress_label.config(text=f"Processing job {i}/{total_jobs}: {job['job_no']}")
                    
                    # Fill weights for this job
                    filled_count, processed_count, expected_count = self.fill_weights_for_job(
                        request_no=job['request_no'],
                        job_no=job['job_no'],
                        material=job.get('material', 'Gold')
                    )
                    
                    if filled_count > 0:
                        success_jobs += 1
                        total_tags_filled += filled_count
                        self.update_job_status(job['job_no'], f"✅ Filled ({filled_count} tags)", filled_count=filled_count)
                        self.log_weight(f"✅ Job {job['job_no']}: Successfully filled {filled_count} tags")
                    elif processed_count > 0 and processed_count >= expected_count:
                        # All tags were already filled - treat as success
                        success_jobs += 1
                        self.update_job_status(job['job_no'], f"✅ Done (Already Filled)", filled_count=0)
                        self.log_weight(f"✅ Job {job['job_no']}: All {processed_count} tags were already filled")
                    else:
                        fail_jobs += 1
                        self.update_job_status(job['job_no'], "❌ Failed", filled_count=0)
                        self.log_weight(f"❌ Job {job['job_no']}: Failed to fill weights (Processed {processed_count}/{expected_count})")
                    
                except Exception as e:
                    fail_jobs += 1
                    self.update_job_status(job['job_no'], "❌ Error", filled_count=0)
                    self.log_weight(f"❌ Error processing Job {job['job_no']}: {str(e)}")
            
            # Final summary
            self.progress_var.set(100)
            self.progress_label.config(text="Complete!")
            self.log_weight(f"\n{'='*60}")
            self.log_weight(f"🏁 Auto-fill complete:")
            self.log_weight(f"   ✅ {success_jobs} jobs succeeded")
            self.log_weight(f"   ❌ {fail_jobs} jobs failed")
            self.log_weight(f"   📊 {total_tags_filled} total tags filled")
            
            # Go back to weight capture list page based on material type
            if self.current_material_type == "Silver":
                list_url = "{portal_base()}/MANAK/NewArticlesListForWeighingSilver"
                self.log_weight(f"🔄 Returning to Silver weight capture list...")
            else:
                list_url = "{portal_base()}/MANAK/NewArticlesListForWeighing"
                self.log_weight(f"🔄 Returning to Gold weight capture list...")
            
            self.driver.get(list_url)
            time.sleep(2)
            
            messagebox.showinfo("Complete", 
                              f"✅ Filled {total_tags_filled} tags in {success_jobs} jobs\n"
                              f"❌ Failed: {fail_jobs} jobs\n\n"
                              f"You can reload the list to see updated status.")
            
        except Exception as e:
            self.log_weight(f"❌ Error in auto-fill: {str(e)}")
    
    def fill_weights_for_job(self, request_no, job_no, material='Gold'):
        """Fill weights for a single job and return count of filled tags"""
        try:
            if not self.driver:
                return 0, 0, 0
            
            # Navigate to weighing form based on material type
            self.log_weight(f"🌐 Opening weighing form for Job {job_no} (Material: {material})...")
            
            # Construct URL based on material type
            # Encode request_no and job_no to base64
            encoded_request = base64.b64encode(request_no.encode()).decode()
            encoded_job = base64.b64encode(job_no.encode()).decode()
            
            if material.lower() == 'silver':
                # Silver weighing form URL
                weight_url = f"{portal_base()}/MANAK/UID_WeighingFormSilver?requestNo={encoded_request}&jobNo={encoded_job}"
            else:
                # Default to Gold weighing form URL (also for Platinum and others)
                weight_url = f"{portal_base()}/MANAK/UID_WeighingForm?requestNo={encoded_request}&jobNo={encoded_job}"
            
            self.log_weight(f"🔗 URL: {weight_url}")
            self.driver.get(weight_url)
            
            # --- BYPASS COM PORT POPUP ---
            try:
                # Overwrite navigator.serial to prevent the browser from asking for serial port access
                self.driver.execute_script("""
                    try {
                        if (navigator.serial) {
                            Object.defineProperty(navigator, 'serial', { 
                                get: () => ({ 
                                    requestPort: () => new Promise(() => {}), 
                                    getPorts: () => Promise.resolve([]) 
                                }) 
                            });
                            console.log("✅ WebSerial API disabled via script");
                        }
                    } catch (e) {}
                """)
            except:
                pass
            # -----------------------------
            
            # Wait for form page
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "tabWeight"))
            )
            time.sleep(1)
            
            self.log_weight(f"✅ Weighing form loaded for Job {job_no}")
            
            # Select 100 entries to show all tags
            try:
                from selenium.webdriver.support.ui import Select
                length_select = Select(self.driver.find_element(By.NAME, "weightTable_length"))
                length_select.select_by_value("100")
                time.sleep(2) # Wait for reload
                self.log_weight("📄 Selected 100 entries per page")
            except Exception as e:
                self.log_weight(f"⚠️ Could not change table length to 100: {e}")
            
            # Find all table rows with weight inputs
            table_rows = self.driver.find_elements(By.XPATH, "//tr[@role='row' and contains(@class, 'odd') or contains(@class, 'even')]")
            
            if not table_rows:
                self.log_weight(f"⚠️ No weight entry rows found")
                return 0, 0, 0
            
            self.log_weight(f"📋 Found {len(table_rows)} tags to process")
            
            # Get weights for this job from cache
            job_weights = self.weights_cache.get(job_no, {})
            
            if not job_weights:
                self.log_weight(f"⚠️ No weights in database for Job {job_no}")
                return 0, 0, 0
            
            filled_count = 0
            delay = float(self.speed_var.get())
            
            # Track which tags we've processed to avoid re-processing
            processed_tags = set()
            expected_fill_count = len(job_weights)  # Total weights we should fill
            
            # Keep processing until all database weights are filled or max iterations reached
            max_iterations = 1000  # Prevent infinite loop - increased to allow large batches
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                
                # Re-find table rows on each iteration (table refreshes after saves)
                current_rows = self.driver.find_elements(By.XPATH, "//tr[@role='row' and contains(@class, 'odd') or contains(@class, 'even')]")
                
                if not current_rows:
                    break
                
                found_unfilled = False  # Track if we found any unfilled tags in this iteration
                
                for i, row in enumerate(current_rows, 1):
                    try:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        
                        if len(cells) < 6:
                            continue
                        
                        # Extract data from row
                        # Column 1: AHC Tag
                        ahc_tag = cells[1].text.strip()
                        
                        # Check if we have weight for this tag
                        if ahc_tag not in job_weights:
                            continue  # Skip tags not in our database
                        
                        # Skip if we've already processed this tag
                        if ahc_tag in processed_tags:
                            continue
                        
                        weight_value = job_weights[ahc_tag]['weight']
                        
                        # Check if weight is already filled (before looking for input field)
                        # Weight column is cells[5] - check for existing weight value
                        already_filled = False
                        try:
                            if len(cells) > 5:
                                # Check for any text content in weight column
                                weight_cell_text = cells[5].text.strip()
                                
                                # If weight cell has text that looks like a number, it's already filled
                                if weight_cell_text and any(char.isdigit() for char in weight_cell_text):
                                    # Make sure it's not just "Enter weight" placeholder text
                                    if "enter" not in weight_cell_text.lower():
                                        self.log_weight(f"  ℹ️ Row {i}: Tag {ahc_tag} - Already filled ({weight_cell_text} gms), skipping")
                                        processed_tags.add(ahc_tag)
                                        already_filled = True
                                
                                # If not found as text, check for disabled/readonly input fields
                                if not already_filled:
                                    disabled_inputs = cells[5].find_elements(By.CSS_SELECTOR, "input[disabled], input[readonly]")
                                    if disabled_inputs:
                                        input_value = disabled_inputs[0].get_attribute('value')
                                        if input_value:
                                            self.log_weight(f"  ℹ️ Row {i}: Tag {ahc_tag} - Already filled ({input_value} gms), skipping")
                                            processed_tags.add(ahc_tag)
                                            already_filled = True
                        except Exception as check_error:
                            pass  # Continue to normal processing
                        
                        if already_filled:
                            continue
                        
                        # Find weight input field in this row
                        weight_inputs = row.find_elements(By.CSS_SELECTOR, "input[id='articlWeight']")
                        
                        if not weight_inputs:
                            # No input field - likely already saved, skip
                            continue
                        
                        weight_input = weight_inputs[0]
                        
                        # If input has a value and row still has save button,
                        # treat it as prefilled-but-not-finalized and click Save.
                        current_value = weight_input.get_attribute('value')
                        if current_value and float(current_value) > 0:
                            save_buttons_existing = row.find_elements(By.CSS_SELECTOR, "button.saveWeight")
                            if save_buttons_existing:
                                found_unfilled = True
                                self.log_weight(f"  💾 Row {i}: Tag {ahc_tag} has prefilled value ({current_value} gms) - clicking Save")
                                save_buttons_existing[0].click()
                                try:
                                    WebDriverWait(self.driver, 3).until(EC.alert_is_present())
                                    alert = self.driver.switch_to.alert
                                    alert_text = alert.text
                                    self.log_weight(f"    📢 Alert: {alert_text}")
                                    alert.accept()
                                    self.log_weight("    ✅ Alert accepted - Saved!")
                                except TimeoutException:
                                    self.log_weight("    ℹ️ No alert (saved directly)")
                                except Exception as alert_error:
                                    self.log_weight(f"    ⚠️ Alert handling error: {str(alert_error)}")
                                
                                processed_tags.add(ahc_tag)
                                time.sleep(delay + 0.5)
                                self.log_weight(f"  ✅ Row {i}: Tag {ahc_tag} finalized with existing value {current_value} gms")
                                break
                            else:
                                self.log_weight(f"  ℹ️ Row {i}: Tag {ahc_tag} - Already filled ({current_value} gms), skipping")
                                processed_tags.add(ahc_tag)
                                continue
                        
                        # Found an unfilled tag - mark it
                        found_unfilled = True
                        
                        # Fill weight - using JavaScript to bypass possible readonly/disabled attributes
                        try:
                            self.driver.execute_script("""
                                var el = arguments[0];
                                var val = arguments[1];
                                el.removeAttribute('readonly');
                                el.removeAttribute('disabled');
                                el.value = val;
                                el.dispatchEvent(new Event('change', { bubbles: true }));
                                el.dispatchEvent(new Event('input', { bubbles: true }));
                                el.dispatchEvent(new Event('blur', { bubbles: true }));
                            """, weight_input, str(weight_value))
                            self.log_weight(f"  📝 Row {i}: Tag {ahc_tag} - Filled {weight_value} gms (via JS)")
                        except Exception as js_err:
                            # Fallback to standard Selenium if JS fails
                            weight_input.clear()
                            weight_input.send_keys(str(weight_value))
                            self.log_weight(f"  📝 Row {i}: Tag {ahc_tag} - Filled {weight_value} gms (fallback)")
                        
                        # Click save button in this row
                        save_buttons = row.find_elements(By.CSS_SELECTOR, "button.saveWeight")
                        
                        if save_buttons:
                            save_buttons[0].click()
                            
                            # Wait for and handle alert confirmation
                            try:
                                WebDriverWait(self.driver, 3).until(EC.alert_is_present())
                                alert = self.driver.switch_to.alert
                                alert_text = alert.text
                                self.log_weight(f"    📢 Alert: {alert_text}")
                                alert.accept()  # Click OK
                                self.log_weight(f"    ✅ Alert accepted - Saved!")
                                filled_count += 1
                                processed_tags.add(ahc_tag)
                            except TimeoutException:
                                # No alert appeared - that's okay
                                self.log_weight(f"    ℹ️ No alert (saved directly)")
                                filled_count += 1
                                processed_tags.add(ahc_tag)
                            except Exception as alert_error:
                                self.log_weight(f"    ⚠️ Alert handling error: {str(alert_error)}")
                            
                            # Wait for page to refresh after alert
                            time.sleep(delay + 0.5)  # Extra time for page refresh
                            
                            self.log_weight(f"  ✅ Row {i}: Tag {ahc_tag} → {weight_value} gms ✅")
                            
                            # Break inner loop to re-scan table after save
                            break
                        else:
                            self.log_weight(f"  ⚠️ Row {i}: Tag {ahc_tag} - Save button not found")
                        
                    except Exception as e:
                        self.log_weight(f"  ❌ Row {i}: Error - {str(e)}")
                        continue
                
                # After processing all rows in this iteration, check if we're done
                if not found_unfilled:
                    # No unfilled tags found in this iteration - we're done
                    break
                
                # Check if we've processed all expected tags
                if len(processed_tags) >= expected_fill_count:
                    self.log_weight(f"✅ All {len(processed_tags)} tags have been processed")
                    break
            
            self.log_weight(f"✅ Completed Job {job_no}: Filled {filled_count} new tags, {len(processed_tags)} total processed out of {expected_fill_count} in database")
            
            # HUID code update intentionally skipped in this flow.
            self.log_weight("ℹ️ HUID update skipped (not required for weight save flow)")
            
            # Auto-click "Submit For Delivery Voucher" button if all weights are filled
            if filled_count > 0:
                try:
                    self.log_weight(f"🔍 Looking for 'Submit For Delivery Voucher' button...")
                    submit_button = self.driver.find_element(By.ID, "submitForPhoto")
                    
                    # Check if button is visible
                    if submit_button.is_displayed():
                        self.log_weight(f"📤 Clicking 'Submit For Delivery Voucher' button...")
                        submit_button.click()
                        
                        # Handle any confirmation alert
                        try:
                            WebDriverWait(self.driver, 3).until(EC.alert_is_present())
                            alert = self.driver.switch_to.alert
                            alert_text = alert.text
                            self.log_weight(f"    📢 Confirmation: {alert_text}")
                            alert.accept()
                            self.log_weight(f"    ✅ Confirmation accepted!")
                        except TimeoutException:
                            pass  # No alert, that's fine
                        
                        time.sleep(2)  # Wait for submission to process
                        self.log_weight(f"✅ Job {job_no} submitted for delivery voucher!")
                    else:
                        self.log_weight(f"⚠️ Submit button found but not visible")
                except Exception as submit_error:
                    self.log_weight(f"⚠️ Submit button not found or error clicking: {str(submit_error)}")
            
            return filled_count, len(processed_tags), expected_fill_count
            
        except Exception as e:
            self.log_weight(f"❌ Error filling weights for Job {job_no}: {str(e)}")
            return 0, 0, 0
    
    def extract_huid_codes_from_table(self):
        """Extract AHC Tag and HUID mappings from weightTable"""
        try:
            huid_mappings = []
            
            # Find the weightTable by ID
            table = self.driver.find_element(By.ID, "weightTable")
            
            # Find all rows in tbody
            rows = table.find_elements(By.XPATH, ".//tbody/tr[@role='row']")
            
            for row in rows:
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    
                    if len(cells) < 5:
                        continue
                    
                    # Extract data:
                    # Column 0: S.No
                    # Column 1: AHC Tag (tag_no)
                    # Column 2: Material Category
                    # Column 3: Item Category
                    # Column 4: HUID code
                    # Column 5: Weight
                    
                    tag_no = cells[1].text.strip()  # AHC Tag
                    huid_code = cells[4].text.strip()  # HUID
                    
                    # Extract weight
                    weight_val = 0.0
                    try:
                        weight_text = cells[5].find_element(By.TAG_NAME, "input").get_attribute("value")
                        if weight_text:
                            weight_val = float(weight_text)
                    except:
                        pass
                    
                    if tag_no:
                        huid_mappings.append({
                            'tag_no': tag_no,
                            'huid_code': huid_code,
                            'weight': weight_val
                        })
                        self.log_weight(f"  📝 Extracted: Tag {tag_no} → HUID {huid_code} ({weight_val}g)")
                
                except Exception as row_error:
                    continue
            
            return huid_mappings
            
        except Exception as e:
            self.log_weight(f"❌ Error extracting HUID codes: {str(e)}")
            return []
    
    def update_huid_codes_in_database(self, job_no, huid_mappings):
        """Update huid_data table with HUID codes via API"""
        try:
            import requests
            urls = self._resolve_get_jobs_api_urls()
            if not urls:
                self.log_weight("❌ No get_jobs_api URL configured for HUID update")
                return 0
            
            if not huid_mappings:
                return 0
                
            updated_count = 0
            
            # Prepare data for API
            mappings_data = [{'tag_no': m['tag_no'], 'huid_code': m['huid_code'], 'weight': m.get('weight', 0)} for m in huid_mappings]
            
            payload = {
                'action': 'update_huid_codes',
                'job_no': job_no,
                'mappings': mappings_data
            }
            
            self.log_weight(f"🌐 Updating HUID codes for Job {job_no} via API...")
            for url in urls:
                try:
                    response = requests.post(url, json=payload, timeout=15)
                    if response.status_code != 200:
                        self.log_weight(f"⚠️ HUID update API HTTP {response.status_code}: {url}")
                        continue
                    result = response.json()
                    if result.get('status') == 'success':
                        updated_count = result.get('updated_count', len(mappings_data))
                        self.log_weight(f"✅ API Updated {updated_count} HUID codes for Job {job_no} ({url})")
                        return updated_count
                    self.log_weight(f"⚠️ HUID update rejected at {url}: {result.get('message')}")
                except Exception as api_err:
                    self.log_weight(f"⚠️ HUID update API failed at {url}: {api_err}")
                    continue
            
            self.log_weight("❌ Could not update HUID codes on any configured API URL")
                
            return updated_count
            
        except Exception as e:
            self.log_weight(f"❌ Error updating HUID codes via API: {str(e)}")
            return 0
    
    def update_job_status(self, job_no, status, filled_count=None):
        """Update job status in tree view"""
        for item in self.jobs_tree.get_children():
            values = list(self.jobs_tree.item(item, 'values'))
            if values[2] == job_no:  # Job No column (index 2)
                if filled_count is not None:
                    values[5] = filled_count  # Tags Filled column (index 5, after Material)
                values[6] = status  # Status column (index 6)
                self.jobs_tree.item(item, values=values)
                break
