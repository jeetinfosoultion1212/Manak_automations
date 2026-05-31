#!/usr/bin/env python3
"""
Completed Jobs Scanner Module
Scans completed articles from MANAK portal CompletedArticlesListForDelieveryVoucher
Allows user to select a month and scans each day's data automatically.
Stores results in job_cards table (or a dedicated completed_jobs table).
"""

from typing import TYPE_CHECKING, Any, Callable, Optional, Dict, List, cast
import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.scrolledtext as st
import threading
import time
import datetime
import calendar
import traceback
import re
import os
import shutil

# Fix MySQL localization issue
os.environ['LANG'] = 'C'
os.environ['LC_ALL'] = 'C'
os.environ['LC_MESSAGES'] = 'C'

import requests

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver
else:
    WebDriver = Any

try:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.wait import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException
except ImportError:
    pass

try:
    from config import DB_CONFIG
    import config
except ImportError:
    DB_CONFIG = {}
    config = None

# MySQL not needed - API only

try:
    from .job_card_exporter import JobCardExporter
except ImportError:
    JobCardExporter = None


from portal_config import build_portal_url, portal_base


def _completed_list_url():
    return build_portal_url("/MANAK/CompletedArticlesListForDelieveryVoucher")


class CompletedJobsScanner:
    """Handles scanning completed jobs from MANAK portal by date range"""

    def __init__(self, driver: Optional[WebDriver], log_callback: Optional[Callable[[str, str], None]], 
                 license_check_callback: Optional[Callable[[], bool]], app_context: Optional[Any] = None) -> None:
        self.driver: Optional[WebDriver] = driver
        self.log_callback: Optional[Callable[[str, str], None]] = log_callback
        self.license_check_callback: Optional[Callable[[], bool]] = license_check_callback
        self.app_context: Optional[Any] = app_context
        self.db_config: Dict[str, Any] = DB_CONFIG if DB_CONFIG else {}
        self.api_url: str = getattr(config, 'CHECK_JOBS_API_URL', '') if config else ''
        self.save_api_url: str = getattr(config, 'SAVE_JOB_API_URL', '') if config else ''
        self.manage_jeweller_url: str = getattr(config, 'MANAGE_JEWELLER_API_URL', '') if config else ''
        self.http_session = requests.Session()
        self.is_processing: bool = False
        self.current_firm_id: str = self._get_firm_id()
        self._scan_cancelled: bool = False
        self.log_visible: bool = False
        self._ensured_jewellers: set[tuple[str, str]] = set()

        # Scanned jobs buffer
        self.scanned_jobs: List[Dict[str, Any]] = []

        # UI widget refs
        self.scan_log_text: Optional[st.ScrolledText] = None
        self.status_label: Optional[ttk.Label] = None
        self.progress_bar: Optional[ttk.Progressbar] = None
        self.progress_var: Optional[tk.DoubleVar] = None
        self.preview_tree: Optional[ttk.Treeview] = None
        self.save_selected_btn: Optional[ttk.Button] = None
        self.select_all_var: Optional[tk.BooleanVar] = None
        self.stats_labels: Dict[str, ttk.Label] = {}
        self.scan_btn: Optional[ttk.Button] = None
        self.stop_btn: Optional[ttk.Button] = None
        self.export_btn: Optional[ttk.Button] = None
        self.toggle_log_btn: Optional[ttk.Button] = None

        # Month/Year selectors
        self.month_var: Optional[tk.StringVar] = None
        self.year_var: Optional[tk.StringVar] = None
        self.date_from_var: Optional[tk.StringVar] = None
        self.date_to_var: Optional[tk.StringVar] = None
        self.scan_mode_var: Optional[tk.StringVar] = None   # 'month' or 'range'
        
        # Frame refs
        self.paned: Optional[ttk.PanedWindow] = None
        self.side_panel: Optional[ttk.Frame] = None
        self.month_frame: Optional[ttk.Frame] = None
        self.range_frame: Optional[ttk.Frame] = None

    # ─────────────────────────── helpers ────────────────────────────

    def _get_firm_id(self) -> str:
        try:
            if self.app_context and hasattr(self.app_context, 'license_manager'):
                lm = self.app_context.license_manager
                if lm:
                    # Try direct firm_id attribute first
                    if hasattr(lm, 'firm_id') and lm.firm_id:
                        return str(lm.firm_id)
                    # Then try get_license_status method
                    status = lm.get_license_status()
                    if status and status.get('firm_id'):
                        return str(status['firm_id'])
            return "2"  # Default fallback
        except Exception as e:
            self.log(f"  ⚠️ Warning: Could not get firm_id, using default: {e}")
            return "2"

    def _wait_for_page_ready(self, timeout: int = 6) -> None:
        if self.driver is None:
            return
        WebDriverWait(self.driver, timeout).until(
            lambda driver: driver.execute_script("return document.readyState") == "complete"
        )
    
    def refresh_current_firm_id(self) -> None:
        """Refresh the current firm ID from license manager"""
        old_id = self.current_firm_id
        self.current_firm_id = self._get_firm_id()
        if old_id != self.current_firm_id:
            self.log(f"🔄 Firm ID changed: {old_id} → {self.current_firm_id}")
        else:
            self.log(f"🔄 Firm ID confirmed: {self.current_firm_id}")

    def log(self, message: str, level: str = 'info') -> None:
        """Thread-safe log"""
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        formatted = f"[{ts}] {message}"

        def _ui():
            if self.scan_log_text:
                try:
                    self.scan_log_text.config(state='normal')
                    self.scan_log_text.insert('end', formatted + '\n')
                    self.scan_log_text.see('end')
                    self.scan_log_text.config(state='disabled')
                except Exception:
                    pass

        if self.scan_log_text:
            self.scan_log_text.after(0, _ui)
        if self.log_callback:
            try:
                self.log_callback(message, level)
            except Exception:
                pass

    def update_status(self, message: str, status_type: str = 'info') -> None:
        colors = {'info': '#17a2b8', 'success': '#28a745', 'warning': '#ffc107', 'danger': '#dc3545'}

        def _u():
            if self.status_label:
                try:
                    self.status_label.config(text=message, foreground=colors.get(status_type, '#17a2b8'))
                except Exception:
                    pass

        if self.status_label:
            self.status_label.after(0, _u)

    def update_progress(self, value: float, message: str = "") -> None:
        def _u():
            if self.progress_var:
                try:
                    self.progress_var.set(value)
                except Exception:
                    pass

        if self.progress_bar:
            self.progress_bar.after(0, _u)
        if message:
            self.log(message)

    # ─────────────────────────── UI setup ────────────────────────────

    def setup_completed_jobs_tab(self, notebook):
        """Create and add the Completed Jobs tab to the notebook"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="✅ Completed Jobs")

        main = ttk.Frame(frame)
        main.pack(fill='both', expand=True, padx=15, pady=10)

        # ── Top control bar ──
        self._setup_controls(main)

        # ── Paned (table + log) ──
        self.paned = ttk.PanedWindow(main, orient='horizontal')
        self.paned.pack(fill='both', expand=True, pady=(8, 0))

        left = ttk.Frame(self.paned)
        self.paned.add(left, weight=4)
        self._setup_table(left)

        self.side_panel = ttk.Frame(self.paned)
        self._setup_side_panel(self.side_panel)
        self.log_visible = False

    def _setup_controls(self, parent):
        ctrl = ttk.LabelFrame(parent, text="🗓️ Date Selection & Controls", padding=8)
        ctrl.pack(fill='x', pady=(0, 6))

        # Row 1: mode toggle
        mode_row = ttk.Frame(ctrl)
        mode_row.pack(fill='x', pady=(0, 6))

        self.scan_mode_var = tk.StringVar(value='month')
        ttk.Radiobutton(mode_row, text="📅 Scan Full Month", variable=self.scan_mode_var,
                        value='month', command=self._on_mode_change).pack(side='left', padx=(0, 20))
        ttk.Radiobutton(mode_row, text="📆 Scan Date Range", variable=self.scan_mode_var,
                        value='range', command=self._on_mode_change).pack(side='left')

        # Row 2: month selector (visible when mode == 'month')
        self.month_frame = ttk.Frame(ctrl)
        self.month_frame.pack(fill='x', pady=(0, 4))

        ttk.Label(self.month_frame, text="Month:").pack(side='left', padx=(0, 4))
        now = datetime.datetime.now()
        months = [f"{i:02d} - {calendar.month_name[i]}" for i in range(1, 13)]
        self.month_var = tk.StringVar(value=months[now.month - 1])
        month_cb = ttk.Combobox(self.month_frame, textvariable=self.month_var,
                                values=months, width=18, state='readonly')
        month_cb.pack(side='left', padx=(0, 12))

        ttk.Label(self.month_frame, text="Year:").pack(side='left', padx=(0, 4))
        years = [str(y) for y in range(now.year - 3, now.year + 2)]
        self.year_var = tk.StringVar(value=str(now.year))
        year_cb = ttk.Combobox(self.month_frame, textvariable=self.year_var,
                               values=years, width=8, state='readonly')
        year_cb.pack(side='left')

        # Row 3: range selector (visible when mode == 'range')
        self.range_frame = ttk.Frame(ctrl)

        ttk.Label(self.range_frame, text="From (MM/DD/YYYY):").pack(side='left', padx=(0, 4))
        self.date_from_var = tk.StringVar(value=now.strftime("%m/%d/%Y"))
        ttk.Entry(self.range_frame, textvariable=self.date_from_var, width=14).pack(side='left', padx=(0, 12))

        ttk.Label(self.range_frame, text="To (MM/DD/YYYY):").pack(side='left', padx=(0, 4))
        self.date_to_var = tk.StringVar(value=now.strftime("%m/%d/%Y"))
        ttk.Entry(self.range_frame, textvariable=self.date_to_var, width=14).pack(side='left')

        # Initially hide range_frame (starts in month mode)
        # self.range_frame stays un-packed

        # Row 4: action buttons
        btn_row = ttk.Frame(ctrl)
        btn_row.pack(fill='x', pady=(6, 0))

        self.scan_btn = ttk.Button(btn_row, text="🚀 Start Scanning",
                                   command=self.start_scanning, style='Success.TButton')
        self.scan_btn.pack(side='left', padx=(0, 8))

        self.stop_btn = ttk.Button(btn_row, text="⏹ Stop", command=self._stop_scan,
                                   style='Danger.TButton', state='disabled')
        self.stop_btn.pack(side='left', padx=(0, 8))

        # Select all + save on right
        self.select_all_var = tk.BooleanVar()
        ttk.Checkbutton(btn_row, text="☑ Select All",
                        variable=self.select_all_var,
                        command=self._toggle_select_all).pack(side='right', padx=(0, 8))

        self.save_selected_btn = ttk.Button(btn_row, text="💾 Save Selected",
                                            command=self.save_selected_jobs,
                                            style='Info.TButton', state='disabled')
        self.save_selected_btn.pack(side='right', padx=(0, 8))

        # Export to Excel button
        self.export_btn = ttk.Button(btn_row, text="📊 Export Excel",
                                     command=self.export_jobs_to_excel,
                                     style='Info.TButton', state='disabled')
        self.export_btn.pack(side='right', padx=(0, 8))

        # Toggle log button
        self.toggle_log_btn = ttk.Button(btn_row, text="📝 Show Log",
                                         command=self._toggle_log)
        self.toggle_log_btn.pack(side='right')

    def _on_mode_change(self) -> None:
        if self.scan_mode_var is not None and self.range_frame is not None and self.month_frame is not None:
            if self.scan_mode_var.get() == 'month':
                self.range_frame.pack_forget()
                self.month_frame.pack(fill='x', pady=(0, 4))
            else:
                self.month_frame.pack_forget()
                self.range_frame.pack(fill='x', pady=(0, 4))

    def _setup_table(self, parent):
        columns = ('sel', 'date', 'request_no', 'job_no', 'jeweller', 'address', 'licence',
                   'item', 'purity', 'pcs', 'reject_pcs', 'weight', 'status')
        self.preview_tree = ttk.Treeview(parent, columns=columns,
                                          show='headings', selectmode='extended', height=22)

        hdrs = [('sel', '☑', 40), ('date', 'Date', 90), ('request_no', 'Request No', 100),
                ('job_no', 'Job No', 100), ('jeweller', 'Jeweller', 180),
                ('address', 'Address', 200), ('licence', 'License No', 100), ('item', 'Item', 100),
                ('purity', 'Purity', 70), ('pcs', 'Pcs', 50),
                ('reject_pcs', 'Reject Pcs', 70), ('weight', 'Weight(g)', 85), ('status', 'Status', 100)]

        for col, text, w in hdrs:
            self.preview_tree.heading(col, text=text)
            anchor = 'center' if col in ('sel', 'pcs', 'reject_pcs', 'weight', 'purity') else 'w'
            self.preview_tree.column(col, width=w, anchor=anchor, minwidth=w - 10)

        v_scroll = ttk.Scrollbar(parent, orient='vertical', command=self.preview_tree.yview)
        h_scroll = ttk.Scrollbar(parent, orient='horizontal', command=self.preview_tree.xview)
        self.preview_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.preview_tree.grid(row=0, column=0, sticky='nsew')
        v_scroll.grid(row=0, column=1, sticky='ns')
        h_scroll.grid(row=1, column=0, sticky='ew')
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        self.preview_tree.bind('<Button-1>', self._on_tree_click)

        # Progress row
        prog_row = ttk.Frame(parent)
        prog_row.grid(row=2, column=0, columnspan=2, sticky='ew', pady=(6, 0))

        self.status_label = ttk.Label(prog_row, text="Ready", font=('Segoe UI', 9))
        self.status_label.pack(side='left', padx=(0, 8))

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(prog_row, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(side='left', fill='x', expand=True)

    def _setup_side_panel(self, parent):
        stats_frame = ttk.LabelFrame(parent, text="📊 Stats", padding=5)
        stats_frame.pack(fill='x', pady=(0, 8))

        for key, label, color in [
            ('dates_scanned', 'Dates Scanned: 0', '#007bff'),
            ('jobs_found', 'Jobs Found: 0', '#28a745'),
            ('jobs_saved', 'Jobs Saved: 0', '#17a2b8'),
            ('errors', 'Errors: 0', '#dc3545'),
        ]:
            lbl = ttk.Label(stats_frame, text=label, font=('Segoe UI', 9, 'bold'), foreground=color)
            lbl.pack(anchor='w')
            self.stats_labels[key] = lbl

        log_frame = ttk.LabelFrame(parent, text="📝 Scan Log", padding=5)
        log_frame.pack(fill='both', expand=True)

        import tkinter.scrolledtext as st
        self.scan_log_text = st.ScrolledText(log_frame, height=12, font=('Consolas', 8),
                                              bg='#f8f9fa', fg='#495057', state='disabled')
        self.scan_log_text.pack(fill='both', expand=True)

    # ─────────────── tree interaction ───────────────

    def _on_tree_click(self, event: Any) -> None:
        if self.preview_tree is None:
            return
        region = self.preview_tree.identify('region', event.x, event.y)
        if region == 'cell':
            col = self.preview_tree.identify_column(event.x)
            item_id = self.preview_tree.identify_row(event.y)
            if col == '#1' and item_id:
                idx = self.preview_tree.index(item_id)
                if idx < len(self.scanned_jobs):
                    self.scanned_jobs[idx]['selected'] = not self.scanned_jobs[idx].get('selected', False)
                    vals = list(self.preview_tree.item(item_id, 'values'))
                    vals[0] = '☑' if self.scanned_jobs[idx]['selected'] else '☐'
                    self.preview_tree.item(item_id, values=vals)

    def _toggle_select_all(self) -> None:
        if self.select_all_var is None or self.preview_tree is None:
            return
        sel = self.select_all_var.get()
        children = self.preview_tree.get_children()
        for i, job in enumerate(self.scanned_jobs):
            job['selected'] = sel
            if i < len(children):
                vals = list(self.preview_tree.item(children[i], 'values'))
                vals[0] = '☑' if sel else '☐'
                self.preview_tree.item(children[i], values=vals)

    def _toggle_log(self) -> None:
        if self.paned is None or self.side_panel is None or self.toggle_log_btn is None:
            return
        if self.log_visible:
            self.paned.forget(self.side_panel)
            self.toggle_log_btn.config(text="📝 Show Log")
            self.log_visible = False
        else:
            self.paned.add(self.side_panel, weight=1)
            self.toggle_log_btn.config(text="📝 Hide Log")
            self.log_visible = True

    # ─────────────── scanning ────────────────────────

    def _stop_scan(self) -> None:
        self._scan_cancelled = True
        self.log("🛑 Stop requested — will stop after current date...")
        self.update_status("Stopping...", "warning")

    def start_scanning(self) -> None:
        if self.is_processing:
            messagebox.showwarning("Busy", "Scan already in progress!")
            return

        # Refresh driver
        if self.app_context and hasattr(self.app_context, 'driver'):
            self.driver = getattr(self.app_context, 'driver')

        if not self.driver:
            messagebox.showerror("No Browser",
                                 "Browser not open.\n\n1. Go to 'Login in MANAK' tab\n2. Open & login browser\n3. Return here")
            return

        try:
            _ = self.driver.current_url
        except Exception:
            self.driver = None
            if self.app_context:
                self.app_context.driver = None
            messagebox.showerror("Browser Disconnected", "Browser was closed. Please reopen.")
            return

        # Build date list
        try:
            dates = self._build_date_list()
        except ValueError as e:
            messagebox.showerror("Date Error", str(e))
            return

        if not dates:
            messagebox.showwarning("No Dates", "No dates in the selected range.")
            return

        self._scan_cancelled = False
        threading.Thread(target=self._scan_worker, args=(dates,), daemon=True).start()

    def _build_date_list(self) -> List[datetime.date]:
        """Build list of (datetime.date) objects to scan"""
        if (self.scan_mode_var is None or self.month_var is None or 
            self.year_var is None or self.date_from_var is None or self.date_to_var is None):
            return []
        
        mode = self.scan_mode_var.get()
        dates: List[datetime.date] = []

        if mode == 'month':
            month_str = self.month_var.get()  # "03 - March"
            month_num = int(month_str.split(' ')[0])
            year_num = int(self.year_var.get())
            _, last_day = calendar.monthrange(year_num, month_num)
            for d in range(1, last_day + 1):
                dates.append(datetime.date(year_num, month_num, d))
        else:
            from_str = self.date_from_var.get().strip()
            to_str = self.date_to_var.get().strip()
            try:
                from_dt = datetime.datetime.strptime(from_str, "%m/%d/%Y").date()
                to_dt = datetime.datetime.strptime(to_str, "%m/%d/%Y").date()
            except ValueError:
                raise ValueError(f"Invalid date format. Please use MM/DD/YYYY.\nFrom: {from_str}\nTo: {to_str}")
            if from_dt > to_dt:
                raise ValueError("'From' date cannot be after 'To' date.")
            cur = from_dt
            while cur <= to_dt:
                dates.append(cur)
                cur += datetime.timedelta(days=1)

        return dates

    def _scan_worker(self, dates: List[datetime.date]) -> None:
        """Background worker: iterate dates, enter each in form, extract jobs"""
        self.is_processing = True
        self._scan_cancelled = False

        def _ui_start() -> None:
            if self.scan_btn and self.stop_btn and self.save_selected_btn and self.preview_tree:
                self.scan_btn.config(state='disabled')
                self.stop_btn.config(state='normal')
                self.save_selected_btn.config(state='disabled')
                # Clear table
                for row in self.preview_tree.get_children():
                    self.preview_tree.delete(row)

        if self.preview_tree:
            self.preview_tree.after(0, _ui_start)  # type: ignore
        self.scanned_jobs = []

        stats = {'dates_scanned': 0, 'jobs_found': 0, 'jobs_saved': 0, 'errors': 0}
        total = len(dates)

        self.log(f"▶ Starting scan for {total} date(s)")
        self.update_status(f"Starting — {total} dates to scan", 'info')

        try:
            # Refresh firm ID before scan
            if hasattr(self, 'refresh_current_firm_id'):
                self.update_progress(1, "🔄 Refreshing firm settings...")
                self.refresh_current_firm_id()
            
            # Navigate to the page once
            self.update_progress(2, "🌐 Navigating to Completed Articles page...")
            if self.driver is None:
                self.log("❌ Driver is not initialized")
                return
            self.driver.get(_completed_list_url())
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(1.5)

            for idx, date_obj in enumerate(dates):
                if self._scan_cancelled:
                    self.log("🛑 Scan cancelled by user.")
                    break

                pct = int(5 + (idx / total) * 90)  # 5% + 90% for dates, leaving 5% for finalization
                pct = min(pct, 95)  # Cap at 95% to prevent overshooting
                date_str_display = date_obj.strftime("%m-%d-%Y")
                date_str_portal = date_obj.strftime("%m/%d/%Y")  # portal expects MM/DD/YYYY format

                self.update_progress(pct, f"📅 Scanning {date_str_display} ({idx+1}/{total})...")
                self.log(f"\n--- Date: {date_str_display} ---")

                try:
                    jobs = self._scan_one_date(date_str_portal)
                    stats['dates_scanned'] += 1

                    if jobs:
                        self.log(f"  Found {len(jobs)} job(s)")
                        stats['jobs_found'] += len(jobs)

                        for job in jobs:
                            job['selected'] = True
                            job['scan_date'] = date_str_display
                            self.scanned_jobs.append(job)

                            def _add_row(j: Dict[str, Any] = job) -> None:
                                if self.preview_tree:
                                    self.preview_tree.insert('', 'end', values=(
                                        '☑',
                                        j.get('scan_date', ''),
                                        j.get('request_no', 'N/A'),
                                        j.get('job_no', 'N/A'),
                                        (j.get('jeweller_name', 'N/A'))[:35],
                                        (j.get('jeweller_address', 'N/A'))[:50],
                                        j.get('licence_no', 'N/A'),
                                        (j.get('item', 'N/A'))[:20],
                                        j.get('purity', '—'),
                                        j.get('pcs', 0),
                                        j.get('reject_pcs', 0),
                                        f"{j.get('weight', 0):.3f}",
                                        '⏳ Pending'
                                    ))

                            if self.preview_tree:
                                self.preview_tree.after(0, _add_row)  # type: ignore
                    else:
                        self.log(f"  No jobs on this date.")

                    self._update_stats(stats)

                except Exception as e:
                    self.log(f"  ❌ Error on {date_str_display}: {e}")
                    stats['errors'] += 1
                    self._update_stats(stats)
                    continue

                time.sleep(0.4)  # polite delay

        except Exception as e:
            self.log(f"❌ Fatal error: {e}\n{traceback.format_exc()}")
            self.update_status("❌ Scan failed", 'danger')
        finally:
            self.is_processing = False
            self.update_progress(100, "✅ Scan complete")
            self.update_status(
                f"Done — {stats['jobs_found']} jobs found across {stats['dates_scanned']} dates", 'success')

            def _ui_end() -> None:
                if self.scan_btn and self.stop_btn and self.save_selected_btn and self.export_btn:
                    self.scan_btn.config(state='normal')
                    self.stop_btn.config(state='disabled')
                    if self.scanned_jobs:
                        self.save_selected_btn.config(state='normal')
                        self.export_btn.config(state='normal')

            if self.preview_tree:
                self.preview_tree.after(0, _ui_end)  # type: ignore

            self.log(f"\n{'='*50}")
            self.log(f"📊 SCAN SUMMARY:")
            self.log(f"   Dates processed : {stats['dates_scanned']}")
            self.log(f"   Jobs found      : {stats['jobs_found']}")
            self.log(f"   Errors          : {stats['errors']}")
            self.log(f"{'='*50}\n")

    def _scan_one_date(self, date_str_portal: str) -> List[Dict[str, Any]]:
        """Enter a date in the portal form, click Go, extract the job list.
        Returns list of dicts with minimal job info (request_no, job_no, jeweller_name, etc.)
        Then for each job opens the voucher detail page and extracts full details.
        """
        if self.driver is None:
            return []
        try:
            # 1. Make sure we are on the right page (reload if necessary)
            try:
                cur_url = self.driver.current_url
                if _completed_list_url().split('?')[0] not in cur_url:
                    self.driver.get(_completed_list_url())
                    self._wait_for_page_ready(10)
            except Exception:
                self.driver.get(_completed_list_url())
                self._wait_for_page_ready(10)

            # 2. Clear and fill the date input  (id="toDate")
            try:
                date_input = WebDriverWait(self.driver, 8).until(
                    EC.presence_of_element_located((By.ID, "toDate"))
                )
                # Clear via JS then set value
                self.driver.execute_script("arguments[0].value = '';", date_input)
                self.driver.execute_script(f"arguments[0].value = '{date_str_portal}';", date_input)
                # Trigger change events so datepicker recognises the value
                self.driver.execute_script(
                    "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));", date_input
                )
                self.log(f"  ✓ Date set: {date_str_portal}")
            except Exception as e:
                self.log(f"  ❌ Could not set date field: {e}")
                return []

            # 3. Click the Go button  (id="submitform")
            try:
                go_btn = WebDriverWait(self.driver, 6).until(
                    EC.element_to_be_clickable((By.ID, "submitform"))
                )
                first_table_html = self.driver.execute_script(
                    "const table = document.querySelector('table'); return table ? table.innerHTML : '';"
                )
                self.driver.execute_script("arguments[0].click();", go_btn)
                self.log("  ✓ Clicked Go")
            except Exception as e:
                self.log(f"  ❌ Could not click Go button: {e}")
                return []

            # 4. Wait for result table
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda driver: (
                        driver.execute_script(
                            "const table = document.querySelector('table'); return table ? table.innerHTML : '';"
                        ) != first_table_html
                    ) or bool(driver.find_elements(By.TAG_NAME, "table"))
                )
            except TimeoutException:
                self.log("  ℹ️ No table appeared (possibly no jobs)")
                return []

            # 5. Parse job rows from the table
            jobs_basic = self._parse_job_list_table()
            if not jobs_basic:
                self.log("  ℹ️ Table found but no job rows extracted")
                return []

            self.log(f"  📋 {len(jobs_basic)} row(s) in list — opening each for details...")

            # 5b. Handle pagination - look for next page
            page_num = 1
            max_pages_to_scan = 100  # Safety limit
            
            while page_num <= max_pages_to_scan:
                # Check for next page button
                next_page_found = False
                try:
                    # FooTable pagination patterns
                    next_button_xpaths = [
                        "//a[@data-page='next']",  # FooTable next arrow
                        "//li[@class='footable-page-arrow']//a[@data-page='next']",
                        "//div[@class='pagination']//a[@class='next']",
                        "//a[contains(text(), 'Next')]",
                        "//button[contains(text(), 'Next')]",
                    ]
                    
                    found_button = None
                    for xpath in next_button_xpaths:
                        try:
                            elements = self.driver.find_elements(By.XPATH, xpath)
                            if elements:
                                for next_btn in elements:
                                    # Check if parent is disabled
                                    parent = next_btn.find_element(By.XPATH, "..")
                                    parent_class = parent.get_attribute('class') or ''
                                    
                                    if 'disabled' not in parent_class and next_btn.is_displayed():
                                        found_button = next_btn
                                        self.log(f"  📄 Found pagination next button")
                                        break
                            if found_button:
                                break
                        except Exception as e:
                            continue
                    
                    if found_button:
                        try:
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", found_button)
                            current_table_html = self.driver.execute_script(
                                "const table = document.querySelector('table'); return table ? table.innerHTML : '';"
                            )
                            self.driver.execute_script("arguments[0].click();", found_button)
                            WebDriverWait(self.driver, 6).until(
                                lambda driver: driver.execute_script(
                                    "const table = document.querySelector('table'); return table ? table.innerHTML : '';"
                                ) != current_table_html
                            )
                            
                            # Parse next page jobs
                            next_jobs = self._parse_job_list_table()
                            if next_jobs:
                                jobs_basic.extend(next_jobs)
                                self.log(f"  📋 Page {page_num + 1}: {len(next_jobs)} row(s) found (total: {len(jobs_basic)})")
                                page_num += 1
                                next_page_found = True
                            else:
                                self.log(f"  ℹ️ Next page button clicked but no jobs found")
                                break
                        except Exception as e:
                            self.log(f"  ⚠️ Error clicking next page: {e}")
                            break
                    else:
                        self.log(f"  ✓ Reached last page (total: {page_num})")
                        break
                except Exception as e:
                    self.log(f"  ⚠️ Pagination error: {e}")
                    break

            self.log(f"  📋 Total {len(jobs_basic)} job(s) to process...")

            # 6. For each job open the detail page and get full info
            full_jobs = []
            for ji, job_basic in enumerate(jobs_basic):
                if self._scan_cancelled:
                    break
                try:
                    self.log(f"    [{ji+1}/{len(jobs_basic)}] Opening job {job_basic.get('job_no', '?')}...")
                    full = self._get_job_details(job_basic)
                    if full:
                        full_jobs.append(full)
                    time.sleep(0.05)
                except Exception as ex:
                    self.log(f"    ⚠ Detail error for {job_basic.get('job_no', '?')}: {ex}")
                    # Still add the basic info so user can see it
                    job_basic['firm_id'] = self.current_firm_id
                    full_jobs.append(job_basic)

            return full_jobs

        except Exception as e:
            self.log(f"  ❌ _scan_one_date error: {e}")
            return []

    def _parse_job_list_table(self) -> List[Dict[str, Any]]:
        """Parse the results table on the Completed Articles list page"""
        if self.driver is None:
            return []
        jobs: List[Dict[str, Any]] = []
        try:
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            target = None
            for t in tables:
                txt = t.text
                if "Request No" in txt or "Job No" in txt or "Jeweller" in txt:
                    target = t
                    break

            if not target:
                # Try getting any meaningful table
                for t in tables:
                    rows = t.find_elements(By.TAG_NAME, "tr")
                    if len(rows) > 1:
                        target = t
                        break

            if not target:
                return []

            rows = target.find_elements(By.TAG_NAME, "tr")

            # Detect header row to know column positions
            header_cells = []
            if rows:
                hcells = rows[0].find_elements(By.TAG_NAME, "th")
                if not hcells:
                    hcells = rows[0].find_elements(By.TAG_NAME, "td")
                header_cells = [c.text.strip().lower() for c in hcells]

            # Try to map columns
            def _col(keywords):
                for kw in keywords:
                    for i, h in enumerate(header_cells):
                        if kw in h:
                            return i
                return -1

            col_req = _col(['request no', 'request'])
            col_job = _col(['job no', 'job card'])
            col_date = _col(['date'])
            col_jeweller = _col(['jeweller', 'party'])
            col_voucher_link = _col(['voucher', 'link', 'delivery'])

            for row in rows[1:]:
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if not cells or len(cells) < 2:
                        continue

                    def _cell(idx, default=''):
                        if 0 <= idx < len(cells):
                            return cells[idx].text.strip()
                        return default

                    request_no = _cell(col_req if col_req >= 0 else 1)
                    job_no = _cell(col_job if col_job >= 0 else 2)
                    job_date = _cell(col_date if col_date >= 0 else 3)
                    jeweller_name = _cell(col_jeweller if col_jeweller >= 0 else 4)

                    if not request_no and not job_no:
                        continue

                    # Extract voucher link
                    voucher_url = ""
                    links = row.find_elements(By.TAG_NAME, "a")
                    for link in links:
                        href = link.get_attribute("href") or ""
                        text = link.text.strip()
                        if "AHCDeliveryVoucher" in href or "Delivery" in text or "Voucher" in text:
                            voucher_url = href
                            break
                    # If no direct link, also try onclick
                    if not voucher_url:
                        for link in links:
                            onclick = link.get_attribute("onclick") or ""
                            if "AHCDeliveryVoucher" in onclick:
                                m = re.search(r"['\"]([^'\"]*AHCDeliveryVoucher[^'\"]*)['\"]", onclick)
                                if m:
                                    voucher_url = m.group(1)
                                    if voucher_url.startswith('/'):
                                        voucher_url = portal_base() + voucher_url
                                    break

                    jobs.append({
                        'request_no': request_no,
                        'job_no': job_no,
                        'job_date': job_date,
                        'jeweller_name': jeweller_name,
                        'voucher_url': voucher_url,
                        'material': 'Gold',
                    })
                except Exception:
                    continue

        except Exception as e:
            self.log(f"  ⚠ Table parse error: {e}")

        return jobs

    def _get_job_details(self, job_basic: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Open voucher detail page and extract full info"""
        if self.driver is None:
            return None
        try:
            request_no = job_basic.get('request_no', '')
            job_no = job_basic.get('job_no', '')
            material = job_basic.get('material', 'Gold')

            # Navigate to voucher page
            if job_basic.get('voucher_url'):
                self.driver.get(job_basic['voucher_url'])
            else:
                url = (f"{portal_base()}/MANAK/AHCDeliveryVoucher"
                       f"?requestNo={request_no}&jobNo={job_no}&material={material}")
                self.driver.get(url)

            self._wait_for_page_ready(8)

            details = {
                'firm_id': self.current_firm_id,
                'request_no': request_no,
                'job_no': job_no,
                'material_type': material,
                'jeweller_name': job_basic.get('jeweller_name', ''),
                'status': 'Complete',
                'purity': '',
                'huid_code': '',  # HUID ID/code from HUID Request Form
                'reject_pcs': 0,
                'bill_no': None,
                'is_billed': 0,
            }

            # Date - USE ACTUAL JOB DATE, NOT CURRENT DATE
            try:
                details['date_of_request'] = None
                # First try to get from job_basic (scanned date)
                jd = job_basic.get('job_date', '')
                if jd:
                    try:
                        details['date_of_request'] = datetime.datetime.strptime(
                            jd, '%d/%m/%Y').strftime('%Y-%m-%d')
                    except Exception:
                        pass
                
                # If not found, try to extract from page
                if not details['date_of_request']:
                    for xp in [
                        "//td[contains(text(),'Job Card Date')]/following-sibling::td",
                        "//label[contains(text(),'Job Card Date')]/following-sibling::*",
                    ]:
                        try:
                            d = self.driver.find_element(By.XPATH, xp).text.strip()
                            if d:
                                try:
                                    details['date_of_request'] = datetime.datetime.strptime(
                                        d, '%d/%m/%Y').strftime('%Y-%m-%d')
                                    break
                                except ValueError:
                                    details['date_of_request'] = d
                                    break
                        except Exception:
                            continue
                
                # Fallback to current date only if nothing found
                if not details['date_of_request']:
                    details['date_of_request'] = datetime.datetime.now().strftime('%Y-%m-%d')
            except Exception:
                details['date_of_request'] = datetime.datetime.now().strftime('%Y-%m-%d')

            # Jeweller Name
            for xp in [
                "//fieldset[.//legend[contains(text(),'Jeweller Details')]]//div[contains(normalize-space(),'Jeweller Name')]//span[@class='makeInitCap']",
                "//legend[contains(text(),'Jeweller Details')]/parent::fieldset//div[contains(normalize-space(),'Jeweller Name')]//span[@class='makeInitCap']",
                "//div[contains(text(),'Jeweller Name')]/following-sibling::div//span[@class='makeInitCap']",
                "//div[contains(normalize-space(),'Jeweller Name')]/following::div[1]//span[@class='makeInitCap']",
                "//span[contains(text(),'Jeweller Name')]/following::div//span[@class='makeInitCap']",
                "//td[contains(text(),'Jeweller Name')]/following-sibling::td//span[@class='makeInitCap']",
                "//td[contains(text(),'Jeweller Name')]/following-sibling::td",
                "//div[contains(text(),'Jeweller Name')]/following-sibling::div",
            ]:
                try:
                    t = self.driver.find_element(By.XPATH, xp).text.strip()
                    if t and len(t) > 2:
                        details['jeweller_name'] = t
                        break
                except Exception:
                    continue

            # Jeweller Address
            details['jeweller_address'] = ''
            details['jeweller_city'] = ''
            details['jeweller_state'] = ''
            for xp in [
                "//fieldset[.//legend[contains(text(),'Jeweller Details')]]//div[contains(normalize-space(),'Jeweller Address')]//span[@class='makeInitCap']",
                "//legend[contains(text(),'Jeweller Details')]/parent::fieldset//div[contains(normalize-space(),'Jeweller Address')]//span[@class='makeInitCap']",
                "//div[contains(text(),'Jeweller Address')]/following-sibling::div//span[@class='makeInitCap']",
                "//div[contains(normalize-space(),'Jeweller Address')]/following::div[1]//span[@class='makeInitCap']",
                "//span[contains(text(),'Jeweller Address')]/following::div//span[@class='makeInitCap']",
                "//td[contains(text(),'Jeweller Address')]/following-sibling::td//span[@class='makeInitCap']",
                "//td[contains(text(),'Jeweller Address')]/following-sibling::td",
                "//div[contains(.,'Address')]/following-sibling::div//span",
            ]:
                try:
                    t = self.driver.find_element(By.XPATH, xp).text.strip()
                    if t and len(t) > 4:
                        details['jeweller_address'] = t
                        break
                except Exception:
                    continue

            # License No
            details['licence_no'] = ''
            for xp in [
                "//div[contains(text(),'License Number')]/following-sibling::div//span[@class='makeInitCap']",
                "//div[contains(text(),'License Number')]/following-sibling::div//span",
                "//td[contains(text(),'License Number')]/following-sibling::td",
                "//td[contains(text(),'Licence Number')]/following-sibling::td",
            ]:
                try:
                    t = self.driver.find_element(By.XPATH, xp).text.strip()
                    if t and len(t) >= 4:
                        details['licence_no'] = t
                        break
                except Exception:
                    continue

            # Pieces - extract from table with colspan structure
            details['pcs'] = 0
            details['huid_pcs'] = 0
            details['reject_pcs'] = 0
            
            # Try to extract PCS from the table rows with colspan
            for xp in [
                "//tr[@id='divmangmt' or contains(@id,'divmangmt')][contains(normalize-space(),'Total Article Received By AHC')]//td[last()]",
                "//tr[@id='divmangmt'][contains(normalize-space(),'Total Article Received By AHC')]//td[position()=last()]",
                "//table[@id='tabAssignCenter']//tr[contains(normalize-space(),'Total Article Received By AHC')]//td[last()]",
                "//td[contains(normalize-space(),'Total Article Received By AHC')]/parent::tr//td[last()]",
                "//td[contains(text(),'Total Article Received By AHC')]/following-sibling::td",
                "//td[contains(text(),'Total Article Send By Jeweller')]/following-sibling::td",
            ]:
                try:
                    elem = self.driver.find_element(By.XPATH, xp)
                    t = elem.text.strip()
                    # Extract numeric value
                    num_match = re.search(r'(\d+(?:\.\d+)?)', t)
                    if num_match:
                        details['pcs'] = int(float(num_match.group(1)))
                        break
                except Exception:
                    continue
            
            # Reject/Fail Pieces
            for xp in [
                "//td[contains(text(),'Total Article Rejected')]/following-sibling::td",
                "//td[contains(text(),'Article Rejected')]/following-sibling::td",
                "//td[contains(text(),'Rejected Pieces')]/following-sibling::td",
                "//td[contains(text(),'Total Fail')]/following-sibling::td",
            ]:
                try:
                    t = self.driver.find_element(By.XPATH, xp).text.strip()
                    if t and t.isdigit():
                        details['reject_pcs'] = int(t)
                        break
                except Exception:
                    continue

            details['purity'] = ''


            # Weight
            details['weight'] = 0.0
            for xp in [
                "//tr[@id='divmangmt'][contains(normalize-space(),'Weight Observed By AHC')]//td[last()]",
                "//table[@id='tabAssignCenter']//tr[contains(normalize-space(),'Weight Observed By AHC')]//td[last()]",
                "//td[contains(normalize-space(),'Weight Observed By AHC')]/parent::tr//td[last()]",
                "//td[contains(text(),'Weight Observed By AHC')]/following-sibling::td",
                "//td[contains(text(),'Total Weight Declared By Jeweller')]/following-sibling::td",
            ]:
                try:
                    t = self.driver.find_element(By.XPATH, xp).text.strip()
                    t = re.sub(r'[^\d.]', '', t)
                    if t:
                        details['weight'] = float(t)
                        break
                except Exception:
                    continue

            # Cornet weight (in mg, converted to g)
            details['cornet_weight'] = 0.0
            for xp in [
                "//tr[@id='divmangmt'][contains(normalize-space(),'Weight of Cornet')]//td[last()]",
                "//table[@id='tabAssignCenter']//tr[contains(normalize-space(),'Weight of Cornet')]//td[last()]",
                "//td[contains(normalize-space(),'Weight of Cornet')]/parent::tr//td[last()]",
                "//td[contains(text(),'Weight of Cornet')]/following-sibling::td",
            ]:
                try:
                    t = self.driver.find_element(By.XPATH, xp).text.strip()
                    t = re.sub(r'[^\d.]', '', t)
                    if t:
                        details['cornet_weight'] = round(float(t) / 1000.0, 4)
                        break
                except Exception:
                    continue

            # Scrap weight (mg -> g)
            details['scrp_cornet_weight'] = 0.0
            for xp in [
                "//tr[@id='divmangmt'][contains(normalize-space(),'Weight of Scrapping')]//td[last()]",
                "//table[@id='tabAssignCenter']//tr[contains(normalize-space(),'Weight of Scrapping')]//td[last()]",
                "//td[contains(normalize-space(),'Weight of Scrapping')]/parent::tr//td[last()]",
                "//td[contains(text(),'Weight of Scrapping')]/following-sibling::td",
            ]:
                try:
                    t = self.driver.find_element(By.XPATH, xp).text.strip()
                    t = re.sub(r'[^\d.]', '', t)
                    if t:
                        details['scrp_cornet_weight'] = round(float(t) / 1000.0, 4)
                        break
                except Exception:
                    continue

            # Accepted items table → item, huid_list
            details['item'] = f"Job {job_no}"
            details['huid_list'] = []
            details['huid_pcs'] = 0
            details['fail_pcs'] = 0

            try:
                items_table = None
                for xp in [
                    "//table[@id='tabAcceptedArticles']",
                    "//legend[contains(text(),'Accepted Items')]/following::table[1]",
                    "//label[contains(text(),'Accepted Items')]/following::table[1]",
                ]:
                    try:
                        items_table = self.driver.find_element(By.XPATH, xp)
                        break
                    except Exception:
                        continue

                if items_table:
                    rows = items_table.find_elements(By.TAG_NAME, "tr")
                    cats = []
                    huid_details = []
                    for row in rows[1:]:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) >= 5:
                            cat = cells[1].text.strip()
                            huid = cells[3].text.strip()
                            w_text = cells[4].text.strip()
                            if cat and cat not in cats:
                                cats.append(cat)
                            huid_w = 0.0
                            try:
                                huid_w = float(re.sub(r'[^\d.]', '', w_text))
                            except Exception:
                                pass
                            if huid:
                                huid_details.append({
                                    'huid': huid,
                                    'item_category': cat,
                                    'weight': huid_w,
                                    'serial_no': cells[0].text.strip()
                                })
                    if cats:
                        details['item'] = ", ".join(cats)
                    if huid_details:
                        details['huid_list'] = huid_details
                        details['huid_pcs'] = len(huid_details)
            except Exception:
                pass

            if details['pcs'] > 0:
                details['huid_pcs'] = details['pcs']

            # Rejected items extraction - count from "Rejected Items Details" table
            try:
                reject_items_table = None
                for xp in [
                    "//h3[contains(text(),'Rejected Items')]/following::table[1]",
                    "//div[contains(text(),'Rejected Items Details')]/following::table[1]",
                    "//legend[contains(text(),'Rejected Items')]/following::table[1]",
                    "//table[contains(preceding-sibling::*/text(),'Rejected Items')]",
                ]:
                    try:
                        reject_items_table = self.driver.find_element(By.XPATH, xp)
                        if reject_items_table:
                            break
                    except Exception:
                        continue

                if reject_items_table:
                    rows = reject_items_table.find_elements(By.TAG_NAME, "tr")
                    reject_count = 0
                    # Count rows, excluding header
                    for row in rows[1:]:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        # Check if row has data (not "No Rejected Items" message)
                        row_text = row.text.strip()
                        if cells and len(cells) > 0 and "No Rejected Items" not in row_text:
                            reject_count += 1
                    
                    if reject_count > 0:
                        details['reject_pcs'] = reject_count
                        details['fail_pcs'] = reject_count
            except Exception:
                pass

            details['purity'] = self._extract_purity_from_huid_request(request_no, job_no)

            details['created_at'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return details

        except Exception as e:
            self.log(f"    ⚠ Detail extraction error: {e}")
            return job_basic  # Return basic info at minimum

    def _extract_purity_from_huid_request(self, request_no: str, job_no: str) -> str:
        if self.driver is None or not request_no or not job_no:
            return ''

        self.log(f"    🔍 Extracting purity from HUID Request Form...")
        try:
            import base64

            base64_request = base64.b64encode(request_no.encode()).decode()
            base64_job = base64.b64encode(job_no.encode()).decode()
            huid_url = (
                build_portal_url("/MANAK/UID_RequestFormViewPage")
                + f"?requestNo={base64_request}&jobNo={base64_job}&material=R29sZA%3D%3D"
            )

            self.driver.get(huid_url)
            self._wait_for_page_ready(6)

            all_rows = self.driver.find_elements(By.XPATH, "//table//tr")
            self.log(f"    🔍 Found {len(all_rows)} total row(s) in table")
            if len(all_rows) <= 1:
                return ''

            header_cells = all_rows[0].find_elements(By.TAG_NAME, "th")
            if not header_cells:
                header_cells = all_rows[0].find_elements(By.TAG_NAME, "td")

            headers = [cell.text.strip() for cell in header_cells]
            purity_col_index = -1
            item_col_index = -1
            best_item_score = -1

            for idx, header in enumerate(headers):
                header_lower = header.lower()
                if purity_col_index < 0 and (
                    'purity' in header_lower or 'grade' in header_lower or 'fineness' in header_lower
                ):
                    purity_col_index = idx

                item_score = -1
                if 'item category' in header_lower:
                    item_score = 4
                elif header_lower == 'item' or header_lower == 'article':
                    item_score = 3
                elif 'item' in header_lower or 'article' in header_lower:
                    item_score = 2
                elif 'category' in header_lower:
                    item_score = 1

                if item_score > best_item_score:
                    best_item_score = item_score
                    item_col_index = idx

            if purity_col_index >= 0:
                self.log(f"    ✅ Purity column selected: {headers[purity_col_index]} (index {purity_col_index})")
            if item_col_index >= 0:
                self.log(f"    ✅ Item column selected: {headers[item_col_index]} (index {item_col_index})")

            data_cells = all_rows[1].find_elements(By.TAG_NAME, "td")
            if purity_col_index >= 0 and len(data_cells) > purity_col_index:
                purity_text = data_cells[purity_col_index].text.strip()
                if purity_text and purity_text.lower() not in ['purity', 'grade', 'declared purity', '-']:
                    self.log(f"    ✅ Extracted purity: {purity_text}")
                    return purity_text

            self.log(f"    📋 First row data: {[cell.text.strip() for cell in data_cells]}")
            for col_idx, cell in enumerate(data_cells):
                cell_text = cell.text.strip()
                if cell_text and (
                    re.match(r'^\d{2}K\d+$', cell_text) or
                    re.match(r'^\d{3}$', cell_text) or
                    re.match(r'^[0-9.]+\s*K$', cell_text)
                ):
                    self.log(f"    ✅ Found purity by pattern at column {col_idx}: {cell_text}")
                    return cell_text
        except Exception as e:
            self.log(f"    ⚠️ Error accessing HUID page: {e}")

        return ''

    # ─────────────── saving ──────────────────────────

    def save_selected_jobs(self) -> None:
        selected = [j for j in self.scanned_jobs if j.get('selected', False)]
        if not selected:
            messagebox.showwarning("No Selection", "Please select at least one job to save.")
            return
        if not messagebox.askyesno("Confirm Save", f"Save {len(selected)} selected job(s) to database?"):
            return
        threading.Thread(target=self._save_worker, args=(selected,), daemon=True).start()

    def _save_worker(self, jobs: List[Dict[str, Any]]) -> None:
        if self.save_selected_btn is None or self.preview_tree is None:
            return
        
        save_btn = cast(ttk.Button, self.save_selected_btn)
        tree = cast(ttk.Treeview, self.preview_tree)
        tree.after(0, lambda: save_btn.config(state='disabled'))
        saved = 0
        errors = 0
        children = tree.get_children()

        self.log(f"\n{'='*50}")
        self.log(f"💾 Saving {len(jobs)} job(s)...")

        for i, job in enumerate(jobs):
            try:
                job_no = job.get('job_no', '?')
                self.log(f"  [{i+1}/{len(jobs)}] Saving {job_no}...")

                # Ensure jeweller
                self._ensure_jeweller(job)

                if self._save_job(job):
                    self.log(f"  ✅ Saved {job_no}")
                    saved += 1

                    # Update tree row
                    try:
                        idx = self.scanned_jobs.index(job)
                        if idx < len(children):
                            def _upd(iid: str = children[idx]) -> None:
                                vals = list(tree.item(iid, 'values'))
                                vals[-1] = '✅ Saved'
                                tree.item(iid, values=vals, tags=('saved',))
                                tree.tag_configure('saved', foreground='#28a745')
                            tree.after(0, _upd)
                    except Exception:
                        pass
                else:
                    self.log(f"  ❌ Failed {job_no}")
                    errors += 1

            except Exception as e:
                self.log(f"  ❌ Error saving: {e}")
                errors += 1

        self.log(f"\n📊 SAVE SUMMARY: Saved={saved}, Errors={errors}")
        self.log(f"{'='*50}\n")
        tree.after(0, lambda: save_btn.config(state='normal'))
        tree.after(0, lambda: messagebox.showinfo(
            "Save Complete", f"Saved: {saved}\nErrors: {errors}"))

    # ─────────────── export to excel ──────────────────────────

    def export_jobs_to_excel(self):
        """Export selected jobs to Excel with pricing calculations"""
        selected = [j for j in self.scanned_jobs if j.get('selected', False)]
        if not selected:
            messagebox.showwarning("No Selection", "Please select at least one job to export.")
            return
        
        if not JobCardExporter:
            messagebox.showerror("Error", "openpyxl library not installed. Please install it first.\npip install openpyxl")
            return
        
        if not messagebox.askyesno("Confirm Export", f"Export {len(selected)} selected job(s) to Excel?"):
            return
        
        threading.Thread(target=self._export_worker, args=(selected,), daemon=True).start()

    def _export_worker(self, jobs):
        """Background worker for Excel export + save to transactions table"""
        try:
            self.export_btn.after(0, lambda: self.export_btn.config(state='disabled'))  # type: ignore
            
            self.log(f"\n{'='*50}")
            self.log(f"📊 Exporting {len(jobs)} job(s) to Excel...")
            
            if JobCardExporter is None:
                self.log("❌ JobCardExporter not available")
                return
            
            exporter_cls = cast(type, JobCardExporter)
            exporter = exporter_cls("exports")
            
            # Prepare all job data for single export - PRESERVE FULL PRECISION
            jobs_data = []
            for job in jobs:
                jobs_data.append({
                    "job_id": job.get('job_no', 'N/A'),
                    "request_no": job.get('request_no', 'N/A'),
                    "date": job.get('date_of_request', ''),
                    "licence": job.get('licence_no', 'N/A'),
                    "jeweller": job.get('jeweller_name', 'N/A'),
                    "pcs": int(job.get('pcs', 0)),
                    "weight": float(job.get('weight', 0)),
                    "scrap_weight": float(job.get('scrp_cornet_weight', 0)),
                    "current_weight": float(job.get('cornet_weight', 0)),
                    "purity": job.get('purity', ''),
                    "bill_no": job.get('bill_no', '')
                })
            
            # Get first job details for license
            first_job = jobs[0]
            licence_no = first_job.get('licence_no', 'N/A')
            request_details = {
                "license_no": licence_no,
                "date": datetime.datetime.now().strftime("%d-%m-%Y")
            }
            
            # Export all to single Excel file
            try:
                self.log(f"\n  📝 Creating single export file with {len(jobs_data)} jobs...")
                filepath = exporter.export_to_excel(jobs_data, request_details)
                self.log(f"  ✅ Excel file created: {filepath}")
                
                # Copy file to Downloads folder for easy access
                download_path = None
                try:
                    downloads_dir = os.path.expanduser("~/Downloads")
                    if os.path.exists(downloads_dir):
                        download_file = os.path.basename(filepath)
                        download_path = os.path.join(downloads_dir, download_file)
                        shutil.copy2(filepath, download_path)
                        self.log(f"  📥 Copied to Downloads: {download_file}")
                except Exception as e:
                    self.log(f"  ℹ Downloads copy skipped: {e}")
                
                # Transaction saving disabled - will be added later
                
                self.log(f"\n📊 EXPORT SUMMARY: 1 Excel file created successfully")
                self.log(f"{'='*50}\n")
                
                # Show success message
                msg = f"✅ Exported successfully!\n\n"
                msg += f"📁 File: {os.path.basename(filepath)}\n"
                if download_path:
                    msg += f"📥 Location: Downloads folder\n"
                else:
                    msg += f"📂 Location: {os.path.abspath(filepath)}\n"
                msg += f"📊 Total Jobs: {len(jobs_data)}\n"
                
                self.export_btn.after(0, lambda: messagebox.showinfo("✅ Export Complete", msg))  # type: ignore
                
            except Exception as e:
                self.log(f"  ❌ Export error: {e}")
                traceback.print_exc()
                self.export_btn.after(0, lambda: messagebox.showerror("❌ Export Failed", str(e)))  # type: ignore
            
            self.export_btn.after(0, lambda: self.export_btn.config(state='normal'))  # type: ignore
            
        except Exception as e:
            self.log(f"❌ Export error: {e}")
            traceback.print_exc()
            self.export_btn.after(0, lambda: messagebox.showerror("❌ Export Error", str(e)))  # type: ignore
            self.export_btn.after(0, lambda: self.export_btn.config(state='normal'))  # type: ignore

    # _save_transaction removed - API only

    def _save_job(self, job):
        """Save job using API only (no MySQL fallback)"""
        try:
            if not self.save_api_url:
                self.log(f"  ❌ API URL not configured")
                return False

            pcs_value = int(job.get('pcs', 0) or 0)
            # Format job data for API
            api_job = {}
            for k, v in job.items():
                if isinstance(v, (datetime.date, datetime.datetime)):
                    api_job[k] = v.strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(v, list):
                    pass  # exclude lists from API payload (HUIDs not saved)
                elif isinstance(v, float):
                    # Round monetary amounts to 2 decimals
                    api_job[k] = round(v, 2)
                else:
                    api_job[k] = v

            api_job['pcs'] = pcs_value
            api_job['huid_pcs'] = pcs_value

            payload = {'action': 'save_job', 'firm_id': self.current_firm_id, 'job': api_job}
            resp = self.http_session.post(self.save_api_url, json=payload, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                if data.get('success'):
                    return True
                else:
                    self.log(f"  ⚠ API: {data.get('message')}")
            else:
                self.log(f"  ❌ API error: Status {resp.status_code}")
        except Exception as e:
            self.log(f"  ❌ Save API error: {e}")

        return False

    # _save_job_db removed - API only

    # _save_huids removed - Only saving job details, not HUIDs

    def _ensure_jeweller(self, job):
        lic = job.get('licence_no', '')
        if not lic or not self.manage_jeweller_url:
            return
        cache_key = (str(self.current_firm_id), str(lic))
        if cache_key in self._ensured_jewellers:
            return
        try:
            # Check
            payload = {'action': 'check', 'licence_no': lic, 'firm_id': self.current_firm_id}
            resp = self.http_session.post(self.manage_jeweller_url, json=payload, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('success') and data.get('exists'):
                    self._ensured_jewellers.add(cache_key)
                    return
            # Create
            payload2 = {
                'action': 'create',
                'firm_id': self.current_firm_id,
                'licence_no': lic,
                'name': job.get('jeweller_name', ''),
                'address': job.get('jeweller_address', ''),
                'city': job.get('jeweller_city', ''),
                'state': job.get('jeweller_state', ''),
            }
            self.http_session.post(self.manage_jeweller_url, json=payload2, timeout=5)
            self._ensured_jewellers.add(cache_key)
        except Exception as e:
            self.log(f"  ⚠ Jeweller ensure error: {e}")

    # ─────────────── stats display ─────────────────

    def _update_stats(self, stats):
        def _u():
            try:
                self.stats_labels['dates_scanned'].config(
                    text=f"📅 Dates Scanned: {stats['dates_scanned']}")
                self.stats_labels['jobs_found'].config(
                    text=f"🔍 Jobs Found: {stats['jobs_found']}")
                self.stats_labels['jobs_saved'].config(
                    text=f"💾 Jobs Saved: {stats.get('jobs_saved', 0)}")
                self.stats_labels['errors'].config(
                    text=f"❌ Errors: {stats['errors']}")
            except Exception:
                pass

        if self.stats_labels:
            self.preview_tree.after(0, _u)  # type: ignore
