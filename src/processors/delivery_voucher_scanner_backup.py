#!/usr/bin/env python3
"""
Delivery Voucher Scanner Module
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
from urllib.parse import parse_qs, urlparse

# Fix MySQL localization issue
os.environ['LANG'] = 'C'
os.environ['LC_ALL'] = 'C'
os.environ['LC_MESSAGES'] = 'C'

from config import DB_CONFIG


class DeliveryVoucherScanner:
    """Handles scanning delivery vouchers with preview and bulk save"""
    
    def __init__(self, driver, log_callback, license_check_callback, app_context=None):
        self.driver = driver
        self.log_callback = log_callback
        self.license_check_callback = license_check_callback
        self.app_context = app_context
        self.db_config = DB_CONFIG
        self.is_processing = False
        self.current_firm_id = self.get_firm_id_from_settings()
        
        # Store scanned jobs in memory before saving
        self.scanned_jobs = []
        
        # UI elements
        self.scan_log_text = None
        self.status_label = None
        self.progress_bar = None
        self.progress_var = None
        self.stats_labels = {}
        self.preview_tree = None
        self.save_selected_btn = None
        self.select_all_var = None
        
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
        """Log message to UI and callback"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        if self.scan_log_text:
            try:
                self.scan_log_text.config(state='normal')
                self.scan_log_text.insert('end', formatted_message + '\n')
                self.scan_log_text.see('end')
                self.scan_log_text.config(state='disabled')
            except Exception:
                pass
        
        if self.log_callback:
            try:
                self.log_callback(message, level)
            except Exception:
                pass
    
    def update_status(self, message, status_type='info'):
        """Update status label"""
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
    
    def update_progress(self, value, message=""):
        """Update progress bar"""
        if self.progress_var:
            try:
                self.progress_var.set(value)
                if message:
                    self.log(message)
            except Exception:
                pass
    
    def setup_scanner_tab(self, notebook):
        """Setup Scan Jobs Details tab"""
        scanner_frame = ttk.Frame(notebook)
        notebook.add(scanner_frame, text="🔍 Scan Jobs Details")
        
        # Main layout - Three sections
        main_container = ttk.Frame(scanner_frame)
        main_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Left section - Controls (25%)
        left_section = ttk.Frame(main_container)
        left_section.pack(side='left', fill='y', padx=(0, 10))
        
        # Center section - Preview Table (45%)
        center_section = ttk.Frame(main_container)
        center_section.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        # Right section - Log (30%)
        right_section = ttk.Frame(main_container)
        right_section.pack(side='right', fill='both', expand=True)
        
        self._setup_left_section(left_section)
        self._setup_center_section(center_section)
        self._setup_right_section(right_section)
    
    def _setup_left_section(self, parent):
        """Setup left section with controls"""
        
        # Firm ID Display
        firm_card = ttk.LabelFrame(parent, text="🏢 Firm Setup", style='Compact.TLabelframe')
        firm_card.pack(fill='x', pady=(0, 10))
        
        firm_frame = ttk.Frame(firm_card)
        firm_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(firm_frame, text="Current Firm ID:", font=('Segoe UI', 9, 'bold')).pack(anchor='w')
        self.firm_id_display = ttk.Label(firm_frame, text=self.current_firm_id, 
                                         font=('Segoe UI', 12, 'bold'), foreground='#17a2b8')
        self.firm_id_display.pack(anchor='w', pady=(2, 0))
        
        # Scan Control
        scan_card = ttk.LabelFrame(parent, text="🔍 Scan Control", style='Compact.TLabelframe')
        scan_card.pack(fill='x', pady=(0, 10))
        
        scan_frame = ttk.Frame(scan_card)
        scan_frame.pack(fill='x', padx=10, pady=10)
        
        self.scan_btn = ttk.Button(
            scan_frame,
            text="🚀 Start Scanning",
            command=self.start_scanning,
            style='Primary.TButton'
        )
        self.scan_btn.pack(fill='x', pady=(0, 5))
        
        ttk.Label(scan_frame, text="Scans delivery vouchers and shows preview",
                 font=('Segoe UI', 8), foreground='#6c757d').pack(anchor='w')
        
        # Progress Section
        progress_card = ttk.LabelFrame(parent, text="📊 Progress", style='Compact.TLabelframe')
        progress_card.pack(fill='x', pady=(0, 10))
        
        progress_frame = ttk.Frame(progress_card)
        progress_frame.pack(fill='x', padx=10, pady=10)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                           maximum=100, style='Modern.Horizontal.TProgressbar')
        self.progress_bar.pack(fill='x', pady=(0, 10))
        
        self.status_label = ttk.Label(progress_frame, text="🟢 Ready to scan",
                                     font=('Segoe UI', 10, 'bold'), foreground='#28a745')
        self.status_label.pack(anchor='w')
        
        # Statistics Section
        stats_card = ttk.LabelFrame(parent, text="📈 Statistics", style='Compact.TLabelframe')
        stats_card.pack(fill='x', pady=(0, 10))
        
        stats_frame = ttk.Frame(stats_card)
        stats_frame.pack(fill='x', padx=10, pady=10)
        
        self.stats_labels['scanned'] = ttk.Label(stats_frame, text="🔍 Scanned: 0",
                                                font=('Segoe UI', 9, 'bold'), foreground='#007bff')
        self.stats_labels['scanned'].pack(anchor='w', pady=(0, 5))
        
        self.stats_labels['existing'] = ttk.Label(stats_frame, text="✅ Already Exists: 0",
                                                 font=('Segoe UI', 9, 'bold'), foreground='#28a745')
        self.stats_labels['existing'].pack(anchor='w', pady=(0, 5))
        
        self.stats_labels['errors'] = ttk.Label(stats_frame, text="❌ Errors: 0",
                                               font=('Segoe UI', 9, 'bold'), foreground='#dc3545')
        self.stats_labels['errors'].pack(anchor='w')
        
        # Guide Section
        guide_card = ttk.LabelFrame(parent, text="📖 How It Works", style='Compact.TLabelframe')
        guide_card.pack(fill='both', expand=True)
        
        guide_frame = ttk.Frame(guide_card)
        guide_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        guide_text = """1️⃣ Scans delivery voucher list
2️⃣ Extracts job details 
3️⃣ Shows preview table
4️⃣ Select jobs to save
5️⃣ Bulk save to database"""
        
        ttk.Label(guide_frame, text=guide_text, font=('Segoe UI', 8),
                 foreground='#495057', justify='left').pack(anchor=' w')
    
    def _setup_center_section(self, parent):
        """Setup center section with preview table"""
        
        # Preview Table Card
        preview_card = ttk.LabelFrame(parent, text="📋 Scanned Jobs Preview", style='Compact.TLabelframe')
        preview_card.pack(fill='both', expand=True)
        
        # Top controls
        top_controls = ttk.Frame(preview_card)
        top_controls.pack(fill='x', padx=10, pady=(10, 5))
        
        # Select All checkbox
        self.select_all_var = tk.BooleanVar()
        select_all_check = ttk.Checkbutton(
            top_controls,
            text="Select All",
            variable=self.select_all_var,
            command=self._toggle_select_all
        )
        select_all_check.pack(side='left')
        
        # Save Selected Button
        self.save_selected_btn = ttk.Button(
            top_controls,
            text="💾 Save Selected",
            command=self.save_selected_jobs,
            style='Success.TButton',
            state='disabled'
        )
        self.save_selected_btn.pack(side='right')
        
        # Preview Table
        table_frame = ttk.Frame(preview_card)
        table_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # Scrollbars
        v_scroll = ttk.Scrollbar(table_frame, orient='vertical')
        h_scroll = ttk.Scrollbar(table_frame, orient='horizontal')
        
        # Treeview
        columns = ('sel', 'request_no', 'job_no', 'date', 'item', 'pcs', 'weight', 'status')
        self.preview_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show='headings',
            yscrollcommand=v_scroll.set,
            xscrollcommand=h_scroll.set,
            height=15
        )
        
        v_scroll.config(command=self.preview_tree.yview)
        h_scroll.config(command=self.preview_tree.xview)
        
        # Column headings
        self.preview_tree.heading('sel', text='☑')
        self.preview_tree.heading('request_no', text='Request No')
        self.preview_tree.heading('job_no', text='Job No')
        self.preview_tree.heading('date', text='Date')
        self.preview_tree.heading('item', text='Item')
        self.preview_tree.heading('pcs', text='Pcs')
        self.preview_tree.heading('weight', text='Weight')
        self.preview_tree.heading('status', text='Status')
        
        # Column widths
        self.preview_tree.column('sel', width=40, anchor='center')
        self.preview_tree.column('request_no', width=100)
        self.preview_tree.column('job_no', width=100)
        self.preview_tree.column('date', width=100)
        self.preview_tree.column('item', width=150)
        self.preview_tree.column('pcs', width=60, anchor='center')
        self.preview_tree.column('weight', width=80, anchor='center')
        self.preview_tree.column('status', width=100)
        
        # Pack
        self.preview_tree.grid(row=0, column=0, sticky='nsew')
        v_scroll.grid(row=0, column=1, sticky='ns')
        h_scroll.grid(row=1, column=0, sticky='ew')
        
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # Bind click
        self.preview_tree.bind('<Button-1>', self._on_tree_click)
        
        # Info label
        ttk.Label(
            preview_card,
            text="💡 Scan jobs first, review, then save selected",
            font=('Segoe UI', 8),
            foreground='#6c757d'
        ).pack(pady=(0, 10))
    
    def _setup_right_section(self, parent):
        """Setup right section with log"""
        
        log_card = ttk.LabelFrame(parent, text="📝 Scanning Log", style='Compact.TLabelframe')
        log_card.pack(fill='both', expand=True)
        
        import tkinter.scrolledtext as scrolledtext
        self.scan_log_text = scrolledtext.ScrolledText(
            log_card,
            height=25,
            font=('Consolas', 9),
            bg='#f8f9fa',
            fg='#495057',
            wrap=tk.WORD,
            state='disabled'
        )
        self.scan_log_text.pack(fill='both', expand=True, padx=10, pady=10)
    
    def _toggle_select_all(self):
        """Toggle selection of all jobs"""
        select_all = self.select_all_var.get()
        
        for i, job in enumerate(self.scanned_jobs):
            job['selected'] = select_all
            item_id = self.preview_tree.get_children()[i]
            checkbox = '☑' if select_all else '☐'
            values = list(self.preview_tree.item(item_id, 'values'))
            values[0] = checkbox
            self.preview_tree.item(item_id, values=values)
    
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
        
        # Get driver from app context if not set
        if not self.driver and self.app_context:
            self.driver = self.app_context.driver
            self.log(" Got driver from app context")        
        # Debug: Check driver status
        self.log(f"DEBUG: Driver status: {self.driver is not None}")
        self.log(f"DEBUG: Driver object: {self.driver}")
        
        if not self.driver:
            messagebox.showerror("Browser Error", "Browser is not available. Please:\n1. Go to 'Login in MANAK' tab\n2. Click 'Open Browser'\n3. Login to portal\n4. Come back and scan")
            return
        
        threading.Thread(target=self._scan_worker, daemon=True).start()
    
    def _scan_worker(self):
        """Worker thread for scanning"""
        self.is_processing = True
        self.scan_btn.config(state='disabled')
        
        # Clear previous results  
        self.scanned_jobs = []
        for item in self.preview_tree.get_children():
            self.preview_tree.delete(item)
        
        stats = {'scanned': 0, 'existing': 0, 'errors': 0}
        
        try:
            self.update_status("🔄 Starting scan...", 'info')
            self.update_progress(10, "🌐 Navigating to delivery voucher list...")
            
            list_url = "https://huid.manakonline.in/MANAK/NewArticlesListForDelieveryVoucher"
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
            
            # Process each job
            for i, job_info in enumerate(jobs_list):
                try:
                    progress = 30 + (i / len(jobs_list)) * 60
                    self.update_progress(progress, f"Processing {i+1}/{len(jobs_list)}...")
                    
                    job_no = job_info['job_no']
                    self.log(f"🔍 Checking job {job_no}...")
                    
                    # Check if exists
                    if self._check_job_exists(job_no):
                        self.log(f"✅ Job {job_no} already in database - Skipping")
                        stats['existing'] += 1
                        self._update_stats_display(stats)
                        continue
                    
                    # Scan details
                    self.log(f"🔍 Scanning details for {job_no}...")
                    job_details = self._scan_voucher_details(job_info)
                    
                    if job_details:
                        # Add to preview (not database yet)
                        job_details['selected'] = True  # Default selected
                        self.scanned_jobs.append(job_details)
                        
                        # Add to tree
                        self.preview_tree.insert('', 'end', values=(
                            '☑',
                            job_details.get('request_no', 'N/A'),
                            job_details.get('job_no', 'N/A'),
                            job_details.get('date_of_request', 'N/A'),
                            job_details.get('item', 'N/A')[:20],
                            job_details.get('pcs', 0),
                            f"{job_details.get('weight', 0):.2f}",
                            '⏳ Pending'
                        ))
                        
                        self.log(f"✅ Scanned job {job_no}")
                        stats['scanned'] += 1
                    else:
                        self.log(f"❌ Failed to extract {job_no}")
                        stats['errors'] += 1
                    
                    self._update_stats_display(stats)
                    time.sleep(1)
                    
                except Exception as e:
                    self.log(f"❌ Error: {str(e)}")
                    stats['errors'] += 1
                    continue
            
            self.update_progress(100, "✅ Scan complete!")
            self.update_status("✅ Scan complete - Review & save", 'success')
            
            # Enable save button if jobs scanned
            if stats['scanned'] > 0:
                self.save_selected_btn.config(state='normal')
            
            self.log(f"\n{'='*50}")
            self.log(f"📊 SCAN SUMMARY:")
            self.log(f"   Scanned: {stats['scanned']}")
            self.log(f"   Already Exists: {stats['existing']}")
            self.log(f"   Errors: {stats['errors']}")
            self.log(f"{'='*50}\n")
            
        except Exception as e:
            self.log(f"❌ Error: {str(e)}")
            self.update_status("❌ Scan failed", 'danger')
            
        finally:
            self.is_processing = False
            self.scan_btn.config(state='normal')
    
    def save_selected_jobs(self):
        """Save selected jobs to database"""
        selected = [j for j in self.scanned_jobs if j.get('selected', False)]
        
        if not selected:
            messagebox.showwarning("No Selection", "Please select jobs to save!")
            return
        
        confirm = messagebox.askyesno("Confirm", f"Save {len(selected)} job(s)?")
        if not confirm:
            return
        
        threading.Thread(target=self._save_worker, args=(selected,), daemon=True).start()
    
    def _save_worker(self, jobs):
        """Save jobs to database"""
        self.save_selected_btn.config(state='disabled')
        
        saved = 0
        errors = 0
        
        self.log(f"\n{'='*50}")
        self.log(f"💾 Saving {len(jobs)} jobs...")
        
        for i, job in enumerate(jobs):
            try:
                self.log(f"Saving {i+1}/{len(jobs)}: {job['job_no']}...")
                
                if self._save_job_to_database(job):
                    self.log(f"✅ Saved {job['job_no']}")
                    saved += 1
                    
                    # Update tree
                    idx = self.scanned_jobs.index(job)
                    item_id = self.preview_tree.get_children()[idx]
                    values = list(self.preview_tree.item(item_id, 'values'))
                    values[-1] = '✅ Saved'
                    self.preview_tree.item(item_id, values=values, tags=('saved',))
                    self.preview_tree.tag_configure('saved', foreground='#28a745')
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
        
        messagebox.showinfo("Complete", f"Saved {saved} jobs\nErrors: {errors}")
        self.save_selected_btn.config(state='normal')
    
    def _scan_delivery_list(self):
        """Scan delivery list page"""
        jobs = []
        
        try:
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
                return jobs
            
            rows = target.find_elements(By.TAG_NAME, "tr")[1:]
            
            for row in rows:
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 4:
                        request_no = cells[1].text.strip()
                        job_no = cells[2].text.strip()
                        job_date = cells[3].text.strip() if len(cells) > 3 else ""
                        material = cells[4].text.strip() if len(cells) > 4 else "Gold"
                        
                        links = cells[-1].find_elements(By.TAG_NAME, "a")
                        voucher_url = ""
                        for link in links:
                            if "Delivery" in link.text:
                                voucher_url = link.get_attribute("href")
                                break
                        
                        if request_no and job_no:
                            jobs.append({
                                'request_no': request_no,
                                'job_no': job_no,
                                'job_date': job_date,
                                'material': material,
                                'voucher_url': voucher_url
                            })
                except:
                    continue
            
            return jobs
        except:
            return jobs
    
    def _scan_voucher_details(self, job_info):
        """Scan voucher details page"""
        try:
            if job_info.get('voucher_url'):
                self.driver.get(job_info['voucher_url'])
            else:
                url = f"https://huid.manakonline.in/MANAK/AHCDeliveryVoucher?requestNo={job_info['request_no']}&jobNo={job_info['job_no']}&material={job_info['material']}"
                self.driver.get(url)
            
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(2)
            
            details = {
                'firm_id': self.current_firm_id,
                'request_no': job_info['request_no'],
                'job_no': job_info['job_no'],
                'material_type': job_info.get('material', 'Gold'),
                'status': 'Complete',
                'bill_no': None,
                'is_billed': 0
            }
            
            # Extract date
            try:
                date_elem = self.driver.find_element(By.XPATH, "//td[contains(text(), 'Job Card Date')]/following-sibling::td")
                details['date_of_request'] = date_elem.text.strip()
            except:
                details['date_of_request'] = job_info.get('job_date', datetime.datetime.now().strftime('%Y-%m-%d'))
            
            # Extract license
            try:
                lic_elem = self.driver.find_element(By.XPATH, "//td[contains(text(), 'License Number')]/following-sibling::td")
                details['licence_no'] = lic_elem.text.strip()
            except:
                details['licence_no'] = ""
            
            # Extract items
            try:
                items_table = self.driver.find_element(By.XPATH, "//h4[contains(text(), 'Accepted Items')]/following::table[1]")
                rows = items_table.find_elements(By.TAG_NAME, "tr")[1:]
                
                items = []
                units = 0
                huids = []
                weight = 0.0
                
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 4:
                        item = cells[1].text.strip()
                        unit = cells[2].text.strip()
                        huid = cells[3].text.strip()
                        wt = cells[4].text.strip() if len(cells) > 4 else "0"
                        
                        if item:
                            items.append(item)
                        if unit.isdigit():
                            units += int(unit)
                        if huid:
                            huids.append(huid)
                        try:
                            weight += float(wt)
                        except:
                            pass
                
                details['item'] = ", ".join(items) if items else "N/A"
                details['pcs'] = units
                details['huid_pcs'] = len(huids)
                details['weight'] = weight
            except:
                details['item'] = "N/A"
                details['pcs'] = 0
                details['huid_pcs'] = 0
                details['weight'] = 0.0
            
            # Extract cornet weight
            try:
                cornet = self.driver.find_element(By.XPATH, "//td[contains(text(), 'Weight of Cornet')]/following-sibling::td")
                details['cornet_weight'] = float(cornet.text.strip().replace('mgs', '').strip()) if cornet.text else 0.0
            except:
                details['cornet_weight'] = 0.0
            
            # Extract scrapping weight
            try:
                scrap = self.driver.find_element(By.XPATH, "//td[contains(text(), 'Weight of Scrapping')]/following-sibling::td")
                details['scrp_cornet_weight'] = float(scrap.text.strip().replace('mgs', '').strip()) if scrap.text else 0.0
            except:
                details['scrp_cornet_weight'] = 0.0
            
            details['created_at'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return details
            
        except Exception as e:
            self.log(f"❌ Error: {str(e)}")
            return None
    
    def _check_job_exists(self, job_no):
        """Check if job exists"""
        try:
            conn = mysql.connector.connect(**self.db_config)
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
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            
            query = """
                INSERT INTO job_cards (
                    firm_id, date_of_request, licence_no, request_no, job_no,
                    item, pcs, weight, huid_pcs, bill_no, is_billed, status,
                    cornet_weight, scrp_cornet_weight, material_type, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                job.get('firm_id'),
                job.get('date_of_request'),
                job.get('licence_no'),
                job.get('request_no'),
                job.get('job_no'),
                job.get('item'),
                job.get('pcs'),
                job.get('weight'),
                job.get('huid_pcs'),
                job.get('bill_no'),
                job.get('is_billed'),
                job.get('status'),
                job.get('cornet_weight'),
                job.get('scrp_cornet_weight'),
                job.get('material_type'),
                job.get('created_at')
            )
            
            cursor.execute(query, values)
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            self.log(f"❌ DB Error: {str(e)}")
            return False
    
    def _update_stats_display(self, stats):
        """Update stats"""
        try:
            if 'scanned' in self.stats_labels:
                self.stats_labels['scanned'].config(text=f"🔍 Scanned: {stats['scanned']}")
            if 'existing' in self.stats_labels:
                self.stats_labels['existing'].config(text=f"✅ Already Exists: {stats['existing']}")
            if 'errors' in self.stats_labels:
                self.stats_labels['errors'].config(text=f"❌ Errors: {stats['errors']}")
        except:
            pass
