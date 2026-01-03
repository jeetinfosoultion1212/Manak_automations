#!/usr/bin/env python3
"""
Multiple Jobs Processor Module
Handles processing multiple jobs from a single report
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import time
import requests
import mysql.connector
from mysql.connector import Error
import base64
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys


class MultipleJobsProcessor:
    """Handles multiple job processing functionality"""
    
    def __init__(self, driver, log_callback, license_check_callback, main_app=None):
        self.driver = driver
        self.main_log_callback = log_callback  # Store external callback separately
        self.check_license_before_action = license_check_callback
        self.main_app = main_app  # Store reference to main app to access settings
        self.api_base_url = "https://your-api-domain.com"  # Update with your actual API URL
        self.notebook = None  # Will be set in setup_multiple_jobs_tab
        self.log_text = None  # Will be set when UI is created
        
        # Database connection details
        self.db_config = {
            'host': '217.21.85.154',
            'database': 'u176143338_hallmarkProver',
            'user': 'u176143338_hallmarkProver',
            'password': 'Rontik10@'
        }
        
        # Jobs card monitoring
        self.jobs_card_monitoring = False
        self.monitor_thread = None
    
    def setup_multiple_jobs_tab(self, notebook):
        """Setup Multiple Jobs Processing tab"""
        self.notebook = notebook  # Store notebook reference
        
        # Create Multiple Jobs tab
        multiple_jobs_frame = ttk.Frame(notebook)
        notebook.add(multiple_jobs_frame, text="🔄 Multiple Jobs")
        
        # Main horizontal layout
        main_horizontal = ttk.Frame(multiple_jobs_frame)
        main_horizontal.pack(fill='both', expand=True, padx=8, pady=8)
        
        # LEFT SECTION - Controls (30% width)
        left_section = ttk.Frame(main_horizontal)
        left_section.pack(side='left', fill='both', expand=True, padx=(0, 8))
        
        # RIGHT SECTION - Results (70% width)
        right_section = ttk.Frame(main_horizontal)
        right_section.pack(side='right', fill='both', expand=True, padx=(8, 0))
        
        # Setup left and right sections
        self.setup_multiple_jobs_left_section(left_section)
        self.setup_multiple_jobs_right_section(right_section)
        
        # Create Jobs Card List tab
        self.setup_jobs_card_list_tab(notebook)
    
    def setup_multiple_jobs_left_section(self, parent):
        """Setup left section with controls and settings"""
        
        # Report Processing Card
        report_card = ttk.LabelFrame(parent, text="📊 Report Processing", style='Compact.TLabelframe')
        report_card.pack(fill='x', pady=(0, 8))
        
        # Report ID input
        report_frame = ttk.Frame(report_card)
        report_frame.pack(fill='x', padx=10, pady=8)
        
        ttk.Label(report_frame, text="Report ID:").pack(anchor='w')
        self.report_id_entry = ttk.Entry(report_frame, width=20)
        self.report_id_entry.pack(fill='x', pady=(2, 8))
        
        # API URL is now managed in Settings page
        api_info = ttk.Label(report_frame, text="💡 API URL is configured in Settings page", 
                            font=('TkDefaultFont', 8), foreground='#6c757d')
        api_info.pack(anchor='w', pady=(0, 4))
        
        # Process buttons - Load data first, then save actions
        button_frame = ttk.Frame(report_frame)
        button_frame.pack(fill='x', pady=(8, 0))
        
        # Load Report Data button (should be clicked first)
        load_data_btn = ttk.Button(button_frame, text="📥 Load Report Data", 
                                 command=self.load_report_data,
                                 style='Info.TButton')
        load_data_btn.pack(fill='x', pady=(0, 4))
        
        # Separator
        separator = ttk.Separator(button_frame, orient='horizontal')
        separator.pack(fill='x', pady=4)
        
        # Save action buttons (disabled until data is loaded)
        save_initial_btn = ttk.Button(button_frame, text="💾 Save Initial Weights", 
                                    command=self.save_initial_weights_multiple_jobs,
                                    style='Success.TButton',
                                    state='disabled')
        save_initial_btn.pack(fill='x', pady=(0, 4))
        self.save_initial_btn = save_initial_btn  # Store reference to enable/disable
        
        save_cornet_btn = ttk.Button(button_frame, text="⚖️ Save Cornet Weights", 
                                   command=self.save_cornet_weights_multiple_jobs,
                                   style='Warning.TButton',
                                   state='disabled')
        save_cornet_btn.pack(fill='x', pady=(0, 4))
        self.save_cornet_btn = save_cornet_btn  # Store reference to enable/disable
        
        process_all_btn = ttk.Button(button_frame, text="🔄 Process All Jobs", 
                                   command=self.process_multiple_jobs_from_report,
                                   style='Action.TButton',
                                   state='disabled')
        process_all_btn.pack(fill='x', pady=(0, 0))
        self.process_all_btn = process_all_btn  # Store reference to enable/disable
        
        # Settings Card
        settings_card = ttk.LabelFrame(parent, text="⚙️ Processing Settings", style='Compact.TLabelframe')
        settings_card.pack(fill='x', pady=(0, 8))
        
        settings_frame = ttk.Frame(settings_card)
        settings_frame.pack(fill='x', padx=10, pady=8)
        
        # Auto submit for HUID checkbox
        self.auto_submit_huid_var = tk.BooleanVar()
        auto_submit_check = ttk.Checkbutton(settings_frame, text="Auto Submit for HUID", 
                                          variable=self.auto_submit_huid_var)
        auto_submit_check.pack(anchor='w', pady=2)
        
        # Delay between jobs
        ttk.Label(settings_frame, text="Delay between jobs (seconds):").pack(anchor='w', pady=(8, 2))
        self.job_delay_var = tk.StringVar(value="2")
        delay_entry = ttk.Entry(settings_frame, textvariable=self.job_delay_var, width=10)
        delay_entry.pack(anchor='w', pady=(0, 8))
        
        # Status Card
        status_card = ttk.LabelFrame(parent, text="📈 Processing Status", style='Compact.TLabelframe')
        status_card.pack(fill='x', pady=(0, 8))
        
        status_frame = ttk.Frame(status_card)
        status_frame.pack(fill='x', padx=10, pady=8)
        
        # Status labels
        self.status_label = ttk.Label(status_frame, text="Ready", foreground='#28a745')
        self.status_label.pack(anchor='w')
        
        self.progress_label = ttk.Label(status_frame, text="No jobs processed")
        self.progress_label.pack(anchor='w', pady=(2, 0))
        
        # Results summary
        self.results_label = ttk.Label(status_frame, text="")
        self.results_label.pack(anchor='w', pady=(8, 0))
    
    def setup_multiple_jobs_right_section(self, parent):
        """Setup right section with job list and results"""
        
        # Job List Card
        jobs_card = ttk.LabelFrame(parent, text="📋 Jobs in Report", style='Compact.TLabelframe')
        jobs_card.pack(fill='both', expand=True, pady=(0, 8))
        
        # Create Treeview for job list
        columns = ('Job No', 'Request No', 'Lots', 'Button Weight', 'Scrap Weight', 'Status')
        self.jobs_tree = ttk.Treeview(jobs_card, columns=columns, show='headings', height=8)
        
        # Configure columns
        self.jobs_tree.heading('Job No', text='Job No')
        self.jobs_tree.heading('Request No', text='Request No')
        self.jobs_tree.heading('Lots', text='Lots')
        self.jobs_tree.heading('Button Weight', text='Button Weight')
        self.jobs_tree.heading('Scrap Weight', text='Scrap Weight')
        self.jobs_tree.heading('Status', text='Status')
        
        self.jobs_tree.column('Job No', width=80)
        self.jobs_tree.column('Request No', width=100)
        self.jobs_tree.column('Lots', width=60)
        self.jobs_tree.column('Button Weight', width=100)
        self.jobs_tree.column('Scrap Weight', width=100)
        self.jobs_tree.column('Status', width=100)
        
        # Scrollbar for treeview
        jobs_scrollbar = ttk.Scrollbar(jobs_card, orient='vertical', command=self.jobs_tree.yview)
        self.jobs_tree.configure(yscrollcommand=jobs_scrollbar.set)
        
        # Pack treeview and scrollbar
        self.jobs_tree.pack(side='left', fill='both', expand=True, padx=(10, 0), pady=10)
        jobs_scrollbar.pack(side='right', fill='y', padx=(0, 10), pady=10)
        
        # Log Card
        log_card = ttk.LabelFrame(parent, text="📝 Processing Log", style='Compact.TLabelframe')
        log_card.pack(fill='x', pady=(0, 0))
        
        # Log text area
        self.log_text = tk.Text(log_card, height=6, wrap='word', font=('Consolas', 9))
        log_scrollbar = ttk.Scrollbar(log_card, orient='vertical', command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side='left', fill='both', expand=True, padx=(10, 0), pady=10)
        log_scrollbar.pack(side='right', fill='y', padx=(0, 10), pady=10)
        
        # Add initial test message to verify logging works
        self.log("📝 Processing Log initialized - Ready for messages", 'multiple_jobs')
    
    
    def load_report_data(self):
        """Load report data first before allowing save actions"""
        # Test logging first
        self.log("🚀 LOAD REPORT DATA BUTTON CLICKED", 'multiple_jobs')
        
        # Check license before loading data
        if not self.check_license_before_action("report data loading"):
            self.log("❌ License check failed", 'multiple_jobs')
            return
        
        try:
            # Get report ID from user
            report_id = self.report_id_entry.get().strip()
            if not report_id:
                messagebox.showwarning("Validation Error", "Please enter Report ID")
                return
            
            # Get API URL from settings
            api_url = self.get_api_url_from_settings()
            if not api_url:
                messagebox.showwarning("Validation Error", "Please configure API URL in Settings page")
                return
            
            # Check if browser is ready
            if not self.driver:
                messagebox.showwarning("Not Ready", "Please open browser and login first")
                return
            
            # Start loading in background thread
            threading.Thread(
                target=self._load_report_data_worker, 
                args=(report_id, api_url), 
                daemon=True
            ).start()
            
        except Exception as e:
            self.log(f"❌ Error starting report data loading: {str(e)}", 'multiple_jobs')
            messagebox.showerror("Error", f"Error starting data loading: {str(e)}")
    
    def _load_report_data_worker(self, report_id, api_url):
        """Worker thread for loading report data"""
        try:
            self.update_status("Fetching report data...", '#ffc107')
            self.log(f"🔍 Loading data for Report ID: {report_id}", 'multiple_jobs')
            
            # Fetch report data from API
            full_api_url = f"{api_url}?report_id={report_id}"
            response = requests.get(full_api_url, timeout=30)
            
            if response.status_code != 200:
                self.update_status("API Error", '#dc3545')
                self.log(f"❌ API Error: HTTP {response.status_code}", 'multiple_jobs')
                messagebox.showerror("API Error", f"Failed to fetch report data: HTTP {response.status_code}")
                return
            
            data = response.json()
            if not data.get('success'):
                self.update_status("API Error", '#dc3545')
                error_msg = data.get('error', 'Unknown error')
                self.log(f"❌ API Error: {error_msg}", 'multiple_jobs')
                messagebox.showerror("API Error", f"API Error: {error_msg}")
                return
            
            # Get job summary
            job_summary = data.get('job_summary', [])
            if not job_summary:
                self.update_status("No Data", '#ffc107')
                self.log("⚠️ No jobs found in this report", 'multiple_jobs')
                messagebox.showwarning("No Data", "No jobs found in this report")
                return
            
            # DEBUG: Log the complete data structure
            self.log(f"🔍 DEBUG: Report data keys: {list(data.keys())}", 'multiple_jobs')
            self.log(f"🔍 DEBUG: Job summary: {job_summary}", 'multiple_jobs')
            
            # Extract strip data from the main report response (it's already there!)
            enhanced_job_summary = []
            strips_data = data.get('strips_data', {})
            check_gold_data = data.get('check_gold_data', [])
            
            self.log(f"🔍 Found strips_data with keys: {list(strips_data.keys())}", 'multiple_jobs')
            self.log(f"🔍 Found {len(check_gold_data)} check gold entries in report", 'multiple_jobs')
            
            for job in job_summary:
                job_no = job['job_no']
                self.log(f"🔍 Processing strip data for Job {job_no}", 'multiple_jobs')
                
                # Extract strips data for this job from the nested structure
                job_strips_data = strips_data.get(job_no, {})
                all_strip_data = []
                
                # Process each lot in the job
                for lot_no, lot_strips in job_strips_data.items():
                    if isinstance(lot_strips, list):
                        all_strip_data.extend(lot_strips)
                        self.log(f"🔍 Found {len(lot_strips)} strips for Job {job_no}, Lot {lot_no}", 'multiple_jobs')
                
                # Also add check gold data if it exists and map to C1/C2
                check_gold_strips = strips_data.get('CHECK_GOLD', [])
                if check_gold_strips and isinstance(check_gold_strips, list):
                    # Flatten the CHECK_GOLD array structure and map strip_no to C1/C2
                    cg_count = 0
                    for cg_group in check_gold_strips:
                        if isinstance(cg_group, list):
                            for strip in cg_group:
                                # Map CHECK_GOLD strip_no '1' to 'C1' and '2' to 'C2'
                                if strip.get('strip_no') == '1':
                                    strip['strip_no'] = 'C1'
                                    cg_count += 1
                                elif strip.get('strip_no') == '2':
                                    strip['strip_no'] = 'C2'
                                    cg_count += 1
                                all_strip_data.append(strip)
                    self.log(f"🔍 Added {cg_count} check gold strips (mapped to C1/C2)", 'multiple_jobs')
                
                if all_strip_data:
                    job['strip_data'] = all_strip_data
                    self.log(f"✅ Found {len(all_strip_data)} total strip entries for Job {job_no}", 'multiple_jobs')
                    
                    # Debug: Show what strip data looks like
                    if all_strip_data:
                        first_strip = all_strip_data[0]
                        self.log(f"🔍 Sample strip data keys: {list(first_strip.keys())}", 'multiple_jobs')
                        self.log(f"🔍 Sample strip data: {first_strip}", 'multiple_jobs')
                else:
                    self.log(f"⚠️ No strip data found for Job {job_no} in report response", 'multiple_jobs')
                
                enhanced_job_summary.append(job)
            
            # Store the enhanced data for later use
            data['job_summary'] = enhanced_job_summary
            self.loaded_report_data = data
            self.loaded_report_id = report_id
            
            # Update UI with job list
            self.update_jobs_list(enhanced_job_summary)
            
            # Enable save action buttons
            self.save_initial_btn.config(state='normal')
            self.save_cornet_btn.config(state='normal')
            self.process_all_btn.config(state='normal')
            
            # Show success message
            self.update_status("Data Loaded", '#28a745')
            self.log(f"✅ Successfully loaded data for {len(enhanced_job_summary)} jobs with strip data", 'multiple_jobs')
            messagebox.showinfo(
                "Data Loaded Successfully",
                f"✅ Loaded complete data for {len(enhanced_job_summary)} jobs in report {report_id}\n\nIncluding strip data (initial, silver, copper, lead values).\n\nYou can now use Save Initial, Save Cornet, or Process All buttons."
            )
            
        except Exception as e:
            self.update_status("Error", '#dc3545')
            self.log(f"❌ Error loading report data: {str(e)}", 'multiple_jobs')
            messagebox.showerror("Error", f"Error loading data: {str(e)}")
    

    def save_initial_weights_multiple_jobs(self):
        """Save initial weights for multiple jobs from a single report"""
        # Test logging first
        self.log("🚀 SAVE INITIAL WEIGHTS BUTTON CLICKED", 'multiple_jobs')
        
        # Check license before automation
        if not self.check_license_before_action("multiple job initial weights"):
            self.log("❌ License check failed", 'multiple_jobs')
            return
        
        try:
            # Check if data has been loaded
            if not hasattr(self, 'loaded_report_data') or not self.loaded_report_data:
                self.log("❌ No report data loaded", 'multiple_jobs')
                messagebox.showwarning("No Data", "Please load report data first using 'Load Report Data' button")
                return
            
            # Check if browser is ready
            if not self.driver:
                self.log("❌ Browser not ready", 'multiple_jobs')
                messagebox.showwarning("Not Ready", "Please open browser and login first")
                return
            
            # Check if user is logged in
            try:
                current_url = self.driver.current_url
                self.log(f"🔍 Current browser URL: {current_url}", 'multiple_jobs')
                if 'eBISLogin' in current_url:
                    self.log("❌ User not logged in - still on login page", 'multiple_jobs')
                    messagebox.showwarning("Not Logged In", "Please login to MANAK portal first")
                    return
                self.log("✅ User appears to be logged in", 'multiple_jobs')
            except Exception as e:
                self.log(f"❌ Error checking login status: {str(e)}", 'multiple_jobs')
                messagebox.showwarning("Browser Error", "Error checking browser status")
                return
            
            self.log("✅ Starting initial weights processing...", 'multiple_jobs')
            
            # Start processing in background thread using pre-loaded data
            threading.Thread(
                target=self._save_initial_weights_worker_with_data, 
                args=(self.loaded_report_data, self.loaded_report_id), 
                daemon=True
            ).start()
            
        except Exception as e:
            self.log(f"❌ Error starting initial weights processing: {str(e)}", 'multiple_jobs')
            messagebox.showerror("Error", f"Error starting processing: {str(e)}")

    def save_cornet_weights_multiple_jobs(self):
        """Save cornet weights for multiple jobs from a single report"""
        # Check license before automation
        if not self.check_license_before_action("multiple job cornet weights"):
            return
        
        try:
            # Check if data has been loaded
            if not hasattr(self, 'loaded_report_data') or not self.loaded_report_data:
                messagebox.showwarning("No Data", "Please load report data first using 'Load Report Data' button")
                return
            
            # Check if browser is ready
            if not self.driver:
                messagebox.showwarning("Not Ready", "Please open browser and login first")
                return
            
            # Start processing in background thread using pre-loaded data
            threading.Thread(
                target=self._save_cornet_weights_worker_with_data, 
                args=(self.loaded_report_data, self.loaded_report_id), 
                daemon=True
            ).start()
            
        except Exception as e:
            self.log(f"❌ Error starting cornet weights processing: {str(e)}", 'multiple_jobs')
            messagebox.showerror("Error", f"Error starting processing: {str(e)}")

    def process_multiple_jobs_from_report(self):
        """Process multiple jobs from a single report in one click"""
        # Check license before automation
        if not self.check_license_before_action("multiple job processing"):
            return
        
        try:
            # Get report ID from user
            report_id = self.report_id_entry.get().strip()
            if not report_id:
                messagebox.showwarning("Validation Error", "Please enter Report ID")
                return
            
            # Get API URL from settings
            api_url = self.get_api_url_from_settings()
            if not api_url:
                messagebox.showwarning("Validation Error", "Please configure API URL in Settings page")
                return
            
            # Check if browser is ready
            if not self.driver:
                messagebox.showwarning("Not Ready", "Please open browser and login first")
                return
            
            # Start processing in background thread
            threading.Thread(
                target=self._process_multiple_jobs_worker, 
                args=(report_id, api_url), 
                daemon=True
            ).start()
            
        except Exception as e:
            self.log(f"❌ Error starting multiple job processing: {str(e)}", 'multiple_jobs')
            messagebox.showerror("Error", f"Error starting processing: {str(e)}")
    
    def _process_multiple_jobs_worker(self, report_id, api_url):
        """Worker thread for processing multiple jobs"""
        try:
            self.update_status("Fetching report data...", '#ffc107')
            self.log(f"🔍 Fetching data for Report ID: {report_id}", 'multiple_jobs')
            
            # Fetch report data from API
            full_api_url = f"{api_url}?report_id={report_id}"
            response = requests.get(full_api_url, timeout=30)
            
            if response.status_code != 200:
                self.update_status("API Error", '#dc3545')
                self.log(f"❌ API Error: HTTP {response.status_code}", 'multiple_jobs')
                messagebox.showerror("API Error", f"Failed to fetch report data: HTTP {response.status_code}")
                return
            
            data = response.json()
            if not data.get('success'):
                self.update_status("API Error", '#dc3545')
                error_msg = data.get('error', 'Unknown error')
                self.log(f"❌ API Error: {error_msg}", 'multiple_jobs')
                messagebox.showerror("API Error", f"API Error: {error_msg}")
                return
            
            # Get job summary
            job_summary = data.get('job_summary', [])
            if not job_summary:
                self.update_status("No Data", '#ffc107')
                self.log("⚠️ No jobs found in this report", 'multiple_jobs')
                messagebox.showwarning("No Data", "No jobs found in this report")
                return
            
            # Update UI with job list
            self.update_jobs_list(job_summary)
            
            # Show confirmation dialog
            job_list = "\n".join([f"Job {job['job_no']} (Request: {job['request_no']}) - {job['total_lots']} lots" 
                                 for job in job_summary])
            
            response = messagebox.askyesno(
                "Confirm Multiple Job Processing",
                f"Found {len(job_summary)} jobs in report {report_id}:\n\n{job_list}\n\nDo you want to process all jobs?"
            )
            
            if not response:
                self.update_status("Cancelled", '#6c757d')
                return
            
            # Start processing jobs
            self.update_status("Processing jobs...", '#007bff')
            success_count = 0
            error_count = 0
            
            for i, job in enumerate(job_summary):
                job_no = job['job_no']
                request_no = job['request_no']
                
                self.update_progress(f"Processing Job {job_no} ({i+1}/{len(job_summary)})")
                self.log(f"🔄 Processing Job {job_no} (Request: {request_no})", 'multiple_jobs')
                
                try:
                    # Process this job
                    success = self._process_single_job_from_report(data, job_no, request_no)
                    if success:
                        success_count += 1
                        self.log(f"✅ Successfully processed Job {job_no}", 'multiple_jobs')
                        self.update_job_status(job_no, "✅ Success")
                    else:
                        error_count += 1
                        self.log(f"❌ Failed to process Job {job_no}", 'multiple_jobs')
                        self.update_job_status(job_no, "❌ Failed")
                        
                except Exception as e:
                    error_count += 1
                    self.log(f"❌ Error processing Job {job_no}: {str(e)}", 'multiple_jobs')
                    self.update_job_status(job_no, "❌ Error")
                
                # Delay between jobs
                delay = int(self.job_delay_var.get())
                if delay > 0 and i < len(job_summary) - 1:  # Don't delay after last job
                    time.sleep(delay)
            
            # Show final results
            self.update_status("Complete", '#28a745')
            self.update_progress(f"Completed: {success_count} success, {error_count} failed")
            self.update_results(f"✅ Success: {success_count} | ❌ Failed: {error_count}")
            
            messagebox.showinfo(
                "Processing Complete",
                f"✅ Successfully processed: {success_count} jobs\n❌ Failed: {error_count} jobs"
            )
            
        except Exception as e:
            self.update_status("Error", '#dc3545')
            self.log(f"❌ Error in multiple job processing: {str(e)}", 'multiple_jobs')
            messagebox.showerror("Error", f"Error in processing: {str(e)}")

    def _save_initial_weights_worker_with_data(self, data, report_id):
        """Worker thread for saving initial weights using pre-loaded data"""
        try:
            # TEST: Verify logging is working
            self.log("🚀 STARTING INITIAL WEIGHTS SAVE PROCESS", 'multiple_jobs')
            self.log(f"🔍 Report ID: {report_id}", 'multiple_jobs')
            self.log(f"🔍 Data keys: {list(data.keys()) if data else 'None'}", 'multiple_jobs')
            
            # Get job summary from pre-loaded data
            job_summary = data.get('job_summary', [])
            if not job_summary:
                self.update_status("No Data", '#ffc107')
                self.log("⚠️ No jobs found in loaded data", 'multiple_jobs')
                messagebox.showwarning("No Data", "No jobs found in loaded data")
                return
            
            # Start processing jobs for initial weights only
            self.update_status("Saving initial weights...", '#007bff')
            success_count = 0
            error_count = 0
            
            for i, job in enumerate(job_summary):
                job_no = job['job_no']
                request_no = job['request_no']
                
                self.update_progress(f"Saving initial weights for Job {job_no} ({i+1}/{len(job_summary)})")
                self.log(f"💾 Saving initial weights for Job {job_no} (Request: {request_no})", 'multiple_jobs')
                
                try:
                    # Process this job for initial weights only
                    success = self._save_initial_weights_for_job(data, job_no, request_no)
                    if success:
                        success_count += 1
                        self.log(f"✅ Successfully saved initial weights for Job {job_no}", 'multiple_jobs')
                        self.update_job_status(job_no, "✅ Initial Saved")
                    else:
                        error_count += 1
                        self.log(f"❌ Failed to save initial weights for Job {job_no}", 'multiple_jobs')
                        self.update_job_status(job_no, "❌ Initial Failed")
                        
                except Exception as e:
                    error_count += 1
                    self.log(f"❌ Error saving initial weights for Job {job_no}: {str(e)}", 'multiple_jobs')
                    self.update_job_status(job_no, "❌ Initial Error")
                
                # Delay between jobs
                delay = int(self.job_delay_var.get())
                if delay > 0 and i < len(job_summary) - 1:
                    time.sleep(delay)
            
            # Show final results
            self.update_status("Complete", '#28a745')
            self.update_progress(f"Initial weights saved: {success_count} success, {error_count} failed")
            self.update_results(f"✅ Initial Weights - Success: {success_count} | ❌ Failed: {error_count}")
            
            messagebox.showinfo(
                "Initial Weights Complete",
                f"✅ Successfully saved initial weights for: {success_count} jobs\n❌ Failed: {error_count} jobs"
            )
            
        except Exception as e:
            self.update_status("Error", '#dc3545')
            self.log(f"❌ Error in initial weights processing: {str(e)}", 'multiple_jobs')
            messagebox.showerror("Error", f"Error in processing: {str(e)}")

    def _save_cornet_weights_worker_with_data(self, data, report_id):
        """Worker thread for saving cornet weights using pre-loaded data"""
        try:
            # TEST: Verify logging is working
            self.log("🚀 STARTING CORNET WEIGHTS SAVE PROCESS", 'multiple_jobs')
            self.log(f"🔍 Report ID: {report_id}", 'multiple_jobs')
            
            # Get job summary from pre-loaded data
            job_summary = data.get('job_summary', [])
            if not job_summary:
                self.update_status("No Data", '#ffc107')
                self.log("⚠️ No jobs found in loaded data", 'multiple_jobs')
                messagebox.showwarning("No Data", "No jobs found in loaded data")
                return
            
            # Start processing jobs for cornet weights only
            self.update_status("Saving cornet weights...", '#007bff')
            success_count = 0
            error_count = 0
            
            for i, job in enumerate(job_summary):
                job_no = job['job_no']
                request_no = job['request_no']
                
                self.update_progress(f"Saving cornet weights for Job {job_no} ({i+1}/{len(job_summary)})")
                self.log(f"⚖️ Saving cornet weights for Job {job_no} (Request: {request_no})", 'multiple_jobs')
                
                try:
                    # Process this job for cornet weights only
                    success = self._save_cornet_weights_for_job(data, job_no, request_no)
                    if success:
                        success_count += 1
                        self.log(f"✅ Successfully saved cornet weights for Job {job_no}", 'multiple_jobs')
                        self.update_job_status(job_no, "✅ Cornet Saved")
                    else:
                        error_count += 1
                        self.log(f"❌ Failed to save cornet weights for Job {job_no}", 'multiple_jobs')
                        self.update_job_status(job_no, "❌ Cornet Failed")
                        
                except Exception as e:
                    error_count += 1
                    self.log(f"❌ Error saving cornet weights for Job {job_no}: {str(e)}", 'multiple_jobs')
                    self.update_job_status(job_no, "❌ Cornet Error")
                
                # Delay between jobs
                delay = int(self.job_delay_var.get())
                if delay > 0 and i < len(job_summary) - 1:
                    time.sleep(delay)
            
            # Show final results
            self.update_status("Complete", '#28a745')
            self.update_progress(f"Cornet weights saved: {success_count} success, {error_count} failed")
            self.update_results(f"⚖️ Cornet Weights - Success: {success_count} | ❌ Failed: {error_count}")
            
            messagebox.showinfo(
                "Cornet Weights Complete",
                f"✅ Successfully saved cornet weights for: {success_count} jobs\n❌ Failed: {error_count} jobs"
            )
            
        except Exception as e:
            self.update_status("Error", '#dc3545')
            self.log(f"❌ Error in cornet weights processing: {str(e)}", 'multiple_jobs')
            messagebox.showerror("Error", f"Error in processing: {str(e)}")

    def _save_initial_weights_worker(self, report_id, api_url):
        """Worker thread for saving initial weights for multiple jobs"""
        try:
            self.update_status("Fetching report data...", '#ffc107')
            self.log(f"🔍 Fetching data for Report ID: {report_id}", 'multiple_jobs')
            
            # Fetch report data from API
            full_api_url = f"{api_url}?report_id={report_id}"
            response = requests.get(full_api_url, timeout=30)
            
            if response.status_code != 200:
                self.update_status("API Error", '#dc3545')
                self.log(f"❌ API Error: HTTP {response.status_code}", 'multiple_jobs')
                messagebox.showerror("API Error", f"Failed to fetch report data: HTTP {response.status_code}")
                return
            
            data = response.json()
            if not data.get('success'):
                self.update_status("API Error", '#dc3545')
                error_msg = data.get('error', 'Unknown error')
                self.log(f"❌ API Error: {error_msg}", 'multiple_jobs')
                messagebox.showerror("API Error", f"API Error: {error_msg}")
                return
            
            # Get job summary
            job_summary = data.get('job_summary', [])
            if not job_summary:
                self.update_status("No Data", '#ffc107')
                self.log("⚠️ No jobs found in this report", 'multiple_jobs')
                messagebox.showwarning("No Data", "No jobs found in this report")
                return
            
            # Update UI with job list
            self.update_jobs_list(job_summary)
            
            # Start processing jobs for initial weights only
            self.update_status("Saving initial weights...", '#007bff')
            success_count = 0
            error_count = 0
            
            for i, job in enumerate(job_summary):
                job_no = job['job_no']
                request_no = job['request_no']
                
                self.update_progress(f"Saving initial weights for Job {job_no} ({i+1}/{len(job_summary)})")
                self.log(f"💾 Saving initial weights for Job {job_no} (Request: {request_no})", 'multiple_jobs')
                
                try:
                    # Process this job for initial weights only
                    success = self._save_initial_weights_for_job(data, job_no, request_no)
                    if success:
                        success_count += 1
                        self.log(f"✅ Successfully saved initial weights for Job {job_no}", 'multiple_jobs')
                        self.update_job_status(job_no, "✅ Initial Saved")
                    else:
                        error_count += 1
                        self.log(f"❌ Failed to save initial weights for Job {job_no}", 'multiple_jobs')
                        self.update_job_status(job_no, "❌ Initial Failed")
                        
                except Exception as e:
                    error_count += 1
                    self.log(f"❌ Error saving initial weights for Job {job_no}: {str(e)}", 'multiple_jobs')
                    self.update_job_status(job_no, "❌ Initial Error")
                
                # Delay between jobs
                delay = int(self.job_delay_var.get())
                if delay > 0 and i < len(job_summary) - 1:
                    time.sleep(delay)
            
            # Show final results
            self.update_status("Complete", '#28a745')
            self.update_progress(f"Initial weights saved: {success_count} success, {error_count} failed")
            self.update_results(f"✅ Initial Weights - Success: {success_count} | ❌ Failed: {error_count}")
            
            messagebox.showinfo(
                "Initial Weights Complete",
                f"✅ Successfully saved initial weights for: {success_count} jobs\n❌ Failed: {error_count} jobs"
            )
            
        except Exception as e:
            self.update_status("Error", '#dc3545')
            self.log(f"❌ Error in initial weights processing: {str(e)}", 'multiple_jobs')
            messagebox.showerror("Error", f"Error in processing: {str(e)}")

    def _save_cornet_weights_worker(self, report_id, api_url):
        """Worker thread for saving cornet weights for multiple jobs"""
        try:
            self.update_status("Fetching report data...", '#ffc107')
            self.log(f"🔍 Fetching data for Report ID: {report_id}", 'multiple_jobs')
            
            # Fetch report data from API
            full_api_url = f"{api_url}?report_id={report_id}"
            response = requests.get(full_api_url, timeout=30)
            
            if response.status_code != 200:
                self.update_status("API Error", '#dc3545')
                self.log(f"❌ API Error: HTTP {response.status_code}", 'multiple_jobs')
                messagebox.showerror("API Error", f"Failed to fetch report data: HTTP {response.status_code}")
                return
            
            data = response.json()
            if not data.get('success'):
                self.update_status("API Error", '#dc3545')
                error_msg = data.get('error', 'Unknown error')
                self.log(f"❌ API Error: {error_msg}", 'multiple_jobs')
                messagebox.showerror("API Error", f"API Error: {error_msg}")
                return
            
            # Get job summary
            job_summary = data.get('job_summary', [])
            if not job_summary:
                self.update_status("No Data", '#ffc107')
                self.log("⚠️ No jobs found in this report", 'multiple_jobs')
                messagebox.showwarning("No Data", "No jobs found in this report")
                return
            
            # Update UI with job list
            self.update_jobs_list(job_summary)
            
            # Start processing jobs for cornet weights only
            self.update_status("Saving cornet weights...", '#007bff')
            success_count = 0
            error_count = 0
            
            for i, job in enumerate(job_summary):
                job_no = job['job_no']
                request_no = job['request_no']
                
                self.update_progress(f"Saving cornet weights for Job {job_no} ({i+1}/{len(job_summary)})")
                self.log(f"⚖️ Saving cornet weights for Job {job_no} (Request: {request_no})", 'multiple_jobs')
                
                try:
                    # Process this job for cornet weights only
                    success = self._save_cornet_weights_for_job(data, job_no, request_no)
                    if success:
                        success_count += 1
                        self.log(f"✅ Successfully saved cornet weights for Job {job_no}", 'multiple_jobs')
                        self.update_job_status(job_no, "✅ Cornet Saved")
                    else:
                        error_count += 1
                        self.log(f"❌ Failed to save cornet weights for Job {job_no}", 'multiple_jobs')
                        self.update_job_status(job_no, "❌ Cornet Failed")
                        
                except Exception as e:
                    error_count += 1
                    self.log(f"❌ Error saving cornet weights for Job {job_no}: {str(e)}", 'multiple_jobs')
                    self.update_job_status(job_no, "❌ Cornet Error")
                
                # Delay between jobs
                delay = int(self.job_delay_var.get())
                if delay > 0 and i < len(job_summary) - 1:
                    time.sleep(delay)
            
            # Show final results
            self.update_status("Complete", '#28a745')
            self.update_progress(f"Cornet weights saved: {success_count} success, {error_count} failed")
            self.update_results(f"✅ Cornet Weights - Success: {success_count} | ❌ Failed: {error_count}")
            
            messagebox.showinfo(
                "Cornet Weights Complete",
                f"✅ Successfully saved cornet weights for: {success_count} jobs\n❌ Failed: {error_count} jobs"
            )
            
        except Exception as e:
            self.update_status("Error", '#dc3545')
            self.log(f"❌ Error in cornet weights processing: {str(e)}", 'multiple_jobs')
            messagebox.showerror("Error", f"Error in processing: {str(e)}")
    
    def _process_single_job_from_report(self, report_data, job_no, request_no):
        """Process a single job from report data"""
        try:
            # Get lot weights for this job
            lot_weights = [lw for lw in report_data.get('lot_weights', []) if lw['job_no'] == job_no]
            
            if not lot_weights:
                self.log(f"⚠️ No lot weights found for Job {job_no}", 'multiple_jobs')
                return False
            
            # Process each lot in this job
            total_lots = len(lot_weights)
            for i, lot_weight in enumerate(lot_weights):
                lot_no = lot_weight['lot_no']
                is_last_lot = (i == total_lots - 1)  # Check if this is the last lot
                
                self.log(f"🔄 Processing Lot {lot_no} for Job {job_no} ({i+1}/{total_lots})", 'multiple_jobs')
                
                # Load weight page
                weight_url = f"https://huid.manakonline.in/MANAK/SamplingweightingDeatils?requestNo={request_no}&jobNo={job_no}"
                self.driver.get(weight_url)
                time.sleep(3)
                
                # Select lot
                if not self._select_lot_in_portal(str(lot_no)):
                    self.log(f"❌ Failed to select Lot {lot_no} for Job {job_no}", 'multiple_jobs')
                    continue
                
                # Fill weights
                self._fill_weights_from_api_data(lot_weight)
                
                # Save weights (without HUID submission)
                self._save_weights_for_lot_without_huid()
                
                self.log(f"✅ Processed Lot {lot_no} for Job {job_no}", 'multiple_jobs')
                
                # Submit for HUID only after the last lot
                if is_last_lot and self.auto_submit_huid_var.get():
                    self.log(f"📤 Submitting HUID for Job {job_no} (after last lot {lot_no})", 'multiple_jobs')
                    self._submit_huid_for_job()
            
            return True
            
        except Exception as e:
            self.log(f"❌ Error processing Job {job_no}: {str(e)}", 'multiple_jobs')
            return False
    
    def _select_lot_in_portal(self, lot_no):
        """Helper method to select lot in portal"""
        try:
            # Use Select2 method
            select2_container = self.driver.find_element(By.ID, "s2id_lotno")
            select2_container.click()
            time.sleep(0.5)
            
            options = self.driver.find_elements(By.CSS_SELECTOR, "ul.select2-results li")
            found = False
            for option in options:
                if option.text.strip().endswith(f"Lot {lot_no}") or option.text.strip() == f"Lot {lot_no}":
                    option.click()
                    found = True
                    self.log(f"✅ Selected Lot {lot_no} in portal", 'multiple_jobs')
                    break
            
            if not found:
                self.log(f"⚠️ Lot {lot_no} not found in Select2 options", 'multiple_jobs')
                return False
            
            time.sleep(1)
            return True
            
        except Exception as e:
            self.log(f"❌ Error selecting lot {lot_no}: {str(e)}", 'multiple_jobs')
            return False
    
    def _fill_weights_from_api_data(self, lot_weight_data):
        """Fill weight fields from API data"""
        try:
            # Fill button weight
            button_weight = lot_weight_data.get('button_weight', 0)
            if button_weight:
                element = self.driver.find_element(By.ID, 'buttonweight')
                element.clear()
                element.send_keys(str(button_weight))
                self.log(f"✅ Filled button weight: {button_weight}", 'multiple_jobs')
            
            # Fill scrap weight
            scrap_weight = lot_weight_data.get('scrap_weight', 0)
            if scrap_weight:
                element = self.driver.find_element(By.ID, 'num_scrap_weight')
                element.clear()
                element.send_keys(str(scrap_weight))
                self.log(f"✅ Filled scrap weight: {scrap_weight}", 'multiple_jobs')
            
        except Exception as e:
            self.log(f"❌ Error filling weights: {str(e)}", 'multiple_jobs')
    
    def _save_weights_for_lot(self):
        """Save weights for current lot"""
        try:
            # Save button weight
            save_btn = self.driver.find_element(By.ID, 'savebuttonweight')
            if save_btn.is_displayed() and save_btn.is_enabled():
                save_btn.click()
                time.sleep(1)
                self.log("💾 Saved button weight", 'multiple_jobs')
            
            # Save scrap weight
            save_btn = self.driver.find_element(By.ID, 'savesampleweight')
            if save_btn.is_displayed() and save_btn.is_enabled():
                save_btn.click()
                time.sleep(1)
                self.log("💾 Saved scrap weight", 'multiple_jobs')
            
        except Exception as e:
            self.log(f"❌ Error saving weights: {str(e)}", 'multiple_jobs')

    def _save_weights_for_lot_without_huid(self):
        """Save weights for a lot without HUID submission"""
        try:
            # Save button weight
            save_btn = self.driver.find_element(By.ID, 'savebuttonweight')
            if save_btn.is_displayed() and save_btn.is_enabled():
                save_btn.click()
                time.sleep(1)
                self.log("💾 Saved button weight", 'multiple_jobs')
            
            # Save scrap weight
            save_btn = self.driver.find_element(By.ID, 'savesampleweight')
            if save_btn.is_displayed() and save_btn.is_enabled():
                save_btn.click()
                time.sleep(1)
                self.log("💾 Saved scrap weight", 'multiple_jobs')
            
        except Exception as e:
            self.log(f"❌ Error saving weights: {str(e)}", 'multiple_jobs')

    def _submit_huid_for_job(self):
        """Submit HUID for the current job (after all lots are processed)"""
        try:
            submit_btn = self.driver.find_element(By.ID, 'submitQM')
            if submit_btn.is_displayed() and submit_btn.is_enabled():
                submit_btn.click()
                self.log("📤 Submitted for HUID", 'multiple_jobs')
                time.sleep(2)
                
                # Handle any alerts that might appear
                try:
                    alert = self.driver.switch_to.alert
                    alert_text = alert.text
                    self.log(f"🔔 HUID Alert: {alert_text}", 'multiple_jobs')
                    alert.accept()
                    time.sleep(1)
                except:
                    pass
                    
                try:
                    alert = self.driver.switch_to.alert
                    alert_text = alert.text
                    self.log(f"🔔 HUID Result: {alert_text}", 'multiple_jobs')
                    alert.accept()
                    time.sleep(1)
                except:
                    pass
                    
            else:
                self.log("⚠️ HUID submit button not available", 'multiple_jobs')
                
        except Exception as e:
            self.log(f"❌ Error submitting HUID: {str(e)}", 'multiple_jobs')

    def _save_initial_weights_for_job(self, report_data, job_no, request_no):
        """Save initial weights for a single job"""
        try:
            # DEBUG: Log the report data structure
            self.log(f"🔍 DEBUG: Processing Job {job_no}, Report data keys: {list(report_data.keys())}", 'multiple_jobs')
            
            # Find the job in the enhanced job summary
            job_data = None
            for job in report_data.get('job_summary', []):
                if job['job_no'] == job_no:
                    job_data = job
                    break
            
            if not job_data:
                self.log(f"❌ Job {job_no} not found in job summary", 'multiple_jobs')
                return False
            
            # Get strip data for this job
            strip_data = job_data.get('strip_data', [])
            if not strip_data:
                self.log(f"❌ No strip data found for Job {job_no}", 'multiple_jobs')
                return False
            
            self.log(f"🔍 DEBUG: Found {len(strip_data)} strips for Job {job_no}", 'multiple_jobs')
            
            # Group strips by lot_no (separate CHECK_GOLD data from regular lots)
            lots_data = {}
            check_gold_data = []  # Store CHECK_GOLD data separately
            
            for strip in strip_data:
                lot_no = strip.get('lot_no', '1')
                # Separate CHECK_GOLD data from regular lots
                if lot_no == '0':
                    check_gold_data.append(strip)
                else:
                    if lot_no not in lots_data:
                        lots_data[lot_no] = []
                    lots_data[lot_no].append(strip)
            
            self.log(f"🔍 DEBUG: Found {len(lots_data)} lots for Job {job_no}: {list(lots_data.keys())}", 'multiple_jobs')
            self.log(f"🔍 DEBUG: Found {len(check_gold_data)} CHECK_GOLD entries for Job {job_no}", 'multiple_jobs')
            
            # Process each lot in this job for initial weights only
            total_lots = len(lots_data)
            for i, (lot_no, strips) in enumerate(lots_data.items()):
                is_last_lot = (i == total_lots - 1)  # Check if this is the last lot
                
                self.log(f"💾 Saving initial weights for Lot {lot_no} in Job {job_no} ({i+1}/{total_lots})", 'multiple_jobs')
                
                # Load weight page
                weight_url = f"https://huid.manakonline.in/MANAK/SamplingweightingDeatils?requestNo={request_no}&jobNo={job_no}"
                self.driver.get(weight_url)
                time.sleep(3)
                
                # Select lot
                if not self._select_lot_in_portal(str(lot_no)):
                    self.log(f"❌ Failed to select Lot {lot_no} for Job {job_no}", 'multiple_jobs')
                    continue
                
                # Create lot_weight_data with strip data + CHECK_GOLD data
                all_strips_for_lot = strips + check_gold_data  # Include CHECK_GOLD data with each lot
                lot_weight_data = {
                    'strip_data': all_strips_for_lot,
                    'button_weight': job_data.get('total_button_weight', 0),
                    'scrap_weight': job_data.get('total_scrap_weight', 0)
                }
                
                # Fill and save initial weights only
                self._fill_and_save_initial_weights(lot_weight_data)
                
                self.log(f"✅ Saved initial weights for Lot {lot_no} in Job {job_no}", 'multiple_jobs')
                
                # Submit for HUID only after the last lot (if auto-submit is enabled)
                if is_last_lot and self.auto_submit_huid_var.get():
                    self.log(f"📤 Submitting HUID for Job {job_no} (after last lot {lot_no})", 'multiple_jobs')
                    self._submit_huid_for_job()
            
            return True
            
        except Exception as e:
            self.log(f"❌ Error saving initial weights for Job {job_no}: {str(e)}", 'multiple_jobs')
            return False

    def _save_cornet_weights_for_job(self, report_data, job_no, request_no):
        """Save cornet weights for a single job"""
        try:
            # Find the job in the enhanced job summary
            job_data = None
            for job in report_data.get('job_summary', []):
                if job['job_no'] == job_no:
                    job_data = job
                    break
            
            if not job_data:
                self.log(f"❌ Job {job_no} not found in job summary", 'multiple_jobs')
                return False
            
            # Get strip data for this job
            strip_data = job_data.get('strip_data', [])
            if not strip_data:
                self.log(f"❌ No strip data found for Job {job_no}", 'multiple_jobs')
                return False
            
            self.log(f"🔍 DEBUG: Found {len(strip_data)} strips for Job {job_no}", 'multiple_jobs')
            
            # Group strips by lot_no (separate CHECK_GOLD data from regular lots)
            lots_data = {}
            check_gold_data = []  # Store CHECK_GOLD data separately
            
            for strip in strip_data:
                lot_no = strip.get('lot_no', '1')
                # Separate CHECK_GOLD data from regular lots
                if lot_no == '0':
                    check_gold_data.append(strip)
                else:
                    if lot_no not in lots_data:
                        lots_data[lot_no] = []
                    lots_data[lot_no].append(strip)
            
            self.log(f"🔍 DEBUG: Found {len(lots_data)} lots for Job {job_no}: {list(lots_data.keys())}", 'multiple_jobs')
            self.log(f"🔍 DEBUG: Found {len(check_gold_data)} CHECK_GOLD entries for Job {job_no}", 'multiple_jobs')
            
            # Process each lot in this job for cornet weights only
            total_lots = len(lots_data)
            for i, (lot_no, strips) in enumerate(lots_data.items()):
                is_last_lot = (i == total_lots - 1)  # Check if this is the last lot
                
                self.log(f"⚖️ Saving cornet weights for Lot {lot_no} in Job {job_no} ({i+1}/{total_lots})", 'multiple_jobs')
                
                # Load weight page
                weight_url = f"https://huid.manakonline.in/MANAK/SamplingweightingDeatils?requestNo={request_no}&jobNo={job_no}"
                self.driver.get(weight_url)
                time.sleep(3)
                
                # Select lot
                if not self._select_lot_in_portal(str(lot_no)):
                    self.log(f"❌ Failed to select Lot {lot_no} for Job {job_no}", 'multiple_jobs')
                    continue
                
                # Create lot_weight_data with strip data + CHECK_GOLD data
                all_strips_for_lot = strips + check_gold_data  # Include CHECK_GOLD data with each lot
                lot_weight_data = {
                    'strip_data': all_strips_for_lot,
                    'button_weight': job_data.get('total_button_weight', 0),
                    'scrap_weight': job_data.get('total_scrap_weight', 0)
                }
                
                # Fill and save cornet weights only
                self._fill_and_save_cornet_weights(lot_weight_data)
                
                self.log(f"✅ Saved cornet weights for Lot {lot_no} in Job {job_no}", 'multiple_jobs')
                
                # Submit for HUID only after the last lot (if auto-submit is enabled)
                if is_last_lot and self.auto_submit_huid_var.get():
                    self.log(f"📤 Submitting HUID for Job {job_no} (after last lot {lot_no})", 'multiple_jobs')
                    self._submit_huid_for_job()
            
            return True
            
        except Exception as e:
            self.log(f"❌ Error saving cornet weights for Job {job_no}: {str(e)}", 'multiple_jobs')
            return False

    def _fill_and_save_initial_weights(self, lot_weight_data):
        """Fill and save initial weights from API data - includes all strip data"""
        try:
            # DEBUG: Log the actual data structure received
            self.log(f"🔍 DEBUG: Received lot_weight_data keys: {list(lot_weight_data.keys())}", 'multiple_jobs')
            self.log(f"🔍 DEBUG: Received lot_weight_data: {lot_weight_data}", 'multiple_jobs')
            
            filled_count = 0
            
            # 1. Fill Sample Drawn Weight (Scrap Weight)
            scrap_weight = lot_weight_data.get('scrap_weight', 0)
            if scrap_weight:
                try:
                    element = self.driver.find_element(By.ID, 'num_scrap_weight')
                    if element.is_displayed() and element.is_enabled():
                        # Try to clear the field first
                        try:
                            element.clear()
                        except:
                            # If clear fails, try selecting all and deleting
                            element.send_keys(Keys.CONTROL + "a")
                            element.send_keys(Keys.DELETE)
                        
                        element.send_keys(str(scrap_weight))
                        filled_count += 1
                        self.log(f"✅ Filled scrap weight: {scrap_weight}", 'multiple_jobs')
                        
                        # Save scrap weight
                        save_btn = self.driver.find_element(By.ID, 'savesampleweight')
                        if save_btn.is_displayed() and save_btn.is_enabled():
                            save_btn.click()
                            time.sleep(1)
                            self.log("💾 Saved scrap weight", 'multiple_jobs')
                    else:
                        self.log(f"⚠️ Scrap weight field not interactable (displayed: {element.is_displayed()}, enabled: {element.is_enabled()})", 'multiple_jobs')
                except Exception as e:
                    self.log(f"❌ Error filling scrap weight: {str(e)}", 'multiple_jobs')
            
            # 2. Fill Button Weight
            button_weight = lot_weight_data.get('button_weight', 0)
            if button_weight:
                try:
                    element = self.driver.find_element(By.ID, 'buttonweight')
                    if element.is_displayed() and element.is_enabled():
                        # Try to clear the field first
                        try:
                            element.clear()
                        except:
                            # If clear fails, try selecting all and deleting
                            element.send_keys(Keys.CONTROL + "a")
                            element.send_keys(Keys.DELETE)
                        
                        element.send_keys(str(button_weight))
                        filled_count += 1
                        self.log(f"✅ Filled button weight: {button_weight}", 'multiple_jobs')
                        
                        # Save button weight
                        save_btn = self.driver.find_element(By.ID, 'savebuttonweight')
                        if save_btn.is_displayed() and save_btn.is_enabled():
                            save_btn.click()
                            time.sleep(1)
                            self.log("💾 Saved button weight", 'multiple_jobs')
                    else:
                        self.log(f"⚠️ Button weight field not interactable (displayed: {element.is_displayed()}, enabled: {element.is_enabled()})", 'multiple_jobs')
                except Exception as e:
                    self.log(f"❌ Error filling button weight: {str(e)}", 'multiple_jobs')
            
            # 3. Fill all Initial Weights, Ag, Pb, Cu from strip data (skip cornet)
            # First, let's try to fill using the actual API data structure
            # Based on the main app, the API provides strip data with keys like 'initial', 'ag', 'cu', 'pb'
            
            # Try to extract strip data from the lot_weight_data
            # The API might provide strip data in a different structure
            strip_data = lot_weight_data.get('strip_data', [])
            if strip_data:
                self.log(f"🔍 DEBUG: Found strip_data: {strip_data}", 'multiple_jobs')
                # Process strip data similar to main app
                self._fill_strip_data_from_api(strip_data)
            else:
                # Try direct field mapping as fallback
                self.log("🔍 DEBUG: No strip_data found, trying direct field mapping", 'multiple_jobs')
                self._fill_initial_weights_direct_mapping(lot_weight_data)
            
            # 4. Click Save (Initial Weight) button for strips
            try:
                save_btn = self.driver.find_element(By.ID, 'chechkgoldM12')
                if save_btn.is_displayed() and save_btn.is_enabled():
                    save_btn.click()
                    self.log("💾 Clicked Save (Initial Weight) button for strips", 'multiple_jobs')
                    time.sleep(1)
                else:
                    self.log("⚠️ Save (Initial Weight) button for strips not interactable", 'multiple_jobs')
            except Exception as e:
                self.log(f"❌ Error clicking Save (Initial Weight) button for strips: {str(e)}", 'multiple_jobs')
            
            # Summary
            self.log(f"🎯 INITIAL WEIGHT FILL COMPLETE: {filled_count} fields filled", 'multiple_jobs')
            
        except Exception as e:
            self.log(f"❌ Error filling/saving initial weights: {str(e)}", 'multiple_jobs')
    
    def _fill_strip_data_from_api(self, strip_data):
        """Fill strip data from API structure similar to main app"""
        try:
            # This should match the main app's strip data processing
            for strip in strip_data:
                strip_no = str(strip.get('strip_no', ''))
                self.log(f"🔍 Processing Strip {strip_no} - Available keys: {list(strip.keys())}", 'multiple_jobs')
                
                if strip_no == '1':
                    mapping = {
                        'num_strip_weight_M11': 'initial',
                        'num_silver_weightM11': 'ag',
                        'num_copper_weightM11': 'cu',
                        'num_lead_weightM11': 'pb',
                        # Note: For initial weights, we don't fill cornet (M2) - that's for Save Cornet button
                    }
                    
                    for field_id, api_key in mapping.items():
                        if api_key in strip:
                            value = str(strip[api_key])
                            if value and value != '0' and value != '0.0':
                                try:
                                    element = self.driver.find_element(By.ID, field_id)
                                    if element.is_displayed() and element.is_enabled():
                                        # Try to clear the field first
                                        try:
                                            element.clear()
                                        except:
                                            # If clear fails, try selecting all and deleting
                                            element.send_keys(Keys.CONTROL + "a")
                                            element.send_keys(Keys.DELETE)
                                        
                                        element.send_keys(value)
                                        self.log(f"✅ Strip 1 - {field_id}: {value}", 'multiple_jobs')
                                    else:
                                        self.log(f"⚠️ Strip 1 - {field_id} not interactable (displayed: {element.is_displayed()}, enabled: {element.is_enabled()})", 'multiple_jobs')
                                except Exception as e:
                                    self.log(f"❌ Error filling Strip 1 {field_id}: {str(e)}", 'multiple_jobs')
                        else:
                            self.log(f"⚠️ Strip 1 - Missing API key: {api_key}", 'multiple_jobs')
                
                elif strip_no == '2':
                    mapping = {
                        'num_strip_weight_M12': 'initial',
                        'num_silver_weightM12': 'ag',
                        'num_copper_weightM12': 'cu',
                        'num_lead_weightM12': 'pb',
                        # Note: For initial weights, we don't fill cornet (M2) - that's for Save Cornet button
                    }
                    
                    for field_id, api_key in mapping.items():
                        if api_key in strip:
                            value = str(strip[api_key])
                            if value and value != '0' and value != '0.0':
                                try:
                                    element = self.driver.find_element(By.ID, field_id)
                                    if element.is_displayed() and element.is_enabled():
                                        # Try to clear the field first
                                        try:
                                            element.clear()
                                        except:
                                            # If clear fails, try selecting all and deleting
                                            element.send_keys(Keys.CONTROL + "a")
                                            element.send_keys(Keys.DELETE)
                                        
                                        element.send_keys(value)
                                        self.log(f"✅ Strip 2 - {field_id}: {value}", 'multiple_jobs')
                                    else:
                                        self.log(f"⚠️ Strip 2 - {field_id} not interactable (displayed: {element.is_displayed()}, enabled: {element.is_enabled()})", 'multiple_jobs')
                                except Exception as e:
                                    self.log(f"❌ Error filling Strip 2 {field_id}: {str(e)}", 'multiple_jobs')
                        else:
                            self.log(f"⚠️ Strip 2 - Missing API key: {api_key}", 'multiple_jobs')
                
                # Handle C1 and C2 (Check Gold) - these might be in separate entries or have different strip_no
                # For now, let's assume they're in the same structure but with different identifiers
                
                elif strip_no == 'C1':
                    mapping = {
                        'num_strip_weight_goldM11': 'initial',
                        'num_silver_weight_goldM11': 'ag',
                        'num_copper_weight_goldM11': 'cu',
                        'num_lead_weight_goldM11': 'pb',
                        # Note: For initial weights, we don't fill cornet (M2) - that's for Save Cornet button
                    }
                    
                    for field_id, api_key in mapping.items():
                        if api_key in strip:
                            value = str(strip[api_key])
                            if value and value != '0' and value != '0.0':
                                try:
                                    element = self.driver.find_element(By.ID, field_id)
                                    if element.is_displayed() and element.is_enabled():
                                        # Try to clear the field first
                                        try:
                                            element.clear()
                                        except:
                                            # If clear fails, try selecting all and deleting
                                            element.send_keys(Keys.CONTROL + "a")
                                            element.send_keys(Keys.DELETE)
                                        
                                        element.send_keys(value)
                                        self.log(f"✅ C1 - {field_id}: {value}", 'multiple_jobs')
                                    else:
                                        self.log(f"⚠️ C1 - {field_id} not interactable (displayed: {element.is_displayed()}, enabled: {element.is_enabled()})", 'multiple_jobs')
                                except Exception as e:
                                    self.log(f"❌ Error filling C1 {field_id}: {str(e)}", 'multiple_jobs')
                        else:
                            self.log(f"⚠️ C1 - Missing API key: {api_key}", 'multiple_jobs')
                
                elif strip_no == 'C2':
                    mapping = {
                        'num_strip_weight_goldM12': 'initial',
                        'num_silver_weight_goldM12': 'ag',
                        'num_copper_weight_goldM12': 'cu',
                        'num_lead_weight_goldM12': 'pb',
                        # Note: For initial weights, we don't fill cornet (M2) - that's for Save Cornet button
                    }
                    
                    for field_id, api_key in mapping.items():
                        if api_key in strip:
                            value = str(strip[api_key])
                            if value and value != '0' and value != '0.0':
                                try:
                                    element = self.driver.find_element(By.ID, field_id)
                                    if element.is_displayed() and element.is_enabled():
                                        # Try to clear the field first
                                        try:
                                            element.clear()
                                        except:
                                            # If clear fails, try selecting all and deleting
                                            element.send_keys(Keys.CONTROL + "a")
                                            element.send_keys(Keys.DELETE)
                                        
                                        element.send_keys(value)
                                        self.log(f"✅ C2 - {field_id}: {value}", 'multiple_jobs')
                                    else:
                                        self.log(f"⚠️ C2 - {field_id} not interactable (displayed: {element.is_displayed()}, enabled: {element.is_enabled()})", 'multiple_jobs')
                                except Exception as e:
                                    self.log(f"❌ Error filling C2 {field_id}: {str(e)}", 'multiple_jobs')
                        else:
                            self.log(f"⚠️ C2 - Missing API key: {api_key}", 'multiple_jobs')
                
                else:
                    self.log(f"⚠️ Unknown strip number: {strip_no}", 'multiple_jobs')
                
        except Exception as e:
            self.log(f"❌ Error filling strip data from API: {str(e)}", 'multiple_jobs')
    
    def _fill_initial_weights_direct_mapping(self, lot_weight_data):
        """Fallback method for direct field mapping"""
        try:
            # Map API fields to UI fields (fallback method)
            field_mapping = {
                'num_strip_weight_M11': 'strip1_initial',
                'num_strip_weight_M12': 'strip2_initial',
                'num_strip_weight_goldM11': 'c1_initial',
                'num_strip_weight_goldM12': 'c2_initial',
                'num_silver_weightM11': 'strip1_silver',
                'num_silver_weightM12': 'strip2_silver',
                'num_silver_weight_goldM11': 'c1_silver',
                'num_silver_weight_goldM12': 'c2_silver',
                'num_copper_weightM11': 'strip1_copper',
                'num_copper_weightM12': 'strip2_copper',
                'num_copper_weight_goldM11': 'c1_copper',
                'num_copper_weight_goldM12': 'c2_copper',
                'num_lead_weightM11': 'strip1_lead',
                'num_lead_weightM12': 'strip2_lead',
                'num_lead_weight_goldM11': 'c1_lead',
                'num_lead_weight_goldM12': 'c2_lead'
            }
            
            initial_weight_fields = [
                'num_strip_weight_M11', 'num_strip_weight_M12',
                'num_strip_weight_goldM11', 'num_strip_weight_goldM12',
                'num_silver_weightM11', 'num_silver_weightM12',
                'num_silver_weight_goldM11', 'num_silver_weight_goldM12',
                'num_copper_weightM11', 'num_copper_weightM12',
                'num_copper_weight_goldM11', 'num_copper_weight_goldM12',
                'num_lead_weightM11', 'num_lead_weightM12',
                'num_lead_weight_goldM11', 'num_lead_weight_goldM12'
            ]
            
            for field_id in initial_weight_fields:
                try:
                    api_key = field_mapping.get(field_id)
                    if api_key and api_key in lot_weight_data:
                        value = lot_weight_data[api_key]
                        if value and str(value) != '0' and str(value) != '0.0':
                            element = self.driver.find_element(By.ID, field_id)
                            if element.is_displayed() and element.is_enabled():
                                element.clear()
                                element.send_keys(str(value))
                                self.log(f"✅ Direct mapping - {field_id}: {value}", 'multiple_jobs')
                    else:
                        self.log(f"⚠️ No API key mapping for {field_id}", 'multiple_jobs')
                except Exception as e:
                    self.log(f"❌ Error filling {field_id}: {str(e)}", 'multiple_jobs')
                    
        except Exception as e:
            self.log(f"❌ Error in direct field mapping: {str(e)}", 'multiple_jobs')

    def _fill_and_save_cornet_weights(self, lot_weight_data):
        """Fill and save cornet weights from API data - M2 (after assaying) fields"""
        try:
            # DEBUG: Log the actual data structure received
            self.log(f"🔍 DEBUG: Received lot_weight_data keys: {list(lot_weight_data.keys())}", 'multiple_jobs')
            self.log(f"🔍 DEBUG: Received lot_weight_data: {lot_weight_data}", 'multiple_jobs')
            
            filled_count = 0
            
            # Fill cornet data from API (M2 - after assaying fields)
            if 'strip_data' in lot_weight_data:
                self.log(f"🔍 DEBUG: Found strip_data for cornet weights: {lot_weight_data['strip_data']}", 'multiple_jobs')
                filled_count += self._fill_cornet_data_from_api(lot_weight_data['strip_data'])
            
            # Click Save Cornet Values button
            try:
                save_btn = self.driver.find_element(By.ID, 'savecornetvalues')
                if save_btn.is_displayed() and save_btn.is_enabled():
                    save_btn.click()
                    self.log("💾 Clicked Save (Cornet Weight) button", 'multiple_jobs')
                    time.sleep(1)
                    
                    # Handle alerts
                    try:
                        alert = self.driver.switch_to.alert
                        alert_text = alert.text
                        self.log(f"🔔 Alert: {alert_text}", 'multiple_jobs')
                        alert.accept()
                        time.sleep(1)
                    except Exception as e:
                        self.log(f"❌ Error handling first alert: {str(e)}", 'multiple_jobs')
                    
                    try:
                        alert = self.driver.switch_to.alert
                        alert_text = alert.text
                        self.log(f"🔔 Result Alert: {alert_text}", 'multiple_jobs')
                        alert.accept()
                        time.sleep(1)
                    except Exception as e:
                        self.log(f"❌ Error handling result alert: {str(e)}", 'multiple_jobs')
                else:
                    self.log("⚠️ Save (Cornet Weight) button not interactable", 'multiple_jobs')
            except Exception as e:
                self.log(f"❌ Error clicking Save (Cornet Weight) button: {str(e)}", 'multiple_jobs')
            
            # Summary
            self.log(f"🎯 CORNET WEIGHT FILL COMPLETE: {filled_count} fields filled", 'multiple_jobs')
            
        except Exception as e:
            self.log(f"❌ Error filling/saving cornet weights: {str(e)}", 'multiple_jobs')
    
    def _fill_cornet_data_from_api(self, strip_data):
        """Fill cornet data from API structure - M2 (after assaying) fields only"""
        try:
            filled_count = 0
            # This should fill only the M2 (after assaying) fields
            for strip in strip_data:
                strip_no = str(strip.get('strip_no', ''))
                self.log(f"🔍 Processing Cornet data for Strip {strip_no} - Available keys: {list(strip.keys())}", 'multiple_jobs')
                
                # Define field mappings for cornet (M2) fields only
                if strip_no == '1':
                    mapping = {
                        'num_cornet_weightM11': 'cornet',  # M2 field for Strip 1
                    }
                    
                elif strip_no == '2':
                    mapping = {
                        'num_cornet_weightM12': 'cornet',  # M2 field for Strip 2
                    }
                    
                elif strip_no == 'C1':
                    mapping = {
                        'num_cornet_weight_goldM11': 'cornet',  # M2 field for C1
                    }
                    
                elif strip_no == 'C2':
                    mapping = {
                        'num_cornet_weight_goldM12': 'cornet',  # M2 field for C2
                    }
                    
                else:
                    self.log(f"⚠️ Unknown strip number for cornet: {strip_no}", 'multiple_jobs')
                    continue
                
                # Fill fields for this strip
                for field_id, api_key in mapping.items():
                    if api_key in strip:
                        value = str(strip[api_key])
                        if value and value != '0' and value != '0.0':
                            try:
                                element = self.driver.find_element(By.ID, field_id)
                                if element.is_displayed() and element.is_enabled():
                                    # Try to clear the field first
                                    try:
                                        element.clear()
                                    except:
                                        # If clear fails, try selecting all and deleting
                                        element.send_keys(Keys.CONTROL + "a")
                                        element.send_keys(Keys.DELETE)
                                    
                                    element.send_keys(value)
                                    filled_count += 1
                                    self.log(f"✅ {strip_no} - {field_id}: {value}", 'multiple_jobs')
                                else:
                                    self.log(f"⚠️ {strip_no} - {field_id} not interactable (displayed: {element.is_displayed()}, enabled: {element.is_enabled()})", 'multiple_jobs')
                            except Exception as e:
                                self.log(f"❌ Error filling {strip_no} {field_id}: {str(e)}", 'multiple_jobs')
                    else:
                        self.log(f"⚠️ {strip_no} - Missing API key for cornet: {api_key}", 'multiple_jobs')
                        
            return filled_count
                    
        except Exception as e:
            self.log(f"❌ Error processing cornet data: {str(e)}", 'multiple_jobs')
            return 0
    
    def update_status(self, status, color='#6c757d'):
        """Update status label"""
        self.status_label.config(text=status, foreground=color)
    
    def update_progress(self, progress):
        """Update progress label"""
        self.progress_label.config(text=progress)
    
    def update_results(self, results):
        """Update results label"""
        self.results_label.config(text=results)
    
    def update_jobs_list(self, job_summary):
        """Update jobs list in treeview"""
        # Clear existing items
        for item in self.jobs_tree.get_children():
            self.jobs_tree.delete(item)
        
        # Add new items
        for job in job_summary:
            self.jobs_tree.insert('', 'end', values=(
                job['job_no'],
                job['request_no'],
                job['total_lots'],
                f"{job['total_button_weight']:.2f}",
                f"{job['total_scrap_weight']:.2f}",
                "Pending"
            ))
    
    def update_job_status(self, job_no, status):
        """Update status of a specific job in treeview"""
        for item in self.jobs_tree.get_children():
            values = self.jobs_tree.item(item, 'values')
            if values[0] == str(job_no):
                # Update the status column
                new_values = list(values)
                new_values[5] = status
                self.jobs_tree.item(item, values=new_values)
                break
    
    def log(self, message, category='multiple_jobs'):
        """Add message to log text area and main app log"""
        timestamp = time.strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        # Update internal log text area (thread-safe)
        if self.log_text:
            try:
                root = self.notebook.winfo_toplevel()
                root.after(0, lambda: self._update_log_text(log_message))
            except Exception as e:
                print(f"Internal log error: {e}")
        
        # Also call the main app's log function
        if self.main_log_callback:
            try:
                self.main_log_callback(message, category)
            except Exception as e:
                print(f"External log error: {e}")
    
    def _update_log_text(self, log_message):
        """Update log text area from main thread"""
        try:
            if self.log_text:
                self.log_text.insert(tk.END, log_message)
                self.log_text.see(tk.END)
                # Force update to ensure the log appears immediately
                self.log_text.update_idletasks()
        except Exception as e:
            print(f"Log update error: {e}")
    
    def setup_jobs_card_list_tab(self, notebook):
        """Setup Jobs Card List tab"""
        jobs_card_frame = ttk.Frame(notebook)
        notebook.add(jobs_card_frame, text="📋 Jobs Card List")
        
        # Main horizontal layout
        main_horizontal = ttk.Frame(jobs_card_frame)
        main_horizontal.pack(fill='both', expand=True, padx=8, pady=8)
        
        # LEFT SECTION - Controls (30% width)
        left_section = ttk.Frame(main_horizontal)
        left_section.pack(side='left', fill='both', expand=True, padx=(0, 8))
        
        # RIGHT SECTION - Data Table (70% width)
        right_section = ttk.Frame(main_horizontal)
        right_section.pack(side='right', fill='both', expand=True, padx=(8, 0))
        
        # Setup left and right sections
        self.setup_jobs_card_left_section(left_section)
        self.setup_jobs_card_right_section(right_section)
    
    def setup_jobs_card_left_section(self, parent):
        """Setup left section with controls"""
        
        # Control Panel Card
        control_card = ttk.LabelFrame(parent, text="🎛️ Control Panel", padding=10)
        control_card.pack(fill='x', pady=(0, 10))
        
        # Load Data Button
        self.load_jobs_card_btn = ttk.Button(
            control_card, 
            text="📥 Load Jobs Card Data", 
            command=self.load_jobs_card_data
        )
        self.load_jobs_card_btn.pack(fill='x', pady=(0, 8))
        
        # Auto Monitor Toggle
        self.auto_monitor_var = tk.BooleanVar(value=False)
        self.auto_monitor_check = ttk.Checkbutton(
            control_card,
            text="🔄 Auto Monitor (1 min)",
            variable=self.auto_monitor_var,
            command=self.toggle_auto_monitor
        )
        self.auto_monitor_check.pack(fill='x', pady=(0, 8))
        
        # Fetch Job Numbers Button
        self.fetch_job_numbers_btn = ttk.Button(
            control_card, 
            text="🔍 Fetch Missing Job Numbers", 
            command=self.fetch_missing_job_numbers,
            state='disabled'
        )
        self.fetch_job_numbers_btn.pack(fill='x', pady=(0, 8))
        
        # Status Display
        status_frame = ttk.LabelFrame(parent, text="📊 Status", padding=10)
        status_frame.pack(fill='x', pady=(0, 10))
        
        self.jobs_card_status_label = ttk.Label(status_frame, text="Ready", foreground='#6c757d')
        self.jobs_card_status_label.pack(anchor='w')
        
        self.jobs_card_progress_label = ttk.Label(status_frame, text="No data loaded")
        self.jobs_card_progress_label.pack(anchor='w')
        
        # Statistics
        stats_frame = ttk.LabelFrame(parent, text="📈 Statistics", padding=10)
        stats_frame.pack(fill='x')
        
        self.total_items_label = ttk.Label(stats_frame, text="Total Items: 0")
        self.total_items_label.pack(anchor='w')
        
        self.missing_job_no_label = ttk.Label(stats_frame, text="Missing Job No: 0")
        self.missing_job_no_label.pack(anchor='w')
        
        self.completed_label = ttk.Label(stats_frame, text="Completed: 0")
        self.completed_label.pack(anchor='w')
    
    def setup_jobs_card_right_section(self, parent):
        """Setup right section with data table"""
        
        # Data Table
        table_frame = ttk.LabelFrame(parent, text="📋 Jobs Card Data", padding=10)
        table_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        # Create Treeview
        columns = ('ID', 'Request No', 'Item', 'Pcs', 'Purity', 'Weight', 'Job No', 'Status')
        self.jobs_card_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=15)
        
        # Define column headings and widths
        column_widths = {'ID': 60, 'Request No': 100, 'Item': 80, 'Pcs': 50, 'Purity': 70, 'Weight': 80, 'Job No': 80, 'Status': 100}
        for col in columns:
            self.jobs_card_tree.heading(col, text=col)
            self.jobs_card_tree.column(col, width=column_widths.get(col, 100))
        
        # Add scrollbars
        v_scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.jobs_card_tree.yview)
        h_scrollbar = ttk.Scrollbar(table_frame, orient='horizontal', command=self.jobs_card_tree.xview)
        self.jobs_card_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack treeview and scrollbars
        self.jobs_card_tree.pack(side='left', fill='both', expand=True)
        v_scrollbar.pack(side='right', fill='y')
        h_scrollbar.pack(side='bottom', fill='x')
        
        # Processing Log
        log_frame = ttk.LabelFrame(parent, text="📝 Processing Log", padding=10)
        log_frame.pack(fill='both', expand=True)
        
        self.jobs_card_log_text = tk.Text(log_frame, height=8, wrap='word', state='disabled')
        log_scrollbar = ttk.Scrollbar(log_frame, orient='vertical', command=self.jobs_card_log_text.yview)
        self.jobs_card_log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.jobs_card_log_text.pack(side='left', fill='both', expand=True)
        log_scrollbar.pack(side='right', fill='y')
    
    def get_firm_id(self):
        """Get firm_id from device license or main app settings"""
        try:
            # First, try to get firm_id from device license
            if self.main_app and hasattr(self.main_app, 'license_manager'):
                license_manager = self.main_app.license_manager
                if hasattr(license_manager, 'firm_id') and license_manager.firm_id:
                    print(f"🏢 Using firm_id from device license: {license_manager.firm_id}")
                    return license_manager.firm_id
            
            # Fallback to app settings
            if self.main_app and hasattr(self.main_app, 'firm_id_var'):
                firm_id = self.main_app.firm_id_var.get().strip()
                return firm_id if firm_id else '2'  # Default to 2 if empty
            return '2'  # Default firm_id
        except Exception as e:
            self.log_jobs_card(f"❌ Error getting firm_id: {e}")
            return '2'  # Default firm_id
    
    def refresh_firm_id_from_license(self):
        """Refresh firm_id from license - called after license verification"""
        try:
            # This method can be called to refresh firm_id after license verification
            # The actual firm_id is retrieved dynamically in get_firm_id()
            self.log_jobs_card("🏢 Firm ID refreshed from license verification")
        except Exception as e:
            self.log_jobs_card(f"❌ Error refreshing firm_id: {str(e)}")
    
    def get_api_url_from_settings(self):
        """Get Report API URL from main app settings"""
        try:
            if self.main_app and hasattr(self.main_app, 'report_api_url_var'):
                api_url = self.main_app.report_api_url_var.get().strip()
                return api_url if api_url else "https://hallmarkpro.prosenjittechhub.com/admin/get_report_by_id.php"
            return "https://hallmarkpro.prosenjittechhub.com/admin/get_report_by_id.php"  # Default API URL
        except Exception as e:
            self.log_jobs_card(f"❌ Error getting Report API URL: {e}")
            return "https://hallmarkpro.prosenjittechhub.com/admin/get_report_by_id.php"  # Default API URL
    
    def get_database_connection(self):
        """Get database connection with retry logic"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # Add connection parameters for executable stability
                db_config_with_params = self.db_config.copy()
                db_config_with_params.update({
                    'connection_timeout': 15,
                    'autocommit': True,
                    'raise_on_warnings': False,
                    'use_pure': True,  # Use pure Python implementation for exe
                    'auth_plugin': 'mysql_native_password'  # Fix for MySQL 8.0+ authentication
                })
                
                self.log_jobs_card(f"🔌 Attempting database connection (attempt {attempt + 1})...")
                connection = mysql.connector.connect(**db_config_with_params)
                
                # Test connection
                cursor = connection.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                cursor.close()
                
                self.log_jobs_card(f"✅ Database connection successful")
                return connection
                
            except Error as e:
                self.log_jobs_card(f"❌ MySQL connection error (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    self.log_jobs_card(f"⏳ Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    self.log_jobs_card(f"❌ All connection attempts failed")
                    return None
            except Exception as e:
                self.log_jobs_card(f"❌ Unexpected error (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    return None
        
        return None
    
    def load_jobs_card_data(self):
        """Load jobs card data from database"""
        threading.Thread(target=self._load_jobs_card_data_worker, daemon=True).start()
    
    def _load_jobs_card_data_worker(self):
        """Worker thread for loading jobs card data"""
        try:
            self.update_jobs_card_status("Loading data...", '#ffc107')
            self.log_jobs_card("🔍 Loading jobs card data from database...")
            
            connection = self.get_database_connection()
            if not connection:
                self.update_jobs_card_status("Database Error", '#dc3545')
                return
            
            cursor = connection.cursor()
            
            # Get firm_id from settings
            firm_id = self.get_firm_id()
            
            # Query to get jobs card data (limit 200, ordered by latest first, filtered by firm_id)
            query = """
                SELECT id, request_no, item, pcs, purity, weight, job_no, status, created_at
                FROM jobs_card 
                WHERE firm_id = %s
                ORDER BY id DESC 
                LIMIT 200
            """
            
            cursor.execute(query, (firm_id,))
            results = cursor.fetchall()
            
            # Clear existing data
            for item in self.jobs_card_tree.get_children():
                self.jobs_card_tree.delete(item)
            
            # Add data to treeview
            missing_job_no_count = 0
            for row in results:
                id_val, request_no, item, pcs, purity, weight, job_no, status, created_at = row
                
                # Determine status
                if not job_no or job_no == '' or job_no == '0':
                    status_text = "Missing Job No"
                    missing_job_no_count += 1
                else:
                    status_text = "Complete"
                
                # Insert into treeview
                self.jobs_card_tree.insert('', 'end', values=(
                    id_val,
                    request_no,
                    item,
                    pcs,
                    purity,
                    f"{weight:.3f}" if weight else "0.000",
                    job_no or "N/A",
                    status_text
                ))
            
            # Update statistics
            total_items = len(results)
            completed_count = total_items - missing_job_no_count
            
            self.total_items_label.config(text=f"Total Items: {total_items}")
            self.missing_job_no_label.config(text=f"Missing Job No: {missing_job_no_count}")
            self.completed_label.config(text=f"Completed: {completed_count}")
            
            # Enable fetch button if there are missing job numbers
            if missing_job_no_count > 0:
                self.fetch_job_numbers_btn.config(state='normal')
            
            cursor.close()
            connection.close()
            
            self.update_jobs_card_status("Data Loaded", '#28a745')
            self.log_jobs_card(f"✅ Loaded {total_items} items ({missing_job_no_count} missing job numbers)")
            
        except Exception as e:
            self.update_jobs_card_status("Error", '#dc3545')
            self.log_jobs_card(f"❌ Error loading jobs card data: {str(e)}")
    
    def toggle_auto_monitor(self):
        """Toggle auto monitoring"""
        if self.auto_monitor_var.get():
            self.start_auto_monitoring()
        else:
            self.stop_auto_monitoring()
    
    def start_auto_monitoring(self):
        """Start auto monitoring for new records"""
        if self.jobs_card_monitoring:
            return
        
        self.jobs_card_monitoring = True
        self.monitor_thread = threading.Thread(target=self._auto_monitor_worker, daemon=True)
        self.monitor_thread.start()
        self.log_jobs_card("🔄 Auto monitoring started (checking every 1 minute)")
    
    def stop_auto_monitoring(self):
        """Stop auto monitoring"""
        self.jobs_card_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
        self.log_jobs_card("⏹️ Auto monitoring stopped")
    
    def _auto_monitor_worker(self):
        """Worker thread for auto monitoring"""
        while self.jobs_card_monitoring:
            try:
                # Check for new records without job_no
                connection = self.get_database_connection()
                if not connection:
                    time.sleep(60)  # Wait 1 minute before retry
                    continue
                
                cursor = connection.cursor()
                
                # Get firm_id from settings
                firm_id = self.get_firm_id()
                
                # Query for records without job_no (filtered by firm_id)
                query = """
                    SELECT id, request_no, item, pcs, purity, weight
                    FROM jobs_card 
                    WHERE firm_id = %s AND (job_no IS NULL OR job_no = '' OR job_no = '0')
                    ORDER BY id DESC
                    LIMIT 50
                """
                
                cursor.execute(query, (firm_id,))
                results = cursor.fetchall()
                
                if results:
                    self.log_jobs_card(f"🔍 Found {len(results)} records without job numbers")
                    
                    # Group by request_no
                    request_groups = {}
                    for row in results:
                        id_val, request_no, item, pcs, purity, weight = row
                        if request_no not in request_groups:
                            request_groups[request_no] = []
                        request_groups[request_no].append(row)
                    
                    # Process each request_no
                    for request_no, items in request_groups.items():
                        self.log_jobs_card(f"🔍 Processing Request No: {request_no} ({len(items)} items)")
                        self.fetch_job_numbers_for_request(request_no, items)
                
                cursor.close()
                connection.close()
                
            except Exception as e:
                self.log_jobs_card(f"❌ Auto monitor error: {str(e)}")
            
            # Wait 1 minute before next check
            time.sleep(60)
    
    def fetch_missing_job_numbers(self):
        """Fetch missing job numbers for all records"""
        threading.Thread(target=self._fetch_missing_job_numbers_worker, daemon=True).start()
    
    def _fetch_missing_job_numbers_worker(self):
        """Worker thread for fetching missing job numbers"""
        try:
            connection = self.get_database_connection()
            if not connection:
                return
            
            cursor = connection.cursor()
            
            # Get firm_id from settings
            firm_id = self.get_firm_id()
            
            # Get all records without job_no (filtered by firm_id)
            query = """
                SELECT id, request_no, item, pcs, purity, weight
                FROM jobs_card 
                WHERE firm_id = %s AND (job_no IS NULL OR job_no = '' OR job_no = '0')
                ORDER BY request_no, id
            """
            
            cursor.execute(query, (firm_id,))
            results = cursor.fetchall()
            
            if not results:
                self.log_jobs_card("✅ No records found without job numbers")
                return
            
            # Group by request_no
            request_groups = {}
            for row in results:
                id_val, request_no, item, pcs, purity, weight = row
                if request_no not in request_groups:
                    request_groups[request_no] = []
                request_groups[request_no].append(row)
            
            total_requests = len(request_groups)
            processed_requests = 0
            
            self.log_jobs_card(f"🔍 Found {total_requests} unique request numbers to process")
            
            for request_no, items in request_groups.items():
                processed_requests += 1
                self.log_jobs_card(f"📋 Processing Request No: {request_no} ({processed_requests}/{total_requests}) - {len(items)} items")
                self.fetch_job_numbers_for_request(request_no, items)
            
            cursor.close()
            connection.close()
            
            # Reload data to show updated results
            self.load_jobs_card_data()
            
        except Exception as e:
            self.log_jobs_card(f"❌ Error fetching job numbers: {str(e)}")
    
    def fetch_job_numbers_for_request(self, request_no, items):
        """Fetch job numbers for a specific request"""
        try:
            if not self.driver:
                self.log_jobs_card("❌ Browser not available for job number fetching")
                return
            
            # Navigate to QM list page
            qm_list_url = "https://huid.manakonline.in/MANAK/qualityManagerDesk_ListCompleted?hmType=HMQM"
            self.driver.get(qm_list_url)
            time.sleep(3)
            
            # Find the request in the list
            request_found = False
            try:
                # Look for the request number in the table
                request_elements = self.driver.find_elements(By.XPATH, f"//td[contains(text(), '{request_no}')]")
                if request_elements:
                    request_found = True
                    self.log_jobs_card(f"✅ Found Request {request_no} in QM list")
                else:
                    self.log_jobs_card(f"⚠️ Request {request_no} not found in QM list")
                    return
            except Exception as e:
                self.log_jobs_card(f"❌ Error finding request {request_no}: {str(e)}")
                return
            
            if not request_found:
                return
            
            # Get all job card links for this request
            job_card_links = []
            try:
                # Find the row containing the request number
                request_row = self.driver.find_element(By.XPATH, f"//td[contains(text(), '{request_no}')]/..")
                
                # Find all "QM Job Card View" links in this row or nearby rows
                links = request_row.find_elements(By.XPATH, ".//a[contains(text(), 'QM Job Card View')]")
                job_card_links.extend(links)
                
                self.log_jobs_card(f"🔍 Found {len(job_card_links)} job card links for Request {request_no}")
                
            except Exception as e:
                self.log_jobs_card(f"❌ Error finding job card links: {str(e)}")
                return
            
            # Process each job card link
            job_mappings = {}  # {item_category: job_no}
            
            for link in job_card_links:
                try:
                    # Get the href URL
                    href = link.get_attribute('href')
                    if not href:
                        continue
                    
                    # Extract job_no from URL parameters
                    job_no = self.extract_job_no_from_url(href)
                    if not job_no:
                        continue
                    
                    # Navigate to the job card page to get item category
                    self.driver.get(href)
                    time.sleep(2)
                    
                    # Extract item category from the page
                    item_category = self.extract_item_category_from_page()
                    if item_category:
                        job_mappings[item_category] = job_no
                        self.log_jobs_card(f"📋 Mapped {item_category} → Job No: {job_no}")
                    
                except Exception as e:
                    self.log_jobs_card(f"❌ Error processing job card link: {str(e)}")
                    continue
            
            # Update database with job numbers
            self.update_job_numbers_in_database(request_no, items, job_mappings)
            
        except Exception as e:
            self.log_jobs_card(f"❌ Error fetching job numbers for Request {request_no}: {str(e)}")
    
    def extract_job_no_from_url(self, url):
        """Extract job number from URL"""
        try:
            # URL format: ...&eJobCard=MTIyMTEyNDkw
            if 'eJobCard=' in url:
                encoded_job_no = url.split('eJobCard=')[1].split('&')[0]
                # Decode base64
                decoded_bytes = base64.b64decode(encoded_job_no)
                job_no = decoded_bytes.decode('utf-8')
                return job_no
            return None
        except Exception as e:
            self.log_jobs_card(f"❌ Error extracting job number from URL: {str(e)}")
            return None
    
    def extract_item_category_from_page(self):
        """Extract item category from job card page"""
        try:
            # Look for item category in the "Jeweller Item Declaration Details" table
            item_category_elements = self.driver.find_elements(By.XPATH, "//td[contains(@class, 'item-category') or contains(text(), 'Ring') or contains(text(), 'Chain') or contains(text(), 'Earring') or contains(text(), 'Bangle')]")
            
            for element in item_category_elements:
                text = element.text.strip()
                if text in ['Ring', 'Chain', 'Earrings', 'Earings', 'Bangles', 'Bangle', 'Necklace', 'Bracelet']:
                    return text
            
            # Fallback: look in the general area
            item_elements = self.driver.find_elements(By.XPATH, "//td[contains(text(), 'Ring') or contains(text(), 'Chain') or contains(text(), 'Earring') or contains(text(), 'Bangle')]")
            if item_elements:
                return item_elements[0].text.strip()
            
            return None
            
        except Exception as e:
            self.log_jobs_card(f"❌ Error extracting item category: {str(e)}")
            return None
    
    def update_job_numbers_in_database(self, request_no, items, job_mappings):
        """Update job numbers in database"""
        try:
            connection = self.get_database_connection()
            if not connection:
                return
            
            cursor = connection.cursor()
            updated_count = 0
            
            for item in items:
                id_val, req_no, item_name, pcs, purity, weight = item
                
                # Find matching job number
                job_no = None
                for category, job_number in job_mappings.items():
                    if self.items_match(item_name, category):
                        job_no = job_number
                        break
                
                if job_no:
                    # Update database
                    update_query = "UPDATE jobs_card SET job_no = %s WHERE id = %s"
                    cursor.execute(update_query, (job_no, id_val))
                    updated_count += 1
                    self.log_jobs_card(f"✅ Updated ID {id_val}: {item_name} → Job No {job_no}")
                else:
                    self.log_jobs_card(f"⚠️ No job number found for {item_name} (ID: {id_val})")
            
            connection.commit()
            cursor.close()
            connection.close()
            
            self.log_jobs_card(f"✅ Updated {updated_count} records for Request {request_no}")
            
        except Exception as e:
            self.log_jobs_card(f"❌ Error updating database: {str(e)}")
    
    def items_match(self, db_item, portal_item):
        """Check if database item matches portal item"""
        # Direct matching
        if db_item.lower() == portal_item.lower():
            return True
        
        # Special cases
        mappings = {
            'earings': 'earrings',
            'earring': 'earrings',
            'bangle': 'bangles'
        }
        
        normalized_db = mappings.get(db_item.lower(), db_item.lower())
        normalized_portal = mappings.get(portal_item.lower(), portal_item.lower())
        
        return normalized_db == normalized_portal
    
    def update_jobs_card_status(self, status, color='#6c757d'):
        """Update jobs card status label"""
        if hasattr(self, 'jobs_card_status_label'):
            self.jobs_card_status_label.config(text=status, foreground=color)
    
    def log_jobs_card(self, message):
        """Add message to jobs card log"""
        timestamp = time.strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        # Update log text area (thread-safe)
        if hasattr(self, 'jobs_card_log_text') and self.jobs_card_log_text:
            try:
                root = self.notebook.winfo_toplevel()
                root.after(0, lambda: self._update_jobs_card_log(log_message))
            except Exception as e:
                print(f"Jobs card log error: {e}")
        
        # Also call the main app's log function
        if self.main_log_callback:
            try:
                self.main_log_callback(message, 'jobs_card')
            except Exception as e:
                print(f"External jobs card log error: {e}")
    
    def _update_jobs_card_log(self, log_message):
        """Update jobs card log text area from main thread"""
        try:
            if hasattr(self, 'jobs_card_log_text') and self.jobs_card_log_text:
                self.jobs_card_log_text.config(state='normal')
                self.jobs_card_log_text.insert(tk.END, log_message)
                self.jobs_card_log_text.see(tk.END)
                self.jobs_card_log_text.config(state='disabled')
                self.jobs_card_log_text.update_idletasks()
        except Exception as e:
            print(f"Jobs card log update error: {e}")
