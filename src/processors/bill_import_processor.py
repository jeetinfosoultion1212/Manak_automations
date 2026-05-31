"""
Bill Import Processor - Advanced dual-table matching system
Integrates scanned completed jobs with Excel bill data for intelligent matching and database saving
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import threading
import logging
from datetime import datetime
import traceback
import os
import requests

try:
    from config import BILL_IMPORT_API_URL
except ImportError:
    BILL_IMPORT_API_URL = ''

# Configure logging
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
os.makedirs(log_dir, exist_ok=True)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(os.path.join(log_dir, 'bill_import.log'))
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


class BillImportProcessor:
    """Handles import and matching of bills from Excel with scanned completed jobs"""
    
    def __init__(self, master, db_config, completed_jobs_scanner=None, license_manager=None):
        """
        Initialize Bill Import Processor
        
        Args:
            master: Tkinter parent widget
            db_config: Database connection configuration
            completed_jobs_scanner: Reference to CompletedJobsScanner instance (for accessing scanned_jobs)
            license_manager: License manager for firm_id
        """
        self.master = master
        self.db_config = db_config
        self.completed_jobs_scanner = completed_jobs_scanner
        self.license_manager = license_manager
        self.api_url = BILL_IMPORT_API_URL
        
        # Data buffers
        self.scanned_jobs = []  # Jobs from portal
        self.excel_bills = []   # Bills from Excel
        self.matched_pairs = [] # Matched job-bill pairs with confidence
        self.current_excel_file = None
        
        # UI elements
        self.scanned_jobs_tree = None
        self.excel_bills_tree = None
        self.matched_pairs_tree = None
        self.status_label = None
        self.confidence_var = None
        self.date_tolerance_var = None
        
        logger.info("BillImportProcessor initialized")

    def create_ui(self, parent_frame):
        """Create the Bill Import UI in the given frame"""
        
        # Control panel at top
        control_frame = ttk.LabelFrame(parent_frame, text="Controls", padding=10)
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(
            button_frame,
            text="Load Jobs",
            command=self.load_scanned_jobs
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Load Jobs (Excel)",
            command=self.load_jobs_from_excel
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Load Bills",
            command=self.load_excel_file
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Auto Match",
            command=self.auto_match
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Save",
            command=self.save_matched_pairs
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Export Bills",
            command=self.export_bills_to_excel
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Export Matched",
            command=self.export_matched_to_excel
        ).pack(side=tk.LEFT, padx=5)
        
        # Settings panel
        settings_frame = ttk.LabelFrame(control_frame, text="Match Settings", padding=5)
        settings_frame.pack(side=tk.RIGHT, fill=tk.X, padx=20)
        
        ttk.Label(settings_frame, text="Min Confidence:").pack(side=tk.LEFT, padx=5)
        self.confidence_var = tk.StringVar(value="85")
        ttk.Spinbox(
            settings_frame,
            from_=0,
            to=100,
            textvariable=self.confidence_var,
            width=5
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(settings_frame, text="Date Tolerance (days):").pack(side=tk.LEFT, padx=5)
        self.date_tolerance_var = tk.StringVar(value="1")
        ttk.Spinbox(
            settings_frame,
            from_=0,
            to=7,
            textvariable=self.date_tolerance_var,
            width=5
        ).pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status_label = ttk.Label(parent_frame, text="Ready", relief=tk.SUNKEN)
        self.status_label.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        
        # Main content area with TABS instead of three panes
        content_frame = ttk.Frame(parent_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create tabs
        self.notebook = ttk.Notebook(content_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # TAB 1: Scanned Jobs (with transaction details - matching Excel export)
        tab1 = ttk.Frame(self.notebook)
        self.notebook.add(tab1, text="📋 Portal Jobs")
        
        scanned_scroll = ttk.Scrollbar(tab1)
        scanned_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.scanned_jobs_tree = ttk.Treeview(
            tab1,
            columns=("Date", "Bill No", "License No", "Jeweller", "Request No", "PCS", "Weight", "Scrap Wt", "Current Wt", "Base Amt", "GST 18%", "Total Amt"),
            height=20,
            yscrollcommand=scanned_scroll.set
        )
        self.scanned_jobs_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scanned_scroll.config(command=self.scanned_jobs_tree.yview)
        
        self.scanned_jobs_tree.heading("#0", text="ID")
        self.scanned_jobs_tree.heading("Date", text="Date")
        self.scanned_jobs_tree.heading("Bill No", text="Bill No")
        self.scanned_jobs_tree.heading("License No", text="License No")
        self.scanned_jobs_tree.heading("Jeweller", text="Jeweller")
        self.scanned_jobs_tree.heading("Request No", text="Request No")
        self.scanned_jobs_tree.heading("PCS", text="PCS")
        self.scanned_jobs_tree.heading("Weight", text="Wt(g)")
        self.scanned_jobs_tree.heading("Scrap Wt", text="Scrap(g)")
        self.scanned_jobs_tree.heading("Current Wt", text="Current(g)")
        self.scanned_jobs_tree.heading("Base Amt", text="Base")
        self.scanned_jobs_tree.heading("GST 18%", text="GST")
        self.scanned_jobs_tree.heading("Total Amt", text="Total")
        
        self.scanned_jobs_tree.column("#0", width=35)
        self.scanned_jobs_tree.column("Date", width=70)
        self.scanned_jobs_tree.column("Bill No", width=70)
        self.scanned_jobs_tree.column("License No", width=75)
        self.scanned_jobs_tree.column("Jeweller", width=100)
        self.scanned_jobs_tree.column("Request No", width=80)
        self.scanned_jobs_tree.column("PCS", width=50)
        self.scanned_jobs_tree.column("Weight", width=65)
        self.scanned_jobs_tree.column("Scrap Wt", width=70)
        self.scanned_jobs_tree.column("Current Wt", width=75)
        self.scanned_jobs_tree.column("Base Amt", width=75)
        self.scanned_jobs_tree.column("GST 18%", width=65)
        self.scanned_jobs_tree.column("Total Amt", width=75)
        
        # TAB 2: Bills from Excel
        tab2 = ttk.Frame(self.notebook)
        self.notebook.add(tab2, text="📊 Bill Data")
        
        bills_scroll = ttk.Scrollbar(tab2)
        bills_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.excel_bills_tree = ttk.Treeview(
            tab2,
            columns=("Date", "Bill No", "Request No", "Licencee", "Licence", "GSTIN", "PCS", "Amount", "CGST", "SGST", "IGST", "Total", "H/M", "REJ"),
            height=20,
            yscrollcommand=bills_scroll.set
        )
        self.excel_bills_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        bills_scroll.config(command=self.excel_bills_tree.yview)
        
        self.excel_bills_tree.heading("#0", text="ID")
        self.excel_bills_tree.heading("Date", text="Date")
        self.excel_bills_tree.heading("Bill No", text="Bill No")
        self.excel_bills_tree.heading("Request No", text="Request ✏️")
        self.excel_bills_tree.heading("Licencee", text="Licencee")
        self.excel_bills_tree.heading("Licence", text="Licence")
        self.excel_bills_tree.heading("GSTIN", text="GSTIN")
        self.excel_bills_tree.heading("PCS", text="PCS")
        self.excel_bills_tree.heading("Amount", text="Amt")
        self.excel_bills_tree.heading("CGST", text="CGST")
        self.excel_bills_tree.heading("SGST", text="SGST")
        self.excel_bills_tree.heading("IGST", text="IGST")
        self.excel_bills_tree.heading("Total", text="Total")
        self.excel_bills_tree.heading("H/M", text="H/M")
        self.excel_bills_tree.heading("REJ", text="REJ")
        
        self.excel_bills_tree.column("#0", width=35)
        self.excel_bills_tree.column("Date", width=70)
        self.excel_bills_tree.column("Bill No", width=75)
        self.excel_bills_tree.column("Request No", width=85)
        self.excel_bills_tree.column("Licencee", width=100)
        self.excel_bills_tree.column("Licence", width=75)
        self.excel_bills_tree.column("GSTIN", width=85)
        self.excel_bills_tree.column("PCS", width=45)
        self.excel_bills_tree.column("Amount", width=65)
        self.excel_bills_tree.column("CGST", width=55)
        self.excel_bills_tree.column("SGST", width=55)
        self.excel_bills_tree.column("IGST", width=55)
        self.excel_bills_tree.column("Total", width=65)
        self.excel_bills_tree.column("H/M", width=45)
        self.excel_bills_tree.column("REJ", width=45)
        
        # Bind double-click to make cells editable
        self.excel_bills_tree.bind("<Double-1>", self._on_excel_bill_double_click)
        
        # Add button frame at bottom of tab2 for editing Request No
        bills_button_frame = ttk.Frame(tab2)
        bills_button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        
        ttk.Button(
            bills_button_frame,
            text="✏️ Edit Request No",
            command=self.edit_request_no_dialog
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(bills_button_frame, text="Tip: Select row & click to edit", foreground="gray", font=('Arial', 8)).pack(side=tk.LEFT, padx=15)
        
        # TAB 3: Matched Data
        tab3 = ttk.Frame(self.notebook)
        self.notebook.add(tab3, text="✅ Matched")
        
        matched_scroll = ttk.Scrollbar(tab3)
        matched_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.matched_pairs_tree = ttk.Treeview(
            tab3,
            columns=("Date", "Bill No", "Request No", "License No", "PCS", "Base Amt", "Total Amt", "Confidence"),
            height=20,
            yscrollcommand=matched_scroll.set
        )
        self.matched_pairs_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        matched_scroll.config(command=self.matched_pairs_tree.yview)
        
        self.matched_pairs_tree.heading("#0", text="ID")
        self.matched_pairs_tree.heading("Date", text="Date")
        self.matched_pairs_tree.heading("Bill No", text="Bill No")
        self.matched_pairs_tree.heading("Request No", text="Request No")
        self.matched_pairs_tree.heading("License No", text="License No")
        self.matched_pairs_tree.heading("PCS", text="PCS")
        self.matched_pairs_tree.heading("Base Amt", text="Base Amt")
        self.matched_pairs_tree.heading("Total Amt", text="Total Amt")
        self.matched_pairs_tree.heading("Confidence", text="Confidence %")
        
        self.matched_pairs_tree.column("#0", width=35)
        self.matched_pairs_tree.column("Date", width=75)
        self.matched_pairs_tree.column("Bill No", width=75)
        self.matched_pairs_tree.column("Request No", width=85)
        self.matched_pairs_tree.column("License No", width=75)
        self.matched_pairs_tree.column("PCS", width=50)
        self.matched_pairs_tree.column("Base Amt", width=75)
        self.matched_pairs_tree.column("Total Amt", width=75)
        self.matched_pairs_tree.column("Confidence", width=80)
    
    def load_scanned_jobs(self):
        """Load scanned jobs directly from CompletedJobsScanner and apply rate calculations"""
        try:
            self.update_status("Loading scanned jobs from portal...")
            
            # Get scanned jobs from the completed_jobs_scanner instance
            if self.completed_jobs_scanner is None:
                messagebox.showwarning("Warning", "No scanner reference available.\nPlease run Completed Jobs Scanner first.")
                self.update_status("Ready")
                return
            
            if not hasattr(self.completed_jobs_scanner, 'scanned_jobs') or not self.completed_jobs_scanner.scanned_jobs:
                messagebox.showwarning("Warning", "No scanned jobs available.\nPlease run Completed Jobs Scanner first.")
                self.update_status("Ready")
                return
            
            # Copy and process scanned jobs with rate calculations
            self.scanned_jobs = []
            for job in self.completed_jobs_scanner.scanned_jobs:
                try:
                    pcs = int(job.get('pcs', 0))
                    
                    # Apply rate calculation (same as JobCardExporter):
                    # - If PCS < 5: Base = 200 (fixed)
                    # - If PCS >= 5: Base = 45 × PCS
                    if pcs < 5:
                        base_amount = 200.0
                    else:
                        base_amount = 45.0 * pcs
                    
                    # Calculate GST amounts
                    gst_18 = base_amount * 0.18
                    cgst_9 = base_amount * 0.09
                    sgst_9 = base_amount * 0.09
                    igst_18 = 0.0  # IGST is 0 when using CGST+SGST (alternative tax structure)
                    # Total = Base Amount + GST(18%)
                    total_amount = base_amount + gst_18
                    
                    # Round total amount to nearest whole rupee
                    total_amount = round(total_amount, 0)
                    
                    # Create job dict with calculated amounts
                    processed_job = {
                        'date': job.get('date_of_request', datetime.now()),
                        'bill_no': job.get('bill_no', ''),
                        'licence_no': job.get('licence_no', ''),
                        'jeweller_name': job.get('jeweller_name', job.get('customer_name', '')),
                        'request_no': job.get('request_no', ''),
                        'pcs': pcs,
                        'weight': float(job.get('weight', 0)),
                        'scrp_cornet_weight': float(job.get('scrp_cornet_weight', 0)),
                        'cornet_weight': float(job.get('cornet_weight', 0)),
                        'base_amount': base_amount,
                        'gst_18': gst_18,
                        'cgst_9': cgst_9,
                        'sgst_9': sgst_9,
                        'igst_18': igst_18,
                        'total_amount': total_amount,
                    }
                    self.scanned_jobs.append(processed_job)
                    logger.debug(f"✅ Processed: {processed_job['request_no']} (PCS:{pcs}, Amount:{total_amount:.2f})")
                except Exception as e:
                    logger.warning(f"⚠️ Error processing job: {e}")
                    continue
            
            logger.info(f"✅ Loaded {len(self.scanned_jobs)} scanned jobs with rate calculations")
            
            if len(self.scanned_jobs) == 0:
                messagebox.showwarning("Warning", "No valid jobs found")
                self.update_status("Ready")
                return
            
            # Populate the tree with aggregated data
            self._populate_scanned_jobs_tree()
            self.update_status(f"✅ Loaded {len(self.scanned_jobs)} scanned jobs")
            
        except Exception as e:
            logger.error(f"Error loading scanned jobs: {e}\n{traceback.format_exc()}")
            messagebox.showerror("Error", f"Error loading scanned jobs:\n{str(e)}")
            self.update_status("Ready")

    def load_jobs_from_excel(self):
        """Load jobs from Excel file (with address data for jewellers table)"""
        try:
            self.update_status("Selecting Jobs Excel file...")
            
            file_path = filedialog.askopenfilename(
                title="Select Jobs Excel File",
                filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")],
                initialdir=os.path.expanduser("~")
            )
            
            if not file_path:
                self.update_status("Ready")
                return
            
            self.scanned_jobs = self._parse_jobs_excel_file(file_path)
            
            # Safety check for tree widget
            if self.scanned_jobs_tree is None:
                logger.warning("Scanned jobs tree not initialized")
                return
            
            # Populate the tree
            self._populate_scanned_jobs_tree()
            
            self.update_status(f"✅ Loaded {len(self.scanned_jobs)} jobs from Excel")
            logger.info(f"Loaded {len(self.scanned_jobs)} jobs from {file_path}")
            
        except Exception as e:
            logger.error(f"Error loading jobs Excel file: {e}\n{traceback.format_exc()}")
            messagebox.showerror("Error", f"Error loading jobs Excel file:\n{str(e)}")
            self.update_status("Ready")

    def _parse_jobs_excel_file(self, file_path):
        """Parse Excel file and extract job data with address information"""
        jobs = []
        try:
            file_ext = os.path.splitext(file_path)[1].lower()
            logger.info(f"Loading Jobs Excel file: {file_path}, Extension: {file_ext}")
            
            df = None
            try:
                if file_ext == '.xls':
                    logger.info("Using xlrd engine for .xls file")
                    df = pd.read_excel(file_path, engine='xlrd', dtype=str)
                else:
                    logger.info("Using openpyxl engine for .xlsx file")
                    df = pd.read_excel(file_path, engine='openpyxl', dtype=str)
            except ImportError as e:
                logger.error(f"ImportError: {e}")
                if file_ext == '.xls':
                    logger.info("xlrd not available, trying openpyxl for .xls")
                    df = pd.read_excel(file_path, engine='openpyxl', dtype=str)
                else:
                    logger.info("openpyxl not available, trying xlrd for .xlsx")
                    df = pd.read_excel(file_path, engine='xlrd', dtype=str)
            
            if df is None:
                raise ValueError("Could not read Excel file with any available engine")
            
            logger.info(f"Successfully read Excel file. Shape: {df.shape}")
            df.columns = df.columns.str.strip().str.lower()
            logger.info(f"Normalized columns: {df.columns.tolist()}")
            
            for idx, row in df.iterrows():
                try:
                    def get_col(series, *names):
                        """Try to get column by multiple possible names"""
                        for name in names:
                            if name in series.index:
                                val = series[name]
                                if pd.notna(val) and str(val).strip():
                                    return str(val).strip()
                        
                        for name in names:
                            for col_name in series.index:
                                col_normalized = ' '.join(col_name.split())
                                name_normalized = ' '.join(name.split())
                                if (name_normalized in col_normalized or col_normalized in name_normalized):
                                    val = series[col_name]
                                    if pd.notna(val) and str(val).strip():
                                        return str(val).strip()
                        return None
                    
                    # Extract job fields - ADDRESS field is critical for jewellers table
                    date_val = get_col(row, 'date', 'job date', 'request date', 'date of request')
                    job_no_val = get_col(row, 'job no', 'job_no', 'job id', 'jobno')
                    request_no_val = get_col(row, 'request no', 'requestno', 'request_no', 'request number')
                    bill_no_val = get_col(row, 'bill no', 'billno', 'bill_no')
                    licence_val = get_col(row, 'licence', 'licence no', 'license', 'license no', 'licence_no')
                    jeweller_val = get_col(row, 'jeweller', 'jeweller name', 'customer name', 'jeweller name')
                    address_val = get_col(row, 'address', 'jeweller address', 'customer address', 'addr', 'location')
                    pcs_val = get_col(row, 'pcs', 'pieces', 'qty', 'quantity', 'total pcs')
                    weight_val = get_col(row, 'weight', 'weight(g)', 'wt', 'total weight')
                    scrap_val = get_col(row, 'scrap weight', 'scrap_weight', 'scrap', 'scrp_cornet_weight')
                    current_val = get_col(row, 'current weight', 'current_weight', 'cornet weight', 'cornet_weight')
                    purity_val = get_col(row, 'purity', 'purity %')
                    
                    if not any([job_no_val, request_no_val, jeweller_val]):
                        continue
                    
                    try:
                        date_obj = pd.to_datetime(date_val).to_pydatetime() if date_val else datetime.now()
                    except Exception as date_err:
                        logger.warning(f"Could not parse date '{date_val}': {date_err}")
                        date_obj = datetime.now()
                    
                    try:
                        pcs_num = int(float(pcs_val)) if pcs_val else 0
                    except:
                        pcs_num = 0
                    
                    # Calculate amounts same as JobCardExporter
                    if pcs_num < 5:
                        base_amount = 200.0
                    else:
                        base_amount = 45.0 * pcs_num
                    
                    gst_18 = base_amount * 0.18
                    cgst_9 = base_amount * 0.09
                    sgst_9 = base_amount * 0.09
                    igst_18 = 0.0
                    total_amount = round(base_amount + gst_18, 0)
                    
                    try:
                        weight_num = float(weight_val) if weight_val else 0.0
                    except:
                        weight_num = 0.0
                    
                    try:
                        scrap_num = float(scrap_val) if scrap_val else 0.0
                    except:
                        scrap_num = 0.0
                    
                    try:
                        current_num = float(current_val) if current_val else 0.0
                    except:
                        current_num = 0.0
                    
                    job = {
                        'index': idx,
                        'date_of_request': date_obj,
                        'job_no': job_no_val or '',
                        'request_no': request_no_val or '',
                        'bill_no': bill_no_val or '',
                        'licence_no': licence_val or '',
                        'jeweller_name': jeweller_val or '',
                        'address': address_val or '',  # CRITICAL: Store address for both address and Address1
                        'pcs': pcs_num,
                        'weight': weight_num,
                        'scrp_cornet_weight': scrap_num,
                        'cornet_weight': current_num,
                        'purity': purity_val or '',
                        'base_amount': base_amount,
                        'gst_18': gst_18,
                        'cgst_9': cgst_9,
                        'sgst_9': sgst_9,
                        'igst_18': igst_18,
                        'total_amount': total_amount,
                    }
                    jobs.append(job)
                    logger.debug(f"Parsed job: {job['job_no']}, Jeweller: {job['jeweller_name']}, Address: {job['address']}")
                    
                except Exception as e:
                    logger.warning(f"Error parsing row {idx}: {e}")
                    continue
            
            logger.info(f"Successfully parsed {len(jobs)} jobs from Excel file")
            return jobs
            
        except Exception as e:
            logger.error(f"Error parsing jobs Excel file: {e}\n{traceback.format_exc()}")
            raise
    
    def _populate_scanned_jobs_tree(self):
        """Populate tree view with request-wise aggregated scanned jobs"""
        try:
            # Safety checks
            if self.scanned_jobs_tree is None:
                logger.warning("Scanned jobs tree not initialized")
                return
            
            if not self.scanned_jobs or len(self.scanned_jobs) == 0:
                logger.warning("No scanned jobs to display")
                return
            
            # Clear existing items
            for item in self.scanned_jobs_tree.get_children():
                self.scanned_jobs_tree.delete(item)
            
            # GROUP BY REQUEST NO and aggregate totals
            request_groups = {}
            for job in self.scanned_jobs:
                if job is None:
                    continue
                    
                req_no = job.get('request_no', 'Unknown')
                
                if req_no not in request_groups:
                    # Safe date parsing
                    date_val = job.get('date', datetime.now())
                    if isinstance(date_val, str):
                        try:
                            date_val = datetime.strptime(date_val, '%Y-%m-%d')
                        except:
                            date_val = datetime.now()
                    
                    request_groups[req_no] = {
                        'date': date_val,
                        'bill_no': job.get('bill_no', ''),
                        'licence_no': job.get('licence_no', ''),
                        'jeweller_name': job.get('jeweller_name', ''),
                        'request_no': req_no,
                        'pcs': 0,
                        'weight': 0.0,
                        'scrap_weight': 0.0,
                        'current_weight': 0.0,
                        'base_amount': 0.0,
                        'gst_18': 0.0,
                        'cgst_9': 0.0,
                        'sgst_9': 0.0,
                        'igst_18': 0.0,
                        'total_amount': 0.0,
                        'jobs': []
                    }
                
                # Accumulate totals from job data with safe conversion
                try:
                    pcs_val = job.get('pcs', 0)
                    request_groups[req_no]['pcs'] += int(pcs_val) if pcs_val else 0
                    
                    weight_val = job.get('weight', 0)
                    request_groups[req_no]['weight'] += float(weight_val) if weight_val else 0.0
                    
                    scrap_val = job.get('scrp_cornet_weight', 0)
                    request_groups[req_no]['scrap_weight'] += float(scrap_val) if scrap_val else 0.0
                    
                    current_val = job.get('cornet_weight', 0)
                    request_groups[req_no]['current_weight'] += float(current_val) if current_val else 0.0
                    
                    base_val = job.get('base_amount', 0)
                    request_groups[req_no]['base_amount'] += float(base_val) if base_val else 0.0
                    
                    gst_val = job.get('gst_18', 0)
                    request_groups[req_no]['gst_18'] += float(gst_val) if gst_val else 0.0
                    
                    cgst_val = job.get('cgst_9', 0)
                    request_groups[req_no]['cgst_9'] += float(cgst_val) if cgst_val else 0.0
                    
                    sgst_val = job.get('sgst_9', 0)
                    request_groups[req_no]['sgst_9'] += float(sgst_val) if sgst_val else 0.0
                    
                    igst_val = job.get('igst_18', 0)
                    request_groups[req_no]['igst_18'] += float(igst_val) if igst_val else 0.0
                    
                    total_val = job.get('total_amount', 0)
                    request_groups[req_no]['total_amount'] += float(total_val) if total_val else 0.0
                    
                    request_groups[req_no]['jobs'].append(job)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error aggregating job {req_no}: {e}")
                    continue
            
            # Populate tree with request-wise aggregated data
            for idx, (req_no, req_data) in enumerate(request_groups.items()):
                try:
                    date_obj = req_data.get('date', datetime.now())
                    if isinstance(date_obj, datetime):
                        date_str = date_obj.strftime('%d-%m-%Y')
                    else:
                        date_str = str(date_obj)
                    
                    # Round total amount to nearest whole rupee
                    total_amount_rounded = round(req_data.get('total_amount', 0), 0)
                    
                    # Insert row with aggregated amounts
                    self.scanned_jobs_tree.insert("", tk.END, f"scanned_{idx}", text=str(idx+1),
                        values=(
                            date_str,
                            req_data.get('bill_no', ''),
                            req_data.get('licence_no', ''),
                            req_data.get('jeweller_name', ''),
                            req_data.get('request_no', ''),
                            str(req_data.get('pcs', 0)),
                            f"{req_data.get('weight', 0):.2f}",
                            f"{req_data.get('scrap_weight', 0):.2f}",
                            f"{req_data.get('current_weight', 0):.2f}",
                            f"{req_data.get('base_amount', 0):.2f}",
                            f"{req_data.get('gst_18', 0):.2f}",
                            f"{total_amount_rounded:.0f}"
                        ))
                except Exception as e:
                    logger.error(f"Error inserting aggregated request {idx}: {e}")
        
        except Exception as e:
            logger.error(f"Error populating scanned jobs tree: {e}\n{traceback.format_exc()}")
    
    def load_excel_file(self):
        """Load bills from Excel file"""
        try:
            self.update_status("Selecting Excel file...")
            
            file_path = filedialog.askopenfilename(
                title="Select Bill Excel File",
                filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")],
                initialdir=os.path.expanduser("~")
            )
            
            if not file_path:
                self.update_status("Ready")
                return
            
            self.current_excel_file = file_path
            self.excel_bills = self._parse_excel_file(file_path)
            
            # Safety check for tree widget
            if self.excel_bills_tree is None:
                logger.warning("Excel bills tree not initialized")
                return
            
            # Use the new populate method
            self._populate_excel_bills_tree()
            
            self.update_status(f"Loaded {len(self.excel_bills)} bills from Excel")
            logger.info(f"Loaded {len(self.excel_bills)} bills from {file_path}")
            
        except Exception as e:
            logger.error(f"Error loading Excel file: {e}\n{traceback.format_exc()}")
            messagebox.showerror("Error", f"Error loading Excel file:\n{str(e)}")
            self.update_status("Ready")
            self.update_status("Ready")
    
    def _parse_excel_file(self, file_path):
        """Parse Excel file and extract bill data"""
        bills = []
        try:
            # Determine file extension and use appropriate engine
            file_ext = os.path.splitext(file_path)[1].lower()
            
            logger.info(f"Loading Excel file: {file_path}, Extension: {file_ext}")
            
            df = None
            
            # Try to read Excel file with appropriate engine
            try:
                if file_ext == '.xls':
                    logger.info("Using xlrd engine for .xls file")
                    df = pd.read_excel(file_path, engine='xlrd', dtype=str)
                else:
                    logger.info("Using openpyxl engine for .xlsx file")
                    df = pd.read_excel(file_path, engine='openpyxl', dtype=str)
            except ImportError as e:
                logger.error(f"ImportError: {e}")
                # Try alternative engine if primary fails
                if file_ext == '.xls':
                    logger.info("xlrd not available, trying openpyxl for .xls")
                    df = pd.read_excel(file_path, engine='openpyxl', dtype=str)
                else:
                    logger.info("openpyxl not available, trying xlrd for .xlsx")
                    df = pd.read_excel(file_path, engine='xlrd', dtype=str)
            
            if df is None:
                raise ValueError("Could not read Excel file with any available engine")
            
            logger.info(f"Successfully read Excel file. Shape: {df.shape}")
            logger.info(f"Original columns: {df.columns.tolist()}")
            
            # Normalize column names (lowercase, strip spaces)
            df.columns = df.columns.str.strip().str.lower()
            logger.info(f"Normalized columns: {df.columns.tolist()}")
            
            # Log first few rows to debug
            logger.debug(f"First row data:\n{df.iloc[0].to_dict() if len(df) > 0 else 'No data'}")
            
            # Expected columns: date, bill no, request no, licence no, pcs, invoice, amount, plus GST details
            for idx, row in df.iterrows():
                try:
                    # Safe column access for pandas Series
                    def get_col(series, *names):
                        """Try to get column by multiple possible names with flexible matching"""
                        # First, try exact matches
                        for name in names:
                            if name in series.index:
                                val = series[name]
                                if pd.notna(val) and str(val).strip():
                                    return str(val).strip()
                        
                        # If no exact match, try fuzzy matching (contains)
                        for name in names:
                            for col_name in series.index:
                                # Normalize both for comparison
                                col_normalized = ' '.join(col_name.split())  # Remove extra spaces
                                name_normalized = ' '.join(name.split())
                                
                                # Check if either contains the other or they match substantially
                                if (name_normalized in col_normalized or col_normalized in name_normalized):
                                    val = series[col_name]
                                    if pd.notna(val) and str(val).strip():
                                        return str(val).strip()
                        
                        return None
                    
                    date_val = get_col(row, 'date', 'bill date', 'billdate', 'invoice date')
                    bill_no_val = get_col(row, 'bill no', 'billno', 'bill_no', 'bill number', 'bill')
                    request_no_val = get_col(row, 'request no', 'requestno', 'request_no', 'request number', 'request')
                    licence_val = get_col(row, 'licence', 'licence no', 'license', 'license no', 'licence_no', 'licence number')
                    licencee_name_val = get_col(row, 'name of licencee', 'name of licensee', 'licencee', 'licensee', 'jeweller', 'jeweller name', 'licencee name', 'licensee name')
                    gstin_val = get_col(row, 'gstin no', 'gstin', 'gstin number', 'gst identification number')
                    pcs_val = get_col(row, 'pcs', 'pieces', 'qty', 'quantity')
                    invoice_val = get_col(row, 'invoice', 'invoice no', 'invoiceno', 'invoice_no')
                    amount_val = get_col(row, 'amount', 'total amount', 'bill amount', 'invoice amount', 'total amt', 'total')
                    
                    # Extract GST columns
                    cgst_val = get_col(row, 'cgst', 'cgst amount', 'cgst %')
                    sgst_val = get_col(row, 'sgst', 'sgst amount', 'sgst %')
                    igst_val = get_col(row, 'igst', 'igst amount', 'igst %')
                    
                    # Extract other details
                    h_m_val = get_col(row, 'h/m', 'hm', 'h m')
                    rej_val = get_col(row, 'rej', 'rejection')
                    
                    # Log extracted values for first row to debug
                    if idx == 0:
                        logger.debug(f"🔍 DEBUG: First row extractions:")
                        logger.debug(f"  - licencee_name_val: '{licencee_name_val}'")
                        logger.debug(f"  - gstin_val: '{gstin_val}'")
                        logger.debug(f"  - cgst_val: '{cgst_val}'")
                        logger.debug(f"  - sgst_val: '{sgst_val}'")
                        logger.debug(f"  - igst_val: '{igst_val}'")
                    
                    # Skip empty rows
                    if not any([bill_no_val, amount_val]):
                        continue
                    
                    # Convert to appropriate types
                    try:
                        date_obj = pd.to_datetime(date_val).to_pydatetime() if date_val else None
                    except Exception as date_err:
                        logger.warning(f"Could not parse date '{date_val}': {date_err}")
                        date_obj = None
                    
                    try:
                        pcs_num = int(float(pcs_val)) if pcs_val else 0
                    except:
                        pcs_num = 0
                    
                    try:
                        amount_num = float(amount_val) if amount_val else 0.0
                    except:
                        amount_num = 0.0
                    
                    try:
                        cgst_num = float(cgst_val) if cgst_val else 0.0
                    except:
                        cgst_num = 0.0
                    
                    try:
                        sgst_num = float(sgst_val) if sgst_val else 0.0
                    except:
                        sgst_num = 0.0
                    
                    try:
                        igst_num = float(igst_val) if igst_val else 0.0
                    except:
                        igst_num = 0.0
                    
                    bill = {
                        'index': idx,
                        'date': date_obj,
                        'bill_no': bill_no_val or '',
                        'request_no': request_no_val or '',
                        'licence_no': licence_val or '',
                        'licencee_name': licencee_name_val or '',
                        'gstin_no': gstin_val or '',
                        'pcs': pcs_num,
                        'invoice_no': invoice_val or '',
                        'amount': amount_num,
                        'total_amount': amount_num,
                        'cgst': cgst_num,
                        'sgst': sgst_num,
                        'igst': igst_num,
                        'h_m': h_m_val or '',
                        'rej': rej_val or '',
                    }
                    bills.append(bill)
                    logger.debug(f"Parsed bill row {idx}: Bill={bill['bill_no']}, Amount={bill['amount']}, CGST={bill['cgst']}, SGST={bill['sgst']}, IGST={bill['igst']}")
                    
                except Exception as e:
                    logger.warning(f"Error parsing row {idx}: {e}")
                    continue
            
            logger.info(f"Successfully parsed {len(bills)} bills from Excel file")
            if len(bills) == 0:
                logger.warning("No valid bill records found in Excel file")
            
            return bills
            
        except Exception as e:
            logger.error(f"Error parsing Excel file {file_path}: {e}\n{traceback.format_exc()}")
            raise
    
    def auto_match(self):
        """Automatically match scanned jobs with bills"""
        try:
            if not self.scanned_jobs:
                messagebox.showwarning("Warning", "No scanned jobs loaded")
                return
            
            if not self.excel_bills:
                messagebox.showwarning("Warning", "No bills loaded from Excel")
                return
            
            # Safety check for tree widget
            if self.matched_pairs_tree is None:
                logger.warning("Matched pairs tree not initialized")
                return
            
            # Safety check for variables
            if self.confidence_var is None or self.date_tolerance_var is None:
                logger.warning("UI variables not initialized")
                messagebox.showerror("Error", "UI components not properly initialized")
                return
            
            self.update_status("Auto-matching jobs and bills...")
            
            min_confidence = int(self.confidence_var.get())
            date_tolerance = int(self.date_tolerance_var.get())
            
            self.matched_pairs = []
            
            for job_idx, job in enumerate(self.scanned_jobs):
                best_match = None
                best_confidence = 0
                
                for bill_idx, bill in enumerate(self.excel_bills):
                    confidence = self._calculate_match_confidence(job, bill, date_tolerance)
                    
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = (job_idx, bill_idx, confidence)
                
                # Add if confidence meets threshold and not already matched
                if best_match and best_confidence >= min_confidence:
                    # Check if bill already matched with different job
                    already_matched = any(pair[1] == best_match[1] for pair in self.matched_pairs)
                    if not already_matched:
                        self.matched_pairs.append(best_match)
            
            # Clear matched pairs tree and populate with matches
            for item in self.matched_pairs_tree.get_children():
                self.matched_pairs_tree.delete(item)
            
            for pair_idx, (job_idx, bill_idx, confidence) in enumerate(self.matched_pairs):
                try:
                    job = self.scanned_jobs[job_idx]
                    bill = self.excel_bills[bill_idx]
                    
                    # 🔥 NEW: Automatically populate request_no in the bill when matched
                    request_no = job.get('request_no', '')
                    if request_no and not bill.get('request_no'):
                        bill['request_no'] = request_no
                        logger.info(f"✅ Populated Request No: {request_no} for Bill {bill.get('bill_no')}")
                    
                    # Format date
                    date_obj = job.get('date')
                    if isinstance(date_obj, datetime):
                        date_str = date_obj.strftime('%d-%m-%Y')
                    else:
                        date_str = str(date_obj) if date_obj else ''
                    
                    # Insert all 8 columns for matched pairs
                    self.matched_pairs_tree.insert("", tk.END, f"pair_{pair_idx}", text=str(pair_idx+1),
                        values=(
                            date_str,
                            bill.get('bill_no', ''),
                            job.get('request_no', ''),
                            job.get('licence_no', ''),
                            str(job.get('pcs', '')),
                            f"{job.get('base_amount', 0):.2f}",
                            f"{round(job.get('total_amount', 0), 0):.0f}",
                            f"{confidence:.1f}%"
                        ))
                except Exception as e:
                    logger.error(f"Error displaying match pair {pair_idx}: {e}")
            
            # 🔥 NEW: Refresh the Bills from Excel tree to show updated request_no values
            self._populate_excel_bills_tree()
            
            self.update_status(f"Found {len(self.matched_pairs)} matches")
            logger.info(f"Auto-matched: Found {len(self.matched_pairs)} pairs")
            
        except Exception as e:
            logger.error(f"Error during auto-match: {e}\n{traceback.format_exc()}")
            messagebox.showerror("Error", f"Error during auto-match:\n{str(e)}")
            self.update_status("Ready")
    
    def _calculate_match_confidence(self, job, bill, date_tolerance):
        """Calculate confidence score for a job-bill pair (0-100)"""
        confidence = 0
        
        try:
            # Licence match (40 points) - highest weight
            if str(job.get('licence_no', '')).strip() == str(bill.get('licence_no', '')).strip():
                confidence += 40
            
            # PCS exact match (35 points)
            if job.get('pcs', 0) == bill.get('pcs', 0):
                confidence += 35
            
            # PCS close match (20 points for within 1 unit)
            elif abs(job.get('pcs', 0) - bill.get('pcs', 0)) <= 1:
                confidence += 20
            
            # Date match (25 points) - with tolerance
            job_date = job.get('date')
            bill_date = bill.get('date')
            
            if job_date and bill_date:
                # Ensure both dates are datetime objects
                if isinstance(job_date, str):
                    try:
                        job_date = pd.to_datetime(job_date).to_pydatetime()
                    except:
                        job_date = None
                
                if isinstance(bill_date, str):
                    try:
                        bill_date = pd.to_datetime(bill_date).to_pydatetime()
                    except:
                        bill_date = None
                
                # Now safely access .date() method
                if job_date and bill_date and hasattr(job_date, 'date') and hasattr(bill_date, 'date'):
                    try:
                        date_diff = abs((job_date.date() - bill_date.date()).days)
                        if date_diff == 0:
                            confidence += 25
                        elif date_diff <= date_tolerance:
                            confidence += 10
                    except Exception as e:
                        logger.warning(f"Error comparing dates: {e}")
            
            return min(confidence, 100)
        
        except Exception as e:
            logger.error(f"Error calculating confidence for job-bill pair: {e}")
            return 0
    
    def _populate_excel_bills_tree(self):
        """Refresh the Bills from Excel tree view with current data"""
        try:
            if self.excel_bills_tree is None or not self.excel_bills:
                return
            
            # Clear existing items
            for item in self.excel_bills_tree.get_children():
                self.excel_bills_tree.delete(item)
            
            # Populate tree with bills
            for idx, bill in enumerate(self.excel_bills):
                try:
                    date_obj = bill.get('date')
                    if isinstance(date_obj, datetime):
                        date_str = date_obj.strftime('%d-%m-%Y')
                    else:
                        date_str = str(date_obj) if date_obj else ''
                    
                    self.excel_bills_tree.insert("", tk.END, f"bill_{idx}", text=str(idx+1),
                        values=(
                            date_str,
                            bill.get('bill_no', ''),
                            bill.get('request_no', ''),  # Updated request_no
                            bill.get('licencee_name', ''),
                            bill.get('licence_no', ''),
                            bill.get('gstin_no', ''),
                            str(bill.get('pcs', '')),
                            f"{bill.get('amount', 0):.2f}",
                            f"{bill.get('cgst', 0):.2f}",
                            f"{bill.get('sgst', 0):.2f}",
                            f"{bill.get('igst', 0):.2f}",
                            f"{bill.get('total_amount', 0):.2f}",
                            bill.get('h_m', ''),
                            bill.get('rej', '')
                        ))
                except Exception as e:
                    logger.error(f"Error inserting bill {idx}: {e}")
        except Exception as e:
            logger.error(f"Error refreshing bills tree: {e}")
    
    def _on_excel_bill_double_click(self, event):
        """Handle double-click to edit Request No cell"""
        try:
            # Safety check: ensure tree widget exists
            if not self.excel_bills_tree:
                logger.warning("Excel bills tree widget not initialized")
                return
            
            # Get selected item
            selection = self.excel_bills_tree.selection()
            if not selection:
                return
            
            item = selection[0]
            
            # Identify which column was clicked
            col = self.excel_bills_tree.identify_column(event.x)
            if not col:
                return
            
            col_num = int(col[1:]) - 1  # Convert to 0-indexed
            
            # Only allow editing of Request No column (index 2)
            if col_num != 2:
                return
            
            # Get current value
            values = self.excel_bills_tree.item(item, 'values')
            current_value = values[col_num] if col_num < len(values) else ''
            
            # Extract bill index safely
            try:
                bill_idx = int(item.split('_')[1])
            except (ValueError, IndexError):
                logger.error(f"Invalid item ID format: {item}")
                return
            
            if bill_idx >= len(self.excel_bills):
                logger.error(f"Bill index {bill_idx} out of range")
                return
            
            # Create edit popup
            edit_window = tk.Toplevel(self.master)
            edit_window.title(f"Edit Request No - Bill {self.excel_bills[bill_idx].get('bill_no', '')}")
            edit_window.geometry("300x150")
            
            ttk.Label(edit_window, text="Request No:").pack(pady=10)
            entry = ttk.Entry(edit_window, width=30)
            entry.insert(0, current_value)
            entry.pack(pady=5)
            entry.focus()
            
            # Store references in a dict to ensure proper closure
            context = {
                'entry': entry,
                'values': list(values),
                'col_num': col_num,
                'item': item,
                'bill_idx': bill_idx,
                'edit_window': edit_window
            }
            
            def save_edit(ctx=context):
                """Save edited request no value"""
                try:
                    new_value = ctx['entry'].get().strip()
                    
                    # Safety checks
                    if ctx['bill_idx'] >= len(self.excel_bills):
                        logger.error(f"Bill index {ctx['bill_idx']} out of range")
                        return
                    
                    if not self.excel_bills_tree:
                        logger.error("Excel bills tree is None")
                        return
                    
                    # Update the data in memory
                    self.excel_bills[ctx['bill_idx']]['request_no'] = new_value
                    
                    # Update the tree display
                    values_list = ctx['values'].copy()
                    values_list[ctx['col_num']] = new_value
                    
                    self.excel_bills_tree.item(ctx['item'], values=tuple(values_list))
                    logger.info(f"✏️ Updated Request No: {new_value} for Bill {ctx['bill_idx']}")
                    
                    ctx['edit_window'].destroy()
                except Exception as e:
                    logger.error(f"Error in save_edit: {e}", exc_info=True)
                    messagebox.showerror("Error", f"Failed to save: {str(e)}")
            
            def on_enter(event):
                """Handle Enter key press"""
                save_edit()
            
            ttk.Button(edit_window, text="Save", command=save_edit).pack(pady=10)
            entry.bind('<Return>', on_enter)
            
        except Exception as e:
            logger.error(f"Error in excel bill double-click handler: {e}", exc_info=True)
    
    def save_matched_pairs(self):
        """Save matched pairs to database"""
        try:
            if not self.matched_pairs:
                messagebox.showwarning("Warning", "No matched pairs to save")
                return
            
            if messagebox.askyesno("Confirm", f"Save {len(self.matched_pairs)} matched pairs to database?"):
                self.update_status("Saving matched pairs...")
                
                # Run save in thread to avoid blocking UI
                thread = threading.Thread(target=self._save_to_database)
                thread.daemon = True
                thread.start()
        
        except Exception as e:
            logger.error(f"Error in save_matched_pairs: {e}\n{traceback.format_exc()}")
            messagebox.showerror("Error", f"Error saving:\n{str(e)}")
            self.update_status("Ready")
    
    def _save_to_database(self):
        """Background thread function to save matched pairs using API"""
        try:
            firm_id = self.license_manager.firm_id if self.license_manager else 1
            
            saved_count = 0
            error_count = 0
            
            for job_idx, bill_idx, confidence in self.matched_pairs:
                try:
                    job = self.scanned_jobs[job_idx]
                    bill = self.excel_bills[bill_idx]
                    
                    # Prepare API payload with ALL required fields from bill_Save_method.md
                    bill_date = bill.get('date', datetime.now())
                    if isinstance(bill_date, datetime):
                        bill_date_str = bill_date.strftime('%Y-%m-%d')
                    else:
                        bill_date_str = str(bill_date)
                    
                    # Calculate GST rate (18% for IGST state)
                    gst_rate = 18.00
                    
                    # Determine payment status based on received_amount
                    received_amount = bill.get('received_amount', 0)
                    total_amount = bill.get('total_amount', 0)
                    if received_amount <= 0:
                        payment_status = 'Unpaid'
                    elif received_amount >= total_amount:
                        payment_status = 'paid'
                    else:
                        payment_status = 'partial'
                    
                    payload = {
                        'action': 'save_matched_bill',
                        'firm_id': firm_id,
                        'job_id': job.get('job_id', job.get('id')),
                        'job_no': job.get('job_no', ''),
                        'request_no': job.get('request_no', ''),
                        'licence_no': job.get('licence_no', '') or bill.get('licence_no', ''),
                        'bill_number': bill.get('invoice_no', ''),
                        'bill_date': bill_date_str,
                        'invoice_number': bill.get('invoice_no', ''),
                        'pcs': bill.get('pcs', 0),
                        'amount': bill.get('amount', 0),
                        'base_amount': bill.get('amount', 0),
                        'cgst': bill.get('cgst', 0),
                        'sgst': bill.get('sgst', 0),
                        'igst': bill.get('igst', 0),
                        'gst_amount': bill.get('cgst', 0) + bill.get('sgst', 0) + bill.get('igst', 0),
                        'gst_rate': gst_rate,
                        'total_amount': bill.get('total_amount', 0),
                        'payment_status': payment_status,
                        'payment_mode': bill.get('payment_mode', 'Bank'),
                        'paid_amount': received_amount,
                        'received_amount': received_amount,
                        'payment_date': bill_date_str if received_amount > 0 else None,
                        'scrap_weight': job.get('scrap_weight', 0),
                        'button_weight': job.get('button_weight', 0),
                        'cornent_weight': job.get('cornent_weight', 0),
                        'reminents_weight': job.get('reminents_weight', 0),
                        'address': job.get('address', ''),  # Store address from jobs
                        'Address1': job.get('address', ''),  # Also store in Address1 column (same data)
                        'narration': f"Bill Import - {bill.get('invoice_no', '')} matched with Job {job.get('job_no', '')}",
                        'is_jobs_wise': 1,
                        'billing_type': 'full',
                        'excluded_job_ids': '',
                        'round_off': 0,
                        'confidence': confidence
                    }
                    
                    # Send to API
                    if self.api_url:
                        resp = requests.post(self.api_url, json=payload, timeout=10)
                        if resp.status_code == 200:
                            data = resp.json()
                            if data.get('success'):
                                saved_count += 1
                                logger.info(f"Saved matched pair {job_idx}-{bill_idx} via API")
                            else:
                                logger.error(f"API error for pair {job_idx}-{bill_idx}: {data.get('message')}")
                                error_count += 1
                        else:
                            logger.error(f"API error for pair {job_idx}-{bill_idx}: Status {resp.status_code}")
                            error_count += 1
                    else:
                        logger.warning(f"API URL not configured, skipping save for pair {job_idx}-{bill_idx}")
                        error_count += 1
                
                except Exception as e:
                    logger.error(f"Error saving pair {job_idx}-{bill_idx}: {e}")
                    error_count += 1
            
            self.master.after(0, self._show_save_result, saved_count, error_count)
        
        except Exception as e:
            logger.error(f"Error in _save_to_database: {e}\n{traceback.format_exc()}")
            self.master.after(0, lambda: messagebox.showerror("Error", f"Save error:\n{str(e)}"))
            self.master.after(0, lambda: self.update_status("Ready"))
    
    def _show_save_result(self, saved_count, error_count):
        """Show save result message"""
        self.update_status(f"Saved {saved_count} pairs" + (f" ({error_count} errors)" if error_count > 0 else ""))
        messagebox.showinfo("Save Complete", 
            f"Saved: {saved_count} pairs\nErrors: {error_count}")
        logger.info(f"Saved {saved_count} pairs to database ({error_count} errors)")
    
    def export_bills_to_excel(self):
        """Export Bills from Excel table to a new Excel file"""
        try:
            if not self.excel_bills:
                messagebox.showwarning("Warning", "No bills to export")
                return
            
            # Ask user for save location
            file_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("CSV files", "*.csv"), ("All files", "*.*")],
                initialfile=f"Bills_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            )
            
            if not file_path:
                return
            
            self.update_status("Exporting bills to Excel...")
            
            # Create DataFrame from excel_bills
            export_data = []
            for bill in self.excel_bills:
                export_data.append({
                    'Date': bill.get('date', ''),
                    'Bill No': bill.get('bill_no', ''),
                    'Request No': bill.get('request_no', ''),
                    'Licencee Name': bill.get('licencee_name', ''),
                    'Licence No': bill.get('licence_no', ''),
                    'GSTIN NO': bill.get('gstin_no', ''),
                    'PCS': bill.get('pcs', 0),
                    'Amount': bill.get('amount', 0),
                    'CGST': bill.get('cgst', 0),
                    'SGST': bill.get('sgst', 0),
                    'IGST': bill.get('igst', 0),
                    'Total Amt': bill.get('total_amount', 0),
                    'H/M': bill.get('h_m', ''),
                    'REJ': bill.get('rej', '')
                })
            
            df = pd.DataFrame(export_data)
            
            # Export based on file extension
            if file_path.endswith('.csv'):
                df.to_csv(file_path, index=False, encoding='utf-8')
            else:
                df.to_excel(file_path, index=False, sheet_name='Bills')
            
            logger.info(f"✅ Exported {len(self.excel_bills)} bills to {file_path}")
            self.update_status(f"✅ Exported {len(self.excel_bills)} bills")
            messagebox.showinfo("Success", f"Exported {len(self.excel_bills)} bills to:\n{file_path}")
            
        except Exception as e:
            logger.error(f"Error exporting bills: {e}\n{traceback.format_exc()}")
            messagebox.showerror("Error", f"Export failed:\n{str(e)}")
            self.update_status("Ready")
    
    def edit_request_no_dialog(self):
        """Open dialog to edit Request No for selected bill"""
        try:
            # Validate tree widget exists
            if not self.excel_bills_tree:
                messagebox.showerror("Error", "Bills table not initialized")
                logger.warning("excel_bills_tree is None")
                return
            
            # Get selection
            selection = self.excel_bills_tree.selection()
            if not selection:
                messagebox.showwarning("Warning", "Please select a bill to edit")
                return
            
            item = selection[0]
            
            # Extract bill index
            try:
                bill_idx = int(item.split('_')[1])
            except (ValueError, IndexError):
                logger.error(f"Invalid item ID format: {item}")
                messagebox.showerror("Error", "Could not identify selected bill")
                return
            
            if bill_idx >= len(self.excel_bills):
                messagebox.showerror("Error", "Bill index out of range")
                logger.error(f"Bill index {bill_idx} out of range (max: {len(self.excel_bills)-1})")
                return
            
            bill = self.excel_bills[bill_idx]
            current_request_no = bill.get('request_no', '')
            bill_no = bill.get('bill_no', '')
            
            # Create edit window
            edit_window = tk.Toplevel(self.master)
            edit_window.title(f"📝 Edit Request No - Bill {bill_no}")
            edit_window.geometry("450x220")
            edit_window.resizable(False, False)
            edit_window.grab_set()  # Make it modal
            
            # Header
            header = ttk.Frame(edit_window)
            header.pack(fill=tk.X, padx=15, pady=10)
            ttk.Label(header, text="Bill Details", font=('Arial', 10, 'bold')).pack(anchor=tk.W)
            
            # Info frame
            info_frame = ttk.LabelFrame(edit_window, text="Current Information", padding=10)
            info_frame.pack(fill=tk.X, padx=15, pady=5)
            
            ttk.Label(info_frame, text=f"Bill No:", font=('Arial', 9, 'bold')).pack(anchor=tk.W)
            ttk.Label(info_frame, text=f"   {bill_no}", foreground="#0066cc").pack(anchor=tk.W)
            
            ttk.Label(info_frame, text=f"Licencee Name:", font=('Arial', 9, 'bold')).pack(anchor=tk.W, pady=(5, 0))
            ttk.Label(info_frame, text=f"   {bill.get('licencee_name', 'N/A')}", foreground="#555555").pack(anchor=tk.W)
            
            ttk.Label(info_frame, text=f"Licence No:", font=('Arial', 9, 'bold')).pack(anchor=tk.W, pady=(5, 0))
            ttk.Label(info_frame, text=f"   {bill.get('licence_no', 'N/A')}", foreground="#555555").pack(anchor=tk.W)
            
            # Edit frame
            edit_frame = ttk.LabelFrame(edit_window, text="Edit Request No", padding=10)
            edit_frame.pack(fill=tk.X, padx=15, pady=5)
            
            ttk.Label(edit_frame, text="New Request No:", font=('Arial', 9)).pack(anchor=tk.W, pady=(0, 5))
            entry = ttk.Entry(edit_frame, width=40, font=('Arial', 11))
            entry.insert(0, current_request_no)
            entry.pack(fill=tk.X, padx=2, pady=2)
            entry.focus()
            # Select all text for easy replacement
            entry.icursor(len(current_request_no))
            
            # Store context for nested functions
            context = {
                'edit_window': edit_window,
                'entry': entry,
                'item': item,
                'bill_idx': bill_idx,
                'current_request_no': current_request_no,
                'bill_no': bill_no
            }
            
            def save_changes():
                """Save the edited Request No"""
                try:
                    new_request_no = context['entry'].get().strip()
                    
                    if not new_request_no:
                        messagebox.showwarning("Warning", "Request No cannot be empty")
                        return
                    
                    # Validate tree widget still exists
                    if not self.excel_bills_tree:
                        logger.error("excel_bills_tree is None during save")
                        messagebox.showerror("Error", "Bills table was closed")
                        return
                    
                    # Update the data in memory
                    self.excel_bills[context['bill_idx']]['request_no'] = new_request_no
                    
                    # Update the tree display
                    tree_values = list(self.excel_bills_tree.item(context['item'], 'values'))
                    tree_values[2] = new_request_no  # Request No is at index 2
                    self.excel_bills_tree.item(context['item'], values=tuple(tree_values))
                    
                    logger.info(f"✏️ Updated Request No from '{context['current_request_no']}' to '{new_request_no}' for Bill {context['bill_no']}")
                    messagebox.showinfo("Success", f"✅ Request No updated to: {new_request_no}")
                    context['edit_window'].destroy()
                    
                except Exception as save_err:
                    logger.error(f"Error saving Request No: {save_err}", exc_info=True)
                    messagebox.showerror("Error", f"Failed to save: {str(save_err)}")
            
            # Buttons frame
            button_frame = ttk.Frame(edit_window)
            button_frame.pack(pady=15)
            
            save_btn = ttk.Button(button_frame, text="💾 Save", command=save_changes, width=15)
            save_btn.pack(side=tk.LEFT, padx=5)
            
            cancel_btn = ttk.Button(button_frame, text="❌ Cancel", command=lambda: context['edit_window'].destroy(), width=15)
            cancel_btn.pack(side=tk.LEFT, padx=5)
            
            # Bind Enter key to save
            entry.bind('<Return>', lambda e: save_changes())
            # Bind Escape to cancel
            entry.bind('<Escape>', lambda e: context['edit_window'].destroy())
            
            # Center the window on parent
            edit_window.transient(self.master)
            edit_window.update_idletasks()
            
        except Exception as err:
            logger.error(f"Error in edit_request_no_dialog: {err}", exc_info=True)
            messagebox.showerror("Error", f"Error opening edit dialog:\n{str(err)}")
    
    def export_matched_to_excel(self):
        """Export MATCHED PAIRS with all details to Excel"""
        try:
            if not self.matched_pairs:
                messagebox.showwarning("Warning", "No matched pairs to export")
                return
            
            # Ask user for save location
            file_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("CSV files", "*.csv"), ("All files", "*.*")],
                initialfile=f"Matched_Bills_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            )
            
            if not file_path:
                return
            
            self.update_status("Exporting matched pairs to Excel...")
            
            # Create comprehensive export data
            export_data = []
            for idx, (job_idx, bill_idx, confidence) in enumerate(self.matched_pairs, 1):
                try:
                    job = self.scanned_jobs[job_idx] if job_idx < len(self.scanned_jobs) else {}
                    bill = self.excel_bills[bill_idx] if bill_idx < len(self.excel_bills) else {}
                    
                    bill_date = bill.get('date', '')
                    if isinstance(bill_date, datetime):
                        bill_date = bill_date.strftime('%Y-%m-%d')
                    
                    export_data.append({
                        'S.No': idx,
                        'Bill Date': bill_date,
                        'Bill No': bill.get('bill_no', ''),
                        'Request No': bill.get('request_no', ''),
                        'Licence No': bill.get('licence_no', ''),
                        'Licencee Name': bill.get('licencee_name', ''),
                        'GSTIN': bill.get('gstin_no', ''),
                        'PCS': bill.get('pcs', 0),
                        'Amount': f"{bill.get('amount', 0):.2f}",
                        'CGST': f"{bill.get('cgst', 0):.2f}",
                        'SGST': f"{bill.get('sgst', 0):.2f}",
                        'IGST': f"{bill.get('igst', 0):.2f}",
                        'Total Amount': f"{bill.get('total_amount', 0):.2f}",
                        'Match Confidence %': f"{confidence:.1f}%",
                        'Payment Status': 'Unpaid',
                        'Notes': f"Matched with portal data (Job: {job.get('job_no', 'N/A')})"
                    })
                except Exception as e:
                    logger.error(f"Error preparing export row {idx}: {e}")
                    continue
            
            if not export_data:
                messagebox.showerror("Error", "No valid data to export")
                return
            
            df = pd.DataFrame(export_data)
            
            # Export based on file extension
            if file_path.endswith('.csv'):
                df.to_csv(file_path, index=False, encoding='utf-8')
            else:
                # Export to Excel with formatting
                with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Matched Bills')
                    
                    # Optional: Add formatting (requires openpyxl)
                    try:
                        from openpyxl.styles import Font, PatternFill, Alignment
                        workbook = writer.book
                        worksheet = writer.sheets['Matched Bills']
                        
                        # Header formatting
                        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
                        header_font = Font(bold=True, color="FFFFFF")
                        
                        for cell in worksheet[1]:
                            cell.fill = header_fill
                            cell.font = header_font
                            cell.alignment = Alignment(horizontal="center", vertical="center")
                        
                        # Auto-adjust column widths
                        for column in worksheet.columns:
                            max_length = 0
                            column_letter = column[0].column_letter
                            for cell in column:
                                try:
                                    if len(str(cell.value)) > max_length:
                                        max_length = len(str(cell.value))
                                except (TypeError, AttributeError):
                                    pass
                            adjusted_width = min(max_length + 2, 50)
                            worksheet.column_dimensions[column_letter].width = adjusted_width
                    except ImportError:
                        logger.warning("openpyxl not available, export will be without formatting")
            
            logger.info(f"✅ Exported {len(export_data)} matched pairs to {file_path}")
            self.update_status(f"✅ Exported {len(export_data)} matched pairs")
            messagebox.showinfo("Success", f"Exported {len(export_data)} matched pairs to:\n{file_path}")
            
        except Exception as e:
            logger.error(f"Error exporting matched pairs: {e}\n{traceback.format_exc()}")
            messagebox.showerror("Error", f"Export failed:\n{str(e)}")
            self.update_status("Ready")
    
    def update_status(self, message):
        """Update status label"""
        if self.status_label:
            self.status_label.config(text=message)
            # Update the root window to refresh the UI
            try:
                root = self.status_label.winfo_toplevel()
                if root and hasattr(root, 'update_idletasks'):
                    root.update_idletasks()
            except:
                pass  # Silently ignore if update fails
