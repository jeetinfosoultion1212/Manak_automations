#!/usr/bin/env python3
"""
Simple Job Creator Module
Scan QM Received List and create jobs with preview
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import base64
import re
from urllib.parse import parse_qs, urlparse
import mysql.connector
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import datetime
import traceback
from config import DB_CONFIG
from portal_config import build_portal_url
import requests
from processors.job_cards_processor import JobCardsProcessor


class SimpleJobCreator:
    """Simple job creator with scan -> preview -> create workflow"""
    
    def __init__(self, driver, log_callback, license_check_callback, app_context=None):
        self.driver = driver
        self.main_log_callback = log_callback
        self.check_license_before_action = license_check_callback
        self.app_context = app_context
        
        # Database config
        self.db_config = DB_CONFIG.copy()
        
        # Initialize internal JobCardsProcessor for advanced logic
        try:
            self.job_processor = JobCardsProcessor(driver, log_callback, license_check_callback, app_context)
        except:
            self.job_processor = None
            print("Warning: JobCardsProcessor could not be initialized")
        
        # Scanned requests storage
        self.scanned_requests = []
        
        # Thread safety - prevent concurrent operations
        self._is_busy = False
        self._busy_lock = threading.Lock()
        self._auto_timer_id = None
        self._processed_request_nos = set()  # Track processed requests across auto-cycles
        
        # UI elements
        self.preview_tree = None
        self.log_text = None
        self.progress_var = None
        self.progress_bar = None
        self.status_label = None
        self.progress_label = None
        self.scan_btn = None
        self.create_selected_btn = None
    
    def get_firm_id_from_settings(self):
        """Get Firm ID - prefer Settings page value, then saved config, then license, then default"""
        try:
            # 1. Prefer Settings page (BIS Portal Firm ID) - user-configured
            if self.app_context:
                if hasattr(self.app_context, 'firm_id_var'):
                    val = self.app_context.firm_id_var.get()
                    if val:
                        return str(val).strip()
                if hasattr(self.app_context, 'get_settings'):
                    settings = self.app_context.get_settings()
                    if isinstance(settings, dict):
                        val = settings.get('firm_id')
                        if val:
                            return str(val).strip()
            # 2. Fallback to saved config file
            try:
                import json, os
                path = os.path.join('config', 'app_settings.json')
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        cfg = json.load(f)
                        val = cfg.get('firm_id')
                        if val:
                            return str(val).strip()
            except: pass
            # 3. Fallback to license
            if self.app_context and hasattr(self.app_context, 'license_manager'):
                license_manager = self.app_context.license_manager
                if hasattr(license_manager, 'firm_id') and license_manager.firm_id:
                    return str(license_manager.firm_id)
        except Exception as e:
            print(f"Warning: Could not get Firm ID: {e}")
        return '2'
    
    def log(self, message):
        """Log message to UI"""
        if self.log_text:
            try:
                def _log():
                    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                    self.log_text.config(state='normal')
                    self.log_text.insert('end', f"[{timestamp}] {message}\n")
                    self.log_text.see('end')
                    self.log_text.config(state='disabled')
                
                if self.log_text.winfo_exists():
                    self.log_text.after(0, _log)
            except:
                pass
    
    def update_status(self, message, status_type='info'):
        """Update status label"""
        if self.status_label:
            def _update():
                colors = {
                    'info': '#17a2b8',
                    'success': '#28a745',
                    'warning': '#ffc107',
                    'danger': '#dc3545'
                }
                icons = {
                    'info': '🔵',
                    'success': '✅',
                    'warning': '⚠️',
                    'danger': '❌'
                }
                self.status_label.config(
                    text=f"{icons.get(status_type, '🔵')} {message}",
                    foreground=colors.get(status_type, '#17a2b8')
                )
            
            if self.status_label.winfo_exists():
                self.status_label.after(0, _update)
    
    def update_progress(self, value, message=""):
        """Update progress bar"""
        if self.progress_var and self.progress_bar:
            def _update():
                self.progress_var.set(value)
                if message and self.progress_label:
                    self.progress_label.config(text=message)
            
            if self.progress_bar.winfo_exists():
                self.progress_bar.after(0, _update)
    
    def setup_ui(self, notebook):
        """Setup simplified Create Jobs UI with horizontal layout"""
        # Main frame
        main_frame = ttk.Frame(notebook)
        notebook.add(main_frame, text="📋 Create Jobs")
        
        # 1. Top Control Bar
        controls_frame = ttk.Frame(main_frame, padding=5)
        controls_frame.pack(fill='x', side='top')
        
        # Left: Actions
        self.scan_btn = ttk.Button(controls_frame, text="🔍 Scan Portal", 
                                 command=self.start_scanning, style='Primary.TButton')
        self.scan_btn.pack(side='left', padx=2)
        
        self.create_selected_btn = ttk.Button(controls_frame, text="💾 Create Jobs", 
                                            command=self.create_selected_jobs, state='disabled', style='Success.TButton')
        self.create_selected_btn.pack(side='left', padx=2)
        
        self.load_missing_btn = ttk.Button(controls_frame, text="🔢 Load Missing Jobs & Update", 
                                          command=self.load_missing_jobs_and_update, style='Info.TButton')
        self.load_missing_btn.pack(side='left', padx=2)
        
        # Auto Process Checkbox
        self.auto_mode_var = tk.BooleanVar(value=False)
        self.auto_mode_chk = ttk.Checkbutton(controls_frame, text="⚡ Auto Process", 
            variable=self.auto_mode_var, style='Success.TCheckbutton', command=self.on_auto_mode_toggle)
        self.auto_mode_chk.pack(side='left', padx=10)
        
        # Right: Log Toggle
        self.show_log_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(controls_frame, text="Show Log", variable=self.show_log_var, 
                      command=self.toggle_log_sidebar).pack(side='right', padx=5)
        
        # 2. Main Content Area (PanedWindow)
        self.content_pane = ttk.PanedWindow(main_frame, orient='horizontal')
        self.content_pane.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Left Pane: Table + Progress
        left_pane = ttk.Frame(self.content_pane)
        self.content_pane.add(left_pane, weight=3)
        
        # Table Container
        table_container = ttk.Frame(left_pane)
        table_container.pack(fill='both', expand=True)
        
        # Table Scrollbars
        v_scroll = ttk.Scrollbar(table_container, orient='vertical')
        v_scroll.pack(side='right', fill='y')
        h_scroll = ttk.Scrollbar(table_container, orient='horizontal')
        h_scroll.pack(side='bottom', fill='x')
        
        # Table
        columns = ('sel', 'request_no', 'item', 'pcs', 'purity', 'weight', 'status')
        self.preview_tree = ttk.Treeview(table_container, columns=columns, show='headings',
                                       yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        v_scroll.config(command=self.preview_tree.yview)
        h_scroll.config(command=self.preview_tree.xview)
        
        self.preview_tree.heading('sel', text='☑')
        self.preview_tree.heading('request_no', text='Request No')
        self.preview_tree.heading('item', text='Item')
        self.preview_tree.heading('pcs', text='Pcs')
        self.preview_tree.heading('purity', text='Purity')
        self.preview_tree.heading('weight', text='Weight (g)')
        self.preview_tree.heading('status', text='Status')
        
        self.preview_tree.column('sel', width=40, anchor='center')
        self.preview_tree.column('request_no', width=120)
        self.preview_tree.column('item', width=150)
        self.preview_tree.column('pcs', width=60, anchor='center')
        self.preview_tree.column('purity', width=80, anchor='center')
        self.preview_tree.column('weight', width=100, anchor='center')
        self.preview_tree.column('status', width=150)
        
        self.preview_tree.pack(fill='both', expand=True)
        self.preview_tree.bind('<Button-1>', self.on_tree_click)
        
        # Progress Bar (Below Table)
        progress_frame = ttk.Frame(left_pane, padding="0 5 0 0")
        progress_frame.pack(fill='x', side='bottom')
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill='x')
        
        self.status_label = ttk.Label(progress_frame, text="Ready", font=('Segoe UI', 9))
        self.status_label.pack(anchor='w', pady=(2,0))
        
        # Right Pane: Log Sidebar (Initially Hidden)
        self.log_frame = ttk.Frame(self.content_pane)
        self.log_text = tk.Text(self.log_frame, width=40, state='disabled', font=('Consolas', 8), bg='#f8f9fa')
        log_scroll = ttk.Scrollbar(self.log_frame, orient='vertical', command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        
        self.log_text.pack(side='left', fill='both', expand=True)
        log_scroll.pack(side='right', fill='y')
        
        # Initial Log State (Hidden)
        if self.show_log_var.get():
             self.content_pane.add(self.log_frame, weight=1)

        self.log("✅ Simple Job Creator initialized")

    def on_auto_mode_toggle(self):
        """Handle auto mode toggle"""
        if self.auto_mode_var.get():
            self._processed_request_nos.clear()  # Reset processed tracking for new auto session
            self.log("⚡ Auto Process Started - Scanning now...")
            self.start_scanning()
        else:
            self._cancel_auto_timer()
            self.log("🛑 Auto Process Stopped")
    
    def _cancel_auto_timer(self):
        """Cancel any pending auto-process timer"""
        if self._auto_timer_id is not None:
            try:
                self.scan_btn.after_cancel(self._auto_timer_id)
            except:
                pass
            self._auto_timer_id = None
    
    def _schedule_auto_timer(self, delay_ms, callback):
        """Schedule an auto-process timer, cancelling any existing one first"""
        self._cancel_auto_timer()
        if self.auto_mode_var.get():  # Only schedule if auto mode is still on
            self._auto_timer_id = self.scan_btn.after(delay_ms, callback)

    def toggle_log_sidebar(self):
        """Toggle the log sidebar visibility"""
        if self.show_log_var.get():
            self.content_pane.add(self.log_frame, weight=1)
        else:
            self.content_pane.forget(self.log_frame)

    def _ensure_valid_window(self):
        """Ensure driver is focused on a valid window"""
        try:
            # Check if current handle is valid
            try:
                current = self.driver.current_window_handle
                if current not in self.driver.window_handles:
                    raise Exception("Handle invalid")
            except:
                # If accessing current_window_handle fails, it's invalid
                raise Exception("Handle invalid")
        except:
            # Try to switch to first available
            if self.driver.window_handles:
                self.driver.switch_to.window(self.driver.window_handles[0])
                self.log("⚠️ Restored window focus to main window")
            else:
                self.log("❌ No browser windows open!")
                raise Exception("Browser closed")

    def _scan_worker(self):
        """Worker: Scan Portal -> Fetch API Data -> Update UI"""
        try:
            self.update_status("Scanning...", 'info')
            self.update_progress(0, "Starting scan...")
            self.log("\n" + "="*50)
            self.log("🔍 Scanning Portal & Merging with DB...")
            
            # Clear data
            self.scanned_requests = []
            for item in self.preview_tree.get_children():
                self.preview_tree.delete(item)
            
            # 1. Scan Portal
            self.update_progress(10, "Navigating to QM List...")
            url = build_portal_url("/MANAK/qualityManagerDesk_List?hmType=HMQM")
            self.driver.get(url)
            
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(2)
            
            portal_requests = self._extract_requests_from_page()
            self.log(f"✅ Found {len(portal_requests)} requests on portal")
            
            if not portal_requests:
                self.update_status("No requests found", 'warning')
                self.update_progress(0, "")
                return

            # 2. Fetch DB Data (API)
            self.update_progress(40, "Fetching DB data...")
            db_data = self._fetch_db_pending_requests()
            
            # 3. Merge Data
            self.update_progress(60, "Merging data...")
            merged_count = 0
            
            for p_req in portal_requests:
                req_no = p_req['request_no']
                
                # Find matching DB items
                db_items = [d for d in db_data if d['request_no'] == req_no]
                
                # Update portal request with DB details
                if db_items:
                    merged_count += 1
                    p_req['db_items'] = db_items # Store list of items
                    # Use first item for display
                    p_req['item'] = db_items[0]['item']
                    p_req['pcs'] = sum(d['pcs'] for d in db_items)
                    p_req['weight'] = sum(d['weight'] for d in db_items)
                    p_req['status'] = 'Ready'
                else:
                    p_req['db_items'] = []
                    p_req['status'] = 'Portal Only'
                    
                p_req['selected'] = True
                self.scanned_requests.append(p_req)
                
                # Add to tree
                self.preview_tree.insert('', 'end', values=(
                    '☑',
                    p_req['request_no'],
                    p_req['item'],
                    p_req['pcs'],
                    p_req.get('purity', ''), # Might be missing if Portal Only
                    f"{p_req['weight']:.2f}",
                    p_req['status']
                ))
            
            self.log(f"✅ Merged {merged_count} requests with DB data")
            self.update_progress(100, f"Scan Complete. {len(self.scanned_requests)} Requests.")
            self.update_status("Scan Complete", 'success')
            self.create_selected_btn.config(state='normal')
            
            # Update stats
            self.stats_labels['scanned'].config(text=f"🔍 Scanned: {len(self.scanned_requests)}")
            self.update_selection_count()
            
        except Exception as e:
            self.log(f"❌ Error scanning: {str(e)}")
            self.update_status("Scan Failed", 'danger')
        finally:
            self.scan_btn.config(state='normal')

    def _fetch_db_pending_requests(self):
        """Fetch pending requests from API"""
        try:
            api_url = None
            if self.app_context:
                if hasattr(self.app_context, 'settings') and isinstance(self.app_context.settings, dict):
                    api_url = self.app_context.settings.get('get_jobs_api_url')
                elif hasattr(self.app_context, 'config_vars') and isinstance(self.app_context.config_vars, dict):
                    var = self.app_context.config_vars.get('get_jobs_api_url')
                    if var: api_url = var.get() if hasattr(var, 'get') else str(var)
            if not api_url:
                try:
                    import config
                    if hasattr(config, 'GET_JOBS_API_URL'):
                        api_url = config.GET_JOBS_API_URL
                except:
                    pass
            if not api_url:
                api_url = "http://localhost/manak_automation/server_scripts/get_jobs_api.php"
            
            payload = {'action': 'get_pending_requests', 'firm_id': self.get_firm_id_from_settings()}
            response = requests.post(api_url, json=payload, timeout=5)
            data = response.json()
            if data.get('status') == 'success':
                return data.get('data', [])
            return []
        except Exception as e:
            self.log(f"⚠️ API Fetch Error: {str(e)}")
            return []


    
    def on_tree_click(self, event):
        """Handle tree click to toggle selection"""
        region = self.preview_tree.identify('region', event.x, event.y)
        if region == 'cell':
            column = self.preview_tree.identify_column(event.x)
            if column == '#1':  # First column (selection)
                item = self.preview_tree.identify_row(event.y)
                if item:
                    self.toggle_selection(item)
    
    def toggle_selection(self, item_id):
        """Toggle selection for an item"""
        values = list(self.preview_tree.item(item_id, 'values'))
        if values[0] == '☑':
            values[0] = '☐'
            # Find and update in scanned_requests
            for req in self.scanned_requests:
                if req['request_no'] == values[1]:
                    req['selected'] = False
                    break
        else:
            values[0] = '☑'
            for req in self.scanned_requests:
                if req['request_no'] == values[1]:
                    req['selected'] = True
                    break
        
        self.preview_tree.item(item_id, values=values)
        self.update_selection_count()
    
    def select_all_requests(self):
        """Select all requests"""
        for item in self.preview_tree.get_children():
            values = list(self.preview_tree.item(item, 'values'))
            values[0] = '☑'
            self.preview_tree.item(item, values=values)
        
        for req in self.scanned_requests:
            req['selected'] = True
        
        self.update_selection_count()
    
    def deselect_all_requests(self):
        """Deselect all requests"""
        for item in self.preview_tree.get_children():
            values = list(self.preview_tree.item(item, 'values'))
            values[0] = '☐'
            self.preview_tree.item(item, values=values)
        
        for req in self.scanned_requests:
            req['selected'] = False
        
        self.update_selection_count()
    
    def update_selection_count(self):
        """Update selected count in stats"""
        selected_count = sum(1 for req in self.scanned_requests if req.get('selected', False))
        # removed stats label update
    
    def start_scanning(self):
        """Start scanning QM Received List (with busy-check to prevent concurrent runs)"""
        if not self.check_license_before_action():
            return
        
        # Prevent concurrent operations
        with self._busy_lock:
            if self._is_busy:
                self.log("⚠️ Already busy - skipping scan request")
                return
            self._is_busy = True
        
        self.scan_btn.config(state='disabled')
        self.create_selected_btn.config(state='disabled')
        threading.Thread(target=self._scan_worker, daemon=True).start()
    
    def _scan_worker(self):
        """Worker thread for scanning"""
        try:
            self.update_status("Scanning...", 'info')
            self.update_progress(0, "Starting scan...")
            self.log("\n" + "="*50)
            self.log("🔍 Starting QM Received List scan...")
            
            # Clear previous data
            self.scanned_requests = []
            for item in self.preview_tree.get_children():
                self.preview_tree.delete(item)
            
            # Navigate to QM Received List
            self.update_progress(10, "Loading QM Received List...")
            self.log("🌐 Navigating to QM Received List...")
            
            self._ensure_valid_window()
            url = build_portal_url("/MANAK/qualityManagerDesk_List?hmType=HMQM")
            self.driver.get(url)
            
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(2)  # Wait for table to load
            
            self.update_progress(30, "Scanning requests...")
            self.log("📋 Scanning requests from table...")
            
            # Get all requests from table
            requests = self._extract_requests_from_page()
            
            if not requests:
                self.log("⚠️ No requests found")
                self.update_status("No requests found", 'warning')
                self.update_progress(0, "")
                
                # Auto Rescan Trigger for EMPTY list
                if self.auto_mode_var.get():
                     self.log("⚡ Auto Process: No requests found. Waiting 10s to rescan...")
                     self._schedule_auto_timer(10000, self.start_scanning)
                
                return
            
            self.log(f"✅ Found {len(requests)} requests")
            self.update_progress(60, f"Processing {len(requests)} requests...")
            
            # Fetch pending data from API to enable updates (pass request numbers for targeted fetch)
            self.log("🔍 Fetching pending data from API...")
            request_nos = [r['request_no'] for r in requests if r.get('request_no')]
            db_data = self._fetch_pending_data_from_api(request_nos=request_nos)
            mapped_count = 0
            
            # Add to preview and merge
            for i, req in enumerate(requests):
                req['selected'] = True  # Default selected
                
                # Merge DB data
                r_no = req['request_no']
                if r_no in db_data:
                     req['db_items'] = db_data[r_no]
                     mapped_count += 1
                     # Update display info from DB data
                     items_count = len(req['db_items'])
                     total_weight = sum([float(it['weight']) for it in req['db_items']])
                     req['items_display'] = f"{items_count} items ({total_weight:.2f}g)"
                     
                     # Aggregate stats for display
                     total_pcs = sum([int(it.get('pcs', 0)) for it in req['db_items']])
                     req['pcs'] = total_pcs
                     
                     purities = set([it.get('purity', '') for it in req['db_items'] if it.get('purity')])
                     req['purity'] = ", ".join(purities) if purities else "N/A"
                     req['weight'] = total_weight
                     
                else:
                     req['db_items'] = []
                     req['items_display'] = "No DB Data"
                     req['pcs'] = 0
                     req['purity'] = ""
                     req['weight'] = 0.0
                
                self.scanned_requests.append(req)
                
                # Add to tree
                self.preview_tree.insert('', 'end', values=(
                    '☑',
                    req.get('request_no', 'N/A'),
                    req.get('items_display', req.get('item', 'N/A')),
                    req.get('pcs', 0),
                    req.get('purity', 'N/A'),
                    f"{req.get('weight', 0):.2f}",
                    '⏳ Pending' if req['db_items'] else '⚠️ No DB Data'
                ))

                
                progress = 60 + (i / len(requests)) * 30
                self.update_progress(progress, f"Processed {i+1}/{len(requests)}")
            
            self.update_progress(100, "✅ Scan complete!")
            self.update_status("Scan complete", 'success')
            self.log(f"✅ Scan complete - {len(requests)} requests ready")
            
            # Update stats
            self.log(f"🔍 Scanned: {len(requests)}")
            self.update_selection_count()
            
            # Enable create button
            self.create_selected_btn.config(state='normal')
            
            # Auto Process Trigger
            if self.auto_mode_var.get():
                # Filter out already-processed requests
                new_requests = [r for r in self.scanned_requests 
                               if r['request_no'] not in self._processed_request_nos and r.get('selected', False)]
                
                if new_requests:
                     self.log(f"⚡ Auto Process: {len(new_requests)} new request(s) to create...")
                     # Directly call create instead of scheduling (we're already in worker thread)
                     # But first release busy so create_selected_jobs can acquire it
                     with self._busy_lock:
                         self._is_busy = False
                     self.scan_btn.after(500, self.create_selected_jobs)
                     return  # Skip the finally busy-release since we already released
                else:
                     self.log("⚡ Auto Process: All requests already processed. Waiting 10s to rescan...")
                     self._schedule_auto_timer(10000, self.start_scanning)
            
        except Exception as e:
            self.log(f"❌ Error scanning: {str(e)}")
            self.log(f"Traceback: {traceback.format_exc()}")
            self.update_status("Scan failed", 'danger')
            self.update_progress(0, "")
        finally:
            # Release busy flag
            with self._busy_lock:
                self._is_busy = False
            self.scan_btn.config(state='normal')
    
    def _extract_requests_from_page(self):
        """Extract requests from QM Received List page"""
        requests = []
        
        try:
            # Try multiple methods to find the table
            table = None
            
            # Method 1: Try by table tag (should work for any table)
            try:
                tables = self.driver.find_elements(By.TAG_NAME, "table")
                self.log(f"📊 Found {len(tables)} tables on page")
                
                # Usually the main data table is the largest one
                if tables:
                    table = tables[0]  # Try first table
                    self.log(f"✓ Using first table")
            except Exception as e:
                self.log(f"⚠️ Method 1 failed: {str(e)}")
            
            if not table:
                self.log("❌ Could not find any table on page")
                return requests
            
            # Get all rows
            rows = table.find_elements(By.TAG_NAME, "tr")
            self.log(f"📋 Found {len(rows)} rows in table")
            
            # Skip header row
            data_rows = rows[1:] if len(rows) > 1 else []
            
            for row_idx, row in enumerate(data_rows):
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    
                    if len(cells) < 3:  # Need at least 3 cells
                        continue
                    
                    # Based on screenshot, columns are:
                    # 0: S No.
                    # 1: Request No
                    # 2: Request Date
                    # 3: Job Card No (N/A for pending)
                    # 4: Jeweller Outlet Name
                    # 5: Jeweller Address
                    # 6: Status
                    # 7: Activity Log
                    
                    request_no = cells[1].text.strip() if len(cells) > 1 else ''
                    request_date = cells[2].text.strip() if len(cells) > 2 else ''
                    status = cells[6].text.strip() if len(cells) > 6 else ''
                    jeweller_desc = cells[4].text.strip() if len(cells) > 4 else ''
                    
                    if request_no:  # Only add if we have a request number
                        requests.append({
                            'request_no': request_no,
                            'request_date': request_date,  # Captured date
                            'item': jeweller_desc,  # Using jeweller name/desc as item
                            'pcs': 0,
                            'purity': '',
                            'weight': 0.0,
                            'status': status
                        })
                        self.log(f"  ✓ Row {row_idx + 1}: Request {request_no} ({request_date}) - {jeweller_desc}")
                except Exception as row_error:
                    self.log(f"⚠️ Error processing row {row_idx + 1}: {str(row_error)}")
                    continue
                    
        except Exception as e:
            self.log(f"⚠️ Error extracting requests: {str(e)}")
            self.log(f"Traceback: {traceback.format_exc()}")
        
        return requests

    def _fetch_pending_data_from_api(self, request_nos=None):
        """Fetch pending job data from API to merge with scan results.
        When request_nos are provided, API fetches by specific request numbers (more reliable)."""
        try:
            # Resolve API URL dynamically
            api_url = None
            
            # 1. Try from app context settings if available
            if self.app_context:
                if hasattr(self.app_context, 'settings') and isinstance(self.app_context.settings, dict):
                    api_url = self.app_context.settings.get('get_jobs_api_url')
                elif hasattr(self.app_context, 'config_vars') and isinstance(self.app_context.config_vars, dict):
                     # Often config vars are Tkinter StringVars
                     var = self.app_context.config_vars.get('get_jobs_api_url')
                     if var: api_url = var.get() if hasattr(var, 'get') else str(var)
                     
            # 2. Try from global config
            if not api_url:
                try: 
                    import config
                    if hasattr(config, 'GET_JOBS_API_URL'):
                        api_url = config.GET_JOBS_API_URL
                except: pass
            
            if api_url:
                self.log(f"  ℹ️ Resolved API URL: {api_url}")
            else:
                self.log("  ⚠️ No API URL found in settings or config")
                
            # 3. Strict or fallback: use only settings when provided
            potential_urls = [api_url] if api_url else [
                "http://localhost/manak-automation/server_scripts/get_jobs_api.php",
                "http://localhost/manak_automation/server_scripts/get_jobs_api.php", 
                "http://localhost/server_scripts/get_jobs_api.php", 
                "http://localhost/get_jobs_api.php"
            ]
            
            firm_id = self.get_firm_id_from_settings() or '2'
            payload = {'action': 'get_pending_requests', 'firm_id': firm_id}
            if request_nos:
                payload['request_nos'] = [str(r) for r in request_nos]
                self.log(f"  ℹ️ Querying API for {len(request_nos)} request(s): {', '.join(str(r) for r in request_nos[:5])}{'...' if len(request_nos) > 5 else ''}")
            
            for url in potential_urls:
                if not url: continue
                try:
                    self.log(f"  Attempting API: {url}...")
                    import requests
                    
                    # Preflight: check connection to surface server-side errors clearly
                    try:
                        chk = requests.post(url, json={'action': 'check_connection'}, timeout=5)
                        if chk.status_code != 200:
                            self.log(f"  ⚠️ HTTP {chk.status_code} from {url} (check_connection)")
                        else:
                            res = chk.json()
                            if res.get('status') != 'success':
                                self.log(f"  ⚠️ API Error (check_connection): {res.get('message')}")
                    except Exception as pe:
                        self.log(f"  ⚠️ Connection check failed: {str(pe)}")
                    
                    resp = requests.post(url, json=payload, timeout=5)
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get('status') == 'success':
                            self.api_url = url # Save working URL
                            self.log(f"  ✓ Connected to API: {url}")
                            
                            # Group by request_no
                            api_data = {}
                            results = data.get('data', [])
                            for row in results:
                                r_no = row['request_no']
                                if r_no not in api_data: api_data[r_no] = []
                                api_data[r_no].append(row)
                                
                            self.log(f"  ✓ Fetched {len(results)} items from API")
                            return api_data
                        else:
                            self.log(f"  ⚠️ API Error ({url}): {data.get('message')}")
                    else:
                        try:
                            snippet = resp.text[:200]
                        except:
                            snippet = ""
                        self.log(f"  ⚠️ HTTP {resp.status_code} from {url} {('→ ' + snippet) if snippet else ''}")
                except Exception as e:
                    self.log(f"  ⚠️ Connection failed to {url}: {str(e)}")
            
            self.log("❌ All API URLs failed.")
            return {}
            
        except Exception as e:
            self.log(f"⚠️ Error fetching from API: {e}")
            return {}

    
    def create_selected_jobs(self):
        """Create jobs for selected requests (with busy-check)"""
        # In auto mode, filter out already-processed requests
        if self.auto_mode_var.get():
            selected = [req for req in self.scanned_requests 
                       if req.get('selected', False) and req['request_no'] not in self._processed_request_nos]
        else:
            selected = [req for req in self.scanned_requests if req.get('selected', False)]
        
        if not selected:
            if not self.auto_mode_var.get():
                messagebox.showwarning("No Selection", "Please select at least one request")
            else:
                self.log("⚡ Auto Process: No new requests to process")
                self._schedule_auto_timer(10000, self.start_scanning)
            return
        
        # Prevent concurrent operations
        with self._busy_lock:
            if self._is_busy:
                self.log("⚠️ Already busy - skipping create request")
                return
            self._is_busy = True
        
        self.create_selected_btn.config(state='disabled')
        threading.Thread(target=self._create_jobs_worker, args=(selected,), daemon=True).start()
    
    def _create_jobs_worker(self, selected_requests):
        """Worker thread for creating jobs - actually creates in portal"""
        try:
            self.update_status("Creating jobs...", 'info')
            self.log("\n" + "="*50)
            self.log(f"💾 Creating jobs for {len(selected_requests)} requests...")
            
            created_count = 0
            processed_ids = set()
            
            # Close any extra windows before starting (safety)
            try:
                main_window = self.driver.window_handles[0]
                for wh in self.driver.window_handles[1:]:
                    self.driver.switch_to.window(wh)
                    self.driver.close()
                self.driver.switch_to.window(main_window)
            except:
                self._ensure_valid_window()
            
            for i, req in enumerate(selected_requests):
                # Check auto mode is still on (user might have toggled off)
                if self.auto_mode_var.get() is False and i > 0:
                    # Only check mid-loop for auto mode; manual mode always continues
                    pass
                    
                # Skip duplicate processing (within this batch)
                if req['request_no'] in processed_ids:
                    self.log(f"ℹ️ Skipping duplicate request {req['request_no']}")
                    continue
                    
                # Skip already-processed requests (across auto cycles)
                if req['request_no'] in self._processed_request_nos:
                    self.log(f"ℹ️ Already processed {req['request_no']} in previous cycle")
                    continue
                    
                processed_ids.add(req['request_no'])
                self._processed_request_nos.add(req['request_no'])  # Track globally to prevent re-scan

                try:
                    self.log(f"\nProcessing request {req['request_no']}...")
                    
                    # Step 1: Navigate back to QM list
                    self.log("  📋 Navigating to QM Received List...")
                    url = build_portal_url("/MANAK/qualityManagerDesk_List?hmType=HMQM")
                    self.driver.get(url)
                    time.sleep(1)
                    
                    # Step 2: Find and click on the request link
                    self.log(f"  🔍 Finding request {req['request_no']} in table...")
                    
                    # Track windows to handle new tab/window
                    original_window = self.driver.current_window_handle
                    windows_before = self.driver.window_handles
                    
                    clicked = self._click_request_link(req['request_no'])
                    
                    if not clicked:
                        self.log(f"  ❌ Could not find request link")
                        continue
                    
                    # Check for new window
                    time.sleep(2)
                    windows_after = self.driver.window_handles
                    if len(windows_after) > len(windows_before):
                         new_window = [w for w in windows_after if w not in windows_before][0]
                         self.driver.switch_to.window(new_window)
                         self.log("  🔀 Switched to new window")
                    else:
                         # Ensure we are on the right window/frame even if no new window opened
                         self._ensure_valid_window()

                    
                    # Step 3: Wait for details page to load
                    time.sleep(3)
                    self.log(f"  ✓ Page Loaded: {self.driver.title}")
                    self.log(f"  🔗 URL: {self.driver.current_url}")
                    
                    # Debug: Check source logic (simplified)
                    src = self.driver.page_source
                    if "RemarksQM" in src:
                         self.log("  ✓ 'RemarksQM' found in page source")
                    else:
                         self.log("  ⚠️ 'RemarksQM' NOT found in page source (Wrong page?)")

                    # Step 4: Fill Remarks (Handles Frames)
                    self.log("  ✍ Filling AHC QM Remarks...")
                    remarks_filled = self._fill_remarks("Ok")
                    
                    if not remarks_filled:
                         self.log("    ⚠️ Remarks field not found (checked frames too)")
                    
                    # Step 5: Click Submit button
                    self.log("  🔘 Clicking Submit button...")
                    submit_clicked = self._click_submit_button()
                    
                    # Switch back to default content in case we were in a frame
                    self.driver.switch_to.default_content()
                    
                    if not submit_clicked:
                        self.log(f"  ❌ Could not click Submit button")
                        # If new window was opened, close it
                        if len(windows_after) > len(windows_before):
                             self.driver.close()
                             self.driver.switch_to.window(original_window)
                        continue
                    
                    # Step 6: Wait for redirect and extract job number
                    time.sleep(3)
                    job_number = self._extract_job_number_from_url()
                    
                    # Close new window if opened and switch back safely
                    if len(windows_after) > len(windows_before):
                         try:
                             self.driver.close()
                             self.log("  ✓ Closed popup window")
                         except Exception as wc_err:
                             self.log(f"  ⚠️ Error closing popup: {wc_err}")
                         
                         try:
                             if original_window in self.driver.window_handles:
                                 self.driver.switch_to.window(original_window)
                             else:
                                 self._ensure_valid_window()
                         except Exception as sw_err:
                             self.log(f"  ⚠️ Error restoring window: {sw_err}")
                             self._ensure_valid_window()
                    
                    if job_number:
                        self.log(f"  ✅ Job card formatted: {job_number}")
                        req['job_no'] = job_number 
                        
                        # Use tags for success
                        created_count += 1
                        
                        # Update tree
                        for item in self.preview_tree.get_children():
                            values = list(self.preview_tree.item(item, 'values'))
                            if values[1] == req['request_no']:
                                values[-1] = f'✅ Created: {job_number}'
                                self.preview_tree.item(item, values=values, tags=('success',))
                                self.preview_tree.tag_configure('success', foreground='#28a745')
                                break
                        
                        # Save to DB immediately
                        self._save_to_database(req)

                    else:
                        self.log(f"  ℹ️ Job number will be fetched from Completed List")
                        # Still count as created because we submitted successfully
                        created_count += 1
                        
                        # Save to DB even if job number missing (so we can update later)
                        self._save_to_database(req)

                        # Update tree to show pending
                        for item in self.preview_tree.get_children():
                            values = list(self.preview_tree.item(item, 'values'))
                            if values[1] == req['request_no']:
                                values[-1] = '⏳ Fetching Job No... (Saved)'
                                self.preview_tree.item(item, values=values, tags=('warning',))
                                self.preview_tree.tag_configure('warning', foreground='#ffc107')
                                break

                    
                    progress = ((i + 1) / len(selected_requests)) * 100
                    self.update_progress(progress, f"Created {i+1}/{len(selected_requests)}")
                    
                    # Update stats
                    self.log(f"✅ Created count: {created_count}")
                    
                except Exception as e:
                    self.log(f"  ❌ Error creating job for {req['request_no']}: {str(e)}")
                    continue
            
            # === AUTOMATIC JOB NUMBER UPDATE FROM COMPLETED LIST ===
            if self.job_processor and created_count > 0:
                self.log("\n" + "="*30)
                total_items = sum(len(r.get('db_items', [])) for r in selected_requests)
                wait_sec = 5 if total_items > 1 else 3
                self.log(f"⏳ Waiting {wait_sec} seconds for BIS to create job cards...")
                time.sleep(wait_sec)
                
                self.log("🔄 Starting Automatic Job Number Update from Completed List...")
                self.update_status("Auto-updating Job Numbers...", 'warning')
                
                # Get unique request numbers that were processed
                processed_requests = list(set([req['request_no'] for req in selected_requests]))
                
                for r_no in processed_requests:
                    original_req = next((r for r in selected_requests if r['request_no'] == r_no), None)
                    if not original_req:
                         continue

                    # Prepare items for processor: (id, req_no, item_name, pcs, purity, weight)
                    processor_items = []
                    if original_req.get('db_items'):
                        for item in original_req['db_items']:
                             processor_items.append((
                                 item.get('id'),
                                 r_no,
                                 item.get('item', ''),
                                 item.get('pcs', 0),
                                 item.get('purity', ''),
                                 item.get('weight', 0.0)
                             ))
                    
                    self._update_jobs_from_completed_list(r_no, processor_items)
            
            # Show Final Success Message
            completion_msg = f"✅ Process Complete!\n\nCreated: {created_count} jobs"
            self.log(completion_msg)
            self.update_status(f"Done: {created_count} created", 'success')
            
            # Don't show blocking messagebox during auto mode
            if not self.auto_mode_var.get():
                messagebox.showinfo("Process Complete", completion_msg)
            
            # Auto rescan
            if self.auto_mode_var.get():
                self.log("⚡ Auto Process: Cycle complete. Waiting 10s to rescan...")
                self._schedule_auto_timer(10000, self.start_scanning)
            
        except Exception as e:
            self.log(f"❌ Error in job creation: {str(e)}")
            self.log(f"Traceback: {traceback.format_exc()}")
            self.update_status("Creation failed", 'danger')
            
            # Even on error, schedule rescan in auto mode
            if self.auto_mode_var.get():
                self._schedule_auto_timer(10000, self.start_scanning)
        finally:
            # Release busy flag
            with self._busy_lock:
                self._is_busy = False
            self.create_selected_btn.config(state='normal')
    
    def _resolve_api_url(self):
        """Resolve API URL and set self.api_url"""
        # Try from app context settings if available
        api_url = None
        if self.app_context:
            if hasattr(self.app_context, 'settings') and isinstance(self.app_context.settings, dict):
                api_url = self.app_context.settings.get('get_jobs_api_url')
            elif hasattr(self.app_context, 'config_vars') and isinstance(self.app_context.config_vars, dict):
                var = self.app_context.config_vars.get('get_jobs_api_url')
                if var: api_url = var.get() if hasattr(var, 'get') else str(var)
        
        # Try from global config
        if not api_url:
            try: 
                import config
                if hasattr(config, 'GET_JOBS_API_URL'):
                    api_url = config.GET_JOBS_API_URL
            except: pass
        
        # Fallback
        if not api_url:
            api_url = "http://localhost/manak_automation/server_scripts/get_jobs_api.php"
        
        self.api_url = api_url

    def load_missing_jobs_and_update(self):
        """Load requests with missing job numbers from DB via API"""
        if not self.driver:
            messagebox.showwarning("Browser Required", "Please open the browser and login to BIS first.")
            return
        
        # Ensure API URL is ready
        self._resolve_api_url()
        
        def _worker():
            try:
                self.load_missing_btn.after(0, lambda: self.load_missing_btn.config(state='disabled'))
                self.log("\n" + "="*50)
                self.log("🔢 Loading requests with missing job numbers via API...")
                self.update_status("Loading missing jobs...", 'info')
                
                # Call API
                api_url = getattr(self, 'api_url', None)
                if not api_url:
                     # Fallback
                     api_url = "http://localhost/manak_automation/server_scripts/get_jobs_api.php"
                
                firm_id = self.get_firm_id_from_settings()
                payload = {'action': 'get_missing_job_numbers', 'firm_id': firm_id}
                
                import requests
                try:
                    self.log(f"  → Connecting to: {api_url}")
                    resp = requests.post(api_url, json=payload, timeout=5)
                    data = resp.json()
                except Exception as apierr:
                    raise Exception(f"API Connection Error: {apierr}")
                
                if data.get('status') != 'success':
                    raise Exception(f"API Error: {data.get('message')}")
                
                rows = data.get('data', [])
                
                if not rows:
                    self.log("✅ No requests with missing job numbers found.")
                    self.load_missing_btn.after(0, lambda: messagebox.showinfo("All Updated", "No requests with missing job numbers found."))
                    return

                # Convert API rows (dict) to format expected by _update_jobs_from_completed_list
                # expected items format: (id, req_no, item, pcs, purity, weight)
                
                by_request = {}
                for r in rows:
                    req_no = str(r.get('request_no', ''))
                    if req_no not in by_request:
                        by_request[req_no] = []
                    
                    item_tuple = (
                        r.get('id'), 
                        req_no, 
                        r.get('item', '') or '', 
                        r.get('pcs', 0) or 0, 
                        r.get('purity', '') or '', 
                        float(r.get('weight', 0) or 0.0)
                    )
                    by_request[req_no].append(item_tuple)
                
                self.log(f"📋 Found {len(rows)} items in {len(by_request)} request(s) needing job numbers")
                self.update_status(f"Updating {len(by_request)} requests...", 'warning')
                
                for req_no, items in by_request.items():
                    self._update_jobs_from_completed_list(req_no, items)
                
                self.log("✅ Load Missing Jobs & Update complete.")
                self.update_status("Update complete", 'success')
                
                n_req, n_items = len(by_request), len(rows)
                self.load_missing_btn.after(0, lambda nr=n_req, ni=n_items: messagebox.showinfo("Complete", f"Processed {nr} request(s) with {ni} items."))
                
            except Exception as e:
                self.log(f"❌ Error: {str(e)}")
                self.load_missing_btn.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                if self.load_missing_btn and self.load_missing_btn.winfo_exists():
                    self.load_missing_btn.after(0, lambda: self.load_missing_btn.config(state='normal'))
        
        threading.Thread(target=_worker, daemon=True).start()
    
    def _click_request_link(self, request_no):
        """Find and click on request link in table"""
        try:
            # Find all rows in table
            table = self.driver.find_element(By.TAG_NAME, "table")
            rows = table.find_elements(By.TAG_NAME, "tr")
            
            for row in rows:
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) > 1:
                        cell_text = cells[1].text.strip()
                        if cell_text == request_no:
                            self.log(f"    Found row for {request_no}")
                            
                            # Strategy 1: Look for specific 'Create Job' URL pattern in explicit links
                            links = row.find_elements(By.TAG_NAME, "a")
                            for link in links:
                                href = link.get_attribute('href')
                                if href and 'QMReceivingUIDJewellerRequest.do' in href:
                                    self.log(f"    ✓ Found Job Creation link: {href[:60]}...")
                                    link.click()
                                    return True
                            
                            # Strategy 2: Look for 'Create Job Card' text
                            for link in links:
                                if "Create Job Card" in link.text or "Create" in link.text:
                                    self.log(f"    ✓ Found Create link by text: {link.text}")
                                    link.click()
                                    return True
                            
                            # Strategy 3: Click Request Number (Fallback)
                            if len(cells) > 1:
                                link = cells[1].find_element(By.TAG_NAME, "a")
                                self.log(f"    ⚠️ Clicking Request No link (Fallback)")
                                link.click()
                                return True
                except:
                    continue
            
            return False
        except Exception as e:
            self.log(f"    Error clicking request link: {str(e)}")
            return False
    
    def _click_submit_button(self):
        """Click the Submit button on request details page"""
        try:
            # Try multiple methods to find and click submit
            submit_patterns = [
                (By.ID, "save"),
                (By.ID, "submit"),
                (By.NAME, "submit"),
                (By.XPATH, "//input[@value='Submit']"),
                (By.XPATH, "//button[contains(text(), 'Submit')]"),
                (By.XPATH, "//input[@type='submit']"),
                (By.XPATH, "//button[@type='submit']"),
                (By.CLASS_NAME, "submit")
            ]
            
            for by, value in submit_patterns:
                try:





























                    
                    button = self.driver.find_element(by, value)
                    button.click()
                    self.log(f"    ✓ Clicked submit button")
                    return True
                except:
                    continue
            
            return False
        except Exception as e:
            self.log(f"    Error clicking submit: {str(e)}")
            return False

    def _fill_remarks(self, text="Ok"):
        """Fill AHC QM Remarks field (Frame-aware)"""
        try:
            # Helper to find and fill in current context
            def try_fill():
                selectors = [
                     (By.ID, "RemarksQM"),
                     (By.NAME, "RemarksQM"),
                     (By.ID, "str_remarks"),
                     (By.ID, "str_Remarks"),
                     (By.NAME, "str_remarks"),
                     (By.NAME, "str_Remarks"),
                     (By.XPATH, "//textarea[contains(@name, 'remark')]"),
                ]
                for by, val in selectors:
                     try:
                          el = self.driver.find_element(by, val)
                          if el.is_displayed():
                               el.clear()
                               el.send_keys(text)
                               self.log(f"    ✓ Filled remarks (Found by {by}={val})")
                               return True
                     except: continue
                return False

            # 1. Try in current content
            if try_fill(): return True
            
            # 2. Try searching in iframes
            frames = self.driver.find_elements(By.TAG_NAME, "iframe")
            if frames:
                self.log(f"    Searching {len(frames)} iframes...")
                for i, frame in enumerate(frames):
                    try:
                        self.driver.switch_to.frame(frame)
                        if try_fill():
                             self.log(f"    ✓ Found in frame {i}")
                             return True # Stay in frame for submit button
                        self.driver.switch_to.default_content()
                    except:
                        self.driver.switch_to.default_content()
            
            # 3. Try searching in framesets/frames
            frames = self.driver.find_elements(By.TAG_NAME, "frame")
            if frames:
                self.log(f"    Searching {len(frames)} framesets...")
                for i, frame in enumerate(frames):
                    try:
                        self.driver.switch_to.frame(frame)
                        if try_fill():
                             self.log(f"    ✓ Found in frame {i}")
                             return True # Stay in frame
                        self.driver.switch_to.default_content()
                    except:
                        self.driver.switch_to.default_content()
                        
            return False
                 
        except Exception as e:
            self.log(f"    Error filling remarks: {e}")
            return False
    
    def _extract_item_name_from_job_page(self):
        """Extract item name from BIS job card page - Item Category column in table"""
        try:
            rows = self.driver.find_elements(By.XPATH, "//table//tr")
            item_category_col_index = None
            for i, row in enumerate(rows):
                cells = row.find_elements(By.XPATH, ".//td")
                if i == 0:
                    for j, cell in enumerate(cells):
                        if "item category" in (cell.text or "").lower():
                            item_category_col_index = j
                            break
                    continue
                if item_category_col_index is not None and len(cells) > item_category_col_index:
                    text = cells[item_category_col_index].text.strip()
                    if text and not text.isdigit() and len(text) < 80:
                        return text
                if len(cells) >= 2:
                    for cell in cells:
                        t = cell.text.strip()
                        if t and not t.isdigit() and len(t) < 50 and t.lower() not in ['accepted', 'pending', 'n/a']:
                            if any(x in t.lower() for x in ['ring', 'chain', 'earring', 'bangle', 'pendant', 'set', 'nath', 'tika', 'mangalsutra', 'ornament', 'mix']):
                                return t
            return None
        except Exception:
            return None

    def _extract_item_details_from_job_page(self):
        """Extract (item_name, purity, quantity, weight) from BIS job card page."""
        try:
            # Try to use the main jewellery items table
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            for table in tables:
                rows = table.find_elements(By.TAG_NAME, "tr")
                if not rows:
                    continue

                for i, row in enumerate(rows):
                    cells = row.find_elements(By.TAG_NAME, "td")
                    # Expect at least S.No, Item Category, Quantity, Purity
                    if len(cells) < 4:
                        continue

                    # Skip header rows that contain labels instead of data
                    joined = " ".join((c.text or "").lower() for c in cells)
                    if any(h in joined for h in ["item category", "declared purity", "purity"]) and i == 0:
                        continue

                    item_category = cells[1].text.strip() if len(cells) > 1 else ""
                    qty_str = cells[2].text.strip() if len(cells) > 2 else ""
                    purity = cells[3].text.strip() if len(cells) > 3 else ""
                    weight_str = cells[4].text.strip() if len(cells) > 4 else ""

                    quantity = None
                    try:
                        if qty_str:
                            import re
                            match = re.search(r'\d+', qty_str)
                            if match: quantity = int(match.group())
                    except: pass
                    
                    weight = None
                    try:
                        if weight_str:
                            import re
                            match = re.search(r'\d+\.\d+|\d+', weight_str)
                            if match: weight = float(match.group())
                    except: pass

                    # Clean up item category
                    if item_category:
                        item_lines = [line.strip() for line in item_category.split("\n") if line.strip()]
                        for line in item_lines:
                            if line and not line.isdigit() and len(line) > 2:
                                item_category = line
                                break

                    if item_category and not item_category.isdigit():
                        return item_category, (purity or None), quantity, weight

            # Fallback: use item-only extractor
            name_only = self._extract_item_name_from_job_page()
            return name_only, None, None, None
        except Exception:
            # Last resort: no data
            return None, None, None, None

    def _extract_job_number_from_url(self):
        """Extract job card number from URL after redirect"""
        try:
            current_url = self.driver.current_url
            self.log(f"    Current URL: {current_url[:80]}...")
            
            # URL format: QMReceivingUIDJewellerRequestView.do?...&eJobCard=MTI0NTkyNTI4
            if 'eJobCard=' in current_url:
                parsed = urlparse(current_url)
                params = parse_qs(parsed.query)
                
                if 'eJobCard' in params:
                    encoded_job = params['eJobCard'][0]
                    # Decode base64
                    try:
                        decoded = base64.b64decode(encoded_job).decode('utf-8')
                        self.log(f"    ✓ Extracted job number: {decoded}")
                        return decoded
                    except:
                        pass
            
            # Try to find job number on the page itself
            try:
                # Look for "Job Card No" or similar labels
                job_patterns = [
                    "//td[contains(text(), 'Job Card')]/following-sibling::td",
                    "//label[contains(text(), 'Job Card')]/following-sibling::*",
                    "//span[contains(@class, 'job')]"
                ]
                
                for pattern in job_patterns:
                    try:
                        element = self.driver.find_element(By.XPATH, pattern)
                        job_text = element.text.strip()
                        if job_text and job_text.isdigit():
                            self.log(f"    ✓ Found job number on page: {job_text}")
                            return job_text
                    except:
                        continue
            except:
                pass
            
            return None
        except Exception as e:
            self.log(f"    Error extracting job number: {str(e)}")
            return None
    
    def _save_to_database(self, request_data):
        """
        DEPRECATED for simple job creator: Items already exist in DB from initial acceptance.
        This method is kept for safety but now only performs non-destructive updates.
        It will NOT update item names to avoid corrupting multi-item requests.
        """
        # Skip actual database save - items are already in DB from initial acceptance phase
        # The job numbers will be updated later by _update_jobs_from_completed_list
        self.log(f"ℹ️ Database update skipped (items already in DB from initial acceptance)")
        return True

    def _resolve_api_url(self):
        """Ensure api_url is set for update_job_via_api"""
        if hasattr(self, 'api_url') and self.api_url:
            return
        if self.app_context:
            if hasattr(self.app_context, 'settings') and isinstance(self.app_context.settings, dict):
                url = self.app_context.settings.get('get_jobs_api_url')
                if url: self.api_url = url; return
            if hasattr(self.app_context, 'config_vars') and isinstance(self.app_context.config_vars, dict):
                var = self.app_context.config_vars.get('get_jobs_api_url')
                if var and hasattr(var, 'get'):
                    url = str(var.get()).strip() if var.get() else ''
                    if url: self.api_url = url; return
        try:
            import config
            if hasattr(config, 'GET_JOBS_API_URL') and config.GET_JOBS_API_URL:
                self.api_url = config.GET_JOBS_API_URL
        except: pass

    def _update_jobs_from_completed_list(self, request_no, processor_items):
        """Scrape Completed List to update job numbers - ONE job number per DB row (not all rows)"""
        try:
            self._resolve_api_url()
            expected_count = len(processor_items)
            url = build_portal_url("/MANAK/qualityManagerDesk_ListCompleted?hmType=HMQM")
            target_links = []
            max_retries = 25
            retry_wait = 8
            
            # Keep retrying until ALL job cards appear - do not proceed until jobs created successfully
            for attempt in range(max_retries):
                self.log(f"  🔍 Checking Completed List for Request {request_no}... (attempt {attempt + 1}/{max_retries})")
                
                self.driver.get(url)
                WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "table")))
                time.sleep(2)
                
                target_links = []
                rows = self.driver.find_elements(By.TAG_NAME, "tr")
                for row in rows:
                    try:
                        text = row.text
                        if request_no in text and ("View" in text or "QMReceivingUIDJewellerRequestView.do" in (row.get_attribute('innerHTML') or '') or "View" in (row.get_attribute('innerHTML') or '')):
                            links = row.find_elements(By.TAG_NAME, "a")
                            for link in links:
                                href = link.get_attribute('href')
                                if href and "QMReceivingUIDJewellerRequestView.do" in href:
                                    target_links.append(href)
                                    break
                    except: continue
                
                self.log(f"  ✓ Found {len(target_links)}/{expected_count} job cards in Completed List")
                
                if len(target_links) >= expected_count:
                    self.log(f"  ✅ All {expected_count} job cards ready - proceeding to update")
                    break
                if attempt < max_retries - 1:
                    self.log(f"  ⏳ Waiting for BIS to create jobs... ({retry_wait}s before retry)")
                    time.sleep(retry_wait)
            
            if len(target_links) < expected_count:
                self.log(f"  ⚠️ Only {len(target_links)}/{expected_count} job cards found after {max_retries} attempts.")
                self.log(f"  💡 Click 'Load Missing Jobs & Update' when BIS is ready to retry.")
                if self.create_selected_btn and self.create_selected_btn.winfo_exists():
                    self.create_selected_btn.after(0, lambda: messagebox.showinfo(
                        "Job Numbers Not Ready",
                        f"Only {len(target_links)}/{expected_count} job cards found.\n\n"
                        "BIS may need more time to create jobs.\n\n"
                        "Click 'Load Missing Jobs & Update' button when ready to retry - "
                        "it will load requests without job numbers and fetch from Completed List."
                    ))
                return
            
            # Build list of unassigned items: (id, req_no, item, pcs, purity, weight)
            unassigned = list(processor_items)
            
            # Fallback: if no processor_items but we have links, use old logic (1 link = 1 request)
            use_by_request = len(unassigned) == 0 and len(target_links) == 1
            
            # 3. Process each link - get item name + purity from page, match by (request_no, item_name, purity), update
            for href in target_links:
                try:
                     self.driver.get(href)
                     time.sleep(2)
                     
                     # Extract Job No from URL or page
                     job_no = self._extract_job_number_from_url()
                     if not job_no:
                         try:
                              body_text = self.driver.find_element(By.TAG_NAME, "body").text
                              match = re.search(r'Job Card No[:\s]+(\d+)', body_text)
                              if match: job_no = match.group(1)
                         except: pass
                     
                     if not job_no:
                         self.log("    ⚠️ Could not find Job No on page")
                         continue
                         
                     # Extract item name, purity, quantity, and weight from BIS page
                     page_item_name, page_purity, page_qty, page_weight = self._extract_item_details_from_job_page()
                     self.log(f"    📄 Extraction result: item='{page_item_name}', purity='{page_purity}', qty={page_qty}, weight={page_weight}")
                     
                     matched_idx = None
                     
                     # Normalize helper function
                     def normalize_str(s):
                         """Normalize string for comparison: lowercase, strip, remove extra spaces"""
                         return str(s or '').strip().lower().replace(' ', '')
                     
                     def normalize_purity(p):
                         """Normalize purity: lowercase, strip, remove spaces, handle None/empty"""
                         normalized = normalize_str(p)
                         if not normalized or normalized == 'none':
                             return None
                         return normalized
                     
                     # Step 1: Try Exact Match by Item Name + Purity
                     if page_item_name:
                         page_item_norm = normalize_str(page_item_name)
                         page_purity_norm = normalize_purity(page_purity)
                         
                         self.log(f"    🔍 Extracted from page - Item: '{page_item_name}' (normalized: '{page_item_norm}'), Purity: '{page_purity}' (normalized: '{page_purity_norm}')")
                         
                         for idx, pit in enumerate(unassigned):
                             db_item_norm = normalize_str(pit[2])
                             db_purity_norm = normalize_purity(pit[4])
                             
                             # Try exact match on item name
                             if page_item_norm != db_item_norm:
                                 continue
                             
                             # Purity matching logic:
                             # If both have purity values, they must match exactly
                             # If one is None, it's still a match (flexible for missing purity)
                             purity_matches = True
                             if page_purity_norm and db_purity_norm:
                                 if page_purity_norm != db_purity_norm:
                                     purity_matches = False
                             
                             if purity_matches:
                                 matched_idx = idx
                                 self.log(f"    ✓ Matched strictly by exact Item '{page_item_name}' and Purity '{page_purity}'")
                                 break
                     
                     # Step 2: Last resort - use first unassigned ONLY if exact match fails
                     if matched_idx is None and unassigned:
                         # Log detailed info about why exact match failed
                         self.log(f"    ❌ NO EXACT MATCH FOUND - Extracted: Item='{page_item_name}', Purity='{page_purity}'")
                         self.log(f"    ❌ Unassigned items available: {[(p[0], p[2], p[4]) for p in unassigned[:3]]}...")
                         matched_idx = 0
                         self.log(f"    ⚠️ FALLBACK: Using first unassigned (id={unassigned[0][0]}, item={unassigned[0][2]}, purity={unassigned[0][4]}) for Job {job_no}")
                     
                     if use_by_request:
                         self.log(f"    📋 Processing Job {job_no} (single-item fallback)")
                         if self._update_job_via_api_by_request(request_no, job_no):
                             self.log(f"    ✅ Updated rows for Request {request_no} → {job_no}")
                             self.scan_btn.after(0, lambda r=request_no, j=job_no: self._update_ui_on_success(r, j))
                         else:
                             self.log(f"    ❌ API Update by request failed")
                     elif matched_idx is not None:
                         pit = unassigned[matched_idx]
                         db_id = pit[0]
                         db_item = pit[2]
                         unassigned.pop(matched_idx)
                         
                         self.log(f"    📋 Processing Job {job_no} → Item {db_item} (id={db_id})")
                         if self._update_job_via_api(db_id, job_no):
                             self.log(f"    ✅ Updated row {db_id} for Request {request_no} → {job_no}")
                             self.scan_btn.after(0, lambda r=request_no, j=job_no: self._update_ui_on_success(r, j))
                         else:
                             self.log(f"    ❌ API Update for id {db_id} failed")
                     else:
                         self.log(f"    ⚠️ Job {job_no} - no matching unassigned item")
                          
                except Exception as e:
                    self.log(f"    ❌ Error processing link {href[-20:]}: {e}")
            
        except Exception as e:
            self.log(f"  ❌ Error in Completed List update: {str(e)}")

    def _update_job_via_api(self, db_id, job_no):
        """Update job number via API"""
        try:
            if not hasattr(self, 'api_url') or not self.api_url:
                 return False
                 
            payload = {'action': 'update_job_card', 'id': db_id, 'job_no': job_no}
            import requests
            resp = requests.post(self.api_url, json=payload, timeout=5)
            if resp.status_code == 200:
                res = resp.json()
                if res.get('status') == 'success':
                    return True
            return False
        except: return False

    def _update_ui_on_success(self, request_no, job_no):
        """Update UI tree item status"""
        try:
            for item in self.preview_tree.get_children():
                values = list(self.preview_tree.item(item, 'values'))
                if values[1] == str(request_no):
                    # Keep previous status if multiple items, or just append
                    current_status = values[-1]
                    if "Updated" in current_status:
                        values[-1] = f"{current_status}, {job_no}"
                    else:
                        values[-1] = f"✅ Updated: {job_no}"
                    
                    self.preview_tree.item(item, values=values, tags=('success',))
                    break
        except: pass

    def _update_job_via_api_by_request(self, request_no, job_no):
        """Update job number for all DB rows of a request"""
        try:
            if not hasattr(self, 'api_url') or not self.api_url:
                 return False
            firm_id = self.get_firm_id_from_settings() or '2'
            payload = {
                'action': 'update_job_card_by_request',
                'firm_id': str(firm_id),
                'request_no': str(request_no),
                'job_no': str(job_no)
            }
            import requests
            resp = requests.post(self.api_url, json=payload, timeout=5)
            if resp.status_code == 200:
                res = resp.json()
                if res.get('status') == 'success':
                    updated = res.get('data', {}).get('updated_rows', 0)
                    if updated == 0:
                        self.log(f"    ⚠️ API returned success but 0 rows updated")
                        return False
                    return True
                else:
                    self.log(f"    ⚠️ API: {res.get('message', 'Update failed')}")
                    return False
            return False
        except Exception as e:
            self.log(f"    ⚠️ Update error: {e}")
            return False
