#!/usr/bin/env python3
"""
Weight Capture Processor Module
Handles automated weight entry from huid_data table to MANAK portal
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import base64

from config import DB_CONFIG


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
        
    def get_firm_id_from_settings(self):
        """Get Firm ID from settings page or device license"""
        try:
            if self.app_context and hasattr(self.app_context, 'firm_id_var'):
                firm_id = self.app_context.firm_id_var.get().strip()
                if firm_id:
                    return firm_id
            
            if self.app_context and hasattr(self.app_context, 'license_manager'):
                license_manager = self.app_context.license_manager
                if hasattr(license_manager, 'firm_id') and license_manager.firm_id:
                    return license_manager.firm_id
        except Exception as e:
            print(f"Warning: Could not get Firm ID: {e}")
        
        return '2'
    
    def refresh_firm_id(self):
        """Refresh firm_id from settings and update display"""
        old_firm_id = self.current_firm_id
        self.current_firm_id = self.get_firm_id_from_settings()
        
        if hasattr(self, 'firm_id_label'):
            self.firm_id_label.config(text=f"Firm {self.current_firm_id}")
        
        if old_firm_id != self.current_firm_id:
            self.log_weight(f"🏢 Firm ID updated from {old_firm_id} to {self.current_firm_id}")
    
    def setup_weight_capture_tab(self, notebook):
        """Setup Weight Capture tab"""
        self.notebook = notebook
        capture_frame = ttk.Frame(notebook)
        notebook.add(capture_frame, text="⚖️ Weight Capture")
        
        # Main container - very compact
        main_container = ttk.Frame(capture_frame)
        main_container.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Compact header with title and badges in one line
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill='x', pady=(0, 5))
        
        # Title on left - smaller
        ttk.Label(header_frame, text="⚖️ Weight Capture", 
                 font=('Segoe UI', 10, 'bold')).pack(side='left')
        
        # Compact badges on right
        info_frame = ttk.Frame(header_frame)
        info_frame.pack(side='right')
        
        # Material type badge - smaller
        self.material_type_label = tk.Label(info_frame, text="📦 Gold", 
                                           font=('Segoe UI', 8, 'bold'),
                                           bg='#FFF3CD', fg='#856404',
                                           padx=5, pady=1, relief='flat')
        self.material_type_label.pack(side='left', padx=(0, 3))
        
        # Firm ID badge - smaller
        self.firm_id_label = tk.Label(info_frame, text=f"Firm {self.current_firm_id}", 
                                     font=('Segoe UI', 8),
                                     bg='#D1ECF1', fg='#0C5460',
                                     padx=5, pady=1, relief='flat')
        self.firm_id_label.pack(side='left')
        
        # Controls - inline, no card
        controls_frame = ttk.Frame(main_container)
        controls_frame.pack(fill='x', pady=(0, 5))
        
        # Compact load buttons on left
        load_btn_frame = ttk.Frame(controls_frame)
        load_btn_frame.pack(side='left')
        
        load_gold_btn = tk.Button(load_btn_frame, text="🔄 Gold", 
                                 font=('Segoe UI', 8, 'bold'),
                                 bg='#17A2B8', fg='white', 
                                 activebackground='#138496', activeforeground='white',
                                 relief='flat', padx=8, pady=2,
                                 cursor='hand2', command=self.load_gold_jobs)
        load_gold_btn.pack(side='left', padx=(0, 3))
        
        load_silver_btn = tk.Button(load_btn_frame, text="🥈 Silver", 
                                   font=('Segoe UI', 8, 'bold'),
                                   bg='#6C757D', fg='white',
                                   activebackground='#5A6268', activeforeground='white',
                                   relief='flat', padx=8, pady=2,
                                   cursor='hand2', command=self.load_silver_jobs)
        load_silver_btn.pack(side='left')
        
        # Compact speed control on right
        speed_frame = ttk.Frame(controls_frame)
        speed_frame.pack(side='right')
        
        ttk.Label(speed_frame, text="⚡", font=('Segoe UI', 9)).pack(side='left', padx=(0, 2))
        self.speed_var = tk.StringVar(value="0.3")
        speed_combo = ttk.Combobox(speed_frame, textvariable=self.speed_var, 
                                   values=['0.3', '0.5', '1.0'], width=4, state='readonly',
                                   font=('Segoe UI', 8))
        speed_combo.pack(side='left', padx=(0, 2))
        ttk.Label(speed_frame, text="s", font=('Segoe UI', 8)).pack(side='left')
        
        # Table - no card, direct
        table_label = ttk.Label(main_container, text="📋 Jobs", font=('Segoe UI', 8, 'bold'), foreground='#495057')
        table_label.pack(anchor='w', pady=(0, 2))
        
        # Table container - minimal padding
        tree_container = ttk.Frame(main_container, relief='solid', borderwidth=1)
        tree_container.pack(fill='both', expand=True, pady=(0, 5))
        
        # Scrollbars
        v_scroll = ttk.Scrollbar(tree_container, orient="vertical")
        v_scroll.pack(side='right', fill='y')
        
        h_scroll = ttk.Scrollbar(tree_container, orient="horizontal")
        h_scroll.pack(side='bottom', fill='x')
        
        # Compact treeview
        columns = ('Select', 'Request No', 'Job No', 'Material', 'Tags', 'Filled', 'Status')
        
        self.jobs_tree = ttk.Treeview(tree_container, columns=columns, show='headings',
                                      yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set,
                                      height=12)
        
        v_scroll.config(command=self.jobs_tree.yview)
        h_scroll.config(command=self.jobs_tree.xview)
        
        # Column headings - compact names
        self.jobs_tree.heading('Select', text='☑')
        self.jobs_tree.heading('Request No', text='Request')
        self.jobs_tree.heading('Job No', text='Job No')
        self.jobs_tree.heading('Material', text='Type')
        self.jobs_tree.heading('Tags', text='Tags')
        self.jobs_tree.heading('Filled', text='Done')
        self.jobs_tree.heading('Status', text='Status')
        
        # Optimized column widths
        self.jobs_tree.column('Select', width=35, anchor='center', minwidth=35)
        self.jobs_tree.column('Request No', width=100, minwidth=80)
        self.jobs_tree.column('Job No', width=100, minwidth=80)
        self.jobs_tree.column('Material', width=60, anchor='center', minwidth=50)
        self.jobs_tree.column('Tags', width=50, anchor='center', minwidth=40)
        self.jobs_tree.column('Filled', width=50, anchor='center', minwidth=40)
        self.jobs_tree.column('Status', width=280, minwidth=150)
        
        self.jobs_tree.pack(fill='both', expand=True)
        
        # Configure row tags for color coding
        self.jobs_tree.tag_configure('ready', background='#D4EDDA')  # Light green
        self.jobs_tree.tag_configure('skip', background='#F8F9FA')   # Light gray
        self.jobs_tree.tag_configure('filled', background='#D1ECF1')  # Light blue
        self.jobs_tree.tag_configure('error', background='#F8D7DA')   # Light red
        
        # Bind click event
        self.jobs_tree.bind('<Button-1>', self.on_tree_click)
        
        # Compact action row
        action_frame = ttk.Frame(main_container)
        action_frame.pack(fill='x', pady=(0, 5))
        
        # Tiny selection buttons on left
        select_btn_frame = ttk.Frame(action_frame)
        select_btn_frame.pack(side='left')
        
        select_all_btn = tk.Button(select_btn_frame, text="☑", 
                                   font=('Segoe UI', 8),
                                   bg='#E9ECEF', fg='#495057',
                                   activebackground='#DEE2E6', activeforeground='#495057',
                                   relief='flat', padx=6, pady=2,
                                   cursor='hand2', command=self.select_all_jobs)
        select_all_btn.pack(side='left', padx=(0, 2))
        
        deselect_all_btn = tk.Button(select_btn_frame, text="☐", 
                                     font=('Segoe UI', 8),
                                     bg='#E9ECEF', fg='#495057',
                                     activebackground='#DEE2E6', activeforeground='#495057',
                                     relief='flat', padx=6, pady=2,
                                     cursor='hand2', command=self.deselect_all_jobs)
        deselect_all_btn.pack(side='left')
        
        # Compact primary action button on right
        autofill_btn = tk.Button(action_frame, text="⚡ Auto-Fill Weights", 
                                font=('Segoe UI', 9, 'bold'),
                                bg='#28A745', fg='white',
                                activebackground='#218838', activeforeground='white',
                                relief='flat', padx=12, pady=4,
                                cursor='hand2', command=self.autofill_selected_weights)
        autofill_btn.pack(side='right')
        
        # Compact progress section
        prog_frame = ttk.Frame(main_container)
        prog_frame.pack(fill='x', pady=(0, 5))
        
        ttk.Label(prog_frame, text="📊", font=('Segoe UI', 8)).pack(side='left', padx=(0, 3))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(prog_frame, variable=self.progress_var, 
                                          maximum=100, mode='determinate')
        self.progress_bar.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        self.progress_label = ttk.Label(prog_frame, text="Ready", 
                                       font=('Segoe UI', 8), foreground='#6C757D')
        self.progress_label.pack(side='left')
        
        # Log card
        log_card = ttk.LabelFrame(main_container, text="� Log", style='Compact.TLabelframe')
        log_card.pack(fill='both', expand=True)
        
        log_inner = ttk.Frame(log_card)
        log_inner.pack(fill='both', expand=True, padx=5, pady=5)
        
        log_scroll = ttk.Scrollbar(log_inner)
        log_scroll.pack(side='right', fill='y')
        
        self.log_text = tk.Text(log_inner, height=6, wrap='word', 
                               font=('Consolas', 8),
                               yscrollcommand=log_scroll.set)
        self.log_text.pack(fill='both', expand=True)
        log_scroll.config(command=self.log_text.yview)
    
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
            if int(values[3]) > 0:  # Tags Available column
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
    
    def _load_jobs_worker(self):
        """Worker thread to load jobs from portal"""
        try:
            self.refresh_firm_id()
            
            if not self.driver:
                self.log_weight("❌ Browser not available. Please login first.")
                return
            
            # Determine the correct URL based on material type
            if self.current_material_type == "Silver":
                list_url = "https://huid.manakonline.in/MANAK/NewArticlesListForWeighingSilver"
                self.log_weight("🥈 Navigating to Silver weight capture list...")
            else:
                list_url = "https://huid.manakonline.in/MANAK/NewArticlesListForWeighing"
                self.log_weight("🌐 Navigating to Gold weight capture list...")
            
            # Navigate to weight capture page
            self.driver.get(list_url)
            
            # Wait for page load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(2)
            
            self.log_weight("🔍 Extracting jobs from portal (checking all pages)...")
            
            # Extract jobs from ALL pages
            all_portal_jobs = []
            page_count = 0
            
            while True:
                page_count += 1
                self.log_weight(f"📄 Processing page {page_count}...")
                
                # Extract jobs from current page
                page_jobs = self.extract_jobs_from_portal()
                
                if page_jobs:
                    all_portal_jobs.extend(page_jobs)
                    self.log_weight(f"✅ Found {len(page_jobs)} jobs on page {page_count}")
                else:
                    self.log_weight(f"⚠️ No jobs found on page {page_count}")
                
                # Try to go to next page
                if not self._go_to_next_page():
                    self.log_weight(f"📄 Reached last page (page {page_count})")
                    break
                
                # Small delay between pages
                time.sleep(1)
            
            if not all_portal_jobs:
                self.log_weight("⚠️ No jobs found on portal")
                return
            
            self.log_weight(f"✅ Found {len(all_portal_jobs)} total jobs across {page_count} pages")
            
            # Pre-load ALL weights from database for these jobs
            self.log_weight("💾 Loading weights from database...")
            job_numbers = [job['job_no'] for job in all_portal_jobs]
            self.preload_weights_cache(job_numbers)
            
            # Clear tree
            self.jobs_tree.delete(*self.jobs_tree.get_children())
            self.jobs_data = []
            self.selected_jobs.clear()
            
            # Add jobs to tree with status
            for job in all_portal_jobs:
                job_no = job['job_no']
                request_no = job['request_no']
                material = job['material']
                
                # Check how many weights available in database
                tags_in_db = self.weights_cache.get(job_no, {})
                tags_available = len([w for w in tags_in_db.values() if w['weight'] > 0])
                
                # Determine status and tag for color coding
                if tags_available == 0:
                    status_text = "❌ Skip (0 weights)"
                    row_tag = 'skip'
                else:
                    status_text = f"✅ Ready ({tags_available} weights)"
                    row_tag = 'ready'
                
                # Add to tree with color-coded tag
                self.jobs_tree.insert('', 'end', values=(
                    '☐',
                    request_no,
                    job_no,
                    material,
                    tags_available,
                    0,  # Filled count (will update during processing)
                    status_text
                ), tags=(row_tag,))
                
                self.jobs_data.append({
                    'request_no': request_no,
                    'job_no': job_no,
                    'material': material,
                    'tags_available': tags_available
                })
            
            ready_count = len([j for j in self.jobs_data if j['tags_available'] > 0])
            self.log_weight(f"✅ Loaded {len(all_portal_jobs)} jobs: {ready_count} ready, {len(all_portal_jobs)-ready_count} skipped")
            
        except Exception as e:
            self.log_weight(f"❌ Error loading jobs: {str(e)}")
    
    def extract_jobs_from_portal(self):
        """Extract jobs from weight capture portal page"""
        try:
            jobs = []
            
            # Find all table rows
            rows = self.driver.find_elements(By.TAG_NAME, "tr")
            
            for row in rows:
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    
                    if len(cells) < 4:
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
                    material = cells[4].text.strip() if len(cells) > 4 else ""
                    
                    # Validate the extracted values
                    # Request No should be 8-9 digits starting with 11
                    if not (request_no.isdigit() and len(request_no) >= 8):
                        # Fallback: search all cells
                        for cell in cells:
                            text = cell.text.strip()
                            if text.isdigit() and len(text) >= 8 and text.startswith('11') and not request_no:
                                request_no = text
                                break
                    
                    # Job No should be 8-9 digits starting with 12
                    if not (job_no.isdigit() and len(job_no) >= 8):
                        # Fallback: search all cells
                        for cell in cells:
                            text = cell.text.strip()
                            if text.isdigit() and len(text) >= 8 and text.startswith('12') and not job_no:
                                job_no = text
                                break
                    
                    # Material validation
                    if material not in ['Gold', 'Silver', 'Platinum']:
                        # Fallback: search all cells
                        for cell in cells:
                            text = cell.text.strip()
                            if text in ['Gold', 'Silver', 'Platinum']:
                                material = text
                                break
                    
                    if request_no and job_no:
                        jobs.append({
                            'request_no': request_no,
                            'job_no': job_no,
                            'material': material or 'Unknown'
                        })
                        self.log_weight(f"  📋 Found: Request={request_no}, Job={job_no}, Material={material}")
                
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
        """Pre-load all weights from database into memory cache for fast lookup"""
        try:
            if not job_numbers:
                return
            
            import mysql.connector
            # Add auth_plugin to fix MySQL 8.0+ authentication compatibility
            db_config_with_auth = self.db_config.copy()
            db_config_with_auth['auth_plugin'] = 'mysql_native_password'
            connection = mysql.connector.connect(**db_config_with_auth)
            cursor = connection.cursor()
            
            # Build placeholders for IN clause
            placeholders = ','.join(['%s'] * len(job_numbers))
            
            # Query all weights for these jobs
            query = f"""
                SELECT job_no, tag_no, weight, huid_code
                FROM huid_data
                WHERE job_no IN ({placeholders})
                  AND weight > 0
                ORDER BY job_no, serial_no
            """
            
            cursor.execute(query, tuple(job_numbers))
            results = cursor.fetchall()
            
            cursor.close()
            connection.close()
            
            # Build cache dictionary
            self.weights_cache = {}
            
            for job_no, tag_no, weight, huid_code in results:
                if job_no not in self.weights_cache:
                    self.weights_cache[job_no] = {}
                
                # Store by tag_no for fast lookup
                self.weights_cache[job_no][str(tag_no)] = {
                    'weight': float(weight),
                    'huid': huid_code
                }
            
            total_weights = sum(len(tags) for tags in self.weights_cache.values())
            self.log_weight(f"✅ Cached {total_weights} weights for {len(self.weights_cache)} jobs")
            
        except Exception as e:
            self.log_weight(f"❌ Error loading weights cache: {str(e)}")
    
    def autofill_selected_weights(self):
        """Auto-fill weights for selected jobs"""
        if not self.selected_jobs:
            messagebox.showwarning("No Selection", "Please select at least one job")
            return
        
        count = len(self.selected_jobs)
        if not messagebox.askyesno("Confirm Auto-Fill", 
                                   f"Auto-fill weights for {count} selected job(s)?"):
            return
        
        threading.Thread(target=self._autofill_worker, daemon=True).start()
    
    def _autofill_worker(self):
        """Worker thread to auto-fill weights"""
        try:
            selected_data = [job for job in self.jobs_data if job['job_no'] in self.selected_jobs]
            
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
                    tags_filled = self.fill_weights_for_job(
                        request_no=job['request_no'],
                        job_no=job['job_no'],
                        material=job.get('material', 'Gold')
                    )
                    
                    if tags_filled > 0:
                        success_jobs += 1
                        total_tags_filled += tags_filled
                        self.update_job_status(job['job_no'], f"✅ Filled ({tags_filled} tags)", filled_count=tags_filled)
                        self.log_weight(f"✅ Job {job['job_no']}: Successfully filled {tags_filled} tags")
                    else:
                        fail_jobs += 1
                        self.update_job_status(job['job_no'], "❌ Failed", filled_count=0)
                        self.log_weight(f"❌ Job {job['job_no']}: Failed to fill weights")
                    
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
                list_url = "https://huid.manakonline.in/MANAK/NewArticlesListForWeighingSilver"
                self.log_weight(f"🔄 Returning to Silver weight capture list...")
            else:
                list_url = "https://huid.manakonline.in/MANAK/NewArticlesListForWeighing"
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
                return 0
            
            # Navigate to weighing form based on material type
            self.log_weight(f"🌐 Opening weighing form for Job {job_no} (Material: {material})...")
            
            # Construct URL based on material type
            # Encode request_no and job_no to base64
            encoded_request = base64.b64encode(request_no.encode()).decode()
            encoded_job = base64.b64encode(job_no.encode()).decode()
            
            if material.lower() == 'silver':
                # Silver weighing form URL
                weight_url = f"https://huid.manakonline.in/MANAK/UID_WeighingFormSilver?requestNo={encoded_request}&jobNo={encoded_job}"
            else:
                # Default to Gold weighing form URL (also for Platinum and others)
                weight_url = f"https://huid.manakonline.in/MANAK/UID_WeighingForm?requestNo={encoded_request}&jobNo={encoded_job}"
            
            self.log_weight(f"🔗 URL: {weight_url}")
            self.driver.get(weight_url)
            
            # Wait for form page
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "tabWeight"))
            )
            time.sleep(1)
            
            self.log_weight(f"✅ Weighing form loaded for Job {job_no}")
            
            # Find all table rows with weight inputs
            table_rows = self.driver.find_elements(By.XPATH, "//tr[@role='row' and contains(@class, 'odd') or contains(@class, 'even')]")
            
            if not table_rows:
                self.log_weight(f"⚠️ No weight entry rows found")
                return 0
            
            self.log_weight(f"📋 Found {len(table_rows)} tags to process")
            
            # Get weights for this job from cache
            job_weights = self.weights_cache.get(job_no, {})
            
            if not job_weights:
                self.log_weight(f"⚠️ No weights in database for Job {job_no}")
                return 0
            
            filled_count = 0
            delay = float(self.speed_var.get())
            
            # Track which tags we've processed to avoid re-processing
            processed_tags = set()
            expected_fill_count = len(job_weights)  # Total weights we should fill
            
            # Keep processing until all database weights are filled or max iterations reached
            max_iterations = 50  # Prevent infinite loop
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
                        
                        # Check if already filled
                        current_value = weight_input.get_attribute('value')
                        if current_value and float(current_value) > 0:
                            self.log_weight(f"  ℹ️ Row {i}: Tag {ahc_tag} - Already filled ({current_value} gms), skipping")
                            processed_tags.add(ahc_tag)
                            continue
                        
                        # Found an unfilled tag - mark it
                        found_unfilled = True
                        
                        # Fill weight
                        weight_input.clear()
                        weight_input.send_keys(str(weight_value))
                        
                        self.log_weight(f"  📝 Row {i}: Tag {ahc_tag} - Filled {weight_value} gms")
                        
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
            
            # NEW: Extract and update HUID codes after all weights are saved
            try:
                self.log_weight(f"📋 Extracting HUID codes from page...")
                huid_mappings = self.extract_huid_codes_from_table()
                
                if huid_mappings:
                    self.log_weight(f"💾 Updating {len(huid_mappings)} HUID codes in database...")
                    updated_count = self.update_huid_codes_in_database(job_no, huid_mappings)
                    self.log_weight(f"✅ Updated {updated_count} HUID codes in database")
                else:
                    self.log_weight(f"⚠️ No HUID codes found to update")
            except Exception as huid_error:
                self.log_weight(f"⚠️ Error updating HUID codes: {str(huid_error)}")
            
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
            
            return filled_count
            
        except Exception as e:
            self.log_weight(f"❌ Error filling weights for Job {job_no}: {str(e)}")
            return 0
    
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
                    
                    if tag_no and huid_code:
                        huid_mappings.append({
                            'tag_no': tag_no,
                            'huid_code': huid_code
                        })
                        self.log_weight(f"  📝 Extracted: Tag {tag_no} → HUID {huid_code}")
                
                except Exception as row_error:
                    continue
            
            return huid_mappings
            
        except Exception as e:
            self.log_weight(f"❌ Error extracting HUID codes: {str(e)}")
            return []
    
    def update_huid_codes_in_database(self, job_no, huid_mappings):
        """Update huid_data table with HUID codes"""
        try:
            import mysql.connector
            # Add auth_plugin to fix MySQL 8.0+ authentication compatibility
            db_config_with_auth = self.db_config.copy()
            db_config_with_auth['auth_plugin'] = 'mysql_native_password'
            connection = mysql.connector.connect(**db_config_with_auth)
            cursor = connection.cursor()
            
            updated_count = 0
            
            for mapping in huid_mappings:
                tag_no = mapping['tag_no']
                huid_code = mapping['huid_code']
                
                # Update query
                update_query = """
                    UPDATE huid_data 
                    SET huid_code = %s 
                    WHERE job_no = %s AND tag_no = %s
                """
                
                cursor.execute(update_query, (huid_code, job_no, tag_no))
                
                if cursor.rowcount > 0:
                    updated_count += 1
                    self.log_weight(f"  ✅ Updated: Job {job_no}, Tag {tag_no} → HUID {huid_code}")
                else:
                    self.log_weight(f"  ⚠️ Not found in DB: Job {job_no}, Tag {tag_no}")
            
            connection.commit()
            cursor.close()
            connection.close()
            
            return updated_count
            
        except Exception as e:
            self.log_weight(f"❌ Database error updating HUID codes: {str(e)}")
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
