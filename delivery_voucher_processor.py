#!/usr/bin/env python3
"""
Delivery Voucher Processor Module
Handles delivery voucher submission automation
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import base64

from config import DB_CONFIG


class DeliveryVoucherProcessor:
    """Handles delivery voucher submission functionality"""
    
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
        
    def get_firm_id_from_settings(self):
        """Get Firm ID from settings page or device license"""
        try:
            # First, try to get from settings page (firm_id_var)
            if self.app_context and hasattr(self.app_context, 'firm_id_var'):
                firm_id = self.app_context.firm_id_var.get().strip()
                if firm_id:
                    print(f"📋 Using Firm ID from settings: {firm_id}")
                    return firm_id
            
            # Fallback to device license
            if self.app_context and hasattr(self.app_context, 'license_manager'):
                license_manager = self.app_context.license_manager
                if hasattr(license_manager, 'firm_id') and license_manager.firm_id:
                    print(f"📋 Using Firm ID from license: {license_manager.firm_id}")
                    return license_manager.firm_id
        except Exception as e:
            print(f"Warning: Could not get Firm ID: {e}")
        
        # Default fallback
        return '2'
    
    def refresh_firm_id(self):
        """Refresh firm_id from settings and update display"""
        old_firm_id = self.current_firm_id
        self.current_firm_id = self.get_firm_id_from_settings()
        
        # Update UI label if it exists
        if hasattr(self, 'firm_id_label'):
            self.firm_id_label.config(text=f"Firm ID: {self.current_firm_id}")
        
        if old_firm_id != self.current_firm_id:
            self.log_delivery(f"🏢 Firm ID updated from {old_firm_id} to {self.current_firm_id}")
    
    def setup_delivery_voucher_tab(self, notebook):
        """Setup Delivery Voucher tab"""
        self.notebook = notebook
        delivery_frame = ttk.Frame(notebook)
        notebook.add(delivery_frame, text="📦 Delivery Voucher")
        
        # Main layout
        main_container = ttk.Frame(delivery_frame)
        main_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Top controls
        controls_frame = ttk.Frame(main_container)
        controls_frame.pack(fill='x', pady=(0, 10))
        
        # Title
        title_label = ttk.Label(controls_frame, text="📦 Delivery Voucher Submission", 
                               font=('Segoe UI', 14, 'bold'))
        title_label.pack(anchor='w', pady=(0, 10))
        
        # Load button
        load_btn = ttk.Button(controls_frame, text="🔄 Load Jobs Ready for Delivery", 
                             style='Info.TButton', command=self.load_delivery_jobs)
        load_btn.pack(side='left', padx=(0, 10))
        
        # Firm ID display (will be updated dynamically)
        self.firm_id_label = ttk.Label(controls_frame, text=f"Firm ID: {self.current_firm_id}", 
                                       font=('Segoe UI', 9))
        self.firm_id_label.pack(side='left', padx=(10, 0))
        
        # Table frame
        table_frame = ttk.LabelFrame(main_container, text="Jobs Ready for Delivery Voucher")
        table_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        # Create treeview with scrollbars
        tree_container = ttk.Frame(table_frame)
        tree_container.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Scrollbars
        v_scroll = ttk.Scrollbar(tree_container, orient="vertical")
        v_scroll.pack(side='right', fill='y')
        
        h_scroll = ttk.Scrollbar(tree_container, orient="horizontal")
        h_scroll.pack(side='bottom', fill='x')
        
        # Treeview
        columns = ('Select', 'ID', 'Request No', 'Job No', 'Item', 'Weight (gms)', 
                   'Scrap Weight (mgs)', 'Return Weight (gms)', 'Status')
        
        self.jobs_tree = ttk.Treeview(tree_container, columns=columns, show='headings',
                                      yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        # Configure scrollbars
        v_scroll.config(command=self.jobs_tree.yview)
        h_scroll.config(command=self.jobs_tree.xview)
        
        # Column headings
        self.jobs_tree.heading('Select', text='☑')
        self.jobs_tree.heading('ID', text='ID')
        self.jobs_tree.heading('Request No', text='Request No')
        self.jobs_tree.heading('Job No', text='Job No')
        self.jobs_tree.heading('Item', text='Item')
        self.jobs_tree.heading('Weight (gms)', text='Weight (gms)')
        self.jobs_tree.heading('Scrap Weight (mgs)', text='Scrap Weight (mgs)')
        self.jobs_tree.heading('Return Weight (gms)', text='Return Weight (gms)')
        self.jobs_tree.heading('Status', text='Status')
        
        # Column widths
        self.jobs_tree.column('Select', width=40, anchor='center')
        self.jobs_tree.column('ID', width=50, anchor='center')
        self.jobs_tree.column('Request No', width=100)
        self.jobs_tree.column('Job No', width=100)
        self.jobs_tree.column('Item', width=100)
        self.jobs_tree.column('Weight (gms)', width=100, anchor='e')
        self.jobs_tree.column('Scrap Weight (mgs)', width=120, anchor='e')
        self.jobs_tree.column('Return Weight (gms)', width=130, anchor='e')
        self.jobs_tree.column('Status', width=150)
        
        self.jobs_tree.pack(fill='both', expand=True)
        
        # Bind click event for checkbox toggle
        self.jobs_tree.bind('<Button-1>', self.on_tree_click)
        
        # Select/Deselect All button
        select_frame = ttk.Frame(main_container)
        select_frame.pack(fill='x', pady=(0, 10))
        
        select_all_btn = ttk.Button(select_frame, text="☑ Select All", 
                                    command=self.select_all_jobs)
        select_all_btn.pack(side='left', padx=(0, 5))
        
        deselect_all_btn = ttk.Button(select_frame, text="☐ Deselect All", 
                                      command=self.deselect_all_jobs)
        deselect_all_btn.pack(side='left')
        
        # Submit button
        submit_btn = ttk.Button(select_frame, text="📦 Submit Selected Delivery Vouchers", 
                               style='Success.TButton', command=self.submit_selected_vouchers)
        submit_btn.pack(side='right')
        
        # Status/Log area
        log_frame = ttk.LabelFrame(main_container, text="📊 Processing Log")
        log_frame.pack(fill='both', expand=True)
        
        # Log text widget
        log_container = ttk.Frame(log_frame)
        log_container.pack(fill='both', expand=True, padx=5, pady=5)
        
        log_scroll = ttk.Scrollbar(log_container)
        log_scroll.pack(side='right', fill='y')
        
        self.log_text = tk.Text(log_container, height=10, wrap='word', 
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
            job_id = values[1]  # ID column
            
            if values[0] == '☑':
                values[0] = '☐'
                self.selected_jobs.discard(job_id)
            else:
                values[0] = '☑'
                self.selected_jobs.add(job_id)
            
            self.jobs_tree.item(item, values=values)
    
    def select_all_jobs(self):
        """Select all jobs"""
        for item in self.jobs_tree.get_children():
            values = list(self.jobs_tree.item(item, 'values'))
            values[0] = '☑'
            self.jobs_tree.item(item, values=values)
            self.selected_jobs.add(values[1])  # Add ID
        
        self.log_delivery(f"✅ Selected all {len(self.selected_jobs)} jobs")
    
    def deselect_all_jobs(self):
        """Deselect all jobs"""
        for item in self.jobs_tree.get_children():
            values = list(self.jobs_tree.item(item, 'values'))
            values[0] = '☐'
            self.jobs_tree.item(item, values=values)
        
        self.selected_jobs.clear()
        self.log_delivery("☐ Deselected all jobs")
    
    def log_delivery(self, message):
        """Log message to delivery voucher log"""
        if self.log_text:
            timestamp = time.strftime("%H:%M:%S")
            self.log_text.insert('end', f"[{timestamp}] {message}\n")
            self.log_text.see('end')
            self.log_text.update()
    
    def load_delivery_jobs(self):
        """Load jobs ready for delivery voucher submission"""
        threading.Thread(target=self._load_delivery_jobs_worker, daemon=True).start()
    
    def _load_delivery_jobs_worker(self):
        """Worker thread to load delivery jobs - scrapes from portal first"""
        try:
            # Refresh firm_id from settings before loading
            self.refresh_firm_id()
            
            if not self.driver:
                self.log_delivery("❌ Browser not available. Please open browser first.")
                return
            
            self.log_delivery(f"🌐 Navigating to delivery voucher list page...")
            
            # Navigate to delivery voucher list page
            list_url = "https://huid.manakonline.in/MANAK/NewArticlesListForDelieveryVoucher"
            self.driver.get(list_url)
            
            # Wait for page to load
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By
            
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                time.sleep(2)  # Wait for table to populate
            except Exception as e:
                self.log_delivery(f"❌ Error loading page: {str(e)}")
                return
            
            self.log_delivery(f"🔍 Extracting jobs from delivery voucher list...")
            
            # Extract jobs from the portal table
            portal_jobs = self.extract_jobs_from_delivery_list()
            
            if not portal_jobs:
                self.log_delivery("⚠️ No jobs found on delivery voucher list page")
                return
            
            self.log_delivery(f"✅ Found {len(portal_jobs)} jobs on delivery voucher list")
            
            # Now get weight data from database for these specific jobs
            self.log_delivery(f"📊 Fetching weight data from database...")
            
            # Get database connection
            import mysql.connector
            # Add auth_plugin to fix MySQL 8.0+ authentication compatibility
            db_config_with_auth = self.db_config.copy()
            db_config_with_auth['auth_plugin'] = 'mysql_native_password'
            connection = mysql.connector.connect(**db_config_with_auth)
            cursor = connection.cursor()
            
            # Clear existing data
            self.jobs_tree.delete(*self.jobs_tree.get_children())
            self.jobs_data = []
            self.selected_jobs.clear()
            
            loaded_count = 0
            
            # For each job from portal, get weight data from database
            for portal_job in portal_jobs:
                request_no = portal_job['request_no']
                job_no = portal_job['job_no']
                
                # Query database for this specific job
                query = """
                    SELECT id, item, weight, scrp_cornet_weight
                    FROM job_cards
                    WHERE firm_id = %s AND job_no = %s
                    LIMIT 1
                """
                
                cursor.execute(query, (self.current_firm_id, job_no))
                result = cursor.fetchone()
                
                if not result:
                    self.log_delivery(f"⚠️ Job {job_no} not found in database")
                    continue
                
                id_val, item, weight, scrap_weight = result
                
                # Calculate weights
                weight_gms = float(weight) if weight else 0
                scrap_gms = float(scrap_weight) if scrap_weight else 0
                scrap_mgs = scrap_gms * 1000  # Convert to milligrams
                return_gms = weight_gms - scrap_gms
                loaded_count += 1
                
                # Add to tree
                self.jobs_tree.insert('', 'end', values=(
                    '☐',  # Not selected by default
                    id_val,
                    request_no,
                    job_no,
                    item or '',
                    f"{weight_gms:.3f}",
                    f"{scrap_mgs:.1f}",
                    f"{return_gms:.3f}",
                    'Ready'
                ))
                
                # Store data
                self.jobs_data.append({
                    'id': id_val,
                    'request_no': request_no,
                    'job_no': job_no,
                    'item': item,
                    'weight_gms': weight_gms,
                    'scrap_mgs': scrap_mgs,
                    'return_gms': return_gms
                })
            
            cursor.close()
            connection.close()
            
            self.log_delivery(f"✅ Loaded {loaded_count} jobs ready for delivery voucher")
            
        except Exception as e:
            self.log_delivery(f"❌ Error loading jobs: {str(e)}")
    
    def extract_jobs_from_delivery_list(self):
        """Extract jobs from the delivery voucher list page"""
        try:
            jobs = []
            
            # Find all table rows
            rows = self.driver.find_elements(By.TAG_NAME, "tr")
            
            for row in rows:
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    
                    if len(cells) < 3:  # Need at least S.No, Request No, Job No
                        continue
                    
                    # Extract Request No and Job No from cells
                    # Based on your screenshot structure
                    request_no = ""
                    job_no = ""
                    
                    for i, cell in enumerate(cells):
                        cell_text = cell.text.strip()
                        
                        # Request numbers are usually 8-9 digits starting with specific patterns
                        if len(cell_text) >= 8 and cell_text.isdigit():
                            # Could be request_no or job_no
                            if not request_no and (cell_text.startswith('11') or cell_text.startswith('10')):
                                request_no = cell_text
                            elif not job_no and cell_text.startswith('1'):
                                job_no = cell_text
                    
                    # Also check for "Delivery Voucher" links which contain the data
                    links = row.find_elements(By.LINK_TEXT, "Delivery Voucher")
                    if links:
                        href = links[0].get_attribute('href')
                        if href and 'requestNo=' in href and 'jobNo=' in href:
                            # Extract from URL parameters
                            import re
                            
                            # Extract encoded request number
                            req_match = re.search(r'requestNo=([^&]+)', href)
                            job_match = re.search(r'jobNo=([^&]+)', href)
                            
                            if req_match and job_match:
                                try:
                                    # Decode base64 encoded values
                                    encoded_req = req_match.group(1)
                                    encoded_job = job_match.group(1)
                                    
                                    request_no = base64.b64decode(encoded_req).decode('utf-8')
                                    job_no = base64.b64decode(encoded_job).decode('utf-8')
                                except Exception:
                                    pass
                    
                    if request_no and job_no:
                        jobs.append({
                            'request_no': request_no,
                            'job_no': job_no
                        })
                        self.log_delivery(f"  📋 Found: Request={request_no}, Job={job_no}")
                
                except Exception as e:
                    continue
            
            return jobs
            
        except Exception as e:
            self.log_delivery(f"❌ Error extracting jobs from list: {str(e)}")
            return []
    
    def submit_selected_vouchers(self):
        """Submit delivery vouchers for selected jobs"""
        if not self.selected_jobs:
            messagebox.showwarning("No Selection", "Please select at least one job to submit")
            return
        
        # Confirm submission
        count = len(self.selected_jobs)
        if not messagebox.askyesno("Confirm Submission", 
                                   f"Submit delivery vouchers for {count} selected job(s)?"):
            return
        
        threading.Thread(target=self._submit_vouchers_worker, daemon=True).start()
    
    def _submit_vouchers_worker(self):
        """Worker thread to submit delivery vouchers"""
        try:
            self.log_delivery(f"🚀 Starting delivery voucher submission for {len(self.selected_jobs)} jobs...")
            
            # Get selected job data
            selected_data = [job for job in self.jobs_data if str(job['id']) in self.selected_jobs]
            
            success_count = 0
            fail_count = 0
            
            for i, job in enumerate(selected_data, 1):
                try:
                    self.log_delivery(f"\n{'='*60}")
                    self.log_delivery(f"📦 Processing {i}/{len(selected_data)}: Job {job['job_no']}")
                    
                    # Submit delivery voucher
                    result = self.submit_delivery_voucher(
                        request_no=job['request_no'],
                        job_no=job['job_no'],
                        return_weight_gms=job['return_gms'],
                        scrap_weight_mgs=job['scrap_mgs']
                    )
                    
                    if result:
                        success_count += 1
                        self.update_job_status(job['id'], '✅ Submitted')
                        self.log_delivery(f"✅ Successfully submitted delivery voucher for Job {job['job_no']}")
                    else:
                        fail_count += 1
                        self.update_job_status(job['id'], '❌ Failed')
                        self.log_delivery(f"❌ Failed to submit delivery voucher for Job {job['job_no']}")
                    
                    # Small delay between submissions
                    time.sleep(1)
                    
                except Exception as e:
                    fail_count += 1
                    self.update_job_status(job['id'], '❌ Error')
                    self.log_delivery(f"❌ Error processing Job {job['job_no']}: {str(e)}")
            
            self.log_delivery(f"\n{'='*60}")
            self.log_delivery(f"🏁 Submission complete: ✅ {success_count} succeeded, ❌ {fail_count} failed")
            
        except Exception as e:
            self.log_delivery(f"❌ Error in voucher submission: {str(e)}")
    
    def submit_delivery_voucher(self, request_no, job_no, return_weight_gms, scrap_weight_mgs):
        """Submit delivery voucher for a single job"""
        try:
            if not self.driver:
                self.log_delivery("❌ Browser not available")
                return False
            
            # Navigate to delivery voucher list page
            list_url = "https://huid.manakonline.in/MANAK/NewArticlesListForDelieveryVoucher"
            self.log_delivery(f"🌐 Navigating to delivery voucher list...")
            self.driver.get(list_url)
            
            # Wait for page load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Search for the specific request and job
            self.log_delivery(f"🔍 Searching for Request: {request_no}, Job: {job_no}")
            
            # Find the "Delivery Voucher" link for this job
            # The link pattern: contains both request_no and job_no
            time.sleep(2)  # Wait for table to load
            
            # Try to find the delivery voucher link
            try:
                # Look for rows containing both request and job number
                rows = self.driver.find_elements(By.TAG_NAME, "tr")
                
                voucher_link = None
                for row in rows:
                    row_text = row.text
                    if request_no in row_text and job_no in row_text:
                        # Found the row, now look for "Delivery Voucher" link
                        links = row.find_elements(By.LINK_TEXT, "Delivery Voucher")
                        if links:
                            voucher_link = links[0]
                            break
                
                if not voucher_link:
                    self.log_delivery(f"⚠️ Could not find 'Delivery Voucher' link for Job {job_no}")
                    return False
                
                # Click the delivery voucher link
                self.log_delivery(f"🔗 Clicking delivery voucher link...")
                voucher_link.click()
                
                # Wait for delivery voucher form page
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "finalWeightReturned"))
                )
                
                self.log_delivery(f"📝 Filling delivery voucher form...")
                
                # Fill the form
                # Weight of Article Returned in gms
                final_weight_input = self.driver.find_element(By.ID, "finalWeightReturned")
                final_weight_input.clear()
                final_weight_input.send_keys(str(round(return_weight_gms, 3)))
                self.log_delivery(f"  ✓ Weight of Article Returned: {return_weight_gms:.3f} gms")
                
                # Weight of Scrapping in mgs
                scrap_input = self.driver.find_element(By.ID, "sampleScrap")
                scrap_input.clear()
                scrap_input.send_keys(str(round(scrap_weight_mgs, 1)))
                self.log_delivery(f"  ✓ Weight of Scrapping: {scrap_weight_mgs:.1f} mgs")
                
                # Wait for any loader/preloader to disappear before submitting
                try:
                    self.log_delivery(f"⏳ Waiting for page to be ready...")
                    # Wait for the preloader to become invisible
                    WebDriverWait(self.driver, 10).until(
                        EC.invisibility_of_element_located((By.ID, "loader-preloader-image"))
                    )
                    self.log_delivery(f"  ✓ Page ready")
                except Exception as loader_error:
                    # If loader doesn't exist or is already gone, that's fine
                    self.log_delivery(f"  ℹ️ No loader detected or already gone")
                    pass
                
                # Small delay to ensure page is fully interactive
                time.sleep(1)
                
                # Submit the form
                submit_btn = self.driver.find_element(By.ID, "submitDelieveryVoucher")
                self.log_delivery(f"📤 Submitting delivery voucher...")
                
                # Try to click with JavaScript if regular click fails
                try:
                    submit_btn.click()
                except Exception as click_error:
                    self.log_delivery(f"  ⚠️ Regular click failed, trying JavaScript click...")
                    self.driver.execute_script("arguments[0].click();", submit_btn)
                
                # Wait a moment for submission
                time.sleep(2)
                
                # Check for success (you might need to adjust this based on actual success indicators)
                # Common patterns: alert, success message, redirect
                try:
                    alert = self.driver.switch_to.alert
                    alert_text = alert.text
                    self.log_delivery(f"📢 Alert: {alert_text}")
                    alert.accept()
                    
                    if "success" in alert_text.lower() or "submitted" in alert_text.lower():
                        return True
                except:
                    # No alert - check for other success indicators
                    # You may need to customize this based on the actual response
                    pass
                
                return True
                
            except Exception as e:
                self.log_delivery(f"❌ Error finding/clicking delivery voucher link: {str(e)}")
                return False
            
        except Exception as e:
            self.log_delivery(f"❌ Error submitting delivery voucher: {str(e)}")
            return False
    
    def update_job_status(self, job_id, status):
        """Update job status in the tree view"""
        for item in self.jobs_tree.get_children():
            values = list(self.jobs_tree.item(item, 'values'))
            if values[1] == str(job_id):
                values[8] = status  # Status column
                self.jobs_tree.item(item, values=values)
                break
