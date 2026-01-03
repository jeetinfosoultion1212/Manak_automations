#!/usr/bin/env python3
"""
Job Cards Processor Module
Handles job cards data management and automatic job number fetching
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import time
import mysql.connector
from mysql.connector import Error
import base64
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import os
import sys

# Fix MySQL localization issue BEFORE importing mysql.connector
os.environ['LANG'] = 'C'
os.environ['LC_ALL'] = 'C'
os.environ['LC_MESSAGES'] = 'C'

from config import DB_CONFIG, get_safe_db_config_for_logging
import traceback
import datetime


class JobCardsProcessor:
    """Handles job cards data management and automatic job number fetching"""
    
    def __init__(self, driver, log_callback, license_check_callback, app_context=None):
        self.driver = driver
        self.main_log_callback = log_callback
        self.check_license_before_action = license_check_callback
        self.app_context = app_context  # Reference to main app for settings
        self.notebook = None
        self.log_text = None
        
        # Database connection details - Load from secure config
        self.db_config = DB_CONFIG.copy()
        
        # Job cards monitoring
        self.job_cards_monitoring = False
        self.monitor_thread = None
        
        # Firm ID management - Get from settings or use default
        self.current_firm_id = self.get_firm_id_from_settings()
        
        # Process lock to prevent conflicts
        self.process_lock = threading.Lock()
        self.is_processing = False
        
        # Initialize crash logging
        self.setup_crash_logging()
    
    def get_firm_id_from_settings(self):
        """Get Firm ID from device license or app settings or return default"""
        try:
            # First, try to get firm_id from device license
            if self.app_context and hasattr(self.app_context, 'license_manager'):
                license_manager = self.app_context.license_manager
                if hasattr(license_manager, 'firm_id') and license_manager.firm_id:
                    print(f"🏢 Using firm_id from device license: {license_manager.firm_id}")
                    return license_manager.firm_id
            
            # Fallback to app settings
            if self.app_context and hasattr(self.app_context, 'firm_id_var'):
                firm_id = self.app_context.firm_id_var.get().strip()
                if firm_id:
                    return firm_id
        except Exception as e:
            print(f"Warning: Could not get Firm ID from license or settings: {e}")
        
        # Return default if nothing available
        return '2'
    
    def update_firm_id_from_settings(self):
        """Update current firm ID from device license or settings"""
        self.current_firm_id = self.get_firm_id_from_settings()
        if hasattr(self, 'firm_id_var'):
            self.firm_id_var.set(self.current_firm_id)
        if hasattr(self, 'current_firm_label'):
            self.current_firm_label.config(text=f"Current Firm ID: {self.current_firm_id}")
        if hasattr(self, 'firm_id_display_label'):
            self.firm_id_display_label.config(text=self.current_firm_id)
    
    def refresh_firm_id_from_license(self):
        """Refresh firm_id from license and update UI"""
        try:
            old_firm_id = self.current_firm_id
            self.current_firm_id = self.get_firm_id_from_settings()
            
            # Update UI elements if they exist
            if hasattr(self, 'firm_id_var'):
                self.firm_id_var.set(self.current_firm_id)
            if hasattr(self, 'current_firm_label'):
                self.current_firm_label.config(text=f"Current Firm ID: {self.current_firm_id}")
            if hasattr(self, 'firm_id_display_label'):
                self.firm_id_display_label.config(text=self.current_firm_id)
            
            # Log the change
            if old_firm_id != self.current_firm_id:
                self.log_job_cards(f"🏢 Firm ID updated from {old_firm_id} to {self.current_firm_id}")
                
        except Exception as e:
            self.log_job_cards(f"❌ Error refreshing firm_id: {str(e)}")
    
    def setup_crash_logging(self):
        """Setup crash logging for debugging exe issues"""
        try:
            # Handle both development and executable environments
            if getattr(sys, 'frozen', False):
                # Running as executable
                base_path = sys._MEIPASS
                log_dir = os.path.join(base_path, 'logs')
            else:
                # Running as script
                log_dir = os.path.join(os.path.dirname(__file__), 'logs')
            
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            self.log_file = os.path.join(log_dir, f'job_cards_debug_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
            
            # Log initial system info
            self.write_crash_log("=== JOB CARDS PROCESSOR INITIALIZED ===")
            self.write_crash_log(f"Timestamp: {datetime.datetime.now()}")
            self.write_crash_log(f"Python version: {os.sys.version}")
            self.write_crash_log(f"Working directory: {os.getcwd()}")
            self.write_crash_log(f"Script directory: {os.path.dirname(__file__)}")
            self.write_crash_log(f"Log file: {self.log_file}")
            
        except Exception as e:
            print(f"Warning: Could not setup crash logging: {e}")
    
    def write_crash_log(self, message):
        """Write message to crash log file"""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] {message}\n")
                f.flush()
        except Exception:
            pass  # Silently fail if logging fails
    
    def setup_job_cards_tab(self, notebook):
        """Setup Update Jobs tab with modern styling"""
        self.notebook = notebook
        
        # Create Update Jobs tab
        job_cards_frame = ttk.Frame(notebook)
        notebook.add(job_cards_frame, text="📋 Update Jobs")
        
        # Main horizontal layout - Left and Right sections
        main_horizontal = ttk.Frame(job_cards_frame)
        main_horizontal.pack(fill='both', expand=True, padx=8, pady=8)
        
        # LEFT SECTION - Controls (30% width)
        left_section = ttk.Frame(main_horizontal)
        left_section.pack(side='left', fill='y', padx=(0, 8))
        
        # RIGHT SECTION - Data Table (70% width)
        right_section = ttk.Frame(main_horizontal)
        right_section.pack(side='right', fill='both', expand=True)
        
        # Setup left and right sections
        self.setup_job_cards_left_section(left_section)
        self.setup_job_cards_right_section(right_section)
    
    def setup_job_cards_left_section(self, parent):
        """Setup left section with improved workflow and modern styling"""
        
        # ==========================================
        # STEP 1: FIRM SETUP
        # ==========================================
        firm_card = ttk.LabelFrame(parent, text="🏢 Firm Setup", style='Compact.TLabelframe')
        firm_card.pack(fill='x', pady=(0, 8))
        
        firm_frame = ttk.Frame(firm_card)
        firm_frame.pack(fill='x', padx=8, pady=8)
        
        # Firm ID display
        ttk.Label(firm_frame, text="Current Firm ID:", font=('Segoe UI', 9, 'bold')).pack(anchor='w')
        self.firm_id_display_label = ttk.Label(firm_frame, text=self.current_firm_id, 
                                             font=('Segoe UI', 12, 'bold'), foreground='#17a2b8')
        self.firm_id_display_label.pack(anchor='w', pady=(2, 0))
        
        # Hidden firm_id variable for internal use
        self.firm_id_var = tk.StringVar(value=self.current_firm_id)
        
        # ==========================================
        # LOAD DATA
        # ==========================================
        load_card = ttk.LabelFrame(parent, text="📥 Load Job Cards", style='Compact.TLabelframe')
        load_card.pack(fill='x', pady=(0, 8))
        
        load_frame = ttk.Frame(load_card)
        load_frame.pack(fill='x', padx=8, pady=8)
        
        # Load Data Button
        self.load_job_cards_btn = ttk.Button(
            load_frame, 
            text="📥 Load Job Cards from Database", 
            command=self.load_job_cards_data,
            style='Info.TButton'
        )
        self.load_job_cards_btn.pack(fill='x', pady=(0, 4))
        
        # Info label
        info_label = ttk.Label(load_frame, 
                              text="💡 Loads accepted requests from database", 
                              font=('Segoe UI', 8), foreground='#6c757d')
        info_label.pack(anchor='w')
        
        # ==========================================
        # CREATE JOB CARDS
        # ==========================================
        create_card = ttk.LabelFrame(parent, text="🎯 Create Job Cards", style='Compact.TLabelframe')
        create_card.pack(fill='x', pady=(0, 8))
        
        create_frame = ttk.Frame(create_card)
        create_frame.pack(fill='x', padx=8, pady=8)
        
        # Create Job Cards Button
        self.create_job_cards_btn = ttk.Button(
            create_frame, 
            text="📋 Scan & Create Job Cards", 
            command=self.create_job_cards_from_qm_received_list,
            style='Primary.TButton'
        )
        self.create_job_cards_btn.pack(fill='x', pady=(0, 4))
        
        # Info label
        create_info = ttk.Label(create_frame, 
                               text="Scans portal and creates job cards for new requests", 
                               font=('Segoe UI', 8), foreground='#6c757d')
        create_info.pack(anchor='w')
        
        # ==========================================
        # UPDATE JOB NUMBERS
        # ==========================================
        fetch_card = ttk.LabelFrame(parent, text="🔢 Update Job Numbers", style='Compact.TLabelframe')
        fetch_card.pack(fill='x', pady=(0, 8))
        
        fetch_frame = ttk.Frame(fetch_card)
        fetch_frame.pack(fill='x', padx=8, pady=8)
        
        # Fetch Job Numbers Button
        self.fetch_job_numbers_btn = ttk.Button(
            fetch_frame, 
            text="🔢 Get Job Numbers", 
            command=self.fetch_missing_job_numbers,
            state='disabled',
            style='Success.TButton'
        )
        self.fetch_job_numbers_btn.pack(fill='x', pady=(0, 4))
        
        # Info label
        fetch_info = ttk.Label(fetch_frame, 
                              text="Updates missing job numbers from portal", 
                              font=('Segoe UI', 8), foreground='#6c757d')
        fetch_info.pack(anchor='w')
        
        # ==========================================
        # AUTO MONITOR SECTION
        # ==========================================
        monitor_card = ttk.LabelFrame(parent, text="🔄 Auto Monitor", style='Compact.TLabelframe')
        monitor_card.pack(fill='x', pady=(0, 8))
        
        monitor_frame = ttk.Frame(monitor_card)
        monitor_frame.pack(fill='x', padx=8, pady=8)
        
        # Auto Monitor Toggle
        self.auto_monitor_var = tk.BooleanVar(value=False)
        self.auto_monitor_check = ttk.Checkbutton(
            monitor_frame,
            text="🤖 Enable Auto Monitor (Every 1 minute)",
            variable=self.auto_monitor_var,
            command=self.toggle_auto_monitor
        )
        self.auto_monitor_check.pack(fill='x', pady=(0, 4))
        
        # Monitor Timer Display
        self.monitor_timer_label = ttk.Label(
            monitor_frame,
            text="⏱️ Next check: --:--",
            font=('Segoe UI', 9),
            foreground='#6c757d'
        )
        self.monitor_timer_label.pack(fill='x', pady=(0, 4))
        
        # Auto monitor info
        auto_info = ttk.Label(monitor_frame, 
                             text="Automatically creates job cards and updates job numbers", 
                             font=('Segoe UI', 8), foreground='#6c757d')
        auto_info.pack(anchor='w')
        
        # Manual run button - Hidden (auto-monitor does the same thing)
        # Uncomment below if you need manual control
        # manual_run_btn = ttk.Button(monitor_frame, text="▶ Run Now", 
        #                            command=self.run_unified_workflow_manual, style='Success.TButton')
        # manual_run_btn.pack(fill='x', pady=(8, 0))
        
        # ==========================================
        # PROGRESS & STATUS SECTION
        # ==========================================
        progress_card = ttk.LabelFrame(parent, text="📊 Current Status", style='Compact.TLabelframe')
        progress_card.pack(fill='x', pady=(0, 8))
        
        progress_frame = ttk.Frame(progress_card)
        progress_frame.pack(fill='x', padx=8, pady=8)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                          maximum=100, style='Modern.Horizontal.TProgressbar')
        self.progress_bar.pack(fill='x', pady=(0, 8))
        
        # Status Display
        self.job_cards_status_label = ttk.Label(progress_frame, text="🟢 Ready", 
                                              font=('Segoe UI', 10, 'bold'), foreground='#28a745')
        self.job_cards_status_label.pack(anchor='w', pady=(0, 4))
        
        self.job_cards_progress_label = ttk.Label(progress_frame, text="💡 Click 'Load Data' to start", 
                                                font=('Segoe UI', 9), foreground='#6c757d')
        self.job_cards_progress_label.pack(anchor='w')
        
        # ==========================================
        # STATISTICS SECTION
        # ==========================================
        stats_card = ttk.LabelFrame(parent, text="📈 Database Statistics", style='Compact.TLabelframe')
        stats_card.pack(fill='x', pady=(0, 8))
        
        stats_frame = ttk.Frame(stats_card)
        stats_frame.pack(fill='x', padx=8, pady=8)
        
        # Statistics labels with better formatting
        self.total_items_label = ttk.Label(stats_frame, text="📋 Total Items: 0", 
                                         font=('Segoe UI', 9, 'bold'), foreground='#17a2b8')
        self.total_items_label.pack(anchor='w', pady=(0, 4))
        
        self.missing_job_no_label = ttk.Label(stats_frame, text="⚠️ Missing Job Numbers: 0", 
                                            font=('Segoe UI', 9, 'bold'), foreground='#ffc107')
        self.missing_job_no_label.pack(anchor='w', pady=(0, 4))
        
        self.completed_label = ttk.Label(stats_frame, text="✅ Completed: 0", 
                                       font=('Segoe UI', 9, 'bold'), foreground='#28a745')
        self.completed_label.pack(anchor='w', pady=(0, 4))
        
        # Ready to fetch label
        self.ready_to_fetch_label = ttk.Label(stats_frame, text="🎯 Ready to Fetch: 0", 
                                            font=('Segoe UI', 9, 'bold'), foreground='#007bff')
        self.ready_to_fetch_label.pack(anchor='w')
        
        # ==========================================
        # WORKFLOW GUIDE SECTION
        # ==========================================
        guide_card = ttk.LabelFrame(parent, text="📖 Quick Guide", style='Compact.TLabelframe')
        guide_card.pack(fill='x', pady=(0, 8))
        
        guide_frame = ttk.Frame(guide_card)
        guide_frame.pack(fill='x', padx=8, pady=8)
        
        # Workflow steps
        steps_text = """1️⃣ Load Data - Get requests from database
2️⃣ Create Job Cards - Scan portal & create cards  
3️⃣ Fetch Job Numbers - Get numbers from QM list
🔄 Auto Monitor - Runs all steps automatically"""
        
        guide_label = ttk.Label(guide_frame, text=steps_text, 
                               font=('Segoe UI', 8), foreground='#495057', justify='left')
        guide_label.pack(anchor='w')
        
        # Processing Details Card - NEW
        details_card = ttk.LabelFrame(parent, text="🔍 Processing Details", style='Compact.TLabelframe')
        details_card.pack(fill='both', expand=True)
        
        # Processing log
        self.job_cards_log_text = tk.Text(
            details_card, 
            height=8, 
            wrap='word', 
            state='disabled',
            font=('Consolas', 7),
            bg='#f8f9fa',
            fg='#495057',
            insertbackground='#495057',
            relief='flat',
            borderwidth=1
        )
        log_scrollbar = ttk.Scrollbar(details_card, orient='vertical', command=self.job_cards_log_text.yview)
        self.job_cards_log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.job_cards_log_text.pack(side='left', fill='both', expand=True, padx=8, pady=8)
        log_scrollbar.pack(side='right', fill='y', pady=8)
    
    def setup_job_cards_right_section(self, parent):
        """Setup right section with improved data table and log"""
        
        # ==========================================
        # JOB CARDS DATA TABLE
        # ==========================================
        data_card = ttk.LabelFrame(parent, text="📋 Job Cards Data", style='Compact.TLabelframe')
        data_card.pack(fill='both', expand=True, pady=(0, 8))
        
        # Table header with summary
        header_frame = ttk.Frame(data_card)
        header_frame.pack(fill='x', padx=8, pady=(8, 4))
        
        # Summary labels
        self.table_summary_label = ttk.Label(header_frame, text="📊 No data loaded", 
                                           font=('Segoe UI', 9, 'bold'), foreground='#6c757d')
        self.table_summary_label.pack(side='left')
        
        # Refresh button
        refresh_btn = ttk.Button(header_frame, text="🔄 Refresh", 
                                command=self.load_job_cards_data, style='Small.TButton')
        refresh_btn.pack(side='right')
        
        # Create Treeview for job cards data with better styling
        columns = ('ID', 'Request No', 'Item', 'Pcs', 'Purity', 'Weight', 'Job No', 'Status')
        
        # Create frame for tree and scrollbars
        tree_frame = ttk.Frame(data_card)
        tree_frame.pack(fill='both', expand=True, padx=8, pady=(0, 8))
        
        self.job_cards_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=12)
        
        # Configure columns with better widths
        column_configs = {
            'ID': 50,
            'Request No': 120,
            'Item': 100,
            'Pcs': 50,
            'Purity': 80,
            'Weight': 80,
            'Job No': 100,
            'Status': 150
        }
        
        for col in columns:
            self.job_cards_tree.heading(col, text=col)
            self.job_cards_tree.column(col, width=column_configs[col], minwidth=column_configs[col])
        
        # Add scrollbars
        tree_scroll_y = ttk.Scrollbar(tree_frame, orient='vertical', command=self.job_cards_tree.yview)
        tree_scroll_x = ttk.Scrollbar(tree_frame, orient='horizontal', command=self.job_cards_tree.xview)
        self.job_cards_tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        
        # Pack tree and scrollbars
        self.job_cards_tree.pack(side='left', fill='both', expand=True)
        tree_scroll_y.pack(side='right', fill='y')
        tree_scroll_x.pack(side='bottom', fill='x')
        
        # ==========================================
        # PROCESSING LOG
        # ==========================================
        log_card = ttk.LabelFrame(parent, text="📝 Processing Log", style='Compact.TLabelframe')
        log_card.pack(fill='both', expand=True)
        
        # Log header with clear button
        log_header_frame = ttk.Frame(log_card)
        log_header_frame.pack(fill='x', padx=8, pady=(8, 4))
        
        ttk.Label(log_header_frame, text="🔄 Real-time processing updates", 
                 font=('Segoe UI', 9, 'bold')).pack(side='left')
        
        clear_log_btn = ttk.Button(log_header_frame, text="🗑️ Clear", 
                                  command=self.clear_log, style='Small.TButton')
        clear_log_btn.pack(side='right')
        
        # Create log text area with better styling
        import tkinter.scrolledtext as scrolledtext
        self.job_cards_log_text = scrolledtext.ScrolledText(log_card, height=8, font=('Consolas', 8), 
                                                           bg='#f8f9fa', fg='#495057', wrap=tk.WORD,
                                                           state='disabled')
        self.job_cards_log_text.pack(fill='both', expand=True, padx=8, pady=(0, 8))
    
    def clear_log(self):
        """Clear the processing log"""
        try:
            if hasattr(self, 'job_cards_log_text'):
                self.job_cards_log_text.config(state='normal')
                self.job_cards_log_text.delete(1.0, tk.END)
                self.job_cards_log_text.config(state='disabled')
        except Exception as e:
            self.log_job_cards(f"⚠️ Error clearing log: {str(e)}")
    
    def get_database_connection(self):
        """Get database connection with timeout and error handling"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                self.write_crash_log(f"Database connection attempt {attempt + 1}/{max_retries}")
                
                # Check if we're in executable environment
                is_executable = getattr(sys, 'frozen', False)
                self.write_crash_log(f"Running in executable mode: {is_executable}")
                
                # Environment variables already set at module level
                
                # Add connection timeout and other parameters for exe stability
                db_config_with_timeout = self.db_config.copy()
                db_config_with_timeout.update({
                    'connection_timeout': 15,  # Reduced timeout
                    'autocommit': True,
                    'raise_on_warnings': False,  # Prevent warnings from causing issues
                    'connect_timeout': 10  # Additional connection timeout
                })
                
                # Additional executable-specific settings
                if is_executable:
                    db_config_with_timeout.update({
                        'use_pure': True,  # Use pure Python implementation
                    })
                
                self.log_job_cards(f"🔌 Attempting database connection (attempt {attempt + 1})...")
                connection = mysql.connector.connect(**db_config_with_timeout)
                
                # Test the connection with a simple query
                cursor = connection.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                cursor.close()
                
                if result:
                    self.log_job_cards(f"✅ Database connection successful (attempt {attempt + 1})")
                    self.write_crash_log(f"Database connection successful on attempt {attempt + 1}")
                    return connection
                else:
                    raise Exception("Connection test query returned no result")
                
            except mysql.connector.Error as e:
                self.log_job_cards(f"❌ MySQL Database connection error (attempt {attempt + 1}): {e}")
                self.log_job_cards(f"❌ Error code: {e.errno}")
                self.log_job_cards(f"❌ SQL state: {e.sqlstate}")
                self.write_crash_log(f"MySQL Error attempt {attempt + 1}: {e}")
                
                if attempt < max_retries - 1:
                    self.log_job_cards(f"⏳ Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    self.log_job_cards("❌ All database connection attempts failed")
                    self.write_crash_log("All database connection attempts failed")
                    return None
                
            except Exception as e:
                self.log_job_cards(f"❌ Unexpected database connection error (attempt {attempt + 1}): {e}")
                self.log_job_cards(f"❌ Error type: {type(e).__name__}")
                self.write_crash_log(f"Unexpected error attempt {attempt + 1}: {e}")
                
                if attempt < max_retries - 1:
                    self.log_job_cards(f"⏳ Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    self.log_job_cards("❌ All database connection attempts failed")
                    self.write_crash_log("All database connection attempts failed")
                    return None
        
        return None
    
    def load_job_cards_data(self):
        """Load job cards data from database"""
        try:
            self.write_crash_log("=== LOAD JOB CARDS DATA CALLED ===")
            
            # Update firm ID from entry or settings
            if hasattr(self, 'firm_id_var'):
                self.current_firm_id = self.firm_id_var.get().strip() or self.get_firm_id_from_settings()
            else:
                self.current_firm_id = self.get_firm_id_from_settings()
            
            self.write_crash_log(f"Firm ID set to: {self.current_firm_id}")
            
            # Start worker thread
            self.write_crash_log("Starting worker thread...")
            threading.Thread(target=self._load_job_cards_data_worker, daemon=True).start()
            
        except Exception as e:
            self.write_crash_log(f"ERROR in load_job_cards_data: {str(e)}")
            self.write_crash_log(f"Traceback: {traceback.format_exc()}")
            messagebox.showerror("Error", f"Error starting data load: {str(e)}")
    
    def _load_job_cards_data_worker(self):
        """Worker thread for loading job cards data with progress updates"""
        connection = None
        cursor = None
        
        try:
            self.write_crash_log("=== WORKER THREAD STARTED ===")
            self.update_job_cards_status("Loading data...", 'warning')
            self.update_progress(10, "Connecting to database...")
            self.log_job_cards(f"🔍 Loading job cards data from database (Firm ID: {self.current_firm_id})...")
            
            # Debug: Log database connection attempt (no sensitive info)
            self.log_job_cards("🔧 Attempting database connection...")
            self.write_crash_log("Attempting database connection...")
            
            # Get database connection with retry logic
            self.log_job_cards("🔌 Attempting database connection...")
            connection = self.get_database_connection()
            if not connection:
                self.update_job_cards_status("Database Error", 'danger')
                self.update_progress(0, "Database connection failed")
                self.log_job_cards("❌ Failed to establish database connection after retries")
                self.write_crash_log("CRITICAL: Database connection failed completely")
                return
            
            self.log_job_cards("✅ Database connection established")
            self.update_progress(30, "Database connected, executing query...")
            
            # Create cursor
            cursor = connection.cursor()
            self.log_job_cards("✅ Database cursor created")
            
            # Query to get job cards data - only those with missing job_no (0, blank, or null)
            query = """
                SELECT id, request_no, item, pcs, purity, weight, job_no, status, created_at
                FROM job_cards 
                WHERE firm_id = %s 
                AND (job_no IS NULL OR job_no = '' OR job_no = '0' OR TRIM(job_no) = '' OR TRIM(job_no) = '0')
                ORDER BY id DESC 
                LIMIT 100
            """
            
            self.log_job_cards(f"🔍 Executing query for firm_id: {self.current_firm_id}")
            cursor.execute(query, (self.current_firm_id,))
            results = cursor.fetchall()
            self.log_job_cards(f"📊 Query returned {len(results)} records")
            self.update_progress(50, f"Found {len(results)} records, processing...")
            
            # Clear existing data safely
            try:
                for item in self.job_cards_tree.get_children():
                    self.job_cards_tree.delete(item)
                self.log_job_cards("🧹 Cleared existing treeview data")
            except Exception as tree_error:
                self.log_job_cards(f"⚠️ Warning clearing treeview: {str(tree_error)}")
            
            # Add data to treeview - all results already have missing job_no from SQL query
            missing_job_no_count = len(results)
            inserted_count = 0
            
            for i, row in enumerate(results):
                try:
                    id_val, request_no, item, pcs, purity, weight, job_no, status, created_at = row
                    
                    # Safe value conversion
                    weight_str = "0.000"
                    try:
                        if weight is not None:
                            weight_str = f"{float(weight):.3f}"
                    except (ValueError, TypeError):
                        weight_str = "0.000"
                    
                    # Insert into treeview (all records have missing job_no)
                    self.job_cards_tree.insert('', 'end', values=(
                        str(id_val) if id_val is not None else "N/A",
                        str(request_no) if request_no is not None else "N/A",
                        str(item) if item is not None else "N/A",
                        str(pcs) if pcs is not None else "N/A",
                        str(purity) if purity is not None else "N/A",
                        weight_str,
                        str(job_no) if job_no is not None else "N/A",
                        "Missing Job No"
                    ))
                    inserted_count += 1
                    
                    # Update progress
                    progress = 50 + (i / len(results)) * 30
                    self.update_progress(progress, f"Processing record {i+1}/{len(results)}...")
                    
                except Exception as row_error:
                    self.log_job_cards(f"⚠️ Error processing row {inserted_count}: {str(row_error)}")
                    continue
            
            self.log_job_cards(f"✅ Successfully inserted {inserted_count} records into treeview")
            self.update_progress(80, "Updating statistics...")
            
            # Update statistics with modern styling - with error handling
            displayed_items = inserted_count  # Items actually inserted
            
            try:
                self.total_items_label.config(text=f"📋 Total Items: {displayed_items}")
                self.missing_job_no_label.config(text=f"⚠️ Missing Job Numbers: {missing_job_no_count}")
                self.completed_label.config(text=f"✅ Completed: {displayed_items - missing_job_no_count}")
                if hasattr(self, 'ready_to_fetch_label'):
                    self.ready_to_fetch_label.config(text=f"🎯 Ready to Fetch: {missing_job_no_count}")
                
                # Update table summary
                if hasattr(self, 'table_summary_label'):
                    if displayed_items > 0:
                        summary_text = f"📊 Loaded {displayed_items} items • {missing_job_no_count} need job numbers"
                        self.table_summary_label.config(text=summary_text, foreground='#495057')
                    else:
                        self.table_summary_label.config(text="📊 No data loaded", foreground='#6c757d')
                
                self.log_job_cards("✅ Updated statistics labels")
            except Exception as label_error:
                self.log_job_cards(f"⚠️ Error updating labels: {str(label_error)}")
            
            # Enable fetch button if there are missing job numbers
            try:
                if missing_job_no_count > 0:
                    self.fetch_job_numbers_btn.config(state='normal')
                    self.log_job_cards("✅ Enabled fetch job numbers button")
                else:
                    self.fetch_job_numbers_btn.config(state='disabled')
                    self.log_job_cards("ℹ️ No missing job numbers found")
            except Exception as button_error:
                self.log_job_cards(f"⚠️ Error updating button state: {str(button_error)}")
            
            self.update_job_cards_status("Data Loaded", 'success')
            self.update_progress(100, f"Loaded {displayed_items} items successfully")
            self.log_job_cards(f"✅ Loaded {displayed_items} items with missing job numbers - ready for job number fetching")
            
        except mysql.connector.Error as db_error:
            self.update_job_cards_status("Database Error", 'danger')
            self.update_progress(0, "Database error occurred")
            self.log_job_cards(f"❌ Database error: {str(db_error)}")
            self.log_job_cards(f"❌ Error code: {db_error.errno}")
            self.log_job_cards(f"❌ SQL state: {db_error.sqlstate}")
            
            # Log to crash file
            self.write_crash_log(f"MYSQL ERROR: {str(db_error)}")
            self.write_crash_log(f"Error code: {db_error.errno}")
            self.write_crash_log(f"SQL state: {db_error.sqlstate}")
            
        except Exception as e:
            self.update_job_cards_status("Error", 'danger')
            self.update_progress(0, "Unexpected error occurred")
            self.log_job_cards(f"❌ Unexpected error loading job cards data: {str(e)}")
            self.log_job_cards(f"❌ Error type: {type(e).__name__}")
            
            # Log to crash file
            self.write_crash_log(f"UNEXPECTED ERROR: {str(e)}")
            self.write_crash_log(f"Error type: {type(e).__name__}")
            self.write_crash_log(f"Traceback: {traceback.format_exc()}")
            
            import traceback
            self.log_job_cards(f"❌ Traceback: {traceback.format_exc()}")
            
            # Show user-friendly error message instead of crashing
            try:
                if hasattr(self, 'notebook') and self.notebook:
                    root = self.notebook.winfo_toplevel()
                    root.after(0, lambda: messagebox.showerror("Database Error", 
                        f"Failed to load job cards data.\n\nError: {str(e)}\n\nPlease check your internet connection and try again."))
            except Exception as ui_error:
                self.write_crash_log(f"UI Error display failed: {str(ui_error)}")
            
        finally:
            # Ensure proper cleanup
            try:
                if cursor:
                    cursor.close()
                    self.log_job_cards("🔒 Closed database cursor")
            except Exception as cursor_error:
                self.log_job_cards(f"⚠️ Error closing cursor: {str(cursor_error)}")
                
            try:
                if connection:
                    connection.close()
                    self.log_job_cards("🔒 Closed database connection")
            except Exception as conn_error:
                self.log_job_cards(f"⚠️ Error closing connection: {str(conn_error)}")
    
    def toggle_auto_monitor(self):
        """Toggle auto monitoring"""
        if self.auto_monitor_var.get():
            self.start_auto_monitoring()
        else:
            self.stop_auto_monitoring()
    
    def start_auto_monitoring(self):
        """Start auto monitoring for new records"""
        if self.job_cards_monitoring:
            return
        
        self.job_cards_monitoring = True
        self.monitor_thread = threading.Thread(target=self._auto_monitor_worker, daemon=True)
        self.monitor_thread.start()
        self.log_job_cards("🔄 Auto monitoring started (checking every 1 minute)")
    
    def stop_auto_monitoring(self):
        """Stop auto monitoring"""
        self.job_cards_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
        
        # Clear timer display
        if hasattr(self, 'monitor_timer_label'):
            self.monitor_timer_label.config(text="⏱️ Next check: --:--")
        
        self.log_job_cards("⏹️ Auto monitoring stopped")
    
    def _auto_monitor_worker(self):
        """Professional unified auto-monitor with intelligent workflow"""
        while self.job_cards_monitoring:
            try:
                # Update firm ID from entry or settings
                try:
                    if hasattr(self, 'firm_id_var'):
                        self.current_firm_id = self.firm_id_var.get().strip() or self.get_firm_id_from_settings()
                    else:
                        self.current_firm_id = self.get_firm_id_from_settings()
                except Exception:
                    self.current_firm_id = self.get_firm_id_from_settings()
                
                # Check if another process is already running
                if self.is_processing:
                    self.log_job_cards("⏰ Auto monitor: Another process running, skipping this cycle")
                    self._countdown_timer(60)  # Countdown for 60 seconds
                    continue
                
                self.log_job_cards("🚀 Auto-monitor cycle started - Unified workflow")
                
                # UNIFIED WORKFLOW: Single intelligent process
                success = self.run_unified_qm_workflow()
                
                if success:
                    self.log_job_cards("✅ Auto-monitor cycle completed successfully")
                else:
                    self.log_job_cards("⚠️ Auto-monitor cycle completed with issues")
                
            except Exception as e:
                self.log_job_cards(f"❌ Auto monitor error: {str(e)}")
                import traceback
                self.write_crash_log(f"Auto monitor error: {traceback.format_exc()}")
            
            # Countdown timer for 60 seconds before next check
            if self.job_cards_monitoring:
                self._countdown_timer(60)
    
    def run_unified_qm_workflow(self):
        """Run unified QM workflow - scan, create, update in one intelligent process"""
        try:
            if not self.driver:
                self.log_job_cards("❌ Browser not available for unified workflow")
                return False
            
            self.log_job_cards("🔍 Step 1: Scanning QM Received List...")
            
            # Navigate to QM Received List
            qm_received_url = "https://huid.manakonline.in/MANAK/qualityManagerDesk_List?hmType=HMQM"
            self.driver.get(qm_received_url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(3)
            
            # Scan all requests from portal
            portal_requests = self.scan_qm_received_list()
            
            if not portal_requests:
                self.log_job_cards("ℹ️ No requests found in QM Received List")
                self.log_job_cards("🔍 Checking database for job cards with missing job numbers...")
                
                # Even if no new requests in portal, check database for missing job numbers
                self.fetch_missing_job_numbers()
                return True
            
            self.log_job_cards(f"📋 Found {len(portal_requests)} requests in portal")
            
            # Get database requests
            db_requests = self.get_all_database_requests()
            self.log_job_cards(f"📊 Found {len(db_requests)} requests in database")
            
            # Analyze and categorize requests
            analysis = self.analyze_requests(portal_requests, db_requests)
            
            # Process requests that need job card creation
            if analysis['need_job_cards']:
                self.log_job_cards(f"🎯 Step 2: Creating job cards for {len(analysis['need_job_cards'])} requests...")
                created_count = self.create_job_cards_batch(analysis['need_job_cards'])
                if created_count > 0:
                    self.log_job_cards(f"✅ Created {created_count} job cards")
                    
                    # Wait a bit for MANAK system to process
                    self.log_job_cards("⏳ Waiting 3 seconds for MANAK system to process job cards...")
                    time.sleep(3)  # Reduced from 5 to 3 seconds for faster processing
                    
                    # Fetch job numbers using the direct method (works immediately!)
                    self.log_job_cards("🔍 Fetching job numbers for newly created job cards using direct method...")
                    self.fetch_missing_job_numbers()
            
            # Process requests that need job number fetching
            if analysis['need_job_numbers']:
                self.log_job_cards(f"🔍 Step 3: Fetching job numbers for {len(analysis['need_job_numbers'])} requests...")
                fetched_count = self.fetch_job_numbers_batch(analysis['need_job_numbers'])
                if fetched_count > 0:
                    self.log_job_cards(f"✅ Fetched {fetched_count} job numbers")
            
            # Update UI with latest data
            self.log_job_cards("🔄 Step 4: Updating UI with latest data...")
            self.load_job_cards_data()
            
            return True
            
        except Exception as e:
            self.log_job_cards(f"❌ Unified workflow error: {str(e)}")
            return False
    
    def scan_qm_received_list(self):
        """Scan QM Received List and return all requests with their status"""
        try:
            requests = []
            
            # Wait for table to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            
            # Find the table containing the requests
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            target_table = None
            
            for table in tables:
                if "Create Job Card" in table.text or "Request No" in table.text:
                    target_table = table
                    break
            
            if not target_table:
                self.log_job_cards("❌ Could not find requests table")
                return requests
            
            # Extract rows from the table
            rows = target_table.find_elements(By.TAG_NAME, "tr")[1:]  # Skip header row
            
            for row in rows:
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 8:  # Ensure we have enough columns
                        request_no = cells[1].text.strip()  # Request No column
                        request_date = cells[2].text.strip()  # Request Date column
                        job_card_no = cells[3].text.strip()  # Job Card No column
                        jeweller_name = cells[4].text.strip()  # Jeweller Outlet Name
                        status = cells[6].text.strip()  # Status column
                        
                        # Check for "Create Job Card" link
                        activity_cell = cells[7]
                        create_link = None
                        try:
                            create_link = activity_cell.find_element(By.LINK_TEXT, "Create Job Card")
                        except:
                            pass
                        
                        if request_no:
                            requests.append({
                                'request_no': request_no,
                                'request_date': request_date,
                                'job_card_no': job_card_no,
                                'jeweller_name': jeweller_name,
                                'status': status,
                                'create_link': create_link,
                                'needs_job_card': create_link is not None,
                                'has_job_card': job_card_no and job_card_no != "NA"
                            })
                            
                except Exception as e:
                    self.log_job_cards(f"⚠️ Error extracting row data: {str(e)}")
                    continue
            
            return requests
            
        except Exception as e:
            self.log_job_cards(f"❌ Error scanning QM received list: {str(e)}")
            return []
    
    def get_all_database_requests(self):
        """Get all requests from database"""
        try:
            connection = self.get_database_connection()
            if not connection:
                return []
            
            cursor = connection.cursor()
            query = """
                SELECT DISTINCT request_no, 
                       COUNT(*) as item_count,
                       SUM(CASE WHEN job_no IS NULL OR job_no = '' OR job_no = '0' THEN 1 ELSE 0 END) as missing_job_count
                FROM job_cards 
                WHERE firm_id = %s
                GROUP BY request_no
                ORDER BY request_no DESC
            """
            
            cursor.execute(query, (self.current_firm_id,))
            results = cursor.fetchall()
            
            db_requests = []
            for row in results:
                request_no, item_count, missing_job_count = row
                db_requests.append({
                    'request_no': request_no,
                    'item_count': item_count,
                    'missing_job_count': missing_job_count,
                    'has_missing_jobs': missing_job_count > 0
                })
            
            cursor.close()
            connection.close()
            
            return db_requests
            
        except Exception as e:
            self.log_job_cards(f"❌ Error getting database requests: {str(e)}")
            return []
    
    def analyze_requests(self, portal_requests, db_requests):
        """Analyze requests and categorize what needs to be done"""
        try:
            # Create lookup dictionaries
            portal_lookup = {req['request_no']: req for req in portal_requests}
            db_lookup = {req['request_no']: req for req in db_requests}
            
            analysis = {
                'need_job_cards': [],      # Portal has "Create Job Card" link
                'need_job_numbers': [],    # Database has missing job numbers
                'in_portal_only': [],      # In portal but not in database
                'in_db_only': [],          # In database but not in portal
                'completed': []            # Has job card and job numbers
            }
            
            # Analyze each portal request
            for request_no, portal_req in portal_lookup.items():
                db_req = db_lookup.get(request_no)
                
                if portal_req['needs_job_card']:
                    # Needs job card creation
                    analysis['need_job_cards'].append(portal_req)
                elif portal_req['has_job_card'] and db_req and db_req['has_missing_jobs']:
                    # Has job card but missing job numbers
                    analysis['need_job_numbers'].append(portal_req)
                elif portal_req['has_job_card'] and (not db_req or not db_req['has_missing_jobs']):
                    # Completed
                    analysis['completed'].append(portal_req)
                
                if not db_req:
                    analysis['in_portal_only'].append(portal_req)
            
            # Find database-only requests
            for request_no, db_req in db_lookup.items():
                if request_no not in portal_lookup:
                    analysis['in_db_only'].append(db_req)
            
            # Log analysis results
            self.log_job_cards(f"📊 Analysis Results:")
            self.log_job_cards(f"   🎯 Need Job Cards: {len(analysis['need_job_cards'])}")
            self.log_job_cards(f"   🔍 Need Job Numbers: {len(analysis['need_job_numbers'])}")
            self.log_job_cards(f"   ✅ Completed: {len(analysis['completed'])}")
            self.log_job_cards(f"   🌐 Portal Only: {len(analysis['in_portal_only'])}")
            self.log_job_cards(f"   💾 Database Only: {len(analysis['in_db_only'])}")
            
            return analysis
            
        except Exception as e:
            self.log_job_cards(f"❌ Error analyzing requests: {str(e)}")
            return {'need_job_cards': [], 'need_job_numbers': [], 'in_portal_only': [], 'in_db_only': [], 'completed': []}
    
    def create_job_cards_batch(self, requests):
        """Create job cards for multiple requests"""
        try:
            created_count = 0
            
            for i, request in enumerate(requests):
                request_no = request['request_no']
                self.log_job_cards(f"🎯 Creating job card for Request {request_no} ({i+1}/{len(requests)})")
                
                if self.create_job_card_for_request_direct(request):
                    created_count += 1
                    self.log_job_cards(f"✅ Successfully created job card for Request {request_no}")
                else:
                    self.log_job_cards(f"❌ Failed to create job card for Request {request_no}")
                
                time.sleep(2)  # Small delay between requests
            
            return created_count
            
        except Exception as e:
            self.log_job_cards(f"❌ Error in batch job card creation: {str(e)}")
            return 0
    
    def fetch_job_numbers_batch(self, requests):
        """Fetch job numbers for multiple requests"""
        try:
            fetched_count = 0
            
            for i, request in enumerate(requests):
                request_no = request['request_no']
                self.log_job_cards(f"🔍 Fetching job numbers for Request {request_no} ({i+1}/{len(requests)})")
                
                if self.fetch_job_numbers_for_request_direct(request_no):
                    fetched_count += 1
                    self.log_job_cards(f"✅ Successfully fetched job numbers for Request {request_no}")
                else:
                    self.log_job_cards(f"❌ Failed to fetch job numbers for Request {request_no}")
                
                time.sleep(1)  # Small delay between requests
            
            return fetched_count
            
        except Exception as e:
            self.log_job_cards(f"❌ Error in batch job number fetching: {str(e)}")
            return 0
    
    def create_job_card_for_request_direct(self, request_data):
        """Create job card for a request - direct method with NEW TAB handling"""
        try:
            request_no = request_data['request_no']
            create_link = request_data['create_link']
            
            if not create_link:
                self.log_job_cards(f"❌ No 'Create Job Card' link found for Request {request_no}")
                return False
            
            # Store original tab handle
            original_tab = self.driver.current_window_handle
            self.log_job_cards(f"🔗 Original tab handle: {original_tab}")
            
            # Get initial tab count
            initial_tabs = self.driver.window_handles
            self.log_job_cards(f"📑 Initial tab count: {len(initial_tabs)}")
            
            self.log_job_cards(f"🔄 Clicking 'Create Job Card' for Request {request_no}...")
            
            # Click the create link using JavaScript for better reliability
            self.driver.execute_script("arguments[0].click();", create_link)
            
            # Wait for new tab to open
            time.sleep(2)  # Reduced from 3 to 2 seconds
            
            # Get updated tab handles
            all_tabs = self.driver.window_handles
            self.log_job_cards(f"📑 Updated tab count: {len(all_tabs)}")
            
            # Find the new tab
            new_tab = None
            for tab in all_tabs:
                if tab not in initial_tabs:
                    new_tab = tab
                    break
            
            if not new_tab:
                self.log_job_cards(f"❌ No new tab opened for Request {request_no}")
                return False
            
            self.log_job_cards(f"🆕 New tab handle: {new_tab}")
            
            # Switch to the new tab
            self.driver.switch_to.window(new_tab)
            self.log_job_cards(f"✅ Switched to new tab for Request {request_no}")
            
            # Wait for page to load and verify we're on the creation page
            time.sleep(2)  # Reduced from 3 to 2 seconds
            
            # Check if we're on the job card creation page
            if not self.verify_job_card_creation_page():
                self.log_job_cards(f"❌ Failed to navigate to job card creation page for Request {request_no}")
                self.driver.close()  # Close the new tab
                self.driver.switch_to.window(original_tab)  # Switch back to original tab
                return False
            
            self.log_job_cards(f"✅ Successfully navigated to job card creation page for Request {request_no}")
            
            # Accept all items on the page
            if not self.accept_all_items_on_page():
                self.log_job_cards(f"❌ Failed to accept items for Request {request_no}")
                self.driver.close()  # Close the new tab
                self.driver.switch_to.window(original_tab)  # Switch back to original tab
                return False
            
            # Add AHC remarks
            if not self.add_ahc_remarks():
                self.log_job_cards(f"❌ Failed to add remarks for Request {request_no}")
                self.driver.close()  # Close the new tab
                self.driver.switch_to.window(original_tab)  # Switch back to original tab
                return False
            
            # Submit the job card
            if not self.submit_job_card():
                self.log_job_cards(f"❌ Failed to submit job card for Request {request_no}")
                self.driver.close()  # Close the new tab
                self.driver.switch_to.window(original_tab)  # Switch back to original tab
                return False
            
            self.log_job_cards(f"✅ Successfully created job card for Request {request_no}")
            
            # Close the new tab and switch back to original tab
            self.driver.close()
            self.driver.switch_to.window(original_tab)
            self.log_job_cards(f"🔄 Closed new tab and switched back to original tab")
            
            return True
            
        except Exception as e:
            self.log_job_cards(f"❌ Error creating job card for Request {request_no}: {str(e)}")
            # Try to switch back to original tab if possible
            try:
                self.driver.switch_to.window(original_tab)
            except:
                pass
            return False
    
    def verify_job_card_creation_page(self):
        """Verify we're on the job card creation page"""
        try:
            # Wait a bit for page to fully load
            time.sleep(1.5)  # Reduced from 2 to 1.5 seconds
            
            # Check current URL
            current_url = self.driver.current_url
            self.log_job_cards(f"🔍 Current URL: {current_url}")
            
            # Look for key elements that indicate we're on the creation page
            indicators = [
                "Jeweller Item Declaration Details",
                "AHC QM Remarks",
                "Submit",
                "Accept"
            ]
            
            page_text = self.driver.page_source
            
            found_indicators = []
            for indicator in indicators:
                if indicator in page_text:
                    found_indicators.append(indicator)
            
            if found_indicators:
                self.log_job_cards(f"✅ Found page indicators: {found_indicators}")
            
            # Check for specific elements with more detailed logging
            elements_found = []
            
            try:
                # Look for the remarks textarea
                remarks_element = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.ID, "RemarksQM"))
                )
                elements_found.append("RemarksQM textarea")
                self.log_job_cards(f"✅ Found RemarksQM textarea")
            except Exception as e:
                self.log_job_cards(f"⚠️ RemarksQM textarea not found: {str(e)}")
            
            try:
                # Look for the submit button
                submit_element = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.ID, "save"))
                )
                elements_found.append("Submit button")
                self.log_job_cards(f"✅ Found Submit button")
            except Exception as e:
                self.log_job_cards(f"⚠️ Submit button not found: {str(e)}")
            
            try:
                # Look for accept checkboxes
                accept_checkboxes = self.driver.find_elements(By.XPATH, "//input[@name='acceptcheckbyQM']")
                if accept_checkboxes:
                    elements_found.append(f"{len(accept_checkboxes)} accept checkboxes")
                    self.log_job_cards(f"✅ Found {len(accept_checkboxes)} accept checkboxes")
                else:
                    self.log_job_cards(f"⚠️ No accept checkboxes found")
            except Exception as e:
                self.log_job_cards(f"⚠️ Error finding accept checkboxes: {str(e)}")
            
            # Consider page verified if we have key elements or indicators
            is_verified = len(elements_found) >= 2 or len(found_indicators) >= 2
            
            if is_verified:
                self.log_job_cards(f"✅ Page verification successful - Found: {elements_found + found_indicators}")
            else:
                self.log_job_cards(f"❌ Page verification failed - Found: {elements_found + found_indicators}")
            
            return is_verified
            
        except Exception as e:
            self.log_job_cards(f"⚠️ Error verifying job card creation page: {str(e)}")
            return False
    
    def fetch_job_numbers_for_request_direct(self, request_no):
        """Fetch job numbers for a specific request - direct method"""
        try:
            # Navigate to QM Completed List
            completed_url = "https://huid.manakonline.in/MANAK/qualityManagerDesk_ListCompleted?hmType=HMQM"
            self.driver.get(completed_url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(2)
            
            # Extract job numbers from completed list
            job_numbers = self.extract_job_numbers_from_completed_table(request_no)
            
            if job_numbers:
                # Update database with job numbers
                self.update_database_with_job_numbers_direct(request_no, job_numbers)
                return True
            else:
                self.log_job_cards(f"⚠️ No job numbers found for Request {request_no}")
                return False
                
        except Exception as e:
            self.log_job_cards(f"❌ Error fetching job numbers for Request {request_no}: {str(e)}")
            return False
    
    def update_database_with_job_numbers_direct(self, request_no, job_numbers):
        """Update database with job numbers for a specific request"""
        try:
            connection = self.get_database_connection()
            if not connection:
                self.log_job_cards(f"❌ Database connection failed for Request {request_no}")
                return False
            
            cursor = connection.cursor()
            
            # Update job numbers for the specific request
            for job_no in job_numbers:
                update_query = """
                    UPDATE job_cards 
                    SET job_no = %s, updated_at = NOW()
                    WHERE request_no = %s AND firm_id = %s AND (job_no IS NULL OR job_no = '' OR job_no = '0')
                    LIMIT 1
                """
                cursor.execute(update_query, (job_no, request_no, self.current_firm_id))
            
            connection.commit()
            updated_count = cursor.rowcount
            cursor.close()
            connection.close()
            
            self.log_job_cards(f"✅ Updated {updated_count} records with job numbers for Request {request_no}")
            return updated_count > 0
            
        except Exception as e:
            self.log_job_cards(f"❌ Error updating database for Request {request_no}: {str(e)}")
            return False
    
    def run_unified_workflow_manual(self):
        """Run unified workflow manually (for testing/debugging)"""
        try:
            # Check if another process is already running
            if self.is_processing:
                self.log_job_cards("⚠️ Another process is already running. Please wait...")
                return
            
            self.log_job_cards("🚀 Starting manual unified workflow...")
            
            # Run in a separate thread
            threading.Thread(target=self._run_unified_workflow_worker, daemon=True).start()
            
        except Exception as e:
            self.log_job_cards(f"❌ Error starting manual workflow: {str(e)}")
    
    def _run_unified_workflow_worker(self):
        """Worker thread for manual unified workflow"""
        try:
            self.is_processing = True
            self.update_job_cards_status("Running Unified Workflow", 'info')
            
            success = self.run_unified_qm_workflow()
            
            if success:
                self.log_job_cards("✅ Manual unified workflow completed successfully")
                self.update_job_cards_status("Completed", 'success')
            else:
                self.log_job_cards("⚠️ Manual unified workflow completed with issues")
                self.update_job_cards_status("Completed with issues", 'warning')
            
        except Exception as e:
            self.log_job_cards(f"❌ Manual workflow error: {str(e)}")
            self.update_job_cards_status("Error", 'danger')
        finally:
            self.is_processing = False
    
    def _countdown_timer(self, seconds):
        """Display countdown timer until next check"""
        try:
            for remaining in range(seconds, 0, -1):
                if not self.job_cards_monitoring:
                    break
                
                # Update timer label
                mins = remaining // 60
                secs = remaining % 60
                if hasattr(self, 'monitor_timer_label'):
                    self.monitor_timer_label.config(text=f"⏱️ Next check: {mins}:{secs:02d}")
                
                time.sleep(1)
            
            # Reset timer display
            if hasattr(self, 'monitor_timer_label') and self.job_cards_monitoring:
                self.monitor_timer_label.config(text="⏱️ Checking now...")
        except Exception as e:
            self.log_job_cards(f"⚠️ Timer display error: {str(e)}")
    
    def fetch_missing_job_numbers(self):
        """Fetch missing job numbers for all records"""
        # Check if another process is already running
        if self.is_processing:
            self.log_job_cards("⚠️ Another job number fetching process is already running. Please wait...")
            return
        
        threading.Thread(target=self._fetch_missing_job_numbers_worker, daemon=True).start()
    
    def _fetch_missing_job_numbers_worker(self):
        """Worker thread for fetching missing job numbers with progress updates"""
        try:
            # Check if another process is already running
            if self.is_processing:
                self.log_job_cards("⚠️ Another job number fetching process is already running. Skipping auto-monitor.")
                return
            
            # Acquire lock to prevent conflicts
            with self.process_lock:
                self.is_processing = True
                self.update_job_cards_status("Fetching job numbers...", 'warning')
                self.update_progress(5, "Starting job number fetch...")
                
                try:
                    connection = self.get_database_connection()
                    if not connection:
                        self.update_job_cards_status("Database Error", 'danger')
                        self.update_progress(0, "Database connection failed")
                        return
                    
                    cursor = connection.cursor()
                    self.update_progress(10, "Connected to database, querying records...")
                    
                    # Get all records without job_no (filtered by firm_id)
                    query = """
                        SELECT id, request_no, item, pcs, purity, weight
                        FROM job_cards 
                        WHERE firm_id = %s AND (job_no IS NULL OR job_no = '' OR job_no = '0')
                        ORDER BY request_no, id
                    """
                    
                    cursor.execute(query, (self.current_firm_id,))
                    results = cursor.fetchall()
                    
                    if not results:
                        self.log_job_cards("✅ No records found without job numbers")
                        self.update_job_cards_status("No records to process", 'info')
                        self.update_progress(100, "No records found")
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
                    
                    self.log_job_cards(f"🔍 Found {total_requests} unique request numbers to process")
                    self.update_progress(20, f"Found {total_requests} requests to process...")
                    
                    for request_no, items in request_groups.items():
                        processed_requests += 1
                        progress = 20 + (processed_requests / total_requests) * 70
                        self.update_progress(progress, f"Processing Request {request_no} ({processed_requests}/{total_requests})...")
                        self.log_job_cards(f"📋 Processing Request No: {request_no} ({processed_requests}/{total_requests}) - {len(items)} items")
                        self.fetch_job_numbers_for_request(request_no, items)
                    
                    cursor.close()
                    connection.close()
                    
                    self.update_progress(95, "Updating display...")
                    # Reload data to show updated results
                    self.load_job_cards_data()
                    
                finally:
                    # Always release the lock
                    self.is_processing = False
                    self.update_job_cards_status("Job number fetch completed", 'success')
                    self.update_progress(100, "Job number fetch completed successfully")
                    self.log_job_cards("✅ Job number fetching process completed")
            
        except Exception as e:
            self.log_job_cards(f"❌ Error fetching job numbers: {str(e)}")
            self.update_job_cards_status("Error occurred", 'danger')
            self.update_progress(0, "Error occurred during processing")
            self.is_processing = False
    
    def fetch_job_numbers_for_request(self, request_no, items):
        """Fetch job numbers for a specific request by scraping the main QM list page - OPTIMIZED"""
        try:
            if not self.driver:
                self.log_job_cards("❌ Browser not available for job number fetching")
                return
            
            self.log_job_cards(f"🌐 Navigating to QM list for Request {request_no}...")
            
            # Navigate to QM list page
            qm_list_url = "https://huid.manakonline.in/MANAK/qualityManagerDesk_ListCompleted?hmType=HMQM"
            self.driver.get(qm_list_url)
            
            # Optimized wait - use WebDriverWait instead of time.sleep
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            try:
                # Wait for page to load with timeout
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                self.log_job_cards(f"✅ QM list page loaded for Request {request_no}")
            except Exception as e:
                self.log_job_cards(f"⚠️ Page load timeout for Request {request_no}: {str(e)}")
                return
            
            # Find the request in the list - OPTIMIZED
            request_found = False
            try:
                # Look for the request number in the table with timeout
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, f"//td[contains(text(), '{request_no}')]"))
                )
                request_found = True
                self.log_job_cards(f"✅ Found Request {request_no} in QM list")
            except Exception:
                self.log_job_cards(f"⚠️ Request {request_no} not found in QM list")
                return
            
            if not request_found:
                return
            
            # NEW APPROACH: Extract job numbers and item categories from the main QM list page
            self.extract_job_data_from_qm_list(request_no, items)
            
        except Exception as e:
            self.log_job_cards(f"❌ Error fetching job numbers for Request {request_no}: {str(e)}")
    
    def extract_job_data_from_qm_list(self, request_no, items):
        """Extract job numbers from QM list and get item categories from individual job card pages"""
        try:
            # Find all rows containing the request number
            request_rows = self.driver.find_elements(By.XPATH, f"//tr[.//td[contains(text(), '{request_no}')]]")
            
            if not request_rows:
                self.log_job_cards(f"⚠️ No rows found for Request {request_no}")
                return
            
            self.log_job_cards(f"🔍 Found {len(request_rows)} rows for Request {request_no}")
            
            # Extract job card URLs from each row
            job_card_urls = []
            
            for i, row in enumerate(request_rows):
                try:
                    # Look for "QM Job Card View" links in this row
                    job_card_links = row.find_elements(By.XPATH, ".//a[contains(text(), 'QM Job Card View')]")
                    
                    for link in job_card_links:
                        href = link.get_attribute('href')
                        if href:
                            # Check if this URL contains our request number (plain text or Base64 encoded)
                            request_found_in_url = False
                            
                            # Method 1: Check for plain text request number
                            if request_no in href:
                                request_found_in_url = True
                            
                            # Method 2: Check for Base64 encoded request number
                            if not request_found_in_url and 'eRequestId=' in href:
                                try:
                                    encoded_request_id = href.split('eRequestId=')[1].split('&')[0]
                                    decoded_request_id = base64.b64decode(encoded_request_id).decode('utf-8')
                                    if decoded_request_id == request_no:
                                        request_found_in_url = True
                                        self.log_job_cards(f"🔍 Found Base64 encoded request {request_no} as {encoded_request_id}")
                                except Exception as decode_error:
                                    self.log_job_cards(f"⚠️ Could not decode eRequestId: {str(decode_error)}")
                            
                            if request_found_in_url:
                                job_card_urls.append(href)
                                self.log_job_cards(f"✅ Found job card URL in row {i+1}: {href}")
                            else:
                                self.log_job_cards(f"⚠️ Skipped URL in row {i+1} (doesn't contain request {request_no})")
                
                except Exception as e:
                    self.log_job_cards(f"❌ Error processing row {i+1}: {str(e)}")
                    continue
            
            self.log_job_cards(f"🔗 Collected {len(job_card_urls)} job card URLs to process")
            
            if not job_card_urls:
                self.log_job_cards(f"⚠️ No job card URLs found for Request {request_no}")
                return
            
            # Process each job card URL individually to get job number and item category - OPTIMIZED
            processed_job_numbers = set()
            
            for i, url in enumerate(job_card_urls):
                try:
                    self.log_job_cards(f"🔍 Processing job card {i+1}/{len(job_card_urls)}")
                    
                    # Navigate to the job card page
                    self.driver.get(url)
                    
                    # Optimized wait - use WebDriverWait instead of time.sleep
                    try:
                        WebDriverWait(self.driver, 8).until(
                            EC.presence_of_element_located((By.TAG_NAME, "body"))
                        )
                    except Exception as e:
                        self.log_job_cards(f"⚠️ Page load timeout for job card {i+1}: {str(e)}")
                        continue
                    
                    # Extract job number from page content
                    job_no = self.extract_job_no_from_page_content()
                    if not job_no:
                        self.log_job_cards(f"⚠️ Could not extract job number from page")
                        continue
                    
                    # Extract item category from the page
                    item_category = self.extract_item_category_from_page()
                    if item_category:
                        self.log_job_cards(f"📋 Found on page: {item_category} → Job No: {job_no}")
                        
                        # Update database immediately for this specific job card
                        job_id = self.update_single_job_number_in_database(request_no, items, job_no, item_category, processed_job_numbers)
                        
                        # NEW: Extract and store HUID tags from the table
                        if job_id:
                            self.log_job_cards(f"🏷️ Extracting HUID tags for Job No: {job_no}...")
                            huid_tags = self.extract_huid_tags_from_table()
                            
                            if huid_tags:
                                # Insert HUID tags into huid_data table
                                inserted = self.insert_huid_data_batch(
                                    job_id=job_id,
                                    job_no=job_no,
                                    request_no=request_no,
                                    huid_tags=huid_tags,
                                    firm_id=self.current_firm_id
                                )
                                self.log_job_cards(f"✅ Stored {inserted} HUID tags for Job {job_no}")
                            else:
                                self.log_job_cards(f"⚠️ No HUID tags found for Job {job_no}")
                        else:
                            self.log_job_cards(f"⚠️ Could not get job_id for HUID tag storage")
                    else:
                        self.log_job_cards(f"⚠️ Could not extract item category for job {job_no}")
                    
                except Exception as e:
                    self.log_job_cards(f"❌ Error processing job card URL: {str(e)}")
                    continue
            
        except Exception as e:
            self.log_job_cards(f"❌ Error extracting job data from QM list: {str(e)}")
    
    def extract_job_no_from_url(self, url):
        """Extract job number from URL (legacy method)"""
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
            self.log_job_cards(f"❌ Error extracting job number from URL: {str(e)}")
            return None
    
    def extract_job_no_from_page_content(self):
        """Extract job number from current page content"""
        try:
            # Get the page source and visible text
            page_text = self.driver.page_source
            visible_text = self.driver.find_element(By.TAG_NAME, "body").text
            
            import re
            
            # Method 1: Look for "Job Card No:" pattern in visible text
            # Based on your page content: "Job Card No:122116439"
            self.log_job_cards(f"🔍 Searching for job number in page text...")
            
            job_card_patterns = [
                r'Job Card No:\s*(\d{8,})',
                r'Job Card No\.\s*(\d{8,})',
                r'Job Card Number:\s*(\d{8,})',
                r'Job Card Number\.\s*(\d{8,})'
            ]
            
            for pattern in job_card_patterns:
                matches = re.findall(pattern, visible_text, re.IGNORECASE)
                if matches:
                    job_no = matches[0]
                    self.log_job_cards(f"📋 Found job number from Job Card pattern: {job_no}")
                    return job_no
            
            # Method 2: Look for job number using the exact HTML structure
            # Based on your HTML: <div class="col-md-4 bold">Job Card No:</div><div class="col-md-8"> 122116439 </div>
            try:
                # Find the "Job Card No:" label and get its next sibling
                job_card_label = self.driver.find_element(By.XPATH, "//div[contains(@class, 'col-md-4') and contains(@class, 'bold') and contains(text(), 'Job Card No')]")
                
                # Get the next sibling div with col-md-8 class
                job_number_element = job_card_label.find_element(By.XPATH, "./following-sibling::div[contains(@class, 'col-md-8')]")
                
                job_no = job_number_element.text.strip()
                if job_no.isdigit() and len(job_no) >= 8:
                    self.log_job_cards(f"📋 Found job number using exact HTML structure: {job_no}")
                    return job_no
                    
            except Exception as e:
                self.log_job_cards(f"⚠️ Could not find job number using exact structure: {str(e)}")
            
            # Method 3: Alternative selectors for job numbers
            job_no_selectors = [
                "//div[contains(@class, 'col-md-8') and text()[normalize-space()]]",
                "//span[contains(text(), 'Job Card')]/following-sibling::*",
                "//td[contains(text(), 'Job Card')]/following-sibling::td",
                "//label[contains(text(), 'Job Card')]/following-sibling::*"
            ]
            
            for selector in job_no_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        text = element.text.strip()
                        if text.isdigit() and len(text) >= 8:
                            self.log_job_cards(f"📋 Found job number in element: {text}")
                            return text
                except:
                    continue
            
            # Method 3: Look for all 8+ digit numbers and filter out request numbers
            all_numbers = re.findall(r'\b(\d{8,})\b', visible_text)
            
            # Filter out common request number patterns and keep job numbers
            for number in all_numbers:
                if len(number) >= 8:  # Job numbers are usually 8+ digits
                    # Skip if it looks like a request number (usually starts with specific patterns)
                    if not number.startswith('115') and not number.startswith('114'):  # Common request number prefixes
                        self.log_job_cards(f"📋 Found potential job number: {number}")
                        return number
            
            # Method 4: Try to extract from URL parameters
            current_url = self.driver.current_url
            if 'eJobCard=' in current_url:
                encoded_job_no = current_url.split('eJobCard=')[1].split('&')[0]
                try:
                    decoded_bytes = base64.b64decode(encoded_job_no)
                    job_no = decoded_bytes.decode('utf-8')
                    self.log_job_cards(f"📋 Found job number in URL parameter: {job_no}")
                    return job_no
                except Exception as e:
                    self.log_job_cards(f"⚠️ Could not decode job number from URL: {str(e)}")
            
            # Method 5: Look for any 8+ digit number that's not the request number
            # Get the request number from the page to exclude it
            request_patterns = [
                r'Request No[\.:]?\s*(\d{8,})',
                r'Request Number[\.:]?\s*(\d{8,})'
            ]
            
            request_no = None
            for pattern in request_patterns:
                matches = re.findall(pattern, visible_text, re.IGNORECASE)
                if matches:
                    request_no = matches[0]
                    break
            
            # Find all 8+ digit numbers and exclude the request number
            all_numbers = re.findall(r'\b(\d{8,})\b', visible_text)
            for number in all_numbers:
                if len(number) >= 8 and number != request_no:
                    self.log_job_cards(f"📋 Found job number (excluding request): {number}")
                    return number
            
            self.log_job_cards(f"⚠️ No job number found on page")
            return None
            
        except Exception as e:
            self.log_job_cards(f"❌ Error extracting job number from page: {str(e)}")
            return None
    
    def extract_item_category_from_page(self):
        """Extract item category from job card page - COMPLETELY REWRITTEN"""
        try:
            # Get the full page text for debugging
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            self.log_job_cards(f"🔍 DEBUG: Page contains text: {page_text[:200]}...")
            
            # Method 1: Look for item category in the table rows (most reliable)
            table_rows = self.driver.find_elements(By.XPATH, "//table//tr")
            
            for i, row in enumerate(table_rows):
                try:
                    cells = row.find_elements(By.XPATH, ".//td")
                    
                    # Look for "Item Category" column header first
                    if i == 0:  # Header row
                        item_category_col_index = None
                        for j, cell in enumerate(cells):
                            if "item category" in cell.text.lower():
                                item_category_col_index = j
                                break
                        continue
                    
                    # If we found the Item Category column, extract from that specific cell
                    if len(cells) > 1:  # Skip header rows with single cell
                        # Look for cells that contain item category text
                        for cell in cells:
                            cell_text = cell.text.strip()
                            # Skip empty cells, numbers, and common non-category text
                            if (cell_text and 
                                not cell_text.isdigit() and 
                                not cell_text.lower() in ['accepted', 'pending', 'rejected', 'n/a', 'yes', 'no'] and
                                len(cell_text) < 50 and  # Reasonable length for item category
                                not any(common_word in cell_text.lower() for common_word in ['grams', 'weight', 'purity', 'quantity', 'date', 'time'])):
                                
                                # This looks like an item category
                                self.log_job_cards(f"📋 Found item category in table row {i}: {cell_text}")
                                return cell_text
                except Exception as e:
                    continue
            
            # Method 2: Look for item category in specific table cells with item details
            item_detail_cells = self.driver.find_elements(By.XPATH, "//td[contains(@class, 'item') or contains(text(), 'Item') or contains(text(), 'Category')]")
            
            for cell in item_detail_cells:
                try:
                    cell_text = cell.text.strip()
                    item_categories = ['Ring', 'Chain', 'Earrings', 'Earings', 'Bangles', 'Bangle', 'Necklace', 'Bracelet', 'Set + Earring', 'Set', 'Mix']
                    
                    for category in item_categories:
                        if category.lower() in cell_text.lower():
                            self.log_job_cards(f"📋 Found item category in item detail cell: {category}")
                            return category
                except Exception as e:
                    continue
            
            # Method 3: Look for item category in the main content area
            content_area = self.driver.find_element(By.TAG_NAME, "body")
            content_text = content_area.text
            
            # Split content into lines and look for item categories
            lines = content_text.split('\n')
            
            for line in lines:
                line = line.strip()
                if len(line) > 0:
                    item_categories = ['Ring', 'Chain', 'Earrings', 'Earings', 'Bangles', 'Bangle', 'Necklace', 'Bracelet', 'Set + Earring', 'Set', 'Mix']
                    
                    for category in item_categories:
                        if category.lower() == line.lower():
                            self.log_job_cards(f"📋 Found item category in content line: {category}")
                            return category
            
            # Method 4: Look for item category in form elements
            form_elements = self.driver.find_elements(By.XPATH, "//input | //select | //textarea")
            
            for element in form_elements:
                try:
                    # Get the label or nearby text for this form element
                    element_id = element.get_attribute('id') or ''
                    element_name = element.get_attribute('name') or ''
                    
                    if 'item' in element_id.lower() or 'item' in element_name.lower():
                        # Find the label for this element
                        try:
                            label = self.driver.find_element(By.XPATH, f"//label[@for='{element_id}']")
                            label_text = label.text.strip()
                            
                            item_categories = ['Ring', 'Chain', 'Earrings', 'Earings', 'Bangles', 'Bangle', 'Necklace', 'Bracelet', 'Set + Earring', 'Set', 'Mix']
                            
                            for category in item_categories:
                                if category.lower() in label_text.lower():
                                    self.log_job_cards(f"📋 Found item category in form label: {category}")
                                    return category
                        except:
                            pass
                except Exception as e:
                    continue
            
            # Method 5: Look for item category in the page title or headers
            try:
                page_title = self.driver.title
                item_categories = ['Ring', 'Chain', 'Earrings', 'Earings', 'Bangles', 'Bangle', 'Necklace', 'Bracelet', 'Set + Earring', 'Set', 'Mix']
                
                for category in item_categories:
                    if category.lower() in page_title.lower():
                        self.log_job_cards(f"📋 Found item category in page title: {category}")
                        return category
            except:
                pass
            
            # Method 6: Look for item category in the URL
            try:
                current_url = self.driver.current_url
                item_categories = ['Ring', 'Chain', 'Earrings', 'Earings', 'Bangles', 'Bangle', 'Necklace', 'Bracelet', 'Set + Earring', 'Set', 'Mix']
                
                for category in item_categories:
                    if category.lower() in current_url.lower():
                        self.log_job_cards(f"📋 Found item category in URL: {category}")
                        return category
            except:
                pass
            
            # Method 7: Fallback - look for any text that could be an item category
            all_text = self.driver.find_element(By.TAG_NAME, "body").text
            
            # Look for common jewelry item patterns
            jewelry_patterns = [
                r'\b(ring|chain|earring|bangle|necklace|bracelet|pendent|pendant|jhumki|jhumka|set|mix)\b',
                r'\b(bangles?|earrings?|chains?|rings?|pendents?|pendants?|jhumkis?|jhumkas?)\b'
            ]
            
            import re
            for pattern in jewelry_patterns:
                matches = re.findall(pattern, all_text.lower())
                if matches:
                    # Return the first match (most likely the item category)
                    category = matches[0].title()  # Capitalize first letter
                    self.log_job_cards(f"📋 Found item category in page text (pattern match): {category}")
                    return category
            
            # Final fallback - look for any word that could be an item category
            words = all_text.split()
            for word in words:
                word_clean = word.strip('.,!?;:()[]{}').lower()
                # Check if it's a reasonable item category (not too long, not a number, not common words)
                if (len(word_clean) >= 3 and len(word_clean) <= 20 and 
                    not word_clean.isdigit() and
                    not word_clean in ['the', 'and', 'for', 'with', 'from', 'this', 'that', 'they', 'have', 'been', 'will', 'would', 'could', 'should']):
                    
                    # Check if it appears in a context that suggests it's an item category
                    word_context = all_text.lower()
                    if word_clean in word_context:
                        # Look for surrounding context
                        word_index = word_context.find(word_clean)
                        context_before = word_context[max(0, word_index-20):word_index]
                        context_after = word_context[word_index:word_index+20]
                        
                        # If it's near words like "category", "item", "type", it's likely an item category
                        if any(keyword in context_before or keyword in context_after for keyword in ['category', 'item', 'type', 'jewelry']):
                            self.log_job_cards(f"📋 Found item category in page text (context match): {word_clean.title()}")
                            return word_clean.title()
            
            self.log_job_cards(f"⚠️ No item category found on page")
            return None
            
        except Exception as e:
            self.log_job_cards(f"❌ Error extracting item category: {str(e)}")
            return None
    
    def extract_huid_tags_from_table(self):
        """Extract all HUID tags from the jewellery items table on job card page"""
        try:
            huid_tags = []
            
            # Find the table containing HUID/Tag data
            # Looking for table with columns: S.No, Item Category, Quantity, Purity, Tag Id [AHC], etc.
            self.log_job_cards(f"🔍 Searching for HUID tags table...")
            
            # Find all table rows with id pattern "trTableLogicGen"
            table_rows = self.driver.find_elements(By.XPATH, "//tr[contains(@id, 'trTableLogicGen')]")
            
            if not table_rows:
                self.log_job_cards(f"⚠️ No table rows found with HUID tags")
                return []
            
            self.log_job_cards(f"✅ Found {len(table_rows)} HUID tag rows")
            
            for i, row in enumerate(table_rows):
                try:
                    # Extract data from each row
                    cells = row.find_elements(By.TAG_NAME, "td")
                    
                    if len(cells) < 6:  # Need at least: S.No, Item, Quantity, Purity, Status, Tag Id
                        continue
                    
                    # Table structure (based on portal):
                    # 0: S.No
                    # 1: Item Category
                    # 2: Quantity
                    # 3: Declared Purity
                    # 4: Receiving Desk Status (Accepted/Pending)
                    # 5: Tag Id [AHC] ← THIS IS WHAT WE WANT
                    # 6: AHC Comments
                    # 7: QM Comments
                    # 8: Accept or Not Accept
                    
                    serial_no = cells[0].text.strip() if len(cells) > 0 else ""
                    item_category = cells[1].text.strip() if len(cells) > 1 else ""
                    quantity = cells[2].text.strip() if len(cells) > 2 else ""
                    purity = cells[3].text.strip() if len(cells) > 3 else ""
                    # Skip column 4 (status - contains "Accepted")
                    # Tag ID is in column 5
                    tag_id = cells[5].text.strip() if len(cells) > 5 else ""
                    
                    # Clean up item category (remove extra whitespace and hidden inputs)
                    # Item category might have hidden input values, extract just the visible text
                    if item_category:
                        # Split by newlines and get the actual item name
                        item_lines = [line.strip() for line in item_category.split('\n') if line.strip()]
                        for line in item_lines:
                            # Skip lines that are just numbers or common labels
                            if line and not line.isdigit() and len(line) > 2:
                                item_category = line
                                break
                    
                    # Only add if we have required data
                    if serial_no and purity and tag_id:
                        tag_data = {
                            'serial_no': serial_no,
                            'item_category': item_category,
                            'purity': purity,
                            'tag_id': tag_id
                        }
                        huid_tags.append(tag_data)
                        self.log_job_cards(f"  📋 Row {i+1}: S.No={serial_no}, Item={item_category}, Purity={purity}, Tag={tag_id}")
                    
                except Exception as e:
                    self.log_job_cards(f"⚠️ Error extracting row {i+1}: {str(e)}")
                    continue
            
            self.log_job_cards(f"✅ Extracted {len(huid_tags)} HUID tags from table")
            return huid_tags
            
        except Exception as e:
            self.log_job_cards(f"❌ Error extracting HUID tags: {str(e)}")
            return []
    
    def insert_huid_data_batch(self, job_id, job_no, request_no, huid_tags, firm_id):
        """Insert batch of HUID tags into huid_data table"""
        try:
            if not huid_tags:
                self.log_job_cards(f"⚠️ No HUID tags to insert")
                return 0
            
            connection = self.get_database_connection()
            if not connection:
                self.log_job_cards(f"❌ Could not connect to database for HUID insert")
                return 0
            
            cursor = connection.cursor()
            inserted_count = 0
            
            # SQL insert query
            insert_query = """
                INSERT INTO huid_data 
                (job_id, job_no, request_no, purity, serial_no, tag_no, item, firm_id, date_added)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """
            
            for tag in huid_tags:
                try:
                    values = (
                        job_id,
                        job_no,
                        request_no,
                        tag.get('purity', ''),
                        tag.get('serial_no', ''),
                        tag.get('tag_id', ''),
                        tag.get('item_category', ''),
                        firm_id
                    )
                    
                    cursor.execute(insert_query, values)
                    inserted_count += 1
                    self.log_job_cards(f"  ✅ Inserted HUID: Job={job_no}, Tag={tag.get('tag_id')}, Item={tag.get('item_category')}")
                    
                except Exception as e:
                    self.log_job_cards(f"  ❌ Error inserting tag {tag.get('tag_id')}: {str(e)}")
                    continue
            
            connection.commit()
            cursor.close()
            connection.close()
            
            self.log_job_cards(f"✅ Successfully inserted {inserted_count}/{len(huid_tags)} HUID tags into database")
            return inserted_count
            
        except Exception as e:
            self.log_job_cards(f"❌ Error in batch HUID insert: {str(e)}")
            return 0
    
    
    def update_single_job_number_in_database(self, request_no, items, job_no, item_category, processed_job_numbers):
        """Update database for a single job card page and return the job_id"""
        try:
            # Skip if we've already processed this job number
            if job_no in processed_job_numbers:
                self.log_job_cards(f"⚠️ Job number {job_no} already processed, skipping")
                return None
            
            connection = self.get_database_connection()
            if not connection:
                return None
            
            cursor = connection.cursor()
            updated_count = 0
            matched_job_id = None
            
            # Find the best matching item for this job card
            best_match = None
            best_score = 0
            
            for item in items:
                id_val, req_no, item_name, pcs, purity, weight = item
                
                # Calculate match score based on item name similarity
                score = self.calculate_match_score(item_name, item_category)
                
                if score > best_score:
                    best_match = item
                    best_score = score
            
            # If we found a good match, update the database
            if best_match and best_score > 30:  # Lower threshold for better matching
                id_val, req_no, item_name, pcs, purity, weight = best_match
                
                # Update database
                update_query = "UPDATE job_cards SET job_no = %s WHERE id = %s"
                cursor.execute(update_query, (job_no, id_val))
                updated_count += 1
                processed_job_numbers.add(job_no)
                matched_job_id = id_val  # Store the job_id to return
                
                self.log_job_cards(f"✅ Updated ID {id_val}: {item_name} → Job No {job_no} (matched: {item_category}, score: {best_score})")
            else:
                self.log_job_cards(f"⚠️ No good match found for {item_category} → Job No {job_no}")
                # Show available database items for debugging
                db_items = [item[2] for item in items]  # item_name is at index 2
                self.log_job_cards(f"📋 Available database items: {db_items}")
                self.log_job_cards(f"📋 Portal item category: '{item_category}'")
            
            connection.commit()
            cursor.close()
            connection.close()
            
            return matched_job_id  # Return the job_id for HUID insertions
            
        except Exception as e:
            self.log_job_cards(f"❌ Error updating single job number: {str(e)}")
            return None
    
    def calculate_match_score(self, db_item, portal_item):
        """Calculate match score between database item and portal item"""
        db_item_lower = db_item.lower().strip()
        portal_item_lower = portal_item.lower().strip()
        
        # Exact match
        if db_item_lower == portal_item_lower:
            return 100
        
        # Check if one contains the other
        if db_item_lower in portal_item_lower or portal_item_lower in db_item_lower:
            return 90
        
        # Check for word-level matches
        db_words = set(db_item_lower.split())
        portal_words = set(portal_item_lower.split())
        
        # Calculate word overlap
        common_words = db_words.intersection(portal_words)
        if common_words:
            # Calculate score based on word overlap percentage
            overlap_ratio = len(common_words) / max(len(db_words), len(portal_words))
            return int(70 + (overlap_ratio * 20))  # 70-90 range
        
        # Check for partial word matches (substrings)
        for db_word in db_words:
            for portal_word in portal_words:
                if len(db_word) >= 3 and len(portal_word) >= 3:
                    # Check if one word contains the other
                    if db_word in portal_word or portal_word in db_word:
                        return 60
        
        # Check for character-level similarity (for typos/variations)
        if len(db_item_lower) > 3 and len(portal_item_lower) > 3:
            # Simple character overlap check
            db_chars = set(db_item_lower)
            portal_chars = set(portal_item_lower)
            char_overlap = len(db_chars.intersection(portal_chars))
            total_chars = len(db_chars.union(portal_chars))
            
            if total_chars > 0:
                char_similarity = char_overlap / total_chars
                if char_similarity > 0.7:  # 70% character overlap
                    return 50
        
        return 0
    
    def update_job_numbers_in_database(self, request_no, items, job_mappings):
        """Update job numbers in database"""
        try:
            connection = self.get_database_connection()
            if not connection:
                return
            
            cursor = connection.cursor()
            updated_count = 0
            
            # Create a list of available job numbers for matching
            available_job_numbers = list(job_mappings.values())
            used_job_numbers = set()
            
            for item in items:
                id_val, req_no, item_name, pcs, purity, weight = item
                
                # Find matching job number
                job_no = None
                matched_category = None
                
                # First, try exact category matching
                for category, job_number in job_mappings.items():
                    if self.items_match(item_name, category):
                        job_no = job_number
                        matched_category = category
                        break
                
                # If no exact match and we have available job numbers, use the first available one
                if not job_no and available_job_numbers:
                    for job_number in available_job_numbers:
                        if job_number not in used_job_numbers:
                            job_no = job_number
                            used_job_numbers.add(job_number)
                            matched_category = "auto-assigned"
                            self.log_job_cards(f"🔀 Auto-assigned job number {job_no} to {item_name} (ID: {id_val})")
                            break
                
                if job_no:
                    # Update database
                    update_query = "UPDATE job_cards SET job_no = %s WHERE id = %s"
                    cursor.execute(update_query, (job_no, id_val))
                    updated_count += 1
                    if matched_category != "auto-assigned":
                        self.log_job_cards(f"✅ Updated ID {id_val}: {item_name} → Job No {job_no} (matched: {matched_category})")
                    else:
                        self.log_job_cards(f"✅ Updated ID {id_val}: {item_name} → Job No {job_no}")
                else:
                    self.log_job_cards(f"⚠️ No job number found for {item_name} (ID: {id_val})")
            
            connection.commit()
            cursor.close()
            connection.close()
            
            self.log_job_cards(f"✅ Updated {updated_count} records for Request {request_no}")
            
        except Exception as e:
            self.log_job_cards(f"❌ Error updating database: {str(e)}")
    
    def items_match(self, db_item, portal_item):
        """Check if database item matches portal item"""
        # Direct matching
        if db_item.lower() == portal_item.lower():
            return True
        
        # Special cases and mappings
        mappings = {
            'earings': 'earrings',
            'earring': 'earrings',
            'bangle': 'bangles',
            'set + earring': 'set + earring',
            'set + earrings': 'set + earring',
            'set earring': 'set + earring',
            'set earrings': 'set + earring'
        }
        
        normalized_db = mappings.get(db_item.lower(), db_item.lower())
        normalized_portal = mappings.get(portal_item.lower(), portal_item.lower())
        
        # Also try partial matching for complex categories
        if 'set' in normalized_db.lower() and 'set' in normalized_portal.lower():
            return True
        
        return normalized_db == normalized_portal
    
    def update_job_cards_status(self, status, status_type='info'):
        """Update job cards status label with modern styling"""
        if hasattr(self, 'job_cards_status_label'):
            # Map status types to colors
            color_map = {
                'success': '#28a745',
                'warning': '#ffc107', 
                'danger': '#dc3545',
                'info': '#17a2b8'
            }
            
            color = color_map.get(status_type, '#17a2b8')
            self.job_cards_status_label.config(text=status, foreground=color)
    
    def update_progress(self, value, text=""):
        """Update progress bar and text"""
        if hasattr(self, 'progress_var'):
            self.progress_var.set(value)
        if hasattr(self, 'job_cards_progress_label') and text:
            self.job_cards_progress_label.config(text=text)
    
    def log_job_cards(self, message):
        """Add message to job cards log"""
        timestamp = time.strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        # Update log text area (thread-safe)
        if hasattr(self, 'job_cards_log_text') and self.job_cards_log_text:
            try:
                root = self.notebook.winfo_toplevel()
                root.after(0, lambda: self._update_job_cards_log(log_message))
            except Exception as e:
                print(f"Job cards log error: {e}")
        
        # Also call the main app's log function
        if self.main_log_callback:
            try:
                self.main_log_callback(message, 'job_cards')
            except Exception as e:
                print(f"External job cards log error: {e}")
    
    def _update_job_cards_log(self, log_message):
        """Update job cards log text area from main thread"""
        try:
            if hasattr(self, 'job_cards_log_text') and self.job_cards_log_text:
                self.job_cards_log_text.config(state='normal')
                self.job_cards_log_text.insert(tk.END, log_message)
                self.job_cards_log_text.see(tk.END)
                self.job_cards_log_text.config(state='disabled')
                self.job_cards_log_text.update_idletasks()
        except Exception as e:
            print(f"Job cards log update error: {e}")
    
    # ==========================================
    # JOB CARD CREATION FROM QM RECEIVED LIST
    # ==========================================
    
    def create_job_cards_from_qm_received_list(self):
        """Create job cards from QM Received List and then update jobs"""
        # Check license before automation
        if not self.check_license_before_action("job card creation"):
            return
            
        try:
            if not self.driver:
                self.log_job_cards("❌ Browser not available. Please open browser and login first.")
                messagebox.showwarning("Not Ready", "Please open browser and login first")
                return
            
            self.log_job_cards("🚀 Starting job card creation from QM Received List...")
            threading.Thread(target=self._create_job_cards_worker, daemon=True).start()
            
        except Exception as e:
            self.log_job_cards(f"❌ Error starting job card creation: {str(e)}")
            messagebox.showerror("Error", f"Error starting job card creation: {str(e)}")
    
    def _create_job_cards_worker(self):
        """Worker thread for creating job cards from QM Received List"""
        try:
            self.update_job_cards_status("Fetching QM Received List...", 'warning')
            
            # Step 1: Navigate to QM Received List
            qm_received_url = "https://huid.manakonline.in/MANAK/qualityManagerDesk_List?hmType=HMQM"
            self.log_job_cards(f"🌐 Navigating to QM Received List: {qm_received_url}")
            self.driver.get(qm_received_url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(3)  # Additional wait for table to populate
            
            # Step 2: Extract available requests from the list
            self.log_job_cards("🔍 Extracting requests from QM Received List...")
            requests_data = self.extract_requests_from_qm_received_list()
            
            if not requests_data:
                self.update_job_cards_status("No Requests Found", 'warning')
                self.log_job_cards("⚠️ No requests found in QM Received List")
                messagebox.showinfo("No Data", "No requests found in QM Received List")
                return
            
            self.log_job_cards(f"✅ Found {len(requests_data)} requests in QM Received List")
            
            # Step 3: Create job cards for each request
            created_count = 0
            for i, request_data in enumerate(requests_data):
                request_no = request_data['request_no']
                self.log_job_cards(f"📋 Processing Request {request_no} ({i+1}/{len(requests_data)})")
                self.update_job_cards_status(f"Creating job card for Request {request_no}...", 'info')
                
                if self.create_job_card_for_request(request_data):
                    created_count += 1
                    self.log_job_cards(f"✅ Successfully created job card for Request {request_no}")
                else:
                    self.log_job_cards(f"❌ Failed to create job card for Request {request_no}")
                
                # Small delay between requests
                time.sleep(2)
            
            self.log_job_cards(f"🎉 Job card creation completed! Created {created_count}/{len(requests_data)} job cards")
            
            if created_count > 0:
                # Step 4: Wait a bit for MANAK system to process
                self.update_job_cards_status("Waiting for system to process...", 'warning')
                self.log_job_cards("⏳ Waiting 3 seconds for MANAK system to process job cards...")
                time.sleep(3)  # Reduced from 5 to 3 seconds for faster processing
                
                # Step 5: Now fetch job numbers using direct method (works immediately!)
                self.log_job_cards("🔍 Fetching job numbers using direct method...")
                self.fetch_missing_job_numbers()
            
            self.update_job_cards_status("Job Card Creation Complete", 'success')
            
        except Exception as e:
            self.log_job_cards(f"❌ Error in job card creation worker: {str(e)}")
            self.update_job_cards_status("Error", 'danger')
    
    def extract_requests_from_qm_received_list(self):
        """Extract ALL request data from QM Received List page and show selection UI"""
        try:
            requests_data = []
            
            # Wait for table to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            
            # Find the table containing the requests
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            target_table = None
            
            for table in tables:
                # Look for table with "Create Job Card" links
                if "Create Job Card" in table.text:
                    target_table = table
                    break
            
            if not target_table:
                self.log_job_cards("❌ Could not find requests table")
                return requests_data
            
            # Extract ALL rows from the table (don't filter by database yet)
            rows = target_table.find_elements(By.TAG_NAME, "tr")[1:]  # Skip header row
            
            for row in rows:
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 8:  # Ensure we have enough columns
                        request_no = cells[1].text.strip()  # Request No column
                        request_date = cells[2].text.strip()  # Request Date column
                        job_card_no = cells[3].text.strip()  # Job Card No column
                        jeweller_name = cells[4].text.strip()  # Jeweller Outlet Name
                        jeweller_address = cells[5].text.strip()  # Jeweller Address
                        status = cells[6].text.strip()  # Status column
                        
                        # Look for "Create Job Card" link in Activity Log column
                        activity_cell = cells[7]
                        create_link = None
                        try:
                            create_link = activity_cell.find_element(By.LINK_TEXT, "Create Job Card")
                        except:
                            pass  # No create link means job card already exists
                        
                        if request_no:
                            # Check if this request is in our database
                            in_database = self.is_request_in_database(request_no)
                            
                            requests_data.append({
                                'request_no': request_no,
                                'request_date': request_date,
                                'job_card_no': job_card_no,
                                'jeweller_name': jeweller_name,
                                'jeweller_address': jeweller_address,
                                'status': status,
                                'create_link': create_link,
                                'in_database': in_database,
                                'can_create_job_card': create_link is not None
                            })
                            
                            if create_link:
                                if in_database:
                                    self.log_job_cards(f"✅ Request {request_no} - Ready for job card creation")
                                else:
                                    self.log_job_cards(f"⚠️ Request {request_no} - Not in database, but has create link")
                            else:
                                self.log_job_cards(f"ℹ️ Request {request_no} - Job card already exists")
                            
                except Exception as e:
                    self.log_job_cards(f"⚠️ Error extracting row data: {str(e)}")
                    continue
            
            self.log_job_cards(f"📋 Scraped {len(requests_data)} requests from QM Received List")
            
            # Show selection dialog for user to choose which requests to process
            if requests_data:
                selected_requests = self.show_request_selection_dialog(requests_data)
                return selected_requests
            else:
                self.log_job_cards("⚠️ No requests found in QM Received List")
                return []
            
        except Exception as e:
            self.log_job_cards(f"❌ Error extracting requests from QM list: {str(e)}")
            return []
    
    def is_request_in_database(self, request_no):
        """Check if request number exists in database"""
        try:
            connection = self.get_database_connection()
            if not connection:
                return False
            
            cursor = connection.cursor()
            query = "SELECT COUNT(*) FROM job_cards WHERE request_no = %s AND firm_id = %s"
            cursor.execute(query, (request_no, self.current_firm_id))
            count = cursor.fetchone()[0]
            
            cursor.close()
            connection.close()
            
            return count > 0
            
        except Exception as e:
            self.log_job_cards(f"⚠️ Error checking database for request {request_no}: {str(e)}")
            return False
    
    def show_request_selection_dialog(self, requests_data):
        """Show dialog for user to select which requests to process"""
        try:
            # Create selection dialog
            dialog = tk.Toplevel()
            dialog.title("Select Requests for Job Card Creation")
            dialog.geometry("900x600")
            dialog.transient(self.notebook.winfo_toplevel())
            dialog.grab_set()
            
            # Main frame
            main_frame = ttk.Frame(dialog)
            main_frame.pack(fill='both', expand=True, padx=10, pady=10)
            
            # Title
            title_label = ttk.Label(main_frame, text="🎯 Select Requests for Job Card Creation", 
                                  font=('Segoe UI', 12, 'bold'))
            title_label.pack(pady=(0, 10))
            
            # Filter frame
            filter_frame = ttk.Frame(main_frame)
            filter_frame.pack(fill='x', pady=(0, 10))
            
            # Filter buttons
            ttk.Button(filter_frame, text="✅ In Database", 
                      command=lambda: self.filter_requests_tree(tree, requests_data, 'in_database')).pack(side='left', padx=(0, 5))
            ttk.Button(filter_frame, text="🎯 Can Create Job Card", 
                      command=lambda: self.filter_requests_tree(tree, requests_data, 'can_create_job_card')).pack(side='left', padx=(0, 5))
            ttk.Button(filter_frame, text="🔄 Show All", 
                      command=lambda: self.filter_requests_tree(tree, requests_data, 'all')).pack(side='left', padx=(0, 5))
            
            # Tree frame
            tree_frame = ttk.Frame(main_frame)
            tree_frame.pack(fill='both', expand=True)
            
            # Create treeview
            columns = ('Select', 'Request No', 'Date', 'Jeweller', 'Status', 'Job Card', 'In DB')
            tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)
            
            # Configure columns
            tree.heading('Select', text='☐')
            tree.heading('Request No', text='Request No')
            tree.heading('Date', text='Date')
            tree.heading('Jeweller', text='Jeweller')
            tree.heading('Status', text='Status')
            tree.heading('Job Card', text='Job Card')
            tree.heading('In DB', text='In DB')
            
            tree.column('Select', width=50)
            tree.column('Request No', width=120)
            tree.column('Date', width=100)
            tree.column('Jeweller', width=200)
            tree.column('Status', width=120)
            tree.column('Job Card', width=80)
            tree.column('In DB', width=60)
            
            # Add scrollbar
            scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            
            tree.pack(side='left', fill='both', expand=True)
            scrollbar.pack(side='right', fill='y')
            
            # Populate tree
            self.populate_requests_tree(tree, requests_data)
            
            # Button frame
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill='x', pady=(10, 0))
            
            # Selection buttons
            ttk.Button(button_frame, text="☑ Select All", 
                      command=lambda: self.select_all_requests(tree, True)).pack(side='left', padx=(0, 5))
            ttk.Button(button_frame, text="☐ Deselect All", 
                      command=lambda: self.select_all_requests(tree, False)).pack(side='left', padx=(0, 5))
            ttk.Button(button_frame, text="✅ Select Ready Only", 
                      command=lambda: self.select_ready_requests(tree, requests_data)).pack(side='left', padx=(0, 10))
            
            # Action buttons
            ttk.Button(button_frame, text="🚀 Create Selected Job Cards", 
                      command=lambda: self.process_selected_requests(dialog, tree, requests_data)).pack(side='right', padx=(5, 0))
            ttk.Button(button_frame, text="❌ Cancel", 
                      command=dialog.destroy).pack(side='right')
            
            # Store tree reference for filtering
            self.requests_tree = tree
            
            # Wait for dialog to close
            dialog.wait_window()
            
            return []  # Will be handled by process_selected_requests
            
        except Exception as e:
            self.log_job_cards(f"❌ Error showing selection dialog: {str(e)}")
            return []
    
    def populate_requests_tree(self, tree, requests_data):
        """Populate the requests tree with data"""
        for i, request in enumerate(requests_data):
            status_text = "✅ Ready" if (request['in_database'] and request['can_create_job_card']) else "⚠️ Check"
            in_db_text = "✅ Yes" if request['in_database'] else "❌ No"
            
            tree.insert('', 'end', values=(
                '☐',  # Checkbox
                request['request_no'],
                request['request_date'],
                request['jeweller_name'][:30] + "..." if len(request['jeweller_name']) > 30 else request['jeweller_name'],
                status_text,
                request['job_card_no'],
                in_db_text
            ), tags=('selectable',))
    
    def filter_requests_tree(self, tree, requests_data, filter_type):
        """Filter the requests tree based on criteria"""
        # Clear tree
        for item in tree.get_children():
            tree.delete(item)
        
        filtered_data = []
        if filter_type == 'in_database':
            filtered_data = [r for r in requests_data if r['in_database']]
        elif filter_type == 'can_create_job_card':
            filtered_data = [r for r in requests_data if r['can_create_job_card']]
        else:  # all
            filtered_data = requests_data
        
        self.populate_requests_tree(tree, filtered_data)
    
    def select_all_requests(self, tree, select):
        """Select or deselect all requests"""
        for item in tree.get_children():
            values = list(tree.item(item, 'values'))
            values[0] = '☑' if select else '☐'
            tree.item(item, values=values)
    
    def select_ready_requests(self, tree, requests_data):
        """Select only requests that are ready (in database and can create job card)"""
        for item in tree.get_children():
            values = list(tree.item(item, 'values'))
            request_no = values[1]
            
            # Find the request data
            request_data = next((r for r in requests_data if r['request_no'] == request_no), None)
            
            if request_data and request_data['in_database'] and request_data['can_create_job_card']:
                values[0] = '☑'
            else:
                values[0] = '☐'
            
            tree.item(item, values=values)
    
    def process_selected_requests(self, dialog, tree, requests_data):
        """Process the selected requests"""
        try:
            selected_requests = []
            
            for item in tree.get_children():
                values = tree.item(item, 'values')
                if values[0] == '☑':  # Selected
                    request_no = values[1]
                    # Find the full request data
                    request_data = next((r for r in requests_data if r['request_no'] == request_no), None)
                    if request_data and request_data['can_create_job_card']:
                        selected_requests.append(request_data)
            
            if not selected_requests:
                messagebox.showwarning("No Selection", "Please select at least one request to process.")
                return
            
            self.log_job_cards(f"🎯 Processing {len(selected_requests)} selected requests...")
            
            # Close dialog
            dialog.destroy()
            
            # Process the selected requests
            threading.Thread(target=self._process_selected_requests_worker, 
                           args=(selected_requests,), daemon=True).start()
            
        except Exception as e:
            self.log_job_cards(f"❌ Error processing selected requests: {str(e)}")
    
    def _process_selected_requests_worker(self, selected_requests):
        """Worker thread to process selected requests"""
        try:
            created_count = 0
            
            for i, request_data in enumerate(selected_requests):
                request_no = request_data['request_no']
                self.log_job_cards(f"📋 Processing Request {request_no} ({i+1}/{len(selected_requests)})")
                
                if self.create_job_card_for_request(request_data):
                    created_count += 1
                    self.log_job_cards(f"✅ Successfully created job card for Request {request_no}")
                else:
                    self.log_job_cards(f"❌ Failed to create job card for Request {request_no}")
                
                time.sleep(2)  # Small delay between requests
            
            self.log_job_cards(f"🎉 Completed processing {created_count}/{len(selected_requests)} requests")
            
            if created_count > 0:
                # Wait for system to process
                self.log_job_cards("⏳ Waiting for system to process...")
                time.sleep(5)
                
                # Fetch job numbers
                self.log_job_cards("🔍 Fetching job numbers...")
                self.fetch_job_numbers_from_completed_list()
                
                # Refresh data
                self.load_job_cards_data()
            
        except Exception as e:
            self.log_job_cards(f"❌ Error in process selected requests worker: {str(e)}")
    
    def get_accepted_requests_from_database(self):
        """Get list of accepted request numbers from database"""
        try:
            connection = self.get_database_connection()
            if not connection:
                self.log_job_cards("❌ Could not connect to database")
                return []
            
            cursor = connection.cursor()
            
            # Get firm_id from settings
            firm_id = self.current_firm_id
            
            # Query to get accepted requests (those without job numbers yet)
            query = """
                SELECT DISTINCT request_no 
                FROM job_cards 
                WHERE firm_id = %s 
                AND (job_no IS NULL OR job_no = '' OR job_no = '0')
                ORDER BY request_no
            """
            
            cursor.execute(query, (firm_id,))
            results = cursor.fetchall()
            
            accepted_requests = [row[0] for row in results] if results else []
            
            cursor.close()
            connection.close()
            
            return accepted_requests
            
        except Exception as e:
            self.log_job_cards(f"❌ Error getting accepted requests from database: {str(e)}")
            return []
    
    def create_job_card_for_request(self, request_data):
        """Create job card for a specific request"""
        try:
            request_no = request_data['request_no']
            create_link = request_data['create_link']
            
            self.log_job_cards(f"🔄 Clicking 'Create Job Card' for Request {request_no}...")
            
            # Click the Create Job Card link
            self.driver.execute_script("arguments[0].click();", create_link)
            
            # Wait for the job card creation page to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(2)  # Reduced from 3 to 2 seconds
            
            # Check if we're on the job card creation page
            current_url = self.driver.current_url
            if "QMReceivingUIDJewellerRequest.do" not in current_url:
                self.log_job_cards(f"⚠️ Not on job card creation page for Request {request_no}")
                return False
            
            self.log_job_cards(f"✅ On job card creation page for Request {request_no}")
            
            # Accept all items
            self.log_job_cards(f"✅ Accepting all items for Request {request_no}...")
            self.accept_all_items_on_page()
            
            # Add AHC remarks
            self.log_job_cards(f"📝 Adding AHC remarks for Request {request_no}...")
            self.add_ahc_remarks()
            
            # Submit the job card
            self.log_job_cards(f"🚀 Submitting job card for Request {request_no}...")
            if self.submit_job_card():
                self.log_job_cards(f"✅ Successfully submitted job card for Request {request_no}")
                return True
            else:
                self.log_job_cards(f"❌ Failed to submit job card for Request {request_no}")
                return False
                
        except Exception as e:
            self.log_job_cards(f"❌ Error creating job card for Request {request_no}: {str(e)}")
            return False
    
    def accept_all_items_on_page(self):
        """Accept all items on the job card creation page"""
        try:
            self.log_job_cards(f"🔍 Looking for accept checkboxes...")
            
            # Find all accept checkboxes using the exact name from HTML
            accept_checkboxes = self.driver.find_elements(By.XPATH, "//input[@name='acceptcheckbyQM']")
            
            if not accept_checkboxes:
                self.log_job_cards(f"⚠️ No accept checkboxes found with name 'acceptcheckbyQM'")
                # Try alternative selectors
                alternative_selectors = [
                    "//input[contains(@name, 'accept')]",
                    "//input[@type='checkbox']",
                    "//input[contains(@class, 'accept')]"
                ]
                
                for selector in alternative_selectors:
                    try:
                        checkboxes = self.driver.find_elements(By.XPATH, selector)
                        if checkboxes:
                            accept_checkboxes = checkboxes
                            self.log_job_cards(f"✅ Found {len(checkboxes)} checkboxes using alternative selector: {selector}")
                            break
                    except Exception as e:
                        self.log_job_cards(f"⚠️ Alternative selector {selector} failed: {str(e)}")
            
            if not accept_checkboxes:
                self.log_job_cards(f"⚠️ No accept checkboxes found with any selector")
                return True  # Continue anyway, maybe checkboxes are already checked
            
            self.log_job_cards(f"📋 Found {len(accept_checkboxes)} accept checkboxes")
            
            accepted_count = 0
            for i, checkbox in enumerate(accept_checkboxes):
                try:
                    # Check if checkbox is visible and enabled
                    if checkbox.is_displayed() and checkbox.is_enabled():
                        if not checkbox.is_selected():
                            self.driver.execute_script("arguments[0].click();", checkbox)
                            accepted_count += 1
                            self.log_job_cards(f"✅ Checked accept checkbox {i+1}")
                            time.sleep(0.3)  # Reduced from 0.5 to 0.3 seconds
                        else:
                            # Already checked, count it
                            accepted_count += 1
                            self.log_job_cards(f"ℹ️ Accept checkbox {i+1} already checked")
                    else:
                        self.log_job_cards(f"⚠️ Accept checkbox {i+1} not visible/enabled")
                except Exception as e:
                    self.log_job_cards(f"⚠️ Error clicking checkbox {i+1}: {str(e)}")
                    continue
            
            self.log_job_cards(f"✅ Processed {len(accept_checkboxes)} checkboxes, {accepted_count} items accepted")
            return True
            
        except Exception as e:
            self.log_job_cards(f"❌ Error accepting items: {str(e)}")
            return False
    
    def add_ahc_remarks(self):
        """Add AHC remarks to the job card"""
        try:
            # Look for AHC QM Remarks textarea using the exact ID from HTML
            remarks_field = None
            
            # Try the exact ID first
            try:
                remarks_field = self.driver.find_element(By.ID, "RemarksQM")
                self.log_job_cards("✅ Found AHC remarks field by ID")
            except:
                # Fallback to other selectors
                remarks_selectors = [
                    "textarea[name='RemarksQM']",
                    "//textarea[@placeholder='Enter QM remarks']",
                    "//textarea[contains(@class, 'pcRequiredField')]"
                ]
                
                for selector in remarks_selectors:
                    try:
                        if selector.startswith("//"):
                            remarks_field = self.driver.find_element(By.XPATH, selector)
                        else:
                            remarks_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                        self.log_job_cards(f"✅ Found AHC remarks field using selector: {selector}")
                        break
                    except:
                        continue
            
            if remarks_field:
                # Get the number of items to create a proper remark
                item_count = len(self.driver.find_elements(By.XPATH, "//input[@name='acceptcheckbyQM']"))
                remarks_text = f"All {item_count} pcs ok"
                
                # Clear the field first
                try:
                    remarks_field.clear()
                except:
                    # If clear fails, select all and delete
                    remarks_field.send_keys(Keys.CONTROL + "a")
                    remarks_field.send_keys(Keys.DELETE)
                
                # Enter the remarks
                remarks_field.send_keys(remarks_text)
                self.log_job_cards(f"✅ Added AHC remarks: {remarks_text}")
                return True
            else:
                self.log_job_cards("⚠️ Could not find AHC remarks field (RemarksQM)")
                return False
                
        except Exception as e:
            self.log_job_cards(f"❌ Error adding AHC remarks: {str(e)}")
            return False
    
    def submit_job_card(self):
        """Submit the job card"""
        try:
            # Look for submit button using the exact ID from HTML
            submit_button = None
            
            # Try the exact ID first
            try:
                submit_button = self.driver.find_element(By.ID, "save")
                self.log_job_cards("✅ Found submit button by ID (save)")
            except:
                # Fallback to other selectors
                submit_selectors = [
                    "input[type='button'][value='Submit']",
                    "input[type='submit']",
                    "button[type='submit']",
                    "//input[@value='Submit']",
                    "//button[contains(text(), 'Submit')]",
                    "//input[@id='submit']",
                    "//button[@id='submit']"
                ]
                
                for selector in submit_selectors:
                    try:
                        if selector.startswith("//"):
                            submit_button = self.driver.find_element(By.XPATH, selector)
                        else:
                            submit_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                        self.log_job_cards(f"✅ Found submit button using selector: {selector}")
                        break
                    except:
                        continue
            
            if submit_button:
                self.log_job_cards("🔄 Clicking submit button...")
                self.driver.execute_script("arguments[0].click();", submit_button)
                
                # Wait for submission to complete
                time.sleep(3)
                
                # Check if submission was successful (look for success message or redirect)
                try:
                    WebDriverWait(self.driver, 15).until(
                        lambda driver: "qualityManagerDesk_List" in driver.current_url or 
                                     "success" in driver.page_source.lower() or
                                     "submitted" in driver.page_source.lower() or
                                     "job card" in driver.page_source.lower()
                    )
                    self.log_job_cards("✅ Job card submitted successfully")
                    return True
                except Exception as e:
                    self.log_job_cards(f"⚠️ Submission status unclear, but button was clicked: {str(e)}")
                    # Even if we can't confirm success, the button was clicked
                    return True
            else:
                self.log_job_cards("❌ Could not find submit button (save)")
                return False
                
        except Exception as e:
            self.log_job_cards(f"❌ Error submitting job card: {str(e)}")
            return False
    
    def fetch_job_numbers_from_completed_list(self):
        """Fetch job numbers from QM completed list after creating job cards"""
        try:
            # Navigate to completed list
            completed_url = "https://huid.manakonline.in/MANAK/qualityManagerDesk_ListCompleted?hmType=HMQM"
            self.log_job_cards(f"🌐 Navigating to QM Completed List: {completed_url}")
            self.driver.get(completed_url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(3)
            
            # Extract job numbers from completed list
            self.log_job_cards("🔍 Extracting job numbers from completed list...")
            job_numbers = self.extract_job_numbers_from_completed_table()
            
            if job_numbers:
                self.log_job_cards(f"✅ Found {len(job_numbers)} job numbers in completed list")
                # Update database with job numbers
                self.update_database_with_job_numbers(job_numbers)
            else:
                self.log_job_cards("⚠️ No job numbers found in completed list")
                
        except Exception as e:
            self.log_job_cards(f"❌ Error fetching job numbers from completed list: {str(e)}")
    
    def extract_job_numbers_from_completed_table(self):
        """Extract job numbers from the completed list table"""
        try:
            job_numbers = []
            
            # Find the table containing job numbers
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            target_table = None
            
            for table in tables:
                # Look for table with job numbers
                if "Job Card No" in table.text or "Job No" in table.text:
                    target_table = table
                    break
            
            if not target_table:
                self.log_job_cards("❌ Could not find completed jobs table")
                return job_numbers
            
            # Extract rows from the table
            rows = target_table.find_elements(By.TAG_NAME, "tr")[1:]  # Skip header row
            
            for row in rows:
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 4:  # Ensure we have enough columns
                        request_no = cells[1].text.strip() if len(cells) > 1 else ""
                        job_card_no = cells[3].text.strip() if len(cells) > 3 else ""  # Job Card No column
                        
                        if job_card_no and job_card_no != "NA" and job_card_no.isdigit():
                            job_numbers.append({
                                'request_no': request_no,
                                'job_card_no': job_card_no
                            })
                            
                except Exception as e:
                    self.log_job_cards(f"⚠️ Error extracting job number from row: {str(e)}")
                    continue
            
            return job_numbers
            
        except Exception as e:
            self.log_job_cards(f"❌ Error extracting job numbers: {str(e)}")
            return []
    
    def update_database_with_job_numbers(self, job_numbers):
        """Update database with newly found job numbers"""
        try:
            connection = self.get_database_connection()
            if not connection:
                self.log_job_cards("❌ Could not connect to database")
                return
            
            cursor = connection.cursor()
            updated_count = 0
            
            for job_data in job_numbers:
                request_no = job_data['request_no']
                job_card_no = job_data['job_card_no']
                
                # Update job_cards table with job number
                update_query = """
                    UPDATE job_cards 
                    SET job_no = %s, updated_at = NOW() 
                    WHERE request_no = %s AND (job_no IS NULL OR job_no = '' OR job_no = '0')
                """
                
                cursor.execute(update_query, (job_card_no, request_no))
                if cursor.rowcount > 0:
                    updated_count += 1
                    self.log_job_cards(f"✅ Updated job_cards table: Request {request_no} -> Job {job_card_no}")
            
            connection.commit()
            cursor.close()
            connection.close()
            
            self.log_job_cards(f"🎉 Database update complete! Updated {updated_count} records")
            
            # Refresh the job cards data to show newly created job cards
            if updated_count > 0:
                self.log_job_cards("🔄 Refreshing job cards data...")
                self.load_job_cards_data()
            
        except Exception as e:
            self.log_job_cards(f"❌ Error updating database with job numbers: {str(e)}")
    
    def check_and_create_job_cards_if_needed(self):
        """Check portal and create job cards if needed - returns True if any were created"""
        try:
            if not self.driver:
                self.log_job_cards("❌ Browser not available for job card creation check")
                return False
            
            # Navigate to QM Received List
            qm_received_url = "https://huid.manakonline.in/MANAK/qualityManagerDesk_List?hmType=HMQM"
            self.driver.get(qm_received_url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(2)
            
            # Get accepted requests from database
            accepted_requests = self.get_accepted_requests_from_database()
            if not accepted_requests:
                self.log_job_cards("ℹ️ No accepted requests in database to check")
                return False
            
            self.log_job_cards(f"📋 Checking {len(accepted_requests)} accepted requests in portal...")
            
            # Find requests in portal that need job cards
            requests_needing_cards = self.find_requests_needing_job_cards(accepted_requests)
            
            if requests_needing_cards:
                self.log_job_cards(f"🎯 Found {len(requests_needing_cards)} requests needing job cards")
                # Create job cards for these requests
                created_count = 0
                for request_data in requests_needing_cards:
                    if self.create_job_card_for_request(request_data):
                        created_count += 1
                    time.sleep(2)  # Small delay between requests
                
                self.log_job_cards(f"✅ Created {created_count} job cards")
                return created_count > 0
            else:
                self.log_job_cards("ℹ️ No requests need job card creation")
                return False
                
        except Exception as e:
            self.log_job_cards(f"❌ Error checking for job card creation: {str(e)}")
            return False
    
    def find_requests_needing_job_cards(self, accepted_requests):
        """Find requests in portal that need job cards created"""
        try:
            requests_needing_cards = []
            
            # Wait for table to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            
            # Find the table containing the requests
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            target_table = None
            
            for table in tables:
                if "Create Job Card" in table.text:
                    target_table = table
                    break
            
            if not target_table:
                self.log_job_cards("❌ Could not find requests table")
                return requests_needing_cards
            
            # Extract rows from the table
            rows = target_table.find_elements(By.TAG_NAME, "tr")[1:]  # Skip header row
            
            for row in rows:
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 8:
                        request_no = cells[1].text.strip()
                        
                        # Only process if this request is in our accepted requests
                        if request_no in accepted_requests:
                            # Check if "Create Job Card" link exists (meaning job card not created yet)
                            activity_cell = cells[7]
                            try:
                                create_link = activity_cell.find_element(By.LINK_TEXT, "Create Job Card")
                                if create_link:
                                    request_date = cells[2].text.strip()
                                    jeweller_name = cells[4].text.strip()
                                    status = cells[6].text.strip()
                                    
                                    requests_needing_cards.append({
                                        'request_no': request_no,
                                        'request_date': request_date,
                                        'jeweller_name': jeweller_name,
                                        'status': status,
                                        'create_link': create_link
                                    })
                                    self.log_job_cards(f"🎯 Request {request_no} needs job card creation")
                            except:
                                # No "Create Job Card" link means job card already exists
                                self.log_job_cards(f"ℹ️ Request {request_no} already has job card")
                                
                except Exception as e:
                    self.log_job_cards(f"⚠️ Error checking row: {str(e)}")
                    continue
            
            return requests_needing_cards
            
        except Exception as e:
            self.log_job_cards(f"❌ Error finding requests needing job cards: {str(e)}")
            return []
    
    def fetch_missing_job_numbers_auto(self):
        """Auto-monitor version of fetching missing job numbers"""
        try:
            connection = self.get_database_connection()
            if not connection:
                self.log_job_cards("❌ Could not connect to database for auto-monitor")
                return
            
            cursor = connection.cursor()
            
            # Query for records without job_no (filtered by firm_id)
            query = """
                SELECT id, request_no, item, pcs, purity, weight
                FROM job_cards 
                WHERE firm_id = %s AND (job_no IS NULL OR job_no = '' OR job_no = '0')
                ORDER BY id DESC
                LIMIT 20
            """
            
            cursor.execute(query, (self.current_firm_id,))
            results = cursor.fetchall()
            
            if results:
                self.log_job_cards(f"🔍 Found {len(results)} records without job numbers")
                
                # Group by request_no
                request_groups = {}
                for row in results:
                    id_val, request_no, item, pcs, purity, weight = row
                    if request_no not in request_groups:
                        request_groups[request_no] = []
                    request_groups[request_no].append(row)
                
                # Process each request_no
                for request_no, items in request_groups.items():
                    self.log_job_cards(f"🔍 Auto-processing Request No: {request_no} ({len(items)} items)")
                    self.fetch_job_numbers_for_request(request_no, items)
            else:
                self.log_job_cards("ℹ️ No records need job number fetching")
            
            cursor.close()
            connection.close()
            
        except Exception as e:
            self.log_job_cards(f"❌ Error in auto fetch missing job numbers: {str(e)}")
