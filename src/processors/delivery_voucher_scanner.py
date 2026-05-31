#!/usr/bin/env python3
"""
Delivery Voucher Scanner Module - THREAD SAFE VERSION
Scans delivery vouchers from MANAK portal and stores job details in database
WITH PREVIEW TABLE AND BULK SAVE FUNCTIONALITY
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import mysql.connector
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import os
import sys
import traceback
import datetime
import re
import base64
from urllib.parse import parse_qs, urlparse

from portal_config import build_portal_url, portal_base

# Fix MySQL localization issue
os.environ['LANG'] = 'C'
os.environ['LC_ALL'] = 'C'
os.environ['LC_MESSAGES'] = 'C'

import requests
from config import DB_CONFIG
import config


class DeliveryVoucherScanner:
    """Handles scanning delivery vouchers with preview and bulk save"""
    
    # BIS Standard Gold Purity Values
    BIS_PURITY_VALUES = [
        "24K995", "23K958", "22K916", "21K875", 
        "20K833", "18K750", "14K585", "9K375"
    ]
    
    def __init__(self, driver, log_callback, license_check_callback, app_context=None):
        self.driver = driver
        self.log_callback = log_callback
        self.license_check_callback = license_check_callback
        self.app_context = app_context
        self.db_config = DB_CONFIG
        self.api_url = config.CHECK_JOBS_API_URL
        self.is_processing = False
        self.current_firm_id = self.get_firm_id_from_settings()
        
        # Store scanned jobs in memory before saving
        self.scanned_jobs = []
        
        # UI elements
        self.scan_log_text = None
        self.status_label = None
        self.progress_bar = None
        self.progress_var = None
        self.auto_timer_id = None  # To track and cancel timer
        self.stats_labels = {}
        self.preview_tree = None
        self.save_selected_btn = None
        self.select_all_var = None
        
        # Store fixed QM URL parameters (eCmlNo, eBranchId, etc.) captured from list page
        # These are constant per AHC centre, only eRequestId and eJobCard change
        self.qm_url_fixed_params = {}
        
    def get_firm_id_from_settings(self):
        """Get Firm ID from device license or app settings"""
        try:
            if self.app_context and hasattr(self.app_context, 'license_manager'):
                license_manager = self.app_context.license_manager
                if license_manager:
                    license_status = license_manager.get_license_status()
                    if license_status and license_status.get('firm_id'):
                        return str(license_status['firm_id'])
            return "2"  # Default firm ID
        except Exception:
            return "2"
    
    def log(self, message, level='info'):
        """Log message to UI and callback - THREAD SAFE"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        def _log_to_ui():
            if self.scan_log_text:
                try:
                    self.scan_log_text.config(state='normal')
                    self.scan_log_text.insert('end', formatted_message + '\n')
                    self.scan_log_text.see('end')
                    self.scan_log_text.config(state='disabled')
                except Exception:
                    pass
        
        if self.scan_log_text:
            self.scan_log_text.after(0, _log_to_ui)
        
        if self.log_callback:
            try:
                self.log_callback(message, level)
            except Exception:
                pass
    
    def update_status(self, message, status_type='info'):
        """Update status label - THREAD SAFE"""
        def _update():
            if self.status_label:
                try:
                    colors = {
                        'info': '#17a2b8',
                        'success': '#28a745',
                        'warning': '#ffc107',
                        'danger': '#dc3545'
                    }
                    self.status_label.config(text=message, foreground=colors.get(status_type, '#17a2b8'))
                except Exception:
                    pass
        
        if self.status_label:
            self.status_label.after(0, _update)
    
    def update_progress(self, value, message=""):
        """Update progress bar - THREAD SAFE"""
        def _update():
            if self.progress_var:
                try:
                    self.progress_var.set(value)
                except Exception:
                    pass
        
        if self.progress_bar:
            self.progress_bar.after(0, _update)
        
        if message:
            self.log(message)
    
    def setup_scanner_tab(self, notebook):
        """Setup Scan Jobs Details tab - Modern Layout"""
        scanner_frame = ttk.Frame(notebook)
        notebook.add(scanner_frame, text="🔍 Scan Jobs Details")
        
        # Main layout container
        main_container = ttk.Frame(scanner_frame)
        main_container.pack(fill='both', expand=True, padx=15, pady=15)
        
        # 1. Top Control Bar (Buttons)
        self._setup_top_bar(main_container)

        # 2. Split View (Table & Side Panel)
        self.paned_window = ttk.PanedWindow(main_container, orient='horizontal')
        self.paned_window.pack(fill='both', expand=True, pady=(10, 0))
        
        # Left Side: Table & Progress
        table_area = ttk.Frame(self.paned_window)
        self.paned_window.add(table_area, weight=4)
        self._setup_table_area(table_area)
        
        # Right Side: Log & Stats (Collapsible) - Hidden by default
        self.side_panel = ttk.Frame(self.paned_window)
        # self.paned_window.add(self.side_panel, weight=1) # Don't add initially
        self._setup_side_panel(self.side_panel)

    def _setup_top_bar(self, parent):
        """Setup top toolbar with action buttons"""
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill='x')
        
        # Left side: Scan Button
        self.scan_btn = ttk.Button(
            toolbar,
            text="🚀 Start Scanning",
            command=self.start_scanning,
            style='Primary.TButton'
        )
        self.scan_btn.pack(side='left', padx=(0, 10))

        # Auto Scan Toggle
        self.auto_scan_var = tk.BooleanVar(value=False)
        self.auto_scan_check = ttk.Checkbutton(
            toolbar,
            text="🔄 Auto Scan & Save",
            variable=self.auto_scan_var,
            command=self._toggle_auto_scan
        )
        self.auto_scan_check.pack(side='left', padx=(10, 0))
        
        # Right side: Action Buttons
        
        # Log Toggle (Default Hidden)
        self.log_visible = False
        self.toggle_log_btn = ttk.Button(
            toolbar,
            text="📝 Show Log",
            command=self._toggle_side_panel,
            style='Secondary.TButton'
        )
        self.toggle_log_btn.pack(side='right')
        
        # Scan Purity
        self.scan_purity_btn = ttk.Button(
            toolbar,
            text="🔍 Scan Purity",
            command=self._scan_purity_for_selected,
            style='Info.TButton',
            state='disabled'
        )
        self.scan_purity_btn.pack(side='right', padx=(0, 10))
        
        # Save Selected
        self.save_selected_btn = ttk.Button(
            toolbar,
            text="💾 Save Selected",
            command=self.save_selected_jobs,
            style='Success.TButton',
            state='disabled'
        )
        self.save_selected_btn.pack(side='right', padx=(0, 10))

        # Select All Checkbox
        self.select_all_var = tk.BooleanVar()
        select_all_check = ttk.Checkbutton(
            toolbar,
            text="Select All",
            variable=self.select_all_var,
            command=self._toggle_select_all
        )
        select_all_check.pack(side='right', padx=(0, 20))

    def _toggle_auto_scan(self):
        """Handle auto scan toggle"""
        if self.auto_scan_var.get():
            self.log("🔄 Auto Scan & Save ENABLED")
            # If not already processing, start scanning
            if not self.is_processing:
                self.start_scanning()
        else:
            self.log("⏹️ Auto Scan & Save DISABLED")
            if self.auto_timer_id:
                try:
                    self.preview_tree.after_cancel(self.auto_timer_id)
                    self.auto_timer_id = None
                except:
                    pass
            self.update_status("Auto Scan Stopped", "warning")

    def _convert_mg_to_gm(self, value):
        """Convert mg to gm (divide by 1000) and round to 3 decimals"""
        try:
            val = float(value) / 1000.0
            return round(val, 3)
        except (ValueError, TypeError):
            return 0.0

    def _setup_table_area(self, parent):
        """Setup table and progress bar"""
        
        # Table Container
        table_container = ttk.Frame(parent)
        table_container.pack(fill='both', expand=True)

        # Treeview
        columns = ('sel', 'request_no', 'job_no', 'date', 'jeweller', 'licence', 'item', 'purity', 'pcs', 'weight', 'cornet', 'scrap', 'status')
        self.preview_tree = ttk.Treeview(
            table_container,
            columns=columns,
            show='headings',
            selectmode='extended',
            height=20
        )
        
        # Column headings
        self.preview_tree.heading('sel', text='☑')
        self.preview_tree.heading('request_no', text='Request No')
        self.preview_tree.heading('job_no', text='Job No')
        self.preview_tree.heading('date', text='Date')
        self.preview_tree.heading('jeweller', text='Jeweller')
        self.preview_tree.heading('licence', text='License No')
        self.preview_tree.heading('item', text='Item')
        self.preview_tree.heading('purity', text='Purity')
        self.preview_tree.heading('pcs', text='Pcs')
        self.preview_tree.heading('weight', text='Weight')
        self.preview_tree.heading('cornet', text='Cornet (g)')
        self.preview_tree.heading('scrap', text='Scrap (g)')
        self.preview_tree.heading('status', text='Status')
        
        # Column widths & styling
        self.preview_tree.column('sel', width=40, anchor='center', stretch=False)
        self.preview_tree.column('request_no', width=90, minwidth=80)
        self.preview_tree.column('job_no', width=90, minwidth=80)
        self.preview_tree.column('date', width=90, minwidth=80)
        self.preview_tree.column('jeweller', width=200, minwidth=150)
        self.preview_tree.column('licence', width=100, minwidth=80)
        self.preview_tree.column('item', width=120, minwidth=100)
        self.preview_tree.column('purity', width=70, anchor='center', minwidth=60)
        self.preview_tree.column('pcs', width=50, anchor='center', minwidth=40)
        self.preview_tree.column('weight', width=80, anchor='center', minwidth=60)
        self.preview_tree.column('cornet', width=80, anchor='center', minwidth=60)
        self.preview_tree.column('scrap', width=80, anchor='center', minwidth=60)
        self.preview_tree.column('status', width=120, minwidth=100)
        
        # Scrollbars
        v_scroll = ttk.Scrollbar(table_container, orient='vertical', command=self.preview_tree.yview)
        h_scroll = ttk.Scrollbar(table_container, orient='horizontal', command=self.preview_tree.xview)
        self.preview_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        # Grid layout for table and scrollbars
        self.preview_tree.grid(row=0, column=0, sticky='nsew')
        v_scroll.grid(row=0, column=1, sticky='ns')
        h_scroll.grid(row=1, column=0, sticky='ew')
        
        table_container.grid_rowconfigure(0, weight=1)
        table_container.grid_columnconfigure(0, weight=1)
        
        # Bind click
        self.preview_tree.bind('<Button-1>', self._on_tree_click)
        
        # Progress Section (Bottom of table)
        progress_frame = ttk.Frame(parent)
        progress_frame.pack(fill='x', pady=(10, 0))
        
        self.status_label = ttk.Label(progress_frame, text="Ready to scan", font=('Segoe UI', 9))
        self.status_label.pack(side='left', padx=(0, 10))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                           maximum=100, style='Modern.Horizontal.TProgressbar')
        self.progress_bar.pack(side='left', fill='x', expand=True)

    def _update_tree_selection(self):
        """Update checkboxes in tree based on scanned_jobs selection state"""
        try:
             children = self.preview_tree.get_children()
             for i, job in enumerate(self.scanned_jobs):
                 if i < len(children):
                     item_id = children[i]
                     current_values = list(self.preview_tree.item(item_id, 'values'))
                     # Only update if changed
                     checkbox = '☑' if job.get('selected') else '☐'
                     if current_values[0] != checkbox:
                         current_values[0] = checkbox
                         self.preview_tree.item(item_id, values=current_values)
        except Exception as e:
             pass

    def _setup_side_panel(self, parent):
        """Setup right side panel with Log and Stats"""
        
        # Statistics (Compact)
        stats_frame = ttk.LabelFrame(parent, text="📊 Stats", padding=5)
        stats_frame.pack(fill='x', pady=(0, 10))
        
        self.stats_labels['scanned'] = ttk.Label(stats_frame, text="Scanned: 0", font=('Segoe UI', 9, 'bold'), foreground='#007bff')
        self.stats_labels['scanned'].pack(anchor='w')
        
        self.stats_labels['existing'] = ttk.Label(stats_frame, text="Exists: 0", font=('Segoe UI', 9), foreground='#28a745')
        self.stats_labels['existing'].pack(anchor='w')
        
        self.stats_labels['errors'] = ttk.Label(stats_frame, text="Errors: 0", font=('Segoe UI', 9), foreground='#dc3545')
        self.stats_labels['errors'].pack(anchor='w')
        
        # Log
        log_frame = ttk.LabelFrame(parent, text="📝 Log", padding=5)
        log_frame.pack(fill='both', expand=True)
        
        import tkinter.scrolledtext as scrolledtext
        self.scan_log_text = scrolledtext.ScrolledText(
            log_frame,
            height=10,
            font=('Consolas', 8),
            bg='#f8f9fa',
            fg='#495057',
            state='disabled'
        )
        self.scan_log_text.pack(fill='both', expand=True)
        
    def _toggle_side_panel(self):
        """Show/Hide side panel"""
        if self.log_visible:
            self.paned_window.forget(self.side_panel)
            self.toggle_log_btn.config(text="📝 Show Log")
            self.log_visible = False
        else:
            self.paned_window.add(self.side_panel, weight=1)
            self.toggle_log_btn.config(text="📝 Hide Log")
            self.log_visible = True
    
    def _toggle_select_all(self):
        """Toggle selection of all jobs"""
        select_all = self.select_all_var.get()
        
        try:
            children = self.preview_tree.get_children()
            for i, job in enumerate(self.scanned_jobs):
                if i < len(children):
                    job['selected'] = select_all
                    item_id = children[i]
                    checkbox = '☑' if select_all else '☐'
                    values = list(self.preview_tree.item(item_id, 'values'))
                    values[0] = checkbox
                    self.preview_tree.item(item_id, values=values)
        except Exception as e:
            self.log(f"Error toggling selection: {str(e)}")
    
    def _on_tree_click(self, event):
        """Handle click on tree to toggle checkbox"""
        region = self.preview_tree.identify('region', event.x, event.y)
        if region == 'cell':
            column = self.preview_tree.identify_column(event.x)
            item_id = self.preview_tree.identify_row(event.y)
            
            if column == '#1' and item_id:
                item_index = self.preview_tree.index(item_id)
                self.scanned_jobs[item_index]['selected'] = not self.scanned_jobs[item_index].get('selected', False)
                
                checkbox = '☑' if self.scanned_jobs[item_index]['selected'] else '☐'
                values = list(self.preview_tree.item(item_id, 'values'))
                values[0] = checkbox
                self.preview_tree.item(item_id, values=values)
    
    def start_scanning(self):
        """Start scanning"""
        if self.is_processing:
            messagebox.showwarning("Already Running", "Scanning in progress!")
            return
        
        # Get driver from app context - ALWAYS refresh to ensure we have the valid instance
        if self.app_context:
            self.driver = self.app_context.driver
            # self.log("✓ Refreshed driver from app context")
        
        # Debug: Check driver status
        self.log(f"DEBUG: Driver status: {self.driver is not None}")
        # if self.driver:
        #     self.log(f"DEBUG: Driver object: {self.driver}")
        
        if not self.driver:
            messagebox.showerror("Browser Error", "Browser is not available. Please:\n1. Go to 'Login in MANAK' tab\n2. Click 'Open Browser'\n3. Login to portal\n4. Come back and scan")
            return
            
        # Verify driver is actually alive and connected
        try:
            _ = self.driver.current_url
        except Exception as e:
            self.log(f"❌ Browser disconnected: {str(e)}")
            self.driver = None
            
            # Reset driver in app context as well since it's dead
            if self.app_context:
                self.app_context.driver = None
                self.app_context.logged_in = False
                
                # Reset UI buttons in main app if possible
                try:
                    if hasattr(self.app_context, 'open_btn'):
                        self.app_context.open_btn.config(state='normal')
                    if hasattr(self.app_context, 'login_btn'):
                        self.app_context.login_btn.config(state='disabled')
                    if hasattr(self.app_context, 'check_btn'):
                        self.app_context.check_btn.config(state='disabled')
                    if hasattr(self.app_context, 'close_btn'):
                        self.app_context.close_btn.config(state='disabled')
                except:
                    pass
            
            messagebox.showerror("Browser Disconnected", "The browser window seems to be closed.\n\nPlease go to 'Login in MANAK' tab and open the browser again.")
            return
        
        threading.Thread(target=self._scan_worker, daemon=True).start()
    
    def _scan_worker(self):
        """Worker thread for scanning - THREAD SAFE"""
        self.is_processing = True
        
        # Schedule GUI updates on main thread
        def update_ui():
            self.scan_btn.config(state='disabled')
            # Clear previous results
            for item in self.preview_tree.get_children():
                self.preview_tree.delete(item)
        
        self.preview_tree.after(0, update_ui)
        
        # Clear previous results data
        self.scanned_jobs = []
        stats = {'scanned': 0, 'existing': 0, 'errors': 0}
        
        try:
            self.update_status("🔄 Starting scan...", 'info')
            self.update_progress(10, "🌐 Navigating to delivery voucher list...")
            
            list_url = build_portal_url("/MANAK/NewArticlesListForDelieveryVoucher")
            self.driver.get(list_url)
            
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(2)
            
            self.update_progress(20, "📋 Scanning delivery voucher list...")
            
            jobs_list = self._scan_delivery_list()
            
            if not jobs_list:
                self.log("ℹ️ No jobs found")
                self.update_status("✅ Scan complete - No jobs", 'success')
                self.update_progress(100)
                return
            
            self.log(f"📋 Found {len(jobs_list)} jobs")
            self.update_progress(30, f"Found {len(jobs_list)} jobs")
            
            # Batch check existing jobs to improve performance
            job_numbers = [j['job_no'] for j in jobs_list]
            existing_jobs = set()
            
            if job_numbers:
                self.log(f"🔍 Checking {len(job_numbers)} jobs via API/DB...")
                check_success = False

                # 1. Try API First
                try:
                    payload = {'job_numbers': job_numbers, 'firm_id': self.current_firm_id}
                    response = requests.post(self.api_url, json=payload, timeout=5)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('success'):
                            existing_list = data.get('existing_jobs', [])
                            existing_jobs = set(existing_list)
                            self.log(f"✓ API Check: Found {len(existing_jobs)} existing jobs")
                            check_success = True
                        else:
                            self.log(f"⚠️ API Error: {data.get('message', 'Unknown error')}")
                    else:
                        self.log(f"⚠️ API returned status {response.status_code}")
                        
                except Exception as e:
                    self.log(f"⚠️ API Connection failed: {str(e)}")
                
                # 2. Fallback to Direct DB if API failed
                if not check_success:
                    try:
                        self.log(f"🔄 Falling back to direct DB check...")
                        # Clone config and set short timeout to prevent hanging if DB is slow
                        db_config_fast = self.db_config.copy()
                        db_config_fast['connect_timeout'] = 3
                        
                        conn = mysql.connector.connect(**db_config_fast)
                        cursor = conn.cursor()
                        
                        # Create placeholder string like %s, %s, %s
                        placeholders = ', '.join(['%s'] * len(job_numbers))
                        query = f"SELECT job_no FROM job_cards WHERE firm_id = %s AND job_no IN ({placeholders})"
                        
                        # Execute query with firm_id + job_numbers list
                        params = [self.current_firm_id] + job_numbers
                        cursor.execute(query, params)
                        
                        existing_jobs = {row[0] for row in cursor.fetchall()}
                        
                        cursor.close()
                        conn.close()
                        self.log(f"✓ DB Check: Found {len(existing_jobs)} existing jobs")
                        check_success = True
                        
                    except Exception as e:
                        self.log(f"⚠️ Database unavailable (Timeout/Error). Proceeding to scan all jobs...")
                        # Fallback to empty set, meaning we will scan everything
                        existing_jobs = set()

            # Setup requests session for fast purity scanning during extraction
            session = None
            try:
                import bs4 # Fail early if bs4 is not installed
                
                session = requests.Session()
                selenium_cookies = self.driver.get_cookies()
                for cookie in selenium_cookies:
                    session.cookies.set(cookie['name'], cookie['value'])
                user_agent = self.driver.execute_script("return navigator.userAgent;")
                session.headers.update({'User-Agent': user_agent})
            except ImportError:
                self.log(f"⚠️ Fast purity scanning disabled: missing 'bs4' module. Purity will be skipped.")
            except Exception as e:
                self.log(f"⚠️ Failed to setup fast purity scanning: {str(e)}")

            # Process each job
            for i, job_info in enumerate(jobs_list):
                try:
                    progress = 30 + (i / len(jobs_list)) * 60
                    self.update_progress(progress, f"Processing {i+1}/{len(jobs_list)}...")
                    
                    job_no = job_info['job_no']
                    # self.log(f"🔍 Checking job {job_no}...") # Removed detailed log to reduce noise
                    
                    # Check if exists (using batch result)
                    if job_no in existing_jobs:
                        self.log(f"✅ Job {job_no} already in database - Skipping")
                        stats['existing'] += 1
                        self._update_stats_display(stats)
                        continue
                    
                    # Scan details
                    self.log(f"🔍 Scanning details for {job_no}...")
                    job_details = self._scan_voucher_details(job_info, session=session)
                    
                    # Purity is NOT extracted during main scan - use 'Scan Purity' button after scanning
                    
                    if job_details:
                        # Add to preview (not database yet)
                        job_details['selected'] = True  # Default selected
                        self.scanned_jobs.append(job_details)
                        
                        # Add to tree (schedule on main thread)
                        def add_to_tree(details=job_details):
                            self.preview_tree.insert('', 'end', values=(
                                '☑',
                                details.get('request_no', 'N/A'),
                                details.get('job_no', 'N/A'),
                                details.get('date_of_request', 'N/A'),
                                details.get('jeweller_name', 'N/A')[:30],
                                details.get('licence_no', 'N/A'),
                                details.get('item', 'N/A')[:20],
                                details.get('purity', 'N/A'),
                                details.get('pcs', 0),
                                f"{details.get('weight', 0):.2f}",
                                f"{details.get('cornet_weight', 0):.4f}",
                                f"{details.get('scrp_cornet_weight', 0):.4f}",
                                '⏳ Pending'
                            ))
                        
                        self.preview_tree.after(0, add_to_tree)
                        
                        self.log(f"✅ Scanned job {job_no}")
                        stats['scanned'] += 1
                    else:
                        self.log(f"❌ Failed to extract {job_no}")
                        stats['errors'] += 1
                    
                    self._update_stats_display(stats)
                    time.sleep(0.3)  # Small delay for UI update
                    
                except Exception as e:
                    self.log(f"❌ Error: {str(e)}")
                    stats['errors'] += 1
                    continue
            
            self.update_progress(100, "✅ Scan complete!")
            self.update_status("✅ Scan complete - Review & save", 'success')
            
            # Enable save button if jobs scanned (schedule on main thread)
            if stats['scanned'] > 0:
                self.preview_tree.after(0, lambda: self.save_selected_btn.config(state='normal'))
            
            self.log(f"\n{'='*50}")
            self.log(f"📊 SCAN SUMMARY:")
            self.log(f"   Scanned: {stats['scanned']}")
            self.log(f"   Already Exists: {stats['existing']}")
            self.log(f"   Errors: {stats['errors']}")
            self.log(f"{'='*50}\n")
            
        except Exception as e:
            self.log(f"❌ Error: {str(e)}")
            self.log(f"Traceback: {traceback.format_exc()}")
            self.update_status("❌ Scan failed", 'danger')
            
        finally:
            self.is_processing = False
            # Re-enable scan button (schedule on main thread)
            self.preview_tree.after(0, lambda: self.scan_btn.config(state='normal'))
            # Enable purity scan button if jobs were scanned
            if self.scanned_jobs:
                self.preview_tree.after(0, lambda: self.scan_purity_btn.config(state='normal'))

            # Handle Auto Scan
            if self.auto_scan_var.get():
                # Process if we have ANY jobs (new or existing) in the list
                if len(self.scanned_jobs) > 0:
                    self.log("🔄 Auto Save: Processing scanned jobs...")
                    # Select all jobs
                    for job in self.scanned_jobs:
                         if not job.get('selected'):
                             job['selected'] = True
                             self._update_tree_selection() # Helper to update UI checkboxes
                    
                    # Trigger auto-save immediately since Purity was fetched during extraction
                    self.log("🔄 Auto Save: All details (including Purity) extracted. Saving jobs...")
                    self.preview_tree.after(1000, lambda: self.save_selected_jobs(auto=True))
                else:
                    self.log("⏳ Auto Scan: No new jobs found")
                    self._start_countdown(30, self.start_scanning)
    
    def _start_countdown(self, seconds, callback):
        """Start countdown timer on status label"""
        if not self.auto_scan_var.get():
            return
            
        def _tick(remaining):
            if not self.auto_scan_var.get():
                return
                
            if remaining > 0:
                self.update_status(f"⏳ Next scan in {remaining}s...", "info")
                self.auto_timer_id = self.preview_tree.after(1000, lambda: _tick(remaining - 1))
            else:
                self.update_status("🔄 Starting scan...", "info")
                callback()
        
        _tick(seconds)

    def save_selected_jobs(self, auto=False):
        """Save selected jobs to database"""
        selected = [j for j in self.scanned_jobs if j.get('selected', False)]
        
        if not selected:
            if not auto:
                messagebox.showwarning("No Selection", "Please select jobs to save!")
            return
        
        if not auto:
            confirm = messagebox.askyesno("Confirm", f"Save {len(selected)} job(s)?")
            if not confirm:
                return
        
        # Start save worker with auto flag
        threading.Thread(target=self._save_worker, args=(selected, auto), daemon=True).start()

    def _save_worker(self, jobs, auto_mode=False):
        """Save jobs to database - THREAD SAFE"""
        # Disable save button (schedule on main thread)
        self.preview_tree.after(0, lambda: self.save_selected_btn.config(state='disabled'))
        
        saved = 0
        errors = 0
        
        self.log(f"\n{'='*50}")
        self.log(f"💾 Saving {len(jobs)} jobs...")
        
        for i, job in enumerate(jobs):
            try:
                self.log(f"Saving {i+1}/{len(jobs)}: {job['job_no']}...")
                
                # Ensure jeweller exists before saving job
                if not self._ensure_jeweller_exists(job):
                    self.log(f"⚠ Warning: Could not ensure jeweller exists for {job['job_no']}, continuing anyway...")
                
                if self._save_job_to_database(job):
                    self.log(f"✅ Saved {job['job_no']}")
                    saved += 1
                    
                    # Save HUIDs if present
                    if job.get('huid_list'):
                        self._save_huids_to_database(job['job_no'], job['huid_list'])
                    
                    # Update tree (schedule on main thread)
                    def update_tree_item(j=job):
                        try:
                            idx = self.scanned_jobs.index(j)
                            children = self.preview_tree.get_children()
                            if idx < len(children):
                                item_id = children[idx]
                                values = list(self.preview_tree.item(item_id, 'values'))
                                values[-1] = '✅ Saved'
                                self.preview_tree.item(item_id, values=values, tags=('saved',))
                                self.preview_tree.tag_configure('saved', foreground='#28a745')
                        except Exception as e:
                            self.log(f"Error updating tree: {str(e)}")
                    
                    self.preview_tree.after(0, update_tree_item)
                else:
                    self.log(f"❌ Failed {job['job_no']}")
                    errors += 1
                    
            except Exception as e:
                self.log(f"❌ Error: {str(e)}")
                errors += 1
        
        self.log(f"\n📊 SAVE SUMMARY:")
        self.log(f"   Saved: {saved}")
        self.log(f"   Errors: {errors}")
        self.log(f"{'='*50}\n")
        
        if not auto_mode:
            # Show messagebox (schedule on main thread)
            self.preview_tree.after(0, lambda: messagebox.showinfo("Complete", f"Saved {saved} jobs\nErrors: {errors}"))
        
        # Re-enable buttons (schedule on main thread)
        self.preview_tree.after(0, lambda: self.save_selected_btn.config(state='normal'))
        self.preview_tree.after(0, lambda: self.scan_purity_btn.config(state='normal'))
        
        if auto_mode:
            self.log("⏳ Cycle done. Restarting soon...")
            self.preview_tree.after(0, lambda: self._start_countdown(30, self.start_scanning))
    
    def _scan_purity_for_selected(self, auto=False, chain_save=False):
        """Scan and update purity for selected jobs"""
        if self.is_processing:
            if not auto:
                messagebox.showwarning("Busy", "Scanner is already running!")
            return
            
        # Get driver from app context - ALWAYS refresh
        if self.app_context:
            self.driver = self.app_context.driver
            
        if not self.driver:
            if not auto:
                messagebox.showerror("No Browser", "Please open the browser first")
            return
            
        if not auto:
             # Verify driver is actually alive
            try:
                 _ = self.driver.current_url
            except Exception:
                 self.driver = None
                 if self.app_context:
                     self.app_context.driver = None
                     # Reset UI state if possible
                     try:
                        if hasattr(self.app_context, 'open_btn'):
                            self.app_context.open_btn.config(state='normal')
                        if hasattr(self.app_context, 'login_btn'):
                            self.app_context.login_btn.config(state='disabled')
                     except:
                        pass
    
                 messagebox.showerror("Browser Disconnected", "The browser window seems to be closed.\n\nPlease open the browser again.")
                 return
        
        selected_indices = []
        for i, job in enumerate(self.scanned_jobs):
            if job.get('selected', False):
                selected_indices.append(i)
        
        if not selected_indices:
            if not auto:
                 messagebox.showinfo("No Selection", "Please select jobs to scan purity for")
            return
        
        # Start scan in background thread
        threading.Thread(target=self._scan_purity_worker, args=(selected_indices, auto, chain_save), daemon=True).start()

    def _scan_purity_worker(self, selected_indices, auto_mode=False, chain_save=False):
        """Worker thread to scan purity for selected jobs"""
        self.is_processing = True
        
        # Disable buttons
        self.preview_tree.after(0, lambda: self.scan_purity_btn.config(state='disabled'))
        self.preview_tree.after(0, lambda: self.save_selected_btn.config(state='disabled'))
        
        self.log(f"\\n{'='*50}")
        self.log(f"🔍 SCANNING PURITY FOR {len(selected_indices)} JOBS")
        self.log(f"{'='*50}\\n")
        
        success = 0
        failed = 0
        


        for idx in selected_indices:
            job = self.scanned_jobs[idx]
            request_no = job['request_no']
            job_no = job['job_no']
            
            try:
                self.log(f"🔍 Fetching purity for job {job_no}...")
                
                # Use _extract_purity which has the proper fallback chain:
                # 1. Use stored qm_url (if captured during scan)
                # 2. Navigate to list page and find the real QM link for this job
                # 3. Construct URL with fixed params (if any were captured)
                # 4. Minimal URL fallback
                qm_url = job.get('qm_url') or None
                purity = self._extract_purity(request_no, job_no, qm_url)
                
                if purity:
                    self.log(f"✓ Found purity: {purity}")
                    # Update job in memory
                    self.scanned_jobs[idx]['purity'] = purity
                    
                    # Update tree view
                    children = self.preview_tree.get_children()
                    if idx < len(children):
                        self.preview_tree.after(0, lambda item=children[idx], p=purity:
                            self.preview_tree.set(item, 'purity', p))
                    
                    success += 1
                else:
                    self.log(f"⚠ Purity not found for job {job_no}")
                    failed += 1
                    
            except Exception as e:
                self.log(f"❌ Error scanning job {job_no}: {str(e)}")
                failed += 1
        
        self.log(f"\\n📊 PURITY SCAN SUMMARY:")
        self.log(f"   Success: {success}")
        self.log(f"   Failed: {failed}")
        self.log(f"{'='*50}\\n")
        
        self.is_processing = False
        
        
        # Re-enable buttons
        self.preview_tree.after(0, lambda: self.scan_purity_btn.config(state='normal'))
        self.preview_tree.after(0, lambda: self.save_selected_btn.config(state='normal'))
        
        # Show completion message
        if not auto_mode:
            self.preview_tree.after(0, lambda: messagebox.showinfo("Complete", 
                f"Purity scan complete!\\n\\nSuccess: {success}\\nFailed: {failed}"))
        
        if chain_save:
            self.log("💾 Auto Scan: Saving jobs with updated purity...")
            self.preview_tree.after(1000, lambda: self.save_selected_jobs(auto=True))
        
        # If auto mode but NOT chaining save (standalone purity scan), update cycle
        elif auto_mode:
            self.log("⏳ Cycle done. Restarting soon...")
            self.preview_tree.after(0, lambda: self._start_countdown(30, self.start_scanning))
    
    def _scan_delivery_list(self):
        """Scan delivery list page with pagination support"""
        jobs = []
        page_num = 1
        seen_job_numbers = set()  # Track job numbers to detect duplicates
        
        try:
            while True:  # Loop through all pages
                self.log(f"📄 Scanning page {page_num}...")
                
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "table"))
                )
                
                tables = self.driver.find_elements(By.TAG_NAME, "table")
                target = None
                
                for table in tables:
                    if "Request No" in table.text or "Job No" in table.text:
                        target = table
                        break
                
                if not target:
                    break
                
                rows = target.find_elements(By.TAG_NAME, "tr")[1:]
                jobs_on_page = 0
                duplicates_on_page = 0
                
                for row in rows:
                    try:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) >= 4:
                            request_no = cells[1].text.strip()
                            job_no = cells[2].text.strip()
                            job_date = cells[3].text.strip() if len(cells) > 3 else ""
                            jeweller_name = cells[4].text.strip() if len(cells) > 4 else "Unknown"
                            
                            # Check for duplicate
                            if job_no in seen_job_numbers:
                                duplicates_on_page += 1
                                continue
                            
                            seen_job_numbers.add(job_no)
                            
                            links = row.find_elements(By.TAG_NAME, "a")
                            voucher_url = ""
                            qm_url = ""
                            
                            for link in links:
                                href = link.get_attribute("href") or ""
                                onclick = link.get_attribute("onclick") or ""
                                text = link.text or ""
                                
                                # Check href and onclick for voucher URL
                                if "Delivery" in text or "AHCDeliveryVoucher" in href:
                                    voucher_url = href
                                
                                # Check href AND onclick for QM URL
                                qm_candidate = ""
                                if "QMReceivingUIDJewellerRequestView" in href:
                                    qm_candidate = href
                                elif "QMReceivingUIDJewellerRequestView" in onclick:
                                    # Extract URL from onclick like: window.open('URL', ...)
                                    import re as _re_list
                                    onclick_match = _re_list.search(r"['\"]([^'\"]*QMReceivingUIDJewellerRequestView[^'\"]*)['\"]" , onclick)
                                    if onclick_match:
                                        qm_candidate = onclick_match.group(1)
                                
                                if qm_candidate:
                                    # Make absolute if relative
                                    if qm_candidate.startswith('/'):
                                        qm_candidate = portal_base() + qm_candidate
                                    qm_url = qm_candidate.replace('&amp;', '&').replace('&#38;', '&')
                                    # Capture fixed params from first good QM URL
                                    if not self.qm_url_fixed_params:
                                        from urllib.parse import urlparse, parse_qs
                                        parsed = urlparse(qm_url)
                                        params = parse_qs(parsed.query)
                                        # Extract only the fixed params (not request/job specific ones)
                                        for key in ['eCmlNo', 'eBranchId', 'eroleId', 'eOutletId', 'eOutletBranchId']:
                                            if key in params:
                                                self.qm_url_fixed_params[key] = params[key][0]
                                        if self.qm_url_fixed_params:
                                            self.log(f"✅ Captured fixed QM URL params: {list(self.qm_url_fixed_params.keys())}")
                            
                            if request_no and job_no:
                                jobs.append({
                                    'request_no': request_no,
                                    'job_no': job_no,
                                    'job_date': job_date,
                                    'jeweller_name': jeweller_name,
                                    'material': 'Gold',  # Default since it's not in table
                                    'voucher_url': voucher_url,
                                    'qm_url': qm_url
                                })
                                jobs_on_page += 1
                    except:
                        continue
                
                self.log(f"✓ Found {jobs_on_page} new jobs on page {page_num}")
                
                # If we found mostly duplicates, we've likely looped back
                if duplicates_on_page > 0 and jobs_on_page == 0:
                    self.log(f"✓ Reached end of list (all jobs on this page were duplicates)")
                    break
                
                # Check for next page button
                try:
                    # Common pagination patterns
                    next_button = None
                    pagination_patterns = [
                        "//a[contains(text(), 'Next')]",
                        "//a[contains(text(), '›')]",
                        "//a[contains(text(), '>')]",
                        "//input[@value='Next']",
                        "//button[contains(text(), 'Next')]"
                    ]
                    
                    for pattern in pagination_patterns:
                        try:
                            next_button = self.driver.find_element(By.XPATH, pattern)
                            if next_button and next_button.is_enabled():
                                # Check if button is actually clickable (not disabled)
                                if 'disabled' in next_button.get_attribute('class') or '':
                                    next_button = None
                                    break
                                    
                                self.log(f"➡️ Navigating to page {page_num + 1}...")
                                next_button.click()
                                time.sleep(2)  # Wait for page to load
                                page_num += 1
                                break
                        except:
                            continue
                    
                    if not next_button:
                        self.log(f"✓ No more pages found")
                        break
                        
                except Exception as e:
                    self.log(f"✓ Finished pagination (no next button)")
                    break
            
            return jobs
        except:
            return jobs
    
    def _scan_voucher_details(self, job_info, session=None):
        """Scan voucher details page with improved extraction"""
        try:
            purity = ""
            
            # Navigate to voucher page
            if job_info.get('voucher_url'):
                self.driver.get(job_info['voucher_url'])
            else:
                url = f"{portal_base()}/MANAK/AHCDeliveryVoucher?requestNo={job_info['request_no']}&jobNo={job_info['job_no']}&material={job_info['material']}"
                self.driver.get(url)

                # Wait for page body to load (reduced timeout for speed)
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                # Removed extra sleep to speed up processing  # Wait for page to load
            
            # Capture QM URL from this page if not already set on job_info
            # Stored in DB so the separate 'Scan Purity' step can use it later
            captured_qm_url = job_info.get('qm_url', '')
            if not captured_qm_url:
                try:
                    import re as _re
                    page_src = self.driver.page_source
                    raw_url = ''

                    # Pattern 1: Full absolute https URL in page source
                    m = _re.search(
                        r'(https?://[^"\'<>\s]*QMReceivingUIDJewellerRequestView[^"\'<>\s]*)',
                        page_src
                    )
                    if m:
                        raw_url = m.group(1)

                    # Pattern 2: Relative URL (e.g. href="/MANAK/QMReceiving...")
                    if not raw_url:
                        m = _re.search(
                            r'["\'](/[^"\'<>\s]*QMReceivingUIDJewellerRequestView[^"\'<>\s]*)["\']',
                            page_src
                        )
                        if m:
                            raw_url = portal_base() + m.group(1)

                    # Pattern 3: Selenium - check all <a> href and onclick attributes
                    if not raw_url:
                        try:
                            for lnk in self.driver.find_elements(By.TAG_NAME, 'a'):
                                href = lnk.get_attribute('href') or ''
                                onclick = lnk.get_attribute('onclick') or ''
                                if 'QMReceivingUIDJewellerRequestView' in href:
                                    raw_url = href
                                    break
                                if 'QMReceivingUIDJewellerRequestView' in onclick:
                                    om = _re.search(r'["\']([^"\']*QMReceivingUIDJewellerRequestView[^"\']*)["\']', onclick)
                                    if om:
                                        c = om.group(1)
                                        raw_url = (portal_base() + c) if c.startswith('/') else c
                                        break
                        except Exception:
                            pass

                    if raw_url:
                        captured_qm_url = raw_url.replace('&amp;', '&').replace('&#38;', '&')
                        self.log(f"✅ Captured QM URL from voucher page")
                        # Capture fixed params so purity scan can construct URLs for other jobs
                        if not self.qm_url_fixed_params:
                            from urllib.parse import urlparse, parse_qs
                            parsed = urlparse(captured_qm_url)
                            params = parse_qs(parsed.query)
                            for key in ['eCmlNo', 'eBranchId', 'eroleId', 'eOutletId', 'eOutletBranchId']:
                                if key in params:
                                    self.qm_url_fixed_params[key] = params[key][0]
                            if self.qm_url_fixed_params:
                                self.log(f"✅ Captured fixed QM params: {list(self.qm_url_fixed_params.keys())}")
                    # else: QM URL not on voucher page - this is normal, purity scan handles it
                except Exception as qm_e:
                    self.log(f"⚠ QM URL capture failed: {qm_e}")

            
            details = {
                'firm_id': self.current_firm_id,
                'request_no': job_info['request_no'],
                'job_no': job_info['job_no'],
                'material_type': job_info.get('material', 'Gold'),
                'qm_url': captured_qm_url,
                'status': 'Complete',
                'bill_no': None,
                'is_billed': 0,
                'purity': purity  # Add purity to details
            }
            
            # Extract date - try multiple patterns
            try:
                date_patterns = [
                    "//td[contains(text(), 'Job Card Date')]/following-sibling::td",
                    "//label[contains(text(), 'Job Card Date')]/following-sibling::*",
                    "//th[contains(text(), 'Job Card Date')]/following-sibling::td"
                ]
                for pattern in date_patterns:
                    try:
                        date_elem = self.driver.find_element(By.XPATH, pattern)
                        date_text = date_elem.text.strip()
                        if date_text:
                            # Convert DD/MM/YYYY to YYYY-MM-DD for MySQL datetime
                            try:
                                date_obj = datetime.datetime.strptime(date_text, '%d/%m/%Y')
                                details['date_of_request'] = date_obj.strftime('%Y-%m-%d')
                                self.log(f"✓ Date extracted: {date_text} -> {details['date_of_request']}")
                            except ValueError:
                                # If format doesn't match, try other common formats
                                try:
                                    date_obj = datetime.datetime.strptime(date_text, '%Y-%m-%d')
                                    details['date_of_request'] = date_text
                                    self.log(f"✓ Date extracted: {date_text}")
                                except:
                                    details['date_of_request'] = datetime.datetime.now().strftime('%Y-%m-%d')
                                    self.log(f"⚠ Date format unknown: {date_text}, using today")
                            break
                    except:
                        continue
                else:
                    # Try to parse job_date from list if available
                    job_date = job_info.get('job_date', '')
                    if job_date:
                        try:
                            date_obj = datetime.datetime.strptime(job_date, '%d/%m/%Y')
                            details['date_of_request'] = date_obj.strftime('%Y-%m-%d')
                            self.log(f"✓ Date from list: {job_date} -> {details['date_of_request']}")
                        except:
                            details['date_of_request'] = datetime.datetime.now().strftime('%Y-%m-%d')
                            self.log(f"⚠ Date not found, using today's date")
                    else:
                        details['date_of_request'] = datetime.datetime.now().strftime('%Y-%m-%d')
                        self.log(f"⚠ Date not found, using today's date")
            except Exception as e:
                details['date_of_request'] = datetime.datetime.now().strftime('%Y-%m-%d')
                self.log(f"⚠ Date extraction failed: {str(e)}")
            
            # Extract Jeweller Name - try multiple patterns
            try:
                jeweller_patterns = [
                    "//div[contains(text(), 'Jeweller Name')]/following-sibling::div//span[@class='makeInitCap']",
                    "//div[contains(text(), 'Jeweller Name')]/following-sibling::div",
                    "//label[contains(text(), 'Jeweller')]/following::span[@class='makeInitCap'][1]"
                ]
                for pattern in jeweller_patterns:
                    try:
                        jeweller_elem = self.driver.find_element(By.XPATH, pattern)
                        jeweller_text = jeweller_elem.text.strip()
                        if jeweller_text:
                            details['jeweller_name'] = jeweller_text
                            self.log(f"✓ Jeweller extracted: {jeweller_text}")
                            break
                    except:
                        continue
                else:
                    details['jeweller_name'] = job_info.get('jeweller_name', "")
                    self.log(f"⚠ Jeweller name not found on page, using list value")
            except Exception as e:
                details['jeweller_name'] = job_info.get('jeweller_name', "")
                self.log(f"⚠ Jeweller extraction failed: {str(e)}")
            
            # Extract Jeweller Address - try multiple patterns
            try:
                address_patterns = [
                    "//div[contains(text(), 'Jeweller Address')]/following-sibling::div//span[@class='makeInitCap']",
                    "//div[contains(., 'Jeweller') and contains(., 'Address')]/following-sibling::div//span",
                    "//div[contains(text(), 'Address')]/following-sibling::div//span[@class='makeInitCap']"
                ]
                for pattern in address_patterns:
                    try:
                        address_elem = self.driver.find_element(By.XPATH, pattern)
                        address_text = address_elem.text.strip()
                        if address_text and len(address_text) > 5:
                            details['jeweller_address'] = address_text
                            
                            details['jeweller_city'] = ""
                            details['jeweller_state'] = ""
                                
                            self.log(f"✓ Address extracted: {address_text[:50]}...")
                            break
                    except:
                        continue
                else:
                    details['jeweller_address'] = ""
                    details['jeweller_city'] = ""
                    details['jeweller_state'] = ""
                    self.log(f"⚠ Jeweller address not found")
            except Exception as e:
                details['jeweller_address'] = ""
                details['jeweller_city'] = ""
                details['jeweller_state'] = ""
                self.log(f"⚠ Address extraction failed: {str(e)}")
            
            # Extract license number - try multiple patterns
            try:
                license_patterns = [
                    "//div[contains(text(), 'License Number')]/following-sibling::div//span[@class='makeInitCap']",
                    "//div[contains(text(), 'License Number')]/following-sibling::div//span",
                    "//div[contains(text(), 'License Number')]/following-sibling::div",
                    "//td[contains(text(), 'License Number')]/following-sibling::td//span",
                    "//label[contains(text(), 'License Number')]/following-sibling::*//span",
                    "//th[contains(text(), 'License Number')]/following-sibling::td",
                    "//td[contains(text(), 'Licence Number')]/following-sibling::td"
                ]
                for pattern in license_patterns:
                    try:
                        lic_elem = self.driver.find_element(By.XPATH, pattern)
                        lic_text = lic_elem.text.strip()
                        if lic_text and len(lic_text) >= 5:  # License should be at least 5 chars
                            details['licence_no'] = lic_text
                            self.log(f"✓ License extracted: {lic_text}")
                            break
                    except:
                        continue
                else:
                    details['licence_no'] = ""
                    self.log(f"⚠ License not found")
            except Exception as e:
                details['licence_no'] = ""
                self.log(f"⚠ License extraction failed: {str(e)}")
            
            # Extract weight data from "Article Weight Details" section
            try:
                # Try to get total pieces received
                pcs_patterns = [
                    "//td[contains(text(), 'Total Article Received By AHC')]/following-sibling::td",
                    "//label[contains(text(), 'Total Article Received')]/following-sibling::*",
                    "//td[contains(text(), 'Total Article Send By Jeweller')]/following-sibling::td"
                ]
                for pattern in pcs_patterns:
                    try:
                        pcs_elem = self.driver.find_element(By.XPATH, pattern)
                        pcs_text = pcs_elem.text.strip()
                        if pcs_text and pcs_text.isdigit():
                            details['pcs'] = int(pcs_text)
                            details['huid_pcs'] = int(pcs_text)
                            self.log(f"✓ Pieces extracted: {pcs_text}")
                            break
                    except:
                        continue
                else:
                    details['pcs'] = 0
                    details['huid_pcs'] = 0
                    self.log(f"⚠ Pieces not found")
            except Exception as e:
                details['pcs'] = 0
                details['huid_pcs'] = 0
                self.log(f"⚠ Pieces extraction failed: {str(e)}")
            
            # Extract weight observed by AHC
            try:
                weight_patterns = [
                    "//td[contains(text(), 'Weight Observed By AHC')]/following-sibling::td",
                    "//td[contains(text(), 'Total Weight Declared By Jeweller')]/following-sibling::td",
                    "//label[contains(text(), 'Weight Observed')]/following-sibling::*"
                ]
                for pattern in weight_patterns:
                    try:
                        weight_elem = self.driver.find_element(By.XPATH, pattern)
                        weight_text = weight_elem.text.strip().replace('gms', '').replace('g', '').strip()
                        if weight_text:
                            details['weight'] = float(weight_text)
                            self.log(f"✓ Weight extracted: {weight_text} gms")
                            break
                    except:
                        continue
                else:
                    details['weight'] = 0.0
                    self.log(f"⚠ Weight not found")
            except Exception as e:
                details['weight'] = 0.0
                self.log(f"⚠ Weight extraction failed: {str(e)}")
            
            # Extract cornet weight
            try:
                cornet_patterns = [
                    "//td[contains(text(), 'Weight of Cornet')]/following-sibling::td",
                    "//label[contains(text(), 'Weight of Cornet')]/following-sibling::*"
                ]
                for pattern in cornet_patterns:
                    try:
                        cornet = self.driver.find_element(By.XPATH, pattern)
                        cornet_text = cornet.text.strip().replace('mgs', '').replace('mg', '').strip()
                        if cornet_text:
                            details['cornet_weight'] = round(float(cornet_text), 3)
                            self.log(f"✓ Cornet weight extracted: {cornet_text} mgs")
                            break
                    except:
                        continue
                else:
                    details['cornet_weight'] = 0.0
                    self.log(f"⚠ Cornet weight not found")
            except Exception as e:
                details['cornet_weight'] = 0.0
                self.log(f"⚠ Cornet weight extraction failed: {str(e)}")
            
            # Extract scrapping weight
            try:
                scrap_patterns = [
                    "//td[contains(text(), 'Weight of Scrapping')]/following-sibling::td",
                    "//label[contains(text(), 'Weight of Scrapping')]/following-sibling::*",
                    "//td[contains(text(), 'Weight of Scrapping in mgs')]/following-sibling::td"
                ]
                for pattern in scrap_patterns:
                    try:
                        scrap = self.driver.find_element(By.XPATH, pattern)
                        scrap_text = scrap.text.strip().replace('mgs', '').replace('mg', '').strip()
                        if scrap_text:
                            details['scrp_cornet_weight'] = round(float(scrap_text), 3)
                            self.log(f"✓ Scrapping weight extracted: {scrap_text} mgs")
                            break
                    except:
                        continue
                else:
                    details['scrp_cornet_weight'] = 0.0
                    self.log(f"⚠ Scrapping weight not found")
            except Exception as e:
                details['scrp_cornet_weight'] = 0.0
                self.log(f"⚠ Scrapping weight extraction failed: {str(e)}")
            
            # Extract rejected items (fail_pcs)
            try:
                rejected_units = 0
                try:
                    rejected_table = self.driver.find_element(By.XPATH, "//*[contains(text(), 'Rejected Items')]/following::table[1]")
                    if "No Rejected Items" not in rejected_table.text:
                        rows = rejected_table.find_elements(By.TAG_NAME, "tr")
                        for row in rows[1:]: # Skip headers
                            try:
                                cells = row.find_elements(By.TAG_NAME, "td")
                                if len(cells) >= 3:
                                    unit_text = cells[2].text.strip()
                                    if unit_text.isdigit():
                                        rejected_units += int(unit_text)
                            except:
                                continue
                except:
                    pass
                details['fail_pcs'] = rejected_units
                self.log(f"✓ Rejected pieces from table: {rejected_units}")
            except Exception as e:
                details['fail_pcs'] = 0
                self.log(f"⚠ Rejected pieces extraction failed: {str(e)}")
            
            # Extract items from "Accepted Items Details" table
            try:
                # Try to find the Accepted Items table by ID or nearby heading
                table_found = False
                items_table = None
                
                # Try multiple methods to find the table
                try:
                    # Method 1: Find by table ID
                    items_table = self.driver.find_element(By.ID, "tabAcceptedArticles")
                    table_found = True
                    self.log(f"✓ Found table by ID: tabAcceptedArticles")
                except:
                    pass
                
                if not table_found:
                    try:
                        # Method 2: Find by legend text
                        items_table = self.driver.find_element(By.XPATH, "//legend[contains(text(), 'Accepted Items')]/following::table[1]")
                        table_found = True
                        self.log(f"✓ Found table by legend")
                    except:
                        pass
                
                if not table_found:
                    try:
                        # Method 3: Find by label text
                        items_table = self.driver.find_element(By.XPATH, "//label[contains(text(), 'Accepted Items')]/following::table[1]")
                        table_found = True
                        self.log(f"✓ Found table by label")
                    except:
                        pass
                
                if table_found and items_table:
                    rows = items_table.find_elements(By.TAG_NAME, "tr")
                    
                    item_categories = []
                    total_units = 0
                    total_weight = 0.0
                    huids = []
                    huid_details = []  # Store detailed HUID data for database
                    
                    # Process each row (skip header row)
                    for i, row in enumerate(rows[1:]):  # Skip header
                        try:
                            cells = row.find_elements(By.TAG_NAME, "td")
                            
                            # Table structure from HTML:
                            # Column 0: S No.
                            # Column 1: Item Category (e.g., "SET")
                            # Column 2: No Of Unit (e.g., "1")
                            # Column 3: HUID (e.g., "2TNL5R")
                            # Column 4: Weight of Article(Gms) (e.g., "20.18")
                            
                            if len(cells) >= 5:
                                s_no = cells[0].text.strip()
                                item_category = cells[1].text.strip()
                                no_of_unit = cells[2].text.strip()
                                huid = cells[3].text.strip()
                                weight_text = cells[4].text.strip()
                                
                                # Add item category if it's valid and not a duplicate
                                if item_category and item_category not in item_categories:
                                    item_categories.append(item_category)
                                
                                # Sum up units
                                if no_of_unit and no_of_unit.isdigit():
                                    total_units += int(no_of_unit)
                                
                                # Collect HUIDs and detailed data
                                if huid:
                                    huids.append(huid)
                                    
                                    # Store detailed HUID data for database
                                    huid_weight = 0.0
                                    try:
                                        huid_weight = float(weight_text)
                                    except:
                                        pass
                                    
                                    huid_details.append({
                                        'huid': huid,
                                        'item_category': item_category,
                                        'weight': huid_weight,
                                        'serial_no': s_no
                                    })
                                
                                # Sum up weights
                                try:
                                    weight_val = float(weight_text)
                                    total_weight += weight_val
                                except:
                                    pass
                                
                                self.log(f"  Row {i+1}: {item_category} x {no_of_unit} = {weight_text} gms (HUID: {huid})")
                        except Exception as e:
                            continue
                    
                    # Set extracted values
                    if item_categories:
                        details['item'] = ", ".join(item_categories)
                        self.log(f"✓ Item categories extracted: {details['item']}")
                    
                    # Store HUID details
                    if huid_details:
                        # Use Weight Observed By AHC instead of individual table weights
                        ahc_weight = details.get('weight', 0.0)
                        if ahc_weight > 0 and len(huid_details) > 0:
                            avg_weight = round(ahc_weight / len(huid_details), 3)
                            for h_detail in huid_details:
                                h_detail['weight'] = avg_weight
                                
                        details['huid_list'] = huid_details
                        self.log(f"✓ Extracted {len(huid_details)} HUIDs for storage (Weights derived from AHC: {ahc_weight})")
                    
                    # Override pcs if we got them from the table
                    if total_units > 0:
                        details['pcs'] = total_units
                        details['huid_pcs'] = len(huids)
                        self.log(f"✓ Pieces from table: {total_units} (HUIDs: {len(huids)})")
                    
                    # Do NOT overwrite 'weight' with total_weight from table
                    # as we want to keep the 'Weight Observed By AHC'
                    if total_weight > 0:
                        self.log(f"✓ Item table total weight: {total_weight:.2f} gms (Keeping AHC weight: {details.get('weight')} gms)")
                
                # Fallback if no items found
                if 'item' not in details or not details.get('item'):
                    details['item'] = f"Job {job_info['job_no']}"
                    self.log(f"⚠ Items not found in table, using job number")
                    
            except Exception as e:
                details['item'] = f"Job {job_info['job_no']}"
                self.log(f"⚠ Items extraction failed: {str(e)}")
                self.log(f"Traceback: {traceback.format_exc()}")
            
            details['created_at'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Convert cornet weights from MG to GM
            details['cornet_weight'] = self._convert_mg_to_gm(details.get('cornet_weight', 0))
            details['scrp_cornet_weight'] = self._convert_mg_to_gm(details.get('scrp_cornet_weight', 0))
            
            # Log summary
            self.log(f"📋 Extracted: Pcs={details.get('pcs', 0)}, Weight={details.get('weight', 0)}, Cornet={details.get('cornet_weight', 0):.4f} gm")
            
            return details
            
        except Exception as e:
            self.log(f"❌ Error in _scan_voucher_details: {str(e)}")
            self.log(f"Traceback: {traceback.format_exc()}")
            return None
    
    
    def _extract_purity(self, request_no, job_no, qm_url=None):
        """Extract purity from QM request page"""
        try:
            # If QM URL is not provided, try to find it (fallback)
            if not qm_url:
                self.log(f"⚠ QM URL missing in job info, searching list page...")
                # Skipping navigation to list page for speed optimization
                
                # Directly construct the QM URL without searching the list page (speed optimization)
                # The URL will be built using request_no, job_no, and default material 'Gold'.
                # Fixed parameters (eCmlNo, eOutletId) will be added if available.
                # No need to navigate the list page here.
                self.log(f"⚠ QM URL not found, constructing UID_RequestFormViewPage URL directly...")
                try:
                    import base64
                    from urllib.parse import urlencode
                    # Encode request and job numbers
                    b64_req = base64.b64encode(str(request_no).encode()).decode()
                    b64_job = base64.b64encode(str(job_no).encode()).decode()
                    # Material – default to 'Gold'
                    material = 'Gold'
                    b64_material = base64.b64encode(material.encode()).decode()
                    # Build query parameters
                    params = {
                        'requestNo': b64_req,
                        'jobNo': b64_job,
                        'material': b64_material
                    }
                    # Add captured fixed params if we have them (they are already base64 strings)
                    if self.qm_url_fixed_params:
                        if 'eCmlNo' in self.qm_url_fixed_params:
                            params['Ecmlno'] = self.qm_url_fixed_params['eCmlNo']
                        if 'eOutletId' in self.qm_url_fixed_params:
                            params['EoutletId'] = self.qm_url_fixed_params['eOutletId']
                    # Construct URL
                    qm_url = f"{portal_base()}/MANAK/UID_RequestFormViewPage?{urlencode(params)}"
                    self.log(f"✅ Constructed UID_RequestFormViewPage URL: {qm_url}")
                except Exception as e:
                    self.log(f"❌ Failed to construct UID_RequestFormViewPage URL: {e}")
                    return None
            
            # Navigate to QM page
            self.log(f"🌐 Navigating to QM page for job {job_no}...")
            # Set a short page load timeout to avoid long waits
            self.driver.set_page_load_timeout(5)
            self.driver.get(qm_url)

            # Wait briefly for the body element (reduced timeout)
            WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            # No extra sleep needed
            self.log(f"📄 QM page loaded, extracting purity...")
            
            # Extract purity from "Declared Purity" column in the table
            try:
                self.log(f"🔍 Searching for purity table...")
                # Find the table with purity information
                purity_patterns = [
                    "//th[contains(text(), 'Declared Purity')]/ancestor::table",
                    "//td[contains(text(), 'Declared Purity')]/ancestor::table",
                    "//table[@id='tabAcceptedArticles']"
                ]
                
                purity_table = None
                for idx, pattern in enumerate(purity_patterns):
                    try:
                        purity_table = self.driver.find_element(By.XPATH, pattern)
                        if purity_table:
                            self.log(f"✓ Found table using pattern {idx + 1}")
                            break
                    except:
                        continue
                
                if purity_table:
                    self.log(f"🔍 Looking for 'Declared Purity' column...")
                    # Find the column index for "Declared Purity"
                    headers = purity_table.find_elements(By.TAG_NAME, "th")
                    self.log(f"📋 Found {len(headers)} columns: {[h.text for h in headers]}")
                    purity_col_idx = -1
                    
                    for idx, header in enumerate(headers):
                        if "Declared Purity" in header.text:
                            purity_col_idx = idx
                            self.log(f"✓ Found 'Declared Purity' at column {idx}")
                            break
                    
                    if purity_col_idx >= 0:
                        # Get the first data row's purity value
                        rows = purity_table.find_elements(By.TAG_NAME, "tr")
                        self.log(f"📋 Found {len(rows)} rows in table")
                        for row in rows[1:]:  # Skip header
                            cells = row.find_elements(By.TAG_NAME, "td")
                            if len(cells) > purity_col_idx:
                                purity_text = cells[purity_col_idx].text.strip()
                                if purity_text:
                                    self.log(f"✓ Purity extracted: {purity_text}")
                                    return purity_text
                    else:
                        self.log(f"⚠ 'Declared Purity' column not found in headers")
                else:
                    self.log(f"⚠ Purity table not found on page")
                
                self.log(f"⚠ Purity not found in table for job {job_no}")
                return None
                
            except Exception as e:
                self.log(f"⚠ Purity extraction failed: {str(e)}")
                return None
                
        except Exception as e:
            self.log(f"⚠ Error navigating to QM page: {str(e)}")
            return None
    
    def _check_job_exists(self, job_no):
        """Check if job exists"""
        try:
            db_config_fast = self.db_config.copy()
            db_config_fast['connect_timeout'] = 3
            conn = mysql.connector.connect(**db_config_fast)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM job_cards WHERE job_no = %s AND firm_id = %s", (job_no, self.current_firm_id))
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return result[0] > 0 if result else False
        except:
            return False
    
    def _save_job_to_database(self, job):
        """Save job to database"""
        try:
            # 1. Try API First
            try:
                # Ensure all values are JSON serializable
                api_job = job.copy()
                # Convert any datetime objects to string
                for key, val in api_job.items():
                    if isinstance(val, (datetime.date, datetime.datetime)):
                        api_job[key] = val.strftime('%Y-%m-%d %H:%M:%S')
                
                payload = {
                    'action': 'save_job',
                    'firm_id': self.current_firm_id,
                    'job': api_job
                }
                
                response = requests.post(config.SAVE_JOB_API_URL, json=payload, timeout=8)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        self.log(f"✅ API: Saved job {job.get('job_no')}")
                        return True
                    else:
                        self.log(f"⚠️ API Save Error: {data.get('message')}")
            except Exception as e:
                self.log(f"⚠️ Job API Save failed: {str(e)}")

            # DB Fallback removed to prevent timeouts
            return False
            
        except Exception as e:
            self.log(f"❌ DB Error: {str(e)}")
            return False
            
    def _check_jeweller_exists(self, licence_no):
        """Check if jeweller exists in database by license number"""
        try:
            # 1. Try API First
            try:
                payload = {
                    'action': 'check',
                    'licence_no': licence_no,
                    'firm_id': self.current_firm_id
                }
                response = requests.post(config.MANAGE_JEWELLER_API_URL, json=payload, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        exists = data.get('exists', False)
                        return exists
                    else:
                        self.log(f"⚠️ API Check Error: {data.get('message')}")
                else:
                    self.log(f"⚠️ API Status Code: {response.status_code}")
                    try:
                        self.log(f"Response: {response.text}")
                    except:
                        pass
                    
            except Exception as e:
                self.log(f"⚠️ Jeweller API Check failed: {str(e)}")

            # DB Fallback removed to prevent timeouts as per user request
            return False
            
        except Exception as e:
            self.log(f"⚠ Error checking jeweller: {str(e)}")
            return False
    
    def _insert_jeweller(self, jeweller_data):
        """Insert new jeweller into database"""
        try:
            # 1. Try API First
            try:
                payload = {
                    'action': 'create',
                    'firm_id': self.current_firm_id,
                    'licence_no': jeweller_data.get('licence_no', ''),
                    'name': jeweller_data.get('jeweller_name', ''),
                    'address': jeweller_data.get('jeweller_address', ''),
                    'city': jeweller_data.get('jeweller_city', ''), 
                    'state': jeweller_data.get('jeweller_state', '')
                }
                
                response = requests.post(config.MANAGE_JEWELLER_API_URL, json=payload, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        self.log(f"✅ API: Jeweller created: {jeweller_data.get('jeweller_name', 'N/A')}")
                        return True
                    else:
                        self.log(f"⚠️ API Create Error: {data.get('message')}")
                else:
                    self.log(f"⚠️ API Status Code: {response.status_code}")
                    try:
                        self.log(f"Response: {response.text}")
                    except:
                        pass
                        
            except Exception as e:
                self.log(f"⚠️ Jeweller API Create failed: {str(e)}")

            # DB Fallback removed to prevent timeouts
            return False
            
        except Exception as e:
            self.log(f"❌ Error inserting jeweller: {str(e)}")
            self.log(f"Traceback: {traceback.format_exc()}")
            return False

    def _save_huids_to_database(self, job_no, huid_list):
        """Save HUIDs to huid_data table"""
        if not huid_list:
            return True
            
        try:
            # 1. Try API First
            try:
                payload = {
                    'action': 'save_huids',
                    'firm_id': self.current_firm_id,
                    'job_no': job_no,
                    'huid_list': huid_list
                }
                
                response = requests.post(config.SAVE_JOB_API_URL, json=payload, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        count = data.get('saved_count', 0)
                        self.log(f"✅ API: Saved {count} HUIDs")
                        return True
                    else:
                        self.log(f"⚠️ API HUID Save Error: {data.get('message')}")
                else:
                    self.log(f"⚠️ API HUID Save Status Code: {response.status_code}")
                    try:
                        self.log(f"Response: {response.text}")
                    except:
                        pass

            except Exception as e:
                self.log(f"⚠️ HUID API Save failed: {str(e)}")

            # DB Fallback removed to prevent timeouts
            return False
            
        except Exception as e:
            self.log(f"❌ Error saving HUIDs: {str(e)}")
            self.log(f"Traceback: {traceback.format_exc()}")
            return False
    
    def _ensure_jeweller_exists(self, job):
        """Ensure jeweller exists in database, create if not"""
        licence_no = job.get('licence_no', '')
        
        if not licence_no:
            self.log(f"⚠ No license number provided for job {job.get('job_no', 'N/A')}")
            return True  # Continue anyway
        
        # Check if jeweller exists
        if self._check_jeweller_exists(licence_no):
            self.log(f"✓ Jeweller already exists (License: {licence_no})")
            return True
        
        # Jeweller doesn't exist, create it
        self.log(f"🆕 Creating new jeweller (License: {licence_no})")
        
        jeweller_data = {
            'licence_no': licence_no,
            'jeweller_name': job.get('jeweller_name', 'Unknown'),
            'jeweller_address': job.get('jeweller_address', ''),
            'jeweller_city': job.get('jeweller_city', ''),
            'jeweller_state': job.get('jeweller_state', '')
        }
        
        return self._insert_jeweller(jeweller_data)
    
    def _update_stats_display(self, stats):
        """Update stats - THREAD SAFE"""
        def _update():
            try:
                if 'scanned' in self.stats_labels:
                    self.stats_labels['scanned'].config(text=f"🔍 Scanned: {stats['scanned']}")
                if 'existing' in self.stats_labels:
                    self.stats_labels['existing'].config(text=f"✅ Already Exists: {stats['existing']}")
                if 'errors' in self.stats_labels:
                    self.stats_labels['errors'].config(text=f"❌ Errors: {stats['errors']}")
            except:
                pass
        
        if self.stats_labels:
            self.preview_tree.after(0, _update)
