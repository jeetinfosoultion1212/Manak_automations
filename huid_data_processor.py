#!/usr/bin/env python3
"""
HUID Data Processor Module
Handles automated extraction and submission of HUID data from weight forms
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import requests
import json
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class HUIDDataProcessor:
    """Handles HUID data extraction and submission functionality"""
    
    def __init__(self, driver, log_callback, license_check_callback):
        self.driver = driver
        self.log = log_callback
        self.check_license_before_action = license_check_callback
        self.api_base_url = "https://hallmarkpro.prosenjittechhub.com/admin"
        self.articles_url = "https://huid.manakonline.in/MANAK/NewArticlesListForWeighing"
        self.extracted_data = []
        
        # Auto monitoring variables
        self.is_monitoring = False
        self.monitor_thread = None
        self.processed_jobs = set()  # Track processed jobs to avoid duplicates
        
    def setup_huid_data_tab(self, notebook):
        """Setup HUID Data Processing tab"""
        self.notebook = notebook
        huid_data_frame = ttk.Frame(notebook)
        notebook.add(huid_data_frame, text="📊 HUID Data")
        
        # Main horizontal layout
        main_horizontal = ttk.Frame(huid_data_frame)
        main_horizontal.pack(fill='both', expand=True, padx=8, pady=8)
        
        # Left panel for controls
        left_panel = ttk.Frame(main_horizontal)
        left_panel.pack(side='left', fill='y', padx=(0, 8))
        left_panel.configure(width=320)
        
        # Right panel for data display
        right_panel = ttk.Frame(main_horizontal)
        right_panel.pack(side='right', fill='both', expand=True)
        
        self.setup_control_panel(left_panel)
        self.setup_data_display(right_panel)
        
    def setup_control_panel(self, parent):
        """Setup the control panel with automation options"""
        
        # Main control card
        control_card = ttk.LabelFrame(parent, text="🎯 HUID Data Extraction", style='Compact.TLabelframe')
        control_card.pack(fill='x', pady=(0, 8))
        
        # Compact header
        header_frame = ttk.Frame(control_card)
        header_frame.pack(fill='x', padx=10, pady=(8, 4))
        
        ttk.Label(header_frame, text="🎯 Automated HUID Data Extraction", 
                 font=('TkDefaultFont', 10, 'bold')).pack(anchor='w')
        
        # API URL (hidden by default)
        api_frame = ttk.Frame(control_card)
        api_frame.pack(fill='x', padx=10, pady=(0, 8))
        
        self.api_url_label = ttk.Label(api_frame, text="API URL:")
        self.api_url_entry = ttk.Entry(api_frame, width=30)
        self.api_url_entry.insert(0, f"{self.api_base_url}/submit_huid_data.php")
        
        # Initially hide the API URL
        self.api_url_visible = False
        self.api_url_label.pack_forget()
        self.api_url_entry.pack_forget()
        
        # Add hint for API URL shortcut
        shortcut_hint = ttk.Label(api_frame, text="💡 Press Shift+H to show/hide API URL", 
                                font=('TkDefaultFont', 8), foreground='#6c757d')
        shortcut_hint.pack(anchor='w', pady=(0, 4))
        
        # Add keyboard shortcut for Shift+H
        self.setup_api_url_shortcut()
        
        # Automation settings
        settings_card = ttk.LabelFrame(parent, text="⚙️ Automation Settings", style='Compact.TLabelframe')
        settings_card.pack(fill='x', pady=(0, 6))
        
        settings_frame = ttk.Frame(settings_card)
        settings_frame.pack(fill='x', padx=10, pady=6)
        
        # Auto pagination
        self.auto_pagination_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_frame, text="Auto handle pagination (100+ records)", 
                       variable=self.auto_pagination_var).pack(anchor='w', pady=(0, 4))
        
        # Delay between pages
        delay_frame = ttk.Frame(settings_frame)
        delay_frame.pack(fill='x', pady=(0, 4))
        ttk.Label(delay_frame, text="Delay between pages (seconds):").pack(side='left')
        self.page_delay_var = tk.StringVar(value="2")
        delay_entry = ttk.Entry(delay_frame, textvariable=self.page_delay_var, width=5)
        delay_entry.pack(side='right')
        
        # Auto submit
        self.auto_submit_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_frame, text="Auto submit extracted data", 
                       variable=self.auto_submit_var).pack(anchor='w', pady=(0, 4))
        
        # Auto monitoring settings
        monitor_frame = ttk.LabelFrame(parent, text="🤖 Auto Monitoring", style='Compact.TLabelframe')
        monitor_frame.pack(fill='x', pady=(0, 6))
        
        monitor_settings_frame = ttk.Frame(monitor_frame)
        monitor_settings_frame.pack(fill='x', padx=10, pady=6)
        
        # Monitoring interval
        interval_frame = ttk.Frame(monitor_settings_frame)
        interval_frame.pack(fill='x', pady=(0, 4))
        ttk.Label(interval_frame, text="Check interval (minutes):").pack(side='left')
        self.monitor_interval_var = tk.StringVar(value="5")
        interval_entry = ttk.Entry(interval_frame, textvariable=self.monitor_interval_var, width=5)
        interval_entry.pack(side='right')
        
        # Auto start monitoring
        self.auto_start_monitor_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(monitor_settings_frame, text="Start monitoring automatically on app startup", 
                       variable=self.auto_start_monitor_var).pack(anchor='w', pady=(0, 4))
        
        # Only process new jobs
        self.only_new_jobs_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(monitor_settings_frame, text="Only process new jobs (skip already processed)", 
                       variable=self.only_new_jobs_var).pack(anchor='w', pady=(0, 4))
        
        # Action buttons
        action_card = ttk.LabelFrame(parent, text="🚀 Actions", style='Compact.TLabelframe')
        action_card.pack(fill='x', pady=(0, 6))
        
        action_frame = ttk.Frame(action_card)
        action_frame.pack(fill='x', padx=10, pady=6)
        
        # Manual extraction button
        extract_btn = ttk.Button(action_frame, text="🔍 Manual Extract", 
                               command=self.extract_huid_data,
                               style='Action.TButton')
        extract_btn.pack(fill='x', pady=(0, 4))
        
        # Auto monitoring button
        self.auto_monitor_btn = ttk.Button(action_frame, text="🤖 Start Auto Monitor", 
                                         command=self.toggle_auto_monitoring,
                                         style='Success.TButton')
        self.auto_monitor_btn.pack(fill='x', pady=(0, 4))
        
        # Submit button
        submit_btn = ttk.Button(action_frame, text="📤 Submit to Database", 
                              command=self.submit_huid_data,
                              style='Warning.TButton')
        submit_btn.pack(fill='x', pady=(0, 4))
        
        # Clear button
        clear_btn = ttk.Button(action_frame, text="🗑️ Clear Data", 
                             command=self.clear_extracted_data,
                             style='Danger.TButton')
        clear_btn.pack(fill='x', pady=(0, 0))
        
        # Status display
        status_card = ttk.LabelFrame(parent, text="📊 Status", style='Compact.TLabelframe')
        status_card.pack(fill='x', pady=(0, 6))
        
        status_frame = ttk.Frame(status_card)
        status_frame.pack(fill='x', padx=10, pady=6)
        
        self.status_label = ttk.Label(status_frame, text="Ready", foreground='#6c757d')
        self.status_label.pack(anchor='w', pady=(0, 2))
        
        self.progress_label = ttk.Label(status_frame, text="No data extracted", foreground='#6c757d')
        self.progress_label.pack(anchor='w', pady=(0, 2))
        
        self.results_label = ttk.Label(status_frame, text="", foreground='#28a745')
        self.results_label.pack(anchor='w', pady=(0, 0))
        
    def setup_data_display(self, parent):
        """Setup the data display panel"""
        
        # Data display card
        data_card = ttk.LabelFrame(parent, text="📋 Extracted HUID Data", style='Compact.TLabelframe')
        data_card.pack(fill='both', expand=True)
        
        # Create treeview for data display
        columns = ('S.No', 'AHC Tag', 'Job No', 'Request No', 'HUID Code', 'Material', 'Item', 'Weight', 'Status')
        self.data_tree = ttk.Treeview(data_card, columns=columns, show='headings', height=15)
        
        # Configure columns
        self.data_tree.heading('S.No', text='S.No')
        self.data_tree.heading('AHC Tag', text='AHC Tag')
        self.data_tree.heading('Job No', text='Job No')
        self.data_tree.heading('Request No', text='Request No')
        self.data_tree.heading('HUID Code', text='HUID Code')
        self.data_tree.heading('Material', text='Material')
        self.data_tree.heading('Item', text='Item')
        self.data_tree.heading('Weight', text='Weight (gms)')
        self.data_tree.heading('Status', text='Status')
        
        # Configure column widths
        self.data_tree.column('S.No', width=50)
        self.data_tree.column('AHC Tag', width=70)
        self.data_tree.column('Job No', width=80)
        self.data_tree.column('Request No', width=100)
        self.data_tree.column('HUID Code', width=100)
        self.data_tree.column('Material', width=80)
        self.data_tree.column('Item', width=80)
        self.data_tree.column('Weight', width=80)
        self.data_tree.column('Status', width=80)
        
        # Add scrollbars
        v_scrollbar = ttk.Scrollbar(data_card, orient='vertical', command=self.data_tree.yview)
        h_scrollbar = ttk.Scrollbar(data_card, orient='horizontal', command=self.data_tree.xview)
        self.data_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack treeview and scrollbars
        self.data_tree.pack(side='left', fill='both', expand=True, padx=(10, 0), pady=10)
        v_scrollbar.pack(side='right', fill='y', padx=(0, 10), pady=10)
        h_scrollbar.pack(side='bottom', fill='x', padx=(10, 10), pady=(0, 10))
        
        # Log area
        log_card = ttk.LabelFrame(parent, text="📝 Processing Log", style='Compact.TLabelframe')
        log_card.pack(fill='x', pady=(8, 0))
        
        log_frame = ttk.Frame(log_card)
        log_frame.pack(fill='both', expand=True, padx=10, pady=8)
        
        self.log_text = tk.Text(log_frame, height=6, wrap='word', font=('Consolas', 9))
        log_scrollbar = ttk.Scrollbar(log_frame, orient='vertical', command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side='left', fill='both', expand=True, padx=(0, 0), pady=0)
        log_scrollbar.pack(side='right', fill='y', padx=(0, 0), pady=0)
        
        # Auto-start monitoring if enabled
        self.notebook.winfo_toplevel().after(5000, self.check_auto_start)  # Check after 5 seconds
    
    def setup_api_url_shortcut(self):
        """Setup Shift+H keyboard shortcut to toggle API URL visibility"""
        try:
            # Get the root window from the notebook
            root = self.notebook.winfo_toplevel()
            
            # Bind Shift+H to toggle API URL visibility
            root.bind('<Shift-h>', self.toggle_api_url_visibility)
            root.bind('<Shift-H>', self.toggle_api_url_visibility)
            
            self.log_message("⌨️ API URL hidden by default. Press Shift+H to toggle visibility", 'huid_data')
            
        except Exception as e:
            self.log(f"⚠️ Could not setup API URL shortcut: {str(e)}", 'huid_data')
    
    def toggle_api_url_visibility(self, event=None):
        """Toggle API URL field visibility"""
        try:
            if self.api_url_visible:
                # Hide API URL
                self.api_url_label.pack_forget()
                self.api_url_entry.pack_forget()
                self.api_url_visible = False
                self.log_message("🔒 API URL hidden (Press Shift+H to show)", 'huid_data')
            else:
                # Show API URL
                self.api_url_label.pack(anchor='w')
                self.api_url_entry.pack(fill='x', pady=(2, 8))
                self.api_url_visible = True
                self.log_message("🔓 API URL visible (Press Shift+H to hide)", 'huid_data')
                
        except Exception as e:
            self.log_message(f"❌ Error toggling API URL visibility: {str(e)}", 'huid_data')
    
    def extract_huid_data(self):
        """Extract HUID data from the articles list page"""
        # Check license before automation
        if not self.check_license_before_action("HUID data extraction"):
            return
        
        try:
            # Use hardcoded URL
            articles_url = self.articles_url
            
            # Check if browser is ready
            if not self.driver:
                messagebox.showwarning("Not Ready", "Please open browser and login first")
                return
            
            # Start extraction in background thread
            threading.Thread(
                target=self._extract_huid_data_worker, 
                args=(articles_url,), 
                daemon=True
            ).start()
            
        except Exception as e:
            self.log_message(f"❌ Error starting HUID data extraction: {str(e)}", 'huid_data')
            messagebox.showerror("Error", f"Error starting extraction: {str(e)}")
    
    def _extract_huid_data_worker(self, articles_url):
        """Worker thread for extracting HUID data"""
        try:
            self.update_status("Starting extraction...", '#ffc107')
            self.log_message(f"🔍 Starting HUID data extraction from: {articles_url}", 'huid_data')
            
            # Navigate to articles list page
            self.driver.get(articles_url)
            time.sleep(3)
            
            # Clear previous data
            self.extracted_data = []
            self.clear_treeview()
            
            # Extract data from all pages
            page_count = 0
            total_extracted = 0
            
            while True:
                page_count += 1
                self.log_message(f"📄 Processing page {page_count}...", 'huid_data')
                self.update_progress(f"Processing page {page_count}")
                
                # Extract data from current page
                page_data = self._extract_page_data()
                if page_data:
                    self.extracted_data.extend(page_data)
                    total_extracted += len(page_data)
                    self.log_message(f"✅ Extracted {len(page_data)} records from page {page_count}", 'huid_data')
                    
                    # Update treeview
                    self.update_treeview(page_data)
                else:
                    self.log_message(f"⚠️ No data found on page {page_count}", 'huid_data')
                
                # Check if there's a next page
                if not self.auto_pagination_var.get():
                    break
                    
                if not self._go_to_next_page():
                    break
                
                # Delay between pages
                delay = int(self.page_delay_var.get())
                if delay > 0:
                    time.sleep(delay)
            
            # Show final results
            self.update_status("Extraction Complete", '#28a745')
            self.update_progress(f"Extracted {total_extracted} records from {page_count} pages")
            self.update_results(f"✅ Total extracted: {total_extracted} records")
            
            # Auto submit if enabled
            if self.auto_submit_var.get() and self.extracted_data:
                self.log_message("📤 Auto-submitting extracted data...", 'huid_data')
                self.submit_huid_data()
            
            messagebox.showinfo(
                "Extraction Complete",
                f"✅ Successfully extracted: {total_extracted} HUID records\n📄 Processed: {page_count} pages"
            )
            
        except Exception as e:
            self.update_status("Error", '#dc3545')
            self.log_message(f"❌ Error in HUID data extraction: {str(e)}", 'huid_data')
            messagebox.showerror("Error", f"Error in extraction: {str(e)}")
    
    def _extract_page_data(self):
        """Extract HUID data from current page"""
        try:
            page_data = []
            
            # Wait for table to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            
            # Find all table rows (skip header)
            rows = self.driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
            
            for row in rows:
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 6:  # Ensure we have enough columns
                        
                        # Extract data from cells
                        s_no = cells[0].text.strip() if len(cells) > 0 else ""
                        ahc_tag = cells[1].text.strip() if len(cells) > 1 else ""
                        material = cells[2].text.strip() if len(cells) > 2 else ""
                        item = cells[3].text.strip() if len(cells) > 3 else ""
                        huid_code = cells[4].text.strip() if len(cells) > 4 else ""
                        weight = cells[5].text.strip() if len(cells) > 5 else ""
                        
                        # Only include records with filled weights
                        if weight and weight != "Enter weight" and weight.replace('.', '').isdigit():
                            huid_record = {
                                'job_id': ahc_tag,  # Using AHC Tag as job_id
                                'job_no': ahc_tag,  # Using AHC Tag as job_no
                                'request_no': self._extract_request_no_from_url(),
                                'purity': material,
                                'serial_no': s_no,
                                'tag_no': ahc_tag,  # Using AHC Tag as tag_no
                                'material': material,
                                'item': item,
                                'huid_code': huid_code,
                                'weight': float(weight) if weight else 0.0,
                                'date_added': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'image_path': '',
                                'pair_id': huid_code,  # Store HUID code in pair_id as requested
                                'firm_id': '1',  # Default firm ID
                                'party_id': '1',  # Default party ID
                                'remarks': f'Extracted from page {len(page_data) + 1}',
                                'ahc_tag': ahc_tag  # Add AHC Tag for display
                            }
                            
                            page_data.append(huid_record)
                            self.log_message(f"📊 Extracted: {huid_code} - {weight}g ({item})", 'huid_data')
                
                except Exception as e:
                    self.log_message(f"⚠️ Error extracting row data: {str(e)}", 'huid_data')
                    continue
            
            return page_data
            
        except Exception as e:
            self.log_message(f"❌ Error extracting page data: {str(e)}", 'huid_data')
            return []
    
    def _extract_request_no_from_url(self):
        """Extract request number from current URL"""
        try:
            current_url = self.driver.current_url
            if 'requestNo=' in current_url:
                start = current_url.find('requestNo=') + len('requestNo=')
                end = current_url.find('&', start)
                if end == -1:
                    end = len(current_url)
                return current_url[start:end]
            return ""
        except:
            return ""
    
    def _go_to_next_page(self):
        """Navigate to next page if available"""
        try:
            # Look for "Next" button
            next_buttons = self.driver.find_elements(By.XPATH, "//a[contains(text(), 'Next')]")
            for button in next_buttons:
                if button.is_enabled() and button.is_displayed():
                    button.click()
                    time.sleep(2)
                    return True
            
            # Look for pagination numbers
            page_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='page']")
            if page_links:
                # Find the next page number
                current_page = 1
                for link in page_links:
                    if link.text.isdigit():
                        page_num = int(link.text)
                        if page_num > current_page:
                            link.click()
                            time.sleep(2)
                            return True
            
            return False
            
        except Exception as e:
            self.log_message(f"⚠️ Error navigating to next page: {str(e)}", 'huid_data')
            return False
    
    def submit_huid_data(self):
        """Submit extracted HUID data to database"""
        if not self.extracted_data:
            messagebox.showwarning("No Data", "No HUID data to submit. Please extract data first.")
            return
        
        try:
            # Get API URL
            api_url = self.api_url_entry.get().strip()
            if not api_url:
                messagebox.showwarning("Validation Error", "Please enter API URL")
                return
            
            # Start submission in background thread
            threading.Thread(
                target=self._submit_huid_data_worker, 
                args=(api_url,), 
                daemon=True
            ).start()
            
        except Exception as e:
            self.log_message(f"❌ Error starting HUID data submission: {str(e)}", 'huid_data')
            messagebox.showerror("Error", f"Error starting submission: {str(e)}")
    
    def _submit_huid_data_worker(self, api_url):
        """Worker thread for submitting HUID data"""
        try:
            self.update_status("Submitting data...", '#007bff')
            self.log_message(f"📤 Submitting {len(self.extracted_data)} HUID records to database", 'huid_data')
            
            # Prepare payload
            payload = {
                'action': 'submit_huid_data',
                'data': self.extracted_data
            }
            
            # Send to API
            response = requests.post(api_url, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    self.update_status("Submission Complete", '#28a745')
                    self.update_results(f"✅ Successfully submitted {len(self.extracted_data)} records")
                    self.log_message(f"✅ Successfully submitted {len(self.extracted_data)} HUID records", 'huid_data')
                    
                    messagebox.showinfo(
                        "Submission Complete",
                        f"✅ Successfully submitted {len(self.extracted_data)} HUID records to database"
                    )
                else:
                    error_msg = result.get('error', 'Unknown error')
                    self.update_status("Submission Failed", '#dc3545')
                    self.log_message(f"❌ Submission failed: {error_msg}", 'huid_data')
                    messagebox.showerror("Submission Failed", f"API Error: {error_msg}")
            else:
                self.update_status("Submission Failed", '#dc3545')
                self.log_message(f"❌ HTTP Error: {response.status_code}", 'huid_data')
                messagebox.showerror("Submission Failed", f"HTTP Error: {response.status_code}")
                
        except Exception as e:
            self.update_status("Submission Error", '#dc3545')
            self.log_message(f"❌ Error submitting HUID data: {str(e)}", 'huid_data')
            messagebox.showerror("Error", f"Error in submission: {str(e)}")
    
    def clear_extracted_data(self):
        """Clear all extracted data"""
        self.extracted_data = []
        self.clear_treeview()
        self.update_status("Ready", '#6c757d')
        self.update_progress("No data extracted")
        self.update_results("")
        self.log_message("🗑️ Cleared all extracted data", 'huid_data')
    
    def toggle_auto_monitoring(self):
        """Toggle automatic monitoring on/off"""
        if self.is_monitoring:
            self.stop_auto_monitoring()
        else:
            self.start_auto_monitoring()
    
    def start_auto_monitoring(self):
        """Start automatic monitoring"""
        # Check license before automation
        if not self.check_license_before_action("auto HUID monitoring"):
            return
        
        try:
            # Use hardcoded URL
            articles_url = self.articles_url
            
            # Check if browser is ready
            if not self.driver:
                messagebox.showwarning("Not Ready", "Please open browser and login first")
                return
            
            # Start monitoring
            self.is_monitoring = True
            self.auto_monitor_btn.config(text="🛑 Stop Auto Monitor", style='Danger.TButton')
            self.update_status("Auto Monitoring Active", '#28a745')
            
            # Start monitoring thread
            self.monitor_thread = threading.Thread(
                target=self._auto_monitor_worker, 
                args=(articles_url,), 
                daemon=True
            )
            self.monitor_thread.start()
            
            self.log_message("🤖 Auto monitoring started", 'huid_data')
            
        except Exception as e:
            self.log_message(f"❌ Error starting auto monitoring: {str(e)}", 'huid_data')
            messagebox.showerror("Error", f"Error starting monitoring: {str(e)}")
    
    def stop_auto_monitoring(self):
        """Stop automatic monitoring"""
        self.is_monitoring = False
        self.auto_monitor_btn.config(text="🤖 Start Auto Monitor", style='Success.TButton')
        self.update_status("Auto Monitoring Stopped", '#6c757d')
        self.log_message("🛑 Auto monitoring stopped", 'huid_data')
    
    def _auto_monitor_worker(self, articles_url):
        """Worker thread for automatic monitoring"""
        try:
            interval_minutes = int(self.monitor_interval_var.get())
            interval_seconds = interval_minutes * 60
            
            self.log_message(f"🤖 Auto monitoring started - checking every {interval_minutes} minutes", 'huid_data')
            
            while self.is_monitoring:
                try:
                    self.log_message("🔍 Checking for new jobs with filled weights...", 'huid_data')
                    
                    # Navigate to articles list page
                    self.driver.get(articles_url)
                    time.sleep(3)
                    
                    # Extract data from current page
                    page_data = self._extract_page_data()
                    
                    if page_data:
                        # Filter out already processed jobs if enabled
                        if self.only_new_jobs_var.get():
                            new_data = []
                            for record in page_data:
                                job_key = f"{record['job_no']}_{record['huid_code']}"
                                if job_key not in self.processed_jobs:
                                    new_data.append(record)
                                    self.processed_jobs.add(job_key)
                            
                            if new_data:
                                self.extracted_data.extend(new_data)
                                self.update_treeview(new_data)
                                self.log_message(f"📊 Found {len(new_data)} new records with filled weights", 'huid_data')
                                
                                # Auto submit if enabled
                                if self.auto_submit_var.get():
                                    self.log_message("📤 Auto-submitting new data...", 'huid_data')
                                    self._submit_huid_data_worker(self.api_url_entry.get().strip())
                            else:
                                self.log_message("ℹ️ No new jobs found", 'huid_data')
                        else:
                            # Process all data
                            self.extracted_data.extend(page_data)
                            self.update_treeview(page_data)
                            self.log_message(f"📊 Found {len(page_data)} records with filled weights", 'huid_data')
                            
                            # Auto submit if enabled
                            if self.auto_submit_var.get():
                                self.log_message("📤 Auto-submitting data...", 'huid_data')
                                self._submit_huid_data_worker(self.api_url_entry.get().strip())
                    else:
                        self.log_message("ℹ️ No jobs with filled weights found", 'huid_data')
                    
                    # Wait for next check
                    if self.is_monitoring:
                        self.log_message(f"⏰ Waiting {interval_minutes} minutes for next check...", 'huid_data')
                        for _ in range(interval_seconds):
                            if not self.is_monitoring:
                                break
                            time.sleep(1)
                
                except Exception as e:
                    self.log_message(f"⚠️ Error during monitoring cycle: {str(e)}", 'huid_data')
                    if self.is_monitoring:
                        time.sleep(30)  # Wait 30 seconds before retrying
            
            self.log_message("🤖 Auto monitoring ended", 'huid_data')
            
        except Exception as e:
            self.log_message(f"❌ Error in auto monitoring: {str(e)}", 'huid_data')
            self.stop_auto_monitoring()
    
    def check_auto_start(self):
        """Check if auto-start monitoring is enabled and start it"""
        try:
            if (self.auto_start_monitor_var.get() and 
                not self.is_monitoring and 
                self.driver):
                
                self.log_message("🚀 Auto-starting monitoring...", 'huid_data')
                self.start_auto_monitoring()
        except Exception as e:
            self.log_message(f"⚠️ Error in auto-start check: {str(e)}", 'huid_data')
    
    def clear_treeview(self):
        """Clear the treeview data"""
        for item in self.data_tree.get_children():
            self.data_tree.delete(item)
    
    def update_treeview(self, data):
        """Update treeview with new data"""
        for record in data:
            self.data_tree.insert('', 'end', values=(
                record.get('serial_no', ''),
                record.get('ahc_tag', ''),
                record.get('job_no', ''),
                record.get('request_no', ''),
                record.get('huid_code', ''),
                record.get('material', ''),
                record.get('item', ''),
                record.get('weight', ''),
                'Extracted'
            ))
    
    def update_status(self, status, color='#6c757d'):
        """Update status label"""
        self.status_label.config(text=status, foreground=color)
    
    def update_progress(self, progress):
        """Update progress label"""
        self.progress_label.config(text=progress, foreground='#6c757d')
    
    def update_results(self, results):
        """Update results label"""
        self.results_label.config(text=results, foreground='#28a745')
    
    def log_message(self, message, category='huid_data'):
        """Log message to the log area"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_message = f"[{timestamp}] {message}\n"
        
        # Add to log text area
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
        
        # Also call the main log callback
        if hasattr(self, 'log') and callable(self.log):
            self.log(message, category)
