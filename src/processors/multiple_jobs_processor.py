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
import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
from selenium import webdriver

from portal_config import portal_base, build_portal_url


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
        
        # Database configuration - use same as main app
        from config import DB_CONFIG
        self.db_config = {
            'host': DB_CONFIG['host'],
            'user': DB_CONFIG['user'],
            'password': DB_CONFIG['password'],
            'database': DB_CONFIG['database'],
            'port': 3306,
            'charset': 'utf8mb4',
            'autocommit': True
        }
    
    def setup_multiple_jobs_tab(self, notebook):
        """Setup Bulk Jobs tab with top control bar layout"""
        self.notebook = notebook
        multiple_jobs_frame = ttk.Frame(notebook)
        notebook.add(multiple_jobs_frame, text="📦 Bulk Jobs")
        
        # Main layout: Vertical (Top Controls -> Middle Table -> Bottom Log)
        
        # 1. TOP CONTROL SECTION
        top_frame = ttk.Frame(multiple_jobs_frame, padding=5)
        top_frame.pack(fill='x', side='top')
        
        # Row 1: Report Loading & Actions
        row1_frame = ttk.Frame(top_frame)
        row1_frame.pack(fill='x', pady=5)
        
        # Report ID Input
        ttk.Label(row1_frame, text="Report ID:", font=('Segoe UI', 9, 'bold')).pack(side='left', padx=(5, 5))
        self.report_id_entry = ttk.Entry(row1_frame, width=15)
        self.report_id_entry.pack(side='left', padx=5)
        
        # Load Button
        load_data_btn = ttk.Button(row1_frame, text="📥 Load Report", 
                                 command=self.load_report_data, style='Info.TButton')
        load_data_btn.pack(side='left', padx=5)
        
        # Separator
        ttk.Separator(row1_frame, orient='vertical').pack(side='left', fill='y', padx=10)
        
        # Action Buttons
        self.save_initial_btn = ttk.Button(row1_frame, text="💾 Save Initial", 
                                    command=self.save_initial_weights_multiple_jobs,
                                    style='Success.TButton', state='disabled')
        self.save_initial_btn.pack(side='left', padx=5)
        
        self.save_cornet_btn = ttk.Button(row1_frame, text="⚖️ Save Cornet", 
                                   command=self.save_cornet_weights_multiple_jobs,
                                   style='Warning.TButton', state='disabled')
        self.save_cornet_btn.pack(side='left', padx=5)

        self.club_btn = ttk.Button(row1_frame, text="🔗 Club",
                                   command=self.club_selected_jobs,
                                   style='Info.TButton', state='disabled')
        self.club_btn.pack(side='left', padx=5)

        self.fire_assay_time_btn = ttk.Button(
            row1_frame, text="🔥 Fire Assay Time",
            command=self.start_fire_assaying_time_for_selected,
            style='Action.TButton', state='disabled',
        )
        self.fire_assay_time_btn.pack(side='left', padx=5)
        
        self.process_all_btn = ttk.Button(row1_frame, text="🔄 Process All", 
                                   command=self.process_multiple_jobs_from_report,
                                   style='Action.TButton', state='disabled')
        # self.process_all_btn.pack(side='left', padx=5) # Maybe hide if confusing
        
        # Settings in Row 1 (Right aligned)
        settings_frame = ttk.Frame(row1_frame)
        settings_frame.pack(side='right', padx=10)
        
        self.auto_submit_huid_var = tk.BooleanVar(value=False) # Default False as requested
        ttk.Checkbutton(settings_frame, text="Auto Submit HUID", 
                      variable=self.auto_submit_huid_var).pack(side='left', padx=10)
                      
        ttk.Label(settings_frame, text="Delay(s):").pack(side='left', padx=(10, 2))
        self.job_delay_var = tk.StringVar(value="2")
        ttk.Entry(settings_frame, textvariable=self.job_delay_var, width=5).pack(side='left')
        
        # 2. STATUS BAR (Thin)
        status_frame = ttk.Frame(multiple_jobs_frame, padding=(5, 2))
        status_frame.pack(fill='x', side='top')
        
        self.status_label = ttk.Label(status_frame, text="Ready", foreground='blue', font=('Segoe UI', 9))
        self.status_label.pack(side='left', padx=5)
        
        self.progress_label = ttk.Label(status_frame, text="", foreground='#6c757d', font=('Segoe UI', 9))
        self.progress_label.pack(side='left', padx=(15, 5))
        
        self.results_label = ttk.Label(status_frame, text="", foreground='#28a745', font=('Segoe UI', 9))
        self.results_label.pack(side='left', padx=5)
        
        self.selection_status_label = ttk.Label(status_frame, text="0 jobs selected", foreground='#6c757d')
        self.selection_status_label.pack(side='right', padx=10)
        
        # 3. MAIN TABLE SECTION
        table_frame = ttk.Frame(multiple_jobs_frame, padding=5)
        table_frame.pack(fill='both', expand=True, side='top')
        
        # Treeview setup
        columns = ('Select', 'Job No', 'Request No', 'Lots', 'Button Weight', 'Scrap Weight', 'Status')
        self.jobs_tree = ttk.Treeview(table_frame, columns=columns, show='headings')
        
        # Headers
        self.jobs_tree.heading('Select', text='✓ Select All', command=self.toggle_select_all)
        self.jobs_tree.heading('Job No', text='Job No')
        self.jobs_tree.heading('Request No', text='Request No')
        self.jobs_tree.heading('Lots', text='Lots')
        self.jobs_tree.heading('Button Weight', text='Button Weight')
        self.jobs_tree.heading('Scrap Weight', text='Scrap Weight')
        self.jobs_tree.heading('Status', text='Status')
        
        # Columns
        self.jobs_tree.column('Select', width=60, anchor='center')
        self.jobs_tree.column('Job No', width=100)
        self.jobs_tree.column('Request No', width=120)
        self.jobs_tree.column('Lots', width=60, anchor='center')
        self.jobs_tree.column('Button Weight', width=100, anchor='center')
        self.jobs_tree.column('Scrap Weight', width=100, anchor='center')
        self.jobs_tree.column('Status', width=150)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.jobs_tree.yview)
        self.jobs_tree.configure(yscrollcommand=scrollbar.set)
        
        self.jobs_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        self.jobs_tree.bind('<Button-1>', self.on_job_tree_click)
        
        # 4. LOG SECTION
        log_frame = ttk.LabelFrame(multiple_jobs_frame, text="📝 Log", padding=5, height=100)
        log_frame.pack(fill='x', side='bottom', padx=5, pady=5)
        
        self.log_text = tk.Text(log_frame, height=5, font=('Consolas', 9))
        log_scroll = ttk.Scrollbar(log_frame, orient='vertical', command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        
        self.log_text.pack(side='left', fill='both', expand=True)
        log_scroll.pack(side='right', fill='y')
        
        # Initialize
        self.log("Bulk Jobs UI initialized (Top Layout)", 'multiple_jobs')
    
    def toggle_select_all(self):
        """Toggle select all/none based on first item"""
        if not self.jobs_tree.get_children(): return
        
        first_item = self.jobs_tree.get_children()[0]
        first_val = self.jobs_tree.item(first_item, 'values')[0]
        
        if first_val == '☑':
            self.select_none_jobs()
        else:
            self.select_all_jobs()
    
    def on_job_tree_click(self, event):
        """Handle clicks on the job tree for checkbox functionality"""
        item = self.jobs_tree.identify('item', event.x, event.y)
        column = self.jobs_tree.identify('column', event.x, event.y)
        
        if item and column == '#1':  # Column 1 is the Select column
            values = list(self.jobs_tree.item(item, 'values'))
            if values[0] == '☐':
                values[0] = '☑'
            else:
                values[0] = '☐'
            self.jobs_tree.item(item, values=values)
            self.update_selection_status()
    
    def select_all_jobs(self):
        """Select all jobs in the list"""
        for item in self.jobs_tree.get_children():
            values = list(self.jobs_tree.item(item, 'values'))
            values[0] = '☑'
            self.jobs_tree.item(item, values=values)
        self.update_selection_status()
    
    def select_none_jobs(self):
        """Deselect all jobs in the list"""
        for item in self.jobs_tree.get_children():
            values = list(self.jobs_tree.item(item, 'values'))
            values[0] = '☐'
            self.jobs_tree.item(item, values=values)
        self.update_selection_status()
    
    def update_selection_status(self):
        """Update the selection status label"""
        selected_count = 0
        total_count = 0
        
        for item in self.jobs_tree.get_children():
            values = self.jobs_tree.item(item, 'values')
            total_count += 1
            if values[0] == '☑':
                selected_count += 1
        
        self.selection_status_label.config(text=f"{selected_count}/{total_count} jobs selected")
        
        # Enable/disable save buttons based on selection
        if selected_count > 0:
            self.save_initial_btn.config(state='normal')
            self.save_cornet_btn.config(state='normal')
            if hasattr(self, 'club_btn'):
                self.club_btn.config(state='normal' if selected_count >= 2 else 'disabled')
            if hasattr(self, 'fire_assay_time_btn'):
                self.fire_assay_time_btn.config(state='normal')
        else:
            self.save_initial_btn.config(state='disabled')
            self.save_cornet_btn.config(state='disabled')
            if hasattr(self, 'club_btn'):
                self.club_btn.config(state='disabled')
            if hasattr(self, 'fire_assay_time_btn'):
                self.fire_assay_time_btn.config(state='disabled')
    
    def get_selected_jobs(self):
        """Get list of selected jobs (tree order)."""
        selected_jobs = []
        for item in self.jobs_tree.get_children():
            values = self.jobs_tree.item(item, 'values')
            if values[0] == '☑':  # Selected
                job_no = values[1]
                if ' (Lot ' in job_no:
                    job_no = job_no.split(' (Lot ')[0]
                selected_jobs.append({
                    'job_no': job_no,
                    'request_no': values[2],
                    'lots': values[3],
                    'button_weight': values[4],
                    'scrap_weight': values[5],
                    'status': values[6]
                })
        return selected_jobs

    @staticmethod
    def _b64_portal(value):
        return base64.b64encode(str(value).encode()).decode()

    def _build_initial_weight_page_url(self, request_no, job_no):
        """Sampling / initial / cornet weight page on UAT/live."""
        enc_req = self._b64_portal(request_no)
        enc_job = self._b64_portal(job_no)
        return (
            f"{portal_base()}/MANAK/SamplingweightingDeatils"
            f"?requestNo={enc_req}&&jobNo={enc_job}"
        )

    def _build_cornet_weight_page_url(self, request_no, job_no):
        return self._build_initial_weight_page_url(request_no, job_no)

    _PURITY_ID_MAP = {
        '22K916': '1001',
        '18K750': '1003',
        '24K999': '1002',
        '20K833': '1004',
        '14K585': '1005',
    }

    def _purity_to_portal_id(self, purity):
        p = (purity or '').strip()
        if p.isdigit():
            return p
        return self._PURITY_ID_MAP.get(p.upper(), '1001')

    def _lookup_job_club_params(self, job_no, request_no):
        """Licence, purity, material for club URL (from job_cards DB)."""
        meta = {'licence_no': '', 'purity': '22K916', 'material_type': 'Gold'}
        try:
            connection = self.get_database_connection()
            if not connection:
                return meta
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT licence_no, purity, material_type
                FROM job_cards
                WHERE job_no = %s AND request_no = %s
                LIMIT 1
                """,
                (str(job_no), str(request_no)),
            )
            row = cursor.fetchone()
            cursor.close()
            connection.close()
            if row:
                if row[0]:
                    meta['licence_no'] = str(row[0]).strip()
                if row[1]:
                    meta['purity'] = str(row[1]).strip()
                if row[2]:
                    meta['material_type'] = str(row[2]).strip()
        except Exception as e:
            self.log(f"⚠️ Job club DB lookup: {e}", 'multiple_jobs')
        return meta

    def _decode_portal_b64(self, value):
        try:
            return base64.b64decode(str(value).strip()).decode('utf-8')
        except Exception:
            return ''

    def _extract_club_urls_from_html(self, html):
        """All UID_Assayingclub URLs embedded in portal HTML/onclick."""
        if not html:
            return []
        found = set()
        patterns = [
            r'(/MANAK/UID_Assayingclub\?[^"\'\s<>]+)',
            r'(https?://[^"\'\s<>]*UID_Assayingclub\?[^"\'\s<>]+)',
            r"(UID_Assayingclub\?[^'\"\\s<>]+)",
        ]
        for pat in patterns:
            for m in re.finditer(pat, html, re.I):
                href = m.group(1).replace('&amp;', '&')
                if not href.startswith('http'):
                    if href.startswith('/'):
                        href = build_portal_url(href)
                    elif href.startswith('UID_'):
                        href = build_portal_url(f'/MANAK/{href}')
                if 'UID_Assayingclub' in href:
                    found.add(href)
        return list(found)

    def _patch_club_url_host_job(self, url, job_no, request_no=None):
        """Use portal URL template but set host eJobCard (and requestNo if given)."""
        parsed = urlparse(url)
        qs = parse_qs(parsed.query, keep_blank_values=True)
        qs['eJobCard'] = [self._b64_portal(job_no)]
        if request_no:
            qs['requestNo'] = [self._b64_portal(request_no)]
        flat = {k: v[0] for k, v in qs.items()}
        new_query = urlencode(flat)
        return urlunparse((
            parsed.scheme, parsed.netloc, parsed.path,
            parsed.params, new_query, parsed.fragment,
        ))

    def _club_url_matches_job(self, url, job_no):
        params = parse_qs(urlparse(url).query)
        enc = (params.get('eJobCard') or [''])[0]
        return self._decode_portal_b64(enc) == str(job_no)

    def _ensure_fire_assaying_list_loaded(self):
        """Navigate to Fire Assaying list and wait for FooTable."""
        list_url = build_portal_url("/MANAK/NewArticlesListForFireAssaying")
        if 'NewArticlesListForFireAssaying' not in (self.driver.current_url or ''):
            self._handle_unexpected_alert()
            self.driver.get(list_url)
            time.sleep(2.5)
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, 'table'))
            )
        except Exception:
            pass
        time.sleep(1)

    def _expand_footable_rows(self):
        """Expand FooTable detail rows (club href is in hidden/detail cells)."""
        expanded = 0
        for toggle in self.driver.find_elements(
            By.CSS_SELECTOR, 'span.footable-toggle, td.footable-first-column span.footable-toggle'
        ):
            try:
                row = toggle.find_element(By.XPATH, './ancestor::tr[1]')
                if 'footable-detail-show' in (row.get_attribute('class') or ''):
                    continue
                self.driver.execute_script('arguments[0].click();', toggle)
                time.sleep(0.25)
                expanded += 1
            except Exception:
                continue
        if expanded:
            self.log(f"🔍 Expanded {expanded} FooTable row(s) for club links", 'multiple_jobs')
        time.sleep(0.5)

    def _normalize_club_href(self, href):
        if not href:
            return None
        href = href.strip().replace('&amp;', '&')
        if href.startswith('/'):
            return build_portal_url(href)
        if href.startswith('UID_'):
            return build_portal_url(f'/MANAK/{href}')
        return href

    def _find_club_url_for_job(self, job_no, request_no, page_html=None):
        """
        Find UID_Assayingclub href (hidden td or footable detail).
        Never click Fire Assaying — pending jobs redirect to SamplingweightingDeatils.
        """
        enc_job = self._b64_portal(job_no)
        html = page_html or (self.driver.page_source if self.driver else '') or ''

        for url in self._extract_club_urls_from_html(html):
            if self._club_url_matches_job(url, job_no):
                return url

        if not self.driver:
            return None

        for link in self.driver.find_elements(
            By.XPATH,
            f"//a[contains(@href,'UID_Assayingclub') and contains(@href,'{enc_job}')]",
        ):
            href = self._normalize_club_href(link.get_attribute('href'))
            if href and self._club_url_matches_job(href, job_no):
                return href

        for block_xpath in (
            f"//tr[.//td[normalize-space(.)='{job_no}']]",
            f"//tr[.//td[normalize-space(.)='{job_no}']]"
            f"/following-sibling::tr[contains(@class,'footable-row-detail')]",
        ):
            for block in self.driver.find_elements(By.XPATH, block_xpath):
                for url in self._extract_club_urls_from_html(
                    block.get_attribute('outerHTML') or ''
                ):
                    if self._club_url_matches_job(url, job_no):
                        return url
                for link in block.find_elements(
                    By.XPATH, ".//a[contains(@href,'UID_Assayingclub')]"
                ):
                    href = self._normalize_club_href(link.get_attribute('href'))
                    if href and self._club_url_matches_job(href, job_no):
                        return href

        enc_req = self._b64_portal(request_no)
        for url in self._extract_club_urls_from_html(html):
            params = parse_qs(urlparse(url).query)
            if (params.get('requestNo') or [''])[0] == enc_req:
                return self._patch_club_url_host_job(url, job_no, request_no)
        return None

    def _pick_club_host_and_url(self, selected_jobs):
        """Prefer ready job as host (100167466), not needs-initial (100167465)."""
        self._ensure_fire_assaying_list_loaded()
        self._expand_footable_rows()
        page_html = self.driver.page_source or ''

        url_map = {}
        for job in selected_jobs:
            jno = job['job_no']
            url = self._find_club_url_for_job(jno, job['request_no'], page_html)
            if url:
                url_map[jno] = url
                self.log(f"  🔗 Club href for Job {jno}", 'multiple_jobs')
            else:
                self.log(f"  ⚠️ No club href for Job {jno}", 'multiple_jobs')

        if not url_map:
            return None, None, None

        def needs_initial(job):
            return 'Needs Initial Values' in (job.get('status') or '')

        for job in selected_jobs:
            if not needs_initial(job) and job['job_no'] in url_map:
                self.log(f"✅ Host Job {job['job_no']} (ready)", 'multiple_jobs')
                return job, url_map[job['job_no']], url_map

        for job in reversed(selected_jobs):
            if job['job_no'] in url_map:
                self.log(
                    f"⚠️ Host Job {job['job_no']} (needs initial — using hidden href)",
                    'multiple_jobs',
                )
                return job, url_map[job['job_no']], url_map
        return None, None, None

    def _open_club_url_direct(self, club_url):
        """driver.get UID_Assayingclub href — do not click Fire Assaying link."""
        if not club_url or 'UID_Assayingclub' not in club_url:
            return False
        self.log(f"🌐 Opening: {club_url[:140]}...", 'multiple_jobs')
        self._handle_unexpected_alert()
        self.driver.get(club_url)
        time.sleep(2.5)
        current = self.driver.current_url or ''
        if 'UID_Assayingclub' in current:
            return True
        if 'SamplingweightingDeatils' in current:
            self.log(f"❌ Redirected to Sampling: {current[:100]}", 'multiple_jobs')
        else:
            self.log(f"❌ Wrong page: {current[:100]}", 'multiple_jobs')
        return False

    def _build_assaying_club_url(self, job_no, request_no):
        self._ensure_fire_assaying_list_loaded()
        self._expand_footable_rows()
        return self._find_club_url_for_job(
            job_no, request_no, self.driver.page_source or ''
        )

    def _resolve_assaying_club_url(self, job_no, request_no):
        return self._build_assaying_club_url(job_no, request_no)

    def _open_club_via_row_click(self, job_no):
        """Deprecated — clicking Fire Assaying opens Sampling for some jobs."""
        return None

    _FIRE_ASSAY_PROCESS_STEPS = (
        ('cupellation_start', 'cupellation_end', 'Cupellation'),
        ('annealingButton_start', 'annealingButton_end', 'Annealing(Button)'),
        ('annealingStrip_start', 'annealingStrip_end', 'Annealing(Strip)'),
        ('partingOne_start', 'partingOne_end', 'Parting 1'),
        ('partingTwo_start', 'partingTwo_end', 'Parting 2'),
        ('annealingCornet_start', 'annealingCornet_end', 'Annealing(Cornet)'),
    )

    def start_fire_assaying_time_for_selected(self):
        """Open Fire Assaying Time for selected jobs and run Start/End steps."""
        if not self.check_license_before_action("fire assaying time"):
            return
        if not self.driver:
            messagebox.showwarning("Not Ready", "Please open browser and login first")
            return
        selected = self.get_selected_jobs()
        if not selected:
            messagebox.showwarning("No Selection", "Please select at least one job")
            return
        try:
            if 'eBISLogin' in (self.driver.current_url or ''):
                messagebox.showwarning("Not Logged In", "Please login to MANAK portal first")
                return
        except Exception:
            pass
        threading.Thread(
            target=self._fire_assaying_time_worker,
            args=(selected,),
            daemon=True,
        ).start()

    def _find_fire_assaying_time_href(self, job_no, request_no):
        """Find Fire Assaying Time link href for a job on the list page."""
        enc_job = self._b64_portal(job_no)
        patterns = [
            r'(/MANAK/[^\s"\'<>]*FireAssay[^\s"\'<>]*)',
            r'(/MANAK/[^\s"\'<>]*Assay[^\s"\'<>]*Time[^\s"\'<>]*)',
            r'(/MANAK/[^\s"\'<>]*Process[^\s"\'<>]*)',
        ]
        page_html = self.driver.page_source or ''
        for pat in patterns:
            for m in re.finditer(pat, page_html, re.I):
                href = m.group(1).replace('&amp;', '&')
                if enc_job in href or job_no in href:
                    if href.startswith('/'):
                        href = build_portal_url(href)
                    return href

        row_xpaths = [
            f"//tr[.//td[normalize-space(.)='{job_no}']]",
            f"//tr[.//td[normalize-space(.)='{job_no}']]"
            f"/following-sibling::tr[contains(@class,'footable-row-detail')]",
        ]
        for row_xpath in row_xpaths:
            for row in self.driver.find_elements(By.XPATH, row_xpath):
                for link in row.find_elements(
                    By.XPATH,
                    ".//a[contains(translate(normalize-space(.),"
                    "'FIRE ASSAYING TIME','fire assaying time'),'fire assaying time') "
                    "or contains(@href,'FireAssay') or contains(@href,'AssayTime')]",
                ):
                    text = (link.text or '').strip().lower()
                    if 'please fill' in text or 'completed' in text or 'clubbed' in text:
                        continue
                    href = self._normalize_club_href(link.get_attribute('href'))
                    if href:
                        return href
                    try:
                        self.driver.execute_script('arguments[0].click();', link)
                        time.sleep(2)
                        if self.driver.find_elements(By.ID, 'cupellation_start'):
                            return self.driver.current_url
                    except Exception:
                        continue
        return None

    def _open_fire_assaying_time_page(self, job_no, request_no):
        """Navigate to Fire Assaying Time process page for one job."""
        self._ensure_fire_assaying_list_loaded()
        self._expand_footable_rows()

        href = self._find_fire_assaying_time_href(job_no, request_no)
        if href and href.startswith('http'):
            self.log(f"🌐 Fire Assay Time URL: {href[:120]}...", 'multiple_jobs')
            self.driver.get(href)
            time.sleep(2)
        else:
            row = None
            for r in self.driver.find_elements(
                By.XPATH, f"//tr[.//td[normalize-space(.)='{job_no}']]"
            ):
                row = r
                break
            if not row:
                self.log(f"❌ Job {job_no} not found on Fire Assaying list", 'multiple_jobs')
                return False
            link = None
            for a in row.find_elements(By.TAG_NAME, 'a'):
                txt = (a.text or '').strip().lower()
                if 'fire assaying time' in txt:
                    link = a
                    break
            if not link:
                cells = row.find_elements(By.TAG_NAME, 'td')
                if cells:
                    for a in cells[-1].find_elements(By.TAG_NAME, 'a'):
                        txt = (a.text or '').strip().lower()
                        if txt and 'please fill' not in txt and 'completed' not in txt:
                            link = a
                            break
            if not link:
                self.log(
                    f"❌ No Fire Assaying Time link for Job {job_no} "
                    f"(may need initial values first)",
                    'multiple_jobs',
                )
                return False
            self.log(f"🖱️ Clicking Fire Assaying Time for Job {job_no}", 'multiple_jobs')
            self.driver.execute_script('arguments[0].click();', link)
            time.sleep(2.5)

        self._handle_unexpected_alert()
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, 'cupellation_start'))
            )
            return True
        except Exception:
            self.log(
                f"⚠️ Process page not detected for Job {job_no}: "
                f"{(self.driver.current_url or '')[:100]}",
                'multiple_jobs',
            )
            return False

    def _wait_button_enabled(self, element_id, timeout=90):
        WebDriverWait(self.driver, timeout).until(
            lambda d: d.find_element(By.ID, element_id).is_enabled()
        )

    def _click_process_button(self, element_id):
        btn = WebDriverWait(self.driver, 15).until(
            EC.element_to_be_clickable((By.ID, element_id))
        )
        self.driver.execute_script('arguments[0].click();', btn)
        time.sleep(0.5)
        self._handle_unexpected_alert()

    def _run_fire_assaying_process_steps(self, job_no):
        """Click Start then End for each fire assaying step (Cupellation → Cornet)."""
        delay = 1.0
        try:
            delay = float(self.job_delay_var.get() or 2)
        except (ValueError, TypeError):
            pass

        completed = 0
        for start_id, end_id, label in self._FIRE_ASSAY_PROCESS_STEPS:
            try:
                start_btn = self.driver.find_element(By.ID, start_id)
                if not start_btn.is_enabled():
                    self.log(f"⏭️ {label}: Start disabled (skip)", 'multiple_jobs')
                    continue

                self._click_process_button(start_id)
                self.log(f"▶️ Job {job_no} — {label}: Start", 'multiple_jobs')
                time.sleep(delay)

                self._wait_button_enabled(end_id)
                self._click_process_button(end_id)
                self.log(f"⏹️ Job {job_no} — {label}: End", 'multiple_jobs')
                time.sleep(delay)
                completed += 1
            except Exception as e:
                self.log(f"⚠️ Job {job_no} — {label}: {e}", 'multiple_jobs')

        return completed > 0

    def _fire_assaying_time_worker(self, selected_jobs):
        """For each selected job: open Fire Assaying Time and run process steps."""
        try:
            try:
                delay = float(self.job_delay_var.get() or 2)
            except (ValueError, TypeError):
                delay = 2.0

            self.update_status("Fire Assaying Time...", '#007bff')
            success = 0
            failed = 0

            for i, job in enumerate(selected_jobs):
                job_no = job['job_no']
                request_no = job['request_no']
                self.update_progress(
                    f"Fire Assay Time Job {job_no} ({i + 1}/{len(selected_jobs)})"
                )
                self.log(
                    f"🔥 Fire Assaying Time: Job {job_no} (Req {request_no})",
                    'multiple_jobs',
                )

                if not self._open_fire_assaying_time_page(job_no, request_no):
                    failed += 1
                    self.update_job_status(job_no, "❌ FA Time Failed")
                    continue

                if self._run_fire_assaying_process_steps(job_no):
                    success += 1
                    self.update_job_status(job_no, "✅ FA Time Done")
                    self.log(f"✅ Fire assaying process completed for Job {job_no}", 'multiple_jobs')
                else:
                    failed += 1
                    self.update_job_status(job_no, "⚠️ FA Time Partial")

                if i < len(selected_jobs) - 1:
                    time.sleep(delay)

            self.update_status("Fire Assay Time complete", '#28a745')
            self.update_results(f"🔥 FA Time — OK: {success} | Failed: {failed}")
            messagebox.showinfo(
                "Fire Assaying Time",
                f"✅ Completed process for {success} job(s)\n❌ Failed/skipped: {failed}",
            )
        except Exception as e:
            self.log(f"❌ Fire Assaying Time error: {e}", 'multiple_jobs')
            self.update_status("Fire Assay Time error", '#dc3545')
            messagebox.showerror("Fire Assaying Time", str(e))

    def club_selected_jobs(self):
        """Open assaying club page for first selected job and club all selected jobs."""
        if not self.check_license_before_action("job clubbing"):
            return
        if not hasattr(self, 'loaded_report_data') or not self.loaded_report_data:
            messagebox.showwarning("No Data", "Please load report data first")
            return
        if not self.driver:
            messagebox.showwarning("Not Ready", "Please open browser and login first")
            return
        selected = self.get_selected_jobs()
        if len(selected) < 2:
            messagebox.showwarning(
                "Selection",
                "Select at least 2 jobs to club.\n\n"
                "The app picks a ready job as host (opens UID_Assayingclub).\n"
                "Jobs needing initial values are merged on the club page.",
            )
            return
        try:
            if 'eBISLogin' in (self.driver.current_url or ''):
                messagebox.showwarning("Not Logged In", "Please login to MANAK portal first")
                return
        except Exception:
            pass
        threading.Thread(
            target=self._club_selected_jobs_worker,
            args=(selected,),
            daemon=True,
        ).start()

    def _club_selected_jobs_worker(self, selected_jobs):
        """Open club page for host job, tick selected rows, click Save."""
        try:
            job_nos = {j['job_no'] for j in selected_jobs}

            self.update_status("Clubbing jobs...", '#007bff')
            self.log(
                f"🔗 Club: {len(selected_jobs)} job(s) selected: "
                f"{', '.join(j['job_no'] for j in selected_jobs)}",
                'multiple_jobs',
            )

            host_job_info, club_url, _url_map = self._pick_club_host_and_url(selected_jobs)
            if not host_job_info or not club_url:
                messagebox.showerror(
                    "Club",
                    "Could not find UID_Assayingclub href on Fire Assaying list.\n\n"
                    "Expand the job row on the portal — the link is in the "
                    "'Fire Assaying' href (not a click if initial values are pending).",
                )
                self.update_status("Club failed", '#dc3545')
                return

            host_job = host_job_info['job_no']
            host_request = host_job_info['request_no']
            self.log(
                f"🔗 Club host: Job {host_job} (Req {host_request}), "
                f"merge: {', '.join(sorted(job_nos - {host_job}))}",
                'multiple_jobs',
            )

            if not self._open_club_url_direct(club_url):
                messagebox.showerror(
                    "Club",
                    f"Could not open UID_Assayingclub for host Job {host_job}.\n\n"
                    "Job 100167465-type rows redirect to Sampling if you click "
                    "'Fire Assaying' — the app uses the hidden href instead.\n"
                    "Use a ready job (e.g. 100167466) as host when possible.",
                )
                self.update_status("Club failed", '#dc3545')
                return

            current_url = self.driver.current_url or ''
            self.log(f"✅ On UID_Assayingclub: {current_url[:120]}...", 'multiple_jobs')

            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, 'table'))
            )

            checked = self._select_jobs_on_club_page(job_nos, host_job)
            if checked == 0:
                self.log(
                    "⚠️ No matching jobs found on club page — check host job / selection",
                    'multiple_jobs',
                )
                messagebox.showwarning(
                    "Club",
                    "Club page opened but no selected job rows were found to check.\n"
                    "Verify jobs on the page match your selection.",
                )
                self.update_status("Club page opened", '#ffc107')
                return

            self.log(f"☑️ Checked {checked} job row(s) on club page", 'multiple_jobs')
            if not self._click_club_save_button():
                messagebox.showerror("Club", "Could not click Save on club page")
                self.update_status("Club failed", '#dc3545')
                return

            time.sleep(2)
            self._handle_unexpected_alert()
            self.log(
                f"✅ Club saved — Job {host_job} with {checked} selected row(s)",
                'multiple_jobs',
            )
            self.update_status("Club complete", '#28a745')
            messagebox.showinfo(
                "Club Complete",
                f"✅ Clubbed {checked} job(s) under host Job {host_job}.\n\n"
                "You can now use Save Initial / Save Cornet for the clubbed job.",
            )
        except Exception as e:
            self.log(f"❌ Club error: {e}", 'multiple_jobs')
            self.update_status("Club error", '#dc3545')
            messagebox.showerror("Club Error", str(e))

    def _select_jobs_on_club_page(self, job_nos, host_job):
        """Tick Accept checkboxes for selected job numbers on UID_Assayingclub table."""
        checked = 0
        targets = {str(j) for j in job_nos}

        for cb in self.driver.find_elements(
            By.CSS_SELECTOR, 'input.accept[type="checkbox"], input.acceptcheck[type="checkbox"]'
        ):
            try:
                val = (cb.get_attribute('value') or '').strip()
                if not val or val not in targets:
                    continue
                if val == str(host_job):
                    continue
                if cb.is_displayed() and not cb.is_selected():
                    self.driver.execute_script('arguments[0].click();', cb)
                    checked += 1
                    self.log(f"  ☑️ Selected Job {val} on club page", 'multiple_jobs')
                elif cb.is_selected():
                    checked += 1
            except Exception:
                continue

        if checked == 0:
            for row in self.driver.find_elements(By.XPATH, '//table//tbody/tr'):
                try:
                    cells = row.find_elements(By.TAG_NAME, 'td')
                    row_job = None
                    for cell in cells:
                        text = cell.text.strip()
                        if text.isdigit() and len(text) >= 8 and text in targets:
                            row_job = text
                            break
                    if not row_job or row_job == str(host_job):
                        continue
                    for cb in row.find_elements(
                        By.XPATH, './/input[@type="checkbox"]'
                    ):
                        if cb.is_displayed() and not cb.is_selected():
                            self.driver.execute_script('arguments[0].click();', cb)
                            checked += 1
                            self.log(f"  ☑️ Selected Job {row_job} (by row)", 'multiple_jobs')
                            break
                except Exception:
                    continue
        return checked

    def _click_club_save_button(self):
        """Click Save on UID_Assayingclub page (clubs checked jobs)."""
        save_xpaths = [
            "//input[@id='add']",
            "//input[@type='button' and @value='Save']",
            "//button[contains(normalize-space(.),'Save')]",
            "//input[contains(@class,'printHuid') and @value='Save']",
        ]
        for xpath in save_xpaths:
            try:
                btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                if btn.is_displayed():
                    btn.click()
                    self.log("✅ Clicked Save on club page", 'multiple_jobs')
                    return True
            except Exception:
                continue
        self.log("❌ Save button not found on club page", 'multiple_jobs')
        return False
    
    def get_database_connection(self):
        """Get database connection with retry logic"""
        max_retries = 2  # Reduced retries to avoid spam
        for attempt in range(1, max_retries + 1):
            try:
                if attempt == 1:  # Only log on first attempt to reduce spam
                    self.log(f"🔌 Attempting database connection...", 'multiple_jobs')
                # Add auth_plugin to fix MySQL 8.0+ authentication compatibility
                db_config_with_auth = self.db_config.copy()
                db_config_with_auth['auth_plugin'] = 'mysql_native_password'
                connection = mysql.connector.connect(**db_config_with_auth)
                if connection.is_connected():
                    if attempt == 1:
                        self.log(f"✅ Database connection successful", 'multiple_jobs')
                    return connection
            except Error as e:
                if attempt == max_retries:  # Only log final failure
                    self.log(f"❌ Database connection failed: {e}", 'multiple_jobs')
                    return None
                if attempt < max_retries:
                    time.sleep(1)  # Shorter wait time
        return None
    
    def get_job_status_from_database(self, job_no, request_no):
        """Get job status from job_cards table"""
        try:
            connection = self.get_database_connection()
            if not connection:
                return "DB Error"
            
            cursor = connection.cursor()
            
            # Extract original job number if it contains lot info (e.g., "122422168 (Lot 1)" -> "122422168")
            original_job_no = job_no.split(' (Lot ')[0] if ' (Lot ' in job_no else job_no
            
            query = """
                SELECT status 
                FROM job_cards 
                WHERE job_no = %s AND request_no = %s
                LIMIT 1
            """
            cursor.execute(query, (original_job_no, request_no))
            result = cursor.fetchone()
            
            if result:
                status = result[0]
                return status if status else "⏳ Pending"
            else:
                return "❓ Not Found"
                
        except Error as e:
            self.log(f"❌ Database error getting job status: {e}", 'multiple_jobs')
            return "DB Error"
        except Exception as e:
            self.log(f"❌ Error getting job status: {e}", 'multiple_jobs')
            return "Error"
        finally:
            if 'connection' in locals() and connection.is_connected():
                connection.close()
    
    def get_batch_job_statuses(self, job_summary):
        """Get job statuses for multiple jobs in one batch query"""
        try:
            connection = self.get_database_connection()
            if not connection:
                return ["DB Error"] * len(job_summary)
            
            cursor = connection.cursor()
            
            # Prepare job numbers and request numbers for batch query
            job_conditions = []
            for job in job_summary:
                # Extract original job number if it contains lot info
                original_job_no = job['job_no'].split(' (Lot ')[0] if ' (Lot ' in job['job_no'] else job['job_no']
                job_conditions.append(f"(job_no = '{original_job_no}' AND request_no = '{job['request_no']}')")
            
            if not job_conditions:
                return ["⏳ Pending"] * len(job_summary)
            
            # Build batch query
            query = f"""
                SELECT job_no, request_no, status 
                FROM job_cards 
                WHERE {' OR '.join(job_conditions)}
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            # Create a lookup dictionary
            status_lookup = {}
            for row in results:
                job_no, request_no, status = row
                key = f"{job_no}_{request_no}"
                status_lookup[key] = status if status else "⏳ Pending"
            
            # Return statuses in the same order as input jobs
            statuses = []
            for job in job_summary:
                original_job_no = job['job_no'].split(' (Lot ')[0] if ' (Lot ' in job['job_no'] else job['job_no']
                key = f"{original_job_no}_{job['request_no']}"
                statuses.append(status_lookup.get(key, "❓ Not Found"))
            
            return statuses
                
        except Error as e:
            self.log(f"❌ Database error getting batch job statuses: {e}", 'multiple_jobs')
            return ["DB Error"] * len(job_summary)
        except Exception as e:
            self.log(f"❌ Error getting batch job statuses: {e}", 'multiple_jobs')
            return ["DB Error"] * len(job_summary)
        finally:
            if 'connection' in locals() and connection.is_connected():
                connection.close()
    
    def get_api_url_from_settings(self):
        """Get Report API URL from main app settings"""
        try:
            if self.main_app and hasattr(self.main_app, 'report_api_url_var'):
                api_url = self.main_app.report_api_url_var.get().strip()
                return api_url if api_url else "https://hallmarkpro.in/admin/get_report_by_id.php"
            return "https://hallmarkpro.in/admin/get_report_by_id.php"  # Default API URL
        except Exception as e:
            self.log(f"❌ Error getting Report API URL: {e}", 'multiple_jobs')
            return "https://hallmarkpro.in/admin/get_report_by_id.php"  # Default API URL
    
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
                
                # Process each lot in the job and track lot weights
                lot_weights = {}  # Track weights per lot
                for lot_no, lot_strips in job_strips_data.items():
                    if isinstance(lot_strips, list):
                        all_strip_data.extend(lot_strips)
                        self.log(f"🔍 Found {len(lot_strips)} strips for Job {job_no}, Lot {lot_no}", 'multiple_jobs')
                        
                        # Calculate weights for this lot
                        lot_button_weight = 0
                        lot_scrap_weight = 0
                        for strip in lot_strips:
                            # Check button weight
                            if 'lot_button_weight' in strip and strip['lot_button_weight'] and lot_button_weight == 0:
                                try:
                                    lot_button_weight = float(strip['lot_button_weight'])
                                except (ValueError, TypeError):
                                    pass
                            # Check scrap weight
                            if 'lot_scrap_weight' in strip and strip['lot_scrap_weight'] and lot_scrap_weight == 0:
                                try:
                                    lot_scrap_weight = float(strip['lot_scrap_weight'])
                                except (ValueError, TypeError):
                                    pass
                            
                            # If we found both weights, we can break early
                            if lot_button_weight > 0 and lot_scrap_weight > 0:
                                break
                        
                        lot_weights[lot_no] = {
                            'button_weight': lot_button_weight,
                            'scrap_weight': lot_scrap_weight
                        }
                        self.log(f"🔍 Lot {lot_no} weights - Button: {lot_button_weight}, Scrap: {lot_scrap_weight}", 'multiple_jobs')
                
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
                    job['lot_weights'] = lot_weights  # Store lot-specific weights
                    self.log(f"✅ Found {len(all_strip_data)} total strip entries for Job {job_no}", 'multiple_jobs')
                    
                    # Debug: Show what strip data looks like
                    if all_strip_data:
                        first_strip = all_strip_data[0]
                        self.log(f"🔍 Sample strip data keys: {list(first_strip.keys())}", 'multiple_jobs')
                        self.log(f"🔍 Sample strip data: {first_strip}", 'multiple_jobs')
                else:
                    self.log(f"⚠️ No strip data found for Job {job_no} in report response", 'multiple_jobs')
                
                # If job has multiple lots, create separate entries for each lot
                if len(lot_weights) > 1:
                    self.log(f"🔄 Job {job_no} has {len(lot_weights)} lots - creating separate entries", 'multiple_jobs')
                    for lot_no, weights in lot_weights.items():
                        lot_job = job.copy()  # Create a copy for each lot
                        lot_job['job_no'] = f"{job_no} (Lot {lot_no})"
                        lot_job['total_lots'] = 1  # Each entry represents 1 lot
                        lot_job['total_button_weight'] = weights['button_weight']
                        lot_job['total_scrap_weight'] = weights['scrap_weight']
                        lot_job['original_job_no'] = job_no
                        lot_job['lot_no'] = lot_no
                        enhanced_job_summary.append(lot_job)
                else:
                    # Single lot job - keep as is
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
        """Save initial weights for selected jobs from a single report"""
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
            
            # Get selected jobs
            selected_jobs = self.get_selected_jobs()
            if not selected_jobs:
                self.log("❌ No jobs selected", 'multiple_jobs')
                messagebox.showwarning("No Selection", "Please select at least one job to process")
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
            
            # Start processing in background thread using pre-loaded data and selected jobs
            threading.Thread(
                target=self._save_initial_weights_worker_with_data, 
                args=(self.loaded_report_data, self.loaded_report_id, selected_jobs), 
                daemon=True
            ).start()
            
        except Exception as e:
            self.log(f"❌ Error starting initial weights processing: {str(e)}", 'multiple_jobs')
            messagebox.showerror("Error", f"Error starting processing: {str(e)}")

    def save_cornet_weights_multiple_jobs(self):
        """Save cornet weights for selected jobs from a single report"""
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
            
            # Get selected jobs
            selected_jobs = self.get_selected_jobs()
            if not selected_jobs:
                messagebox.showwarning("No Selection", "Please select at least one job to process")
                return
            
            # Start processing in background thread using pre-loaded data and selected jobs
            threading.Thread(
                target=self._save_cornet_weights_worker_with_data, 
                args=(self.loaded_report_data, self.loaded_report_id, selected_jobs), 
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

    def _save_initial_weights_worker_with_data(self, data, report_id, selected_jobs):
        """Worker thread for saving initial weights using pre-loaded data and selected jobs"""
        try:
            # TEST: Verify logging is working
            self.log("🚀 STARTING INITIAL WEIGHTS SAVE PROCESS", 'multiple_jobs')
            self.log(f"🔍 Report ID: {report_id}", 'multiple_jobs')
            self.log(f"🔍 Processing {len(selected_jobs)} selected jobs", 'multiple_jobs')
            self.log(f"🔍 Data keys: {list(data.keys()) if data else 'None'}", 'multiple_jobs')
            
            # Use selected jobs instead of all jobs
            job_summary = selected_jobs
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

    def _save_cornet_weights_worker_with_data(self, data, report_id, selected_jobs):
        """Worker thread for saving cornet weights using pre-loaded data and selected jobs"""
        try:
            # TEST: Verify logging is working
            self.log("🚀 STARTING CORNET WEIGHTS SAVE PROCESS", 'multiple_jobs')
            self.log(f"🔍 Report ID: {report_id}", 'multiple_jobs')
            self.log(f"🔍 Processing {len(selected_jobs)} selected jobs", 'multiple_jobs')
            
            # Use selected jobs instead of all jobs
            job_summary = selected_jobs
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
                
                # Load sampling weight page
                weight_url = self._build_initial_weight_page_url(request_no, job_no)
                self.driver.get(weight_url)
                time.sleep(3)
                
                # Select lot
                if not self._select_lot_in_portal(str(lot_no), job_no):
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
    
    def _handle_unexpected_alert(self):
        """Handle any unexpected alerts that might block execution"""
        try:
            # Check for alert
            WebDriverWait(self.driver, 1).until(EC.alert_is_present())
            alert = self.driver.switch_to.alert
            text = alert.text
            self.log(f"⚠️ Handling unexpected alert: {text}", 'multiple_jobs')
            alert.accept()
            time.sleep(1)
            return True
        except:
            return False

    def _select_lot_in_portal(self, lot_no, job_no=None):
        """Helper method to select lot in portal
        
        Args:
            lot_no: The lot number to select
            job_no: Optional job number to match against (for disambiguation)
        """
        try:
            # Handle any leftover alerts first
            self._handle_unexpected_alert()
            
            # Wait for any masking elements to disappear (like previous dropdowns)
            try:
                WebDriverWait(self.driver, 2).until(
                    EC.invisibility_of_element_located((By.ID, "select2-drop-mask"))
                )
            except:
                pass  # Use pass instead of logging to avoid clutter

            # Use Select2 method with explicit wait/retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    select2_container = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.ID, "s2id_lotno"))
                    )
                    select2_container.click()
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    self.log(f"⚠️ Retry {attempt+1} clicking lot dropdown...", 'multiple_jobs')
                    self._handle_unexpected_alert() # Check if alert is blocking
                    time.sleep(1)

            time.sleep(0.5)
            
            options = self.driver.find_elements(By.CSS_SELECTOR, "ul.select2-results li")
            found = False
            
            # Log all available options for debugging
            all_options = [opt.text.strip() for opt in options]
            self.log(f"🔍 DEBUG: Available lot options: {all_options}", 'multiple_jobs')
            
            for option in options:
                option_text = option.text.strip()
                
                # Handle both formats: "Lot 1" and "Lot 1:123537638" (Lot No:Job No)
                # Priority 1: If job_no is provided, try to match "Lot X:JobNo" format first
                if job_no and option_text == f"Lot {lot_no}:{job_no}":
                    option.click()
                    found = True
                    self.log(f"✅ Selected Lot {lot_no} in portal (matched: '{option_text}' with job {job_no})", 'multiple_jobs')
                    break
                
                # Priority 2: Match plain "Lot X" format (no job number suffix)
                elif option_text == f"Lot {lot_no}" and ':' not in option_text:
                    option.click()
                    found = True
                    self.log(f"✅ Selected Lot {lot_no} in portal (matched: '{option_text}')", 'multiple_jobs')
                    break
            
            # Fallback: If no exact match found and job_no not provided, use old logic
            if not found and not job_no:
                for option in options:
                    option_text = option.text.strip()
                    if (option_text.endswith(f"Lot {lot_no}") or
                        option_text.startswith(f"Lot {lot_no}:")):
                        option.click()
                        found = True
                        self.log(f"⚠️ Selected Lot {lot_no} using fallback (matched: '{option_text}')", 'multiple_jobs')
                        break
            
            if not found:
                self.log(f"❌ Lot {lot_no} not found in Select2 options (job: {job_no})", 'multiple_jobs')
                # Close dropdown if it's still open
                try:
                    webdriver.ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                except:
                    pass
                return False
            
            # Verify dropdown is closed
            try:
                # Wait for mask to disappear
                WebDriverWait(self.driver, 2).until(
                    EC.invisibility_of_element_located((By.ID, "select2-drop-mask"))
                )
            except:
                self.log("⚠️ Dropdown mask still present, forcing close...", 'multiple_jobs')
                try:
                    # Try clicking the label or title to close dropdown
                    self.driver.find_element(By.TAG_NAME, "h3").click() 
                except:
                    try:
                        # Fallback to ESC
                        webdriver.ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                    except:
                        pass
                time.sleep(1)

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
            
            # Find the job in the enhanced job summary (handle both original and lot-specific job numbers)
            job_data = None
            for job in report_data.get('job_summary', []):
                if job['job_no'] == job_no or job.get('original_job_no') == job_no:
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
            
            # Get the actual job number for portal (use original_job_no if this is a lot-specific entry)
            portal_job_no = job_data.get('original_job_no', job_no)
            
            # If this is a lot-specific job entry, only process that specific lot
            if 'lot_no' in job_data:
                specific_lot = str(job_data['lot_no'])
                if specific_lot in lots_data:
                    lots_data = {specific_lot: lots_data[specific_lot]}
                    self.log(f"🎯 Processing specific lot {specific_lot} for job {portal_job_no}", 'multiple_jobs')
                else:
                    self.log(f"❌ Specific lot {specific_lot} not found in strip data", 'multiple_jobs')
                    return False
            
            # Process each lot in this job for initial weights only
            total_lots = len(lots_data)
            for i, (lot_no, strips) in enumerate(lots_data.items()):
                is_last_lot = (i == total_lots - 1)  # Check if this is the last lot
                
                self.log(f"💾 Saving initial weights for Lot {lot_no} in Job {portal_job_no} ({i+1}/{total_lots})", 'multiple_jobs')
                
                # Load initial weight page (SamplingweightingDeatils on UAT/live)
                weight_url = self._build_initial_weight_page_url(request_no, portal_job_no)
                self.log(f"🌐 Initial weight page: {weight_url}", 'multiple_jobs')
                
                # Handle potential alerts before navigation
                self._handle_unexpected_alert()
                
                try:
                    self.driver.get(weight_url)
                    # --- BYPASS COM PORT POPUP ---
                    try:
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
                except Exception as e:
                    self.log(f"⚠️ Navigation error (attempt 1): {str(e)}", 'multiple_jobs')
                    # If alert blocked navigation, handle it and retry
                    if self._handle_unexpected_alert():
                        self.driver.get(weight_url)
                
                time.sleep(3)
                
                # Check for alert again after page load attempts
                self._handle_unexpected_alert()
                
                # Select lot
                if not self._select_lot_in_portal(str(lot_no), portal_job_no):
                    self.log(f"❌ Failed to select Lot {lot_no} for Job {portal_job_no}", 'multiple_jobs')
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
                
                self.log(f"✅ Saved initial weights for Lot {lot_no} in Job {portal_job_no}", 'multiple_jobs')
                
                # Submit for HUID only after the last lot (if auto-submit is enabled)
                if is_last_lot and self.auto_submit_huid_var.get():
                    self.log(f"📤 Submitting HUID for Job {portal_job_no} (after last lot {lot_no})", 'multiple_jobs')
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
            
            # Get the actual job number for portal (use original_job_no if this is a lot-specific entry)
            portal_job_no = job_data.get('original_job_no', job_no)
            
            # If this is a lot-specific job entry, only process that specific lot
            if 'lot_no' in job_data:
                specific_lot = str(job_data['lot_no'])
                if specific_lot in lots_data:
                    lots_data = {specific_lot: lots_data[specific_lot]}
                    self.log(f"🎯 Processing specific lot {specific_lot} for job {portal_job_no}", 'multiple_jobs')
                else:
                    self.log(f"❌ Specific lot {specific_lot} not found in strip data", 'multiple_jobs')
                    return False
            
            # Process each lot in this job for cornet weights only
            total_lots = len(lots_data)
            for i, (lot_no, strips) in enumerate(lots_data.items()):
                is_last_lot = (i == total_lots - 1)  # Check if this is the last lot
                
                self.log(f"⚖️ Saving cornet weights for Lot {lot_no} in Job {portal_job_no} ({i+1}/{total_lots})", 'multiple_jobs')
                
                # Check session before navigation
                if "login" in self.driver.current_url.lower():
                    self.log("⚠️ Session timeout detected. Please login manually...", 'multiple_jobs')
                    messagebox.showwarning("Session Timeout", "Please login to the portal and click OK to continue.")
                
                # Load cornet weight page
                weight_url = self._build_cornet_weight_page_url(request_no, portal_job_no)
                self.log(f"🌐 Cornet weight page: {weight_url}", 'multiple_jobs')
                
                nav_success = False
                for attempt in range(3):
                    try:
                        self._handle_unexpected_alert()  # Clear any alerts before nav
                        self.driver.set_page_load_timeout(30)
                        self.driver.get(weight_url)
                        time.sleep(2)
                        
                        # Handle alert that might appear immediately after load
                        self._handle_unexpected_alert()
                        
                        # Verify we are on the right page (look for Lot No dropdown or similar)
                        if "login" not in self.driver.current_url.lower():
                            nav_success = True
                            break
                    except Exception as e:
                        # Check if it was an alert exception
                        if "alert" in str(e).lower():
                            self._handle_unexpected_alert()
                        
                        self.log(f"⚠️ Navigation attempt {attempt+1} failed: {e}", 'multiple_jobs')
                        time.sleep(2)
                
                if not nav_success:
                    self.log(f"❌ Failed to navigate to weight page for {portal_job_no}", 'multiple_jobs')
                    continue
                                
                time.sleep(1) # Extra stability wait
                
                # Select lot
                if not self._select_lot_in_portal(str(lot_no), portal_job_no):
                    self.log(f"❌ Failed to select Lot {lot_no} for Job {portal_job_no}", 'multiple_jobs')
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
                
                self.log(f"✅ Saved cornet weights for Lot {lot_no} in Job {portal_job_no}", 'multiple_jobs')
                
                # Submit for HUID only after the last lot (if auto-submit is enabled)
                if is_last_lot and self.auto_submit_huid_var.get():
                    self.log(f"📤 Submitting HUID for Job {portal_job_no} (after last lot {lot_no})", 'multiple_jobs')
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
            
            # Safety: Ensure no dropdowns are blocking the view
            try:
                WebDriverWait(self.driver, 2).until(
                    EC.invisibility_of_element_located((By.ID, "select2-drop-mask"))
                )
            except:
                self.log("⚠️ Overlay still detected before filling weights, attempting to clear...", 'multiple_jobs')
                try:
                    webdriver.ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                except:
                    pass
            
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
                    
                    # Handle possible alerts after saving initial weights
                    for _ in range(2):
                        try:
                            WebDriverWait(self.driver, 2).until(EC.alert_is_present())
                            alert = self.driver.switch_to.alert
                            self.log(f"🔔 Alert handled: {alert.text}", 'multiple_jobs')
                            alert.accept()
                            time.sleep(1)
                        except:
                            break
                            
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
                                        # Tab out to trigger events
                                        element.send_keys(Keys.TAB)
                                        self.log(f"✅ Strip 1 - {field_id}: {value}", 'multiple_jobs')
                                        time.sleep(0.1) # Small delay
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
                                        # Tab out to trigger events
                                        element.send_keys(Keys.TAB)
                                        self.log(f"✅ Strip 2 - {field_id}: {value}", 'multiple_jobs')
                                        time.sleep(0.1) # Small delay
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
                                        # Tab out to trigger events
                                        element.send_keys(Keys.TAB)
                                        self.log(f"✅ C1 - {field_id}: {value}", 'multiple_jobs')
                                        time.sleep(0.1) # Small delay
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
                                        # Tab out to trigger events
                                        element.send_keys(Keys.TAB)
                                        self.log(f"✅ C2 - {field_id}: {value}", 'multiple_jobs')
                                        time.sleep(0.1) # Small delay
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
            
            # Safety: Ensure no dropdowns are blocking the view
            try:
                WebDriverWait(self.driver, 2).until(
                    EC.invisibility_of_element_located((By.ID, "select2-drop-mask"))
                )
            except:
                self.log("⚠️ Overlay still detected before filling cornet weights, attempting to clear...", 'multiple_jobs')
                try:
                    webdriver.ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                except:
                    pass

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
                    
                    # Handle alerts loop - sometimes multiple alerts appear
                    for _ in range(3):  # Check up to 3 times
                        try:
                            WebDriverWait(self.driver, 2).until(EC.alert_is_present())
                            alert = self.driver.switch_to.alert
                            alert_text = alert.text
                            self.log(f"🔔 Alert handled: {alert_text}", 'multiple_jobs')
                            alert.accept()
                            time.sleep(1)
                        except:
                            break  # No more alerts
                            
                    # try:
                    #     alert = self.driver.switch_to.alert
                    #     alert_text = alert.text
                    #     self.log(f"🔔 Result Alert: {alert_text}", 'multiple_jobs')
                    #     alert.accept()
                    #     time.sleep(1)
                    # except Exception as e:
                    #     pass # self.log(f"❌ Error handling result alert: {str(e)}", 'multiple_jobs')
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
                                    # Tab out to trigger events
                                    element.send_keys(Keys.TAB)
                                    time.sleep(0.1) # Small delay
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
        if hasattr(self, 'progress_label') and self.progress_label:
            self.progress_label.config(text=progress)

    def update_results(self, results):
        """Update results label"""
        if hasattr(self, 'results_label') and self.results_label:
            self.results_label.config(text=results)
    
    def update_jobs_list(self, job_summary):
        """Update jobs list in treeview with status from portal scan only"""
        # Clear existing items
        for item in self.jobs_tree.get_children():
            self.jobs_tree.delete(item)
        
        self.log(f"📊 Loading job list for {len(job_summary)} jobs...", 'multiple_jobs')
        
        # Scan Fire Assaying portal to check availability
        self.log(f"🔍 Scanning Fire Assaying portal for job availability...", 'multiple_jobs')
        portal_jobs_list = self.scan_fire_assaying_portal()
        
        # Convert list to dict for faster lookup
        portal_jobs_map = {j['job_no']: j for j in portal_jobs_list}
        
        # Add new items with portal status
        for i, job in enumerate(job_summary):
            job_no = job['job_no']
            request_no = job['request_no']
            
            # Determine status based on portal availability
            if job_no in portal_jobs_map:
                p_job = portal_jobs_map[job_no]
                if p_job.get('needs_initial_values'):
                    status = "⚠️ Needs Initial Values"
                elif p_job.get('available'):
                    status = "🎯 Ready to Process"
                elif p_job.get('is_completed'):  # Should be filtered out but just in case
                    status = "✅ Completed"
                else:
                    status = "⏳ Pending in Portal" # Seen in list but not actionable
            else:
                # Not found in the Fire Assaying list
                # Could be completed or not yet assigned
                status = "❓ Not in Fire Assaying List"

            # Check special case for "Completed" if we want to guess
            # but rely on "Not in List" generally
            
            self.jobs_tree.insert('', 'end', values=(
                '☐',  # Checkbox column (unchecked by default)
                job['job_no'],
                job['request_no'],
                job['total_lots'],
                f"{job['total_button_weight']:.2f}",
                f"{job['total_scrap_weight']:.2f}",
                status
            ))
        
        # Auto-select jobs that are ready to process
        auto_selected_count = self.auto_select_ready_jobs()
        
        # Update selection status
        self.update_selection_status()
        self.log(f"✅ Loaded {len(job_summary)} jobs. Status updated from portal scan.", 'multiple_jobs')
        
        if auto_selected_count > 0:
            self.log(f"🎯 Auto-selected {auto_selected_count} jobs that are ready to process", 'multiple_jobs')
        else:
            self.log(f"ℹ️ No jobs are ready to process at this time", 'multiple_jobs')
    
    
    def auto_select_ready_jobs(self):
        """Auto-select jobs that are ready to process (available in portal)"""
        selected_count = 0
        
        for item in self.jobs_tree.get_children():
            values = self.jobs_tree.item(item, 'values')
            status = values[6]  # Status column
            
            # Auto-select if status is "Ready to Process" or "Available in Portal"
            if "🎯 Ready to Process" in status or "🟢 Available in Portal" in status:
                # Update checkbox to checked
                new_values = list(values)
                new_values[0] = '☑'  # Checked checkbox
                self.jobs_tree.item(item, values=new_values)
                selected_count += 1
        
        return selected_count
    
    def update_job_status(self, job_no, status):
        """Update status of a specific job in treeview"""
        for item in self.jobs_tree.get_children():
            values = self.jobs_tree.item(item, 'values')
            if values[1] == str(job_no):  # Job No is now column 1 (after checkbox)
                # Update the status column (column 6)
                new_values = list(values)
                new_values[6] = status
                self.jobs_tree.item(item, values=new_values)
                break
    
    def get_batch_job_statuses(self, job_summary):
        """Get database statuses for multiple jobs in a single batch query"""
        try:
            connection = self.get_database_connection()
            if not connection:
                # Return default statuses if connection fails
                return ["⏳ Pending (DB Error)"] * len(job_summary)
            
            cursor = connection.cursor()
            
            # Extract job numbers and request numbers
            job_numbers = []
            request_numbers = []
            for job in job_summary:
                # Extract original job number if it contains lot info
                job_no = job['job_no']
                original_job_no = job_no.split(' (Lot ')[0] if ' (Lot ' in job_no else job_no
                job_numbers.append(original_job_no)
                request_numbers.append(job['request_no'])
            
            # Build batch query with placeholders
            placeholders = ','.join(['%s'] * len(job_numbers))
            query = f"""
                SELECT job_no, request_no, status 
                FROM job_cards 
                WHERE job_no IN ({placeholders})
            """
            
            cursor.execute(query, tuple(job_numbers))
            results = cursor.fetchall()
            
            # Create a lookup dictionary
            status_lookup = {}
            for job_no, request_no, status in results:
                key = f"{job_no}_{request_no}"
                status_lookup[key] = status if status else "⏳ Pending"
            
            # Build status list in the same order as job_summary
            statuses = []
            for i, job in enumerate(job_summary):
                job_no = job_numbers[i]
                request_no = request_numbers[i]
                key = f"{job_no}_{request_no}"
                statuses.append(status_lookup.get(key, "❓ Not Found"))
            
            cursor.close()
            connection.close()
            
            return statuses
            
        except Exception as e:
            self.log(f"❌ Error getting batch job statuses: {str(e)}", 'multiple_jobs')
            # Return default statuses on error
            return ["⏳ Pending (DB Error)"] * len(job_summary)
    
    def scan_fire_assaying_portal(self):
        """Scan Fire Assaying portal to get available jobs"""
        try:
            if not self.driver:
                self.log("❌ Browser not available for portal scanning", 'multiple_jobs')
                return []
            
            self.log("🌐 Navigating to Fire Assaying portal...", 'multiple_jobs')
            fire_assay_url = build_portal_url("/MANAK/NewArticlesListForFireAssaying")
            self.driver.get(fire_assay_url)
            
            # Wait for page to load
            time.sleep(3)
            
            # Find the table containing job data
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            portal_jobs = []
            
            for table in tables:
                if "Request No" in table.text and "Job No" in table.text:
                    self.log("✅ Found Fire Assaying table", 'multiple_jobs')
                    rows = table.find_elements(By.TAG_NAME, "tr")[1:]  # Skip header
                    
                    for row in rows:
                        try:
                            cells = row.find_elements(By.TAG_NAME, "td")
                            if len(cells) >= 6:
                                job_no = cells[2].text.strip()  # Job No column
                                request_no = cells[1].text.strip()  # Request No column
                                fire_assay_status = cells[6].text.strip()  # Fire Assaying column
                                
                                if job_no and job_no.isdigit():
                                    # Get Fire Assaying Time status (last column)
                                    fire_assay_time = cells[7].text.strip() if len(cells) > 7 else ""
                                    
                                    # Only add jobs that are NOT completed
                                    # Available = "Fire Assaying" link exists AND not "Completed"
                                    is_completed = "Completed" in fire_assay_time or fire_assay_time == "Completed"
                                    has_fire_assaying_link = fire_assay_status == "Fire Assaying" or "Fire Assaying" in fire_assay_status
                                    needs_initial_values = "Please Fill Initial Values" in fire_assay_time
                                    
                                    # Only add if NOT completed
                                    if not is_completed:
                                        portal_jobs.append({
                                            'job_no': job_no,
                                            'request_no': request_no,
                                            'fire_assay_status': fire_assay_status,
                                            'fire_assay_time': fire_assay_time,
                                            'available': has_fire_assaying_link and not needs_initial_values,
                                            'needs_initial_values': needs_initial_values,
                                            'is_completed': is_completed
                                        })
                        except Exception as e:
                            continue
                    break
            
            self.log(f"🔍 Found {len(portal_jobs)} jobs in Fire Assaying portal (excluding completed jobs)", 'multiple_jobs')
            
            # Debug: Show available vs needs initial values
            available_count = sum(1 for j in portal_jobs if j['available'])
            needs_initial_count = sum(1 for j in portal_jobs if j['needs_initial_values'])
            self.log(f"   📊 {available_count} jobs available, {needs_initial_count} need initial values", 'multiple_jobs')
            return portal_jobs
            
        except Exception as e:
            self.log(f"❌ Error scanning Fire Assaying portal: {str(e)}", 'multiple_jobs')
            return []
    
    def get_portal_status_for_job(self, job_no, portal_jobs):
        """Get portal status for a specific job"""
        for portal_job in portal_jobs:
            if portal_job['job_no'] == str(job_no):
                if portal_job['available']:
                    return "🟢 Available in Portal"
                elif portal_job['needs_initial_values']:
                    return "🟡 Needs Initial Values"
                else:
                    return "🟡 In Portal (Not Ready)"
        
        # Not found in portal - could be completed or not yet available
        return "🔴 Not in Portal (Completed or Not Ready)"
    
    def combine_statuses(self, db_status, portal_status):
        """Combine database and portal statuses into a single status"""
        # If database shows completed, keep that
        if "✅ Completed" in db_status:
            return db_status
        
        # If database shows processing, keep that
        if "🔄 Processing" in db_status:
            return db_status
        
        # PRIORITY: Show portal status first (it's more current)
        if "🟢 Available in Portal" in portal_status:
            return "🎯 Ready to Process"
        
        if "🟡 Needs Initial Values" in portal_status:
            return "🟡 Needs Initial Values"
        
        if "🟡 In Portal (Not Ready)" in portal_status:
            return "🟡 In Portal (Not Ready)"
        
        if "🔴 Not in Portal (Completed or Not Ready)" in portal_status:
            return "🔴 Completed or Not in Portal"
        
        # If database shows pending and portal shows available, combine them
        if "⏳ Pending" in db_status and "🟢 Available in Portal" in portal_status:
            return "🎯 Ready to Process"
        
        # If database shows pending but not in portal
        if "⏳ Pending" in db_status and "🔴 Not in Portal" in portal_status:
            return "⏳ Pending (Not in Portal)"
        
        # Return the portal status if database is pending
        if "⏳ Pending" in db_status:
            return portal_status
        
        # Default to database status
        return db_status

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
