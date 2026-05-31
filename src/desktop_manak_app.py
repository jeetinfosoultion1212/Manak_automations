#!/usr/bin/env python3
"""
MANAK Portal Desktop Application
Enhanced Compact UI with Responsive Design - No Scrolling Required
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, UnexpectedAlertPresentException, NoAlertPresentException
import random
import json
import base64
import os
import datetime
try:
    import pandas as pd
except ImportError:
    pass

class LoadingDialog:
    """Custom loading dialog with progress indication"""
    def __init__(self, parent, title="Loading...", message="Please wait..."):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x200")
        self.dialog.configure(bg='#f0f2f5')
        self.dialog.resizable(False, False)
        
        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (200 // 2)
        self.dialog.geometry(f"400x200+{x}+{y}")
        
        # Content
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Spinner/loading icon
        self.spinner_label = tk.Label(main_frame, text="â³", font=('Segoe UI', 24), bg='#f0f2f5')
        self.spinner_label.pack(pady=(0, 10))
        
        # Message
        self.message_label = tk.Label(main_frame, text=message, font=('Segoe UI', 10), 
                                    bg='#f0f2f5', wraplength=350)
        self.message_label.pack(pady=(0, 15))
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate', length=300)
        self.progress.pack(pady=(0, 10))
        self.progress.start(10)
        
        # Status text
        self.status_label = tk.Label(main_frame, text="Initializing...", font=('Segoe UI', 9), 
                                   bg='#f0f2f5', fg='#6c757d')
        self.status_label.pack()
        
        # Cancel button
        self.cancel_btn = ttk.Button(main_frame, text="Cancel", command=self.cancel)
        self.cancel_btn.pack(pady=(10, 0))
        
        self.cancelled = False
        
    def update_status(self, message):
        """Update the status message"""
        self.status_label.config(text=message)
        self.dialog.update()
        
    def update_message(self, message):
        """Update the main message"""
        self.message_label.config(text=message)
        self.dialog.update()
        
    def cancel(self):
        """Cancel the operation"""
        self.cancelled = True
        self.dialog.destroy()
        
    def close(self):
        """Close the dialog"""
        self.dialog.destroy()

class ManakDesktopApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("MANAK Portal Weight Entry Automation | Prosenjit Tech Hub")
        self.root.geometry("1400x900")  # Wider window for better layout
        self.root.configure(bg='#f0f2f5')
        self.root.minsize(1200, 800)  # Minimum size
        self.style = ttk.Style()
        self.setup_styles()
        
        # Automation state
        self.driver = None
        self.logged_in = False
        self.page_loaded = False
        
        # Reception Browser state
        self.reception_driver = None
        
        # All weight entry field IDs from MANAK portal
        self.field_ids = {
            # Sampling Details Section
            'num_scrap_weight': 'num_scrap_weight',
            'buttonweight': 'buttonweight',
            
            # Fire Assaying Details - Strip 1
            'num_strip_weight_M11': 'num_strip_weight_M11',
            'num_silver_weightM11': 'num_silver_weightM11', 
            'num_copper_weightM11': 'num_copper_weightM11',
            'num_lead_weightM11': 'num_lead_weightM11',
            'num_cornet_weightM11': 'num_cornet_weightM11',
            'averagedelta1': 'averagedelta1',
            'num_fineness_reportM11': 'num_fineness_reportM11',
            'num_mean_finenessM11': 'num_mean_finenessM11',
            'str_remarksM11': 'str_remarksM11',
            
            # Fire Assaying Details - Strip 2
            'num_strip_weight_M12': 'num_strip_weight_M12',
            'num_silver_weightM12': 'num_silver_weightM12',
            'num_copper_weightM12': 'num_copper_weightM12', 
            'num_lead_weightM12': 'num_lead_weightM12',
            'num_cornet_weightM12': 'num_cornet_weightM12',
            'num_fineness_report_goldM11': 'num_fineness_report_goldM11',
            
            # C1 (Check Gold)
            'num_strip_weight_goldM11': 'num_strip_weight_goldM11',
            'num_silver_weight_goldM11': 'num_silver_weight_goldM11',
            'num_copper_weight_goldM11': 'num_copper_weight_goldM11',
            'num_lead_weight_goldM11': 'num_lead_weight_goldM11',
            'num_cornet_weight_goldM11': 'num_cornet_weight_goldM11',
            'delta11': 'delta11',
            
            # C2 (Check Gold)
            'num_strip_weight_goldM12': 'num_strip_weight_goldM12',
            'num_silver_weight_goldM12': 'num_silver_weight_goldM12',
            'num_copper_weight_goldM12': 'num_copper_weight_goldM12',
            'num_lead_weight_goldM12': 'num_lead_weight_goldM12',
            'num_cornet_weight_goldM12': 'num_cornet_weight_goldM12',
            'delta22': 'delta22'
        }
        
        self.setup_ui()
        # Load saved settings
        self.load_settings()
        # Clear fields on app start
        self.clear_fields_on_start()
        
        self.log("âœ… Application initialized successfully", 'status')
        
    def setup_styles(self):
        """Setup enhanced custom styles for the application"""
        self.style.theme_use('clam')
        
        # Color scheme
        self.colors = {
            'primary': '#4a90e2',
            'success': '#28a745',
            'danger': '#dc3545',
            'warning': '#ffc107',
            'info': '#17a2b8',
            'light': '#f8f9fa',
            'dark': '#343a40',
            'secondary': '#6c757d',
            'accent': '#9b59b6',
            'bg_main': '#f0f2f5',
            'bg_card': '#ffffff',
            'bg_input': '#f8f9fa',
            'border': '#dee2e6',
            'text_primary': '#212529',
            'text_secondary': '#6c757d'
        }
        
        default_font = ('Segoe UI', 9)
        small_font = ('Segoe UI', 8)
        header_font = ('Segoe UI', 10, 'bold')
        
        # Configure main styles
        self.style.configure('Card.TFrame', background=self.colors['bg_card'], relief='solid', borderwidth=1)
        self.style.configure('Header.TLabel', font=header_font, background=self.colors['bg_card'], foreground=self.colors['text_primary'])
        
        # Compact entry styles
        large_font = ('Segoe UI', 12)
        self.style.configure('Compact.TEntry', 
                           font=large_font, 
                           fieldbackground=self.colors['bg_input'], 
                           borderwidth=1, 
                           relief='solid')
        
        self.style.configure('Success.TEntry', 
                           font=large_font, 
                           fieldbackground='#e8f5e8', 
                           borderwidth=1, 
                           relief='solid')
                           
        self.style.configure('Warning.TEntry', 
                           font=large_font, 
                           fieldbackground='#fff3cd', 
                           borderwidth=1, 
                           relief='solid')
        
        # Button styles - smaller
        self.style.configure('Compact.TButton', 
                           background=self.colors['primary'], 
                           foreground='white', 
                           font=('Segoe UI', 8, 'bold'), 
                           borderwidth=0, 
                           padding=(8, 4))
        
        self.style.configure('Success.TButton', 
                           background=self.colors['success'], 
                           foreground='white', 
                           font=('Segoe UI', 8, 'bold'), 
                           borderwidth=0, 
                           padding=(8, 4))
        
        self.style.configure('Danger.TButton', 
                           background=self.colors['danger'], 
                           foreground='white', 
                           font=('Segoe UI', 8, 'bold'), 
                           borderwidth=0, 
                           padding=(8, 4))
        
        self.style.configure('Info.TButton', 
                           background=self.colors['info'], 
                           foreground='white', 
                           font=('Segoe UI', 8, 'bold'), 
                           borderwidth=0, 
                           padding=(8, 4))
        
        self.style.configure('Warning.TButton', 
                           background=self.colors['warning'], 
                           foreground=self.colors['dark'], 
                           font=('Segoe UI', 8, 'bold'), 
                           borderwidth=0, 
                           padding=(8, 4))
        
        # Notebook styles
        self.style.configure('TNotebook', background=self.colors['bg_main'])
        self.style.configure('TNotebook.Tab', 
                           font=('Segoe UI', 9, 'bold'), 
                           padding=[12, 6], 
                           background=self.colors['secondary'], 
                           foreground='white')
        self.style.map('TNotebook.Tab', 
                      background=[('selected', self.colors['primary'])], 
                      foreground=[('selected', 'white')])
        
        # LabelFrame styles - compact
        self.style.configure('Compact.TLabelframe', 
                           background=self.colors['bg_card'], 
                           relief='solid', 
                           borderwidth=1,
                           bordercolor=self.colors['border'])
        self.style.configure('Compact.TLabelframe.Label', 
                           font=('Segoe UI', 9, 'bold'), 
                           foreground=self.colors['primary'],
                           background=self.colors['bg_card'])
        
        # Add custom style for Submit Manak button
        self.style.configure('SubmitManak.TButton',
            background='#007bff',
            foreground='white',
            font=('Segoe UI', 10, 'bold'),
            borderwidth=0,
            padding=(8, 4))
        self.style.map('SubmitManak.TButton',
            background=[('active', '#0056b3'), ('pressed', '#0056b3'), ('!disabled', '#007bff')],
            foreground=[('active', 'white'), ('pressed', 'white'), ('!disabled', 'white')])
        
    def setup_ui(self):
        """Create the enhanced compact desktop application interface"""
        
        # Main container with padding
        main_container = ttk.Frame(self.root)
        main_container.pack(fill='both', expand=True, padx=8, pady=8)
        # Brand name at the top
        brand_label = ttk.Label(main_container, text="MANAK AUTOMATION", font=('Segoe UI', 14, 'bold'), foreground='#007bff')
        brand_label.pack(pady=(0, 8))
        
        # Main notebook for tabs
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill='both', expand=True)
        
        # Browser Control Tab
        self.setup_browser_tab()
        
        # Weight Entry Tab - NEW COMPACT DESIGN
        self.setup_weight_tab_compact()
        
        # Accept Request Tab - NEW
        self.setup_accept_request_tab()
        
        # Generate Request Tab - NEW
        self.setup_generate_request_tab()
        
        # Settings Tab
        self.setup_settings_tab()
        
    def setup_browser_tab(self):
        """Setup browser control tab with enhanced UI"""
        browser_frame = ttk.Frame(self.notebook)
        self.notebook.add(browser_frame, text="ðŸŒ Browser Control")
        
        # Browser controls card
        control_card = ttk.LabelFrame(browser_frame, text="ðŸŽ›ï¸ Browser Controls", style='Compact.TLabelframe')
        control_card.pack(fill='x', padx=10, pady=(10, 8))
        
        # Button grid
        btn_container = ttk.Frame(control_card)
        btn_container.pack(fill='x', padx=10, pady=10)
        
        # QM Browser Controls
        qm_frame = ttk.LabelFrame(btn_container, text="ðŸ‘¤ QM Browser (Main)", style='Compact.TLabelframe')
        qm_frame.pack(fill='x', pady=(0, 10))
        
        qm_btns = ttk.Frame(qm_frame)
        qm_btns.pack(fill='x', padx=5, pady=5)
        
        self.open_btn = ttk.Button(qm_btns, text="ðŸš€ Open QM Browser", style='Compact.TButton', command=self.open_browser)
        self.open_btn.pack(side='left', padx=(0, 5))
        
        self.login_btn = ttk.Button(qm_btns, text="ðŸ”‘ Login Page", style='Info.TButton', command=self.navigate_to_login, state='disabled')
        self.login_btn.pack(side='left', padx=(0, 5))
        
        self.check_btn = ttk.Button(qm_btns, text="ðŸ” Check Login", style='Success.TButton', command=self.check_login, state='disabled')
        self.check_btn.pack(side='left', padx=(0, 5))
        
        self.close_btn = ttk.Button(qm_btns, text="âŒ Close QM", style='Danger.TButton', command=self.close_browser, state='disabled')
        self.close_btn.pack(side='left')

        # Reception Browser Controls
        rec_frame = ttk.LabelFrame(btn_container, text="ðŸ‘¤ Reception Browser", style='Compact.TLabelframe')
        rec_frame.pack(fill='x')
        
        rec_btns = ttk.Frame(rec_frame)
        rec_btns.pack(fill='x', padx=5, pady=5)
        
        self.open_reception_btn_main = ttk.Button(rec_btns, text="ðŸš€ Open Reception Browser", style='Compact.TButton', command=self.open_reception_browser)
        self.open_reception_btn_main.pack(side='left', padx=(0, 5))
        
        self.close_reception_btn_main = ttk.Button(rec_btns, text="âŒ Close Reception", style='Danger.TButton', command=self.close_reception_browser, state='disabled')
        self.close_reception_btn_main.pack(side='left')
        
        # Status display card
        status_card = ttk.LabelFrame(browser_frame, text="ðŸ“‹ Status Log", style='Compact.TLabelframe')
        status_card.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        self.status_text = scrolledtext.ScrolledText(status_card, height=8, font=('Consolas', 8), 
                                                   bg='#f8f9fa', fg='#495057', wrap=tk.WORD)
        self.status_text.pack(fill='both', expand=True, padx=10, pady=10)
        
    def setup_weight_tab_compact(self):
        """Setup weight entry tab with COMPACT RESPONSIVE design - NO SCROLLING"""
        weight_frame = ttk.Frame(self.notebook)
        self.notebook.add(weight_frame, text="âš–ï¸ Weight Entry")
        
        # Main horizontal layout - Left and Right sections
        main_horizontal = ttk.Frame(weight_frame)
        main_horizontal.pack(fill='both', expand=True, padx=8, pady=8)
        
        # LEFT SECTION - Request Details & Controls (30% width)
        left_section = ttk.Frame(main_horizontal)
        left_section.pack(side='left', fill='y', padx=(0, 8))
        
        # RIGHT SECTION - Weight Entry Table (70% width)
        right_section = ttk.Frame(main_horizontal)
        right_section.pack(side='right', fill='both', expand=True)
        
        # === LEFT SECTION CONTENT ===
        self.setup_left_section(left_section)
        
        # === RIGHT SECTION CONTENT ===
        self.setup_right_section_table(right_section)
        
    def setup_left_section(self, parent):
        """Setup left section with request details and controls"""
        
        # Request details card - COMPACT
        request_card = ttk.LabelFrame(parent, text="ðŸ“‹ Request Details", style='Compact.TLabelframe')
        request_card.pack(fill='x', pady=(0, 8))
        
        # Request form grid - MORE COMPACT
        form_grid = ttk.Frame(request_card)
        form_grid.pack(fill='x', padx=8, pady=8)
        
        # Row 1
        ttk.Label(form_grid, text="Request:", font=('Segoe UI', 8, 'bold')).grid(row=0, column=0, sticky='w', pady=2)
        self.request_entry = ttk.Entry(form_grid, width=15, style='Compact.TEntry', font=('Segoe UI', 10, 'bold'))
        self.request_entry.grid(row=0, column=1, pady=2, padx=(5, 0))
        self.request_entry.insert(0, "110387653")
        
        # Row 2
        ttk.Label(form_grid, text="Job:", font=('Segoe UI', 8, 'bold')).grid(row=1, column=0, sticky='w', pady=2)
        self.job_entry = ttk.Entry(form_grid, width=15, style='Compact.TEntry', font=('Segoe UI', 10, 'bold'))
        self.job_entry.grid(row=1, column=1, pady=2, padx=(5, 0))
        self.job_entry.insert(0, "114647155")
        # Bind to key press for instant response
        self.job_entry.bind('<KeyRelease>', self.on_job_no_key_release)
        self.job_entry.bind('<FocusOut>', self.on_job_no_change)
        self.job_entry.bind('<Return>', self.on_job_no_change)
        
        # Row 3 - Manual Lot Selection
        ttk.Label(form_grid, text="Lot:", font=('Segoe UI', 8, 'bold')).grid(row=2, column=0, sticky='w', pady=2)
        self.manual_lot_var = tk.StringVar(value='1')
        self.manual_lot_combo = ttk.Combobox(form_grid, textvariable=self.manual_lot_var, 
                                           values=['1', '2', '3', '4', '5'], width=12, 
                                           state='readonly', font=('Segoe UI', 10, 'bold'))
        self.manual_lot_combo.grid(row=2, column=1, pady=2, padx=(5, 0))
        
        # Bind lot selection change to apply weights
        self.manual_lot_combo.bind('<<ComboboxSelected>>', self.on_lot_selection_change)
        
        # Auto-load info and manual refresh button
        btn_container = ttk.Frame(request_card)
        btn_container.pack(fill='x', padx=8, pady=(0, 8))
        
        # Info label about auto-loading
        auto_load_info = ttk.Label(btn_container, text="ðŸ“¡ Data loads automatically when Job No is entered", 
                                 font=('Segoe UI', 8, 'italic'), foreground='#666666')
        auto_load_info.pack(fill='x', pady=(0, 2))
        
        # Manual refresh button (smaller, less prominent)
        self.fetch_data_btn = ttk.Button(btn_container, text="ðŸ”„ Refresh Data", style='Secondary.TButton', command=self.fetch_api_data)
        self.fetch_data_btn.pack(fill='x', pady=2)
        
        # Apply lot weights button
        self.apply_weights_btn = ttk.Button(btn_container, text="âš–ï¸ Apply Lot Weights", style='Info.TButton', command=self.apply_current_lot_weights)
        self.apply_weights_btn.pack(fill='x', pady=2)
        
        # Sampling Details card - COMPACT
        sampling_card = ttk.LabelFrame(parent, text="ðŸ·ï¸ Sampling Details", style='Compact.TLabelframe')
        sampling_card.pack(fill='x', pady=(0, 8))
        
        sampling_grid = ttk.Frame(sampling_card)
        sampling_grid.pack(fill='x', padx=8, pady=8)
        
        # Scrap Weight
        ttk.Label(sampling_grid, text="Scrap Wt:", font=('Segoe UI', 8, 'bold')).grid(row=0, column=0, sticky='w', pady=2)
        self.scrap_entry = ttk.Entry(sampling_grid, width=12, style='Compact.TEntry', font=('Segoe UI', 10, 'bold'))
        self.scrap_entry.grid(row=0, column=1, pady=2, padx=(5, 0))
        
        # Button Weight
        ttk.Label(sampling_grid, text="Button Wt:", font=('Segoe UI', 8, 'bold')).grid(row=1, column=0, sticky='w', pady=2)
        self.button_entry = ttk.Entry(sampling_grid, width=12, style='Compact.TEntry', font=('Segoe UI', 10, 'bold'))
        self.button_entry.grid(row=1, column=1, pady=2, padx=(5, 0))
        
        # Lot weights info label
        self.lot_weights_info = ttk.Label(sampling_grid, text="", font=('Segoe UI', 7, 'italic'), foreground='#666666')
        self.lot_weights_info.grid(row=2, column=0, columnspan=2, sticky='w', pady=(2, 0))
        
        # Initialize weight entries dict
        self.weight_entries = {
            'num_scrap_weight': self.scrap_entry,
            'buttonweight': self.button_entry
        }
        
        # Available Lots/Strips card
        self.strip_table_frame = ttk.LabelFrame(parent, text="ðŸ“Š Available Lots", style='Compact.TLabelframe')
        self.strip_table_frame.pack(fill='x', pady=(0, 8))
        
        # Control buttons card - COMPACT
        control_card = ttk.LabelFrame(parent, text="ðŸŽ® Controls", style='Compact.TLabelframe')
        control_card.pack(fill='x', pady=(0, 8))
        
        control_btn_frame = ttk.Frame(control_card)
        control_btn_frame.pack(fill='x', padx=8, pady=8)
        
        # Automated workflow button (renamed and styled)
        self.submit_manak_btn = ttk.Button(control_btn_frame, text="Submit Manak", style='SubmitManak.TButton', command=self.auto_workflow, state='normal')
        self.submit_manak_btn.pack(fill='x', pady=2)
        
        # Restore Clear All button in Controls section
        self.clear_btn = ttk.Button(control_btn_frame, text="ðŸ§¹ Clear All", style='Danger.TButton', command=self.clear_weight_fields)
        self.clear_btn.pack(fill='x', pady=2)
        
        # Compact weight log card
        weight_log_card = ttk.LabelFrame(parent, text="ðŸ“ Entry Log", style='Compact.TLabelframe')
        weight_log_card.pack(fill='both', expand=True)
        
        self.weight_log = scrolledtext.ScrolledText(weight_log_card, height=8, font=('Consolas', 7), 
                                                  bg='#f8f9fa', fg='#495057', wrap=tk.WORD)
        self.weight_log.pack(fill='both', expand=True, padx=8, pady=8)
        
        # Instructions
        instructions = """
ðŸš€ QUICK START:
1. Open Browser â†’ Login
2. Enter Request & Job â†’ Click "Auto Workflow" ðŸš€

ðŸ“¦ LOT SELECTION:
â€¢ Manual: Use dropdown in Request Details
â€¢ API: Use dropdown in Available Lots
â€¢ Auto Workflow: Automatically selects and fills

âš¡ AUTO WORKFLOW:
â€¢ Loads page automatically
â€¢ Fetches API data
â€¢ Selects appropriate lot
â€¢ Fills all fields in UI and portal
â€¢ Brings browser to front
        """.strip()
        
        self.log(instructions)
        
    def setup_right_section_table(self, parent):
        """Setup right section with Fire Assaying table layout matching web interface"""
        
        # Fire Assaying Details card
        fire_card = ttk.LabelFrame(parent, text="ðŸ”¥ Fire Assaying Details", style='Compact.TLabelframe')
        fire_card.pack(fill='both', expand=True, padx=0, pady=0)
        
        # Create table container with padding
        table_container = ttk.Frame(fire_card)
        table_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create the table matching web interface structure
        self.create_fire_assaying_table(table_container)
        
    def create_fire_assaying_table(self, parent):
        """Create the Fire Assaying table matching the web interface exactly"""
        
        # Main table frame
        table_frame = ttk.Frame(parent)
        table_frame.pack(fill='both', expand=True)
        
        # Configure grid weights for responsiveness
        for i in range(10):  # 10 columns
            table_frame.columnconfigure(i, weight=1, minsize=80)
        
        # HEADER ROW
        headers = [
            "S No.", "Initial wt. of\nsample (mg) M1", "Wt.of Silver\n(mg)", 
            "Wt.of Copper\n(mg)", "Weight of Lead\n(gm)", "Wt. of cornet  (mg)\nM2",
            "Delta Values\nâˆ†", "Fineness\nPurity Report", "Mean Fineness\nReport (W)", "Remarks\n(Pass/Fail/Repeat )"
        ]
        
        # Create header row with styling
        for col, header in enumerate(headers):
            header_label = tk.Label(table_frame, text=header, font=('Segoe UI', 8, 'bold'), 
                                  bg='#4a90e2', fg='white', relief='solid', borderwidth=1,
                                  wraplength=100, justify='center')
            header_label.grid(row=0, column=col, sticky='ew', padx=1, pady=1, ipady=8)
        
        # STRIP 1 ROW
        self.create_table_row(table_frame, 1, "Strip 1", {
            'initial': 'num_strip_weight_M11',
            'silver': 'num_silver_weightM11',
            'copper': 'num_copper_weightM11',
            'lead': 'num_lead_weightM11',
            'cornet': 'num_cornet_weightM11',
            'delta': 'averagedelta1',
            'fineness': 'num_fineness_reportM11',
            'mean_fineness': 'num_mean_finenessM11',
            'remarks': 'str_remarksM11'
        }, "Strip1 (W1)", '#e3f2fd')
        
        # STRIP 2 ROW
        self.create_table_row(table_frame, 2, "Strip 2", {
            'initial': 'num_strip_weight_M12',
            'silver': 'num_silver_weightM12',
            'copper': 'num_copper_weightM12',
            'lead': 'num_lead_weightM12',
            'cornet': 'num_cornet_weightM12',
            'delta': None,  # No delta for strip 2
            'fineness': 'num_fineness_report_goldM11',
            'mean_fineness': None,  # No mean fineness for strip 2
            'remarks': None
        }, "Strip2 (W2)", '#fff3e0')
        
        # C1 (Check Gold) ROW
        self.create_table_row(table_frame, 3, "C1(Check\nGold)", {
            'initial': 'num_strip_weight_goldM11',
            'silver': 'num_silver_weight_goldM11',
            'copper': 'num_copper_weight_goldM11',
            'lead': 'num_lead_weight_goldM11',
            'cornet': 'num_cornet_weight_goldM11',
            'delta': 'delta11',
            'fineness': None,
            'mean_fineness': None,
            'remarks': None
        }, "Delta 1", '#e8f5e9')
        
        # C2 (Check Gold) ROW
        self.create_table_row(table_frame, 4, "C2(Check\nGold)", {
            'initial': 'num_strip_weight_goldM12',
            'silver': 'num_silver_weight_goldM12',
            'copper': 'num_copper_weight_goldM12',
            'lead': 'num_lead_weight_goldM12',
            'cornet': 'num_cornet_weight_goldM12',
            'delta': 'delta22',
            'fineness': None,
            'mean_fineness': None,
            'remarks': None
        }, "Delta 2", '#f3e5f5')
        
        # SAVE BUTTONS ROW
        self.create_save_buttons_row(table_frame, 5)
        
    def create_table_row(self, parent, row, s_no, field_mapping, fineness_text, bg_color):
        """Create a table row with entries"""
        
        # S No. column
        s_no_label = tk.Label(parent, text=s_no, font=('Segoe UI', 8, 'bold'), 
                            bg=bg_color, relief='solid', borderwidth=1, justify='center')
        s_no_label.grid(row=row, column=0, sticky='ew', padx=1, pady=1, ipady=4)
        
        # Entry columns
        columns = ['initial', 'silver', 'copper', 'lead', 'cornet', 'delta', 'fineness', 'mean_fineness', 'remarks']
        
        for col_idx, col_key in enumerate(columns, 1):
            field_id = field_mapping.get(col_key)
            
            if field_id:
                # Create entry widget
                if col_key == 'remarks':
                    entry = ttk.Entry(parent, width=12, style='Compact.TEntry', font=('Segoe UI', 10, 'bold'))
                else:
                    entry = ttk.Entry(parent, width=8, style='Compact.TEntry', font=('Segoe UI', 10, 'bold'))
                
                entry.grid(row=row, column=col_idx, sticky='ew', padx=2, pady=2)
                
                # Store in weight_entries dict
                self.weight_entries[field_id] = entry
                
            elif col_key == 'fineness' and fineness_text:
                # Special label for fineness column
                fineness_label = tk.Label(parent, text=fineness_text, font=('Segoe UI', 7), 
                                        bg='#f8f9fa', relief='solid', borderwidth=1, justify='center')
                fineness_label.grid(row=row, column=col_idx, sticky='ew', padx=2, pady=2, ipady=2)
                
            else:
                # Empty cell
                empty_label = tk.Label(parent, text="", bg='#f8f9fa', relief='solid', borderwidth=1)
                empty_label.grid(row=row, column=col_idx, sticky='ew', padx=2, pady=2, ipady=4)
        
    def create_save_buttons_row(self, parent, row):
        """Create save buttons row at bottom of table"""
        # Empty cells for first 4 columns
        for col in range(4):
            empty_label = tk.Label(parent, text="", bg='#ffffff', relief='flat')
            empty_label.grid(row=row, column=col, sticky='ew', padx=2, pady=8)
        # Save (Initial Weight) button
        save_initial_btn = ttk.Button(parent, text="Save (Initial Weight)", 
                                    style='Info.TButton', command=self.save_initial_weights)
        save_initial_btn.grid(row=row, column=4, columnspan=2, sticky='ew', padx=4, pady=8)
        # Save (Cornet Weight) button  
        # Add checkbox for 'Include Submit HUID'
        self.include_submit_huid_var = tk.BooleanVar(value=False)
        include_submit_huid_cb = ttk.Checkbutton(parent, text="Include Submit HUID", variable=self.include_submit_huid_var)
        include_submit_huid_cb.grid(row=row, column=6, sticky='e', padx=(0, 4), pady=8)
        save_cornet_btn = ttk.Button(parent, text="Save (Cornet Weight)", 
                                   style='Success.TButton', command=self.save_cornet_weights)
        save_cornet_btn.grid(row=row, column=7, sticky='ew', padx=4, pady=8)
    
    def save_initial_weights(self):
        """Automated workflow: Fill portal fields with current UI values only (skip cornet weights), show progress dialog, and save initial weights."""
        try:
            request_no = self.request_entry.get().strip()
            job_no = self.job_entry.get().strip()
            if not request_no:
                messagebox.showwarning("Validation Error", "Please enter request number")
                return
            if not job_no:
                messagebox.showwarning("Validation Error", "Please enter job number")
                return
            if not self.driver or not self.logged_in:
                messagebox.showwarning("Not Ready", "Please open browser and login first")
                return
            # Always use the currently selected lot from the UI
            if hasattr(self, 'lot_var') and self.lot_var.get():
                selected_lot = self.lot_var.get()
            else:
                selected_lot = self.manual_lot_var.get()
            self.current_lot_no = selected_lot
            self.log(f"ðŸŽ¯ Save Initial Weights will use Lot: {selected_lot}", 'weight')
            threading.Thread(target=self._save_initial_weights_worker, args=(request_no, job_no, selected_lot), daemon=True).start()
        except Exception as e:
            self.log(f"âŒ Error starting save initial weights workflow: {str(e)}", 'weight')
            messagebox.showerror("Error", f"Error starting workflow: {str(e)}")

    def _save_initial_weights_worker(self, request_no, job_no, selected_lot):
        """Worker thread for save initial weights: fill portal fields with current UI values only, skip cornet weights, and save."""
        loading_dialog = None
        try:
            loading_dialog = LoadingDialog(self.root, "Save Initial Weights", "Filling portal fields (initial weights only, skipping cornet)...")
            # Step 1: Load weight page
            loading_dialog.update_status("Loading weight page...")
            loading_dialog.update_message("Loading weight entry page for the request...")
            encoded_request = base64.b64encode(str(request_no).encode()).decode()
            encoded_job = base64.b64encode(str(job_no).encode()).decode()
            weight_url = f"https://newmanak.uat.dcservices.in/MANAK/UID_WeighingForm?requestNo={encoded_request}&jobNo={encoded_job}"
            self.driver.get(weight_url)
            time.sleep(3)
            current_url = self.driver.current_url
            if 'UID_WeighingForm' not in current_url:
                raise Exception("Failed to load weight page")
            self.page_loaded = True
            self.log(f"âœ… Weight page loaded: {current_url}", 'weight')
            # Step 2: Select Lot No in the portal using Select2 widget
            try:
                select2_container = self.driver.find_element(By.ID, "s2id_lotno")
                select2_container.click()
                time.sleep(0.5)
                options = self.driver.find_elements(By.CSS_SELECTOR, "ul.select2-results li")
                found = False
                for option in options:
                    if option.text.strip().endswith(f"Lot {selected_lot}") or option.text.strip() == f"Lot {selected_lot}":
                        option.click()
                        found = True
                        self.log(f"âœ… Selected Lot {selected_lot} in portal via Select2", 'weight')
                        break
                if not found:
                    raise Exception(f"Lot {selected_lot} not found in Select2 options")
                time.sleep(1)
                lot_dropdown = self.driver.find_element(By.ID, "lotno")
                selected_value = lot_dropdown.get_attribute('value')
                if selected_value != str(selected_lot):
                    self.log(f"âš ï¸ Lot selection verification failed: expected {selected_lot}, got {selected_value}", 'weight')
                else:
                    self.log(f"âœ… Lot selection verified: {selected_value}", 'weight')
            except Exception as select2_error:
                self.log(f"âš ï¸ Select2 lot selection failed: {str(select2_error)}. Trying fallback methods...", 'weight')
                try:
                    wait = WebDriverWait(self.driver, 10)
                    lot_dropdown = wait.until(EC.presence_of_element_located((By.ID, "lotno")))
                    if not lot_dropdown.is_displayed() or not lot_dropdown.is_enabled():
                        self.driver.execute_script("arguments[0].style.display = 'block'; arguments[0].removeAttribute('readonly');", lot_dropdown)
                        time.sleep(0.5)
                    self.driver.execute_script("arguments[0].value = '';", lot_dropdown)
                    time.sleep(0.2)
                    from selenium.webdriver.support.ui import Select
                    select_element = Select(lot_dropdown)
                    select_element.select_by_value(selected_lot)
                    self.log(f"âœ… Selected Lot {selected_lot} in portal via Select fallback", 'weight')
                    time.sleep(1)
                except Exception as fallback_error:
                    self.log(f"âŒ Could not select lot in portal: {str(fallback_error)}", 'weight')
            filled_count = 0
            skipped_count = 0
            error_count = 0
            # 1. Fill Sample Drawn Weight
            for field_name in ['num_scrap_weight']:
                try:
                    value = self.weight_entries[field_name].get().strip()
                    if not value:
                        skipped_count += 1
                        continue
                    element = self.driver.find_element(By.ID, field_name)
                    if element.is_displayed() and element.is_enabled():
                        element.clear()
                        element.send_keys(value)
                        filled_count += 1
                        self.log(f"âœ… Filled {field_name}: {value}", 'weight')
                        # Click savesampleweight button
                        try:
                            save_btn = self.driver.find_element(By.ID, 'savesampleweight')
                            if save_btn.is_displayed() and save_btn.is_enabled():
                                save_btn.click()
                                self.log("ðŸ’¾ Clicked Save Sample Weight button", 'weight')
                                time.sleep(1)
                        except Exception as e:
                            self.log(f"âŒ Error clicking Save Sample Weight button: {str(e)}", 'weight')
                    else:
                        skipped_count += 1
                except Exception as e:
                    error_count += 1
                    self.log(f"âŒ Error filling {field_name}: {str(e)}", 'weight')
            # 2. Fill Button Weight
            for field_name in ['buttonweight']:
                try:
                    value = self.weight_entries[field_name].get().strip()
                    if not value:
                        skipped_count += 1
                        continue
                    element = self.driver.find_element(By.ID, field_name)
                    if element.is_displayed() and element.is_enabled():
                        element.clear()
                        element.send_keys(value)
                        filled_count += 1
                        self.log(f"âœ… Filled {field_name}: {value}", 'weight')
                        # Click savebuttonweight button
                        try:
                            save_btn = self.driver.find_element(By.ID, 'savebuttonweight')
                            if save_btn.is_displayed() and save_btn.is_enabled():
                                save_btn.click()
                                self.log("ðŸ’¾ Clicked Save Button Weight button", 'weight')
                                time.sleep(1)
                        except Exception as e:
                            self.log(f"âŒ Error clicking Save Button Weight button: {str(e)}", 'weight')
                    else:
                        skipped_count += 1
                except Exception as e:
                    error_count += 1
                    self.log(f"âŒ Error filling {field_name}: {str(e)}", 'weight')
            # 3. Fill all Initial Weights, Ag, Pb, Cu (skip cornet)
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
            for field_name in initial_weight_fields:
                try:
                    value = self.weight_entries[field_name].get().strip()
                    if not value:
                        skipped_count += 1
                        continue
                    element = self.driver.find_element(By.ID, field_name)
                    if element.is_displayed() and element.is_enabled():
                        element.clear()
                        element.send_keys(value)
                        filled_count += 1
                        self.log(f"âœ… Filled {field_name}: {value}", 'weight')
                    else:
                        skipped_count += 1
                except Exception as e:
                    error_count += 1
                    self.log(f"âŒ Error filling {field_name}: {str(e)}", 'weight')
            # Click Save (Initial Weight) button for strips
            try:
                save_btn = self.driver.find_element(By.ID, 'chechkgoldM12')
                if save_btn.is_displayed() and save_btn.is_enabled():
                    save_btn.click()
                    self.log("ðŸ’¾ Clicked Save (Initial Weight) button for strips", 'weight')
                    time.sleep(1)
                else:
                    self.log("âš ï¸ Save (Initial Weight) button for strips not interactable", 'weight')
            except Exception as e:
                self.log(f"âŒ Error clicking Save (Initial Weight) button for strips: {str(e)}", 'weight')
            # Summary
            self.log(f"ðŸŽ¯ INITIAL WEIGHT FILL COMPLETE:", 'weight')
            self.log(f"âœ… Filled: {filled_count} | âš ï¸ Skipped: {skipped_count} | âŒ Errors: {error_count}", 'weight')
            loading_dialog.update_status("Done!")
            loading_dialog.update_message("All initial weight fields filled in portal.")
            time.sleep(1)
            loading_dialog.close()
            if filled_count > 0:
                messagebox.showinfo("Success", f"âœ… Successfully filled {filled_count} initial weight fields!")
            else:
                messagebox.showwarning("No Changes", "No initial weight fields were filled. Please check your inputs.")
        except Exception as e:
            if loading_dialog:
                loading_dialog.close()
            self.log(f"âŒ Error in save initial weights workflow: {str(e)}", 'weight')
            messagebox.showerror("Error", f"Error in save initial weights workflow: {str(e)}")
    
    def auto_workflow(self):
        """Automated workflow: Fill portal fields with current UI values only (no API fetch)"""
        try:
            request_no = self.request_entry.get().strip()
            job_no = self.job_entry.get().strip()
            if not request_no:
                messagebox.showwarning("Validation Error", "Please enter request number")
                return
            if not job_no:
                messagebox.showwarning("Validation Error", "Please enter job number")
                return
            if not self.driver or not self.logged_in:
                messagebox.showwarning("Not Ready", "Please open browser and login first")
                return
            # Always use the currently selected lot from the UI
            if hasattr(self, 'lot_var') and self.lot_var.get():
                selected_lot = self.lot_var.get()
            else:
                selected_lot = self.manual_lot_var.get()
            self.current_lot_no = selected_lot
            self.log(f"ðŸŽ¯ Auto workflow will use Lot: {selected_lot}", 'weight')
            threading.Thread(target=self._auto_workflow_worker, args=(request_no, job_no, selected_lot), daemon=True).start()
        except Exception as e:
            self.log(f"âŒ Error starting auto workflow: {str(e)}", 'weight')
            messagebox.showerror("Error", f"Error starting workflow: {str(e)}")
    
    def _auto_workflow_worker(self, request_no, job_no, selected_lot):
        """Worker thread for automated workflow: fill portal fields with current UI values only"""
        loading_dialog = None
        try:
            loading_dialog = LoadingDialog(self.root, "Auto Workflow", "Filling portal fields with current UI values...")
            # Step 1: Load weight page
            loading_dialog.update_status("Loading weight page...")
            loading_dialog.update_message("Loading weight entry page for the request...")
            encoded_request = base64.b64encode(str(request_no).encode()).decode()
            encoded_job = base64.b64encode(str(job_no).encode()).decode()
            weight_url = f"https://newmanak.uat.dcservices.in/MANAK/UID_WeighingForm?requestNo={encoded_request}&jobNo={encoded_job}"
            self.driver.get(weight_url)
            time.sleep(3)
            current_url = self.driver.current_url
            if 'UID_WeighingForm' not in current_url:
                raise Exception("Failed to load weight page")
            self.page_loaded = True
            self.log(f"âœ… Weight page loaded: {current_url}", 'weight')
            # Step 2: Select Lot No in the portal using Select2 widget
            try:
                select2_container = self.driver.find_element(By.ID, "s2id_lotno")
                select2_container.click()
                time.sleep(0.5)
                options = self.driver.find_elements(By.CSS_SELECTOR, "ul.select2-results li")
                found = False
                for option in options:
                    if option.text.strip().endswith(f"Lot {selected_lot}") or option.text.strip() == f"Lot {selected_lot}":
                        option.click()
                        found = True
                        self.log(f"âœ… Selected Lot {selected_lot} in portal via Select2", 'weight')
                        break
                if not found:
                    raise Exception(f"Lot {selected_lot} not found in Select2 options")
                time.sleep(1)
                lot_dropdown = self.driver.find_element(By.ID, "lotno")
                selected_value = lot_dropdown.get_attribute('value')
                if selected_value != str(selected_lot):
                    self.log(f"âš ï¸ Lot selection verification failed: expected {selected_lot}, got {selected_value}", 'weight')
                else:
                    self.log(f"âœ… Lot selection verified: {selected_value}", 'weight')
            except Exception as select2_error:
                self.log(f"âš ï¸ Select2 lot selection failed: {str(select2_error)}. Trying fallback methods...", 'weight')
                try:
                    wait = WebDriverWait(self.driver, 10)
                    lot_dropdown = wait.until(EC.presence_of_element_located((By.ID, "lotno")))
                    if not lot_dropdown.is_displayed() or not lot_dropdown.is_enabled():
                        self.driver.execute_script("arguments[0].style.display = 'block'; arguments[0].removeAttribute('readonly');", lot_dropdown)
                        time.sleep(0.5)
                    self.driver.execute_script("arguments[0].value = '';", lot_dropdown)
                    time.sleep(0.2)
                    from selenium.webdriver.support.ui import Select
                    select_element = Select(lot_dropdown)
                    select_element.select_by_value(selected_lot)
                    self.log(f"âœ… Selected Lot {selected_lot} in portal via Select fallback", 'weight')
                    time.sleep(1)
                except Exception as fallback_error:
                    self.log(f"âŒ Could not select lot in portal: {str(fallback_error)}", 'weight')
            # Step 3: Fill Sample Drawn Weight and Button Weight
            filled_count = 0
            skipped_count = 0
            error_count = 0
            for field_name in ['num_scrap_weight', 'buttonweight']:
                try:
                    value = self.weight_entries[field_name].get().strip()
                    if not value:
                        skipped_count += 1
                        continue
                    element = self.driver.find_element(By.ID, field_name)
                    if element.is_displayed() and element.is_enabled():
                        element.clear()
                        element.send_keys(value)
                        filled_count += 1
                        self.log(f"âœ… Filled {field_name}: {value}", 'weight')
                    else:
                        skipped_count += 1
                except Exception as e:
                    error_count += 1
                    self.log(f"âŒ Error filling {field_name}: {str(e)}", 'weight')
            # Step 4: Fill all Fire Assaying fields
            for field_name, field_id in self.field_ids.items():
                if field_name in ['num_scrap_weight', 'buttonweight']:
                    continue  # Already filled
                try:
                    value = self.weight_entries[field_name].get().strip()
                    if not value:
                        skipped_count += 1
                        continue
                    element = self.driver.find_element(By.ID, field_id)
                    if element.is_displayed() and element.is_enabled():
                        element.clear()
                        element.send_keys(value)
                        filled_count += 1
                        self.log(f"âœ… Filled {field_id}: {value}", 'weight')
                    else:
                        skipped_count += 1
                except Exception as e:
                    error_count += 1
                    self.log(f"âŒ Error filling {field_id}: {str(e)}", 'weight')
            # Summary
            self.log(f"ðŸŽ¯ WORKFLOW COMPLETE: Fields filled in portal.", 'weight')
            self.log(f"âœ… Filled: {filled_count} | âš ï¸ Skipped: {skipped_count} | âŒ Errors: {error_count}", 'weight')
            loading_dialog.update_status("Done!")
            loading_dialog.update_message("All fields filled in portal.")
            time.sleep(1)
            loading_dialog.close()
        except Exception as e:
            if loading_dialog:
                loading_dialog.close()
            self.log(f"âŒ Error in auto workflow: {str(e)}", 'weight')
            messagebox.showerror("Error", f"Error in auto workflow: {str(e)}")
    
    def select_lot_in_portal(self):
        """Manually select lot in portal without fetching API data"""
        try:
            if not self.driver or not self.page_loaded:
                messagebox.showwarning("Not Ready", "Please load weight page first")
                return
            
            # Get the manually selected lot
            lot_no = self.manual_lot_var.get()
            self.current_lot_no = lot_no
            
            from selenium.webdriver.support.ui import WebDriverWait, Select
            from selenium.webdriver.support import expected_conditions as EC
            import time
            
            # Select the correct lot in the portal
            try:
                wait = WebDriverWait(self.driver, 10)
                lot_dropdown = wait.until(EC.presence_of_element_located((By.ID, "lotno")))
                
                # Try to make it visible if not interactable
                if not lot_dropdown.is_displayed() or not lot_dropdown.is_enabled():
                    self.driver.execute_script("arguments[0].style.display = 'block'; arguments[0].removeAttribute('readonly');", lot_dropdown)
                    time.sleep(0.5)
                
                # Clear any existing selection first
                self.driver.execute_script("arguments[0].value = '';", lot_dropdown)
                time.sleep(0.2)
                
                # Try multiple selection methods
                try:
                    select_element = Select(lot_dropdown)
                    select_element.select_by_value(lot_no)
                    self.log(f"âœ… Selected Lot {lot_no} in portal via Select", 'weight')
                except Exception as select_error:
                    # Try direct value setting
                    try:
                        self.driver.execute_script(f"arguments[0].value = '{lot_no}';", lot_dropdown)
                        self.driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", lot_dropdown)
                        self.log(f"âœ… Selected Lot {lot_no} in portal via direct value", 'weight')
                    except Exception as direct_error:
                        # Try by index (lot_no - 1)
                        try:
                            select_element = Select(lot_dropdown)
                            select_element.select_by_index(int(lot_no) - 1)
                            self.log(f"âœ… Selected Lot {lot_no} in portal via index", 'weight')
                        except Exception as index_error:
                            self.log(f"âš ï¸ Could not select lot in portal: {str(select_error)} | Direct: {str(direct_error)} | Index: {str(index_error)}", 'weight')
                
                # Verify selection was successful
                time.sleep(1)  # Wait for page to update
                try:
                    selected_value = lot_dropdown.get_attribute('value')
                    if selected_value != lot_no:
                        self.log(f"âš ï¸ Lot selection verification failed: expected {lot_no}, got {selected_value}", 'weight')
                    else:
                        self.log(f"âœ… Lot selection verified: {selected_value}", 'weight')
                except:
                    pass
                    
            except Exception as e:
                self.log(f"âš ï¸ Could not find lot dropdown: {str(e)}", 'weight')
                
        except Exception as e:
            self.log(f"âŒ Error selecting lot in portal: {str(e)}", 'weight')
            messagebox.showerror("Error", f"Error selecting lot: {str(e)}")
    
    def save_cornet_weights(self):
        """Save cornet weights and related fields to portal, and optionally submit HUID if checkbox is checked. Always loads the page, shows progress dialog, and selects the lot."""
        loading_dialog = None
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            import time
            # Get the correct lot number - use API lot if available, otherwise use manual selection
            lot_no = str(getattr(self, 'current_lot_no', self.manual_lot_var.get()))
            request_no = self.request_entry.get().strip()
            job_no = self.job_entry.get().strip()
            loading_dialog = LoadingDialog(self.root, "Save Cornet Weights", "Filling cornet weights and saving...")
            loading_dialog.update_status("Loading weight page...")
            loading_dialog.update_message("Loading weight entry page for the request...")
            encoded_request = base64.b64encode(str(request_no).encode()).decode()
            encoded_job = base64.b64encode(str(job_no).encode()).decode()
            weight_url = f"https://newmanak.uat.dcservices.in/MANAK/UID_WeighingForm?requestNo={encoded_request}&jobNo={encoded_job}"
            self.driver.get(weight_url)
            time.sleep(3)
            current_url = self.driver.current_url
            if 'UID_WeighingForm' not in current_url:
                raise Exception("Failed to load weight page")
            self.page_loaded = True
            self.log(f"âœ… Weight page loaded: {current_url}", 'weight')
            loading_dialog.update_status("Selecting lot...")
            # Select the lot
            try:
                select2_container = self.driver.find_element(By.ID, "s2id_lotno")
                select2_container.click()
                time.sleep(0.5)
                options = self.driver.find_elements(By.CSS_SELECTOR, "ul.select2-results li")
                found = False
                for option in options:
                    if option.text.strip().endswith(f"Lot {lot_no}") or option.text.strip() == f"Lot {lot_no}":
                        option.click()
                        found = True
                        self.log(f"âœ… Selected Lot {lot_no} in portal via Select2", 'weight')
                        break
                if not found:
                    raise Exception(f"Lot {lot_no} not found in Select2 options")
                time.sleep(1)
                lot_dropdown = self.driver.find_element(By.ID, "lotno")
                selected_value = lot_dropdown.get_attribute('value')
                if selected_value != str(lot_no):
                    self.log(f"âš ï¸ Lot selection verification failed: expected {lot_no}, got {selected_value}", 'weight')
                else:
                    self.log(f"âœ… Lot selection verified: {selected_value}", 'weight')
            except Exception as select2_error:
                self.log(f"âš ï¸ Select2 lot selection failed: {str(select2_error)}. Trying fallback methods...", 'weight')
                try:
                    wait = WebDriverWait(self.driver, 10)
                    lot_dropdown = wait.until(EC.presence_of_element_located((By.ID, "lotno")))
                    if not lot_dropdown.is_displayed() or not lot_dropdown.is_enabled():
                        self.driver.execute_script("arguments[0].style.display = 'block'; arguments[0].removeAttribute('readonly');", lot_dropdown)
                        time.sleep(0.5)
                    self.driver.execute_script("arguments[0].value = '';", lot_dropdown)
                    time.sleep(0.2)
                    from selenium.webdriver.support.ui import Select
                    select_element = Select(lot_dropdown)
                    select_element.select_by_value(lot_no)
                    self.log(f"âœ… Selected Lot {lot_no} in portal via Select fallback", 'weight')
                    time.sleep(1)
                except Exception as fallback_error:
                    self.log(f"âŒ Could not select lot in portal: {str(fallback_error)}", 'weight')
            loading_dialog.update_status("Filling cornet weights...")
            # Fill only cornet weight fields
            cornet_fields = [
                'num_cornet_weightM11', 'num_cornet_weightM12',
                'num_cornet_weight_goldM11', 'num_cornet_weight_goldM12'
            ]
            filled_count = 0
            for field_id in cornet_fields:
                try:
                    if field_id in self.weight_entries:
                        value = self.weight_entries[field_id].get().strip()
                        if value:
                            element = self.driver.find_element(By.ID, field_id)
                            if element.is_displayed() and element.is_enabled():
                                element.clear()
                                element.send_keys(value)
                                filled_count += 1
                                self.weight_entries[field_id].configure(style='Compact.TEntry')
                                self.log(f"âœ… Filled {field_id}: {value}", 'weight')
                except Exception as e:
                    self.log(f"âŒ Error filling {field_id}: {str(e)}", 'weight')
            loading_dialog.update_status("Saving cornet weights...")
            # Click savecornetvalues button
            try:
                save_btn = self.driver.find_element(By.ID, 'savecornetvalues')
                if save_btn.is_displayed() and save_btn.is_enabled():
                    save_btn.click()
                    self.log("ðŸ’¾ Clicked Save Cornet Weight button", 'weight')
                    time.sleep(1)
                    # Handle first alert (Are you sure you want to save?)
                    try:
                        alert = self.driver.switch_to.alert
                        alert_text = alert.text
                        self.log(f"ðŸ”” Alert: {alert_text}", 'weight')
                        alert.accept()
                        time.sleep(1)
                    except Exception as e:
                        self.log(f"âŒ Error handling first alert: {str(e)}", 'weight')
                    # Handle second alert (result)
                    try:
                        alert = self.driver.switch_to.alert
                        alert_text = alert.text
                        self.log(f"ðŸ”” Result Alert: {alert_text}", 'weight')
                        alert.accept()
                        time.sleep(1)
                    except Exception as e:
                        self.log(f"âŒ Error handling result alert: {str(e)}", 'weight')
                else:
                    self.log("âš ï¸ Save Cornet Weight button not interactable", 'weight')
            except Exception as e:
                self.log(f"âŒ Error clicking Save Cornet Weight button: {str(e)}", 'weight')
            loading_dialog.update_status("Done!")
            loading_dialog.update_message("Cornet weights saved.")
            time.sleep(1)
            loading_dialog.close()
            # If checkbox is checked, submit for HUID
            if getattr(self, 'include_submit_huid_var', None) and self.include_submit_huid_var.get():
                try:
                    submit_btn = self.driver.find_element(By.ID, 'submitQM')
                    if submit_btn.is_displayed() and submit_btn.is_enabled():
                        submit_btn.click()
                        self.log("ðŸ“¤ Submitted for HUID (auto)", 'weight')
                        messagebox.showinfo("Submitted", "Form submitted for HUID!")
                    else:
                        self.log("âš ï¸ Submit For HUID button not interactable", 'weight')
                        messagebox.showwarning("Not Submitted", "Submit For HUID button not interactable")
                except Exception as e:
                    self.log(f"âŒ Error submitting for HUID: {str(e)}", 'weight')
                    messagebox.showerror("Error", f"Error submitting for HUID: {str(e)}")
            else:
                self.log("â„¹ï¸ Not submitting for HUID (checkbox not checked)", 'weight')
        except Exception as e:
            if loading_dialog:
                loading_dialog.close()
            self.log(f"âŒ Error saving cornet weights: {str(e)}", 'weight')
            messagebox.showerror("Error", f"Error saving cornet weights: {str(e)}")
    
    def submit_for_huid(self):
        """Submit form for HUID processing"""
        try:
            if not self.driver or not self.page_loaded:
                messagebox.showwarning("Not Ready", "Please load weight page first")
                return
            
            # Look for submit button
            submit_buttons = [
                "Submit For HUID",
                "submit",
                "Submit",
                "SUBMIT"
            ]
            
            submitted = False
            for button_text in submit_buttons:
                try:
                    # Try to find button by text
                    submit_btn = self.driver.find_element(By.XPATH, f"//button[contains(text(), '{button_text}')]")
                    if submit_btn.is_displayed() and submit_btn.is_enabled():
                        submit_btn.click()
                        submitted = True
                        break
                except:
                    continue
            
            if submitted:
                self.log("ðŸ“¤ Form submitted for HUID processing", 'weight')
                messagebox.showinfo("Success", "âœ… Form submitted for HUID processing!")
            else:
                self.log("âš ï¸ Submit button not found", 'weight')
                messagebox.showwarning("Warning", "Submit button not found on page")
                
        except Exception as e:
            self.log(f"âŒ Error submitting form: {str(e)}", 'weight')
    
    def setup_settings_tab(self):
        """Setup settings tab"""
        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text="âš™ï¸ Settings")
        
        # Settings card
        settings_card = ttk.LabelFrame(settings_frame, text="ðŸ”§ Configuration", style='Compact.TLabelframe')
        settings_card.pack(fill='x', padx=10, pady=10)
        
        settings_grid = ttk.Frame(settings_card)
        settings_grid.pack(fill='x', padx=10, pady=10)
        
        # Username
        ttk.Label(settings_grid, text="Username:", font=('Segoe UI', 9, 'bold')).grid(row=0, column=0, padx=(0, 8), pady=8, sticky='w')
        self.username_var = tk.StringVar(value='qmhmc14')
        username_entry = ttk.Entry(settings_grid, textvariable=self.username_var, width=25, style='Compact.TEntry', font=('Segoe UI', 10, 'bold'))
        username_entry.grid(row=0, column=1, padx=(0, 8), pady=8, sticky='w')
        
        # Password
        ttk.Label(settings_grid, text="Password:", font=('Segoe UI', 9, 'bold')).grid(row=1, column=0, padx=(0, 8), pady=8, sticky='w')
        self.password_var = tk.StringVar(value='')  # Empty default for security
        password_entry = ttk.Entry(settings_grid, textvariable=self.password_var, width=25, style='Compact.TEntry', show='*', font=('Segoe UI', 10, 'bold'))
        password_entry.grid(row=1, column=1, padx=(0, 8), pady=8, sticky='w')
        
        # Separator
        ttk.Separator(settings_grid, orient='horizontal').grid(row=2, column=0, columnspan=2, sticky='ew', pady=15)
        
        # Reception credentials heading
        ttk.Label(settings_grid, text="Reception Login (for Accept Requests):", font=('Segoe UI', 9, 'bold'), foreground='#0066cc').grid(row=3, column=0, columnspan=2, padx=(0, 8), pady=(10, 5), sticky='w')
        
        # Reception Username
        ttk.Label(settings_grid, text="Reception Username:", font=('Segoe UI', 9, 'bold')).grid(row=4, column=0, padx=(0, 8), pady=8, sticky='w')
        self.reception_username_var = tk.StringVar(value='')
        reception_username_entry = ttk.Entry(settings_grid, textvariable=self.reception_username_var, width=25, style='Compact.TEntry', font=('Segoe UI', 10, 'bold'))
        reception_username_entry.grid(row=4, column=1, padx=(0, 8), pady=8, sticky='w')
        
        # Reception Password
        ttk.Label(settings_grid, text="Reception Password:", font=('Segoe UI', 9, 'bold')).grid(row=5, column=0, padx=(0, 8), pady=8, sticky='w')
        self.reception_password_var = tk.StringVar(value='')
        reception_password_entry = ttk.Entry(settings_grid, textvariable=self.reception_password_var, width=25, style='Compact.TEntry', show='*', font=('Segoe UI', 10, 'bold'))
        reception_password_entry.grid(row=5, column=1, padx=(0, 8), pady=8, sticky='w')
        
        # Separator
        ttk.Separator(settings_grid, orient='horizontal').grid(row=6, column=0, columnspan=2, sticky='ew', pady=15)
        
        # Job Data API URL
        ttk.Label(settings_grid, text="Job Data API:", font=('Segoe UI', 9, 'bold')).grid(row=7, column=0, padx=(0, 8), pady=8, sticky='w')
        self.api_url_var = tk.StringVar(value='https://mahalaxmihallmarkingcentre.com/admin/get_job_report.php?job_no=')
        api_url_entry = ttk.Entry(settings_grid, textvariable=self.api_url_var, width=50, style='Compact.TEntry', font=('Segoe UI', 10, 'bold'))
        api_url_entry.grid(row=7, column=1, padx=(0, 8), pady=8, sticky='w')
        
        # Request No API URL
        ttk.Label(settings_grid, text="Request No API:", font=('Segoe UI', 9, 'bold')).grid(row=8, column=0, padx=(0, 8), pady=8, sticky='w')
        self.request_api_url_var = tk.StringVar(value='https://mahalaxmihallmarkingcentre.com/admin/API/get_request_no.php?job_no=')
        request_api_entry = ttk.Entry(settings_grid, textvariable=self.request_api_url_var, width=50, style='Compact.TEntry', font=('Segoe UI', 10, 'bold'))
        request_api_entry.grid(row=8, column=1, padx=(0, 8), pady=8, sticky='w')
        
        # Orders API URL
        ttk.Label(settings_grid, text="Orders API:", font=('Segoe UI', 9, 'bold')).grid(row=9, column=0, padx=(0, 8), pady=8, sticky='w')
        self.orders_api_url_var = tk.StringVar(value='http://localhost/manak_auto_fill/get_orders.php')
        orders_api_entry = ttk.Entry(settings_grid, textvariable=self.orders_api_url_var, width=50, style='Compact.TEntry', font=('Segoe UI', 10, 'bold'))
        orders_api_entry.grid(row=9, column=1, padx=(0, 8), pady=8, sticky='w')
        
        # API Key
        ttk.Label(settings_grid, text="API Key:", font=('Segoe UI', 9, 'bold')).grid(row=10, column=0, padx=(0, 8), pady=8, sticky='w')
        self.api_key_var = tk.StringVar(value='')
        api_key_entry = ttk.Entry(settings_grid, textvariable=self.api_key_var, width=50, style='Compact.TEntry', show='*', font=('Segoe UI', 10, 'bold'))
        api_key_entry.grid(row=10, column=1, padx=(0, 8), pady=8, sticky='w')
        
        # Save button
        save_btn = ttk.Button(settings_grid, text="ðŸ’¾ Save Settings", style='Success.TButton', command=self.save_settings)
        save_btn.grid(row=11, column=0, columnspan=2, pady=15)
        
    def _show_validation_error(self, widget, message):
        """Show validation error styling"""
        widget.configure(style='Warning.TEntry')
        messagebox.showwarning("Validation Error", message)
        
    def _clear_validation_error(self, widget):
        """Clear validation error styling"""
        widget.configure(style='Compact.TEntry')
        
    def log(self, message, target='status'):
        """Add message to log with timestamp"""
        timestamp = time.strftime('%H:%M:%S')
        log_message = f"[{timestamp}] {message}\n"
        
        if target == 'status':
            self.status_text.insert(tk.END, log_message)
            self.status_text.see(tk.END)
        elif target == 'weight':
            self.weight_log.insert(tk.END, log_message)
            self.weight_log.see(tk.END)
        elif target == 'acknowledge':
            self.acknowledge_log.insert(tk.END, log_message)
            self.acknowledge_log.see(tk.END)
        elif target == 'generate':
            self.generate_log.insert(tk.END, log_message)
            self.generate_log.see(tk.END)
            
        self.root.update()
        
    def open_browser(self):
        """Open visible Chrome browser and go directly to login page"""
        try:
            self.log("ðŸš€ Starting Chrome browser...")
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1280,720")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--allow-running-insecure-content")
            chrome_options.add_experimental_option("detach", True)
            chrome_options.add_argument("--disable-features=WebSerial")
            chrome_options.add_argument("--disable-blink-features=WebSerial")
            chrome_options.add_argument("--disable-device-discovery-notifications")
            
            # Block serial port popup
            prefs = {
                "profile.default_content_setting_values.serial_port": 2,
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            try:
                from selenium.webdriver.chrome.service import Service
                service = Service('/nix/store/8zj50jw4w0hby47167kqqsaqw4mm5bkd-chromedriver-unwrapped-138.0.7204.100/bin/chromedriver')
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            except:
                self.driver = webdriver.Chrome(options=chrome_options)
                
            self.driver.set_page_load_timeout(30)
            self.wait = WebDriverWait(self.driver, 15)
            
            self.log("âœ… Browser opened successfully!")
            
            # Go directly to login page
            self.driver.get("https://newmanak.uat.dcservices.in/MANAK/eBISLogin")
            self._auto_fill_login_credentials()
            
            # Update button states
            self.open_btn.config(state='disabled')
            self.login_btn.config(state='normal')
            self.check_btn.config(state='normal')
            self.close_btn.config(state='normal')
            
        except Exception as e:
            self.log(f"âŒ Error opening browser: {str(e)}")
            messagebox.showerror("Browser Error", f"Failed to open browser: {str(e)}")

    def navigate_to_login(self):
        """Navigate to MANAK portal login page"""
        if not self.driver:
            messagebox.showwarning("No Browser", "Please open browser first")
            return
            
        try:
            self.log("ðŸ”‘ Navigating to MANAK portal login page...")
            portal_url = "https://newmanak.uat.dcservices.in/MANAK/eBISLogin"
            self.driver.get(portal_url)
            time.sleep(3)
            self._auto_fill_login_credentials()
            
            current_url = self.driver.current_url
            self.log(f"âœ… Navigated to: {current_url}")
            self.log("ðŸ‘¤ Please complete login manually (including CAPTCHA)")
            
        except Exception as e:
            self.log(f"âŒ Error navigating to portal: {str(e)}")

    def _auto_fill_login_credentials(self):
        """Auto-fill username and password on the login page"""
        try:
            WebDriverWait(self.driver, 10).until(lambda d: '/eBISLogin' in d.current_url)
            
            try:
                user_field = self.driver.find_element(By.ID, 'InputEmail')
            except:
                user_field = self.driver.find_element(By.NAME, 'userId')
                
            try:
                pass_field = self.driver.find_element(By.ID, 'InputPassword')
            except:
                pass_field = self.driver.find_element(By.NAME, 'passwd')
            
            user_field.clear()
            user_field.send_keys(self.username_var.get())
            pass_field.clear()
            pass_field.send_keys(self.password_var.get())
            
            self.log("âœ… Credentials auto-filled. Please enter CAPTCHA and login.")
            
        except Exception as e:
            self.log(f"â„¹ï¸ Could not auto-fill credentials: {str(e)}")
            
    def check_login(self):
        """Check if user has completed login"""
        if not self.driver:
            messagebox.showwarning("No Browser", "Please open browser first")
            return
            
        try:
            current_url = self.driver.current_url
            page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            
            self.log(f"ðŸ” Current URL: {current_url}")
            
            # Check for login indicators
            if any(indicator in page_text for indicator in ['login', 'signin', 'captcha', 'username']):
                self.logged_in = False
                self.log("âš ï¸ Still on login page - please complete login")
            else:
                            self.logged_in = True
            self.log("âœ… Login appears successful!")
            self.submit_manak_btn.config(state='normal')
                
        except Exception as e:
            self.log(f"âŒ Error checking login: {str(e)}")
            
    def load_weight_page(self):
        """Load weight entry page for specific request"""
        if not self.driver or not self.logged_in:
            messagebox.showwarning("Not Ready", "Please login first")
            return
            
        try:
            request_no = self.request_entry.get().strip()
            job_no = self.job_entry.get().strip()
            
            if not request_no:
                self._show_validation_error(self.request_entry, "Please enter request number")
                return
                
            self._clear_validation_error(self.request_entry)
            
            # Construct URL
            encoded_request = base64.b64encode(str(request_no).encode()).decode()
            weight_url = f"https://newmanak.uat.dcservices.in/MANAK/UID_WeighingForm?requestNo={encoded_request}"
            if job_no:
                encoded_job = base64.b64encode(str(job_no).encode()).decode()
                weight_url += f"&jobNo={encoded_job}"
                
            self.log(f"ðŸ“„ Loading weight page: {weight_url}", 'weight')
            
            self.driver.get(weight_url)
            time.sleep(3)
            
            current_url = self.driver.current_url
            self.log(f"âœ… Loaded: {current_url}", 'weight')
            
            # Check for form fields
            found_fields = {}
            total_fields = 0
            
            for field_name, field_id in self.field_ids.items():
                try:
                    element = self.driver.find_element(By.ID, field_id)
                    if element.is_displayed():
                        found_fields[field_name] = True
                        total_fields += 1
                except:
                    found_fields[field_name] = False
                    
            self.log(f"ðŸ” Found {total_fields}/{len(self.field_ids)} fields", 'weight')
            
            if total_fields > 0:
                self.page_loaded = True
                self.auto_fill_btn.config(state='normal')
                self.select_lot_btn.config(state='normal')
                self.auto_workflow_btn.config(state='normal')
                self.log("âœ… Weight page loaded - ready for automation", 'weight')
            else:
                self.log("âš ï¸ No weight fields detected", 'weight')
                
        except Exception as e:
            self.log(f"âŒ Error loading weight page: {str(e)}", 'weight')
            
    def clear_weight_fields(self):
        """Clear all weight entry fields"""
        for entry in self.weight_entries.values():
            entry.delete(0, tk.END)
            entry.configure(style='Compact.TEntry')
        self.log("ðŸ§¹ Cleared all fields", 'weight')
        
    def load_settings(self):
        """Load saved settings from config file"""
        try:
            settings_path = 'config/app_settings.json'
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                
                # Load settings into variables
                if 'username' in settings:
                    self.username_var.set(settings['username'])
                if 'password' in settings:
                    self.password_var.set(settings['password'])
                if 'reception_username' in settings:
                    self.reception_username_var.set(settings['reception_username'])
                if 'reception_password' in settings:
                    self.reception_password_var.set(settings['reception_password'])
                if 'api_url' in settings:
                    self.api_url_var.set(settings['api_url'])
                if 'request_api_url' in settings:
                    self.request_api_url_var.set(settings['request_api_url'])
                if 'orders_api_url' in settings:
                    self.orders_api_url_var.set(settings['orders_api_url'])
                if 'api_key' in settings:
                    self.api_key_var.set(settings['api_key'])
                    
                self.log("âœ… Settings loaded from config file", 'status')
            else:
                self.log("â„¹ï¸ No saved settings found, using defaults", 'status')
                
        except Exception as e:
            self.log(f"âš ï¸ Error loading settings: {str(e)}", 'status')
    
    def clear_fields_on_start(self):
        """Clear request and job fields when app starts"""
        try:
            self.request_entry.delete(0, tk.END)
            self.job_entry.delete(0, tk.END)
            self.log("ðŸ§¹ Cleared request fields on startup", 'weight')
        except Exception as e:
            self.log(f"âš ï¸ Error clearing fields on start: {str(e)}", 'weight')
    
    def save_settings(self):
        """Save application settings"""
        try:
            # Save settings to a config file
            settings = {
                'username': self.username_var.get(),
                'password': self.password_var.get(),
                'reception_username': self.reception_username_var.get(),
                'reception_password': self.reception_password_var.get(),
                'api_url': self.api_url_var.get(),
                'request_api_url': self.request_api_url_var.get(),
                'orders_api_url': self.orders_api_url_var.get(),
                'api_key': self.api_key_var.get()
            }
            
            # Create config directory if it doesn't exist
            os.makedirs('config', exist_ok=True)
            
            with open('config/app_settings.json', 'w') as f:
                json.dump(settings, f, indent=2)
                
            messagebox.showinfo("Settings Saved", "âœ… Settings saved successfully!")
            self.log("ðŸ’¾ Settings saved to config/app_settings.json", 'status')
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")
            self.log(f"âŒ Error saving settings: {str(e)}", 'status')
            
    def close_browser(self):
        """Close browser and reset state"""
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
                
            self.logged_in = False
            self.page_loaded = False
            
            # Reset button states
            self.open_btn.config(state='normal')
            self.login_btn.config(state='disabled')
            self.check_btn.config(state='disabled')
            self.close_btn.config(state='disabled')
            self.submit_manak_btn.config(state='disabled')
            
            self.log("âœ… Browser closed")
            
        except Exception as e:
            self.log(f"âŒ Error closing browser: {str(e)}")

    def open_reception_browser(self):
        """Open Chrome browser for Reception tasks"""
        try:
            self.log("ðŸš€ Starting Reception Browser...", 'acknowledge')
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1280,720")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--allow-running-insecure-content")
            chrome_options.add_experimental_option("detach", True)
            chrome_options.add_argument("--disable-features=WebSerial")
            chrome_options.add_argument("--disable-blink-features=WebSerial")
            chrome_options.add_argument("--disable-device-discovery-notifications")
            
            # Block serial port popup
            prefs = {
                "profile.default_content_setting_values.serial_port": 2,
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            try:
                from selenium.webdriver.chrome.service import Service
                service = Service('/nix/store/8zj50jw4w0hby47167kqqsaqw4mm5bkd-chromedriver-unwrapped-138.0.7204.100/bin/chromedriver')
                self.reception_driver = webdriver.Chrome(service=service, options=chrome_options)
            except:
                self.reception_driver = webdriver.Chrome(options=chrome_options)
                
            self.reception_driver.set_page_load_timeout(30)
            
            self.log("âœ… Reception Browser opened! Navigating to login...", 'acknowledge')
            
            # Go directly to login page
            self.reception_driver.get("https://newmanak.uat.dcservices.in/MANAK/eBISLogin")
            self._auto_fill_reception_login_credentials()
            
            # Update button states
            if hasattr(self, 'open_reception_btn'):
                self.open_reception_btn.config(state='disabled')
                self.close_reception_btn.config(state='normal')
            if hasattr(self, 'open_reception_btn_main'):
                self.open_reception_btn_main.config(state='disabled')
                self.close_reception_btn_main.config(state='normal')
            
        except Exception as e:
            self.log(f"âŒ Error opening reception browser: {str(e)}", 'acknowledge')
            messagebox.showerror("Browser Error", f"Failed to open reception browser: {str(e)}")

    def close_reception_browser(self):
        """Close Reception browser"""
        try:
            if self.reception_driver:
                self.reception_driver.quit()
                self.reception_driver = None
                
            # Reset button states
            if hasattr(self, 'open_reception_btn'):
                self.open_reception_btn.config(state='normal')
                self.close_reception_btn.config(state='disabled')
            if hasattr(self, 'open_reception_btn_main'):
                self.open_reception_btn_main.config(state='normal')
                self.close_reception_btn_main.config(state='disabled')
            
            self.log("âœ… Reception Browser closed", 'acknowledge')
            
        except Exception as e:
            self.log(f"âŒ Error closing reception browser: {str(e)}", 'acknowledge')

    def _auto_fill_reception_login_credentials(self):
        """Auto-fill reception username and password"""
        try:
            WebDriverWait(self.reception_driver, 10).until(lambda d: '/eBISLogin' in d.current_url)
            
            try:
                user_field = self.reception_driver.find_element(By.ID, 'InputEmail')
            except:
                user_field = self.reception_driver.find_element(By.NAME, 'userId')
                
            try:
                pass_field = self.reception_driver.find_element(By.ID, 'InputPassword')
            except:
                pass_field = self.reception_driver.find_element(By.NAME, 'passwd')
            
            user_field.clear()
            user_field.send_keys(self.reception_username_var.get())
            pass_field.clear()
            pass_field.send_keys(self.reception_password_var.get())
            
            self.log("âœ… Reception credentials auto-filled. Please login.", 'acknowledge')
            
        except Exception as e:
            self.log(f"â„¹ï¸ Could not auto-fill reception credentials: {str(e)}", 'acknowledge')

    def fetch_api_data(self):
        """Fetch job and strip data from the server"""
        job_no = self.job_entry.get().strip()
        if not job_no:
            self._show_validation_error(self.job_entry, "Job Number is required!")
            return
            
        self._clear_validation_error(self.job_entry)
        self.log(f"ðŸ”Ž Fetching data for Job: {job_no}", 'weight')
        threading.Thread(target=self._fetch_api_data_worker, args=(job_no,), daemon=True).start()

    def _fetch_api_data_worker(self, job_no):
        """Worker thread for API data fetching"""
        try:
            api_url = self.api_url_var.get()
            if not api_url.endswith('='):
                if '?' in api_url:
                    api_url += '&job_no='
                else:
                    api_url += '?job_no='
            
            full_url = f"{api_url}{job_no}"
            
            # Add API key to URL if provided
            api_key = getattr(self, 'api_key_var', tk.StringVar()).get().strip()
            if api_key:
                separator = '&' if '?' in full_url else '?'
                full_url += f"{separator}api_key={api_key}"
            
            # Log without exposing sensitive data (hide domain, job number and API key)
            domain = api_url.split('//')[1].split('/')[0] if '//' in api_url else api_url.split('/')[0]
            masked_domain = '*****' + domain[-8:] if len(domain) > 8 else domain
            self.log(f"ðŸŒ API Request: {masked_domain}/... (Job: ***{job_no[-4:]})", 'weight')
            response = requests.get(full_url, timeout=15, allow_redirects=True)
            
            self.log(f"ðŸ“¡ Response Status: {response.status_code}", 'weight')
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get('success') and data.get('data'):
                        self.log("âœ… Data fetched successfully!", 'weight')
                        
                        # Store lot weights data if available
                        if 'lot_weights' in data:
                            self.log(f"ðŸ“Š Found dedicated lot_weights data: {len(data['lot_weights'])} lots", 'weight')
                            self.root.after(0, self._display_strip_table, data['data'], data.get('lot_weights', []))
                        else:
                            self.log("ðŸ”„ No dedicated lot_weights found, will extract from strip data", 'weight')
                            self.log(f"ðŸ“¡ Calling _display_strip_table with {len(data['data'])} strips", 'weight')
                            self.root.after(0, self._display_strip_table, data['data'])
                    else:
                        self.log("âš ï¸ No data found for this job number.", 'weight')
                        messagebox.showwarning("No Data", "No data found for this job number.")
                except ValueError:
                    self.log("âŒ Invalid JSON response from API", 'weight')
                    messagebox.showerror("API Error", "Invalid response format from API")
            else:
                self.log(f"âŒ API Error: Status {response.status_code}", 'weight')
                messagebox.showerror("API Error", f"Server returned status code {response.status_code}")
                
        except requests.exceptions.Timeout:
            self.log("â±ï¸ Request timeout - API took too long to respond", 'weight')
            messagebox.showerror("Timeout", "Request timeout - API took too long to respond")
        except requests.exceptions.ConnectionError:
            self.log("ðŸŒ Connection error - Check internet connection", 'weight')
            messagebox.showerror("Connection Error", "Could not connect to API - Check internet connection")
        except Exception as e:
            self.log(f"âŒ Unexpected error: {str(e)}", 'weight')
            messagebox.showerror("API Error", f"Unexpected error: {str(e)}")

    def _display_strip_table(self, strips, lot_weights=None):
        """Display fetched strip data in compact table format"""
        self.log(f"ðŸ” _display_strip_table called with {len(strips)} strips, lot_weights={lot_weights is not None}", 'weight')
        
        # Group strips by lot_no
        lots = {}
        for strip in strips:
            lot_no = strip.get('lot_no', '1')
            lots.setdefault(lot_no, []).append(strip)
            
        self.lots_data = lots
        
        # Store lot weights data - prioritize API lot_weights over strip data
        self.lot_weights_data = {}
        
        # First, try to use the dedicated lot_weights from API
        if lot_weights:
            for lot_weight in lot_weights:
                lot_no = str(lot_weight.get('lot_no', '1'))
                self.lot_weights_data[lot_no] = {
                    'button_weight': float(lot_weight.get('button_weight', 0)),
                    'scrap_weight': float(lot_weight.get('scrap_weight', 0)),
                    'milligram_addition': float(lot_weight.get('milligram_addition', 0))
                }
                self.log(f"ðŸ“Š Lot {lot_no} weights: Button={self.lot_weights_data[lot_no]['button_weight']}, Scrap={self.lot_weights_data[lot_no]['scrap_weight']}", 'weight')
        else:
            # Extract from strip data - this is the main path for your API
            self.log("ðŸ”„ Extracting lot weights from strip data...", 'weight')
            processed_lots = set()  # Track which lots we've processed to avoid duplicates
            
            for strip in strips:
                lot_no = strip.get('lot_no', '1')
                
                # Only process each lot once (use first strip for each lot)
                if lot_no not in processed_lots:
                    processed_lots.add(lot_no)
                    self.log(f"ðŸ” Processing lot {lot_no} - has lot_button_weight: {'lot_button_weight' in strip}, has lot_scrap_weight: {'lot_scrap_weight' in strip}", 'weight')
                    
                    if 'lot_button_weight' in strip and 'lot_scrap_weight' in strip:
                        self.lot_weights_data[lot_no] = {
                            'button_weight': float(strip.get('lot_button_weight', 0)),
                            'scrap_weight': float(strip.get('lot_scrap_weight', 0)),
                            'milligram_addition': float(strip.get('milligram_addition', 0))
                        }
                        self.log(f"âœ… Extracted lot weights for Lot {lot_no}: Button={self.lot_weights_data[lot_no]['button_weight']}, Scrap={self.lot_weights_data[lot_no]['scrap_weight']}", 'weight')
                    else:
                        self.log(f"âš ï¸ Lot {lot_no} strip missing lot weight data", 'weight')
            
            self.log(f"ðŸ“Š Extracted lot weights for {len(self.lot_weights_data)} lots", 'weight')
        
        # Update lot weights info display
        self._update_lot_weights_display()
        
        # Automatically apply lot weights for the currently selected lot
        if hasattr(self, 'manual_lot_var') and self.manual_lot_var.get():
            current_lot = self.manual_lot_var.get()
            if hasattr(self, 'lot_weights_data') and current_lot in self.lot_weights_data:
                self.log(f"âš–ï¸ Auto-applying lot weights for current lot {current_lot}...", 'weight')
                self.apply_lot_weights_to_fields(current_lot)
        
        # Clear previous table
        for widget in self.strip_table_frame.winfo_children():
            widget.destroy()
        
        if not lots:
            ttk.Label(self.strip_table_frame, text="No data available", 
                     font=('Segoe UI', 9, 'italic')).pack(padx=8, pady=8)
            return
        
        table_container = ttk.Frame(self.strip_table_frame)
        table_container.pack(fill='x', padx=8, pady=8)
        
        lot_nos = sorted(lots.keys(), key=lambda x: int(x))
        
        # Lot selection if multiple lots
        if len(lot_nos) > 1:
            lot_frame = ttk.Frame(table_container)
            lot_frame.pack(fill='x', pady=(0, 8))
            
            ttk.Label(lot_frame, text="ðŸ“¦ Lot:", font=('Segoe UI', 8, 'bold')).pack(side='left', padx=(0, 5))
            
            self.lot_var = tk.StringVar(value=lot_nos[0])
            lot_dropdown = ttk.Combobox(lot_frame, textvariable=self.lot_var, 
                                      values=lot_nos, state='readonly', width=8,
                                      font=('Segoe UI', 8))
            lot_dropdown.pack(side='left', padx=(0, 5))
            
            # Update current_lot_no when selection changes
            def on_lot_change(event):
                selected_lot = self.lot_var.get()
                self.current_lot_no = selected_lot
                self.log(f"ðŸ“¦ Lot selection changed to: {selected_lot}", 'weight')
                self._auto_fill_all_fields_for_lot(selected_lot)
            
            lot_dropdown.bind('<<ComboboxSelected>>', on_lot_change)
            
            auto_fill_lot_btn = ttk.Button(lot_frame, text="ðŸ”„ Fill", 
                                         style='Info.TButton',
                                         command=lambda: self._auto_fill_all_fields_for_lot(self.lot_var.get()))
            auto_fill_lot_btn.pack(side='left')
            
            self.current_lot_no = lot_nos[0]
        else:
            self.current_lot_no = lot_nos[0]
            auto_fill_btn = ttk.Button(table_container, text="ðŸ”„ Auto Fill from API", 
                                     style='Success.TButton',
                                     command=lambda: self._auto_fill_all_fields_for_lot(self.current_lot_no))
            auto_fill_btn.pack(fill='x', pady=(0, 5))
        
        # Show compact lot summary
        summary_text = f"ðŸ“Š {len(lot_nos)} lot(s), {sum(len(strips) for strips in lots.values())} strips"
        ttk.Label(table_container, text=summary_text, 
                 font=('Segoe UI', 7, 'italic'), foreground='#6c757d').pack()

    def _update_lot_weights_display(self):
        """Update the lot weights info display"""
        try:
            if hasattr(self, 'lot_weights_data') and self.lot_weights_data:
                lot_count = len(self.lot_weights_data)
                info_text = f"ðŸ“Š API weights loaded for {lot_count} lot(s)"
                if hasattr(self, 'lot_weights_info'):
                    self.lot_weights_info.config(text=info_text, foreground='#28a745')
                
                # Debug: Log the lot weights data
                self.log(f"ðŸ” Lot weights data: {self.lot_weights_data}", 'weight')
            else:
                if hasattr(self, 'lot_weights_info'):
                    self.lot_weights_info.config(text="âš ï¸ No lot weights data available", foreground='#ffc107')
                self.log("âš ï¸ No lot weights data available", 'weight')
        except Exception as e:
            print(f"Error updating lot weights display: {e}")
            self.log(f"âŒ Error updating lot weights display: {e}", 'weight')
    
    def apply_lot_weights_to_fields(self, lot_no):
        """Apply lot weights from API to the weight fields for a specific lot"""
        try:
            if hasattr(self, 'lot_weights_data') and lot_no in self.lot_weights_data:
                lot_data = self.lot_weights_data[lot_no]
                
                # Apply scrap weight
                scrap_weight = lot_data['scrap_weight']
                self.weight_entries['num_scrap_weight'].delete(0, tk.END)
                self.weight_entries['num_scrap_weight'].insert(0, str(scrap_weight))
                self.weight_entries['num_scrap_weight'].configure(style='Success.TEntry')
                
                # Apply button weight
                button_weight = lot_data['button_weight']
                self.weight_entries['buttonweight'].delete(0, tk.END)
                self.weight_entries['buttonweight'].insert(0, str(button_weight))
                self.weight_entries['buttonweight'].configure(style='Success.TEntry')
                
                self.log(f"âœ… Applied API weights for Lot {lot_no}: Scrap={scrap_weight}, Button={button_weight}", 'weight')
                return True
            else:
                self.log(f"âš ï¸ No API weights available for Lot {lot_no}", 'weight')
                return False
        except Exception as e:
            self.log(f"âŒ Error applying lot weights: {e}", 'weight')
            return False
    
    def apply_current_lot_weights(self):
        """Apply lot weights for the currently selected lot"""
        try:
            # Get current lot selection
            current_lot = self.manual_lot_var.get()
            if not current_lot:
                messagebox.showwarning("No Lot Selected", "Please select a lot first")
                return
            
            self.log(f"ðŸ” Applying lot weights for Lot {current_lot}...", 'weight')
            
            # Check if lot weights data exists
            if not hasattr(self, 'lot_weights_data') or not self.lot_weights_data:
                messagebox.showwarning("No Lot Weights", "No lot weights data available. Please fetch data first.")
                return
            
            # Apply weights for the current lot
            if self.apply_lot_weights_to_fields(current_lot):
                messagebox.showinfo("Success", f"âœ… Applied lot weights for Lot {current_lot}")
            else:
                messagebox.showwarning("No Weights", f"No lot weights available for Lot {current_lot}")
                
        except Exception as e:
            self.log(f"âŒ Error applying current lot weights: {e}", 'weight')
            messagebox.showerror("Error", f"Error applying lot weights: {e}")
    
    def on_lot_selection_change(self, event=None):
        """Handle lot selection change to apply weights automatically"""
        try:
            selected_lot = self.manual_lot_var.get()
            if selected_lot and hasattr(self, 'lot_weights_data') and selected_lot in self.lot_weights_data:
                self.log(f"ðŸ”„ Lot changed to {selected_lot}, applying weights...", 'weight')
                self.apply_lot_weights_to_fields(selected_lot)
        except Exception as e:
            self.log(f"âŒ Error handling lot selection change: {e}", 'weight')
    

    def _auto_fill_all_fields_for_lot(self, lot_no):
        """Auto-fill all fields for a specific lot"""
        try:
            # Update current_lot_no to ensure portal selection uses correct lot
            self.current_lot_no = str(lot_no)
            
            # Clear all fields first
            for entry in self.weight_entries.values():
                entry.delete(0, tk.END)
                entry.configure(style='Compact.TEntry')
            
            strips = self.lots_data.get(lot_no, [])
            if not strips:
                messagebox.showwarning("No Data", f"No strips found for Lot {lot_no}")
                return
            
            filled_count = 0
            missing_keys = []
            
            # Fill Strip 1 and Strip 2 data
            for strip in strips:
                strip_no = str(strip.get('strip_no', ''))
                self.log(f"ðŸ” Processing Strip {strip_no} - Available keys: {list(strip.keys())}", 'weight')
                
                if strip_no == '1':
                    mapping = {
                        'num_strip_weight_M11': 'initial',
                        'num_silver_weightM11': 'ag',
                        'num_copper_weightM11': 'cu',
                        'num_lead_weightM11': 'pb',
                        'num_cornet_weightM11': 'cornet',
                        'averagedelta1': 'delta',
                        'num_fineness_reportM11': 'fineness',
                        'num_mean_finenessM11': 'fineness',
                        'str_remarksM11': 'remarks',
                    }
                    
                    for field_id, api_key in mapping.items():
                        if field_id in self.weight_entries:
                            if api_key in strip:
                                value = str(strip[api_key])
                                if value and value != '0' and value != '0.0':
                                    self.weight_entries[field_id].insert(0, value)
                                    self.weight_entries[field_id].configure(style='Success.TEntry')
                                    filled_count += 1
                                    self.log(f"âœ… Strip {strip_no} - {field_id}: {value}", 'weight')
                                else:
                                    self.log(f"âš ï¸ Strip {strip_no} - {field_id}: API returned zero/empty value", 'weight')
                            else:
                                missing_keys.append(f"Strip {strip_no} - {api_key}")
                                self.log(f"âŒ Strip {strip_no} - Missing API key: {api_key}", 'weight')
                            
                elif strip_no == '2':
                    mapping = {
                        'num_strip_weight_M12': 'initial',
                        'num_silver_weightM12': 'ag',
                        'num_copper_weightM12': 'cu',
                        'num_lead_weightM12': 'pb',
                        'num_cornet_weightM12': 'cornet',
                        'num_fineness_report_goldM11': 'fineness',
                    }
                    for field_id, api_key in mapping.items():
                        if field_id in self.weight_entries and api_key in strip:
                            value = str(strip[api_key])
                            if value and value != '0' and value != '0.0':
                                self.weight_entries[field_id].delete(0, tk.END)
                                self.weight_entries[field_id].insert(0, value)
                                filled_count += 1
                                self.log(f"âœ… Strip {strip_no} - {field_id}: {value}", 'weight')
                                self.weight_entries[field_id].configure(style='Success.TEntry')
                            else:
                                self.log(f"âš ï¸ Strip {strip_no} - {field_id}: API returned zero/empty value", 'weight')
                            missing_keys.append(f"Strip {strip_no} - {api_key}")
                            self.log(f"âŒ Strip {strip_no} - Missing API key: {api_key}", 'weight')
                            
                # Note: Check Gold data (C1, C2) is handled separately below
                # as it's stored in dedicated fields in every strip record
            
            # Fill Check Gold data from first strip (Check Gold data is in every strip record)
            if strips:
                first_strip = strips[0]
                self.log(f"ðŸ” Extracting Check Gold data from first strip - Available Check Gold keys: {[k for k in first_strip.keys() if 'check_gold' in k]}", 'weight')
                
                check_gold_mapping = {
                    'num_strip_weight_goldM11': 'check_gold_c1_init',
                    'num_cornet_weight_goldM11': 'check_gold_c1_cornet',
                    'delta11': 'check_gold_c1_delta',
                    'num_silver_weight_goldM11': 'check_gold_c1_ag',
                    'num_copper_weight_goldM11': 'check_gold_c1_cu',
                    'num_lead_weight_goldM11': 'check_gold_c1_pb',
                    'num_strip_weight_goldM12': 'check_gold_c2_init',
                    'num_cornet_weight_goldM12': 'check_gold_c2_cornet',
                    'delta22': 'check_gold_c2_delta',
                    'num_silver_weight_goldM12': 'check_gold_c2_ag',
                    'num_copper_weight_goldM12': 'check_gold_c2_cu',
                    'num_lead_weight_goldM12': 'check_gold_c2_pb',
                }
                
                for field_id, api_key in check_gold_mapping.items():
                    if field_id in self.weight_entries and api_key in first_strip:
                        value = str(first_strip[api_key])
                        if value and value != '0' and value != '0.0':
                            self.weight_entries[field_id].insert(0, value)
                            self.weight_entries[field_id].configure(style='Success.TEntry')
                            filled_count += 1
                            self.log(f"âœ… Check Gold - {field_id}: {value}", 'weight')
                        else:
                            self.log(f"âš ï¸ Check Gold - {field_id}: API returned zero/empty value", 'weight')
                    else:
                        if field_id in self.weight_entries:
                            missing_keys.append(f"Check Gold - {api_key}")
                            self.log(f"âŒ Check Gold - Missing API key: {api_key}", 'weight')
            
            # Use API lot weights if available, otherwise generate random weights
            # Always prioritize API weights over existing values
            self.log(f"ðŸ” Checking lot weights for lot {lot_no}...", 'weight')
            self.log(f"ðŸ” Available lot_weights_data: {getattr(self, 'lot_weights_data', 'Not found')}", 'weight')
            
            if hasattr(self, 'lot_weights_data') and lot_no in self.lot_weights_data:
                # Use API weights - clear existing values first
                scrap_weight = self.lot_weights_data[lot_no]['scrap_weight']
                self.weight_entries['num_scrap_weight'].delete(0, tk.END)
                self.weight_entries['num_scrap_weight'].insert(0, str(scrap_weight))
                self.weight_entries['num_scrap_weight'].configure(style='Success.TEntry')
                filled_count += 1
                self.log(f"âœ… API scrap weight: {scrap_weight}", 'weight')
                
                button_weight = self.lot_weights_data[lot_no]['button_weight']
                self.weight_entries['buttonweight'].delete(0, tk.END)
                self.weight_entries['buttonweight'].insert(0, str(button_weight))
                self.weight_entries['buttonweight'].configure(style='Success.TEntry')
                filled_count += 1
                self.log(f"âœ… API button weight: {button_weight}", 'weight')
            else:
                # Fallback: only generate if fields are empty
                if not self.weight_entries['num_scrap_weight'].get().strip():
                    scrap_weight = round(random.uniform(390, 420), 3)
                    self.weight_entries['num_scrap_weight'].insert(0, str(scrap_weight))
                    self.weight_entries['num_scrap_weight'].configure(style='Warning.TEntry')
                    filled_count += 1
                    self.log(f"ðŸ”„ Generated scrap weight: {scrap_weight}", 'weight')
                
                if not self.weight_entries['buttonweight'].get().strip():
                    button_weight = round(random.uniform(380, 410), 3)
                    self.weight_entries['buttonweight'].insert(0, str(button_weight))
                    self.weight_entries['buttonweight'].configure(style='Warning.TEntry')
                    filled_count += 1
                    self.log(f"ðŸ”„ Generated button weight: {button_weight}", 'weight')
            
            # Reset styling after delay
            self.root.after(3000, self._reset_entry_styles)
            
            # Summary with missing keys info
            if missing_keys:
                self.log(f"âš ï¸ Missing API keys: {', '.join(missing_keys)}", 'weight')
            
            self.log(f"âœ… Auto-filled {filled_count} fields for Lot {lot_no}", 'weight')
            
            # Automatically apply lot weights if available
            if hasattr(self, 'lot_weights_data') and lot_no in self.lot_weights_data:
                self.log(f"âš–ï¸ Auto-applying lot weights for Lot {lot_no}...", 'weight')
                self.apply_lot_weights_to_fields(lot_no)
            
            messagebox.showinfo("Success", f"âœ… Auto-filled {filled_count} fields for Lot {lot_no}")
            
        except Exception as e:
            self.log(f"âŒ Error auto-filling lot {lot_no}: {str(e)}", 'weight')
            messagebox.showerror("Error", f"Error auto-filling: {str(e)}")
    
    def _reset_entry_styles(self):
        """Reset all entry styles to default"""
        for entry in self.weight_entries.values():
            entry.configure(style='Compact.TEntry')
            
    def run(self):
        """Start the desktop application"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Add global exception handler
        def handle_exception(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                # Handle Ctrl+C gracefully
                self.log("âš ï¸ Application interrupted by user", 'status')
                self.on_closing()
            else:
                # Log unexpected errors but don't crash
                self.log(f"âŒ Unexpected error: {exc_type.__name__}: {exc_value}", 'status')
                return False  # Don't suppress the exception, just log it
        
        import sys
        sys.excepthook = handle_exception
        
        self.root.mainloop()
        
    def on_closing(self):
        """Handle application closing"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        self.root.destroy()

    def get_request_no_from_api(self, job_no):
        """Get Request No from API using Job No"""
        try:
            if not hasattr(self, 'request_api_url_var'):
                self.log("âš ï¸ Request No API URL not configured", 'weight')
                return None
                
            api_url = self.request_api_url_var.get().strip()
            if not api_url:
                self.log("âš ï¸ Request No API URL is empty", 'weight')
                return None
                
            # Get API key if configured
            api_key = getattr(self, 'api_key_var', tk.StringVar()).get().strip()
            
            # Ensure URL ends with job_no parameter
            if not api_url.endswith('='):
                if '?' in api_url:
                    api_url += '&job_no='
                else:
                    api_url += '?job_no='
                    
            full_url = f"{api_url}{job_no}"
            
            # Add API key to URL if provided
            if api_key:
                separator = '&' if '?' in full_url else '?'
                full_url += f"{separator}api_key={api_key}"
            
            # Log without exposing sensitive data (hide domain, job number and API key)
            domain = api_url.split('//')[1].split('/')[0] if '//' in api_url else api_url.split('/')[0]
            masked_domain = '*****' + domain[-8:] if len(domain) > 8 else domain
            self.log(f"ðŸŒ Request No API: {masked_domain}/... (Job: ***{job_no[-4:]})", 'weight')
            
            # Make API request with timeout
            response = requests.get(full_url, timeout=3)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get('success') and data.get('request_no'):
                        request_no = data['request_no']
                        self.log(f"âœ… Found Request No: {request_no}", 'weight')
                        return request_no
                    elif data.get('success') and data.get('data') and data['data'].get('request_no'):
                        request_no = data['data']['request_no']
                        self.log(f"âœ… Found Request No: {request_no}", 'weight')
                        return request_no
                    else:
                        self.log(f"âš ï¸ No Request No found for Job No: {job_no}", 'weight')
                        return None
                except ValueError:
                    # Try to parse as plain text
                    text_response = response.text.strip()
                    if text_response and text_response.isdigit():
                        self.log(f"âœ… Found Request No: {text_response}", 'weight')
                        return text_response
                    else:
                        self.log(f"âš ï¸ Invalid API response format", 'weight')
                        return None
            else:
                self.log(f"âŒ API Error: Status {response.status_code}", 'weight')
                return None
                
        except requests.exceptions.Timeout:
            self.log("â±ï¸ Request No API timeout", 'weight')
            return None
        except requests.exceptions.ConnectionError:
            self.log("ðŸŒ Request No API connection error", 'weight')
            return None
        except Exception as e:
            self.log(f"âŒ Request No API error: {str(e)}", 'weight')
            return None

    def on_job_no_key_release(self, event=None):
        """Handle key release for instant Request No lookup and job reports data loading"""
        try:
            job_no = self.job_entry.get().strip()
            
            # Only query if job number is at least 9 digits
            if len(job_no) >= 9:
                self.log(f"ðŸ” Quick lookup for Job No: {job_no}", 'weight')
                
                # Get request number
                request_no = self.get_request_no_from_api(job_no)
                if request_no:
                    self.request_entry.delete(0, tk.END)
                    self.request_entry.insert(0, request_no)
                    self.log(f"âœ… Auto-filled Request No: {request_no}", 'weight')
                
                # Automatically fetch job reports data
                self.log(f"ðŸ”Ž Auto-loading reports data for Job: {job_no}", 'weight')
                threading.Thread(target=self._fetch_api_data_worker, args=(job_no,), daemon=True).start()
                    
        except Exception as e:
            self.log(f"âŒ Error in key release handler: {str(e)}", 'weight')

    def on_job_no_change(self, event=None):
        """Handle focus out and enter key for Request No lookup and job reports data loading"""
        try:
            job_no = self.job_entry.get().strip()
            if not job_no:
                return
                
            # Only query if we haven't already found it via key release
            current_request = self.request_entry.get().strip()
            if not current_request:
                self.log(f"ðŸ” Final lookup for Job No: {job_no}", 'weight')
                request_no = self.get_request_no_from_api(job_no)
                
                if request_no:
                    self.request_entry.delete(0, tk.END)
                    self.request_entry.insert(0, request_no)
                    self.log(f"âœ… Auto-filled Request No: {request_no}", 'weight')
            
            # Automatically fetch job reports data if job number is valid
            if len(job_no) >= 9:
                self.log(f"ðŸ”Ž Auto-loading reports data for Job: {job_no}", 'weight')
                threading.Thread(target=self._fetch_api_data_worker, args=(job_no,), daemon=True).start()
                    
        except Exception as e:
            self.log(f"âŒ Error in job number change handler: {str(e)}", 'weight')

    def setup_accept_request_tab(self):
        """Setup Accept Request tab with full automation"""
        accept_frame = ttk.Frame(self.notebook)
        self.notebook.add(accept_frame, text="âœ… Accept Request")
        
        # Main horizontal layout
        main_horizontal = ttk.Frame(accept_frame)
        main_horizontal.pack(fill='both', expand=True, padx=8, pady=8)
        
        # LEFT SECTION - Controls (30% width)
        left_section = ttk.Frame(main_horizontal)
        left_section.pack(side='left', fill='y', padx=(0, 8))
        
        # RIGHT SECTION - Request List (70% width)
        right_section = ttk.Frame(main_horizontal)
        right_section.pack(side='right', fill='both', expand=True)
        
        # === LEFT SECTION CONTENT ===
        self.setup_accept_request_left_section(left_section)
        
        # === RIGHT SECTION CONTENT ===
        self.setup_accept_request_right_section(right_section)
        
    def setup_accept_request_left_section(self, parent):
        """Setup left section with controls and settings"""
        
        # Controls card
        controls_card = ttk.LabelFrame(parent, text="ðŸŽ® Controls", style='Compact.TLabelframe')
        controls_card.pack(fill='x', pady=(0, 8))
        
        controls_frame = ttk.Frame(controls_card)
        controls_frame.pack(fill='x', padx=8, pady=8)
        
        # Fetch Requests button
        
        # Reception Browser Controls
        browser_frame = ttk.LabelFrame(controls_frame, text="ðŸŒ Reception Browser", style='Compact.TLabelframe')
        browser_frame.pack(fill='x', pady=(0, 5))
        
        bf_grid = ttk.Frame(browser_frame)
        bf_grid.pack(fill='x', padx=4, pady=4)
        
        self.open_reception_btn = ttk.Button(bf_grid, text="ðŸš€ Open", style='Compact.TButton', command=self.open_reception_browser)
        self.open_reception_btn.pack(side='left', fill='x', expand=True, padx=(0, 2))
        
        self.close_reception_btn = ttk.Button(bf_grid, text="âŒ Close", style='Danger.TButton', command=self.close_reception_browser, state='disabled')
        self.close_reception_btn.pack(side='left', fill='x', expand=True, padx=(2, 0))

        # Fetch Requests button
        self.fetch_requests_btn = ttk.Button(controls_frame, text="ðŸ“‹ Fetch Requests", 
                                           style='Info.TButton', command=self.fetch_request_list)
        self.fetch_requests_btn.pack(fill='x', pady=2)
        
        # Auto Acknowledge All button
        self.auto_acknowledge_all_btn = ttk.Button(controls_frame, text="ðŸ¤– Auto Acknowledge All", 
                                                 style='Success.TButton', command=self.auto_acknowledge_all_requests,
                                                 state='disabled')
        self.auto_acknowledge_all_btn.pack(fill='x', pady=2)
        
        # Clear List button
        self.clear_requests_btn = ttk.Button(controls_frame, text="ðŸ§¹ Clear List", 
                                          style='Danger.TButton', command=self.clear_request_list)
        self.clear_requests_btn.pack(fill='x', pady=2)
        
        # Settings card
        settings_card = ttk.LabelFrame(parent, text="âš™ï¸ Acknowledge Settings", style='Compact.TLabelframe')
        settings_card.pack(fill='x', pady=(0, 8))
        
        settings_frame = ttk.Frame(settings_card)
        settings_frame.pack(fill='x', padx=8, pady=8)
        
        # AHC Remarks (disabled - not needed)
        ach_remarks_label = ttk.Label(settings_frame, text="â„¹ï¸ AHC Remarks: Not required for automation", 
                                    font=('Segoe UI', 8, 'italic'), foreground='#6c757d')
        ach_remarks_label.pack(anchor='w', pady=2)
        
        # Auto-fill quantity and weight checkbox
        self.auto_fill_qty_weight_var = tk.BooleanVar(value=True)
        auto_fill_cb = ttk.Checkbutton(settings_frame, text="Auto-fill quantity & weight from declaration", 
                                     variable=self.auto_fill_qty_weight_var)
        auto_fill_cb.pack(anchor='w', pady=2)
        
        # Auto-print voucher checkbox (always enabled now)
        auto_print_label = ttk.Label(settings_frame, text="âœ… Voucher Print: Always enabled", 
                                   font=('Segoe UI', 8, 'italic'), foreground='#28a745')
        auto_print_label.pack(anchor='w', pady=2)
        
        # Status card
        status_card = ttk.LabelFrame(parent, text="ðŸ“Š Status", style='Compact.TLabelframe')
        status_card.pack(fill='x', pady=(0, 8))
        
        status_frame = ttk.Frame(status_card)
        status_frame.pack(fill='x', padx=8, pady=8)
        
        # Status labels
        self.total_requests_label = ttk.Label(status_frame, text="Total Requests: 0", font=('Segoe UI', 8))
        self.total_requests_label.pack(anchor='w', pady=1)
        
        self.pending_requests_label = ttk.Label(status_frame, text="Pending: 0", font=('Segoe UI', 8))
        self.pending_requests_label.pack(anchor='w', pady=1)
        
        self.completed_requests_label = ttk.Label(status_frame, text="Completed: 0", font=('Segoe UI', 8))
        self.completed_requests_label.pack(anchor='w', pady=1)
        
        # Progress bar
        self.acknowledge_progress = ttk.Progressbar(status_frame, mode='determinate', length=200)
        self.acknowledge_progress.pack(fill='x', pady=5)
        
        # Log card
        log_card = ttk.LabelFrame(parent, text="ðŸ“ Acknowledge Log", style='Compact.TLabelframe')
        log_card.pack(fill='both', expand=True)
        
        self.acknowledge_log = scrolledtext.ScrolledText(log_card, height=8, font=('Consolas', 7), 
                                                       bg='#f8f9fa', fg='#495057', wrap=tk.WORD)
        self.acknowledge_log.pack(fill='both', expand=True, padx=8, pady=8)
        
    def setup_accept_request_right_section(self, parent):
        """Setup right section with request list table"""
        
        # Request List card
        list_card = ttk.LabelFrame(parent, text="ðŸ“‹ Request List", style='Compact.TLabelframe')
        list_card.pack(fill='both', expand=True)
        
        # Create Treeview for request list
        columns = ('S.No.', 'Request No.', 'Request Date', 'Jeweller Name', 'Jeweller Address', 'Status', 'Action')
        
        self.request_tree = ttk.Treeview(list_card, columns=columns, show='headings', height=15)
        
        # Configure columns
        for col in columns:
            self.request_tree.heading(col, text=col)
            if col in ['S.No.', 'Request No.', 'Status']:
                self.request_tree.column(col, width=80, minwidth=80)
            elif col == 'Request Date':
                self.request_tree.column(col, width=100, minwidth=100)
            elif col == 'Jeweller Name':
                self.request_tree.column(col, width=150, minwidth=150)
            elif col == 'Jeweller Address':
                self.request_tree.column(col, width=200, minwidth=200)
            elif col == 'Action':
                self.request_tree.column(col, width=120, minwidth=120)
        
        # Add scrollbars
        tree_scroll_y = ttk.Scrollbar(list_card, orient='vertical', command=self.request_tree.yview)
        tree_scroll_x = ttk.Scrollbar(list_card, orient='horizontal', command=self.request_tree.xview)
        self.request_tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        
        # Pack tree and scrollbars
        self.request_tree.pack(side='left', fill='both', expand=True)
        tree_scroll_y.pack(side='right', fill='y')
        tree_scroll_x.pack(side='bottom', fill='x')
        
        # Bind double-click event for manual acknowledge
        self.request_tree.bind('<Double-1>', self.on_request_double_click)
        
        # Store request data
        self.request_data = []
        
    def fetch_request_list(self):
        """Fetch request list from MANAK portal"""
        # Flexible check: allow if either driver is available
        if not self.reception_driver and (not self.driver or not self.logged_in):
            messagebox.showwarning("Not Ready", "Please open browser (QM or Reception) and login first")
            return
            
        self.log("ðŸ” Fetching request list...", 'acknowledge')
        threading.Thread(target=self._fetch_request_list_worker, daemon=True).start()
        
    def _fetch_request_list_worker(self):
        """Worker thread for fetching request list with pagination support"""
        # Determine which driver to use
        driver = self.reception_driver if self.reception_driver else self.driver
        if not driver: return

        loading_dialog = None
        try:
            loading_dialog = LoadingDialog(self.root, "Fetching Requests", "Loading request list from MANAK portal...")
            
            # Navigate to request list page
            loading_dialog.update_status("Navigating to request list page...")
            request_list_url = "https://newmanak.uat.dcservices.in/MANAK/assayingAH_List?hmType=HMRD"
            driver.get(request_list_url)
            time.sleep(1)
            
            # Wait for page to load
            loading_dialog.update_status("Waiting for page to load...")
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            
            all_requests = []
            current_page = 1
            max_pages = 20  # Limit to 20 pages to prevent infinite loops
            
            while current_page <= max_pages:
                loading_dialog.update_status(f"Parsing page {current_page}...")
                self.log(f"ðŸ“„ Processing page {current_page}...", 'acknowledge')
                
                # Find the request table
                tables = driver.find_elements(By.TAG_NAME, "table")
                request_table = None
                
                for table in tables:
                    try:
                        # Look for table with request data
                        rows = table.find_elements(By.TAG_NAME, "tr")
                        if len(rows) > 1:  # Has data rows
                            first_row = rows[1]  # First data row
                            cells = first_row.find_elements(By.TAG_NAME, "td")
                            if len(cells) >= 6:  # Has enough columns
                                # Check if first cell contains a number (S.No.)
                                if cells[0].text.strip().replace('.', '').isdigit():
                                    request_table = table
                                    break
                    except:
                        continue
                
                if not request_table:
                    self.log(f"âš ï¸ No request table found on page {current_page}", 'acknowledge')
                    break
                
                # Parse table data
                rows = request_table.find_elements(By.TAG_NAME, "tr")
                page_requests = []
                
                for i, row in enumerate(rows[1:], 1):  # Skip header row
                    try:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) >= 7:
                            s_no = cells[0].text.strip()
                            request_no = cells[1].text.strip()
                            request_date = cells[2].text.strip()
                            jeweller_name = cells[3].text.strip()
                            jeweller_address = cells[4].text.strip()
                            status = cells[5].text.strip()
                            
                            # Find acknowledge link
                            acknowledge_link = None
                            try:
                                link_element = row.find_element(By.XPATH, ".//a[contains(text(), 'Acknowledge')]")
                                acknowledge_link = link_element.get_attribute('href')
                            except:
                                pass
                            
                            if request_no and acknowledge_link:
                                page_requests.append({
                                    's_no': s_no,
                                    'request_no': request_no,
                                    'request_date': request_date,
                                    'jeweller_name': jeweller_name,
                                    'jeweller_address': jeweller_address,
                                    'status': status,
                                    'acknowledge_url': acknowledge_link
                                })
                                
                    except Exception as e:
                        self.log(f"âš ï¸ Error parsing row {i} on page {current_page}: {str(e)}", 'acknowledge')
                        continue
                
                all_requests.extend(page_requests)
                self.log(f"âœ… Found {len(page_requests)} requests on page {current_page} (Total: {len(all_requests)})", 'acknowledge')
                
                # Check if there's a next page
                try:
                    # Try to find "Next" button or link
                    next_button = None
                    
                    # Method 1: Look for pagination with "Next" text
                    try:
                        next_button = driver.find_element(By.XPATH, "//a[contains(text(), 'Next') or contains(text(), 'next') or contains(text(), 'â€º') or contains(text(), 'Â»')]")
                    except:
                        pass
                    
                    # Method 2: Look for pagination with page numbers and next arrow
                    if not next_button:
                        try:
                            next_button = driver.find_element(By.XPATH, "//a[@class='next' or contains(@class, 'next')]")
                        except:
                            pass
                    
                    # Method 3: Look for specific page number higher than current
                    if not next_button:
                        try:
                            next_page_num = current_page + 1
                            next_button = driver.find_element(By.XPATH, f"//a[text()='{next_page_num}']")
                        except:
                            pass
                    
                    if next_button and next_button.is_displayed() and next_button.is_enabled():
                        # Check if button is actually clickable (not disabled)
                        button_class = next_button.get_attribute('class') or ''
                        if 'disabled' not in button_class.lower():
                            self.log(f"ðŸ”„ Navigating to page {current_page + 1}...", 'acknowledge')
                            next_button.click()
                            time.sleep(1)  # Wait for page to load
                            current_page += 1
                        else:
                            self.log(f"âœ… Reached last page (page {current_page})", 'acknowledge')
                            break
                    else:
                        self.log(f"âœ… No more pages found (stopped at page {current_page})", 'acknowledge')
                        break
                        
                except Exception as e:
                    self.log(f"â„¹ï¸ No next page button found on page {current_page}: {str(e)}", 'acknowledge')
                    break
            
            # Update UI with all collected request data
            self.root.after(0, self._update_request_list_ui, all_requests)
            
            loading_dialog.update_status("Done!")
            loading_dialog.update_message(f"Found {len(all_requests)} requests across {current_page} page(s)")
            time.sleep(1)
            loading_dialog.close()
            
            if all_requests:
                self.log(f"âœ… Successfully fetched {len(all_requests)} requests from {current_page} page(s)", 'acknowledge')
                messagebox.showinfo("Success", f"âœ… Found {len(all_requests)} requests to acknowledge across {current_page} page(s)!")
            else:
                self.log("âš ï¸ No requests found to acknowledge", 'acknowledge')
                messagebox.showwarning("No Requests", "No requests found to acknowledge")
                
        except Exception as e:
            if loading_dialog:
                loading_dialog.close()
            self.log(f"âŒ Error fetching request list: {str(e)}", 'acknowledge')
            messagebox.showerror("Error", f"Error fetching request list: {str(e)}")
            
    def _update_request_list_ui(self, requests):
        """Update the request list UI with fetched data"""
        # Clear existing data
        for item in self.request_tree.get_children():
            self.request_tree.delete(item)
        
        self.request_data = requests
        
        # Add requests to treeview
        for request in requests:
            self.request_tree.insert('', 'end', values=(
                request['s_no'],
                request['request_no'],
                request['request_date'],
                request['jeweller_name'],
                request['jeweller_address'],
                request['status'],
                "ðŸ”„ Acknowledge"
            ))
        
        # Update status labels
        total = len(requests)
        pending = len([r for r in requests if r['status'] == 'New Request'])
        completed = total - pending
        
        self.total_requests_label.config(text=f"Total Requests: {total}")
        self.pending_requests_label.config(text=f"Pending: {pending}")
        self.completed_requests_label.config(text=f"Completed: {completed}")
        
        # Enable auto acknowledge button if there are pending requests
        if pending > 0:
            self.auto_acknowledge_all_btn.config(state='normal')
        else:
            self.auto_acknowledge_all_btn.config(state='disabled')
            
    def clear_request_list(self):
        """Clear the request list"""
        for item in self.request_tree.get_children():
            self.request_tree.delete(item)
        
        self.request_data = []
        
        # Reset status labels
        self.total_requests_label.config(text="Total Requests: 0")
        self.pending_requests_label.config(text="Pending: 0")
        self.completed_requests_label.config(text="Completed: 0")
        
        # Disable auto acknowledge button
        self.auto_acknowledge_all_btn.config(state='disabled')
        
        self.log("ðŸ§¹ Request list cleared", 'acknowledge')
        
    def on_request_double_click(self, event):
        """Handle double-click on request row for manual acknowledge"""
        selection = self.request_tree.selection()
        if selection:
            item = selection[0]
            values = self.request_tree.item(item, 'values')
            request_no = values[1]  # Request No is in second column
            
            # Find the request data
            request = None
            for req in self.request_data:
                if req['request_no'] == request_no:
                    request = req
                    break
            
            if request:
                response = messagebox.askyesno("Acknowledge Request", 
                                             f"Do you want to acknowledge request {request_no}?")
                if response:
                    threading.Thread(target=self._acknowledge_single_request, 
                                   args=(request,), daemon=True).start()
                    
    def auto_acknowledge_all_requests(self):
        """Automatically acknowledge all pending requests"""
        pending_requests = [req for req in self.request_data if req['status'] == 'New Request']
        
        if not pending_requests:
            messagebox.showinfo("No Pending Requests", "No pending requests to acknowledge")
            return
            
        response = messagebox.askyesno("Auto Acknowledge All", 
                                     f"Do you want to automatically acknowledge all {len(pending_requests)} pending requests?")
        if response:
            threading.Thread(target=self._auto_acknowledge_all_worker, 
                           args=(pending_requests,), daemon=True).start()
            
    def _auto_acknowledge_all_worker(self, requests):
        """Worker thread for auto acknowledging all requests"""
        loading_dialog = None
        try:
            loading_dialog = LoadingDialog(self.root, "Auto Acknowledge All", 
                                         f"Processing {len(requests)} requests...")
            
            total = len(requests)
            completed = 0
            failed = 0
            
            # Update progress bar
            self.acknowledge_progress['maximum'] = total
            self.acknowledge_progress['value'] = 0
            
            for i, request in enumerate(requests, 1):
                try:
                    loading_dialog.update_status(f"Processing request {i}/{total}: {request['request_no']}")
                    loading_dialog.update_message(f"Acknowledging {request['jeweller_name']}...")
                    
                    success = self._acknowledge_single_request_internal(request)
                    
                    if success:
                        completed += 1
                        self.log(f"âœ… Acknowledged request {request['request_no']}", 'acknowledge')
                    else:
                        failed += 1
                        self.log(f"âŒ Failed to acknowledge request {request['request_no']}", 'acknowledge')
                        
                except Exception as e:
                    failed += 1
                    self.log(f"âŒ Error acknowledging request {request['request_no']}: {str(e)}", 'acknowledge')
                
                # Update progress
                self.acknowledge_progress['value'] = i
                self.root.update()
                
                # Small delay between requests
                time.sleep(0.5)  # Reduced from 2 to 0.5 seconds
            
            # Final update
            loading_dialog.update_status("Done!")
            loading_dialog.update_message(f"Completed: {completed}, Failed: {failed}")
            time.sleep(2)
            loading_dialog.close()
            
            # Show results
            messagebox.showinfo("Auto Acknowledge Complete", 
                              f"âœ… Completed: {completed}\nâŒ Failed: {failed}")
            
            # Refresh the request list
            self.fetch_request_list()
            
        except Exception as e:
            if loading_dialog:
                loading_dialog.close()
            self.log(f"âŒ Error in auto acknowledge: {str(e)}", 'acknowledge')
            messagebox.showerror("Error", f"Error in auto acknowledge: {str(e)}")
            
    def _acknowledge_single_request(self, request):
        """Acknowledge a single request (for manual acknowledge)"""
        try:
            success = self._acknowledge_single_request_internal(request)
            
            if success:
                self.log(f"âœ… Successfully acknowledged request {request['request_no']}", 'acknowledge')
                messagebox.showinfo("Success", f"âœ… Request {request['request_no']} acknowledged successfully!")
            else:
                self.log(f"âŒ Failed to acknowledge request {request['request_no']}", 'acknowledge')
                messagebox.showerror("Error", f"âŒ Failed to acknowledge request {request['request_no']}")
                
        except Exception as e:
            self.log(f"âŒ Error acknowledging request {request['request_no']}: {str(e)}", 'acknowledge')
            messagebox.showerror("Error", f"Error acknowledging request: {str(e)}")
            
    def _acknowledge_single_request_internal(self, request):
        """Internal method to acknowledge a single request"""
        # Determine which driver to use
        driver = self.reception_driver if self.reception_driver else self.driver
        if not driver: return False

        try:
            # Step 1: Open acknowledge page
            self.log(f"ðŸ”— Opening acknowledge page for request {request['request_no']}", 'acknowledge')
            driver.get(request['acknowledge_url'])
            time.sleep(1)  # Reduced from 3 to 1 second
            
            # Step 2: Wait for page to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "form"))
            )
            
            # Step 3: Fill the form
            self.log("ðŸ“ Filling acknowledge form...", 'acknowledge')
            
            # Generate Tag ID - Select "Yes" radio button
            try:
                # Method 1: Try by exact ID
                tag_id_yes_radio = driver.find_element(By.ID, "strRadioTag_yes")
                if not tag_id_yes_radio.is_selected():
                    tag_id_yes_radio.click()
                    time.sleep(0.2)  # Reduced from 0.5 to 0.2 seconds
                    self.log("âœ… Selected 'Yes' for Generate Tag ID (Method 1)", 'acknowledge')
                else:
                    self.log("âœ… Generate Tag ID 'Yes' already selected", 'acknowledge')
            except Exception as e:
                self.log(f"âš ï¸ Method 1 failed: {str(e)}", 'acknowledge')
                try:
                    # Method 2: Try by name and value
                    tag_id_yes_radio = driver.find_element(By.XPATH, "//input[@name='strRadioTag' and @value='Y']")
                    if not tag_id_yes_radio.is_selected():
                        tag_id_yes_radio.click()
                        time.sleep(0.2)  # Reduced from 0.5 to 0.2 seconds
                        self.log("âœ… Selected 'Yes' for Generate Tag ID (Method 2)", 'acknowledge')
                    else:
                        self.log("âœ… Generate Tag ID 'Yes' already selected", 'acknowledge')
                except Exception as e2:
                    self.log(f"âš ï¸ Method 2 failed: {str(e2)}", 'acknowledge')
                    try:
                        # Method 3: Try by label text
                        yes_label = driver.find_element(By.XPATH, "//label[contains(text(), 'Yes')]//input[@type='radio']")
                        if not yes_label.is_selected():
                            yes_label.click()
                            time.sleep(0.2)  # Reduced from 0.5 to 0.2 seconds
                            self.log("âœ… Selected 'Yes' for Generate Tag ID (Method 3)", 'acknowledge')
                        else:
                            self.log("âœ… Generate Tag ID 'Yes' already selected", 'acknowledge')
                    except Exception as e3:
                        self.log(f"âš ï¸ Could not select Generate Tag ID: {str(e3)}", 'acknowledge')
            
            # Auto-fill quantity and weight if enabled
            if self.auto_fill_qty_weight_var.get():
                self._auto_fill_quantity_and_weight(driver)
            
            # Skip filling AHC Receiving Remarks - not needed
            self.log("â„¹ï¸ Skipping AHC Receiving Remarks (not required)", 'acknowledge')
            
            # Step 4: Click Add button
            try:
                add_button = driver.find_element(By.XPATH, "//input[@type='button' and @value='Add']")
                if add_button.is_displayed() and add_button.is_enabled():
                    add_button.click()
                    self.log("âœ… Clicked Add button", 'acknowledge')
                    time.sleep(1)  # Reduced from 3 to 1 second
                else:
                    raise Exception("Add button not interactable")
            except Exception as e:
                self.log(f"âŒ Could not click Add button: {str(e)}", 'acknowledge')
                return False
            
            # Step 5: Handle the redirect and accept all items
            current_url = driver.current_url
            if 'message=' in current_url:
                self.log("ðŸ”„ Redirected to accept page, accepting all items...", 'acknowledge')
                
                # Wait for page to fully load
                time.sleep(0.5)  # Reduced from 2 to 0.5 seconds
                
                # Step 5a: Find and click the "select all" checkbox with multiple methods
                select_all_clicked = False
                
                # Method 1: Try by exact class name and structure
                try:
                    select_all_checkbox = driver.find_element(By.XPATH, "//th[contains(text(), 'Accept')]//input[@type='checkbox' and contains(@class, 'selectall')]")
                    if select_all_checkbox.is_displayed():
                        if not select_all_checkbox.is_selected():
                            select_all_checkbox.click()
                            time.sleep(0.3)  # Reduced from 1 to 0.3 seconds
                            self.log("âœ… Clicked 'Select All' checkbox in Accept header (Method 1)", 'acknowledge')
                            select_all_clicked = True
                        else:
                            self.log("âœ… Select All checkbox already selected", 'acknowledge')
                            select_all_clicked = True
                except Exception as e:
                    self.log(f"âš ï¸ Method 1 failed: {str(e)}", 'acknowledge')
                
                # Method 2: Try by finding checkbox in Accept column header
                if not select_all_clicked:
                    try:
                        # Find table with Accept column
                        tables = driver.find_elements(By.TAG_NAME, "table")
                        for table in tables:
                            try:
                                # Look for Accept column header
                                accept_header = table.find_element(By.XPATH, ".//th[contains(text(), 'Accept')]")
                                # Find checkbox in the same row or nearby
                                select_all_checkbox = accept_header.find_element(By.XPATH, ".//input[@type='checkbox']")
                                if select_all_checkbox.is_displayed():
                                    if not select_all_checkbox.is_selected():
                                        select_all_checkbox.click()
                                        time.sleep(0.3)  # Reduced from 1 to 0.3 seconds
                                        self.log("âœ… Clicked 'Select All' checkbox (Method 2)", 'acknowledge')
                                        select_all_clicked = True
                                        break
                            except:
                                continue
                    except Exception as e:
                        self.log(f"âš ï¸ Method 2 failed: {str(e)}", 'acknowledge')
                
                # Method 3: Try by finding first checkbox in table
                if not select_all_clicked:
                    try:
                        select_all_checkbox = driver.find_element(By.XPATH, "//table//input[@type='checkbox'][1]")
                        if select_all_checkbox.is_displayed():
                            if not select_all_checkbox.is_selected():
                                select_all_checkbox.click()
                                time.sleep(0.3)  # Reduced from 1 to 0.3 seconds
                                self.log("âœ… Clicked first checkbox in table (Method 3)", 'acknowledge')
                                select_all_clicked = True
                    except Exception as e:
                        self.log(f"âš ï¸ Method 3 failed: {str(e)}", 'acknowledge')
                
                if not select_all_clicked:
                    self.log("âŒ Could not find or click Select All checkbox", 'acknowledge')
                
                # Step 6: Click Voucher Print with multiple methods
                voucher_clicked = False
                
                # Method 1: Try by href containing getAHCRceiptJrxmlReportVoucher
                try:
                    voucher_link = driver.find_element(By.XPATH, "//a[contains(@href, 'getAHCRceiptJrxmlReportVoucher')]")
                    if voucher_link.is_displayed():
                        voucher_link.click()
                        time.sleep(0.5)  # Reduced from 2 to 0.5 seconds
                        self.log("âœ… Clicked Voucher Print link (Method 1)", 'acknowledge')
                        voucher_clicked = True
                except Exception as e:
                    self.log(f"âš ï¸ Voucher Method 1 failed: {str(e)}", 'acknowledge')
                
                # Method 2: Try by text containing "Voucher Print"
                if not voucher_clicked:
                    try:
                        voucher_link = driver.find_element(By.XPATH, "//a[contains(text(), 'Voucher Print')]")
                        if voucher_link.is_displayed():
                            voucher_link.click()
                            time.sleep(0.5)  # Reduced from 2 to 0.5 seconds
                            self.log("âœ… Clicked Voucher Print link (Method 2)", 'acknowledge')
                            voucher_clicked = True
                    except Exception as e:
                        self.log(f"âš ï¸ Voucher Method 2 failed: {str(e)}", 'acknowledge')
                
                # Method 3: Try by button with Voucher Print text
                if not voucher_clicked:
                    try:
                        voucher_button = driver.find_element(By.XPATH, "//input[@type='button' and contains(@value, 'Voucher')]")
                        if voucher_button.is_displayed():
                            voucher_button.click()
                            time.sleep(0.5)  # Reduced from 2 to 0.5 seconds
                            self.log("âœ… Clicked Voucher Print button (Method 3)", 'acknowledge')
                            voucher_clicked = True
                    except Exception as e:
                        self.log(f"âš ï¸ Voucher Method 3 failed: {str(e)}", 'acknowledge')
                
                # Method 4: Try by any element containing "Voucher"
                if not voucher_clicked:
                    try:
                        voucher_element = driver.find_element(By.XPATH, "//*[contains(text(), 'Voucher') and contains(text(), 'Print')]")
                        if voucher_element.is_displayed():
                            voucher_element.click()
                            time.sleep(0.5)  # Reduced from 2 to 0.5 seconds
                            self.log("âœ… Clicked Voucher Print element (Method 4)", 'acknowledge')
                            voucher_clicked = True
                    except Exception as e:
                        self.log(f"âš ï¸ Voucher Method 4 failed: {str(e)}", 'acknowledge')
                
                if not voucher_clicked:
                    self.log("âŒ Could not find or click Voucher Print", 'acknowledge')
                
                # Step 7: Click Submit with multiple methods
                submit_clicked = False
                
                # Method 1: Try by value="Submit"
                try:
                    submit_button = driver.find_element(By.XPATH, "//input[@type='button' and @value='Submit']")
                    if submit_button.is_displayed() and submit_button.is_enabled():
                        submit_button.click()
                        time.sleep(0.5)  # Reduced from 2 to 0.5 seconds
                        self.log("âœ… Clicked Submit button (Method 1)", 'acknowledge')
                        submit_clicked = True
                except Exception as e:
                    self.log(f"âš ï¸ Submit Method 1 failed: {str(e)}", 'acknowledge')
                
                # Method 2: Try by text containing "Submit"
                if not submit_clicked:
                    try:
                        submit_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Submit')]")
                        if submit_button.is_displayed():
                            submit_button.click()
                            time.sleep(0.5)  # Reduced from 2 to 0.5 seconds
                            self.log("âœ… Clicked Submit button (Method 2)", 'acknowledge')
                            submit_clicked = True
                    except Exception as e:
                        self.log(f"âš ï¸ Submit Method 2 failed: {str(e)}", 'acknowledge')
                
                # Method 3: Try by any element with Submit text
                if not submit_clicked:
                    try:
                        submit_element = driver.find_element(By.XPATH, "//*[contains(text(), 'Submit')]")
                        if submit_element.is_displayed():
                            submit_element.click()
                            time.sleep(0.5)  # Reduced from 2 to 0.5 seconds
                            self.log("âœ… Clicked Submit element (Method 3)", 'acknowledge')
                            submit_clicked = True
                    except Exception as e:
                        self.log(f"âš ï¸ Submit Method 3 failed: {str(e)}", 'acknowledge')
                
                if not submit_clicked:
                    self.log("âŒ Could not find or click Submit button", 'acknowledge')
                    return False
                
                # Handle any confirmation dialogs
                try:
                    alert = driver.switch_to.alert
                    alert_text = alert.text
                    self.log(f"ðŸ”” Alert: {alert_text}", 'acknowledge')
                    alert.accept()
                    time.sleep(1)
                except:
                    pass
                    
                # Save to database immediately after acknowledgement
                self.save_acknowledged_request_to_db(request)
                
                return True
            else:
                self.log("âš ï¸ Expected redirect did not occur", 'acknowledge')
                return False
                
        except Exception as e:
            self.log(f"âŒ Error in acknowledge workflow: {str(e)}", 'acknowledge')
            return False
            
    def save_acknowledged_request_to_db(self, request):
        """Save acknowledged request details to database via API"""
        try:
            # Derive API URL from orders_api_url (assuming get_jobs_api.php is in same dir)
            orders_url = self.orders_api_url_var.get()
            if not orders_url:
                self.log("âš ï¸ Cannot save to DB: Orders API URL not set", 'acknowledge')
                return

            base_url = orders_url.rsplit('/', 1)[0]
            api_url = f"{base_url}/get_jobs_api.php"
            
            # Format date: DD-MM-YYYY -> YYYY-MM-DD HH:MM:SS
            try:
                req_date = request.get('request_date', '')
                if req_date:
                    # Append current time
                    current_time = pd.Timestamp.now().strftime("%H:%M:%S") if 'pd' in globals() else time.strftime("%H:%M:%S")
                    dt = datetime.datetime.strptime(req_date, "%d-%m-%Y")
                    formatted_date = f"{dt.strftime('%Y-%m-%d')} {current_time}"
                else:
                    formatted_date = time.strftime("%Y-%m-%d %H:%M:%S")
            except:
                formatted_date = time.strftime("%Y-%m-%d %H:%M:%S")

            payload = {
                'action': 'create_or_update_job_card',
                'request_no': request.get('request_no', ''),
                'firm_id': '1', # Default or fetch connection
                'date_of_request': formatted_date,
                'item': request.get('jeweller_name', ''), # Using Jeweller Name as Item/Desc
                'description': request.get('jeweller_name', ''), 
                'status': 'Created'
            }
            
            # Fetch firm_id if possible (maybe from settings or separate API?)
            # For now defaulting to 1 as per simple_job_creator logic usually
            
            self.log(f"ðŸ’¾ Saving to DB: Request {payload['request_no']} ({payload['date_of_request']})", 'acknowledge')
            
            response = requests.post(api_url, data=payload, timeout=5)
            
            if response.status_code == 200:
                res_json = response.json()
                if res_json.get('status') == 'success':
                    self.log(f"âœ… Saved to DB: {res_json.get('message')}", 'acknowledge')
                else:
                    self.log(f"âš ï¸ DB Save Failed: {res_json.get('message')}", 'acknowledge')
            else:
                self.log(f"âŒ DB API Error: {response.status_code}", 'acknowledge')
                
        except Exception as e:
            self.log(f"âŒ Error saving to DB: {str(e)}", 'acknowledge')

    def _auto_fill_quantity_and_weight(self, driver=None):
        """Auto-fill quantity and weight from the item declaration table"""
        if not driver: driver = self.driver
        try:
            # Find the item declaration table
            tables = driver.find_elements(By.TAG_NAME, "table")
            
            for table in tables:
                try:
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    if len(rows) > 1:
                        # Check if this table has item declaration data
                        header_row = rows[0]
                        header_cells = header_row.find_elements(By.TAG_NAME, "th")
                        header_texts = [cell.text.strip() for cell in header_cells]
                        
                        if "Item Category" in header_texts and "Quantity" in header_texts:
                            # This is the item declaration table
                            self.log("ðŸ“Š Found item declaration table", 'acknowledge')
                            
                            # Process each data row
                            for row in rows[1:]:  # Skip header
                                cells = row.find_elements(By.TAG_NAME, "td")
                                if len(cells) >= 7:
                                    try:
                                        # Get declared quantity and weight
                                        declared_qty = cells[2].text.strip()  # Quantity column
                                        declared_weight = cells[3].text.strip()  # Weight column
                                        
                                        # Fill "Received Quantity by AHC"
                                        received_qty_field = cells[5].find_element(By.TAG_NAME, "input")
                                        if received_qty_field.is_displayed() and received_qty_field.is_enabled():
                                            received_qty_field.clear()
                                            received_qty_field.send_keys(declared_qty)
                                        
                                        # Fill "Observed Item Category Weight"
                                        observed_weight_field = cells[6].find_element(By.TAG_NAME, "input")
                                        if observed_weight_field.is_displayed() and observed_weight_field.is_enabled():
                                            observed_weight_field.clear()
                                            observed_weight_field.send_keys(declared_weight)
                                            
                                        self.log(f"âœ… Auto-filled: Qty={declared_qty}, Weight={declared_weight}", 'acknowledge')
                                        
                                    except Exception as e:
                                        self.log(f"âš ï¸ Error filling row data: {str(e)}", 'acknowledge')
                                        continue
                            
                            break
                            
                except Exception as e:
                    continue
            
            # Also fill the main observed weight and quantity fields
            try:
                # Observed Net Weight AHC
                observed_weight_field = self.driver.find_element(By.NAME, "observedNetWeightAHC")
                if observed_weight_field.is_displayed() and observed_weight_field.is_enabled():
                    # Get total weight from the table
                    total_weight = self._get_total_weight_from_table()
                    if total_weight:
                        observed_weight_field.clear()
                        observed_weight_field.send_keys(total_weight)
                        self.log(f"âœ… Auto-filled Observed Net Weight: {total_weight}", 'acknowledge')
                
                # Observed net Quantity
                observed_qty_field = self.driver.find_element(By.NAME, "observedNetQuantity")
                if observed_qty_field.is_displayed() and observed_qty_field.is_enabled():
                    # Get total quantity from the table
                    total_qty = self._get_total_quantity_from_table()
                    if total_qty:
                        observed_qty_field.clear()
                        observed_qty_field.send_keys(total_qty)
                        self.log(f"âœ… Auto-filled Observed Net Quantity: {total_qty}", 'acknowledge')
                        
            except Exception as e:
                self.log(f"âš ï¸ Error filling main fields: {str(e)}", 'acknowledge')
                
        except Exception as e:
            self.log(f"âŒ Error in auto-fill quantity and weight: {str(e)}", 'acknowledge')
            
    def _get_total_weight_from_table(self):
        """Get total weight from the item declaration table"""
        try:
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            
            for table in tables:
                try:
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    if len(rows) > 1:
                        header_row = rows[0]
                        header_cells = header_row.find_elements(By.TAG_NAME, "th")
                        header_texts = [cell.text.strip() for cell in header_cells]
                        
                        if "Item Category" in header_texts and "Tot. Item Category Weight" in header_texts:
                            total_weight = 0
                            for row in rows[1:]:
                                cells = row.find_elements(By.TAG_NAME, "td")
                                if len(cells) >= 4:
                                    try:
                                        weight_text = cells[3].text.strip()  # Weight column
                                        weight = float(weight_text) if weight_text else 0
                                        total_weight += weight
                                    except:
                                        continue
                            return str(total_weight)
                except:
                    continue
            return None
        except:
            return None
            
    def _get_total_quantity_from_table(self):
        """Get total quantity from the item declaration table"""
        try:
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            
            for table in tables:
                try:
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    if len(rows) > 1:
                        header_row = rows[0]
                        header_cells = header_row.find_elements(By.TAG_NAME, "th")
                        header_texts = [cell.text.strip() for cell in header_cells]
                        
                        if "Item Category" in header_texts and "Quantity" in header_texts:
                            total_qty = 0
                            for row in rows[1:]:
                                cells = row.find_elements(By.TAG_NAME, "td")
                                if len(cells) >= 3:
                                    try:
                                        qty_text = cells[2].text.strip()  # Quantity column
                                        qty = int(qty_text) if qty_text else 0
                                        total_qty += qty
                                    except:
                                        continue
                            return str(total_qty)
                except:
                    continue
            return None
        except:
            return None

    def setup_generate_request_tab(self):
        """Setup Generate Request tab with full automation"""
        generate_frame = ttk.Frame(self.notebook)
        self.notebook.add(generate_frame, text="ðŸ“ Generate Request")
        
        # Main horizontal layout
        main_horizontal = ttk.Frame(generate_frame)
        main_horizontal.pack(fill='both', expand=True, padx=8, pady=8)
        
        # LEFT SECTION - Controls (30% width)
        left_section = ttk.Frame(main_horizontal)
        left_section.pack(side='left', fill='y', padx=(0, 8))
        
        # RIGHT SECTION - Order List (70% width)
        right_section = ttk.Frame(main_horizontal)
        right_section.pack(side='right', fill='both', expand=True)
        
        # === LEFT SECTION CONTENT ===
        self.setup_generate_request_left_section(left_section)
        
        # === RIGHT SECTION CONTENT ===
        self.setup_generate_request_right_section(right_section)
        
    def setup_generate_request_left_section(self, parent):
        """Setup left section with controls and settings"""
        
        # Controls card
        controls_card = ttk.LabelFrame(parent, text="ðŸŽ® Controls", style='Compact.TLabelframe')
        controls_card.pack(fill='x', pady=(0, 8))
        
        controls_frame = ttk.Frame(controls_card)
        controls_frame.pack(fill='x', padx=8, pady=8)
        
        # Fetch Orders button
        self.fetch_orders_btn = ttk.Button(controls_frame, text="ðŸ“‹ Fetch Orders", 
                                         style='Info.TButton', command=self.fetch_order_list)
        self.fetch_orders_btn.pack(fill='x', pady=2)
        
        # Auto Generate All button
        self.auto_generate_all_btn = ttk.Button(controls_frame, text="ðŸ¤– Auto Generate All", 
                                              style='Success.TButton', command=self.auto_generate_all_requests,
                                              state='disabled')
        self.auto_generate_all_btn.pack(fill='x', pady=2)
        
        # Clear List button
        self.clear_orders_btn = ttk.Button(controls_frame, text="ðŸ§¹ Clear List", 
                                         style='Danger.TButton', command=self.clear_order_list)
        self.clear_orders_btn.pack(fill='x', pady=2)
        
        # Settings card
        settings_card = ttk.LabelFrame(parent, text="âš™ï¸ Generate Settings", style='Compact.TLabelframe')
        settings_card.pack(fill='x', pady=(0, 8))
        
        settings_frame = ttk.Frame(settings_card)
        settings_frame.pack(fill='x', padx=8, pady=8)
        
        # Default State
        ttk.Label(settings_frame, text="Default State:", font=('Segoe UI', 8, 'bold')).pack(anchor='w', pady=2)
        self.default_state_var = tk.StringVar(value="Delhi")
        self.default_state_combo = ttk.Combobox(settings_frame, textvariable=self.default_state_var, 
                                              values=['Delhi', 'Maharashtra', 'Karnataka', 'Tamil Nadu', 'Gujarat'], 
                                              width=15, state='readonly', font=('Segoe UI', 10))
        self.default_state_combo.pack(fill='x', pady=2)
        
        # Auto-fill item details checkbox
        self.auto_fill_item_details_var = tk.BooleanVar(value=True)
        auto_fill_cb = ttk.Checkbutton(settings_frame, text="Auto-fill item details from order", 
                                     variable=self.auto_fill_item_details_var)
        auto_fill_cb.pack(anchor='w', pady=2)
        
        # Status card
        status_card = ttk.LabelFrame(parent, text="ðŸ“Š Status", style='Compact.TLabelframe')
        status_card.pack(fill='x', pady=(0, 8))
        
        status_frame = ttk.Frame(status_card)
        status_frame.pack(fill='x', padx=8, pady=8)
        
        # Status labels
        self.total_orders_label = ttk.Label(status_frame, text="Total Orders: 0", font=('Segoe UI', 8))
        self.total_orders_label.pack(anchor='w', pady=1)
        
        self.pending_orders_label = ttk.Label(status_frame, text="Pending: 0", font=('Segoe UI', 8))
        self.pending_orders_label.pack(anchor='w', pady=1)
        
        self.completed_orders_label = ttk.Label(status_frame, text="Completed: 0", font=('Segoe UI', 8))
        self.completed_orders_label.pack(anchor='w', pady=1)
        
        # Progress bar
        self.generate_progress = ttk.Progressbar(status_frame, mode='determinate', length=200)
        self.generate_progress.pack(fill='x', pady=5)
        
        # Log card
        log_card = ttk.LabelFrame(parent, text="ðŸ“ Generate Log", style='Compact.TLabelframe')
        log_card.pack(fill='both', expand=True)
        
        self.generate_log = scrolledtext.ScrolledText(log_card, height=8, font=('Consolas', 7), 
                                                    bg='#f8f9fa', fg='#495057', wrap=tk.WORD)
        self.generate_log.pack(fill='both', expand=True, padx=8, pady=8)
        
    def setup_generate_request_right_section(self, parent):
        """Setup right section with order list table"""
        
        # Order List card
        list_card = ttk.LabelFrame(parent, text="ðŸ“‹ Order List", style='Compact.TLabelframe')
        list_card.pack(fill='both', expand=True)
        
        # Create Treeview for order list
        columns = ('Order No.', 'Jeweller Name', 'License No.', 'Purity', 'Item Weight', 'Status', 'Action')
        
        self.order_tree = ttk.Treeview(list_card, columns=columns, show='headings', height=15)
        
        # Configure columns
        for col in columns:
            self.order_tree.heading(col, text=col)
            if col in ['Order No.', 'License No.', 'Status']:
                self.order_tree.column(col, width=100, minwidth=100)
            elif col == 'Jeweller Name':
                self.order_tree.column(col, width=150, minwidth=150)
            elif col in ['Purity', 'Item Weight']:
                self.order_tree.column(col, width=80, minwidth=80)
            elif col == 'Action':
                self.order_tree.column(col, width=120, minwidth=120)
        
        # Add scrollbars
        tree_scroll_y = ttk.Scrollbar(list_card, orient='vertical', command=self.order_tree.yview)
        tree_scroll_x = ttk.Scrollbar(list_card, orient='horizontal', command=self.order_tree.xview)
        self.order_tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        
        # Pack tree and scrollbars
        self.order_tree.pack(side='left', fill='both', expand=True)
        tree_scroll_y.pack(side='right', fill='y')
        tree_scroll_x.pack(side='bottom', fill='x')
        
        # Bind double-click event for manual generate
        self.order_tree.bind('<Double-1>', self.on_order_double_click)
        
        # Store order data
        self.order_data = []
        
    def fetch_order_list(self):
        """Fetch order list from API"""
        if not self.driver or not self.logged_in:
            messagebox.showwarning("Not Ready", "Please open browser and login first")
            return
            
        self.log("ðŸ” Fetching order list...", 'generate')
        threading.Thread(target=self._fetch_order_list_worker, daemon=True).start()
        
    def _fetch_order_list_worker(self):
        """Worker thread for fetching order list from database/API"""
        loading_dialog = None
        try:
            loading_dialog = LoadingDialog(self.root, "Fetching Orders", "Loading all orders from database...")
            
            # Get API URL from settings
            orders_api_url = getattr(self, 'orders_api_url_var', tk.StringVar(value='http://localhost/manak_auto_fill/get_orders.php')).get().strip()
            
            loading_dialog.update_status("Fetching all orders from database...")
            
            # Make API call to get all orders
            try:
                # No API key required for orders API
                headers = {}
                
                self.log(f"ðŸŒ Fetching orders from: {orders_api_url}", 'generate')
                response = requests.get(orders_api_url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        
                        # Handle different response formats
                        if isinstance(data, dict):
                            if 'orders' in data:
                                orders = data['orders']
                            elif 'data' in data:
                                orders = data['data']
                            else:
                                orders = data
                        elif isinstance(data, list):
                            orders = data
                        else:
                            orders = []
                        
                        # Transform orders to standard format
                        formatted_orders = []
                        for order in orders:
                            try:
                                # Calculate total weight and get purity from items
                                total_weight = 0.0
                                purities = set()
                                
                                # Process items array
                                items = order.get('items', [])
                                for item in items:
                                    weight = float(item.get('weight', 0))
                                    total_weight += weight
                                    purity = item.get('purity', '')
                                    if purity:
                                        purities.add(purity)
                                
                                # Join multiple purities with comma if different
                                purity_str = ', '.join(sorted(purities)) if purities else 'N/A'
                                
                                formatted_order = {
                                    'order_no': str(order.get('order_number', order.get('order_no', order.get('id', '')))),
                                    'jeweller_name': str(order.get('jeweller_name', order.get('jeweller', order.get('customer_name', '')))),
                                    'license_no': str(order.get('licence_no', order.get('license_no', order.get('license_number', '')))),
                                    'state': str(order.get('state', order.get('State', self.default_state_var.get()))),
                                    'purity': purity_str,
                                    'item_weight': f"{total_weight:.2f}",
                                    'status': str(order.get('status', order.get('order_status', 'Pending'))),
                                    'order_date': str(order.get('order_date', '')),
                                    'items': items  # Keep original items for detailed view
                                }
                                formatted_orders.append(formatted_order)
                            except Exception as e:
                                self.log(f"âš ï¸ Error formatting order: {str(e)}", 'generate')
                                continue
                        
                        # Update UI with order data
                        self.root.after(0, self._update_order_list_ui, formatted_orders)
                        
                        loading_dialog.update_status("Done!")
                        loading_dialog.update_message(f"Found {len(formatted_orders)} orders")
                        time.sleep(1)
                        loading_dialog.close()
                        
                        if formatted_orders:
                            self.log(f"âœ… Successfully fetched {len(formatted_orders)} orders", 'generate')
                            messagebox.showinfo("Success", f"âœ… Found {len(formatted_orders)} orders to generate!")
                        else:
                            self.log("âš ï¸ No orders found to generate", 'generate')
                            messagebox.showwarning("No Orders", "No orders found to generate")
                            
                    except ValueError:
                        self.log("âŒ Invalid JSON response from API", 'generate')
                        messagebox.showerror("API Error", "Invalid response format from API")
                else:
                    self.log(f"âŒ API Error: Status {response.status_code}", 'generate')
                    messagebox.showerror("API Error", f"Server returned status code {response.status_code}")
                    
            except requests.exceptions.Timeout:
                self.log("â±ï¸ Request timeout - API took too long to respond", 'generate')
                messagebox.showerror("Timeout", "Request timeout - API took too long to respond")
            except requests.exceptions.ConnectionError:
                self.log("ðŸŒ Connection error - Check internet connection", 'generate')
                messagebox.showerror("Connection Error", "Could not connect to API - Check internet connection")
            except Exception as e:
                self.log(f"âŒ API Error: {str(e)}", 'generate')
                messagebox.showerror("API Error", f"Error fetching orders: {str(e)}")
                
        except Exception as e:
            if loading_dialog:
                loading_dialog.close()
            self.log(f"âŒ Error fetching order list: {str(e)}", 'generate')
            messagebox.showerror("Error", f"Error fetching order list: {str(e)}")
            
    def _update_order_list_ui(self, orders):
        """Update the order list UI with fetched data"""
        # Clear existing data
        for item in self.order_tree.get_children():
            self.order_tree.delete(item)
        
        self.order_data = orders
        
        # Add orders to treeview
        for order in orders:
            self.order_tree.insert('', 'end', values=(
                order['order_no'],
                order['jeweller_name'],
                order['license_no'],
                order['purity'],
                order['item_weight'],
                order['status'],
                "ðŸ”„ Generate"
            ))
        
        # Update status labels
        total = len(orders)
        pending = len([o for o in orders if o['status'] == 'Pending'])
        completed = total - pending
        
        self.total_orders_label.config(text=f"Total Orders: {total}")
        self.pending_orders_label.config(text=f"Pending: {pending}")
        self.completed_orders_label.config(text=f"Completed: {completed}")
        
        # Enable auto generate button if there are pending orders
        if pending > 0:
            self.auto_generate_all_btn.config(state='normal')
        else:
            self.auto_generate_all_btn.config(state='disabled')
            
    def clear_order_list(self):
        """Clear the order list"""
        for item in self.order_tree.get_children():
            self.order_tree.delete(item)
        
        self.order_data = []
        
        # Reset status labels
        self.total_orders_label.config(text="Total Orders: 0")
        self.pending_orders_label.config(text="Pending: 0")
        self.completed_orders_label.config(text="Completed: 0")
        
        # Disable auto generate button
        self.auto_generate_all_btn.config(state='disabled')
        
        self.log("ðŸ§¹ Order list cleared", 'generate')
        
    def on_order_double_click(self, event):
        """Handle double-click on order row for manual generate"""
        selection = self.order_tree.selection()
        if selection:
            item = selection[0]
            values = self.order_tree.item(item, 'values')
            order_no = values[0]  # Order No is in first column
            
            # Find the order data
            order = None
            for ord in self.order_data:
                if ord['order_no'] == order_no:
                    order = ord
                    break
            
            if order:
                # Show order details first
                self._show_order_details(order)
                
    def _show_order_details(self, order):
        """Show detailed order information in a popup"""
        details_window = tk.Toplevel(self.root)
        details_window.title(f"Order Details - {order['order_no']}")
        details_window.geometry("600x500")
        details_window.configure(bg='#f0f2f5')
        details_window.resizable(True, True)
        
        # Center the window
        details_window.update_idletasks()
        x = (details_window.winfo_screenwidth() // 2) - (600 // 2)
        y = (details_window.winfo_screenheight() // 2) - (500 // 2)
        details_window.geometry(f"600x500+{x}+{y}")
        
        # Main frame
        main_frame = ttk.Frame(details_window)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Order header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill='x', pady=(0, 15))
        
        ttk.Label(header_frame, text=f"Order: {order['order_no']}", 
                 font=('Segoe UI', 14, 'bold')).pack(anchor='w')
        ttk.Label(header_frame, text=f"Date: {order.get('order_date', 'N/A')}", 
                 font=('Segoe UI', 10)).pack(anchor='w')
        ttk.Label(header_frame, text=f"Status: {order['status']}", 
                 font=('Segoe UI', 10)).pack(anchor='w')
        
        # Jeweller info
        jeweller_frame = ttk.LabelFrame(main_frame, text="Jeweller Information", padding=10)
        jeweller_frame.pack(fill='x', pady=(0, 15))
        
        ttk.Label(jeweller_frame, text=f"Name: {order['jeweller_name']}", 
                 font=('Segoe UI', 10)).pack(anchor='w')
        ttk.Label(jeweller_frame, text=f"License: {order['license_no']}", 
                 font=('Segoe UI', 10)).pack(anchor='w')
        
        # Items section
        items_frame = ttk.LabelFrame(main_frame, text="Items", padding=10)
        items_frame.pack(fill='both', expand=True, pady=(0, 15))
        
        # Create treeview for items
        columns = ('Item Name', 'Weight', 'Pieces', 'Purity')
        items_tree = ttk.Treeview(items_frame, columns=columns, show='headings', height=8)
        
        for col in columns:
            items_tree.heading(col, text=col)
            items_tree.column(col, width=120)
        
        # Add scrollbar
        items_scrollbar = ttk.Scrollbar(items_frame, orient='vertical', command=items_tree.yview)
        items_tree.configure(yscrollcommand=items_scrollbar.set)
        
        items_tree.pack(side='left', fill='both', expand=True)
        items_scrollbar.pack(side='right', fill='y')
        
        # Populate items
        items = order.get('items', [])
        for item in items:
            items_tree.insert('', 'end', values=(
                item.get('item_name', ''),
                item.get('weight', ''),
                item.get('pieces', ''),
                item.get('purity', '')
            ))
        
        # Summary
        summary_frame = ttk.Frame(main_frame)
        summary_frame.pack(fill='x', pady=(0, 15))
        
        total_weight = sum(float(item.get('weight', 0)) for item in items)
        total_pieces = sum(int(item.get('pieces', 0)) for item in items)
        
        ttk.Label(summary_frame, text=f"Total Weight: {total_weight:.2f} grams", 
                 font=('Segoe UI', 10, 'bold')).pack(side='left')
        ttk.Label(summary_frame, text=f"Total Pieces: {total_pieces}", 
                 font=('Segoe UI', 10, 'bold')).pack(side='right')
        
        # Action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x')
        
        ttk.Button(button_frame, text="Generate Request", 
                  command=lambda: self._generate_order_request(order, details_window)).pack(side='left', padx=(0, 10))
        ttk.Button(button_frame, text="Close", 
                  command=details_window.destroy).pack(side='right')
        
    def _generate_order_request(self, order, window):
        """Generate request for the selected order"""
        window.destroy()  # Close details window
        response = messagebox.askyesno("Generate Request", 
                                     f"Do you want to generate request for order {order['order_no']}?")
        if response:
            threading.Thread(target=self._generate_single_request, 
                           args=(order,), daemon=True).start()
                    
    def auto_generate_all_requests(self):
        """Automatically generate all pending requests"""
        pending_orders = [ord for ord in self.order_data if ord['status'] == 'Pending']
        
        if not pending_orders:
            messagebox.showinfo("No Pending Orders", "No pending orders to generate")
            return
            
        response = messagebox.askyesno("Auto Generate All", 
                                     f"Do you want to automatically generate all {len(pending_orders)} pending orders?")
        if response:
            threading.Thread(target=self._auto_generate_all_worker, 
                           args=(pending_orders,), daemon=True).start()
            
    def _auto_generate_all_worker(self, orders):
        """Worker thread for auto generating all requests"""
        loading_dialog = None
        try:
            loading_dialog = LoadingDialog(self.root, "Auto Generate All", 
                                         f"Processing {len(orders)} orders...")
            
            total = len(orders)
            completed = 0
            failed = 0
            
            # Update progress bar
            self.generate_progress['maximum'] = total
            self.generate_progress['value'] = 0
            
            for i, order in enumerate(orders, 1):
                try:
                    loading_dialog.update_status(f"Processing order {i}/{total}: {order['order_no']}")
                    loading_dialog.update_message(f"Generating request for {order['jeweller_name']}...")
                    
                    success = self._generate_single_request_internal(order)
                    
                    if success:
                        completed += 1
                        self.log(f"âœ… Generated request for order {order['order_no']}", 'generate')
                    else:
                        failed += 1
                        self.log(f"âŒ Failed to generate request for order {order['order_no']}", 'generate')
                        
                except Exception as e:
                    failed += 1
                    self.log(f"âŒ Error generating request for order {order['order_no']}: {str(e)}", 'generate')
                
                # Update progress
                self.generate_progress['value'] = i
                self.root.update()
                
                # Small delay between requests
                time.sleep(0.5)
            
            # Final update
            loading_dialog.update_status("Done!")
            loading_dialog.update_message(f"Completed: {completed}, Failed: {failed}")
            time.sleep(2)
            loading_dialog.close()
            
            # Show results
            messagebox.showinfo("Auto Generate Complete", 
                              f"âœ… Completed: {completed}\nâŒ Failed: {failed}")
            
            # Refresh the order list
            self.fetch_order_list()
            
        except Exception as e:
            if loading_dialog:
                loading_dialog.close()
            self.log(f"âŒ Error in auto generate: {str(e)}", 'generate')
            messagebox.showerror("Error", f"Error in auto generate: {str(e)}")
            
    def _generate_single_request(self, order):
        """Generate a single request (for manual generate)"""
        try:
            success = self._generate_single_request_internal(order)
            
            if success:
                self.log(f"âœ… Successfully generated request for order {order['order_no']}", 'generate')
                messagebox.showinfo("Success", f"âœ… Request generated successfully for order {order['order_no']}!")
            else:
                self.log(f"âŒ Failed to generate request for order {order['order_no']}", 'generate')
                messagebox.showerror("Error", f"âŒ Failed to generate request for order {order['order_no']}")
                
        except Exception as e:
            self.log(f"âŒ Error generating request for order {order['order_no']}: {str(e)}", 'generate')
            messagebox.showerror("Error", f"Error generating request: {str(e)}")
            
    def _select_select2_option(self, container_selector, search_value, log_prefix="Select2"):
        """Helper method to select an option from a Select2 dropdown"""
        try:
            # Find the container
            container = None
            for selector in [container_selector] if isinstance(container_selector, str) else container_selector:
                try:
                    container = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if container.is_displayed():
                        self.log(f"âœ… Found {log_prefix} container with selector: {selector}", 'generate')
                        break
                except:
                    continue
            
            if not container:
                self.log(f"âš ï¸ Could not find {log_prefix} container", 'generate')
                return False
            
            # Scroll to and click the container
            self.driver.execute_script("arguments[0].scrollIntoView(true);", container)
            time.sleep(0.5)
            
            try:
                container.click()
            except:
                self.driver.execute_script("arguments[0].click();", container)
            
            time.sleep(1)
            self.log(f"âœ… Clicked {log_prefix} container", 'generate')
            
            # Wait for and interact with search input
            try:
                # Wait for search input to be present and interactable
                search_input = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".select2-input"))
                )
                
                WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".select2-input"))
                )
                
                # Focus the input
                self.driver.execute_script("arguments[0].focus();", search_input)
                time.sleep(0.5)
                
                if search_input.is_displayed() and search_input.is_enabled():
                    # Clear and type the search value
                    search_input.clear()
                    search_input.send_keys(search_value)
                    time.sleep(1)
                    self.log(f"âœ… Typed {log_prefix} value: {search_value}", 'generate')
                    
                    # Wait for options and select
                    try:
                        WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".select2-results li"))
                        )
                        
                        options = self.driver.find_elements(By.CSS_SELECTOR, ".select2-results li")
                        self.log(f"ðŸ“‹ Found {len(options)} {log_prefix} options", 'generate')
                        
                        # Try to find exact match first
                        selected = False
                        for option in options:
                            if search_value.lower() in option.text.lower():
                                option.click()
                                time.sleep(1)
                                self.log(f"âœ… Selected exact {log_prefix} match: {option.text}", 'generate')
                                selected = True
                                break
                        
                        # If no exact match, try partial matches
                        if not selected:
                            search_parts = search_value.lower().split()
                            for option in options:
                                option_text = option.text.lower()
                                if any(part in option_text for part in search_parts):
                                    option.click()
                                    time.sleep(1)
                                    self.log(f"âœ… Selected partial {log_prefix} match: {option.text}", 'generate')
                                    selected = True
                                    break
                        
                        # If still no match, select first option
                        if not selected and options:
                            options[0].click()
                            time.sleep(1)
                            self.log(f"âœ… Selected first available {log_prefix}: {options[0].text}", 'generate')
                            selected = True
                        
                        return selected
                        
                    except Exception as e:
                        self.log(f"âš ï¸ Could not select {log_prefix} option: {str(e)}", 'generate')
                        return False
                else:
                    self.log(f"âš ï¸ {log_prefix} search input not interactable", 'generate')
                    return False
            except Exception as e:
                self.log(f"âš ï¸ Could not find {log_prefix} search input: {str(e)}", 'generate')
                return False
                
        except Exception as e:
            self.log(f"âš ï¸ Could not select {log_prefix}: {str(e)}", 'generate')
            return False

    def _generate_single_request_internal(self, order):
        """Internal method to generate a single request"""
        try:
            # Step 1: Open generate request page
            self.log(f"ðŸ”— Opening generate request page for order {order['order_no']}", 'generate')
            generate_url = "https://newmanak.uat.dcservices.in/MANAK/AHC_RequestSubmission?cml_no=Q1JPL1JBSEMvUi0xMTAwNTg=&outletid=Mg==&EbranchId=OA==&requestno=&outletname=TUFIQUxBWE1JIEhBTExNQVJLIENFTlRSRQ=="
            self.driver.get(generate_url)
            time.sleep(1)
            
            # Step 2: Wait for page to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "form"))
            )
            
            # Additional wait for Select2 elements to be ready
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".select2-container"))
                )
                self.log("âœ… Select2 containers loaded", 'generate')
            except:
                self.log("âš ï¸ Select2 containers not found, proceeding anyway", 'generate')
            
            # Step 3: Select State using Select2
            self.log("ðŸ›ï¸ Selecting state...", 'generate')
            try:
                # Wait for page to fully load
                time.sleep(3)
                
                # Use state from order data if available, otherwise use default
                state_to_select = order.get('state', self.default_state_var.get())
                self.log(f"ðŸŽ¯ Attempting to select state: {state_to_select}", 'generate')
                
                # Use the helper method for Select2 selection
                state_selectors = [
                    "#s2id_state",
                    "[id*='state']",
                    ".select2-container[id*='state']",
                    ".select2-container:first-child"
                ]
                
                self._select_select2_option(state_selectors, state_to_select, "State")
                    
            except Exception as e:
                self.log(f"âš ï¸ Could not select state: {str(e)}", 'generate')
            
            # Step 4: Select Jeweller by License No using Select2
            self.log(f"ðŸ‘¤ Selecting jeweller by license: {order['license_no']}", 'generate')
            try:
                # Wait for jeweller dropdown to be populated
                time.sleep(2)
                
                # Use the helper method for Select2 selection
                jeweller_selectors = [
                    "#s2id_jeweller",
                    "[id*='jeweller']",
                    ".select2-container[id*='jeweller']",
                    ".select2-container:nth-child(2)"  # Second select2 container
                ]
                
                self._select_select2_option(jeweller_selectors, order['license_no'], "Jeweller")
            except Exception as e:
                self.log(f"âš ï¸ Could not select jeweller: {str(e)}", 'generate')
            
            # Step 5: Click Add Items button
            self.log("âž• Clicking Add Items button...", 'generate')
            try:
                # First, try to close any open Select2 dropdowns that might be blocking
                try:
                    # Check if there's a select2-drop-mask overlay
                    mask = self.driver.find_element(By.CSS_SELECTOR, "#select2-drop-mask")
                    if mask.is_displayed():
                        # Click outside to close dropdown
                        self.driver.find_element(By.TAG_NAME, "body").click()
                        time.sleep(0.5)
                        self.log("âœ… Closed Select2 dropdown overlay", 'generate')
                except:
                    pass
                
                # Wait a bit for any animations to complete
                time.sleep(1)
                
                # Try to find and click the Add Items button
                add_items_btn = self.driver.find_element(By.ID, "Adddata_btn")
                if add_items_btn.is_displayed() and add_items_btn.is_enabled():
                    # Try to scroll to the button first
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", add_items_btn)
                    time.sleep(0.5)
                    
                    # Try clicking with JavaScript if regular click fails
                    try:
                        add_items_btn.click()
                    except:
                        self.driver.execute_script("arguments[0].click();", add_items_btn)
                    
                    time.sleep(1)
                    self.log("âœ… Clicked Add Items button", 'generate')
                else:
                    raise Exception("Add Items button not interactable")
            except Exception as e:
                self.log(f"âŒ Could not click Add Items button: {str(e)}", 'generate')
                return False
            
            # Step 6: Fill item details in dynamic form
            if self.auto_fill_item_details_var.get():
                self.log("ðŸ“ Filling item details...", 'generate')
                
                # Select Item Category using Select2
                try:
                    # Wait for the item category dropdown to be available
                    time.sleep(2)
                    
                    # Use the helper method for Select2 selection
                    category_selectors = [
                        "#s2id_itemCategory",
                        "[id*='itemCategory']",
                        "[id*='category']",
                        ".select2-container[id*='category']"
                    ]
                    
                    self._select_select2_option(category_selectors, "Ring", "Item Category")
                except Exception as e:
                    self.log(f"âš ï¸ Could not select item category: {str(e)}", 'generate')
                
                # Fill Item Weight
                try:
                    # Wait a bit for the form to load
                    time.sleep(1)
                    
                    # Try different possible selectors for weight field
                    weight_selectors = [
                        "input[name='itemWeight']",
                        "input[name='weight']", 
                        "input[id*='weight']",
                        "input[placeholder*='weight']",
                        "input[placeholder*='Weight']",
                        "input[type='text']",
                        "input[type='number']"
                    ]
                    
                    weight_field = None
                    for selector in weight_selectors:
                        try:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            for element in elements:
                                if element.is_displayed() and element.is_enabled():
                                    # Check if this looks like a weight field
                                    placeholder = element.get_attribute('placeholder') or ''
                                    name = element.get_attribute('name') or ''
                                    if 'weight' in placeholder.lower() or 'weight' in name.lower() or not placeholder:
                                        weight_field = element
                                        self.log(f"âœ… Found weight field with selector: {selector}", 'generate')
                                        break
                            if weight_field:
                                break
                        except:
                            continue
                    
                    if weight_field and weight_field.is_displayed():
                        # Scroll to the field
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", weight_field)
                        time.sleep(0.5)
                        
                        weight_field.clear()
                        weight_field.send_keys(order['item_weight'])
                        self.log(f"âœ… Filled item weight: {order['item_weight']}", 'generate')
                    else:
                        self.log("âš ï¸ Weight field not found", 'generate')
                except Exception as e:
                    self.log(f"âš ï¸ Could not fill item weight: {str(e)}", 'generate')
                
                # Select Purity using Select2
                try:
                    # Try to find purity dropdown
                    purity_selectors = [
                        "#s2id_purity",
                        "#s2id_purityType", 
                        "#s2id_karat"
                    ]
                    
                    purity_container = None
                    for selector in purity_selectors:
                        try:
                            purity_container = self.driver.find_element(By.CSS_SELECTOR, selector)
                            if purity_container.is_displayed():
                                break
                        except:
                            continue
                    
                    if purity_container:
                        purity_container.click()
                        time.sleep(0.5)
                        
                        # Extract purity value (e.g., "22K 916" -> "22K")
                        purity_value = order['purity'].split()[0] if ' ' in order['purity'] else order['purity']
                        
                        # Find the search input and type the purity
                        search_input = self.driver.find_element(By.CSS_SELECTOR, f"{purity_selectors[0]} .select2-input")
                        search_input.clear()
                        search_input.send_keys(purity_value)
                        time.sleep(1)
                        
                        # Select the first matching option
                        options = self.driver.find_elements(By.CSS_SELECTOR, f"{purity_selectors[0]} .select2-results li")
                        for option in options:
                            if purity_value in option.text:
                                option.click()
                                time.sleep(0.5)
                                self.log(f"âœ… Selected purity: {order['purity']}", 'generate')
                                break
                    else:
                        self.log("âš ï¸ Purity dropdown not found", 'generate')
                except Exception as e:
                    self.log(f"âš ï¸ Could not select purity: {str(e)}", 'generate')
            
            # Step 7: Click Save button
            self.log("ðŸ’¾ Clicking Save button...", 'generate')
            try:
                # Wait a bit for any form processing
                time.sleep(2)
                
                # Try different possible selectors for Save button
                save_selectors = [
                    "//input[@type='button' and @value='Save']",
                    "//input[@type='submit' and @value='Save']",
                    "//button[contains(text(), 'Save')]",
                    "//input[@value='Save']",
                    "//button[@value='Save']",
                    "//input[contains(@class, 'save')]",
                    "//button[contains(@class, 'save')]",
                    "//input[@id='save_btn']",
                    "//button[@id='save_btn']",
                    "//input[contains(@onclick, 'save')]",
                    "//button[contains(@onclick, 'save')]"
                ]
                
                save_btn = None
                for selector in save_selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        for element in elements:
                            if element.is_displayed() and element.is_enabled():
                                save_btn = element
                                self.log(f"âœ… Found Save button with selector: {selector}", 'generate')
                                break
                        if save_btn:
                            break
                    except:
                        continue
                
                if save_btn and save_btn.is_displayed() and save_btn.is_enabled():
                    # Scroll to the button first
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", save_btn)
                    time.sleep(0.5)
                    
                    # Try clicking with JavaScript if regular click fails
                    try:
                        save_btn.click()
                    except:
                        self.driver.execute_script("arguments[0].click();", save_btn)
                    
                    time.sleep(1)
                    self.log("âœ… Clicked Save button", 'generate')
                else:
                    # If no Save button found, check if we need to submit the form differently
                    self.log("âš ï¸ Save button not found, checking for alternative submission methods", 'generate')
                    
                    # Try to find any submit button or form submission
                    submit_selectors = [
                        "//input[@type='submit']",
                        "//button[@type='submit']",
                        "//input[contains(@value, 'Submit')]",
                        "//button[contains(text(), 'Submit')]"
                    ]
                    
                    submit_btn = None
                    for selector in submit_selectors:
                        try:
                            elements = self.driver.find_elements(By.XPATH, selector)
                            for element in elements:
                                if element.is_displayed() and element.is_enabled():
                                    submit_btn = element
                                    self.log(f"âœ… Found Submit button with selector: {selector}", 'generate')
                                    break
                            if submit_btn:
                                break
                        except:
                            continue
                    
                    if submit_btn:
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", submit_btn)
                        time.sleep(0.5)
                        submit_btn.click()
                        time.sleep(1)
                        self.log("âœ… Clicked Submit button instead of Save", 'generate')
                    else:
                        raise Exception("Save button not found or not interactable")
            except Exception as e:
                self.log(f"âŒ Could not click Save button: {str(e)}", 'generate')
                return False
            
            # Step 8: Check if redirected to add more items page or if we need to wait for Save button
            current_url = self.driver.current_url
            self.log(f"ðŸ“ Current URL: {current_url}", 'generate')
            
            # Wait a bit more for any page transitions
            time.sleep(3)
            
            # Check if we're on a page with item details or if we need to look for different buttons
            if 'item_category=' in current_url or 'request' in current_url.lower():
                self.log("ðŸ”„ On request submission page", 'generate')
                
                # Step 9: Look for Submit to AHC or similar buttons
                try:
                    submit_selectors = [
                        "//input[@type='button' and contains(@value, 'Submit')]",
                        "//button[contains(text(), 'Submit')]",
                        "//input[contains(@value, 'Submit to AHC')]",
                        "//button[contains(text(), 'Submit to AHC')]",
                        "//input[@type='submit']",
                        "//button[@type='submit']"
                    ]
                    
                    submit_btn = None
                    for selector in submit_selectors:
                        try:
                            elements = self.driver.find_elements(By.XPATH, selector)
                            for element in elements:
                                if element.is_displayed() and element.is_enabled():
                                    submit_btn = element
                                    self.log(f"âœ… Found Submit button with selector: {selector}", 'generate')
                                    break
                            if submit_btn:
                                break
                        except:
                            continue
                    
                    if submit_btn:
                        # Scroll to the button first
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", submit_btn)
                        time.sleep(0.5)
                        
                        # Try clicking with JavaScript if regular click fails
                        try:
                            submit_btn.click()
                        except:
                            self.driver.execute_script("arguments[0].click();", submit_btn)
                        
                        time.sleep(1)
                        self.log("âœ… Clicked Submit to AHC", 'generate')
                        
                        # Handle any confirmation dialogs
                        try:
                            alert = self.driver.switch_to.alert
                            alert_text = alert.text
                            self.log(f"ðŸ”” Alert: {alert_text}", 'generate')
                            alert.accept()
                            time.sleep(0.5)
                        except:
                            pass
                            
                        return True
                    else:
                        self.log("âš ï¸ No Submit button found, checking if request was already submitted", 'generate')
                        # Check if there's any success message or if we're already on a success page
                        try:
                            success_indicators = [
                                "//*[contains(text(), 'success')]",
                                "//*[contains(text(), 'submitted')]",
                                "//*[contains(text(), 'request')]",
                                "//*[contains(@class, 'success')]"
                            ]
                            
                            for indicator in success_indicators:
                                try:
                                    element = self.driver.find_element(By.XPATH, indicator)
                                    if element.is_displayed():
                                        self.log(f"âœ… Found success indicator: {element.text}", 'generate')
                                        return True
                                except:
                                    continue
                        except:
                            pass
                        
                        raise Exception("Submit button not found and no success indicators")
                except Exception as e:
                    self.log(f"âŒ Could not click Submit to AHC: {str(e)}", 'generate')
                    return False
            else:
                self.log("âš ï¸ Not on expected request submission page", 'generate')
                # Try to find any other submission buttons
                try:
                    all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
                    input_buttons = self.driver.find_elements(By.TAG_NAME, "input")
                    
                    for button in all_buttons + input_buttons:
                        if button.is_displayed() and button.is_enabled():
                            button_text = button.text or button.get_attribute('value') or ''
                            if any(keyword in button_text.lower() for keyword in ['submit', 'save', 'confirm', 'proceed']):
                                self.log(f"ðŸ” Found potential submission button: {button_text}", 'generate')
                                button.click()
                                time.sleep(1)
                                return True
                except:
                    pass
                
                return False
                
        except Exception as e:
            self.log(f"âŒ Error in generate request workflow: {str(e)}", 'generate')
            return False

if __name__ == "__main__":
    app = ManakDesktopApp()
    app.run()
