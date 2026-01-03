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
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys


class MultipleJobsProcessor:
    """Handles multiple job processing functionality"""
    
    def __init__(self, driver, log_callback, license_check_callback):
        self.driver = driver
        self.main_log_callback = log_callback  # Store external callback separately
        self.check_license_before_action = license_check_callback
        self.api_base_url = "https://your-api-domain.com"  # Update with your actual API URL
        self.notebook = None  # Will be set in setup_multiple_jobs_tab
        self.log_text = None  # Will be set when UI is created
    
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
    
    def setup_multiple_jobs_left_section(self, parent):
        """Setup left section with controls and settings"""
        
        # Report Processing Card
        report_card = ttk.LabelFrame(parent, text="📊 Report Processing", padding=10)
        report_card.pack(fill='x', pady=(0, 10))
        
        # API URL Input
        api_frame = ttk.Frame(report_card)
        api_frame.pack(fill='x', pady=(0, 8))
        
        ttk.Label(api_frame, text="Report API URL:", font=('Segoe UI', 9, 'bold')).pack(anchor='w')
        self.api_url_var = tk.StringVar(value='https://hallmarkpro.prosenjittechhub.com/admin/get_report_by_id.php?report_id=')
        api_entry = ttk.Entry(api_frame, textvariable=self.api_url_var, width=50)
        api_entry.pack(fill='x', pady=(2, 0))
        
        # Report ID Input
        report_id_frame = ttk.Frame(report_card)
        report_id_frame.pack(fill='x', pady=(0, 8))
        
        ttk.Label(report_id_frame, text="Report ID:", font=('Segoe UI', 9, 'bold')).pack(anchor='w')
        self.report_id_var = tk.StringVar()
        report_id_entry = ttk.Entry(report_id_frame, textvariable=self.report_id_var, width=20)
        report_id_entry.pack(fill='x', pady=(2, 0))
        
        # Load Data Button
        self.load_data_btn = ttk.Button(
            report_card, 
            text="📥 Load Report Data", 
            command=self.load_report_data
        )
        self.load_data_btn.pack(fill='x', pady=(8, 8))
        
        # Processing Buttons (initially disabled)
        self.save_initial_btn = ttk.Button(
            report_card, 
            text="💾 Save Initial Weights", 
            command=self.save_initial_weights_multiple_jobs,
            state='disabled'
        )
        self.save_initial_btn.pack(fill='x', pady=(0, 8))
        
        self.save_cornet_btn = ttk.Button(
            report_card, 
            text="💾 Save Cornet Weights", 
            command=self.save_cornet_weights_multiple_jobs,
            state='disabled'
        )
        self.save_cornet_btn.pack(fill='x', pady=(0, 8))
        
        self.process_all_btn = ttk.Button(
            report_card, 
            text="🚀 Process All Jobs", 
            command=self.process_multiple_jobs_from_report,
            state='disabled'
        )
        self.process_all_btn.pack(fill='x', pady=(0, 8))
        
        # Auto Submit HUID Option
        self.auto_submit_huid_var = tk.BooleanVar(value=True)
        auto_submit_check = ttk.Checkbutton(
            report_card,
            text="🔄 Auto Submit HUID",
            variable=self.auto_submit_huid_var
        )
        auto_submit_check.pack(fill='x', pady=(8, 0))
        
        # Status Display Card
        status_card = ttk.LabelFrame(parent, text="📊 Status", padding=10)
        status_card.pack(fill='x', pady=(0, 10))
        
        self.status_label = ttk.Label(status_card, text="Ready", foreground='#6c757d')
        self.status_label.pack(anchor='w')
        
        self.progress_label = ttk.Label(status_card, text="No data loaded")
        self.progress_label.pack(anchor='w')
        
        self.results_label = ttk.Label(status_card, text="")
        self.results_label.pack(anchor='w')
        
        # Jobs List Card
        jobs_card = ttk.LabelFrame(parent, text="📋 Jobs in Report", padding=10)
        jobs_card.pack(fill='both', expand=True)
        
        # Jobs listbox with scrollbar
        listbox_frame = ttk.Frame(jobs_card)
        listbox_frame.pack(fill='both', expand=True)
        
        self.jobs_listbox = tk.Listbox(listbox_frame, height=8)
        jobs_scrollbar = ttk.Scrollbar(listbox_frame, orient='vertical', command=self.jobs_listbox.yview)
        self.jobs_listbox.configure(yscrollcommand=jobs_scrollbar.set)
        
        self.jobs_listbox.pack(side='left', fill='both', expand=True)
        jobs_scrollbar.pack(side='right', fill='y')
    
    def setup_multiple_jobs_right_section(self, parent):
        """Setup right section with results and logs"""
        
        # Results Display
        results_card = ttk.LabelFrame(parent, text="📈 Processing Results", padding=10)
        results_card.pack(fill='both', expand=True, pady=(0, 10))
        
        # Results text area with scrollbar
        results_frame = ttk.Frame(results_card)
        results_frame.pack(fill='both', expand=True)
        
        self.results_text = tk.Text(results_frame, height=15, wrap='word', state='disabled')
        results_scrollbar = ttk.Scrollbar(results_frame, orient='vertical', command=self.results_text.yview)
        self.results_text.configure(yscrollcommand=results_scrollbar.set)
        
        self.results_text.pack(side='left', fill='both', expand=True)
        results_scrollbar.pack(side='right', fill='y')
        
        # Processing Log
        log_card = ttk.LabelFrame(parent, text="📝 Processing Log", padding=10)
        log_card.pack(fill='both', expand=True)
        
        # Log text area with scrollbar
        log_frame = ttk.Frame(log_card)
        log_frame.pack(fill='both', expand=True)
        
        self.log_text = tk.Text(log_frame, height=10, wrap='word', state='disabled')
        log_scrollbar = ttk.Scrollbar(log_frame, orient='vertical', command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side='left', fill='both', expand=True)
        log_scrollbar.pack(side='right', fill='y')
    
    def setup_api_url_shortcut(self):
        """Setup API URL shortcut button"""
        # This method can be called to add a shortcut button for API URL
        pass
    
    def toggle_api_url_visibility(self, event=None):
        """Toggle API URL visibility"""
        # This method can be implemented if needed
        pass
    
    def load_report_data(self):
        """Load report data from API"""
        report_id = self.report_id_var.get().strip()
        api_url = self.api_url_var.get().strip()
        
        if not report_id:
            messagebox.showerror("Error", "Please enter a Report ID")
            return
        
        if not api_url:
            messagebox.showerror("Error", "Please enter an API URL")
            return
        
        # Check license before proceeding
        if not self.check_license_before_action("load report data"):
            return
        
        # Start worker thread
        threading.Thread(target=self._load_report_data_worker, args=(report_id, api_url), daemon=True).start()
    
    def _load_report_data_worker(self, report_id, api_url):
        """Worker thread for loading report data"""
        try:
            self.update_status("Loading report data...", '#ffc107')
            self.log("🔍 Loading report data from API...")
            
            # Make API request
            full_url = f"{api_url}{report_id}"
            response = requests.get(full_url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    self.log("✅ Report data loaded successfully")
                    
                    # Extract job summary
                    job_summary = data.get('job_summary', [])
                    
                    # Update UI with loaded data
                    self.loaded_report_data = data
                    
                    # Enable processing buttons
                    self.save_initial_btn.config(state='normal')
                    self.save_cornet_btn.config(state='normal')
                    self.process_all_btn.config(state='normal')
                    
                    # Update jobs list
                    self.update_jobs_list(job_summary)
                    
                    self.update_status("Report data loaded", '#28a745')
                    self.log(f"📋 Found {len(job_summary)} jobs in report")
                    
                else:
                    self.update_status("API Error", '#dc3545')
                    self.log(f"❌ API returned error: {data.get('message', 'Unknown error')}")
            else:
                self.update_status("HTTP Error", '#dc3545')
                self.log(f"❌ HTTP {response.status_code}: {response.text}")
                
        except requests.exceptions.Timeout:
            self.update_status("Timeout", '#dc3545')
            self.log("❌ Request timeout - please check your connection")
        except requests.exceptions.RequestException as e:
            self.update_status("Network Error", '#dc3545')
            self.log(f"❌ Network error: {str(e)}")
        except Exception as e:
            self.update_status("Error", '#dc3545')
            self.log(f"❌ Unexpected error: {str(e)}")
    
    def save_initial_weights_multiple_jobs(self):
        """Save initial weights for multiple jobs"""
        if not hasattr(self, 'loaded_report_data') or not self.loaded_report_data:
            messagebox.showerror("Error", "Please load report data first")
            return
        
        if not self.driver:
            messagebox.showerror("Error", "Browser not available. Please open browser first.")
            return
        
        # Check license before proceeding
        if not self.check_license_before_action("save initial weights"):
            return
        
        # Start worker thread
        threading.Thread(target=self._save_initial_weights_worker_with_data, 
                        args=(self.loaded_report_data, self.report_id_var.get()), daemon=True).start()
    
    def save_cornet_weights_multiple_jobs(self):
        """Save cornet weights for multiple jobs"""
        if not hasattr(self, 'loaded_report_data') or not self.loaded_report_data:
            messagebox.showerror("Error", "Please load report data first")
            return
        
        if not self.driver:
            messagebox.showerror("Error", "Browser not available. Please open browser first.")
            return
        
        # Check license before proceeding
        if not self.check_license_before_action("save cornet weights"):
            return
        
        # Start worker thread
        threading.Thread(target=self._save_cornet_weights_worker_with_data, 
                        args=(self.loaded_report_data, self.report_id_var.get()), daemon=True).start()
    
    def process_multiple_jobs_from_report(self):
        """Process all jobs from the loaded report"""
        if not hasattr(self, 'loaded_report_data') or not self.loaded_report_data:
            messagebox.showerror("Error", "Please load report data first")
            return
        
        if not self.driver:
            messagebox.showerror("Error", "Browser not available. Please open browser first.")
            return
        
        # Check license before proceeding
        if not self.check_license_before_action("process multiple jobs"):
            return
        
        # Start worker thread
        threading.Thread(target=self._process_multiple_jobs_worker, 
                        args=(self.report_id_var.get(), self.api_url_var.get()), daemon=True).start()
    
    def _process_multiple_jobs_worker(self, report_id, api_url):
        """Worker thread for processing multiple jobs"""
        try:
            self.update_status("Processing multiple jobs...", '#ffc107')
            self.log("🚀 Starting multiple jobs processing...")
            
            # Get fresh data
            full_url = f"{api_url}{report_id}"
            response = requests.get(full_url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    job_summary = data.get('job_summary', [])
                    total_jobs = len(job_summary)
                    
                    self.log(f"📋 Processing {total_jobs} jobs...")
                    
                    successful_jobs = 0
                    failed_jobs = 0
                    
                    for i, job in enumerate(job_summary):
                        job_no = job.get('job_no')
                        request_no = job.get('request_no')
                        
                        if job_no and request_no:
                            self.log(f"🔄 Processing Job {i+1}/{total_jobs}: {job_no}")
                            
                            try:
                                # Process single job (initial + cornet + HUID submission)
                                success = self._process_single_job_from_report(data, job_no, request_no)
                                
                                if success:
                                    successful_jobs += 1
                                    self.log(f"✅ Job {job_no} completed successfully")
                                else:
                                    failed_jobs += 1
                                    self.log(f"❌ Job {job_no} failed")
                                    
                            except Exception as e:
                                failed_jobs += 1
                                self.log(f"❌ Job {job_no} error: {str(e)}")
                        else:
                            failed_jobs += 1
                            self.log(f"❌ Job {i+1} missing job_no or request_no")
                    
                    # Final results
                    self.update_status("Processing completed", '#28a745')
                    self.log(f"🎉 Processing completed: {successful_jobs} successful, {failed_jobs} failed")
                    
                else:
                    self.update_status("API Error", '#dc3545')
                    self.log(f"❌ API returned error: {data.get('message', 'Unknown error')}")
            else:
                self.update_status("HTTP Error", '#dc3545')
                self.log(f"❌ HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.update_status("Error", '#dc3545')
            self.log(f"❌ Processing error: {str(e)}")
    
    def _save_initial_weights_worker_with_data(self, data, report_id):
        """Worker thread for saving initial weights with pre-loaded data"""
        try:
            self.update_status("Saving initial weights...", '#ffc107')
            self.log("💾 Starting initial weights saving...")
            
            job_summary = data.get('job_summary', [])
            total_jobs = len(job_summary)
            
            self.log(f"📋 Processing {total_jobs} jobs for initial weights...")
            
            successful_jobs = 0
            failed_jobs = 0
            
            for i, job in enumerate(job_summary):
                job_no = job.get('job_no')
                request_no = job.get('request_no')
                
                if job_no and request_no:
                    self.log(f"🔄 Processing Job {i+1}/{total_jobs}: {job_no}")
                    
                    try:
                        success = self._save_initial_weights_for_job(data, job_no, request_no)
                        
                        if success:
                            successful_jobs += 1
                            self.log(f"✅ Job {job_no} initial weights saved")
                        else:
                            failed_jobs += 1
                            self.log(f"❌ Job {job_no} initial weights failed")
                            
                    except Exception as e:
                        failed_jobs += 1
                        self.log(f"❌ Job {job_no} error: {str(e)}")
                else:
                    failed_jobs += 1
                    self.log(f"❌ Job {i+1} missing job_no or request_no")
            
            # Final results
            self.update_status("Initial weights completed", '#28a745')
            self.log(f"🎉 Initial weights completed: {successful_jobs} successful, {failed_jobs} failed")
            
        except Exception as e:
            self.update_status("Error", '#dc3545')
            self.log(f"❌ Initial weights error: {str(e)}")
    
    def _save_cornet_weights_worker_with_data(self, data, report_id):
        """Worker thread for saving cornet weights with pre-loaded data"""
        try:
            self.update_status("Saving cornet weights...", '#ffc107')
            self.log("💾 Starting cornet weights saving...")
            
            job_summary = data.get('job_summary', [])
            total_jobs = len(job_summary)
            
            self.log(f"📋 Processing {total_jobs} jobs for cornet weights...")
            
            successful_jobs = 0
            failed_jobs = 0
            
            for i, job in enumerate(job_summary):
                job_no = job.get('job_no')
                request_no = job.get('request_no')
                
                if job_no and request_no:
                    self.log(f"🔄 Processing Job {i+1}/{total_jobs}: {job_no}")
                    
                    try:
                        success = self._save_cornet_weights_for_job(data, job_no, request_no)
                        
                        if success:
                            successful_jobs += 1
                            self.log(f"✅ Job {job_no} cornet weights saved")
                        else:
                            failed_jobs += 1
                            self.log(f"❌ Job {job_no} cornet weights failed")
                            
                    except Exception as e:
                        failed_jobs += 1
                        self.log(f"❌ Job {job_no} error: {str(e)}")
                else:
                    failed_jobs += 1
                    self.log(f"❌ Job {i+1} missing job_no or request_no")
            
            # Final results
            self.update_status("Cornet weights completed", '#28a745')
            self.log(f"🎉 Cornet weights completed: {successful_jobs} successful, {failed_jobs} failed")
            
        except Exception as e:
            self.update_status("Error", '#dc3545')
            self.log(f"❌ Cornet weights error: {str(e)}")
    
    def _save_initial_weights_worker(self, report_id, api_url):
        """Worker thread for saving initial weights"""
        try:
            self.update_status("Loading and saving initial weights...", '#ffc107')
            self.log("💾 Loading report data and saving initial weights...")
            
            # Get fresh data
            full_url = f"{api_url}{report_id}"
            response = requests.get(full_url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    self._save_initial_weights_worker_with_data(data, report_id)
                else:
                    self.update_status("API Error", '#dc3545')
                    self.log(f"❌ API returned error: {data.get('message', 'Unknown error')}")
            else:
                self.update_status("HTTP Error", '#dc3545')
                self.log(f"❌ HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.update_status("Error", '#dc3545')
            self.log(f"❌ Error: {str(e)}")
    
    def _save_cornet_weights_worker(self, report_id, api_url):
        """Worker thread for saving cornet weights"""
        try:
            self.update_status("Loading and saving cornet weights...", '#ffc107')
            self.log("💾 Loading report data and saving cornet weights...")
            
            # Get fresh data
            full_url = f"{api_url}{report_id}"
            response = requests.get(full_url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    self._save_cornet_weights_worker_with_data(data, report_id)
                else:
                    self.update_status("API Error", '#dc3545')
                    self.log(f"❌ API returned error: {data.get('message', 'Unknown error')}")
            else:
                self.update_status("HTTP Error", '#dc3545')
                self.log(f"❌ HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.update_status("Error", '#dc3545')
            self.log(f"❌ Error: {str(e)}")
    
    def _process_single_job_from_report(self, report_data, job_no, request_no):
        """Process a single job (initial + cornet + HUID submission)"""
        try:
            self.log(f"🔄 Processing Job {job_no} (Request: {request_no})")
            
            # Step 1: Save initial weights
            self.log(f"💾 Saving initial weights for Job {job_no}")
            initial_success = self._save_initial_weights_for_job(report_data, job_no, request_no)
            
            if not initial_success:
                self.log(f"❌ Failed to save initial weights for Job {job_no}")
                return False
            
            # Step 2: Save cornet weights
            self.log(f"💾 Saving cornet weights for Job {job_no}")
            cornet_success = self._save_cornet_weights_for_job(report_data, job_no, request_no)
            
            if not cornet_success:
                self.log(f"❌ Failed to save cornet weights for Job {job_no}")
                return False
            
            # Step 3: Submit HUID (if enabled)
            if self.auto_submit_huid_var.get():
                self.log(f"🔄 Submitting HUID for Job {job_no}")
                huid_success = self._submit_huid_for_job()
                
                if huid_success:
                    self.log(f"✅ HUID submitted successfully for Job {job_no}")
                else:
                    self.log(f"⚠️ HUID submission failed for Job {job_no}")
            
            return True
            
        except Exception as e:
            self.log(f"❌ Error processing Job {job_no}: {str(e)}")
            return False
    
    def _select_lot_in_portal(self, lot_no):
        """Select lot in the portal"""
        try:
            # Wait for lot selection dropdown
            lot_dropdown = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "lotSelection"))
            )
            
            # Click dropdown
            lot_dropdown.click()
            time.sleep(1)
            
            # Select lot
            lot_option = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, f"//option[@value='{lot_no}']"))
            )
            lot_option.click()
            time.sleep(2)
            
            return True
            
        except Exception as e:
            self.log(f"❌ Error selecting lot {lot_no}: {str(e)}")
            return False
    
    def _fill_weights_from_api_data(self, lot_weight_data):
        """Fill weights from API data"""
        try:
            # Fill scrap and button weights
            scrap_weight = lot_weight_data.get('scrap_weight', 0)
            button_weight = lot_weight_data.get('button_weight', 0)
            
            # Fill scrap weight
            scrap_element = self.driver.find_element(By.ID, "num_scrap_weight")
            scrap_element.clear()
            scrap_element.send_keys(str(scrap_weight))
            
            # Fill button weight
            button_element = self.driver.find_element(By.ID, "buttonweight")
            button_element.clear()
            button_element.send_keys(str(button_weight))
            
            # Fill strip data
            strip_data = lot_weight_data.get('strip_data', [])
            self._fill_strip_data_from_api(strip_data)
            
            return True
            
        except Exception as e:
            self.log(f"❌ Error filling weights: {str(e)}")
            return False
    
    def _save_weights_for_lot(self):
        """Save weights for current lot"""
        try:
            # Click save button
            save_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "saveinitialvalues"))
            )
            save_btn.click()
            time.sleep(2)
            
            # Handle any alerts
            try:
                alert = self.driver.switch_to.alert
                alert.accept()
                time.sleep(1)
            except:
                pass
            
            return True
            
        except Exception as e:
            self.log(f"❌ Error saving weights: {str(e)}")
            return False
    
    def _save_weights_for_lot_without_huid(self):
        """Save weights for current lot without HUID submission"""
        try:
            # Click save button without HUID
            save_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "saveinitialvalueswithoutHUID"))
            )
            save_btn.click()
            time.sleep(2)
            
            # Handle any alerts
            try:
                alert = self.driver.switch_to.alert
                alert.accept()
                time.sleep(1)
            except:
                pass
            
            return True
            
        except Exception as e:
            self.log(f"❌ Error saving weights: {str(e)}")
            return False
    
    def _submit_huid_for_job(self):
        """Submit HUID for the current job"""
        try:
            # Click HUID submission button
            huid_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "submitHUID"))
            )
            huid_btn.click()
            time.sleep(2)
            
            # Handle any alerts
            try:
                alert = self.driver.switch_to.alert
                alert.accept()
                time.sleep(1)
            except:
                pass
            
            return True
            
        except Exception as e:
            self.log(f"❌ Error submitting HUID: {str(e)}")
            return False
    
    def _save_initial_weights_for_job(self, report_data, job_no, request_no):
        """Save initial weights for a specific job"""
        try:
            self.log(f"💾 Saving initial weights for Job {job_no}")
            
            # Get strips data for this job
            strips_data = report_data.get('strips_data', {}).get(job_no, [])
            check_gold_data = report_data.get('check_gold_data', [])
            
            if not strips_data:
                self.log(f"⚠️ No strips data found for Job {job_no}")
                return False
            
            # Group strips by lot_no
            lots = {}
            for strip in strips_data:
                lot_no = strip.get('lot_no', '1')
                if lot_no not in lots:
                    lots[lot_no] = []
                lots[lot_no].append(strip)
            
            # Process each lot
            for lot_no, strips in lots.items():
                if lot_no == '0':  # Skip CHECK_GOLD lot
                    continue
                    
                self.log(f"🔄 Processing Lot {lot_no} for Job {job_no}")
                
                # Create lot weight data
                lot_weight_data = {
                    'scrap_weight': strips[0].get('lot_scrap_weight', 0),
                    'button_weight': strips[0].get('lot_button_weight', 0),
                    'strip_data': strips + check_gold_data  # Include CHECK_GOLD data
                }
                
                # Fill and save weights
                success = self._fill_and_save_initial_weights(lot_weight_data)
                
                if not success:
                    self.log(f"❌ Failed to save initial weights for Lot {lot_no}")
                    return False
            
            self.log(f"✅ Initial weights saved successfully for Job {job_no}")
            return True
            
        except Exception as e:
            self.log(f"❌ Error saving initial weights for Job {job_no}: {str(e)}")
            return False
    
    def _save_cornet_weights_for_job(self, report_data, job_no, request_no):
        """Save cornet weights for a specific job"""
        try:
            self.log(f"💾 Saving cornet weights for Job {job_no}")
            
            # Get strips data for this job
            strips_data = report_data.get('strips_data', {}).get(job_no, [])
            check_gold_data = report_data.get('check_gold_data', [])
            
            if not strips_data:
                self.log(f"⚠️ No strips data found for Job {job_no}")
                return False
            
            # Group strips by lot_no
            lots = {}
            for strip in strips_data:
                lot_no = strip.get('lot_no', '1')
                if lot_no not in lots:
                    lots[lot_no] = []
                lots[lot_no].append(strip)
            
            # Process each lot
            for lot_no, strips in lots.items():
                if lot_no == '0':  # Skip CHECK_GOLD lot
                    continue
                    
                self.log(f"🔄 Processing Lot {lot_no} for Job {job_no}")
                
                # Create lot weight data
                lot_weight_data = {
                    'scrap_weight': strips[0].get('lot_scrap_weight', 0),
                    'button_weight': strips[0].get('lot_button_weight', 0),
                    'strip_data': strips + check_gold_data  # Include CHECK_GOLD data
                }
                
                # Fill and save cornet weights
                success = self._fill_and_save_cornet_weights(lot_weight_data)
                
                if not success:
                    self.log(f"❌ Failed to save cornet weights for Lot {lot_no}")
                    return False
            
            self.log(f"✅ Cornet weights saved successfully for Job {job_no}")
            return True
            
        except Exception as e:
            self.log(f"❌ Error saving cornet weights for Job {job_no}: {str(e)}")
            return False
    
    def _fill_and_save_initial_weights(self, lot_weight_data):
        """Fill and save initial weights for a lot"""
        try:
            # Fill scrap and button weights
            scrap_weight = lot_weight_data.get('scrap_weight', 0)
            button_weight = lot_weight_data.get('button_weight', 0)
            
            # Fill scrap weight
            scrap_element = self.driver.find_element(By.ID, "num_scrap_weight")
            scrap_element.clear()
            scrap_element.send_keys(Keys.CONTROL + "a")
            scrap_element.send_keys(Keys.DELETE)
            scrap_element.send_keys(str(scrap_weight))
            
            # Fill button weight
            button_element = self.driver.find_element(By.ID, "buttonweight")
            button_element.clear()
            button_element.send_keys(Keys.CONTROL + "a")
            button_element.send_keys(Keys.DELETE)
            button_element.send_keys(str(button_weight))
            
            # Fill strip data
            strip_data = lot_weight_data.get('strip_data', [])
            self._fill_strip_data_from_api(strip_data)
            
            # Save weights
            return self._save_weights_for_lot()
            
        except Exception as e:
            self.log(f"❌ Error filling initial weights: {str(e)}")
            return False
    
    def _fill_strip_data_from_api(self, strip_data):
        """Fill strip data from API response"""
        try:
            for strip in strip_data:
                strip_no = strip.get('strip_no', '')
                initial = strip.get('initial', 0)
                ag = strip.get('ag', 0)
                cu = strip.get('cu', 0)
                pb = strip.get('pb', 0)
                
                # Map strip numbers to field IDs
                if strip_no == '1':
                    # Strip 1 fields
                    initial_field = "num_strip_weight_M11"
                    ag_field = "num_silver_weightM11"
                    cu_field = "num_copper_weightM11"
                    pb_field = "num_lead_weightM11"
                elif strip_no == '2':
                    # Strip 2 fields
                    initial_field = "num_strip_weight_M12"
                    ag_field = "num_silver_weightM12"
                    cu_field = "num_copper_weightM12"
                    pb_field = "num_lead_weightM12"
                elif strip_no == 'C1':
                    # C1 fields (CHECK_GOLD)
                    initial_field = "num_strip_weight_goldM11"
                    ag_field = "num_silver_weight_goldM11"
                    cu_field = "num_copper_weight_goldM11"
                    pb_field = "num_lead_weight_goldM11"
                elif strip_no == 'C2':
                    # C2 fields (CHECK_GOLD)
                    initial_field = "num_strip_weight_goldM12"
                    ag_field = "num_silver_weight_goldM12"
                    cu_field = "num_copper_weight_goldM12"
                    pb_field = "num_lead_weight_goldM12"
                else:
                    continue
                
                # Fill fields with robust element interaction
                try:
                    # Fill initial weight
                    element = self.driver.find_element(By.ID, initial_field)
                    if element.is_displayed() and element.is_enabled():
                        element.clear()
                        element.send_keys(Keys.CONTROL + "a")
                        element.send_keys(Keys.DELETE)
                        element.send_keys(str(initial))
                    
                    # Fill silver weight
                    element = self.driver.find_element(By.ID, ag_field)
                    if element.is_displayed() and element.is_enabled():
                        element.clear()
                        element.send_keys(Keys.CONTROL + "a")
                        element.send_keys(Keys.DELETE)
                        element.send_keys(str(ag))
                    
                    # Fill copper weight
                    element = self.driver.find_element(By.ID, cu_field)
                    if element.is_displayed() and element.is_enabled():
                        element.clear()
                        element.send_keys(Keys.CONTROL + "a")
                        element.send_keys(Keys.DELETE)
                        element.send_keys(str(cu))
                    
                    # Fill lead weight
                    element = self.driver.find_element(By.ID, pb_field)
                    if element.is_displayed() and element.is_enabled():
                        element.clear()
                        element.send_keys(Keys.CONTROL + "a")
                        element.send_keys(Keys.DELETE)
                        element.send_keys(str(pb))
                        
                except Exception as e:
                    self.log(f"⚠️ Error filling {strip_no} data: {str(e)}")
                    continue
            
            return True
            
        except Exception as e:
            self.log(f"❌ Error filling strip data: {str(e)}")
            return False
    
    def _fill_initial_weights_direct_mapping(self, lot_weight_data):
        """Fill initial weights using direct field mapping"""
        try:
            # This method can be used for direct field mapping if needed
            pass
        except Exception as e:
            self.log(f"❌ Error in direct mapping: {str(e)}")
            return False
    
    def _fill_and_save_cornet_weights(self, lot_weight_data):
        """Fill and save cornet weights for a lot"""
        try:
            # Fill strip data (cornet fields only)
            strip_data = lot_weight_data.get('strip_data', [])
            self._fill_cornet_data_from_api(strip_data)
            
            # Save cornet weights
            save_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "savecornetvalues"))
            )
            save_btn.click()
            time.sleep(2)
            
            # Handle any alerts
            try:
                alert = self.driver.switch_to.alert
                alert.accept()
                time.sleep(1)
            except:
                pass
            
            return True
            
        except Exception as e:
            self.log(f"❌ Error filling cornet weights: {str(e)}")
            return False
    
    def _fill_cornet_data_from_api(self, strip_data):
        """Fill cornet data from API response (M2 fields only)"""
        try:
            for strip in strip_data:
                strip_no = strip.get('strip_no', '')
                cornet = strip.get('cornet', 0)
                
                # Map strip numbers to cornet field IDs
                if strip_no == '1':
                    # Strip 1 cornet field
                    cornet_field = "num_cornet_weightM11"
                    cornet_gold_field = "num_cornet_weight_goldM11"
                elif strip_no == '2':
                    # Strip 2 cornet field
                    cornet_field = "num_cornet_weightM12"
                    cornet_gold_field = "num_cornet_weight_goldM12"
                else:
                    continue
                
                # Fill cornet fields with robust element interaction
                try:
                    # Fill cornet weight
                    element = self.driver.find_element(By.ID, cornet_field)
                    if element.is_displayed() and element.is_enabled():
                        element.clear()
                        element.send_keys(Keys.CONTROL + "a")
                        element.send_keys(Keys.DELETE)
                        element.send_keys(str(cornet))
                    
                    # Fill cornet gold weight (same value)
                    element = self.driver.find_element(By.ID, cornet_gold_field)
                    if element.is_displayed() and element.is_enabled():
                        element.clear()
                        element.send_keys(Keys.CONTROL + "a")
                        element.send_keys(Keys.DELETE)
                        element.send_keys(str(cornet))
                        
                except Exception as e:
                    self.log(f"⚠️ Error filling {strip_no} cornet data: {str(e)}")
                    continue
            
            return True
            
        except Exception as e:
            self.log(f"❌ Error filling cornet data: {str(e)}")
            return False
    
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
        """Update jobs listbox"""
        self.jobs_listbox.delete(0, tk.END)
        
        for job in job_summary:
            job_no = job.get('job_no', 'N/A')
            request_no = job.get('request_no', 'N/A')
            lots = job.get('total_lots', 0)
            
            display_text = f"Job: {job_no} | Request: {request_no} | Lots: {lots}"
            self.jobs_listbox.insert(tk.END, display_text)
    
    def update_job_status(self, job_no, status):
        """Update status of a specific job in the list"""
        # This can be implemented to update job status in the listbox
        pass
    
    def log(self, message, category='multiple_jobs'):
        """Add message to log"""
        timestamp = time.strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        # Update log text area (thread-safe)
        if self.log_text:
            try:
                root = self.notebook.winfo_toplevel()
                root.after(0, lambda: self._update_log_text(log_message))
            except Exception as e:
                print(f"Log error: {e}")
        
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
