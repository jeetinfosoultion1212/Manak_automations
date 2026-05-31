#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MANAK Portal Desktop Application
Enhanced Compact UI with Responsive Design - No Scrolling Required
"""

# Fix MySQL localization issue and encoding BEFORE any other imports
import os
import sys

os.environ['LANG'] = 'C'
os.environ['LC_ALL'] = 'C'
os.environ['LC_MESSAGES'] = 'C'

# CRITICAL: Override print IMMEDIATELY to prevent Unicode errors in executable
import builtins
_original_print = builtins.print

def safe_print(*args, **kwargs):
    """Print function that handles Unicode encoding errors - essential for executable"""
    try:
        # Try normal print first
        _original_print(*args, **kwargs)
    except (UnicodeEncodeError, UnicodeDecodeError, LookupError):
        # If it fails, strip Unicode and retry
        try:
            safe_args = []
            for arg in args:
                if isinstance(arg, str):
                    # Remove ALL non-ASCII characters
                    safe_text = arg.encode('ascii', 'ignore').decode('ascii')
                    safe_args.append(safe_text)
                else:
                    safe_args.append(str(arg))
            _original_print(*safe_args, **kwargs)
        except:
            # If it still fails, just skip it completely
            pass

# Replace print globally BEFORE any other code runs
builtins.print = safe_print
print = safe_print

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
import threading
import time
from datetime import datetime
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.select import Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, UnexpectedAlertPresentException, NoAlertPresentException
import random
import json
import base64
import os
import sys
import sqlite3
import config
from config import DB_CONFIG
import portal_config

# Import device licensing
try:
    from license.device_license import DeviceLicenseManager
except ImportError:
    print("Warning: Device licensing module not found. Running without license verification.")
    DeviceLicenseManager = None

# Import extracted modules
try:
    from processors.request_generator import RequestGenerator
except ImportError:
    print("Warning: Request generator module not found.")
    RequestGenerator = None

try:
    from processors.multiple_jobs_processor import MultipleJobsProcessor
except ImportError:
    print("Warning: Multiple jobs processor module not found.")
    MultipleJobsProcessor = None

try:
    from processors.weight_capture_processor import WeightCaptureProcessor
except ImportError:
    print("Warning: Weight capture processor module not found.")
    WeightCaptureProcessor = None

try:
    from processors.delivery_voucher_processor import DeliveryVoucherProcessor
except ImportError:
    print("Warning: Delivery voucher processor module not found.")
    DeliveryVoucherProcessor = None

try:
    from processors.job_cards_processor import JobCardsProcessor
except ImportError:
    print("Warning: Job cards processor module not found.")
    JobCardsProcessor = None

try:
    from processors.delivery_voucher_scanner import DeliveryVoucherScanner
except ImportError:
    print("Warning: Delivery voucher scanner module not found.")
    DeliveryVoucherScanner = None

try:
    from processors.completed_jobs_scanner import CompletedJobsScanner
except ImportError:
    print("Warning: Completed jobs scanner module not found.")
    CompletedJobsScanner = None

try:
    from processors.bill_import_processor import BillImportProcessor
except ImportError:
    print("Warning: Bill import processor module not found.")
    BillImportProcessor = None

try:
    from processors.jeweller_request_generator import JewellerRequestGenerator
except ImportError:
    print("Warning: Jeweller request generator module not found.")
    JewellerRequestGenerator = None

# Import font loader
try:
    from utils.font_loader import load_fonts_from_directory
except ImportError:
    def load_fonts_from_directory(directory: str = "fonts") -> int: 
        return 0

try:
    from utils.tag_manager import TagManager
except ImportError:
    print("Warning: TagManager module not found.")
    TagManager = None


# Removed: Portal Browser tab (not needed - using simple embedded browser in bulk jobs instead)


__version__ = "10.0"

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
        self.spinner_label = tk.Label(main_frame, text="⏳", font=('Segoe UI', 24), bg='#f0f2f5')
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
        # Initialize device licensing first
        self.license_manager = None
        if DeviceLicenseManager:
            self.license_manager = DeviceLicenseManager()
        
        self.root = tk.Tk()
        self.root.title(f"MANAK Automations v{__version__} | Tech Hub")
        self.root.geometry("1400x900")  # Wider window for better layout
        self.root.configure(bg='#f0f2f5')
        self.root.minsize(1200, 800)  # Minimum size
        self.style = ttk.Style()
        self.setup_styles()
        
        # Setup global exception handler to prevent crashes
        self.setup_global_exception_handler()
        
        # Load custom fonts
        self.load_custom_fonts()
        
        # Setup executable-specific configurations
        self.setup_executable_config()
        
        # Test critical imports before proceeding
        self.test_critical_imports()
        
        # Automation state
        self.driver = None
        self.reception_driver = None  # Second browser instance for reception tasks
        self.logged_in = False
        self.page_loaded = False
        self.license_verified = False  # Track license verification status
        self.tag_manager = TagManager() if TagManager else None
        
        # API configuration variables
        self.api_url_var = tk.StringVar()
        self.orders_api_url_var = tk.StringVar()
        self.api_key_var = tk.StringVar()
        
        # Processor initialization
        self.bulk_jobs_processor = None
        self.selected_credential_type = None
        
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
        
        # Initialize processors (will be updated when driver is available)
        self.multiple_jobs_processor = None
        self.weight_capture_processor = None
        self.delivery_voucher_processor = None
        self.job_cards_processor = None
        self.delivery_voucher_scanner = None
        self.huid_data_processor = None
        
        # Initialize button references (will be set during UI setup)
        self.auto_fill_btn = None
        self.select_lot_btn = None
        self.auto_workflow_btn = None
        
        # Initialize settings dictionary
        self.settings = {}
        
        self.setup_ui()
        # Load saved settings
        self.load_settings()
        # Clear fields on app start
        self.clear_fields_on_start()
        
        # Update fetch button text based on initial job number
        # self.root.after(100, self.on_job_number_change)
        
        # Start periodic license status updates
        self.root.after(1000, self.update_license_status_display)
        
        # Enforce license verification at startup
        self.enforce_startup_license()  # Simplified license verification enabled
        
        # Set up proper cleanup on exit
        self.root.protocol("WM_DELETE_WINDOW", self._cleanup_and_exit)
        
        # The Saved Jobs tab is already added in setup_ui() method
        # No need to add it again here
        

    
        
    def _cleanup_and_exit(self):
        """Clean up resources and exit gracefully"""
        try:
            # Close browser if open
            if hasattr(self, 'driver') and self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
            
            # Close database connections
            if hasattr(self, 'conn') and self.conn:
                try:
                    self.conn.close()
                except:
                    pass
                self.conn = None
            
            # Destroy license dialog if open
            if hasattr(self, '_license_dialog') and self._license_dialog:
                try:
                    self._license_dialog.destroy()
                except:
                    pass
                self._license_dialog = None
            
            # Destroy root window
            if hasattr(self, 'root') and self.root:
                try:
                    self.root.quit()
                    self.root.destroy()
                except:
                    pass
            
        except Exception as e:
            print(f"Error during cleanup: {e}")
        finally:
            import sys
            sys.exit(0)
        
    def refresh_jewellers_list(self):
        """Refresh jewellers list after license verification"""
        if hasattr(self, 'jeweller_request_generator') and self.jeweller_request_generator:
            try:
                # Add a small delay to ensure UI is ready
                self.root.after(500, self.jeweller_request_generator.load_jewellers)
            except Exception as e:
                self.log(f"⚠️ Error refreshing jewellers list: {e}", 'system')

    def enforce_startup_license(self):
        """Enforce license verification at application startup - Simplified version"""
        # Check for development mode (bypass license)
        if os.environ.get('MANAK_DEV_MODE') == '1':
            print("🔧 Development mode detected - bypassing license verification")
            self.license_verified = True
            return
            
        if not self.license_manager:
            # If license manager is not available, show warning but allow access
            messagebox.showwarning("License Manager", "Device licensing is not available. Running in unrestricted mode.")
            self.license_verified = True
            return
            
        # Check cache first - if we have a valid cached license, just check status
        if self.license_manager.check_cache():
            print("✅ Valid cached license found - checking status only")
            if self.license_manager.check_license_status_only():
                self.license_verified = True
                self.log("✅ License status verified from cache", 'status')
                
                # Start periodic verification (status check only)
                self.license_manager.start_periodic_verification(self)
                self.log("🔄 Periodic license status monitoring started", 'status')
                self.refresh_jewellers_list()  # Refresh jewellers list
                return
            else:
                print("⚠️ Cached license is no longer active")
                self.license_manager.clear_cache()
        
        # If no valid cache, check license automatically using MAC address
        if self.license_manager.check_license():
            self.license_verified = True
            self.log("✅ License verified at startup", 'status')
            
            # Start periodic verification
            self.license_manager.start_periodic_verification(self)
            self.log("🔄 Periodic license verification started", 'status')
            self.refresh_jewellers_list()  # Refresh jewellers list
        else:
            # License verification failed, force user to settings page
            self.force_license_setup()
        
        # If we reach here and license is still not verified, the dialog should have handled exit
        if not self.license_verified:
            # This should not happen, but just in case
            self.root.quit()
            self.root.destroy()
            sys.exit(0)
    
    def force_license_setup(self):
        """Force user to license setup page"""
        # Show alert that license verification is required
        result = messagebox.askokcancel(
            "License Required", 
            "Device license verification is required.\n\n"
            "Click OK to proceed to license verification.",
            icon="warning"
        )
        
        if result:
            # Open settings tab and show license dialog immediately
            if hasattr(self, 'notebook'):
                self.notebook.select(3)  # Settings tab
                self.license_verified = False
                # Update UI to reflect the tab change
                self.root.update()
                # Show license dialog immediately
                self.show_license_setup_dialog()
            else:
                # If notebook not ready, show license dialog directly
                self.show_license_setup_dialog()
        else:
            # If user clicks Cancel, exit the application
            self.root.quit()
            self.root.destroy()
            import sys
            sys.exit(0)

    def show_license_setup_dialog(self):
        """Show license setup dialog and enforce verification"""
        try:
            # Define the exit function first
            def exit_app():
                """Exit the application"""
                try:
                    response = messagebox.askyesno("Exit Application", 
                                               "Are you sure you want to exit the application?")
                    if response:
                        if hasattr(self, '_license_dialog') and self._license_dialog:
                            try:
                                self._license_dialog.destroy()
                                self._license_dialog = None
                            except:
                                pass
                        try:
                            self.root.quit()
                            self.root.destroy()
                        except:
                            pass
                        import sys
                        sys.exit(0)
                except Exception as e:
                    print(f"Error in exit_app: {str(e)}")
                    sys.exit(1)

            # Create a more user-friendly dialog
            dialog = tk.Toplevel(self.root)
            dialog.title("MANAK Automation - License Setup")
            dialog.geometry("500x400")  # Reduced size
            dialog.configure(bg='#f0f2f5')
            dialog.resizable(False, False)
            dialog.grab_set()
            dialog.focus_set()
            dialog.attributes('-topmost', True)
            
            # Center the dialog
            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
            y = (dialog.winfo_screenheight() // 2) - (400 // 2)
            dialog.geometry(f"500x400+{x}+{y}")
            
            # Store dialog reference
            self._license_dialog = dialog
        except Exception as e:
            print(f"Error creating license dialog: {str(e)}")
            return
        # Content
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill='both', expand=True, padx=15, pady=15)  # Reduced padding
        
        # Header with icon
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill='x', pady=(0, 10))  # Reduced padding
        
        header_label = tk.Label(header_frame, text="🔐 License Verification", 
                              font=('Segoe UI', 14, 'bold'), bg='#f0f2f5', fg='#2c3e50')  # Smaller font
        header_label.pack()
        
        subtitle_label = tk.Label(header_frame, text="Device License Required", 
                                font=('Segoe UI', 10), bg='#f0f2f5', fg='#7f8c8d')  # Smaller font
        subtitle_label.pack(pady=(2, 0))  # Reduced padding
        
        # Device Information
        device_frame = ttk.LabelFrame(main_frame, text="📱 Device Information", style='Compact.TLabelframe')
        device_frame.pack(fill='x', pady=(0, 10))  # Reduced padding
        
        # Grid layout for device info
        device_grid = ttk.Frame(device_frame)
        device_grid.pack(fill='x', padx=10, pady=5)  # Reduced padding
        
        def copy_to_clipboard(text, field_name):
            """Helper function to copy text to clipboard"""
            dialog.clipboard_clear()
            dialog.clipboard_append(text)
            status_label.config(text=f"✅ {field_name} copied to clipboard", fg='#27ae60')
            dialog.update()
            # Reset status after 2 seconds
            dialog.after(2000, lambda: status_label.config(text=""))

        # MAC Address (read-only) with copy button
        ttk.Label(device_grid, text="MAC Address:", font=('Segoe UI', 9, 'bold')).grid(row=0, column=0, sticky='w', pady=2)
        mac_address = (self.license_manager.mac_address if self.license_manager else None) or "Unknown"
        mac_label = tk.Label(device_grid, text=mac_address, font=('Segoe UI', 9),
                           bg='#f8f9fa', fg='#495057', relief='sunken', padx=5, pady=2)
        mac_label.grid(row=0, column=1, sticky='ew', padx=(5,5), pady=2)
        ttk.Button(device_grid, text="📋", width=3, 
                  command=lambda: copy_to_clipboard(mac_address, "MAC Address")).grid(row=0, column=2, pady=2)
        
        # Device ID (read-only) with copy button
        ttk.Label(device_grid, text="Device ID:", font=('Segoe UI', 9, 'bold')).grid(row=1, column=0, sticky='w', pady=2)
        device_id = (self.license_manager.device_id if self.license_manager else None) or "Unknown"
        device_id_label = tk.Label(device_grid, text=device_id, font=('Segoe UI', 9),
                                 bg='#f8f9fa', fg='#495057', relief='sunken', padx=5, pady=2)
        device_id_label.grid(row=1, column=1, sticky='ew', padx=(5,5), pady=2)
        ttk.Button(device_grid, text="📋", width=3,
                  command=lambda: copy_to_clipboard(device_id, "Device ID")).grid(row=1, column=2, pady=2)
        
        device_grid.columnconfigure(1, weight=1)  # Make second column expandable
        
        # Portal Credentials
        portal_frame = ttk.LabelFrame(main_frame, text="🌐 Portal Credentials", style='Compact.TLabelframe')
        portal_frame.pack(fill='x', pady=(0, 10))  # Reduced padding
        
        # Grid layout for credentials
        cred_grid = ttk.Frame(portal_frame)
        cred_grid.pack(fill='x', padx=10, pady=5)  # Reduced padding
        
        # Username
        ttk.Label(cred_grid, text="Username:", font=('Segoe UI', 9, 'bold')).grid(row=0, column=0, sticky='w', pady=2)
        username_var = tk.StringVar()
        username_entry = ttk.Entry(cred_grid, textvariable=username_var, width=30, font=('Segoe UI', 9))
        username_entry.grid(row=0, column=1, sticky='ew', padx=(5,0), pady=2)
        
        # Password
        ttk.Label(cred_grid, text="Password:", font=('Segoe UI', 9, 'bold')).grid(row=1, column=0, sticky='w', pady=2)
        password_var = tk.StringVar()
        password_entry = ttk.Entry(cred_grid, textvariable=password_var, width=30, font=('Segoe UI', 9), show='*')
        password_entry.grid(row=1, column=1, sticky='ew', padx=(5,0), pady=2)
        
        cred_grid.columnconfigure(1, weight=1)  # Make second column expandable
        
        # Status label
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill='x', pady=(0, 10))
        
        status_label = tk.Label(status_frame, text="", font=('Segoe UI', 9), bg='#f0f2f5')
        status_label.pack()
        
        def verify_license():
            try:
                username = username_var.get().strip()
                password = password_var.get().strip()
                
                if not username or not password:
                    status_label.config(text="❌ Please enter both Username and Password", fg='#e74c3c')
                    return
                
                # Show verifying status
                status_label.config(text="🔄 Verifying license...", fg='#f39c12')
                dialog.update()
                
                # Verify with portal credentials
                # Save username in entry field
                self.portal_username_var.set(username)
                
                if self.license_manager and self.license_manager.verify_device_license(username, password):
                    self.license_verified = True
                    
                    # Get license details for display
                    license_status = self.license_manager.get_license_status()
                    expiry_info = ""
                    
                    if license_status.get('expires_at'):
                        try:
                            expiry_timestamp = license_status['expires_at']
                            current_time = time.time()
                            
                            if current_time > expiry_timestamp:
                                # License expired
                                status_label.config(text="❌ License EXPIRED!", fg='#e74c3c')
                                expiry_info = f"Expired on: {datetime.fromtimestamp(expiry_timestamp).strftime('%Y-%m-%d %H:%M') }"
                            else:
                                # License valid
                                expiry_date = datetime.fromtimestamp(expiry_timestamp).strftime('%Y-%m-%d %H:%M')
                                days_left = int((expiry_timestamp - current_time) / 86400)
                                
                                if days_left <= 7:
                                    status_label.config(text="⚠️ License EXPIRING SOON!", fg='#f39c12')
                                    expiry_info = f"Expires in {days_left} days: {expiry_date}"
                                else:
                                    status_label.config(text="✅ License verified successfully!", fg='#27ae60')
                                    expiry_info = f"Valid for {days_left} days: {expiry_date}"
                        except Exception:
                            status_label.config(text="✅ License verified successfully!", fg='#27ae60')
                            expiry_info = "License valid (expiry info unavailable)"
                    else:
                        status_label.config(text="✅ License verified successfully!", fg='#27ae60')
                        expiry_info = "License valid (no expiry date)"
                    
                    # Show expiry information
                    if expiry_info:
                        messagebox.showinfo("License Status", f"License verified successfully!\n\n{expiry_info}")
                    
                    # Save settings after successful verification
                    self.save_settings()
                    self.refresh_jewellers_list()  # Refresh jewellers list
                    
                    # Close dialog after short delay
                    dialog.after(2000, dialog.destroy)
                else:
                    status_label.config(text="❌ License verification failed. Please check your credentials.", fg='#e74c3c')
            except Exception as e:
                error_msg = f"Error verifying license: {str(e)}"
                print(error_msg)  # Log to console
                try:
                    if status_label and status_label.winfo_exists():
                        status_label.config(text=f"❌ {error_msg}", fg='#e74c3c')
                except (tk.TclError, AttributeError):
                    pass
        
            # Define exit_app function
            def _create_exit_app():
                def exit_app():
                    """Exit the application"""
                    try:
                        response = messagebox.askyesno("Exit Application", 
                                                   "Are you sure you want to exit the application?")
                        if response:
                            if hasattr(self, '_license_dialog') and self._license_dialog:
                                try:
                                    self._license_dialog.destroy()
                                    self._license_dialog = None
                                except:
                                    pass
                            try:
                                self.root.quit()
                                self.root.destroy()
                            except:
                                pass
                            import sys
                            sys.exit(0)
                    except Exception as e:
                        print(f"Error in exit_app: {str(e)}")
                        sys.exit(1)
                return exit_app

            # Create exit_app function
            exit_app = _create_exit_app()

            # Buttons frame with grid layout
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=(5, 0))
        
        # Create button grid
        verify_btn = ttk.Button(button_frame, text="✓ Verify", 
                               command=verify_license, style='Success.TButton', width=15)
        verify_btn.pack(side='left', padx=5)
        
        exit_btn = ttk.Button(button_frame, text="✕ Exit", 
                             command=exit_app, style='Danger.TButton', width=15)
        exit_btn.pack(side='right', padx=5)
        
        # Help text
        help_text = tk.Label(main_frame, text="💡 Enter to verify, Esc to exit", 
                           font=('Segoe UI', 8), bg='#f0f2f5', fg='#95a5a6')
        help_text.pack(pady=(5, 0))
        
        # Focus on first entry
        username_entry.focus()
        
        # Bind keyboard shortcuts
        dialog.bind('<Return>', lambda e: verify_license())
        dialog.bind('<Escape>', lambda e: exit_app())
        
        # Show dialog and wait
        dialog.wait_window()
        
        # If license is still not verified after dialog closes
        if not self.license_verified:
            response = messagebox.askyesno(
                "License Required", 
                "License verification is required to use this application.\n\n"
                "Do you want to try verifying again?",
                icon="warning"
            )
            if response:
                # Show the dialog again
                self.root.after(100, self.show_license_setup_dialog)
            else:
                # Exit the application
                self.root.quit()
                self.root.destroy()
                sys.exit(0)

    def check_license_before_action(self, action_name="this action"):
        """Check license before performing any critical action - persistent version"""
        if not self.license_manager:
            return True  # Allow if no license manager
            
        # First check if we have a valid cached license
        if self.license_manager.check_cache():
            # We have a valid cached license, no need to ask for verification again
            self.license_verified = True
            return True
            
        # If no valid cache, check if license is still active on server
        try:
            if self.license_manager.check_license_status_only():
                # License is still active on server, update cache and proceed
                self.license_verified = True
                return True
            else:
                # License is inactive on server
                self.log("❌ License is inactive on server", 'license')
                self.license_verified = False
        except Exception as e:
            self.log(f"❌ License status check error: {str(e)}", 'license')
            # For network errors, if we have cached credentials, allow the action
            if self.license_manager.portal_username and self.license_manager.portal_password:
                self.log("⚠️ Using cached credentials due to network error", 'license')
                self.license_verified = True
                return True
        
        # Only ask for verification if we don't have valid cache AND server check failed
        if not self.license_verified:
            response = messagebox.askyesno(
                "License Required", 
                f"Device license verification required for {action_name}.\n\n"
                "You will be redirected to the Settings page to verify your license."
            )
            if response:
                # Open settings tab for license verification
                if hasattr(self, 'notebook'):
                    self.notebook.select(3)  # Settings tab
                else:
                    self.show_license_setup_dialog()
            return False
            
        return True
        
    def setup_styles(self):
        """Setup enhanced custom styles for the application"""
        self.style.theme_use('clam')
        
        # Color scheme
        # Modern Color scheme
        self.colors = {
            'primary': '#0ea5e9',       # Modern Sky Blue
            'primary_dark': '#0284c7',  # Darker Blue for pressed
            'success': '#10b981',       # Emerald Green
            'danger': '#ef4444',        # Rose Red
            'warning': '#f59e0b',       # Amber
            'info': '#3b82f6',          # Royal Blue
            'light': '#f8fafc',         # Slate 50
            'dark': '#1e293b',          # Slate 800
            'secondary': '#64748b',     # Slate 500
            'accent': '#8b5cf6',        # Violet
            'bg_main': '#f1f5f9',       # Slate 100
            'bg_card': '#ffffff',       # White
            'bg_input': '#ffffff',      # White
            'border': '#e2e8f0',        # Slate 200
            'text_primary': '#0f172a',  # Slate 900
            'text_secondary': '#64748b' # Slate 500
        }
        
        default_font = ('Segoe UI', 10)
        small_font = ('Segoe UI', 9)
        header_font = ('Segoe UI', 11, 'bold')
        
        # Configure main styles
        self.style.configure('Card.TFrame', background=self.colors['bg_card'], relief='flat', borderwidth=0)
        self.style.configure('Header.TLabel', font=header_font, background=self.colors['bg_card'], foreground=self.colors['text_primary'])
        
        # Compact entry styles
        large_font = ('Segoe UI', 11)
        self.style.configure('Compact.TEntry', 
                           font=large_font, 
                           fieldbackground=self.colors['bg_input'], 
                           borderwidth=1, 
                           relief='solid',
                           selectbackground=self.colors['primary'],
                           selectforeground='white')
        
        self.style.configure('Success.TEntry', 
                           font=large_font, 
                           fieldbackground='#ecfdf5', 
                           borderwidth=1, 
                           relief='solid')
                           
        self.style.configure('Warning.TEntry', 
                           font=large_font, 
                           fieldbackground='#fffbeb', 
                           borderwidth=1, 
                           relief='solid')
        
        # Button styles - Modern
        self.style.configure('Compact.TButton', 
                           background=self.colors['primary'], 
                           foreground='white', 
                           font=('Segoe UI', 9, 'bold'), 
                           borderwidth=0, 
                           padding=(10, 6))
        self.style.map('Compact.TButton',
            background=[('active', self.colors['primary_dark']), ('pressed', self.colors['primary_dark'])],
            foreground=[('active', 'white'), ('pressed', 'white')])
        
        self.style.configure('Success.TButton', 
                           background=self.colors['success'], 
                           foreground='white', 
                           font=('Segoe UI', 9, 'bold'), 
                           borderwidth=0, 
                           padding=(10, 6))
        self.style.map('Success.TButton',
            background=[('active', '#059669'), ('pressed', '#059669')],
            foreground=[('active', 'white'), ('pressed', 'white')])
            
        self.style.configure('Danger.TButton', 
                           background=self.colors['danger'], 
                           foreground='white', 
                           font=('Segoe UI', 9, 'bold'), 
                           borderwidth=0, 
                           padding=(10, 6))
        self.style.map('Danger.TButton',
            background=[('active', '#dc2626'), ('pressed', '#dc2626')],
            foreground=[('active', 'white'), ('pressed', 'white')])

        self.style.configure('Info.TButton', 
                           background=self.colors['info'], 
                           foreground='white', 
                           font=('Segoe UI', 9, 'bold'), 
                           borderwidth=0, 
                           padding=(10, 6))
        self.style.map('Info.TButton',
            background=[('active', '#2563eb'), ('pressed', '#2563eb')],
            foreground=[('active', 'white'), ('pressed', 'white')])
        
        self.style.configure('Warning.TButton', 
                           background=self.colors['warning'], 
                           foreground='#1e293b', 
                           font=('Segoe UI', 9, 'bold'), 
                           borderwidth=0, 
                           padding=(10, 6))
        self.style.map('Warning.TButton',
            background=[('active', '#d97706'), ('pressed', '#d97706')],
            foreground=[('active', 'white'), ('pressed', 'white')])
        
        # Notebook styles
        self.style.configure('TNotebook', background=self.colors['bg_main'], borderwidth=0)
        self.style.configure('TNotebook.Tab', 
                           font=('Segoe UI', 8, 'bold'), 
                           padding=[8, 5], 
                           background='#e2e8f0', 
                           foreground='#64748b',
                           borderwidth=0)
        self.style.map('TNotebook.Tab', 
                      background=[('selected', 'white')], 
                      foreground=[('selected', self.colors['primary'])])
        
        # LabelFrame styles - compact
        self.style.configure('Compact.TLabelframe', 
                           background=self.colors['bg_card'], 
                           relief='flat', 
                           borderwidth=1,
                           bordercolor=self.colors['border'])
        self.style.configure('Compact.TLabelframe.Label', 
                           font=('Segoe UI', 10, 'bold'), 
                           foreground=self.colors['primary'],
                           background=self.colors['bg_card'])
        
        # Treeview styles
        self.style.configure("Treeview", 
                           background="white",
                           foreground=self.colors['text_primary'],
                           fieldbackground="white",
                           rowheight=30,
                           font=('Segoe UI', 9))
        self.style.configure("Treeview.Heading", 
                           font=('Segoe UI', 9, 'bold'),
                           background=self.colors['bg_main'],
                           foreground=self.colors['text_primary'])
        self.style.map("Treeview", 
                      background=[('selected', self.colors['primary'])],
                      foreground=[('selected', 'white')])
        
        # Add custom style for Submit Manak button
        self.style.configure('SubmitManak.TButton',
            background=self.colors['info'],
            foreground='white',
            font=('Segoe UI', 11, 'bold'),
            borderwidth=0,
            padding=(10, 8))
        self.style.map('SubmitManak.TButton',
            background=[('active', '#2563eb'), ('pressed', '#2563eb'), ('!disabled', self.colors['info'])],
            foreground=[('active', 'white'), ('pressed', 'white'), ('!disabled', 'white')])
    
    def setup_global_exception_handler(self):
        """Setup global exception handler to prevent crashes"""
        import sys
        import traceback
        
        def handle_exception(exc_type, exc_value, exc_traceback):
            """Global exception handler"""
            if issubclass(exc_type, KeyboardInterrupt):
                # Allow keyboard interrupt to work normally
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            
            # Log the exception
            error_msg = f"Unhandled exception: {exc_type.__name__}: {exc_value}"
            print(f"CRITICAL ERROR: {error_msg}")
            print(f"Traceback: {traceback.format_exception(exc_type, exc_value, exc_traceback)}")
            
            # Show user-friendly error message instead of crashing
            try:
                if hasattr(self, 'root') and self.root:
                    self.root.after(0, lambda: messagebox.showerror("Application Error", 
                        f"An unexpected error occurred:\n\n{error_msg}\n\nThe application will continue running, but some features may not work properly.\n\nPlease restart the application if problems persist."))
            except:
                pass
        
        # Set the global exception handler
        sys.excepthook = handle_exception
        
        # Also handle tkinter exceptions
        def handle_tkinter_exception():
            """Handle tkinter exceptions"""
            try:
                import tkinter as tk
                original_report_callback_exception = tk.Tk.report_callback_exception
                
                def custom_report_callback_exception(self, exc, val, tb):
                    error_msg = f"Tkinter exception: {exc.__name__}: {val}"
                    print(f"TKINTER ERROR: {error_msg}")
                    print(f"Traceback: {traceback.format_exception(exc, val, tb)}")
                    
                    # Show user-friendly error message
                    try:
                        messagebox.showerror("Interface Error", 
                            f"A user interface error occurred:\n\n{error_msg}\n\nThe application will continue running.")
                    except:
                        pass
                
                tk.Tk.report_callback_exception = custom_report_callback_exception  # type: ignore
            except Exception as e:
                print(f"Failed to setup tkinter exception handler: {e}")
        
        handle_tkinter_exception()
    
    def load_custom_fonts(self):
        """Load custom fonts from 'fonts' directory if available"""
        try:
            # Look in project root 'fonts' directory
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            fonts_dir = os.path.join(project_root, 'fonts')
            
            if os.path.exists(fonts_dir):
                count = load_fonts_from_directory(fonts_dir)
                if count > 0:
                    self.log(f"✅ Loaded {count} custom fonts from {fonts_dir}", 'system')
                    # Could set a flag here or try to detect the font name
                    # For now, we assume user knows the font name and might change it in code or config
            else:
                # Create directory so user knows where to put them
                try:
                    os.makedirs(fonts_dir, exist_ok=True)
                except:
                    pass
        except Exception as e:
            print(f"Error loading custom fonts: {e}")

    def setup_executable_config(self):
        """Setup configurations specific to executable environment"""
        try:
            # Check if running as executable
            if getattr(sys, 'frozen', False):
                # Running as executable
                self.is_executable = True
                try:
                    self.base_path = sys._MEIPASS  # type: ignore
                except AttributeError:
                    self.base_path = os.path.dirname(os.path.abspath(sys.executable))
                print(f"Running as executable from: {self.base_path}")
            else:
                # Running as script
                self.is_executable = False
                self.base_path = os.path.dirname(os.path.abspath(__file__))
                print(f"Running as script from: {self.base_path}")
            
            # Ensure logs directory exists
            log_dir = os.path.join(self.base_path, 'logs')
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
                
        except Exception as e:
            print(f"Error setting up executable config: {e}")
            self.is_executable = False
            self.base_path = os.path.dirname(os.path.abspath(__file__))
    
    def test_critical_imports(self):
        """Test critical imports to prevent crashes"""
        critical_modules = [
            'mysql.connector',
            'selenium',
            'requests',
            'tkinter',
            'threading',
            'json',
            'base64',
            'datetime',
            'traceback'
        ]
        
        failed_imports = []
        
        for module in critical_modules:
            try:
                __import__(module)
                print(f"[OK] {module} imported successfully")
            except ImportError as e:
                failed_imports.append(f"{module}: {e}")
                print(f"✗ {module} import failed: {e}")
        
        if failed_imports:
            error_msg = "Critical modules failed to import:\n" + "\n".join(failed_imports)
            print(f"CRITICAL ERROR: {error_msg}")
            
            # Show error dialog
            try:
                messagebox.showerror("Critical Error", 
                    f"Some required modules are missing:\n\n{error_msg}\n\nThe application may not work properly.")
            except:
                pass
        
        return len(failed_imports) == 0
        
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
        
        # TAB ORDER (as requested):
        # 1. Login in MANAK (Browser)
        # 2. Accept Request
        # 3. Create Jobs (Job Cards)
        # 4. Bulk Jobs (Multiple Jobs)
        # 5. Single Jobs (Weight Entry)
        # 6. Delivery Voucher
        # 7. Settings
        
        # 1. Login in MANAK Tab (Browser Control)
        self.setup_browser_tab()
        
        # 2. Jeweller Request Tab (Moved here as requested)
        try:
            if JewellerRequestGenerator:
                self.jeweller_request_generator = JewellerRequestGenerator(
                    self.notebook,  # Notebook instance
                    None,  # Driver will be set later
                    self.log,
                    self.license_manager  # Pass license manager
                )
                self.log("✅ Jeweller Request loaded successfully", 'system')
        except Exception as e:
            self.jeweller_request_generator = None
            self.log(f"⚠️ Jeweller Request not available: {e}", 'system')

        # 3. Accept Request Tab
        self.setup_accept_request_tab()
        
        # 4. Create Jobs Tab (Simple Job Creator)
        try:
            from processors.simple_job_creator import SimpleJobCreator
            from processors.delivery_voucher_processor import DeliveryVoucherProcessor
            from processors.weight_capture_processor import WeightCaptureProcessor
            
            self.simple_job_creator = SimpleJobCreator(
                None,  # Driver will be set later when browser opens
                self.log,
                self.check_license_before_action,
                self  # Pass app context for settings access
            )
            self.simple_job_creator.setup_ui(self.notebook)
            self.log("✅ Create Jobs loaded successfully", 'system')
            
            # Store processors for later (will be added in order)
            self.delivery_voucher_processor = DeliveryVoucherProcessor(
                None,  # Driver will be set later when browser opens
                self.log,
                self.check_license_before_action,
                self  # Pass app context for settings access
            )
            
            self.weight_capture_processor = WeightCaptureProcessor(
                None,  # Driver will be set later when browser opens
                self.log,
                self.check_license_before_action,
                self  # Pass app context for settings access
            )
        except ImportError as e:
            self.simple_job_creator = None
            self.delivery_voucher_processor = None
            self.weight_capture_processor = None
            self.log(f"⚠️ Create Jobs not available: {e}", 'system')
            placeholder_frame = ttk.Frame(self.notebook)
            self.notebook.add(placeholder_frame, text="📋 Create Jobs (Unavailable)")
        except Exception as e:
            self.simple_job_creator = None
            self.delivery_voucher_processor = None
            self.weight_capture_processor = None
            self.log(f"❌ Error loading Create Jobs: {e}", 'system')
            placeholder_frame = ttk.Frame(self.notebook)
            self.notebook.add(placeholder_frame, text="📋 Create Jobs (Error)")
        
        # 5. Jobs Tab (Renamed from Bulk Jobs)
        if MultipleJobsProcessor:
            self.multiple_jobs_processor = MultipleJobsProcessor(
                None,  # Driver will be set later when browser opens
                self.log,
                self.check_license_before_action,
                self  # Pass main app reference for settings access
            )
            # We need to monkey-patch the tab title creation if it's hardcoded in the class
            # or just rely on the order here if it adds itself.
            # Usually it adds itself via setup_multiple_jobs_tab using self.notebook.add
            # Inspecting MultipleJobsProcessor would be cleaner but for now assuming it uses the text provided
            # Wait, we need to make sure the title is "Jobs"
            self.multiple_jobs_processor.setup_multiple_jobs_tab(self.notebook)
            # Iterate tabs to rename "Bulk Jobs" to "Jobs" if needed, 
            # but simpler to let it add and then we can rename last tab
            try:
                current_tab_count = self.notebook.index('end')
                self.notebook.tab(current_tab_count-1, text="📂 Jobs")
            except:
                pass

        # 6. Weight Capture Tab (Moved here as requested)
        try:
            if hasattr(self, 'weight_capture_processor') and self.weight_capture_processor:
                # Create tab frame first to avoid duplicates on error
                capture_frame = ttk.Frame(self.notebook)
                self.notebook.add(capture_frame, text="⚖️ Weight Capture")
                
                try:
                    # Now populate the tab
                    self.weight_capture_processor.populate_weight_capture_tab(capture_frame)
                    self.log("✅ Weight Capture module loaded successfully", 'system')
                except Exception as setup_error:
                    # Clear the frame and show error
                    for widget in capture_frame.winfo_children():
                        widget.destroy()
                    error_label = ttk.Label(capture_frame, 
                                          text=f"Error loading Weight Capture:\n{str(setup_error)}\n\nPlease check the logs.",
                                          font=('Segoe UI', 10),
                                          foreground='red',
                                          justify='center')
                    error_label.pack(expand=True, pady=50)
                    self.log(f"❌ Error setting up Weight Capture tab: {setup_error}", 'system')
                    import traceback
                    self.log(traceback.format_exc(), 'system')
        except Exception as e:
            self.log(f"❌ Error loading Weight Capture module: {e}", 'system')
            import traceback
            self.log(traceback.format_exc(), 'system')
        
        # 7. Get Jobs Data Tab (Renamed from Scan Jobs Details)
        try:
            # Check if class is available
            if 'DeliveryVoucherScanner' in globals() and DeliveryVoucherScanner is not None:
                self.delivery_voucher_scanner = DeliveryVoucherScanner(
                    None,  # Driver will be set later when browser opens
                    self.log,
                    self.check_license_before_action,
                    self  # Pass app context for settings access
                )
                self.delivery_voucher_scanner.setup_scanner_tab(self.notebook)
                
                # Check if tab was actually added before trying to rename
                # If scanner failed silently inside setup, tab count won't increase
                try:
                    # Rename the last added tab
                    current_tab_count = self.notebook.index('end')
                    # Optionally verify it's the right tab? For now assume sequential adding
                    self.notebook.tab(current_tab_count-1, text="📊 Get Jobs Data")
                except:
                    pass
                self.log("✅ Get Jobs Data module loaded successfully", 'system')
            else:
                self.delivery_voucher_scanner = None
                self.log("⚠️ DeliveryVoucherScanner class not available (Import failed?)", 'system')
        except Exception as e:
            self.delivery_voucher_scanner = None
            self.log(f"⚠️ Get Jobs Data module error: {e}", 'system')
            # Add placeholder so user knows it failed
            try:
                placeholder = ttk.Frame(self.notebook)
                self.notebook.add(placeholder, text="📊 Get Jobs Data (Error)")
                ttk.Label(placeholder, text=f"Error loading module: {e}").pack(padx=20, pady=20)
            except:
                pass

        # 8. Delivery Voucher Tab
        try:
            if hasattr(self, 'delivery_voucher_processor') and self.delivery_voucher_processor:
                self.delivery_voucher_processor.setup_delivery_voucher_tab(self.notebook)
                self.log("✅ Delivery Voucher module loaded successfully", 'system')
        except Exception as e:
            self.log(f"❌ Error loading Delivery Voucher tab: {e}", 'system')
            # Add placeholder
            placeholder = ttk.Frame(self.notebook)
            self.notebook.add(placeholder, text="📦 Delivery Voucher (Error)")
            ttk.Label(placeholder, text=f"Error loading module: {e}").pack(padx=20, pady=20)

        # 9. Migrate Jobs Tab (Completed Jobs Scanner - RENAMED)
        try:
            if CompletedJobsScanner:
                self.completed_jobs_scanner = CompletedJobsScanner(
                    None,  # driver set later
                    self.log,
                    self.check_license_before_action,
                    self
                )
                self.completed_jobs_scanner.setup_completed_jobs_tab(self.notebook)
                self.log("✅ Migrate Jobs module loaded successfully", 'system')
            else:
                self.completed_jobs_scanner = None
                self.log("⚠️ CompletedJobsScanner class not available", 'system')
        except Exception as e:
            self.completed_jobs_scanner = None
            self.log(f"⚠️ Migrate Jobs module error: {e}", 'system')
            try:
                placeholder = ttk.Frame(self.notebook)
                self.notebook.add(placeholder, text="🔄 Migrate Jobs")
            except:
                pass

        # 10. Bill Migrate Tab (Bill Import - RENAMED)
        try:
            if BillImportProcessor:
                self.bill_import_processor = BillImportProcessor(
                    self,  # master Tkinter widget
                    DB_CONFIG,  # database configuration
                    self.completed_jobs_scanner,  # reference to scanner for accessing scanned_jobs
                    self.license_manager  # license manager for firm_id
                )
                # Create UI frame for the processor
                bill_import_frame = ttk.Frame(self.notebook)
                self.notebook.add(bill_import_frame, text="📄 Bill Migrate")
                self.bill_import_processor.create_ui(bill_import_frame)
                self.log("✅ Bill Migrate module loaded successfully", 'system')
            else:
                self.bill_import_processor = None
                self.log("⚠️ BillImportProcessor class not available", 'system')
        except Exception as e:
            self.bill_import_processor = None
            self.log(f"⚠️ Bill Migrate module error: {e}", 'system')
            try:
                placeholder = ttk.Frame(self.notebook)
                self.notebook.add(placeholder, text="📄 Bill Migrate")
            except:
                pass
            
        # 11. Settings Tab (after Bill Migrate)
        try:
            self.setup_settings_tab()
            self.log("✅ Settings tab loaded successfully", 'system')
        except Exception as e:
            self.log(f"❌ Error loading Settings tab: {e}", 'system')
            placeholder = ttk.Frame(self.notebook)
            self.notebook.add(placeholder, text="⚙️ Settings (Error)")
            ttk.Label(placeholder, text=f"Error loading settings: {e}").pack(padx=20, pady=20)
        
        # Keep tabs compact so all menu items fit in one row.
        self.compact_notebook_tab_labels()
        
        
        # Hidden Single Jobs tab (kept for compatibility but not in main flow)
        # self.setup_weight_tab_compact()
        
        
    def compact_notebook_tab_labels(self):
        """Shorten tab labels to improve visibility on smaller widths"""
        if not hasattr(self, 'notebook') or not self.notebook:
            return
        
        label_map = {
            "Login in MANAK": "Login",
            "Generate Request": "Generate Req",
            "Accept Request": "Accept Req",
            "Create Jobs": "Create Jobs",
            "Weight Capture": "Weight Cap",
            "Get Jobs Data": "Get Jobs",
            "Delivery Voucher": "Delivery Vchr",
            "Completed Jobs": "Completed",
            "Migrate Jobs": "Migrate",
            "Bill Migrate": "Bill Migr",
            "Settings": "Settings",
            "Single Jobs": "Single Jobs"
        }
        
        for tab_id in self.notebook.tabs():
            tab_text = (self.notebook.tab(tab_id, "text") or "").strip()
            normalized_text = tab_text
            
            # Remove leading emoji/symbol to save width.
            if " " in normalized_text:
                first_token, rest = normalized_text.split(" ", 1)
                if any(ord(ch) > 127 for ch in first_token):
                    normalized_text = rest.strip()
            
            for full_text, compact_text in label_map.items():
                if full_text in normalized_text:
                    normalized_text = compact_text
                    break
            
            self.notebook.tab(tab_id, text=normalized_text)
    
    def setup_settings_tab(self):
        """Setup main Settings tab using legacy full settings UI."""
        # Prevent duplicate Settings tabs if setup_ui is invoked more than once.
        for tab_id in self.notebook.tabs():
            tab_text = (self.notebook.tab(tab_id, "text") or "").strip()
            if "Settings" in tab_text:
                self.notebook.select(tab_id)
                return

        # The legacy implementation includes full device verification,
        # credentials, and API URL fields expected by current workflows.
        self._OLD_setup_settings_tab()
    
    def _test_url(self, url):
        """Test if a URL is accessible"""
        import requests
        try:
            response = requests.head(url, timeout=5, verify=True)
            if response.status_code < 400:
                messagebox.showinfo("URL Test", f"✅ URL is accessible\nStatus: {response.status_code}")
            else:
                messagebox.showwarning("URL Test", f"⚠️ URL returned status {response.status_code}")
        except Exception as e:
            messagebox.showerror("URL Test", f"❌ URL is not accessible\n{str(e)}")
    
    def setup_browser_tab(self):
        """Setup Login in MANAK tab with enhanced UI for Dual Browsers"""
        browser_frame = ttk.Frame(self.notebook)
        self.notebook.add(browser_frame, text="🔐 Login in MANAK")
        
        # Browser controls card
        control_card = ttk.LabelFrame(browser_frame, text="🎛️ Browser Controls", style='Compact.TLabelframe')
        control_card.pack(fill='x', padx=10, pady=(10, 8))
        
        # Button grid
        btn_container = ttk.Frame(control_card)
        btn_container.pack(fill='x', padx=10, pady=10)
        
        # QM Browser Controls
        qm_frame = ttk.LabelFrame(btn_container, text="👤 QM Browser (Main)", style='Compact.TLabelframe')
        qm_frame.pack(fill='x', pady=(0, 10))
        
        qm_btns = ttk.Frame(qm_frame)
        qm_btns.pack(fill='x', padx=5, pady=5)
        
        self.open_btn = ttk.Button(qm_btns, text="🚀 Open QM Browser", style='Compact.TButton', command=self.open_browser)
        self.open_btn.pack(side='left', padx=(0, 5))
        
        self.login_btn = ttk.Button(qm_btns, text="🔑 Login Page", style='Info.TButton', command=self.navigate_to_login, state='disabled')
        self.login_btn.pack(side='left', padx=(0, 5))
        
        self.check_btn = ttk.Button(qm_btns, text="🔍 Check Login", style='Success.TButton', command=self.check_login, state='disabled')
        self.check_btn.pack(side='left', padx=(0, 5))
        
        self.close_btn = ttk.Button(qm_btns, text="❌ Close QM", style='Danger.TButton', command=self.close_browser, state='disabled')
        self.close_btn.pack(side='left')

        # Reception Browser Controls
        rec_frame = ttk.LabelFrame(btn_container, text="👤 Reception Browser", style='Compact.TLabelframe')
        rec_frame.pack(fill='x')
        
        rec_btns = ttk.Frame(rec_frame)
        rec_btns.pack(fill='x', padx=5, pady=5)
        
        self.open_reception_btn_main = ttk.Button(rec_btns, text="🚀 Open Reception Browser", style='Compact.TButton', command=self.open_reception_browser)
        self.open_reception_btn_main.pack(side='left', padx=(0, 5))
        
        self.close_reception_btn_main = ttk.Button(rec_btns, text="❌ Close Reception", style='Danger.TButton', command=self.close_reception_browser, state='disabled')
        self.close_reception_btn_main.pack(side='left')
        
        # Status display card
        status_card = ttk.LabelFrame(browser_frame, text="📋 Status Log", style='Compact.TLabelframe')
        status_card.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        self.status_text = scrolledtext.ScrolledText(status_card, height=8, font=('Consolas', 8), 
                                                   bg='#f8f9fa', fg='#495057', wrap=tk.WORD)
        self.status_text.pack(fill='both', expand=True, padx=10, pady=10)
        
    def setup_weight_tab_compact(self):
        """Setup Single Jobs tab with COMPACT RESPONSIVE design - NO SCROLLING"""
        weight_frame = ttk.Frame(self.notebook)
        self.notebook.add(weight_frame, text="⚖️ Single Jobs")
        
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
        request_card = ttk.LabelFrame(parent, text="📋 Request Details", style='Compact.TLabelframe')
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
        
        # Bind job entry to update button text
        self.job_entry.bind('<KeyRelease>', self.on_job_number_change)
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
        
        # Load & Fetch buttons (hide Load Page)
        btn_container = ttk.Frame(request_card)
        btn_container.pack(fill='x', padx=8, pady=(0, 8))
        self.fetch_data_btn = ttk.Button(btn_container, text="🔎 Fetch Data", style='Info.TButton', command=self.smart_fetch_data, state='disabled')
        self.fetch_data_btn.pack(fill='x', pady=2)
        
        # Sampling Details card - COMPACT
        sampling_card = ttk.LabelFrame(parent, text="🏷️ Sampling Details", style='Compact.TLabelframe')
        sampling_card.pack(fill='x', pady=(0, 8))
        
        sampling_grid = ttk.Frame(sampling_card)
        sampling_grid.pack(fill='x', padx=8, pady=8)
        
        # Scrap Weight and Button Weight in same row (inline)
        ttk.Label(sampling_grid, text="Scrap Wt:", font=('Segoe UI', 8, 'bold')).grid(row=0, column=0, sticky='w', pady=2)
        self.scrap_entry = ttk.Entry(sampling_grid, width=12, style='Compact.TEntry', font=('Segoe UI', 10, 'bold'))
        self.scrap_entry.grid(row=0, column=1, pady=2, padx=(5, 10))
        
        # Button Weight in same row
        ttk.Label(sampling_grid, text="Button Wt:", font=('Segoe UI', 8, 'bold')).grid(row=0, column=2, sticky='w', pady=2, padx=(10, 0))
        self.button_entry = ttk.Entry(sampling_grid, width=12, style='Compact.TEntry', font=('Segoe UI', 10, 'bold'))
        self.button_entry.grid(row=0, column=3, pady=2, padx=(5, 0))
        
        # Initialize weight entries dict
        self.weight_entries = {
            'num_scrap_weight': self.scrap_entry,
            'buttonweight': self.button_entry
        }
        
        # Available Lots/Strips card
        self.strip_table_frame = ttk.LabelFrame(parent, text="📊 Available Lots", style='Compact.TLabelframe')
        self.strip_table_frame.pack(fill='x', pady=(0, 8))
        
        # Control buttons card - COMPACT
        control_card = ttk.LabelFrame(parent, text="🎮 Controls", style='Compact.TLabelframe')
        control_card.pack(fill='x', pady=(0, 8))
        
        control_btn_frame = ttk.Frame(control_card)
        control_btn_frame.pack(fill='x', padx=8, pady=8)
        
        # Automated workflow button (renamed and styled)
        self.submit_manak_btn = ttk.Button(control_btn_frame, text="Submit Manak", style='SubmitManak.TButton', command=self.auto_workflow, state='normal')
        self.submit_manak_btn.pack(fill='x', pady=2)
        
        # Restore Clear All button in Controls section
        self.clear_btn = ttk.Button(control_btn_frame, text="🧹 Clear All", style='Danger.TButton', command=self.clear_weight_fields)
        self.clear_btn.pack(fill='x', pady=2)
        
        # Compact weight log card
        weight_log_card = ttk.LabelFrame(parent, text="📝 Entry Log", style='Compact.TLabelframe')
        weight_log_card.pack(fill='both', expand=True)
        
        self.weight_log = scrolledtext.ScrolledText(weight_log_card, height=8, font=('Consolas', 7), 
                                                  bg='#f8f9fa', fg='#495057', wrap=tk.WORD)
        self.weight_log.pack(fill='both', expand=True, padx=8, pady=8)
        
        # Instructions
        instructions = """
🚀 QUICK START:
1. Open Browser → Login
2. Enter Request & Job → Click "Auto Workflow" 🚀

📦 LOT SELECTION:
• Manual: Use dropdown in Request Details
• API: Use dropdown in Available Lots
• Auto Workflow: Automatically selects and fills

⚡ AUTO WORKFLOW:
• Loads page automatically
• Fetches API data
• Selects appropriate lot
• Fills all fields in UI and portal
• Brings browser to front
        """.strip()
        
        self.log(instructions)
        
    def setup_right_section_table(self, parent):
        """Setup right section with Fire Assaying table layout matching web interface"""
        
        # Delta Calculation Section - NEW
        delta_card = ttk.LabelFrame(parent, text="🧮 Delta Calculations", style='Compact.TLabelframe')
        delta_card.pack(fill='x', padx=0, pady=(0, 8))
        
        # Create delta calculation display
        self.create_delta_calculation_section(delta_card)
        
        # Fire Assaying Details card
        fire_card = ttk.LabelFrame(parent, text="🔥 Fire Assaying Details", style='Compact.TLabelframe')
        fire_card.pack(fill='both', expand=True, padx=0, pady=0)
        
        # Create table container with padding
        table_container = ttk.Frame(fire_card)
        table_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create the table matching web interface structure
        self.create_fire_assaying_table(table_container)
        
    def create_delta_calculation_section(self, parent):
        """Create the delta calculation display section"""
        
        # Main frame for delta calculations
        delta_frame = ttk.Frame(parent)
        delta_frame.pack(fill='x', padx=10, pady=8)
        
        # Configure grid weights
        for i in range(6):
            delta_frame.columnconfigure(i, weight=1, minsize=100)
        
        # Header row
        headers = ["C1 Initial (mg)", "C1 M2 (mg)", "C1 Delta (mg)", "C2 Initial (mg)", "C2 M2 (mg)", "C2 Delta (mg)"]
        for col, header in enumerate(headers):
            header_label = tk.Label(delta_frame, text=header, font=('Segoe UI', 8, 'bold'), 
                                  bg='#6c757d', fg='white', relief='solid', borderwidth=1,
                                  justify='center')
            header_label.grid(row=0, column=col, sticky='ew', padx=1, pady=1, ipady=4)
        
        # Values row
        # C1 Initial (read-only display)
        self.c1_initial_display = tk.Label(delta_frame, text="0.000", font=('Segoe UI', 9, 'bold'), 
                                          bg='#e8f5e9', relief='solid', borderwidth=1, justify='center')
        self.c1_initial_display.grid(row=1, column=0, sticky='ew', padx=1, pady=1, ipady=4)
        
        # C1 M2 (read-only display)
        self.c1_m2_display = tk.Label(delta_frame, text="0.000", font=('Segoe UI', 9, 'bold'), 
                                     bg='#e8f5e9', relief='solid', borderwidth=1, justify='center')
        self.c1_m2_display.grid(row=1, column=1, sticky='ew', padx=1, pady=1, ipady=4)
        
        # C1 Delta (calculated, read-only)
        self.c1_delta_display = tk.Label(delta_frame, text="0.000", font=('Segoe UI', 9, 'bold'), 
                                        bg='#28a745', fg='white', relief='solid', borderwidth=1, justify='center')
        self.c1_delta_display.grid(row=1, column=2, sticky='ew', padx=1, pady=1, ipady=4)
        
        # C2 Initial (read-only display)
        self.c2_initial_display = tk.Label(delta_frame, text="0.000", font=('Segoe UI', 9, 'bold'), 
                                          bg='#f3e5f5', relief='solid', borderwidth=1, justify='center')
        self.c2_initial_display.grid(row=1, column=3, sticky='ew', padx=1, pady=1, ipady=4)
        
        # C2 M2 (read-only display)
        self.c2_m2_display = tk.Label(delta_frame, text="0.000", font=('Segoe UI', 9, 'bold'), 
                                     bg='#f3e5f5', relief='solid', borderwidth=1, justify='center')
        self.c2_m2_display.grid(row=1, column=4, sticky='ew', padx=1, pady=1, ipady=4)
        
        # C2 Delta (calculated, read-only)
        self.c2_delta_display = tk.Label(delta_frame, text="0.000", font=('Segoe UI', 9, 'bold'), 
                                        bg='#28a745', fg='white', relief='solid', borderwidth=1, justify='center')
        self.c2_delta_display.grid(row=1, column=5, sticky='ew', padx=1, pady=1, ipady=4)
        
        # Average Delta row
        avg_frame = ttk.Frame(parent)
        avg_frame.pack(fill='x', padx=10, pady=(0, 8))
        
        ttk.Label(avg_frame, text="📊 Average Delta:", font=('Segoe UI', 9, 'bold')).pack(side='left', padx=(0, 10))
        
        self.avg_delta_display = tk.Label(avg_frame, text="0.000", font=('Segoe UI', 10, 'bold'), 
                                         bg='#007bff', fg='white', relief='solid', borderwidth=1, 
                                         justify='center', padx=20, pady=5)
        self.avg_delta_display.pack(side='left')
        
        # Status indicator
        self.delta_status_label = tk.Label(avg_frame, text="⏳ Enter C1 and C2 values to calculate", 
                                         font=('Segoe UI', 8), fg='#6c757d')
        self.delta_status_label.pack(side='left', padx=(20, 0))
        
        # Manual calculation button
        calc_btn = ttk.Button(avg_frame, text="🔄 Recalculate", style='Info.TButton', 
                             command=self.calculate_deltas)
        calc_btn.pack(side='right', padx=(0, 10))
        
        # Purity threshold input
        purity_frame = ttk.Frame(parent)
        purity_frame.pack(fill='x', padx=10, pady=(0, 8))
        
        ttk.Label(purity_frame, text="🎯 Purity Threshold (%):", font=('Segoe UI', 9, 'bold')).pack(side='left', padx=(0, 10))
        
        self.purity_threshold_var = tk.StringVar(value="91.6")
        purity_entry = ttk.Entry(purity_frame, textvariable=self.purity_threshold_var, width=8, 
                                style='Compact.TEntry', font=('Segoe UI', 9, 'bold'))
        purity_entry.pack(side='left', padx=(0, 10))
        
        # Calculate fineness button
        fineness_btn = ttk.Button(purity_frame, text="🧮 Calculate Fineness", style='Success.TButton', 
                                 command=self.calculate_all_fineness)
        fineness_btn.pack(side='left', padx=(0, 10))
        
        # Show theoretical fineness button
        theoretical_btn = ttk.Button(purity_frame, text="📊 Show Theoretical", style='Info.TButton', 
                                   command=self.show_theoretical_fineness)
        theoretical_btn.pack(side='left', padx=(0, 10))
        
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
            "Delta Values\n∆", "Fineness\nPurity Report", "Mean Fineness\nReport (W)", "Remarks\n(Pass/Fail/Repeat )"
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
            'delta': 'delta12',  # Add delta field for strip 2
            'fineness': 'num_fineness_report_goldM11',
            'mean_fineness': None,  # No mean fineness for strip 2
            'remarks': 'str_remarksM12'  # Add remarks field for strip 2
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
        
        # Bind delta calculations after all entries are created
        self.bind_delta_calculations()
        
        # Bind fineness calculations after all entries are created
        self.bind_fineness_calculations()
        
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
        # Check license before automation
        if not self.check_license_before_action("weight automation"):
            return
            
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
            # Get the correct lot number - prioritize current_lot_no, then lot_var, then manual_lot_var
            if hasattr(self, 'current_lot_no') and self.current_lot_no:
                selected_lot = str(self.current_lot_no)
            elif hasattr(self, 'lot_var') and self.lot_var.get():
                selected_lot = str(self.lot_var.get())
            else:
                selected_lot = str(self.manual_lot_var.get())
            self.current_lot_no = selected_lot
            self.log(f"🎯 Save Initial Weights will use Lot: {selected_lot}", 'weight')
            threading.Thread(target=self._save_initial_weights_worker, args=(request_no, job_no, selected_lot), daemon=True).start()
        except Exception as e:
            self.log(f"❌ Error starting save initial weights workflow: {str(e)}", 'weight')
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
            weight_url = f"{portal_config.portal_base()}/MANAK/UID_WeighingForm?requestNo={encoded_request}&jobNo={encoded_job}"
            self.driver.get(weight_url) # type: ignore
            time.sleep(3)
            current_url = self.driver.current_url # pyright: ignore[reportOptionalMemberAccess]
            if 'UID_WeighingForm' not in current_url:
                raise Exception("Failed to load weight page")
            self.page_loaded = True
            self.log(f"✅ Weight page loaded: {current_url}", 'weight')
            # Step 2: Select Lot No in the portal using Select2 widget
            try:
                select2_container = self.driver.find_element(By.ID, "s2id_lotno") # pyright: ignore[reportOptionalMemberAccess]
                select2_container.click()
                time.sleep(0.5)
                options = self.driver.find_elements(By.CSS_SELECTOR, "ul.select2-results li") # pyright: ignore[reportOptionalMemberAccess]
                found = False
                for option in options:
                    if option.text.strip().endswith(f"Lot {selected_lot}") or option.text.strip() == f"Lot {selected_lot}":
                        option.click()
                        found = True
                        self.log(f"✅ Selected Lot {selected_lot} in portal via Select2", 'weight')
                        break
                if not found:
                    raise Exception(f"Lot {selected_lot} not found in Select2 options")
                time.sleep(1)
                lot_dropdown = self.driver.find_element(By.ID, "lotno") # pyright: ignore[reportOptionalMemberAccess]
                selected_value = lot_dropdown.get_attribute('value')
                if selected_value != str(selected_lot):
                    self.log(f"⚠️ Lot selection verification failed: expected {selected_lot}, got {selected_value}", 'weight')
                else:
                    self.log(f"✅ Lot selection verified: {selected_value}", 'weight')
            except Exception as select2_error:
                self.log(f"⚠️ Select2 lot selection failed: {str(select2_error)}. Trying fallback methods...", 'weight')
                try:
                    wait = WebDriverWait(self.driver, 10) # pyright: ignore[reportArgumentType]
                    lot_dropdown = wait.until(EC.presence_of_element_located((By.ID, "lotno")))
                    if not lot_dropdown.is_displayed() or not lot_dropdown.is_enabled():
                        self.driver.execute_script("arguments[0].style.display = 'block'; arguments[0].removeAttribute('readonly');", lot_dropdown) # pyright: ignore[reportOptionalMemberAccess]
                        time.sleep(0.5)
                    self.driver.execute_script("arguments[0].value = '';", lot_dropdown) # type: ignore
                    time.sleep(0.2)
                    from selenium.webdriver.support.select import Select
                    select_element = Select(lot_dropdown)
                    select_element.select_by_value(selected_lot)
                    self.log(f"✅ Selected Lot {selected_lot} in portal via Select fallback", 'weight')
                    time.sleep(1)
                except Exception as fallback_error:
                    self.log(f"❌ Could not select lot in portal: {str(fallback_error)}", 'weight')
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
                    element = self.driver.find_element(By.ID, field_name) # type: ignore
                    if element.is_displayed() and element.is_enabled():
                        element.clear()
                        element.send_keys(value)
                        filled_count += 1
                        self.log(f"✅ Filled {field_name}: {value}", 'weight')
                        # Click savesampleweight button
                        try:
                            save_btn = self.driver.find_element(By.ID, 'savesampleweight')  # type: ignore
                            if save_btn.is_displayed() and save_btn.is_enabled():
                                save_btn.click()
                                self.log("💾 Clicked Save Sample Weight button", 'weight')
                                time.sleep(1)
                        except Exception as e:
                            self.log(f"❌ Error clicking Save Sample Weight button: {str(e)}", 'weight')
                    else:
                        skipped_count += 1
                except Exception as e:
                    error_count += 1
                    self.log(f"❌ Error filling {field_name}: {str(e)}", 'weight')
            # 2. Fill Button Weight
            for field_name in ['buttonweight']:
                try:
                    value = self.weight_entries[field_name].get().strip()
                    if not value:
                        skipped_count += 1
                        continue
                    element = self.driver.find_element(By.ID, field_name) # type: ignore
                    if element.is_displayed() and element.is_enabled():
                        element.clear()
                        element.send_keys(value)
                        filled_count += 1
                        self.log(f"✅ Filled {field_name}: {value}", 'weight')
                        # Click savebuttonweight button
                        try:
                            save_btn = self.driver.find_element(By.ID, 'savebuttonweight')  # type: ignore
                            if save_btn.is_displayed() and save_btn.is_enabled():
                                save_btn.click()
                                self.log("💾 Clicked Save Button Weight button", 'weight')
                                time.sleep(1)
                        except Exception as e:
                            self.log(f"❌ Error clicking Save Button Weight button: {str(e)}", 'weight')
                    else:
                        skipped_count += 1
                except Exception as e:
                    error_count += 1
                    self.log(f"❌ Error filling {field_name}: {str(e)}", 'weight')
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
                    element = self.driver.find_element(By.ID, field_name)  # type: ignore
                    if element.is_displayed() and element.is_enabled():
                        element.clear()
                        element.send_keys(value)
                        filled_count += 1
                        self.log(f"✅ Filled {field_name}: {value}", 'weight')
                    else:
                        skipped_count += 1
                except Exception as e:
                    error_count += 1
                    self.log(f"❌ Error filling {field_name}: {str(e)}", 'weight')
            # Click Save (Initial Weight) button for strips
            try:
                save_btn = self.driver.find_element(By.ID, 'chechkgoldM12')  # type: ignore
                if save_btn.is_displayed() and save_btn.is_enabled():
                    save_btn.click()
                    self.log("💾 Clicked Save (Initial Weight) button for strips", 'weight')
                    time.sleep(1)
                else:
                    self.log("⚠️ Save (Initial Weight) button for strips not interactable", 'weight')
            except Exception as e:
                self.log(f"❌ Error clicking Save (Initial Weight) button for strips: {str(e)}", 'weight')
            # Summary
            self.log(f"🎯 INITIAL WEIGHT FILL COMPLETE:", 'weight')
            self.log(f"✅ Filled: {filled_count} | ⚠️ Skipped: {skipped_count} | ❌ Errors: {error_count}", 'weight')
            loading_dialog.update_status("Done!")
            loading_dialog.update_message("All initial weight fields filled in portal.")
            time.sleep(1)
            loading_dialog.close()
            if filled_count > 0:
                messagebox.showinfo("Success", f"✅ Successfully filled {filled_count} initial weight fields!")
            else:
                messagebox.showwarning("No Changes", "No initial weight fields were filled. Please check your inputs.")
            self.log_memory_usage("after save initial weights")
        except Exception as e:
            if loading_dialog:
                loading_dialog.close()
            self.log(f"❌ Error in save initial weights workflow: {str(e)}", 'weight')
            messagebox.showerror("Error", f"Error in save initial weights workflow: {str(e)}")
    
    def auto_workflow(self):
        """Automated workflow: Fill portal fields with current UI values only (no API fetch)"""
        # Check license before automation
        if not self.check_license_before_action("automation workflow"):
            return
            
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
            # Get the correct lot number - prioritize current_lot_no, then lot_var, then manual_lot_var
            if hasattr(self, 'current_lot_no') and self.current_lot_no:
                selected_lot = str(self.current_lot_no)
            elif hasattr(self, 'lot_var') and self.lot_var.get():
                selected_lot = str(self.lot_var.get())
            else:
                selected_lot = str(self.manual_lot_var.get())
            self.current_lot_no = selected_lot
            self.log(f"🎯 Auto workflow will use Lot: {selected_lot}", 'weight')
            threading.Thread(target=self._auto_workflow_worker, args=(request_no, job_no, selected_lot), daemon=True).start()
        except Exception as e:
            self.log(f"❌ Error starting auto workflow: {str(e)}", 'weight')
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
            weight_url = f"{portal_config.portal_base()}/MANAK/UID_WeighingForm?requestNo={encoded_request}&jobNo={encoded_job}"
            self.driver.get(weight_url)  # type: ignore
            time.sleep(3)
            current_url = self.driver.current_url  # type: ignore
            if 'UID_WeighingForm' not in current_url:
                raise Exception("Failed to load weight page")
            self.page_loaded = True
            self.log(f"✅ Weight page loaded: {current_url}", 'weight')
            # Step 2: Select Lot No in the portal using Select2 widget
            try:
                select2_container = self.driver.find_element(By.ID, "s2id_lotno")  # type: ignore
                select2_container.click()
                time.sleep(0.5)
                options = self.driver.find_elements(By.CSS_SELECTOR, "ul.select2-results li")  # type: ignore
                found = False
                for option in options:
                    if option.text.strip().endswith(f"Lot {selected_lot}") or option.text.strip() == f"Lot {selected_lot}":
                        option.click()
                        found = True
                        self.log(f"✅ Selected Lot {selected_lot} in portal via Select2", 'weight')
                        break
                if not found:
                    raise Exception(f"Lot {selected_lot} not found in Select2 options")
                time.sleep(1)
                lot_dropdown = self.driver.find_element(By.ID, "lotno")  # type: ignore  # type: ignore
                selected_value = lot_dropdown.get_attribute('value')
                if selected_value != str(selected_lot):
                    self.log(f"⚠️ Lot selection verification failed: expected {selected_lot}, got {selected_value}", 'weight')
                else:
                    self.log(f"✅ Lot selection verified: {selected_value}", 'weight')
            except Exception as select2_error:
                self.log(f"⚠️ Select2 lot selection failed: {str(select2_error)}. Trying fallback methods...", 'weight')
                try:
                    wait = WebDriverWait(self.driver, 10)  # type: ignore
                    lot_dropdown = wait.until(EC.presence_of_element_located((By.ID, "lotno")))
                    if not lot_dropdown.is_displayed() or not lot_dropdown.is_enabled():
                        self.driver.execute_script("arguments[0].style.display = 'block'; arguments[0].removeAttribute('readonly');", lot_dropdown)  # type: ignore
                        time.sleep(0.5)
                    self.driver.execute_script("arguments[0].value = '';", lot_dropdown)  # type: ignore
                    time.sleep(0.2)
                    from selenium.webdriver.support.select import Select
                    select_element = Select(lot_dropdown)
                    select_element.select_by_value(selected_lot)
                    self.log(f"✅ Selected Lot {selected_lot} in portal via Select fallback", 'weight')
                    time.sleep(1)
                except Exception as fallback_error:
                    self.log(f"❌ Could not select lot in portal: {str(fallback_error)}", 'weight')
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
                    element = self.driver.find_element(By.ID, field_name)  # type: ignore  # type: ignore
                    if element.is_displayed() and element.is_enabled():
                        element.clear()
                        element.send_keys(value)
                        filled_count += 1
                        self.log(f"✅ Filled {field_name}: {value}", 'weight')
                    else:
                        skipped_count += 1
                except Exception as e:
                    error_count += 1
                    self.log(f"❌ Error filling {field_name}: {str(e)}", 'weight')
            # Step 4: Fill all Fire Assaying fields
            for field_name, field_id in self.field_ids.items():
                if field_name in ['num_scrap_weight', 'buttonweight']:
                    continue  # Already filled
                try:
                    value = self.weight_entries[field_name].get().strip()
                    if not value:
                        skipped_count += 1
                        continue
                    element = self.driver.find_element(By.ID, field_id)  # type: ignore
                    if element.is_displayed() and element.is_enabled():
                        element.clear()
                        element.send_keys(value)
                        filled_count += 1
                        self.log(f"✅ Filled {field_id}: {value}", 'weight')
                    else:
                        skipped_count += 1
                except Exception as e:
                    error_count += 1
                    self.log(f"❌ Error filling {field_id}: {str(e)}", 'weight')
            # Summary
            self.log(f"🎯 WORKFLOW COMPLETE: Fields filled in portal.", 'weight')
            self.log(f"✅ Filled: {filled_count} | ⚠️ Skipped: {skipped_count} | ❌ Errors: {error_count}", 'weight')
            loading_dialog.update_status("Done!")
            loading_dialog.update_message("All fields filled in portal.")
            time.sleep(1)
            loading_dialog.close()
        except Exception as e:
            if loading_dialog:
                loading_dialog.close()
            self.log(f"❌ Error in auto workflow: {str(e)}", 'weight')
            messagebox.showerror("Error", f"Error in auto workflow: {str(e)}")
    
    def select_lot_in_portal(self):
        """Manually select lot in portal without fetching API data"""
        # Check license before automation
        if not self.check_license_before_action("lot selection"):
            return
            
        try:
            if not self.driver or not self.page_loaded:
                messagebox.showwarning("Not Ready", "Please load weight page first")
                return
            
            # Get the manually selected lot
            lot_no = self.manual_lot_var.get()
            self.current_lot_no = lot_no
            
            from selenium.webdriver.support.wait import WebDriverWait
            from selenium.webdriver.support.select import Select
            from selenium.webdriver.support import expected_conditions as EC
            import time
            
            # Select the correct lot in the portal
            try:
                wait = WebDriverWait(self.driver, 10)  # type: ignore
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
                    self.log(f"✅ Selected Lot {lot_no} in portal via Select", 'weight')
                except Exception as select_error:
                    # Try direct value setting
                    try:
                        self.driver.execute_script(f"arguments[0].value = '{lot_no}';", lot_dropdown)
                        self.driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", lot_dropdown)
                        self.log(f"✅ Selected Lot {lot_no} in portal via direct value", 'weight')
                    except Exception as direct_error:
                        # Try by index (lot_no - 1)
                        try:
                            select_element = Select(lot_dropdown)
                            select_element.select_by_index(int(lot_no) - 1)
                            self.log(f"✅ Selected Lot {lot_no} in portal via index", 'weight')
                        except Exception as index_error:
                            self.log(f"⚠️ Could not select lot in portal: {str(select_error)} | Direct: {str(direct_error)} | Index: {str(index_error)}", 'weight')
                
                # Verify selection was successful
                time.sleep(1)  # Wait for page to update
                try:
                    selected_value = lot_dropdown.get_attribute('value')  # type: ignore
                    if selected_value != lot_no:
                        self.log(f"⚠️ Lot selection verification failed: expected {lot_no}, got {selected_value}", 'weight')
                    else:
                        self.log(f"✅ Lot selection verified: {selected_value}", 'weight')
                except:
                    pass
                    
            except Exception as e:
                self.log(f"⚠️ Could not find lot dropdown: {str(e)}", 'weight')
                
        except Exception as e:
            self.log(f"❌ Error selecting lot in portal: {str(e)}", 'weight')
            messagebox.showerror("Error", f"Error selecting lot: {str(e)}")
    
    def save_cornet_weights(self):
        """Save cornet weights and related fields to portal, and optionally submit HUID if checkbox is checked. Always loads the page, shows progress dialog, and selects the lot."""
        # Check license before automation
        if not self.check_license_before_action("cornet weight automation"):
            return
            
        loading_dialog = None
        try:
            from selenium.webdriver.support.wait import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            import time
            # Get the correct lot number using helper method
            lot_no = self._get_current_lot_selection()
            request_no = self.request_entry.get().strip()
            job_no = self.job_entry.get().strip()
            loading_dialog = LoadingDialog(self.root, "Save Cornet Weights", "Filling cornet weights and saving...")
            loading_dialog.update_status("Loading weight page...")
            loading_dialog.update_message("Loading weight entry page for the request...")
            encoded_request = base64.b64encode(str(request_no).encode()).decode()
            encoded_job = base64.b64encode(str(job_no).encode()).decode()
            weight_url = f"{portal_config.portal_base()}/MANAK/UID_WeighingForm?requestNo={encoded_request}&jobNo={encoded_job}"
            self.driver.get(weight_url)  # type: ignore
            time.sleep(3)
            current_url = self.driver.current_url # type: ignore
            if 'UID_WeighingForm' not in current_url:
                raise Exception("Failed to load weight page")
            self.page_loaded = True
            self.log(f"✅ Weight page loaded: {current_url}", 'weight')
            loading_dialog.update_status("Selecting lot...")
            # Select the lot using helper method
            if not self._select_lot_in_portal(lot_no):
                raise Exception(f"Failed to select Lot {lot_no} in portal")
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
                            element = self.driver.find_element(By.ID, field_id)  # type: ignore
                            if element.is_displayed() and element.is_enabled():
                                element.clear()
                                element.send_keys(value)
                                filled_count += 1
                                self.weight_entries[field_id].configure(style='Compact.TEntry')
                                self.log(f"✅ Filled {field_id}: {value}", 'weight')
                except Exception as e:
                    self.log(f"❌ Error filling {field_id}: {str(e)}", 'weight')
            loading_dialog.update_status("Saving cornet weights...")
            # Click savecornetvalues button
            try:
                save_btn = self.driver.find_element(By.ID, 'savecornetvalues')  # type: ignore
                if save_btn.is_displayed() and save_btn.is_enabled():
                    save_btn.click()
                    self.log("💾 Clicked Save Cornet Weight button", 'weight')
                    time.sleep(1)
                    # Handle first alert (Are you sure you want to save?)
                    try:
                        alert = self.driver.switch_to.alert  # type: ignore
                        alert_text = alert.text
                        self.log(f"🔔 Alert: {alert_text}", 'weight')
                        alert.accept()
                        time.sleep(1)
                    except Exception as e:
                        self.log(f"❌ Error handling first alert: {str(e)}", 'weight')
                    # Handle second alert (result)
                    try:
                        alert = self.driver.switch_to.alert  # type: ignore
                        alert_text = alert.text
                        self.log(f"🔔 Result Alert: {alert_text}", 'weight')
                        alert.accept()
                        time.sleep(1)
                    except Exception as e:
                        self.log(f"❌ Error handling result alert: {str(e)}", 'weight')
                else:
                    self.log("⚠️ Save Cornet Weight button not interactable", 'weight')
            except Exception as e:
                self.log(f"❌ Error clicking Save Cornet Weight button: {str(e)}", 'weight')
            loading_dialog.update_status("Done!")
            loading_dialog.update_message("Cornet weights saved.")
            time.sleep(1)
            loading_dialog.close()
            # If checkbox is checked, submit for HUID
            if getattr(self, 'include_submit_huid_var', None) and self.include_submit_huid_var.get():
                try:
                    submit_btn = self.driver.find_element(By.ID, 'submitQM')  # type: ignore
                    if submit_btn.is_displayed() and submit_btn.is_enabled():
                        submit_btn.click()
                        self.log("📤 Submitted for HUID (auto)", 'weight')
                        messagebox.showinfo("Submitted", "Form submitted for HUID!")
                    else:
                        self.log("⚠️ Submit For HUID button not interactable", 'weight')
                        messagebox.showwarning("Not Submitted", "Submit For HUID button not interactable")
                except Exception as e:
                    self.log(f"❌ Error submitting for HUID: {str(e)}", 'weight')
                    messagebox.showerror("Error", f"Error submitting for HUID: {str(e)}")
            else:
                self.log("ℹ️ Not submitting for HUID (checkbox not checked)", 'weight')
            self.log_memory_usage("after save cornet weights")
        except Exception as e:
            if loading_dialog:
                loading_dialog.close()
            self.log(f"❌ Error saving cornet weights: {str(e)}", 'weight')
            messagebox.showerror("Error", f"Error saving cornet weights: {str(e)}")
    
    def submit_for_huid(self):
        """Submit form for HUID processing"""
        # Check license before submission
        if not self.check_license_before_action("HUID submission"):
            return
            
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
                self.log("📤 Form submitted for HUID processing", 'weight')
                messagebox.showinfo("Success", "✅ Form submitted for HUID processing!")
            else:
                self.log("⚠️ Submit button not found", 'weight')
                messagebox.showwarning("Warning", "Submit button not found on page")
                
        except Exception as e:
            self.log(f"❌ Error submitting form: {str(e)}", 'weight')
    
    def _OLD_setup_settings_tab(self):
        """DEPRECATED: Old settings tab - replaced with new implementation at line 1407"""
        # Main container frame
        settings_container = ttk.Frame(self.notebook)
        self.notebook.add(settings_container, text="⚙️ Settings")
        
        # Create canvas for scrolling
        canvas = tk.Canvas(settings_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(settings_container, orient="vertical", command=canvas.yview)
        
        # Create scrollable frame inside canvas
        settings_frame = ttk.Frame(canvas)
        
        # Configure canvas scrolling
        settings_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        # Create window inside canvas
        window_id = canvas.create_window((0, 0), window=settings_frame, anchor="nw")
        
        # Proper resizing to fill width
        def on_canvas_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(window_id, width=event.width)
            
        canvas.bind("<Configure>", on_canvas_configure)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # === Row 1: Device Info & License Verification ===
        row1 = ttk.Frame(settings_frame)
        row1.pack(fill='x', padx=20, pady=10)
        
        # --- Device Information Card (Left) ---
        if self.license_manager:
            device_card = ttk.LabelFrame(row1, text="📱 Device Info", style='Compact.TLabelframe')
            device_card.pack(side='left', fill='both', expand=True, padx=(0, 10))
            
            # Grid layout for device info
            device_grid = ttk.Frame(device_card)
            device_grid.pack(fill='x', padx=15, pady=10)
            device_grid.columnconfigure(1, weight=1)
            
            # MAC Address
            ttk.Label(device_grid, text="MAC Address:", font=('Segoe UI', 9, 'bold')).grid(row=0, column=0, sticky='w', pady=5)
            mac_address = (self.license_manager.mac_address if self.license_manager else None) or "Unknown"
            mac_label = tk.Label(device_grid, text=mac_address, font=('Segoe UI', 9), 
                               bg='#f8f9fa', fg='#495057', relief='sunken', padx=8, pady=4, anchor='w')
            mac_label.grid(row=0, column=1, sticky='ew', padx=(10, 0))
            
            # Device ID
            ttk.Label(device_grid, text="Device ID:", font=('Segoe UI', 9, 'bold')).grid(row=1, column=0, sticky='w', pady=5)
            device_id = (self.license_manager.device_id if self.license_manager else None) or "Unknown"
            device_id_label = tk.Label(device_grid, text=device_id, font=('Segoe UI', 9), 
                                     bg='#f8f9fa', fg='#495057', relief='sunken', padx=8, pady=4, anchor='w')
            device_id_label.grid(row=1, column=1, sticky='ew', padx=(10, 0))
            
            # Status
            ttk.Label(device_grid, text="License Status:", font=('Segoe UI', 9, 'bold')).grid(row=2, column=0, sticky='w', pady=5)
            status_frame = ttk.Frame(device_grid)
            status_frame.grid(row=2, column=1, sticky='w', padx=(10, 0))
            
            self.license_status_label = ttk.Label(status_frame, text="⏳ Not Verified", font=('Segoe UI', 9, 'bold'), foreground='#ffc107')
            self.license_status_label.pack(side='left')
            
            self.license_info_label = ttk.Label(status_frame, text="", font=('Segoe UI', 9))
            self.license_info_label.pack(side='left', padx=(10, 0))

        # --- License Verification Card (Right) ---
        if self.license_manager:
            portal_card = ttk.LabelFrame(row1, text="🔐 License Verification", style='Compact.TLabelframe')
            portal_card.pack(side='left', fill='both', expand=True, padx=(10, 0))
            
            portal_grid = ttk.Frame(portal_card)
            portal_grid.pack(fill='x', padx=15, pady=10)
            portal_grid.columnconfigure(1, weight=1)
            
            # Username
            ttk.Label(portal_grid, text="Portal Username:", font=('Segoe UI', 9, 'bold')).grid(row=0, column=0, sticky='w', pady=5)
            self.portal_username_var = tk.StringVar()
            portal_username_entry = ttk.Entry(portal_grid, textvariable=self.portal_username_var, style='Compact.TEntry', font=('Segoe UI', 10))
            portal_username_entry.grid(row=0, column=1, sticky='ew', padx=(10, 0))
            
            # Password
            ttk.Label(portal_grid, text="Portal Password:", font=('Segoe UI', 9, 'bold')).grid(row=1, column=0, sticky='w', pady=5)
            self.portal_password_var = tk.StringVar()
            portal_password_entry = ttk.Entry(portal_grid, textvariable=self.portal_password_var, style='Compact.TEntry', show='*', font=('Segoe UI', 10))
            portal_password_entry.grid(row=1, column=1, sticky='ew', padx=(10, 0))
            
            # Buttons
            btn_frame = ttk.Frame(portal_grid)
            btn_frame.grid(row=2, column=0, columnspan=2, pady=(15, 0), sticky='w')
            
            verify_btn = ttk.Button(btn_frame, text="🔍 Verify License", style='Info.TButton', command=self.verify_license)
            verify_btn.pack(side='left', padx=(0, 10))
            
            clear_btn = ttk.Button(btn_frame, text="🗑️ Clear License", style='Danger.TButton', command=self.clear_license)
            clear_btn.pack(side='left')

        # === Row 2: BIS Portal Configuration & Reception Login ===
        row2 = ttk.Frame(settings_frame)
        row2.pack(fill='x', padx=20, pady=10)

        # --- BIS Portal Configuration Card (Left) ---
        bis_card = ttk.LabelFrame(row2, text="🏢 BIS Portal Configuration", style='Compact.TLabelframe')
        bis_card.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        bis_grid = ttk.Frame(bis_card)
        bis_grid.pack(fill='x', padx=15, pady=10)
        bis_grid.columnconfigure(1, weight=1)
        
        # Username
        ttk.Label(bis_grid, text="BIS Username:", font=('Segoe UI', 9, 'bold')).grid(row=0, column=0, sticky='w', pady=5)
        self.username_var = tk.StringVar(value='qmhmc1')
        bis_username_entry = ttk.Entry(bis_grid, textvariable=self.username_var, style='Compact.TEntry', font=('Segoe UI', 10))
        bis_username_entry.grid(row=0, column=1, sticky='ew', padx=(10, 0))
        
        # Password
        ttk.Label(bis_grid, text="BIS Password:", font=('Segoe UI', 9, 'bold')).grid(row=1, column=0, sticky='w', pady=5)
        self.password_var = tk.StringVar(value='Mahalaxmi14')
        bis_password_entry = ttk.Entry(bis_grid, textvariable=self.password_var, style='Compact.TEntry', show='*', font=('Segoe UI', 10))
        bis_password_entry.grid(row=1, column=1, sticky='ew', padx=(10, 0))
        
        # Firm ID
        ttk.Label(bis_grid, text="Firm ID:", font=('Segoe UI', 9, 'bold')).grid(row=2, column=0, sticky='w', pady=5)
        self.firm_id_var = tk.StringVar(value='2')
        self.firm_id_display_label = tk.Label(bis_grid, text='2', font=('Segoe UI', 9, 'bold'), 
                                             fg='#17a2b8', bg='#f8f9fa', relief='sunken', padx=10, pady=4, anchor='w')
        self.firm_id_display_label.grid(row=2, column=1, sticky='ew', padx=(10, 0))

        # --- Reception Login Card (Right) ---
        recep_card = ttk.LabelFrame(row2, text="👤 Reception Login", style='Compact.TLabelframe')
        recep_card.pack(side='left', fill='both', expand=True, padx=(10, 0))
        
        recep_grid = ttk.Frame(recep_card)
        recep_grid.pack(fill='x', padx=15, pady=10)
        recep_grid.columnconfigure(1, weight=1)
        
        # Username
        ttk.Label(recep_grid, text="Reception Username:", font=('Segoe UI', 9, 'bold')).grid(row=0, column=0, sticky='w', pady=5)
        self.reception_username_var = tk.StringVar(value='mahalaxmird')
        recep_username_entry = ttk.Entry(recep_grid, textvariable=self.reception_username_var, style='Compact.TEntry', font=('Segoe UI', 10))
        recep_username_entry.grid(row=0, column=1, sticky='ew', padx=(10, 0))
        
        # Password
        ttk.Label(recep_grid, text="Reception Password:", font=('Segoe UI', 9, 'bold')).grid(row=1, column=0, sticky='w', pady=5)
        self.reception_password_var = tk.StringVar()
        recep_password_entry = ttk.Entry(recep_grid, textvariable=self.reception_password_var, style='Compact.TEntry', show='*', font=('Segoe UI', 10))
        recep_password_entry.grid(row=1, column=1, sticky='ew', padx=(10, 0))

        # === Row 3: API Configuration (Full Width) ===
        api_card = ttk.LabelFrame(settings_frame, text="🌐 API Configuration", style='Compact.TLabelframe')
        api_card.pack(fill='x', padx=20, pady=10)
        
        # Container for swappable content to handle locking
        self.api_container = ttk.Frame(api_card)
        self.api_container.pack(fill='x', padx=15, pady=10)
        
        # --- Locked View ---
        self.api_locked_frame = ttk.Frame(self.api_container)
        
        lock_msg = ttk.Frame(self.api_locked_frame)
        lock_msg.pack(pady=10)
        ttk.Label(lock_msg, text="🔒 Restricted Area", font=('Segoe UI', 10, 'bold'), foreground='#6c757d').pack(side='left', padx=5)
        ttk.Label(lock_msg, text="- Enter password to configure API endpoints", font=('Segoe UI', 9), foreground='#6c757d').pack(side='left')
        
        lock_grid = ttk.Frame(self.api_locked_frame)
        lock_grid.pack(pady=(0, 10))
        
        ttk.Label(lock_grid, text="Password:").pack(side='left', padx=5)
        self.api_unlock_pass_var = tk.StringVar()
        pass_entry = ttk.Entry(lock_grid, textvariable=self.api_unlock_pass_var, show="●", width=25, style='Compact.TEntry')
        pass_entry.pack(side='left', padx=5)
        
        def unlock_api(event=None):
            if self.api_unlock_pass_var.get() == "Manak2024":
                self.api_locked_frame.pack_forget()
                self.api_unlocked_frame.pack(fill='x')
                self.api_unlock_pass_var.set("") # Clear password
            else:
                messagebox.showerror("Access Denied", "Incorrect Password for API Configuration")

        pass_entry.bind('<Return>', unlock_api)
        ttk.Button(lock_grid, text="🔓 Unlock Settings", command=unlock_api, style='Info.TButton').pack(side='left', padx=5)
        
        self.api_locked_frame.pack(fill='x') # Show locked view by default
        
        # --- Unlocked View (Hidden initially) ---
        self.api_unlocked_frame = ttk.Frame(self.api_container)
        self.api_unlocked_frame.columnconfigure(1, weight=1)
        
        # Base API URL
        ttk.Label(self.api_unlocked_frame, text="Server API URL:", font=('Segoe UI', 9, 'bold')).grid(row=0, column=0, sticky='w', pady=5)
        self.api_base_url_var = tk.StringVar(value="https://hallmarkpro.in/admin/")
        
        base_url_container = ttk.Frame(self.api_unlocked_frame)
        base_url_container.grid(row=0, column=1, sticky='ew', padx=(10, 0))
        base_url_container.columnconfigure(0, weight=1)
        
        api_url_entry = ttk.Entry(base_url_container, textvariable=self.api_base_url_var, style='Compact.TEntry', font=('Segoe UI', 10))
        api_url_entry.grid(row=0, column=0, sticky='ew')
        
        # Re-lock button
        def relock_api():
            self.api_unlocked_frame.pack_forget()
            self.api_locked_frame.pack(fill='x')
            
        ttk.Button(base_url_container, text="🔒 Lock", command=relock_api, style='Small.TButton', width=6).grid(row=0, column=1, padx=(5, 0))

        ttk.Label(self.api_unlocked_frame, text="Base URL for requests (e.g. https://domain.com/admin/)", font=('Segoe UI', 8, 'italic'), foreground='#6c757d').grid(row=1, column=1, sticky='w', padx=(10, 0))

        # Individual Fields Section
        ttk.Label(self.api_unlocked_frame, text="API Endpoints Setup", font=('Segoe UI', 9, 'bold', 'underline'), foreground='#007bff').grid(row=2, column=0, columnspan=4, sticky='w', pady=(20, 10))
        
        # Configure columns for grid layout (2 columns of fields)
        self.api_unlocked_frame.columnconfigure(1, weight=1)
        self.api_unlocked_frame.columnconfigure(3, weight=1)
        
        # Row 3: Jeweller API & Check Jobs API
        ttk.Label(self.api_unlocked_frame, text="Jeweller API:", font=('Segoe UI', 9)).grid(row=3, column=0, sticky='w', pady=5, padx=(0, 5))
        self.jeweller_api_url_var = tk.StringVar(value=config.JEWELLER_API_URL)
        ttk.Entry(self.api_unlocked_frame, textvariable=self.jeweller_api_url_var, style='Compact.TEntry').grid(row=3, column=1, sticky='ew', padx=(0, 20))
        
        ttk.Label(self.api_unlocked_frame, text="Check Jobs API:", font=('Segoe UI', 9)).grid(row=3, column=2, sticky='w', pady=5, padx=(0, 5))
        self.check_jobs_api_url_var = tk.StringVar(value=config.CHECK_JOBS_API_URL)
        ttk.Entry(self.api_unlocked_frame, textvariable=self.check_jobs_api_url_var, style='Compact.TEntry').grid(row=3, column=3, sticky='ew')
        
        # Row 4: Manage Jeweller API & Save Job API
        ttk.Label(self.api_unlocked_frame, text="Manage Jeweller:", font=('Segoe UI', 9)).grid(row=4, column=0, sticky='w', pady=5, padx=(0, 5))
        self.manage_jeweller_api_url_var = tk.StringVar(value=config.MANAGE_JEWELLER_API_URL)
        ttk.Entry(self.api_unlocked_frame, textvariable=self.manage_jeweller_api_url_var, style='Compact.TEntry').grid(row=4, column=1, sticky='ew', padx=(0, 20))
        
        ttk.Label(self.api_unlocked_frame, text="Save Job API:", font=('Segoe UI', 9)).grid(row=4, column=2, sticky='w', pady=5, padx=(0, 5))
        self.save_job_api_url_var = tk.StringVar(value=config.SAVE_JOB_API_URL)
        ttk.Entry(self.api_unlocked_frame, textvariable=self.save_job_api_url_var, style='Compact.TEntry').grid(row=4, column=3, sticky='ew')
        
        # Row 5: Report API & Get Jobs API
        ttk.Label(self.api_unlocked_frame, text="Report API:", font=('Segoe UI', 9)).grid(row=5, column=0, sticky='w', pady=5, padx=(0, 5))
        self.report_api_url_var = tk.StringVar(value=getattr(config, 'REPORT_API_URL', ''))
        ttk.Entry(self.api_unlocked_frame, textvariable=self.report_api_url_var, style='Compact.TEntry').grid(row=5, column=1, sticky='ew', padx=(0, 20))
        
        ttk.Label(self.api_unlocked_frame, text="Get Jobs API:", font=('Segoe UI', 9)).grid(row=5, column=2, sticky='w', pady=5, padx=(0, 5))
        self.get_jobs_api_url_var = tk.StringVar(value=getattr(config, 'GET_JOBS_API_URL', ''))
        ttk.Entry(self.api_unlocked_frame, textvariable=self.get_jobs_api_url_var, style='Compact.TEntry').grid(row=5, column=3, sticky='ew')
        
        # Row 6: Request API
        ttk.Label(self.api_unlocked_frame, text="Request API:", font=('Segoe UI', 9)).grid(row=6, column=0, sticky='w', pady=5, padx=(0, 5))
        self.request_api_url_var = tk.StringVar(value=getattr(config, 'REQUEST_API_URL', ''))
        ttk.Entry(self.api_unlocked_frame, textvariable=self.request_api_url_var, style='Compact.TEntry').grid(row=6, column=1, sticky='ew', padx=(0, 20))
        
        # Row 7: Portal Generate Request URL (New)
        ttk.Label(self.api_unlocked_frame, text="Portal Gen URL:", font=('Segoe UI', 9)).grid(row=7, column=0, sticky='w', pady=5, padx=(0, 5))
        self.portal_generate_url_var = tk.StringVar(value=portal_config.get_default_portal_generate_url())
        ttk.Entry(self.api_unlocked_frame, textvariable=self.portal_generate_url_var, style='Compact.TEntry').grid(row=7, column=1, columnspan=3, sticky='ew')
        ttk.Label(self.api_unlocked_frame, text="(Enter the specific 'Generate Request' page URL for your firm)", font=('Segoe UI', 8, 'italic'), foreground='#6c757d').grid(row=8, column=1, columnspan=3, sticky='w')
        

        

        
        # === MANAK Portal: Live vs Demo ===
        portal_env_card = ttk.LabelFrame(settings_frame, text="MANAK Portal Environment", style='Compact.TLabelframe')
        portal_env_card.pack(fill='x', padx=20, pady=10)

        portal_env_inner = ttk.Frame(portal_env_card)
        portal_env_inner.pack(fill='x', padx=15, pady=10)

        self.portal_env_var = tk.StringVar(value=portal_config.get_portal_env())
        ttk.Radiobutton(
            portal_env_inner,
            text="Live — huid.manakonline.in (production)",
            variable=self.portal_env_var,
            value=portal_config.PORTAL_ENV_LIVE,
            command=self._on_portal_env_change,
        ).pack(anchor='w', pady=2)
        ttk.Radiobutton(
            portal_env_inner,
            text="Demo — newmanak.uat.dcservices.in (testing)",
            variable=self.portal_env_var,
            value=portal_config.PORTAL_ENV_DEMO,
            command=self._on_portal_env_change,
        ).pack(anchor='w', pady=2)

        self.portal_env_status_label = ttk.Label(
            portal_env_inner,
            text="",
            font=('Segoe UI', 8),
            foreground='#6c757d',
        )
        self.portal_env_status_label.pack(anchor='w', pady=(6, 0))
        self._update_portal_env_status_label()

        # === Login URL (portal browser) ===
        login_url_card = ttk.LabelFrame(settings_frame, text="Portal Login URL", style='Compact.TLabelframe')
        login_url_card.pack(fill='x', padx=20, pady=10)

        login_url_grid = ttk.Frame(login_url_card)
        login_url_grid.pack(fill='x', padx=15, pady=10)
        login_url_grid.columnconfigure(1, weight=1)

        ttk.Label(login_url_grid, text="Login Page URL:", font=('Segoe UI', 9, 'bold')).grid(row=0, column=0, sticky='w', pady=5, padx=(0, 10))
        self.login_url_var = tk.StringVar(value=portal_config.get_default_login_url())
        ttk.Entry(login_url_grid, textvariable=self.login_url_var, style='Compact.TEntry').grid(row=0, column=1, sticky='ew')

        # === Save Button ===
        save_btn_frame = ttk.Frame(settings_frame)
        save_btn_frame.pack(fill='x', padx=20, pady=20)
        
        save_btn = ttk.Button(save_btn_frame, text="💾 Save All Settings", style='Success.TButton', command=self.save_settings)
        save_btn.pack(fill='x', ipady=5)
        
        # Add some padding at the bottom
        ttk.Frame(settings_frame, height=20).pack()

    def update_license_status_display(self):
        """Update the license status display in the UI"""
        if not hasattr(self, 'license_status_label') or not hasattr(self, 'license_info_label'):
            return
            
        # Get current license status
        if self.license_manager:
            status = self.license_manager.get_license_status()
            
            if self.license_verified:
                self.license_status_label.configure(text="✅ Verified", foreground='#28a745')
                
                # Update firm_id display from license
                if hasattr(self.license_manager, 'firm_id') and self.license_manager.firm_id:
                    self.firm_id_var.set(self.license_manager.firm_id)
                    if hasattr(self, 'firm_id_display_label'):
                        self.firm_id_display_label.configure(text=self.license_manager.firm_id)
                
                # Update job cards processor firm_id
                if hasattr(self, 'job_cards_processor') and self.job_cards_processor:
                    self.job_cards_processor.refresh_firm_id_from_license()
                
                # Update bulk jobs processor firm_id
                if hasattr(self, 'bulk_jobs_processor') and self.bulk_jobs_processor:
                    self.bulk_jobs_processor.refresh_firm_id_from_license()
                
                # Show expiry or trial info
                if status.get('expires_at'):
                    try:
                        expiry_date = datetime.fromtimestamp(status['expires_at']).strftime('%Y-%m-%d %H:%M')
                        self.license_info_label.configure(
                            text=f"(Valid until: {expiry_date})",
                            foreground='#28a745'
                        )
                    except:
                        self.license_info_label.configure(text="", foreground='#28a745')
                elif status.get('trial_active'):
                    trial_info = status.get('trial_info', {})
                    days_left = trial_info.get('days_left', 'Unknown')
                    self.license_info_label.configure(
                        text=f"(Trial: {days_left} days remaining)",
                        foreground='#ffc107'
                    )
            else:
                self.license_status_label.configure(text="❌ Not Verified", foreground='#dc3545')
                self.license_info_label.configure(text="", foreground='#dc3545')
                
        self.root.update()
        
        # Schedule next update in 5 seconds
        self.root.after(5000, self.update_license_status_display)
        
    def _block_expired_license(self):
        """Block access when license is expired"""
        try:
            # Show expiration warning
            messagebox.showwarning(
                "License Expired", 
                "Your license has expired. Please renew your license to continue using the application.\n\n"
                "All features are now disabled until license is renewed."
            )
            
            # Disable critical features
            self._disable_expired_features()
            
            # Log the blocking
            self.log("🚫 Access blocked - License expired", 'status')
            
        except Exception as e:
            print(f"Error blocking expired license: {e}")
            
    def _disable_expired_features(self):
        """Disable features when license is expired"""
        try:
            # Disable main functionality buttons
            if hasattr(self, 'submit_manak_btn'):
                self.submit_manak_btn.configure(state='disabled')
            if hasattr(self, 'fetch_data_btn'):
                self.fetch_data_btn.configure(state='disabled')
            if hasattr(self, 'open_btn'):
                self.open_btn.configure(state='disabled')
                
            # Show expired status in main UI
            if hasattr(self, 'weight_log'):
                self.weight_log.insert(tk.END, "\n🚫 LICENSE EXPIRED - Features Disabled\n")
                self.weight_log.see(tk.END)
                
        except Exception as e:
            print(f"Error disabling expired features: {e}")
        
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
        try:
            if target == 'status' and hasattr(self, 'status_text') and self.status_text and self.status_text.winfo_exists():
                self.status_text.insert(tk.END, log_message)
                self.status_text.see(tk.END)
            elif target == 'weight' and hasattr(self, 'weight_log') and self.weight_log and self.weight_log.winfo_exists():
                self.weight_log.insert(tk.END, log_message)
                self.weight_log.see(tk.END)
            elif target == 'acknowledge' and hasattr(self, 'acknowledge_log') and self.acknowledge_log and self.acknowledge_log.winfo_exists():
                self.acknowledge_log.insert(tk.END, log_message)
                self.acknowledge_log.see(tk.END)
            elif target == 'generate' and hasattr(self, 'weight_log') and self.weight_log and self.weight_log.winfo_exists():
                self.weight_log.insert(tk.END, log_message)
                self.weight_log.see(tk.END)
            # Only update if root exists
            if hasattr(self, 'root') and self.root and self.root.winfo_exists():
                self.root.update()
        except (tk.TclError, AttributeError, Exception) as e:
            # Fallback to console only if GUI fails
            print(f"GUI logging failed for {target}: {e}")
            print(log_message.strip())

    def get_portal_base_url(self):
        """Current MANAK portal base URL (live or demo) from Settings."""
        if hasattr(self, 'portal_env_var'):
            portal_config.set_portal_env(self.portal_env_var.get())
        return portal_config.get_portal_base_url()

    def build_portal_url(self, path):
        """Build MANAK portal URL using current environment."""
        env = self.portal_env_var.get() if hasattr(self, 'portal_env_var') else None
        return portal_config.build_portal_url(path, env)

    def _on_portal_env_change(self):
        """Switch login / portal URLs when Live or Demo is selected."""
        env = self.portal_env_var.get()
        portal_config.set_portal_env(env)
        if hasattr(self, 'login_url_var'):
            self.login_url_var.set(portal_config.swap_portal_base_in_url(self.login_url_var.get(), env))
        if hasattr(self, 'portal_generate_url_var'):
            self.portal_generate_url_var.set(
                portal_config.swap_portal_base_in_url(self.portal_generate_url_var.get(), env)
            )
        self._update_portal_env_status_label()
        if hasattr(self, 'huid_data_processor') and self.huid_data_processor:
            self.huid_data_processor.articles_url = portal_config.build_portal_url(
                "/MANAK/NewArticlesListForWeighing", env
            )
        label = "Live" if env == portal_config.PORTAL_ENV_LIVE else "Demo"
        self.log(f"MANAK portal environment: {label} ({portal_config.get_portal_base_url()})", 'system')

    def _update_portal_env_status_label(self):
        if not hasattr(self, 'portal_env_status_label'):
            return
        env = self.portal_env_var.get() if hasattr(self, 'portal_env_var') else portal_config.get_portal_env()
        base = portal_config.get_portal_base_url(env)
        name = "Live (production)" if env == portal_config.PORTAL_ENV_LIVE else "Demo (UAT testing)"
        self.portal_env_status_label.configure(text=f"Active: {name} — {base}")

    def _get_configured_login_url(self):
        """Return login URL from settings, with safe fallback."""
        default_url = portal_config.get_default_login_url()
        if hasattr(self, 'login_url_var'):
            configured = (self.login_url_var.get() or "").strip()
            if configured:
                return configured
        return default_url

    def _get_insecure_camera_origin(self):
        """Return origin to allow camera on non-HTTPS MANAK endpoints."""
        try:
            from urllib.parse import urlparse
            candidate = ""
            if hasattr(self, 'login_url_var') and self.login_url_var.get().strip():
                candidate = self.login_url_var.get().strip()
            if not candidate:
                return ""
            parsed = urlparse(candidate)
            if parsed.scheme and parsed.netloc:
                return f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            pass
        return ""
    
    def open_browser(self):
        """Open visible Chrome browser and go directly to login page"""
        try:
            # Ask user which credentials to use
            from tkinter import simpledialog
            
            # Create custom dialog for credential selection
            choice_dialog = tk.Toplevel(self.root)
            choice_dialog.title("Select Login Credentials")
            choice_dialog.geometry("400x200")
            choice_dialog.resizable(False, False)
            choice_dialog.transient(self.root)
            choice_dialog.grab_set()
            
            # Center the dialog
            choice_dialog.update_idletasks()
            x = (choice_dialog.winfo_screenwidth() // 2) - (400 // 2)
            y = (choice_dialog.winfo_screenheight() // 2) - (200 // 2)
            choice_dialog.geometry(f"400x200+{x}+{y}")
            
            selected_cred = tk.StringVar(value="qm")
            
            # Header
            header_label = ttk.Label(choice_dialog, text="Choose BIS Portal Credentials", font=('Segoe UI', 12, 'bold'))
            header_label.pack(pady=15)
            
            # Radio buttons frame
            radio_frame = ttk.Frame(choice_dialog)
            radio_frame.pack(pady=10)
            
            # QM option
            qm_radio = ttk.Radiobutton(
                radio_frame, 
                text="🔵 QM Login (Weight Entry, HUID, etc.)", 
                variable=selected_cred, 
                value="qm",
                style='Compact.TRadiobutton'
            )
            qm_radio.pack(anchor='w', pady=5, padx=20)
            
            # Reception option
            reception_radio = ttk.Radiobutton(
                radio_frame, 
                text="🟢 Reception Login (Accept Request)", 
                variable=selected_cred, 
                value="reception",
                style='Compact.TRadiobutton'
            )
            reception_radio.pack(anchor='w', pady=5, padx=20)
            
            # Buttons
            button_frame = ttk.Frame(choice_dialog)
            button_frame.pack(pady=15)
            
            def on_ok():
                self.selected_credential_type = selected_cred.get()
                choice_dialog.destroy()
            
            def on_cancel():
                self.selected_credential_type = None
                choice_dialog.destroy()
            
            ok_btn = ttk.Button(button_frame, text="✅ Continue", command=on_ok, style='Success.TButton', width=12)
            ok_btn.pack(side='left', padx=5)
            
            cancel_btn = ttk.Button(button_frame, text="❌ Cancel", command=on_cancel, style='Danger.TButton', width=12)
            cancel_btn.pack(side='left', padx=5)
            
            # Wait for dialog to close
            choice_dialog.wait_window()
            
            # Check if user cancelled
            if not hasattr(self, 'selected_credential_type') or self.selected_credential_type is None:
                self.log("ℹ️ Browser opening cancelled by user")
                return
            
            self.log(f"🚀 Starting Chrome browser with {self.selected_credential_type.upper()} credentials...")
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1280,720")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--allow-running-insecure-content")
            chrome_options.add_argument("--use-fake-ui-for-media-stream")
            chrome_options.add_argument("--disable-features=WebSerial")
            chrome_options.add_argument("--disable-blink-features=WebSerial")
            chrome_options.add_argument("--disable-device-discovery-notifications")
            insecure_origin = self._get_insecure_camera_origin()
            if insecure_origin:
                chrome_options.add_argument(f"--unsafely-treat-insecure-origin-as-secure={insecure_origin}")
            chrome_options.add_experimental_option("detach", True)
            
            # Configure download directory
            import os
            self.download_dir = os.path.join(os.getcwd(), 'downloads')
            if not os.path.exists(self.download_dir):
                os.makedirs(self.download_dir)
            
            prefs = {
                "download.default_directory": self.download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "plugins.always_open_pdf_externally": True,  # Force download PDF
                "profile.default_content_setting_values.media_stream_camera": 1,
                "profile.default_content_setting_values.media_stream_mic": 1,
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
            
            # Update multiple jobs processor with driver now that it's available
            if self.multiple_jobs_processor:
                self.multiple_jobs_processor.driver = self.driver # type: ignore # type: ignore
                self.multiple_jobs_processor.main_log_callback = self.log
            
            # Update delivery voucher scanner with driver
            self.log(f"DEBUG: Checking delivery_voucher_scanner: {self.delivery_voucher_scanner is not None}", 'system')
            if self.delivery_voucher_scanner:
                self.log(f"DEBUG: Assigning driver to scanner...", 'system')
                self.delivery_voucher_scanner.driver = self.driver
                self.log(f"✅ Assigned driver to delivery voucher scanner", 'system')
            else:
                self.log(f"⚠️ Delivery voucher scanner is None", 'system')
            
            # Update jeweller request generator with driver (Reception specific)
            try:
                if hasattr(self, 'jeweller_request_generator') and self.jeweller_request_generator:
                    self.jeweller_request_generator.driver = self.reception_driver
                    if self.reception_driver:
                        self.log(f"✅ Assigned reception driver to jeweller request generator", 'system')
            except Exception as e:
                self.log(f"⚠️ Error assigning driver to jeweller request generator: {e}", 'system')
            
            if self.simple_job_creator:
                self.simple_job_creator.driver = self.driver # type: ignore
                self.simple_job_creator.main_log_callback = self.log
            
            # Update completed jobs scanner with driver
            if hasattr(self, 'completed_jobs_scanner') and self.completed_jobs_scanner:
                self.completed_jobs_scanner.driver = self.driver
                self.log(f"✅ Assigned driver to completed jobs scanner", 'system')
            
            # Update bill import processor with driver
            if hasattr(self, 'bill_import_processor') and self.bill_import_processor:
                self.bill_import_processor.driver = self.driver # type: ignore
                self.log(f"✅ Assigned driver to bill import processor", 'system')
            
            if self.delivery_voucher_processor:
                self.delivery_voucher_processor.driver = self.driver # type: ignore
                self.delivery_voucher_processor.main_log_callback = self.log
            
            if hasattr(self, 'weight_capture_processor') and self.weight_capture_processor:
                self.weight_capture_processor.driver = self.driver # type: ignore
                self.weight_capture_processor.main_log_callback = self.log

            # Update HUID data processor with driver now that it's available
            if hasattr(self, 'huid_data_processor') and self.huid_data_processor:
                self.huid_data_processor.driver = self.driver
                self.huid_data_processor.main_log_callback = self.log
            
            self.log("✅ Browser opened successfully!")
            
            # Go directly to configured login page
            login_url = self._get_configured_login_url()
            self.log(f"🔑 Opening login page: {login_url}")
            self.driver.get(login_url)
            self._auto_fill_login_credentials()
            
            # Update button states
            self.open_btn.config(state='disabled')
            self.login_btn.config(state='normal')
            self.check_btn.config(state='normal')
            self.close_btn.config(state='normal')
            
        except Exception as e:
            self.log(f"❌ Error opening browser: {str(e)}")
            messagebox.showerror("Browser Error", f"Failed to open browser: {str(e)}")

    def navigate_to_login(self):
        """Navigate to MANAK portal login page using configured URL"""
        if not self.driver:
            messagebox.showwarning("No Browser", "Please open browser first")
            return
            
        try:
            login_url = self._get_configured_login_url()
            
            self.log(f"🔑 Navigating to login page: {login_url}...")
            self.driver.get(login_url)
            time.sleep(3)
            self._auto_fill_login_credentials()
            
            current_url = self.driver.current_url
            self.log(f"✅ Navigated to: {current_url}")
            self.log("👤 Please complete login manually (including CAPTCHA)")
            
        except Exception as e:
            self.log(f"❌ Error navigating to portal: {str(e)}")

    def _auto_fill_login_credentials(self):
        """Auto-fill username and password on the login page based on user's credential selection"""
        if not self.driver:
            self.log("❌ WebDriver not initialized", 'system')
            return
            
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
            
            # Use the credential type selected by user in the dialog
            try:
                if hasattr(self, 'selected_credential_type') and self.selected_credential_type == 'reception':
                    # Use Reception credentials
                    username = self.reception_username_var.get() if hasattr(self, 'reception_username_var') and self.reception_username_var.get() else self.username_var.get()
                    password = self.reception_password_var.get() if hasattr(self, 'reception_password_var') and self.reception_password_var.get() else self.password_var.get()
                    self.log(f"✅ Using Reception credentials (User Selected)")
                else:
                    # Use QM credentials (default)
                    username = self.username_var.get()
                    password = self.password_var.get()
                    self.log(f"✅ Using QM credentials (User Selected)")
            except Exception as e:
                # Fallback to QM credentials if selection fails
                username = self.username_var.get()
                password = self.password_var.get()
                self.log(f"⚠️ Credential selection failed, using QM credentials: {str(e)}")
            
            user_field.clear()
            user_field.send_keys(username)
            pass_field.clear()
            pass_field.send_keys(password)
            
            self.log("✅ Credentials auto-filled. Please enter CAPTCHA and login.")
            
        except Exception as e:
            self.log(f"ℹ️ Could not auto-fill credentials: {str(e)}")
            
    def check_login(self):
        """Check if user has completed login"""
        if not self.driver:
            messagebox.showwarning("No Browser", "Please open browser first")
            return
            
        try:
            current_url = self.driver.current_url
            page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            
            self.log(f"🔍 Current URL: {current_url}")
            
            # Check for login indicators
            if any(indicator in page_text for indicator in ['login', 'signin', 'captcha', 'username']):
                self.logged_in = False
                self.log("⚠️ Still on login page - please complete login")
                return False
            else:
                self.logged_in = True
                self.log("✅ Login appears successful!")
                if hasattr(self, 'submit_manak_btn'):
                    self.submit_manak_btn.config(state='normal')
                return True
                
        except Exception as e:
            self.log(f"❌ Error checking login: {str(e)}")
            return False
            
    def load_weight_page(self):
        """Load weight entry page for specific request"""
        # Check license before accessing weight entry features
        if not self.check_license_before_action("weight entry"):
            return
            
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
            weight_url = f"{portal_config.portal_base()}/MANAK/UID_WeighingForm?requestNo={encoded_request}"
            if job_no:
                encoded_job = base64.b64encode(str(job_no).encode()).decode()
                weight_url += f"&jobNo={encoded_job}"
                
            self.log(f"📄 Loading weight page: {weight_url}", 'weight')
            
            self.driver.get(weight_url)
            time.sleep(3)
            
            current_url = self.driver.current_url
            self.log(f"✅ Loaded: {current_url}", 'weight')
            
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
                    
            self.log(f"🔍 Found {total_fields}/{len(self.field_ids)} fields", 'weight')
            
            if total_fields > 0:
                self.page_loaded = True
                if hasattr(self, 'auto_fill_btn') and self.auto_fill_btn:
                    self.auto_fill_btn.config(state='normal')
                if hasattr(self, 'select_lot_btn') and self.select_lot_btn:
                    self.select_lot_btn.config(state='normal')
                if hasattr(self, 'auto_workflow_btn') and self.auto_workflow_btn:
                    self.auto_workflow_btn.config(state='normal')
                self.log("✅ Weight page loaded - ready for automation", 'weight')
            else:
                self.log("⚠️ No weight fields detected", 'weight')
                
        except Exception as e:
            self.log(f"❌ Error loading weight page: {str(e)}", 'weight')
            
    def clear_weight_fields(self):
        """Clear all weight entry fields"""
        for entry in self.weight_entries.values():
            entry.delete(0, tk.END)
            entry.configure(style='Compact.TEntry')
        
        # Clear delta calculations
        self.clear_delta_calculations()
        
        self.log("🧹 Cleared all fields", 'weight')
        
    def clear_delta_calculations(self):
        """Clear all delta calculation displays"""
        try:
            if hasattr(self, 'c1_initial_display'):
                self.c1_initial_display.config(text="0.000")
                self.c1_m2_display.config(text="0.000")
                self.c1_delta_display.config(text="0.000")
                self.c2_initial_display.config(text="0.000")
                self.c2_m2_display.config(text="0.000")
                self.c2_delta_display.config(text="0.000")
                self.avg_delta_display.config(text="0.000")
                self.delta_status_label.config(text="⏳ Enter C1 and C2 values to calculate", fg='#6c757d')
                
            # Clear fineness fields
            fineness_fields = [
                'num_fineness_reportM11', 'num_fineness_report_goldM11', 
                'num_mean_finenessM11', 'str_remarksM11', 'str_remarksM12',
                'averagedelta1', 'delta12'
            ]
            
            for field_id in fineness_fields:
                if field_id in self.weight_entries:
                    self.weight_entries[field_id].delete(0, tk.END)
                    self.weight_entries[field_id].configure(style='Compact.TEntry')
                    
        except Exception as e:
            self.log(f"⚠️ Error clearing delta calculations: {str(e)}", 'weight')
        
    def load_settings(self):
        """Load saved settings from config file"""
        try:
            settings_path = 'config/app_settings.json'
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                
                # Load settings into variables (only if they exist)
                if hasattr(self, 'username_var') and 'username' in settings:
                    self.username_var.set(settings['username'])
                if hasattr(self, 'password_var') and 'password' in settings:
                    self.password_var.set(settings['password'])
                if hasattr(self, 'firm_id_var') and 'firm_id' in settings:
                    self.firm_id_var.set(settings['firm_id'])
                if hasattr(self, 'api_url_var') and 'api_url' in settings:
                    self.api_url_var.set(settings['api_url'])
                if hasattr(self, 'request_api_url_var') and 'request_api_url' in settings:
                    self.request_api_url_var.set(settings['request_api_url'])
                if hasattr(self, 'orders_api_url_var') and 'orders_api_url' in settings:
                    self.orders_api_url_var.set(settings['orders_api_url'])
                if hasattr(self, 'report_api_url_var') and 'report_api_url' in settings:
                    self.report_api_url_var.set(settings['report_api_url'])
                if hasattr(self, 'api_key_var') and 'api_key' in settings:
                    self.api_key_var.set(settings['api_key'])
                
                # Load portal credentials
                if hasattr(self, 'portal_username_var') and 'portal_username' in settings:
                    self.portal_username_var.set(settings['portal_username'])
                if hasattr(self, 'portal_password_var') and 'portal_password' in settings:
                    self.portal_password_var.set(settings['portal_password'])
                    
                # Load reception credentials
                if hasattr(self, 'reception_username_var') and 'reception_username' in settings:
                    self.reception_username_var.set(settings['reception_username'])
                if hasattr(self, 'reception_password_var') and 'reception_password' in settings:
                    self.reception_password_var.set(settings['reception_password'])

                # Load MANAK portal environment (live / demo) and portal URLs
                env = settings.get('portal_env', portal_config.DEFAULT_PORTAL_ENV)
                portal_config.set_portal_env(env)
                if hasattr(self, 'portal_env_var'):
                    self.portal_env_var.set(env)
                if hasattr(self, 'portal_generate_url_var'):
                    if 'portal_generate_url' in settings:
                        self.portal_generate_url_var.set(
                            portal_config.swap_portal_base_in_url(settings['portal_generate_url'], env)
                        )
                    else:
                        self.portal_generate_url_var.set(portal_config.get_default_portal_generate_url(env))
                if hasattr(self, 'login_url_var'):
                    if 'login_url' in settings:
                        self.login_url_var.set(
                            portal_config.swap_portal_base_in_url(settings['login_url'], env)
                        )
                    else:
                        self.login_url_var.set(portal_config.get_default_login_url(env))
                if hasattr(self, 'portal_env_status_label'):
                    self._update_portal_env_status_label()

                # Load API Configuration
                if hasattr(self, 'api_base_url_var') and 'api_base_url' in settings:
                    base_url = settings['api_base_url'].strip()
                    self.api_base_url_var.set(base_url)
                    
                    # Update config if base URL is provided
                    if base_url:
                        if not base_url.endswith('/'):
                            base_url += '/'
                        
                        # Update global config constants
                        try:
                            config.JEWELLER_API_URL = base_url + "get_jewellers_api.php"
                            config.CHECK_JOBS_API_URL = base_url + "check_jobs_api.php"
                            config.MANAGE_JEWELLER_API_URL = base_url + "manage_jeweller_api.php"
                            config.SAVE_JOB_API_URL = base_url + "save_job_api.php"
                            config.REPORT_API_URL = base_url + "get_report_by_id.php"
                            config.GET_JOBS_API_URL = base_url + "get_jobs_api.php"
                            config.REQUEST_API_URL = base_url + "API/get_request_no.php"
                            
                            # Only log in debug mode to avoid exposing infrastructure
                            if config.APP_CONFIG.get('debug_mode'):
                                self.log(f"🔧 API configuration updated", 'status')
                        except Exception as e:
                            self.log(f"⚠️ Error updating config constants: {str(e)}", 'status')
                    
                # Load individual API overrides (if present, they override base URL defaults)
                if hasattr(self, 'jeweller_api_url_var') and 'jeweller_api_url' in settings:
                    url = settings['jeweller_api_url']
                    self.jeweller_api_url_var.set(url)
                    config.JEWELLER_API_URL = url
                    
                if hasattr(self, 'check_jobs_api_url_var') and 'check_jobs_api_url' in settings:
                    url = settings['check_jobs_api_url']
                    self.check_jobs_api_url_var.set(url)
                    config.CHECK_JOBS_API_URL = url
                    
                if hasattr(self, 'manage_jeweller_api_url_var') and 'manage_jeweller_api_url' in settings:
                    url = settings['manage_jeweller_api_url']
                    self.manage_jeweller_api_url_var.set(url)
                    config.MANAGE_JEWELLER_API_URL = url
                    
                if hasattr(self, 'save_job_api_url_var') and 'save_job_api_url' in settings:
                    url = settings['save_job_api_url']
                    self.save_job_api_url_var.set(url)
                    config.SAVE_JOB_API_URL = url
                    
                if hasattr(self, 'get_jobs_api_url_var') and 'get_jobs_api_url' in settings:
                    url = settings['get_jobs_api_url']
                    self.get_jobs_api_url_var.set(url)
                    config.GET_JOBS_API_URL = url

                self.log("✅ Settings loaded from config file", 'status')
            else:
                self.log("ℹ️ No saved settings found, using defaults", 'status')
                
        except Exception as e:
            self.log(f"⚠️ Error loading settings: {str(e)}", 'status')
    
    def clear_fields_on_start(self):
        """Clear request and job fields when app starts"""
        try:
            self.request_entry.delete(0, tk.END)
            self.job_entry.delete(0, tk.END)
            self.log("🧹 Cleared request fields on startup", 'weight')
        except Exception as e:
            self.log(f"⚠️ Error clearing fields on start: {str(e)}", 'weight')
    
    def verify_license(self):
        """Verify device license with portal credentials - enhanced version"""
        if not self.license_manager:
            messagebox.showwarning("License Manager", "Device licensing is not enabled.")
            return
        
        # Get portal credentials from settings
        username = self.portal_username_var.get().strip()
        password = self.portal_password_var.get().strip()
        
        if not username or not password:
            messagebox.showwarning("Missing Information", "Please enter both Portal Username and Password.")
            return
        
        try:
            # Verify with portal credentials and get status
            if self.license_manager.verify_device_license(username, password):
                self.license_verified = True  # Update verification status
                status = self.license_manager.get_license_status()
                
                # Update status label with verification state
                self.license_status_label.configure(text="✅ Verified", foreground='#28a745')
                
                # Get and format expiry/trial info
                if status.get('trial_active'):
                    trial_info = status.get('trial_info', {})
                    days_left = trial_info.get('days_left', 'Unknown')
                    self.license_info_label.configure(
                        text=f"(Trial: {days_left} days remaining)",
                        foreground='#ffc107'
                    )
                else:
                    next_check = status.get('next_check', 0)
                    if next_check:
                        expiry_date = datetime.fromtimestamp(next_check).strftime('%Y-%m-%d %H:%M')
                        self.license_info_label.configure(
                            text=f"(Valid until: {expiry_date})",
                            foreground='#28a745'
                        )
                
                messagebox.showinfo("License Verified", "✅ Device license verified successfully!")
                self.log("✅ License verified successfully", 'status')
                
                # Save portal credentials if verification successful
                self.save_settings()  # Auto-save settings after successful verification
                
                # Start periodic verification if not already running
                if not self.license_manager.verification_thread or not self.license_manager.verification_thread.is_alive():
                    self.license_manager.start_periodic_verification(self)
                    self.log("🔄 Periodic license verification started", 'status')
                    
                # Update all UI elements that depend on license status
                self.root.update()
            else:
                self.license_verified = False  # Update verification status
                self.license_status_label.config(text="❌ Not Authorized", foreground='#dc3545')
                messagebox.showerror("License Error", "❌ Device license verification failed!")
                self.log("❌ License verification failed", 'status')
        except Exception as e:
            self.license_verified = False  # Update verification status
            self.license_status_label.config(text="⚠️ Error", foreground='#ffc107')
            messagebox.showerror("Error", f"Error verifying license: {str(e)}")
            self.log(f"❌ Error verifying license: {str(e)}", 'status')
    
    def save_settings(self):
        try:
            settings = self.get_settings()
            os.makedirs('config', exist_ok=True)
            with open('config/app_settings.json', 'w') as f:
                json.dump(settings, f, indent=2)
            
            # Update job cards processor with new firm ID
            if hasattr(self, 'job_cards_processor') and self.job_cards_processor:
                self.job_cards_processor.update_firm_id_from_settings()

            # Update API configuration immediately
            # Priority 1: Individual overrides if present and modified? 
            # Simplified: Use Base URL to drive defaults, but if we want to support overrides, we need to save them.
            # For now, let's stick to Base URL driving everything to avoid confusion, 
            # unless we want to support mixed mode. 
            # The prompt says "dynamic API settings" -> usually implies base URL switching.
            # But since I added the advanced fields, I should probably respect them if visible?
            # Let's just update based on the Base URL for consistency as requested by the user's "dynamic link" goal.
            # The individual fields are currently just displaying what the Base URL would generate, 
            # unless I bind them to update automatically when Base URL changes.
            # Actually, let's just use the Base URL logic for now to ensure robustness.
            if 'api_base_url' in settings:
                base_url = settings['api_base_url'].strip()
                if base_url:
                    if not base_url.endswith('/'):
                        base_url += '/'
                    
                    # Update config constants
                    config.JEWELLER_API_URL = base_url + "get_jewellers_api.php"
                    config.CHECK_JOBS_API_URL = base_url + "check_jobs_api.php"
                    config.MANAGE_JEWELLER_API_URL = base_url + "manage_jeweller_api.php"
                    config.SAVE_JOB_API_URL = base_url + "save_job_api.php"
                    config.REPORT_API_URL = base_url + "get_report_by_id.php"
                    config.GET_JOBS_API_URL = base_url + "get_jobs_api.php"
                    config.REQUEST_API_URL = base_url + "API/get_request_no.php"
                    
                    # Only log in debug mode to avoid exposing infrastructure
                    if config.APP_CONFIG.get('debug_mode'):
                        self.log(f"🔧 API configuration synchronized", 'status')
                    
                    # Update the advanced fields variables to reflect the change
                    if hasattr(self, 'jeweller_api_url_var'):
                        self.jeweller_api_url_var.set(config.JEWELLER_API_URL)
                    if hasattr(self, 'check_jobs_api_url_var'):
                        self.check_jobs_api_url_var.set(config.CHECK_JOBS_API_URL)
                    if hasattr(self, 'manage_jeweller_api_url_var'):
                        self.manage_jeweller_api_url_var.set(config.MANAGE_JEWELLER_API_URL)
                    if hasattr(self, 'save_job_api_url_var'):
                        self.save_job_api_url_var.set(config.SAVE_JOB_API_URL)
                    if hasattr(self, 'report_api_url_var'):
                        self.report_api_url_var.set(config.REPORT_API_URL)
                    if hasattr(self, 'get_jobs_api_url_var'):
                        self.get_jobs_api_url_var.set(config.GET_JOBS_API_URL)
                    if hasattr(self, 'request_api_url_var'):
                        self.request_api_url_var.set(config.REQUEST_API_URL)

            messagebox.showinfo("Settings Saved", "✅ Settings saved successfully!")
            self.log("💾 Settings saved to config/app_settings.json", 'status')
        except Exception as e:
            try:
                messagebox.showerror("Error", f"Failed to save settings: {str(e)}")
                self.log(f"❌ Error saving settings: {str(e)}", 'status')
            except Exception:
                print(f"Error saving settings: {str(e)}")
    

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
            if hasattr(self, 'submit_manak_btn'):
                self.submit_manak_btn.config(state='disabled')
            
            self.log("✅ Browser closed")
            
        except Exception as e:
            self.log(f"❌ Error closing browser: {str(e)}")

    def open_reception_browser(self):
        """Open a separate browser instance for Reception tasks"""
        try:
            self.log("🚀 Launching Reception Chrome...", 'status')
            
            # Setup Chrome options
            chrome_options = Options()
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--allow-running-insecure-content")
            chrome_options.add_argument("--use-fake-ui-for-media-stream")
            insecure_origin = self._get_insecure_camera_origin()
            if insecure_origin:
                chrome_options.add_argument(f"--unsafely-treat-insecure-origin-as-secure={insecure_origin}")

            # Create driver with fallback logic matching open_browser
            try:
                from selenium.webdriver.chrome.service import Service
                # Try specific path (legacy/nix support)
                chromedriver_path = "/nix/store/x423854737d94f27621183556-chromedriver-115.0.5790.170/bin/chromedriver"
                if os.path.exists(chromedriver_path):
                    service = Service(chromedriver_path)
                    self.reception_driver = webdriver.Chrome(service=service, options=chrome_options)
                else:
                    raise Exception("Specific driver path not found")
            except:
                # Fallback to default (let Selenium Manager handle it or use PATH)
                self.reception_driver = webdriver.Chrome(options=chrome_options)
            
            self.log("✅ Reception Browser Launched successfully", 'status')
            
            # Navigate to configured login page
            reception_login_url = self._get_configured_login_url()
            self.log(f"🔑 Opening reception login page: {reception_login_url}", 'status')
            self.reception_driver.get(reception_login_url)
            
            # Auto-fill credentials
            self.root.after(2000, self._auto_fill_reception_login_credentials)
            
            # Update button states
            if hasattr(self, 'open_reception_btn_main'):
                self.open_reception_btn_main.config(state='disabled')
                self.close_reception_btn_main.config(state='normal')
            
            # Update jeweller request generator to use reception browser
            try:
                if hasattr(self, 'jeweller_request_generator') and self.jeweller_request_generator:
                    self.jeweller_request_generator.driver = self.reception_driver
                    self.log(f"✅ Assigned reception driver to jeweller request generator", 'system')
            except Exception as e:
                self.log(f"⚠️ Error assigning reception driver to jeweller request generator: {e}", 'system')

            
        except Exception as e:
            self.log(f"❌ Error opening reception browser: {str(e)}", 'status')
            messagebox.showerror("Browser Error", f"Failed to open reception browser: {str(e)}")

    def close_reception_browser(self):
        """Close Reception browser"""
        try:
            if self.reception_driver:
                self.reception_driver.quit()
                self.reception_driver = None
                
            # Reset button states
            if hasattr(self, 'open_reception_btn_main'):
                self.open_reception_btn_main.config(state='normal')
                self.close_reception_btn_main.config(state='disabled')
            
            self.log("✅ Reception Browser closed", 'status')
            
        except Exception as e:
            self.log(f"❌ Error closing reception browser: {str(e)}", 'status')

    def _auto_fill_reception_login_credentials(self):
        """Auto-fill login credentials for Reception browser"""
        try:
            if not self.reception_driver:
                return

            # Wait for URL content to ensure page loaded
            try:
                WebDriverWait(self.reception_driver, 10).until(lambda d: '/eBISLogin' in d.current_url or '/login' in d.current_url)
            except:
                self.log("⚠️ Timeout waiting for login page load", 'status')
            
            # Get credentials (prioritize reception specific, fallback to main)
            username = ""
            password = ""
            
            if hasattr(self, 'reception_username_var') and self.reception_username_var.get():
                username = self.reception_username_var.get()
            elif hasattr(self, 'portal_username_var'):
                username = self.portal_username_var.get()
                
            if hasattr(self, 'reception_password_var') and self.reception_password_var.get():
                password = self.reception_password_var.get()
            elif hasattr(self, 'portal_password_var'):
                password = self.portal_password_var.get()
                
            if username and password:
                user_field = None
                pass_field = None
                
                # Robust User Field Search
                user_selectors = [
                    (By.ID, "userId"),
                    (By.NAME, "userId"),
                    (By.ID, "InputEmail"), # Common on eBISLogin
                    (By.NAME, "username"),
                    (By.ID, "username"),
                    (By.NAME, "loginId")
                ]
                
                for by, value in user_selectors:
                    try:
                        element = self.reception_driver.find_element(by, value)
                        if element.is_displayed():
                            user_field = element
                            break
                    except:
                        continue
                        
                # Robust Password Field Search
                pass_selectors = [
                    (By.ID, "password"),
                    (By.NAME, "password"),
                    (By.ID, "InputPassword"), # Common on eBISLogin
                    (By.NAME, "passwd")
                ]
                
                for by, value in pass_selectors:
                    try:
                        element = self.reception_driver.find_element(by, value)
                        if element.is_displayed():
                            pass_field = element
                            break
                    except:
                        continue
                
                if user_field and pass_field:
                    try:
                        user_field.clear()
                        user_field.send_keys(username)
                        pass_field.clear()
                        pass_field.send_keys(password)
                        
                        self.log("✅ Reception Credentials auto-filled", 'status')
                        
                    except Exception as e:
                        self.log(f"⚠️ Could not fill fields: {e}", 'status')
                else:
                    self.log(f"⚠️ Could not find login fields. Url: {self.reception_driver.current_url}", 'status')
            
        except Exception as e:
            self.log(f"⚠️ Error auto-filling reception login: {str(e)}", 'status')

    def smart_fetch_data(self):
        """Fetch data from API only"""
        if not self.check_license_before_action("data fetching"):
            return
        job_no = self.job_entry.get().strip()
        if not job_no:
            self._show_validation_error(self.job_entry, "Job Number is required!")
            return
        self._clear_validation_error(self.job_entry)
        
        # Fetch from API only
        self.fetch_data_btn.configure(text="🔎 Fetch from API", style='Info.TButton')
        self.log(f"🔎 Fetching data for Job: {job_no}", 'weight')
        threading.Thread(target=self._fetch_api_data_worker, args=(job_no,), daemon=True).start()
    
    
    
    def on_job_number_change(self, event=None):
        """Update button text when job number changes"""
        job_no = self.job_entry.get().strip()
        if job_no:
                self.fetch_data_btn.configure(text="🔎 Fetch from API", style='Info.TButton')
        else:
            self.fetch_data_btn.configure(text="🔎 Fetch Data", style='Info.TButton')
    
    def fetch_api_data(self):
        """Fetch job and strip data from the server and auto-fill first lot"""
        if not self.check_license_before_action("API data fetching"):
            return
            
        # Safety check for job_entry
        if not hasattr(self, 'job_entry') or not self.job_entry:
            self.log("❌ Job Entry field not found (Single Jobs tab inactive)", 'error')
            return
            
        job_no = self.job_entry.get().strip()
        if not job_no:
            self._show_validation_error(self.job_entry, "Job Number is required!")
            return
        self._clear_validation_error(self.job_entry)
        self.log(f"🔎 Fetching data for Job: {job_no}", 'weight')
        threading.Thread(target=self._fetch_api_data_worker, args=(job_no,), daemon=True).start()

    def _fetch_api_data_worker(self, job_no):
        """Worker thread for API data fetching and auto-fill"""
        try:
            api_url = self.api_url_var.get()
            if not api_url.endswith('='):
                if '?' in api_url:
                    api_url += '&job_no='
                else:
                    api_url += '?job_no='
            full_url = f"{api_url}{job_no}"
            api_key = getattr(self, 'api_key_var', tk.StringVar()).get().strip()
            if api_key:
                separator = '&' if '?' in full_url else '?'
                full_url += f"{separator}api_key={api_key}"
            # Log without exposing sensitive data (hide domain, job number and API key)
            domain = api_url.split('//')[1].split('/')[0] if '//' in api_url else api_url.split('/')[0]
            masked_domain = '*****' + domain[-8:] if len(domain) > 8 else domain
            self.log(f"🌐 API Request: {masked_domain}/... (Job: ***{job_no[-4:]})", 'weight')
            response = requests.get(full_url, timeout=15, allow_redirects=True)
            self.log(f"📡 Response Status: {response.status_code}", 'weight')
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Debug: Log the actual data received from API
                    self.log(f"[DEBUG] API raw data: {data}", 'weight')
                    if data.get('success') and data.get('data'):
                        self.log("✅ Data fetched successfully!", 'weight')
                        # Update button to show API data was found
                        self.root.after(0, lambda: self.fetch_data_btn.configure(text="✅ API Data Loaded", style='Success.TButton'))
                        self.root.after(0, self._display_strip_table_and_autofill, data['data'])
                    else:
                        self.log("⚠️ No data found for this job number.", 'weight')
                        self.root.after(0, lambda: self.fetch_data_btn.configure(text="❌ No Data Found", style='Danger.TButton'))
                        self.root.after(0, lambda: messagebox.showwarning("No Data", "No data found for this job number in API."))
                except ValueError:
                    self.log("❌ Invalid JSON response from API", 'weight')
                    messagebox.showerror("API Error", "Invalid response format from API")
            else:
                self.log(f"❌ API Error: Status {response.status_code}", 'weight')
                messagebox.showerror("API Error", f"Server returned status code {response.status_code}")
        except requests.exceptions.Timeout:
            self.log("⏱️ Request timeout - API took too long to respond", 'weight')
            messagebox.showerror("Timeout", "Request timeout - API took too long to respond")
        except requests.exceptions.ConnectionError:
            self.log("🌐 Connection error - Check internet connection", 'weight')
            messagebox.showerror("Connection Error", "Could not connect to API - Check internet connection")
        except Exception as e:
            self.log(f"❌ Unexpected error: {str(e)}", 'weight')
            messagebox.showerror("API Error", f"Unexpected error: {str(e)}")

    def _display_strip_table_and_autofill(self, strips):
        """Display fetched strip data and auto-fill first lot"""
        # Extract lot weights from strip data first
        self._extract_lot_weights_from_strips(strips)
        self._display_strip_table(strips)
        # Auto-fill first lot if available
        if hasattr(self, 'lots_data') and self.lots_data:
            first_lot = sorted(self.lots_data.keys(), key=lambda x: int(x))[0]
            self._auto_fill_all_fields_for_lot(first_lot)

    def _extract_lot_weights_from_strips(self, strips):
        """Extract lot weights from strip data"""
        try:
            self.log("🔄 Extracting lot weights from strip data...", 'weight')
            self.lot_weights_data = {}
            processed_lots = set()  # Track which lots we've processed to avoid duplicates
            
            for strip in strips:
                lot_no = strip.get('lot_no', '1')
                
                # Only process each lot once (use first strip for each lot)
                if lot_no not in processed_lots:
                    processed_lots.add(lot_no)
                    self.log(f"🔍 Processing lot {lot_no} - has lot_button_weight: {'lot_button_weight' in strip}, has lot_scrap_weight: {'lot_scrap_weight' in strip}", 'weight')
                    
                    if 'lot_button_weight' in strip and 'lot_scrap_weight' in strip:
                        self.lot_weights_data[lot_no] = {
                            'button_weight': float(strip.get('lot_button_weight', 0)),
                            'scrap_weight': float(strip.get('lot_scrap_weight', 0)),
                            'milligram_addition': float(strip.get('milligram_addition', 0))
                        }
                        self.log(f"✅ Extracted lot weights for Lot {lot_no}: Button={self.lot_weights_data[lot_no]['button_weight']}, Scrap={self.lot_weights_data[lot_no]['scrap_weight']}", 'weight')
                    else:
                        self.log(f"⚠️ Lot {lot_no} strip missing lot weight data", 'weight')
            
            self.log(f"📊 Extracted lot weights for {len(self.lot_weights_data)} lots", 'weight')
            
        except Exception as e:
            self.log(f"❌ Error extracting lot weights from strips: {e}", 'weight')

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
            strip1_weight = None
            strip2_weight = None
            for strip in strips:
                strip_no = str(strip.get('strip_no', ''))
                self.log(f"🔍 Processing Strip {strip_no} - Available keys: {list(strip.keys())}", 'weight')
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
                    # Capture Strip1 weight for Button Weight calculation
                    if 'initial' in strip and strip['initial'] not in [None, '', '0', '0.0']:
                        try:
                            strip1_weight = float(strip['initial'])
                        except Exception:
                            strip1_weight = None
                    for field_id, api_key in mapping.items():
                        if field_id in self.weight_entries:
                            if api_key in strip:
                                value = str(strip[api_key])
                                if value and value != '0' and value != '0.0':
                                    self.weight_entries[field_id].insert(0, value)
                                    self.weight_entries[field_id].configure(style='Success.TEntry')
                                    filled_count += 1
                                    self.log(f"✅ Strip {strip_no} - {field_id}: {value}", 'weight')
                                else:
                                    self.log(f"⚠️ Strip {strip_no} - {field_id}: API returned zero/empty value", 'weight')
                            else:
                                missing_keys.append(f"Strip {strip_no} - {api_key}")
                                self.log(f"❌ Strip {strip_no} - Missing API key: {api_key}", 'weight')
                elif strip_no == '2':
                    mapping = {
                        'num_strip_weight_M12': 'initial',
                        'num_silver_weightM12': 'ag',
                        'num_copper_weightM12': 'cu',
                        'num_lead_weightM12': 'pb',
                        'num_cornet_weightM12': 'cornet',
                        'num_fineness_report_goldM11': 'fineness',
                    }
                    # Capture Strip2 weight for Button Weight calculation
                    if 'initial' in strip and strip['initial'] not in [None, '', '0', '0.0']:
                        try:
                            strip2_weight = float(strip['initial'])
                        except Exception:
                            strip2_weight = None
                    for field_id, api_key in mapping.items():
                        if field_id in self.weight_entries and api_key in strip:
                            value = str(strip[api_key])
                            if value and value != '0' and value != '0.0':
                                self.weight_entries[field_id].delete(0, tk.END)
                                self.weight_entries[field_id].insert(0, value)
                                filled_count += 1
                                self.log(f"✅ Strip {strip_no} - {field_id}: {value}", 'weight')
                                self.weight_entries[field_id].configure(style='Success.TEntry')
                            else:
                                self.log(f"⚠️ Strip {strip_no} - {field_id}: API returned zero/empty value", 'weight')
                            missing_keys.append(f"Strip {strip_no} - {api_key}")
                            self.log(f"❌ Strip {strip_no} - Missing API key: {api_key}", 'weight')
            # Calculate and set Button Weight and Scrap Weight
            if strip1_weight is not None and strip2_weight is not None:
                button_weight = (strip1_weight + strip2_weight)
                scrap_weight = button_weight + 0.001
                # Set Button Weight
                if 'buttonweight' in self.weight_entries:
                    self.weight_entries['buttonweight'].delete(0, tk.END)
                    self.weight_entries['buttonweight'].insert(0, str(button_weight))
                    self.weight_entries['buttonweight'].configure(style='Success.TEntry')
                # Set Scrap Weight
                if 'num_scrap_weight' in self.weight_entries:
                    self.weight_entries['num_scrap_weight'].delete(0, tk.END)
                    self.weight_entries['num_scrap_weight'].insert(0, str(scrap_weight))
                    self.weight_entries['num_scrap_weight'].configure(style='Success.TEntry')
            
            # Fill Check Gold data from first strip (Check Gold data is in every strip record)
            if strips:
                first_strip = strips[0]
                self.log(f"🔍 Extracting Check Gold data from first strip - Available Check Gold keys: {[k for k in first_strip.keys() if 'check_gold' in k]}", 'weight')
                
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
                            self.log(f"✅ Check Gold - {field_id}: {value}", 'weight')
                        else:
                            self.log(f"⚠️ Check Gold - {field_id}: API returned zero/empty value", 'weight')
                    else:
                        if field_id in self.weight_entries:
                            missing_keys.append(f"Check Gold - {api_key}")
                            self.log(f"❌ Check Gold - Missing API key: {api_key}", 'weight')
            
            # Use API lot weights if available, otherwise generate random weights
            self.log(f"🔍 Checking lot weights for lot {lot_no}...", 'weight')
            self.log(f"🔍 Available lot_weights_data: {getattr(self, 'lot_weights_data', 'Not found')}", 'weight')
            
            if hasattr(self, 'lot_weights_data') and lot_no in self.lot_weights_data:
                # Use API weights - clear existing values first
                scrap_weight = self.lot_weights_data[lot_no]['scrap_weight']
                self.weight_entries['num_scrap_weight'].delete(0, tk.END)
                self.weight_entries['num_scrap_weight'].insert(0, str(scrap_weight))
                self.weight_entries['num_scrap_weight'].configure(style='Success.TEntry')
                filled_count += 1
                self.log(f"✅ API scrap weight: {scrap_weight}", 'weight')
                
                button_weight = self.lot_weights_data[lot_no]['button_weight']
                self.weight_entries['buttonweight'].delete(0, tk.END)
                self.weight_entries['buttonweight'].insert(0, str(button_weight))
                self.weight_entries['buttonweight'].configure(style='Success.TEntry')
                filled_count += 1
                self.log(f"✅ API button weight: {button_weight}", 'weight')
            else:
                # Fallback: only generate if fields are empty
                if not self.weight_entries['num_scrap_weight'].get().strip():
                    scrap_weight = round(random.uniform(390, 420), 3)
                    self.weight_entries['num_scrap_weight'].insert(0, str(scrap_weight))
                    self.weight_entries['num_scrap_weight'].configure(style='Warning.TEntry')
                    filled_count += 1
                    self.log(f"🔄 Generated scrap weight: {scrap_weight}", 'weight')
                
            if not self.weight_entries['buttonweight'].get().strip():
                button_weight = round(random.uniform(380, 410), 3)
                self.weight_entries['buttonweight'].insert(0, str(button_weight))
                self.weight_entries['buttonweight'].configure(style='Warning.TEntry')
                filled_count += 1
                self.log(f"🔄 Generated button weight: {button_weight}", 'weight')
            
            # Reset styling after delay
            self.root.after(3000, self._reset_entry_styles)
            
            # Update delta calculations after auto-filling
            self.calculate_deltas()
            
            # Update fineness calculations after auto-filling
            self.calculate_all_fineness()
            
            # Summary with missing keys info
            if missing_keys:
                self.log(f"⚠️ Missing API keys: {', '.join(missing_keys)}", 'weight')
            
            self.log(f"✅ Auto-filled {filled_count} fields for Lot {lot_no}", 'weight')
            messagebox.showinfo("Success", f"✅ Auto-filled {filled_count} fields for Lot {lot_no}")
            
        except Exception as e:
            self.log(f"❌ Error auto-filling lot {lot_no}: {str(e)}", 'weight')
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
                self.log("⚠️ Application interrupted by user", 'status')
                self.on_closing()
            else:
                # Log unexpected errors but don't crash
                self.log(f"❌ Unexpected error: {exc_type.__name__}: {exc_value}", 'status')
                return False  # Don't suppress the exception, just log it
        
        import sys
        sys.excepthook = handle_exception
        
        self.root.mainloop()
        
    def on_closing(self):
        """Handle application closing - enhanced version"""
        try:
            # Stop periodic license verification
            if hasattr(self, 'license_manager') and self.license_manager:
                self.license_manager.stop_periodic_verification()
                self.log("🛑 Stopped periodic license verification", 'status')
            
            # Close browser
            if hasattr(self, 'driver') and self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                    
            self.root.destroy()
        except Exception as e:
            print(f"Error during shutdown: {e}")

    def get_request_no_from_api(self, job_no):
        """Get Request No from API using Job No"""
        try:
            if not hasattr(self, 'request_api_url_var'):
                self.log("⚠️ Request No API URL not configured", 'weight')
                return None
                
            api_url = self.request_api_url_var.get().strip()
            if not api_url:
                self.log("⚠️ Request No API URL is empty", 'weight')
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
            self.log(f"🌐 Request No API: {masked_domain}/... (Job: ***{job_no[-4:]})", 'weight')
            
            # Make API request with timeout
            response = requests.get(full_url, timeout=3)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get('success') and data.get('request_no'):
                        request_no = data['request_no']
                        self.log(f"✅ Found Request No: {request_no}", 'weight')
                        return request_no
                    elif data.get('success') and data.get('data') and data['data'].get('request_no'):
                        request_no = data['data']['request_no']
                        self.log(f"✅ Found Request No: {request_no}", 'weight')
                        return request_no
                    else:
                        self.log(f"⚠️ No Request No found for Job No: {job_no}", 'weight')
                        return None
                except ValueError:
                    # Try to parse as plain text
                    text_response = response.text.strip()
                    if text_response and text_response.isdigit():
                        self.log(f"✅ Found Request No: {text_response}", 'weight')
                        return text_response
                    else:
                        self.log(f"⚠️ Invalid API response format", 'weight')
                        return None
            else:
                self.log(f"❌ API Error: Status {response.status_code}", 'weight')
                return None
                
        except requests.exceptions.Timeout:
            self.log("⏱️ Request No API timeout", 'weight')
            return None
        except requests.exceptions.ConnectionError:
            self.log("🌐 Request No API connection error", 'weight')
            return None
        except Exception as e:
            self.log(f"❌ Request No API error: {str(e)}", 'weight')
            return None

    def on_job_no_key_release(self, event=None):
        """Handle key release for instant Request No lookup"""
        try:
            job_no = self.job_entry.get().strip()
            # Only query if job number is at least 9 digits
            if len(job_no) >= 9:
                self.log(f"🔍 Quick lookup for Job No: {job_no}", 'weight')
                request_no = self.get_request_no_from_api(job_no)
                if request_no:
                    self.request_entry.delete(0, tk.END)
                    self.request_entry.insert(0, request_no)
                    self.log(f"✅ Auto-filled Request No: {request_no}", 'weight')
            # Enable fetch button if both job and request are present
            self._update_fetch_data_btn_state()
        except Exception as e:
            self.log(f"❌ Error in key release handler: {str(e)}", 'weight')

    def on_job_no_change(self, event=None):
        """Check API for job/lot data and auto-populate if found."""
        try:
            job_no = self.job_entry.get().strip()
            request_no = self.request_entry.get().strip()
            lot_no = self.manual_lot_var.get().strip() if hasattr(self, 'manual_lot_var') else '1'
            if not job_no:
                self._update_fetch_data_btn_state()
                return
            # Check API only
            def api_check_callback(api_data):
                if api_data:
                        self._display_strip_table_and_autofill(api_data)
                        self.log("✅ Populated from API.", 'weight')
                else:
                    self.log("⚠️ No data found in API. Please enter manually.", 'weight')
            # Start API check in background
            def api_worker():
                api_url = self.api_url_var.get()
                if not api_url.endswith('='):
                    if '?' in api_url:
                        api_url += '&job_no='
                    else:
                        api_url += '?job_no='
                full_url = f"{api_url}{job_no}"
                api_key = getattr(self, 'api_key_var', tk.StringVar()).get().strip()
                if api_key:
                    separator = '&' if '?' in full_url else '?'
                    full_url += f"{separator}api_key={api_key}"
                # Note: Not logging this URL to avoid exposing API key
                try:
                    import requests
                    response = requests.get(full_url, timeout=5, allow_redirects=True)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('success') and data.get('data'):
                            self.root.after(0, lambda: api_check_callback(data['data']))
                            return
                except Exception as e:
                    self.log(f"❌ API check error: {str(e)}", 'weight')
                self.root.after(0, lambda: api_check_callback(None))
            import threading
            threading.Thread(target=api_worker, daemon=True).start()
            self._update_fetch_data_btn_state()
        except Exception as e:
            self.log(f"❌ Error in job number change handler: {str(e)}", 'weight')

    def _update_fetch_data_btn_state(self):
        """Enable fetch button only if both job and request are present"""
        job_no = self.job_entry.get().strip()
        request_no = self.request_entry.get().strip()
        if job_no and request_no:
            self.fetch_data_btn.config(state='normal')
        else:
            self.fetch_data_btn.config(state='disabled')

    def setup_accept_request_tab(self):
        """Setup Accept Request tab with enhanced horizontal UI"""
        accept_frame = ttk.Frame(self.notebook)
        self.notebook.add(accept_frame, text="✅ Accept Request")
        
        # 1. Top Bar: Controls (Full Width)
        controls_frame = ttk.Frame(accept_frame, padding="5 5 5 5")
        controls_frame.pack(fill='x', side='top')
        
        # Left: Action Buttons
        ttk.Button(controls_frame, text="📋 Fetch Requests", style='Info.TButton', 
                   command=self.fetch_request_list).pack(side='left', padx=2)
                   
        self.auto_acknowledge_all_btn = ttk.Button(controls_frame, text="🤖 Auto Acknowledge All", 
                                                 style='Success.TButton', command=self.auto_acknowledge_all_requests,
                                                 state='disabled')
        self.auto_acknowledge_all_btn.pack(side='left', padx=2)
        
        self.clear_requests_btn = ttk.Button(controls_frame, text="🧹 Clear List", 
                                           style='Danger.TButton', command=self.clear_request_list).pack(side='left', padx=2)

        # Settings Checkboxes (Next to buttons)
        self.save_job_data_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(controls_frame, text="Save Job Data", variable=self.save_job_data_var).pack(side='left', padx=10)
        
        self.auto_fill_qty_weight_var = tk.BooleanVar(value=True)
        # Hidden or available? User didn't ask, but logic needs it. I'll keep it active but hidden to unclutter, or add small checkbox.
        # Adding small checkbox
        ttk.Checkbutton(controls_frame, text="Auto-fill Wt", variable=self.auto_fill_qty_weight_var).pack(side='left', padx=5)

        # Right: Toggles
        # Log Toggle
        self.show_log_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(controls_frame, text="Show Log", variable=self.show_log_var, 
                      command=self.toggle_log_panel).pack(side='right', padx=2)

        # Tag Manager Button
        ttk.Button(controls_frame, text="⚙️ Manage Tags", command=self.show_tag_manager).pack(side='right', padx=2)
        
        # Status Label (Compact)
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(controls_frame, textvariable=self.status_var, font=('Segoe UI', 9), foreground='#666').pack(side='right', padx=10)

        # 2. Main Content: Table (Full Width)
        table_frame = ttk.Frame(accept_frame, padding=5)
        table_frame.pack(fill='both', expand=True)
        
        # Columns: Added 'Tag Prefix'
        columns = ('S.No.', 'Request No.', 'Jeweller Name', 'Address', 'Tag Prefix', 'Status', 'Action')
        
        self.request_tree = ttk.Treeview(table_frame, columns=columns, show='headings')
        
        # Configure columns
        self.request_tree.heading('S.No.', text='S.No.')
        self.request_tree.column('S.No.', width=50, minwidth=50, anchor='center')
        
        self.request_tree.heading('Request No.', text='Request No.')
        self.request_tree.column('Request No.', width=100, minwidth=100)
        
        self.request_tree.heading('Jeweller Name', text='Jeweller Name')
        self.request_tree.column('Jeweller Name', width=200, minwidth=150)
        
        self.request_tree.heading('Address', text='Address')
        self.request_tree.column('Address', width=150, minwidth=100)
        
        self.request_tree.heading('Tag Prefix', text='Tag Prefix (Edit)')
        self.request_tree.column('Tag Prefix', width=100, minwidth=80, anchor='center')
        
        self.request_tree.heading('Status', text='Status')
        self.request_tree.column('Status', width=100, minwidth=100)
        
        self.request_tree.heading('Action', text='Action')
        self.request_tree.column('Action', width=80, minwidth=80, anchor='center')
        
        # Scrollbars
        y_scroll = ttk.Scrollbar(table_frame, orient='vertical', command=self.request_tree.yview)
        x_scroll = ttk.Scrollbar(table_frame, orient='horizontal', command=self.request_tree.xview)
        self.request_tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        
        self.request_tree.pack(side='left', fill='both', expand=True)
        y_scroll.pack(side='right', fill='y')
        x_scroll.pack(side='bottom', fill='x')
        
        # Bindings
        self.request_tree.bind('<Double-1>', self.on_request_tree_double_click)
        
        # 3. Log Panel (Initial State: Hidden)
        self.log_container = ttk.Frame(accept_frame)
        
        log_label = ttk.Label(self.log_container, text="📝 Acknowledge Log", font=('Segoe UI', 9, 'bold'))
        log_label.pack(anchor='w', padx=5, pady=(5,0))
        
        self.acknowledge_log = scrolledtext.ScrolledText(self.log_container, height=8, font=('Consolas', 8), 
                                                       bg='#f8f9fa', fg='#495057')
        self.acknowledge_log.pack(fill='both', expand=True, padx=5, pady=5)

        # Initialize vars
        self.request_data = [] # Store raw data
        self.tag_prefix_var = tk.StringVar(value="") # Keeps compatibility
        
        # Initial Log State
        if self.show_log_var.get():
             self.log_container.pack(fill='both', expand=False, side='bottom', padx=5, pady=5)

    def toggle_log_panel(self):
        if self.show_log_var.get():
            self.log_container.pack(fill='both', expand=False, side='bottom', padx=5, pady=5)
        else:
            self.log_container.pack_forget()

    def show_tag_manager(self): # type: ignore
        """Show the Tag Manager dialog"""
        if getattr(self, 'tag_manager', None):
            self.tag_manager.show_editor(self.root) # type: ignore
        else:
            messagebox.showerror("Error", "TagManager module not available.")

    def on_request_tree_double_click(self, event):
        region = self.request_tree.identify("region", event.x, event.y)
        if region != "cell":
            return
            
        column = self.request_tree.identify_column(event.x)
        item_id = self.request_tree.identify_row(event.y)
        if not item_id: return
        
        # Get column name. #1 is S.No., #5 is Tag Prefix
        # Columns: S.No, ReqNo, JewellerName, Address, TagPrefix, Status, Action
        # Indices: 0, 1, 2, 3, 4, 5, 6
        
        col_idx = int(column.replace('#', '')) - 1
        
        # Check if Tag Prefix column (index 4)
        if col_idx == 4:
            self.edit_tree_cell(item_id, column, 'tag_prefix')
        elif col_idx == 6: # Action
             self.on_request_double_click(event)

    def edit_tree_cell(self, item_id, column, data_key):
        x, y, w, h = self.request_tree.bbox(item_id, column)
        entry = ttk.Entry(self.request_tree)
        entry.place(x=x, y=y, width=w, height=h)
        
        current_val = self.request_tree.set(item_id, column)
        entry.insert(0, str(current_val) if current_val is not None else "")
        entry.select_range(0, tk.END)
        entry.focus()
        
        def save_edit(event=None):
            new_val = entry.get()
            self.request_tree.set(item_id, column, new_val)
            entry.destroy()
            
            # Update data
            values = self.request_tree.item(item_id, 'values')
            req_no = values[1]
            for req in self.request_data:
                if req['request_no'] == req_no:
                    req[data_key] = new_val
                    break
        
        entry.bind('<Return>', save_edit)
        entry.bind('<FocusOut>', lambda e: save_edit())
        
    def setup_accept_request_left_section(self, parent):
        """Setup left section with controls and settings"""
        
        # Controls card
        controls_card = ttk.LabelFrame(parent, text="🎮 Controls", style='Compact.TLabelframe')
        controls_card.pack(fill='x', pady=(0, 8))
        
        controls_frame = ttk.Frame(controls_card)
        controls_frame.pack(fill='x', padx=8, pady=8)
        
        # Fetch Requests button
        self.fetch_requests_btn = ttk.Button(controls_frame, text="📋 Fetch Requests", 
                                           style='Info.TButton', command=self.fetch_request_list)
        self.fetch_requests_btn.pack(fill='x', pady=2)
        
        # Auto Acknowledge All button
        self.auto_acknowledge_all_btn = ttk.Button(controls_frame, text="🤖 Auto Acknowledge All", 
                                                 style='Success.TButton', command=self.auto_acknowledge_all_requests,
                                                 state='disabled')
        self.auto_acknowledge_all_btn.pack(fill='x', pady=2)
        
        # Clear List button
        self.clear_requests_btn = ttk.Button(controls_frame, text="🧹 Clear List", 
                                          style='Danger.TButton', command=self.clear_request_list)
        self.clear_requests_btn.pack(fill='x', pady=2)
        
        # Settings card
        settings_card = ttk.LabelFrame(parent, text="⚙️ Acknowledge Settings", style='Compact.TLabelframe')
        settings_card.pack(fill='x', pady=(0, 8))
        
        settings_frame = ttk.Frame(settings_card)
        settings_frame.pack(fill='x', padx=8, pady=8)
        
        # AHC Remarks (disabled - not needed)
        ach_remarks_label = ttk.Label(settings_frame, text="ℹ️ AHC Remarks: Not required for automation", 
                                    font=('Segoe UI', 8, 'italic'), foreground='#6c757d')
        ach_remarks_label.pack(anchor='w', pady=2)
        
        # Auto-fill quantity and weight checkbox
        self.auto_fill_qty_weight_var = tk.BooleanVar(value=True)
        auto_fill_cb = ttk.Checkbutton(settings_frame, text="Auto-fill quantity & weight from declaration", 
                                     variable=self.auto_fill_qty_weight_var)
        auto_fill_cb.pack(anchor='w', pady=2)
        
        # Save Job Data checkbox
        self.save_job_data_var = tk.BooleanVar(value=True)
        save_job_cb = ttk.Checkbutton(settings_frame, text="Save Request Data to Job Card Database", 
                                     variable=self.save_job_data_var)
        save_job_cb.pack(anchor='w', pady=2)
        
        # Auto-print voucher checkbox (always enabled now)
        auto_print_label = ttk.Label(settings_frame, text="✅ Voucher Print: Always enabled", 
                                   font=('Segoe UI', 8, 'italic'), foreground='#28a745')
        auto_print_label.pack(anchor='w', pady=2)
        
        # Tag Prefix Pattern
        ttk.Label(settings_frame, text="Tag Prefix Pattern:", font=('Segoe UI', 8, 'bold')).pack(anchor='w', pady=(8, 2))
        self.tag_prefix_var = tk.StringVar(value="")
        
        # Frame for Entry + Manage Button
        tag_frame = ttk.Frame(settings_frame)
        tag_frame.pack(fill='x', pady=2)
        
        self.tag_prefix_entry = ttk.Entry(tag_frame, textvariable=self.tag_prefix_var)
        self.tag_prefix_entry.pack(side='left', fill='x', expand=True, padx=(0, 2))
        
        # Manage Button
        ttk.Button(tag_frame, text="⚙️", width=3, command=self.show_tag_manager).pack(side='right')
        
        ttk.Label(settings_frame, text="(e.g. ABC - Default / Optional)", font=('Segoe UI', 7, 'italic'), foreground='#6c757d').pack(anchor='w', pady=0)
        
        # Status card
        status_card = ttk.LabelFrame(parent, text="📊 Status", style='Compact.TLabelframe')
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
        log_card = ttk.LabelFrame(parent, text="📝 Acknowledge Log", style='Compact.TLabelframe')
        log_card.pack(fill='both', expand=True)
        
        self.acknowledge_log = scrolledtext.ScrolledText(log_card, height=8, font=('Consolas', 7), 
                                                       bg='#f8f9fa', fg='#495057', wrap=tk.WORD)
        self.acknowledge_log.pack(fill='both', expand=True, padx=8, pady=8)
        
        self.acknowledge_log.pack(fill='both', expand=True, padx=8, pady=8)

    def show_tag_manager(self):
        """Show the Tag Manager dialog"""
        if getattr(self, 'tag_manager', None):
            self.tag_manager.show_editor(self.root)
        else:
            messagebox.showerror("Error", "TagManager module not available.")
        
    def setup_accept_request_right_section(self, parent):
        """Setup right section with request list table"""
        
        # Request List card
        list_card = ttk.LabelFrame(parent, text="📋 Request List", style='Compact.TLabelframe')
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
        
    def _map_request_list_columns(self, header_texts):
        """Map column index for received-request list (live + UAT layouts)."""
        col = {}
        for i, raw in enumerate(header_texts):
            h = (raw or '').strip().lower().replace('\n', ' ')
            if 's.no' in h or h.startswith('s no') or h == 'sl' or h == 'sl.':
                col['sno'] = i
            elif 'request no' in h:
                col['request_no'] = i
            elif 'request date' in h or (h == 'date' and 'request_date' not in col):
                col['request_date'] = i
            elif 'jeweller name' in h or 'outlet name' in h or h == 'name':
                col['jeweller_name'] = i
            elif 'jeweller address' in h or ('address' in h and 'jeweller' in h):
                col['jeweller_address'] = i
            elif 'status' in h:
                col['status'] = i
        if 'jeweller_address' not in col and 'jeweller_name' not in col:
            for i, raw in enumerate(header_texts):
                h = (raw or '').strip().lower()
                if 'jeweller' in h:
                    col['jeweller_name'] = i
                    break
        return col

    def _normalize_portal_href(self, href):
        """Turn relative / javascript-free portal paths into full URLs."""
        if not href:
            return None
        href = href.strip()
        if not href or href == '#' or href.lower().startswith('javascript:'):
            return None
        if href.startswith('/'):
            return portal_config.build_portal_url(href)
        return href

    def _url_from_onclick_or_data_attrs(self, el):
        """Extract acknowledge URL from onclick / data-* when href is # or javascript."""
        import re
        chunks = []
        for attr in ('onclick', 'data-url', 'data-href', 'ng-click'):
            try:
                val = el.get_attribute(attr)
                if val:
                    chunks.append(val)
            except Exception:
                pass
        combined = ' '.join(chunks)
        if not combined:
            return None
        patterns = [
            r"['\"]([^'\"]*AHCReceivingUIDJewellerRequest[^'\"]*)['\"]",
            r"['\"]([^'\"]*ReceivingUIDJewellerRequest[^'\"]*)['\"]",
            r"['\"]([^'\"]*(?:ReceivingUID|AHCReceiving)[^'\"]*)['\"]",
            r"(/MANAK/[^\s'\"<>]+Receiving[^\s'\"<>]*)",
            r"location\.href\s*=\s*['\"]([^'\"]+)['\"]",
        ]
        for pat in patterns:
            m = re.search(pat, combined, re.I)
            if m:
                return self._normalize_portal_href(m.group(1).strip())
        return None

    def _resolve_acknowledge_url_from_element(self, el):
        """Resolve a navigable acknowledge URL from a link/button element."""
        url = self._normalize_portal_href((el.get_attribute('href') or '').strip())
        if url:
            return url
        return self._url_from_onclick_or_data_attrs(el)

    def _portal_driver_for_request_list(self):
        """Prefer the browser already showing the HMRD received-request list."""
        marker = 'assayingAH_List'
        for d in (self.driver, self.reception_driver):
            if not d:
                continue
            try:
                url = (d.current_url or '').lower()
                if marker in url and 'hmtype=hmrd' in url:
                    return d
            except Exception:
                continue
        return self.reception_driver if self.reception_driver else self.driver

    def _get_acknowledge_href_from_row(self, row):
        """Find acknowledge/receive URL in a list row (text or href patterns)."""
        link_xpaths = [
            ".//a[contains(@href,'AHCReceivingUIDJewellerRequest')]",
            ".//a[contains(@href,'ReceivingUIDJewellerRequest')]",
            ".//a[contains(translate(normalize-space(.),"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'acknowledge')]",
            ".//a[contains(translate(@title,"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'acknowledge')]",
            ".//input[contains(translate(@value,"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'acknowledge')]",
            ".//button[contains(translate(normalize-space(.),"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'acknowledge')]",
        ]
        for xpath in link_xpaths:
            try:
                for el in row.find_elements(By.XPATH, xpath):
                    url = self._resolve_acknowledge_url_from_element(el)
                    if url:
                        return url
            except Exception:
                continue
        try:
            for el in row.find_elements(By.XPATH, './/a[@href]'):
                href = (el.get_attribute('href') or '').strip()
                if 'ReceivingUID' in href or 'eRequestId' in href:
                    url = self._normalize_portal_href(href)
                    if url:
                        return url
        except Exception:
            pass
        try:
            for el in row.find_elements(By.XPATH, './/*[@onclick]'):
                url = self._url_from_onclick_or_data_attrs(el)
                if url:
                    return url
        except Exception:
            pass
        return None

    def _find_received_requests_table(self, driver):
        """Locate the hallmarking received-request table (not layout/menu tables)."""
        best_table = None
        best_score = -1
        for table in driver.find_elements(By.TAG_NAME, 'table'):
            try:
                text = (table.text or '')[:800].lower()
                if 'request' not in text:
                    continue
                score = 0
                if 'request no' in text:
                    score += 3
                if 'jeweller' in text or 'received request' in text:
                    score += 2
                links = table.find_elements(
                    By.XPATH,
                    ".//a[contains(@href,'ReceivingUID') or "
                    "contains(translate(.,'ACKNOWLEDGE','acknowledge'),'acknowledge')]",
                )
                score += min(len(links), 5)
                data_rows = table.find_elements(By.XPATH, './/tbody/tr[td]')
                if not data_rows:
                    data_rows = [
                        r for r in table.find_elements(By.TAG_NAME, 'tr')
                        if r.find_elements(By.TAG_NAME, 'td')
                    ]
                score += min(len(data_rows), 5)
                if score > best_score:
                    best_score = score
                    best_table = table
            except Exception:
                continue
        return best_table

    def _parse_received_requests_from_table(self, table):
        """Parse rows from received-request list table."""
        requests = []
        skipped_no_link = 0
        skipped_no_req = 0

        header_cells = []
        thead_rows = table.find_elements(By.XPATH, './/thead/tr')
        if thead_rows:
            header_cells = [
                c.text.strip() for c in
                thead_rows[0].find_elements(By.XPATH, './th|./td')
            ]
        if not header_cells:
            all_rows = table.find_elements(By.TAG_NAME, 'tr')
            if all_rows:
                header_cells = [
                    c.text.strip() for c in
                    all_rows[0].find_elements(By.XPATH, './th|./td')
                ]

        col = self._map_request_list_columns(header_cells)
        if 'request_no' not in col:
            col = {
                'sno': 0, 'request_no': 1, 'request_date': 2,
                'jeweller_name': 3, 'jeweller_address': 4, 'status': 5,
            }

        data_rows = table.find_elements(By.XPATH, './/tbody/tr[td]')
        if not data_rows:
            data_rows = [
                r for r in table.find_elements(By.TAG_NAME, 'tr')
                if r.find_elements(By.TAG_NAME, 'td')
            ]
            if data_rows and data_rows[0].find_elements(By.TAG_NAME, 'th'):
                data_rows = data_rows[1:]

        for row in data_rows:
            try:
                cells = row.find_elements(By.TAG_NAME, 'td')
                if len(cells) < 3:
                    continue

                def cell_at(key, default_idx):
                    idx = col.get(key, default_idx)
                    if idx is None or idx >= len(cells):
                        return ''
                    return cells[idx].text.strip()

                request_no = cell_at('request_no', 1)
                if not request_no or not any(ch.isdigit() for ch in request_no):
                    continue

                acknowledge_link = self._get_acknowledge_href_from_row(row)
                if not acknowledge_link:
                    skipped_no_link += 1
                    continue

                jeweller_name = cell_at('jeweller_name', 3)
                jeweller_address = cell_at('jeweller_address', 4)
                if not jeweller_name and jeweller_address:
                    jeweller_name = jeweller_address.split('\n')[0].strip()
                if not jeweller_address and jeweller_name:
                    jeweller_address = jeweller_name

                requests.append({
                    's_no': cell_at('sno', 0),
                    'request_no': request_no,
                    'request_date': cell_at('request_date', 2),
                    'jeweller_name': jeweller_name,
                    'jeweller_address': jeweller_address,
                    'status': cell_at('status', 5),
                    'acknowledge_url': acknowledge_link,
                })
            except Exception:
                continue

        if skipped_no_link or skipped_no_req:
            self.log(
                f"ℹ️ Parsed {len(requests)} rows "
                f"(skipped {skipped_no_link} without action link)",
                'acknowledge',
            )
        return requests

    def fetch_request_list(self):
        """Fetch request list from MANAK portal"""
        # Check license before API operations
        if not self.check_license_before_action("request list fetching"):
            return
            
        # Dual Browser Logic
        if not self.reception_driver and (not self.driver or not self.logged_in):
             messagebox.showwarning("Not Ready", "Please open browser (QM or Reception) and login first")
             return
            
        self.log("🔍 Fetching request list...", 'acknowledge')
        threading.Thread(target=self._fetch_request_list_worker, daemon=True).start()
        
    def _fetch_request_list_worker(self):
        """Worker thread for fetching request list (with pagination)."""
        loading_dialog = None
        try:
            driver = self._portal_driver_for_request_list()
            if not driver:
                self.log("❌ No active browser found", 'acknowledge')
                return

            loading_dialog = LoadingDialog(
                self.root, "Fetching Requests", "Loading request list from MANAK portal..."
            )

            request_list_url = portal_config.build_portal_url("/MANAK/assayingAH_List?hmType=HMRD")
            current_url = ''
            try:
                current_url = (driver.current_url or '').lower()
            except Exception:
                pass
            if 'assayingah_list' not in current_url or 'hmtype=hmrd' not in current_url:
                loading_dialog.update_status("Navigating to request list page...")
                driver.get(request_list_url)
            else:
                loading_dialog.update_status("Using open request list page...")

            loading_dialog.update_status("Waiting for request table...")
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//table[.//*[contains(text(),'Request No') or contains(text(),'Request No.')]]"
                        "//tr[td]",
                    ))
                )
            except Exception:
                pass
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//table//a[contains(translate(normalize-space(.),"
                        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'acknowledge')]",
                    ))
                )
            except Exception:
                pass
            time.sleep(1.5)

            all_requests = []
            current_page = 1
            max_pages = 20

            while current_page <= max_pages:
                loading_dialog.update_status(f"Parsing page {current_page}...")
                self.log(f"📄 Processing list page {current_page}...", 'acknowledge')

                request_table = self._find_received_requests_table(driver)
                if not request_table:
                    if current_page == 1:
                        raise Exception(
                            "Request table not found — ensure you are logged in and on "
                            "'List of Received Request - Hallmarking'"
                        )
                    break

                page_requests = self._parse_received_requests_from_table(request_table)
                for req in page_requests:
                    jeweller_state = ''
                    jeweller_info = self._lookup_jeweller_by_name(req.get('jeweller_name', ''))
                    if jeweller_info:
                        jeweller_state = (
                            jeweller_info.get('State') or jeweller_info.get('state') or ''
                        )
                    if not jeweller_state:
                        jeweller_state = self._infer_state_from_address(
                            req.get('jeweller_address', '')
                        )
                    req['jeweller_state'] = jeweller_state

                all_requests.extend(page_requests)
                self.log(
                    f"✅ Page {current_page}: {len(page_requests)} requests "
                    f"(total {len(all_requests)})",
                    'acknowledge',
                )

                next_button = None
                for xpath in (
                    "//a[contains(text(),'Next') or contains(text(),'next') or contains(text(),'»')]",
                    "//a[contains(@class,'next')]",
                    f"//a[normalize-space(text())='{current_page + 1}']",
                ):
                    try:
                        next_button = driver.find_element(By.XPATH, xpath)
                        if next_button.is_displayed():
                            break
                        next_button = None
                    except Exception:
                        continue

                if next_button and next_button.is_enabled():
                    btn_class = (next_button.get_attribute('class') or '').lower()
                    if 'disabled' not in btn_class:
                        next_button.click()
                        time.sleep(1.5)
                        current_page += 1
                        continue
                break

            requests = all_requests
            self.root.after(0, self._update_request_list_ui, requests)

            loading_dialog.update_status("Done!")
            loading_dialog.update_message(f"Found {len(requests)} requests")
            time.sleep(0.5)
            loading_dialog.close()

            if requests:
                self.log(
                    f"✅ Successfully fetched {len(requests)} requests from {current_page} page(s)",
                    'acknowledge',
                )
                messagebox.showinfo(
                    "Success",
                    f"✅ Found {len(requests)} requests to acknowledge!",
                )
            else:
                self.log("⚠️ No requests found to acknowledge", 'acknowledge')
                messagebox.showwarning(
                    "No Requests",
                    "No requests found to acknowledge.\n\n"
                    "The page may use a different action link — stay on the list page "
                    "after login, then try Fetch again.",
                )

        except Exception as e:
            if loading_dialog:
                loading_dialog.close()
            self.log(f"❌ Error fetching request list: {str(e)}", 'acknowledge')
            messagebox.showerror("Error", f"Error fetching request list: {str(e)}")
            
    def _update_request_list_ui(self, requests):
        """Update the request list UI with fetched data"""
        # Clear existing data
        for item in self.request_tree.get_children():
            self.request_tree.delete(item)
        
        self.request_data = requests
        
        # Add requests to treeview with Tag Prefix lookup
        for request in requests:
            # Determine initial tag prefix
            tag_prefix = ""
            if getattr(self, 'tag_manager', None):
                tag_prefix = self.tag_manager.get_prefix(request['jeweller_name']) or ""
            
            # Store in request object so we can use/edit it
            request['tag_prefix'] = tag_prefix
            
            self.request_tree.insert('', 'end', values=(
                request['s_no'],
                request['request_no'],
                request['jeweller_name'],
                request['jeweller_address'],
                tag_prefix,
                request['status'],
                "🔄 Ack"
            ))
        
        # Update status (Compact)
        total = len(requests)
        pending = len([r for r in requests if r['status'] == 'New Request'])
        completed = total - pending
        
        status_text = f"Total: {total} | Pending: {pending} | Completed: {completed}"
        if hasattr(self, 'status_var'):
             self.status_var.set(status_text)
        
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
        # Reset status labels
        if hasattr(self, 'status_var'):
             self.status_var.set("Ready")
        
        # Disable auto acknowledge button
        self.auto_acknowledge_all_btn.config(state='disabled')
        
        self.log("🧹 Request list cleared", 'acknowledge')
        
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
        # Check license before automation
        if not self.check_license_before_action("request automation"):
            return
            
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
                        self.log(f"✅ Acknowledged request {request['request_no']}", 'acknowledge')
                    else:
                        failed += 1
                        self.log(f"❌ Failed to acknowledge request {request['request_no']}", 'acknowledge')
                        
                except Exception as e:
                    failed += 1
                    self.log(f"❌ Error acknowledging request {request['request_no']}: {str(e)}", 'acknowledge')
                
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
                              f"✅ Completed: {completed}\n❌ Failed: {failed}")
            
            # Refresh the request list
            self.fetch_request_list()
            
        except Exception as e:
            if loading_dialog:
                loading_dialog.close()
            self.log(f"❌ Error in auto acknowledge: {str(e)}", 'acknowledge')
            messagebox.showerror("Error", f"Error in auto acknowledge: {str(e)}")
            
    def _acknowledge_single_request(self, request):
        """Acknowledge a single request (for manual acknowledge)"""
        try:
            success = self._acknowledge_single_request_internal(request)
            
            if success:
                self.log(f"✅ Successfully acknowledged request {request['request_no']}", 'acknowledge')
                messagebox.showinfo("Success", f"✅ Request {request['request_no']} acknowledged successfully!")
            else:
                self.log(f"❌ Failed to acknowledge request {request['request_no']}", 'acknowledge')
                messagebox.showerror("Error", f"❌ Failed to acknowledge request {request['request_no']}")
                
        except Exception as e:
            self.log(f"❌ Error acknowledging request {request['request_no']}: {str(e)}", 'acknowledge')
            messagebox.showerror("Error", f"Error acknowledging request: {str(e)}")
            
    def _lookup_jeweller_by_name(self, jeweller_name):
        """Match jeweller from HallmarkPro API by name (for State, licence, etc.)."""
        if not jeweller_name or not hasattr(self, 'jeweller_api_url_var'):
            return None
        try:
            import requests
            url = self.jeweller_api_url_var.get().strip()
            if not url:
                return None
            firm_id = 2
            if hasattr(self, 'license_manager') and self.license_manager:
                try:
                    firm_id = int(getattr(self.license_manager, 'firm_id', 2) or 2)
                except (TypeError, ValueError):
                    pass
            sep = '&' if '?' in url else '?'
            url = f"{url}{sep}firm_id={firm_id}"
            resp = requests.get(url, timeout=15)
            if resp.status_code != 200:
                return None
            data = resp.json()
            items = data if isinstance(data, list) else data.get('data', data.get('jewellers', []))
            target = jeweller_name.strip().upper()
            for j in items:
                name = str(j.get('Jewellers_Name', j.get('name', ''))).strip().upper()
                if name == target or target in name or name in target:
                    return j
        except Exception as e:
            self.log(f"⚠️ Jeweller lookup failed: {e}", 'acknowledge')
        return None

    def _infer_state_from_address(self, address):
        """Infer Indian state from address text or pincode when State column is missing."""
        if not address:
            return ''
        addr = address.upper()
        pincode_map = {
            '110': 'Delhi', '111': 'Delhi', '112': 'Delhi', '113': 'Delhi',
            '400': 'Maharashtra', '401': 'Maharashtra', '410': 'Maharashtra',
            '560': 'Karnataka', '561': 'Karnataka',
            '600': 'Tamil Nadu', '601': 'Tamil Nadu',
            '700': 'West Bengal', '711': 'West Bengal',
        }
        import re
        m = re.search(r'\b(\d{6})\b', address)
        if m:
            prefix = m.group(1)[:3]
            if prefix in pincode_map:
                return pincode_map[prefix]
        state_keywords = [
            ('DELHI', 'Delhi'), ('MUMBAI', 'Maharashtra'), ('MAHARASHTRA', 'Maharashtra'),
            ('KARNATAKA', 'Karnataka'), ('TAMIL NADU', 'Tamil Nadu'), ('WEST BENGAL', 'West Bengal'),
            ('GUJARAT', 'Gujarat'), ('RAJASTHAN', 'Rajasthan'), ('UTTAR PRADESH', 'Uttar Pradesh'),
            ('HARYANA', 'Haryana'), ('PUNJAB', 'Punjab'),
        ]
        for key, state in state_keywords:
            if key in addr:
                return state
        return ''

    def _map_acknowledge_table_columns(self, header_texts):
        """Map column index by header labels (Live + UAT layouts)."""
        col = {}
        for i, raw in enumerate(header_texts):
            h = (raw or '').strip().lower().replace('\n', ' ')
            if (
                'item' in h and 'category' in h
                and 'weight' not in h and 'observed' not in h
            ):
                col['category'] = i
            elif (
                h in ('quantity', 'qty')
                or (h.startswith('quantity') and 'received' not in h and 'ahc' not in h)
            ):
                if 'qty' not in col:
                    col['qty'] = i
            elif 'received' in h and 'quantity' in h:
                col['rec_qty'] = i
            elif 'declared purity' in h or (h == 'purity' or h.endswith(' purity')):
                col['purity'] = i
            elif 'observed' in h and 'weight' in h:
                col['observed_weight'] = i
            elif 'total weight' in h and 'article' in h:
                col['declared_weight'] = i
            elif h == 'accept' or ('accept' in h and 'checkbox' not in h):
                col['accept'] = i
        if 'observed_weight' in col:
            col['weight'] = col['observed_weight']
        elif 'declared_weight' in col:
            col['weight'] = col['declared_weight']
        return col

    def _portal_set_input_value(self, driver, element, value):
        """Set an input value and fire events so portal jQuery handlers run."""
        driver.execute_script(
            """
            var el = arguments[0], val = arguments[1];
            el.value = val;
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
            el.dispatchEvent(new KeyboardEvent('keyup', {bubbles: true}));
            if (window.jQuery) { jQuery(el).val(val).trigger('keyup').trigger('change'); }
            """,
            element,
            str(value),
        )

    def _sync_observed_net_totals(self, driver):
        """Run portal calculateSum / calculateSumQuantity (updates readonly net fields)."""
        driver.execute_script(
            """
            if (typeof calculateSum === 'function') { calculateSum(); }
            else {
                var sum = 0;
                document.querySelectorAll('.totItemCatgWeight').forEach(function(el) {
                    var v = parseFloat(el.value);
                    if (!isNaN(v) && el.value.length) sum += v;
                });
                var ow = document.getElementById('observed_weight_ahc');
                if (ow) ow.value = sum.toFixed(3);
                if (window.jQuery && jQuery('#observed_weight_ahc').length) {
                    jQuery('#observed_weight_ahc').val(sum.toFixed(3)).trigger('change');
                }
            }
            if (typeof calculateSumQuantity === 'function') { calculateSumQuantity(); }
            else {
                var qsum = 0;
                document.querySelectorAll('.numquantity,.recquantity').forEach(function(el) {
                    var v = parseFloat(el.value);
                    if (!isNaN(v) && el.value.length) qsum += v;
                });
                var tq = document.getElementById('total_net_quantity');
                if (tq) tq.value = qsum;
                if (window.jQuery && jQuery('#total_net_quantity').length) {
                    jQuery('#total_net_quantity').val(qsum).trigger('change');
                }
            }
            """
        )

    def _cell_text_or_input(self, cell):
        """Read visible text or input value from a table cell."""
        try:
            inputs = cell.find_elements(By.TAG_NAME, 'input')
            for inp in inputs:
                val = (inp.get_attribute('value') or '').strip()
                if val:
                    return val
        except Exception:
            pass
        return (cell.text or '').strip().split('\n')[0].strip()

    def _cell_visible_label(self, cell):
        """Prefer human-readable cell text (e.g. Earings, 22K916), not hidden codes."""
        text = (cell.text or '').strip()
        for line in (ln.strip() for ln in text.split('\n') if ln.strip()):
            if not self._looks_like_numeric_code(line):
                return line
        try:
            for inp in cell.find_elements(By.TAG_NAME, 'input'):
                cls = (inp.get_attribute('class') or '').lower()
                if 'hide' in cls or 'hidden' in cls:
                    continue
                val = (inp.get_attribute('value') or '').strip()
                if val and not self._looks_like_numeric_code(val):
                    return val
        except Exception:
            pass
        return text.split('\n')[0].strip() if text else ''

    @staticmethod
    def _looks_like_numeric_code(value):
        """True for weights and internal ids (10.35, 1003), not item names."""
        s = (value or '').strip()
        if not s:
            return True
        try:
            float(s.replace(',', ''))
            return True
        except ValueError:
            pass
        return s.isdigit()

    def _find_acknowledge_declaration_table(self, driver):
        """Pick the item-declaration table with the most data rows (multi-item requests)."""
        xpath = (
            "//table[.//th[contains(translate(., "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'item category')]]"
        )
        best_table = None
        best_headers = []
        best_col = {}
        best_rows = []
        for table in driver.find_elements(By.XPATH, xpath):
            try:
                headers = [th.text.strip() for th in table.find_elements(By.XPATH, './/th')]
                if not any('item category' in (h or '').lower() for h in headers):
                    continue
                col = self._map_acknowledge_table_columns(headers)
                if 'category' not in col:
                    continue
                rows = self._declaration_table_data_rows(table)
                if len(rows) > len(best_rows):
                    best_table = table
                    best_headers = headers
                    best_col = col
                    best_rows = rows
            except Exception:
                continue
        return best_table, best_headers, best_col, best_rows

    def _declaration_table_data_rows(self, table):
        """All visible data rows in the declaration table."""
        rows = table.find_elements(By.XPATH, './/tbody/tr[td]')
        if not rows:
            rows = [
                r for r in table.find_elements(By.TAG_NAME, 'tr')
                if r.find_elements(By.TAG_NAME, 'td')
            ]
            if rows and rows[0].find_elements(By.TAG_NAME, 'th'):
                rows = rows[1:]
        return [r for r in rows if r.is_displayed()]

    def _row_weight_from_cells(self, cells, col, header_weight, header_pcs, row_qty):
        """Weight from observed input, else declared article weight, else header split."""
        for key in ('observed_weight', 'declared_weight', 'weight'):
            idx = col.get(key)
            if idx is None or idx >= len(cells):
                continue
            wt_text = self._cell_text_or_input(cells[idx])
            try:
                w = float(wt_text) if wt_text else 0.0
            except (ValueError, TypeError):
                w = 0.0
            if w > 0:
                return w
        if row_qty > 0 and header_weight and header_pcs:
            try:
                hw = float(header_weight)
                hp = int(header_pcs)
                if hp > 0 and hw > 0:
                    return round((hw / hp) * row_qty, 3)
            except (ValueError, TypeError):
                pass
        return 0.0

    def _log_job_row_debug(self, index, job, total):
        """Log one extracted row before DB save (debug)."""
        self.log(
            f"  📋 Row {index}/{total}: item={job.get('item')!r} | "
            f"pcs={job.get('pcs')} | weight={job.get('weight')}g | "
            f"purity={job.get('purity')!r} | licence={job.get('licence_no')} | "
            f"req={job.get('request_no')}",
            'acknowledge',
        )

    def _save_acknowledge_jobs_batch(self, jobs_to_save, request_no):
        """Save every extracted item row to the API with debug logging."""
        jobs_with_data = [
            j for j in jobs_to_save
            if (j.get('pcs', 0) or 0) > 0 or (float(j.get('weight', 0) or 0)) > 0
        ]
        skipped = len(jobs_to_save) - len(jobs_with_data)
        if skipped > 0:
            self.log(
                f"ℹ️ Skipped {skipped} empty row(s) (pcs=0 and weight=0)",
                'acknowledge',
            )
        if not jobs_with_data:
            self.log("⚠️ No job rows to save to database", 'acknowledge')
            return
        self.log(
            f"💾 Saving {len(jobs_with_data)} item row(s) for Request #{request_no} to database...",
            'acknowledge',
        )
        multi = len(jobs_with_data) > 1
        if multi and self._try_save_jobs_batch(jobs_with_data, request_no):
            return
        for i, job in enumerate(jobs_with_data, 1):
            self._log_job_row_debug(i, job, len(jobs_with_data))
            self._save_job_via_api(job)
            time.sleep(0.15)

    def _extract_acknowledge_jobs_from_table(self, driver, request, header_weight, header_pcs, header_purity, cml_no):
        """Extract per-row jobs from acknowledge page table (all items)."""
        jobs = []
        item_types_list = []
        try:
            table, headers, col, rows = self._find_acknowledge_declaration_table(driver)
            if not table or 'category' not in col:
                self.log("⚠️ Item declaration table not found", 'acknowledge')
                return jobs, item_types_list

            self.log(
                f"📊 Table headers: {headers}",
                'acknowledge',
            )
            self.log(
                f"📊 Scanning {len(rows)} data row(s) (columns: {col})",
                'acknowledge',
            )

            for row_idx, row in enumerate(rows, 1):
                try:
                    cells = row.find_elements(By.TAG_NAME, 'td')
                    if len(cells) < max(col.values()) + 1:
                        self.log(
                            f"⚠️ Row {row_idx}: only {len(cells)} cells, need "
                            f"{max(col.values()) + 1} — skipped",
                            'acknowledge',
                        )
                        continue

                    cat_text = self._cell_visible_label(cells[col['category']])
                    if not cat_text or 'category' in cat_text.lower() or 'total' in cat_text.lower():
                        continue
                    if self._looks_like_numeric_code(cat_text):
                        self.log(
                            f"⚠️ Row {row_idx}: item looks like weight/code: {cat_text!r} — skipped",
                            'acknowledge',
                        )
                        continue

                    qty_text = self._cell_text_or_input(cells[col['qty']]) if 'qty' in col else '0'
                    try:
                        row_qty = int(float(qty_text)) if qty_text else 0
                    except (ValueError, TypeError):
                        row_qty = 0

                    purity_text = ''
                    if 'purity' in col:
                        purity_text = self._cell_visible_label(cells[col['purity']])

                    row_weight = self._row_weight_from_cells(
                        cells, col, header_weight, header_pcs, row_qty
                    )

                    if row_qty <= 0 and row_weight <= 0:
                        self.log(
                            f"⚠️ Row {row_idx} ({cat_text}): no qty/weight — skipped",
                            'acknowledge',
                        )
                        continue

                    job = {
                        'request_no': request['request_no'],
                        'job_no': '',
                        'item': cat_text,
                        'purity': purity_text or header_purity,
                        'weight': row_weight,
                        'pcs': row_qty,
                        'licence_no': cml_no,
                        'material_type': 'Gold',
                        'date_of_request': datetime.now().strftime('%Y-%m-%d'),
                        'status': 'XRF',
                        'jeweller_name': request.get('jeweller_name', ''),
                    }
                    jobs.append(job)
                    item_types_list.append(cat_text)
                    self._log_job_row_debug(len(jobs), job, len(rows))
                except Exception as row_err:
                    self.log(f"⚠️ Row {row_idx} parse error: {row_err}", 'acknowledge')
                    continue
        except Exception as e:
            self.log(f"⚠️ Error extracting items: {e}", 'acknowledge')
        return jobs, item_types_list

    def _fill_uat_article_weights(self, driver):
        """Fill per-article weight inputs (UAT: itemWeightIndidual / weightCls) from header net weight."""
        try:
            total_w = 0.0
            for field_id in ('netweight', 'numweight'):
                elems = driver.find_elements(By.ID, field_id)
                if elems and elems[0].get_attribute('value'):
                    total_w = float(elems[0].get_attribute('value'))
                    break
            if total_w <= 0:
                return
            weight_inputs = driver.find_elements(By.CSS_SELECTOR, 'input.weightCls')
            active = [w for w in weight_inputs if w.is_displayed()]
            if not active:
                return
            per_item = round(total_w / len(active), 3)
            for inp in active:
                self._portal_set_input_value(driver, inp, per_item)
            for inp in driver.find_elements(By.CSS_SELECTOR, 'input.totItemCatgWeight'):
                try:
                    if inp.is_displayed() and not (inp.get_attribute('value') or '').strip():
                        self._portal_set_input_value(driver, inp, per_item)
                except Exception:
                    continue
            self._sync_observed_net_totals(driver)
            self.log(
                f"✅ Filled {len(active)} article weight(s) @ {per_item}g each (total {total_w}g)",
                'acknowledge',
            )
        except Exception as e:
            self.log(f"⚠️ Article weight fill: {e}", 'acknowledge')

    def _check_accept_checkboxes(self, driver):
        """Check Accept column checkboxes on UAT/live acknowledge page."""
        checked = 0
        try:
            try:
                select_all = driver.find_element(By.CSS_SELECTOR, 'input.selectall')
                if select_all.is_displayed() and not select_all.is_selected():
                    driver.execute_script('arguments[0].click();', select_all)
                    time.sleep(0.2)
            except Exception:
                pass
            boxes = driver.find_elements(
                By.XPATH,
                "//table[.//th[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]]"
                "//input[@type='checkbox']",
            )
            for cb in boxes:
                try:
                    if cb.is_displayed() and not cb.is_selected():
                        driver.execute_script("arguments[0].click();", cb)
                        checked += 1
                except Exception:
                    continue
            if checked:
                self.log(f"✅ Checked {checked} Accept checkbox(es)", 'acknowledge')
            return checked > 0
        except Exception as e:
            self.log(f"⚠️ Accept checkboxes: {e}", 'acknowledge')
            return False

    def _click_acknowledge_submit_on_page(self, driver):
        """Submit acknowledge form (UAT: Submit on same page; Live: may redirect after Add)."""
        self._check_accept_checkboxes(driver)
        submit_xpaths = [
            "//input[@id='save']",
            "//input[@type='button' and @value='Submit']",
            "//button[normalize-space()='Submit']",
            "//input[@type='button' and translate(@value,'submit','SUBMIT')='Submit']",
            "//input[@type='submit' and translate(@value,'submit','SUBMIT')='Submit']",
            "//button[contains(translate(.,'submit','SUBMIT'),'Submit')]",
            "//*[self::button or self::input][contains(translate(@value,'submit','SUBMIT'),'Submit')]",
        ]
        for xpath in submit_xpaths:
            try:
                btn = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                time.sleep(0.2)
                try:
                    btn.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", btn)
                self.log(f"✅ Clicked Submit ({xpath[:50]}...)", 'acknowledge')
                time.sleep(1.5)
                try:
                    alert = driver.switch_to.alert
                    self.log(f"🔔 Alert: {alert.text}", 'acknowledge')
                    alert.accept()
                    time.sleep(0.5)
                except Exception:
                    pass
                return True
            except Exception:
                continue
        return False

    def _acknowledge_single_request_internal(self, request):
        """Internal logic to acknowledge a single request"""
        request_no = request['request_no']
        
        # Dual Browser Selection
        driver = self._portal_driver_for_request_list()
        if not driver:
            self.log("❌ No active browser found", 'acknowledge')
            return False

        try:
            self.log(f"🔄 Processing Request: {request_no}", 'acknowledge')
            
            # 1. Open Acknowledge Page
            # Both browsers now use the same interface, so use the extracted URL
            if 'acknowledge_url' in request and request['acknowledge_url']:
                url = request['acknowledge_url']
                if url.startswith('/'):
                    url = portal_config.build_portal_url(url)
            else:
                self.log(f"❌ No acknowledge URL found for request {request_no}", 'acknowledge')
                return False
                
            driver.get(url)
            time.sleep(2)  # Give page time to load
            
            # Step 2: Wait for page to load and verify we're on the right page
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "form"))
                )
                
                # Check if we're on the acknowledge page by looking for key elements
                page_title = driver.title
                self.log(f"📄 Page loaded: {page_title}", 'acknowledge')
                
                # Check current URL
                current_url = driver.current_url
                self.log(f"🔗 Current URL: {current_url}", 'acknowledge')
                
            except Exception as e:
                self.log(f"⚠️ Page load timeout or form not found: {str(e)}", 'acknowledge')
                # Try to continue anyway
            
            # Step 3: Fill the form
            self.log("📝 Filling acknowledge form...", 'acknowledge')
            
            # Wait a bit more for dynamic content to load
            time.sleep(1)
            
            # Generate Tag ID - Select "Yes" radio button (OPTIONAL - continue if fails)
            tag_id_selected = False
            try:
                # Method 1: Try by exact ID
                tag_id_yes_radio = driver.find_element(By.ID, "strRadioTag_yes")
                if not tag_id_yes_radio.is_selected():
                    tag_id_yes_radio.click()
                    time.sleep(0.3)
                    self.log("✅ Selected 'Yes' for Generate Tag ID (Method 1)", 'acknowledge')
                    tag_id_selected = True
                else:
                    self.log("✅ Generate Tag ID 'Yes' already selected", 'acknowledge')
                    tag_id_selected = True
            except Exception as e:
                self.log(f"⚠️ Method 1 failed: {str(e)}", 'acknowledge')
                try:
                    # Method 2: Try by name and value
                    tag_id_yes_radio = driver.find_element(By.XPATH, "//input[@name='strRadioTag' and @value='Y']")
                    if not tag_id_yes_radio.is_selected():
                        tag_id_yes_radio.click()
                        time.sleep(0.3)
                        self.log("✅ Selected 'Yes' for Generate Tag ID (Method 2)", 'acknowledge')
                        tag_id_selected = True
                    else:
                        self.log("✅ Generate Tag ID 'Yes' already selected", 'acknowledge')
                        tag_id_selected = True
                except Exception as e2:
                    self.log(f"⚠️ Method 2 failed: {str(e2)}", 'acknowledge')
                    try:
                        # Method 3: Try by label text
                        yes_label = driver.find_element(By.XPATH, "//label[contains(text(), 'Yes')]//input[@type='radio']")
                        if not yes_label.is_selected():
                            yes_label.click()
                            time.sleep(0.3)
                            self.log("✅ Selected 'Yes' for Generate Tag ID (Method 3)", 'acknowledge')
                            tag_id_selected = True
                        else:
                            self.log("✅ Generate Tag ID 'Yes' already selected", 'acknowledge')
                            tag_id_selected = True
                    except Exception as e3:
                        self.log(f"⚠️ Could not select Generate Tag ID (all methods failed)", 'acknowledge')
                        self.log("ℹ️ This field may be optional or page structure has changed", 'acknowledge')
            
            # Fill Tag Prefix if configured
            # Determine prefix from request object (updated via table edit)
            tag_prefix = request.get('tag_prefix', '')
            
            # Fallback to mapping if missing (safety check)
            if not tag_prefix and getattr(self, 'tag_manager', None):
                 tag_prefix = self.tag_manager.get_prefix(request.get('jeweller_name', '')) or ""

            if tag_prefix:
                try:
                    # Wait for field to be enabled
                    try:
                        WebDriverWait(driver, 3).until(
                            lambda d: d.find_element(By.ID, "str_tag_pattern").is_enabled()
                        )
                    except:
                        pass

                    tag_prefix_field = driver.find_element(By.ID, "str_tag_pattern")
                    
                    if tag_prefix_field.is_displayed():
                        # Force enable if needed (JS)
                        driver.execute_script("arguments[0].removeAttribute('disabled');", tag_prefix_field)
                        driver.execute_script("arguments[0].removeAttribute('readonly');", tag_prefix_field)
                        
                        tag_prefix_field.clear()
                        tag_prefix_field.send_keys(tag_prefix)
                        
                        # Ensure value is set
                        driver.execute_script("arguments[0].value = arguments[1];", tag_prefix_field, tag_prefix)
                        self.log(f"✅ Filled Tag Prefix: {tag_prefix}", 'acknowledge')
                    else:
                        self.log("⚠️ Tag Prefix field found but not displayed", 'acknowledge')
                except Exception as e:
                    self.log(f"⚠️ Could not fill Tag Prefix: {str(e)}", 'acknowledge')
            
            # Auto-fill quantity and weight if enabled
            if self.auto_fill_qty_weight_var.get():
                self._auto_fill_quantity_and_weight(driver)
            else:
                self.log("ℹ️ Auto-fill quantity/weight is disabled", 'acknowledge')
            
            # Skip filling AHC Receiving Remarks - not needed
            self.log("ℹ️ Skipping AHC Receiving Remarks (not required)", 'acknowledge')
            
            # --- NEW: Extract Data and Save Job Card (BEFORE ADD CLICK) ---
            try:
                self.log("📊 Extracting request details...", 'acknowledge')
                
                # Extract Data using Hidden Inputs (Most Reliable)
                jeweller_name = "Unknown"
                item_type = ""
                purity = ""
                weight = 0.0
                pcs = 0
                request_no = request['request_no'] # Default to what we have
                
                try:
                    # 1. Jeweller Name (str_outlet_name or separate field)
                    elem = driver.find_elements(By.ID, "str_outlet_name")
                    if elem: jeweller_name = elem[0].get_attribute("value")
                    else:
                        # Fallback to Jeweller Name Span
                        elem = driver.find_elements(By.XPATH, "//span[contains(text(), 'Jeweller Name')]/following::span[1]")
                        if elem: jeweller_name = elem[0].text.strip()
                        
                    # 2. Total Weight (netweight or numweight)
                    elem = driver.find_elements(By.ID, "netweight")
                    if elem: 
                        attr_val = elem[0].get_attribute("value")
                        weight = float(attr_val) if attr_val else 0
                    else:
                        elem = driver.find_elements(By.ID, "numweight")
                        if elem:
                            attr_val = elem[0].get_attribute("value")
                            weight = float(attr_val) if attr_val else 0
                            
                    # 3. Request No (num_request_no)
                    elem = driver.find_elements(By.ID, "num_request_no")
                    if elem: request_no = elem[0].get_attribute("value")

                    # 4. Total Quantity (totQuantityjew or from table)
                    elem = driver.find_elements(By.ID, "totQuantityjew")
                    if elem:
                        attr_val = elem[0].get_attribute("value")
                        pcs = int(attr_val) if attr_val else 0
                    
                    # 5. CML No / License No (str_cml_no)
                    cml_no = ""
                    elem = driver.find_elements(By.ID, "str_cml_no")
                    if elem: cml_no = elem[0].get_attribute("value")
                    
                    # 6. Item rows (UAT + live table layouts)
                    jobs_to_save = []
                    item_types_list = []
                    jobs_to_save, item_types_list = self._extract_acknowledge_jobs_from_table(
                        driver,
                        request,
                        str(weight) if weight else '',
                        pcs,
                        purity,
                        cml_no,
                    )
                    if item_types_list:
                        item_type = ', '.join(item_types_list)
                        self.log(f"✅ Extracted {len(jobs_to_save)} Items: {item_type}", 'acknowledge')

                    # Final consolidated logging
                    self.log(f"✅ Extracted Header: {jeweller_name} | Total: {pcs} pcs | {weight}g | Lic: {cml_no}", 'acknowledge')
                    
                    if not jobs_to_save:
                        self.log("⚠️ No table rows extracted, using header totals", 'acknowledge')
                        jobs_to_save.append({
                            'request_no': request_no,
                            'job_no': '',
                            'item': item_type if item_type else 'Gold Jewellery',
                            'purity': purity,
                            'weight': weight,
                            'pcs': pcs if pcs else 1,
                            'licence_no': cml_no,
                            'material_type': 'Gold',
                            'date_of_request': datetime.now().strftime('%Y-%m-%d'),
                            'status': 'XRF',
                            'jeweller_name': request.get('jeweller_name', jeweller_name),
                        })
                    else:
                        for job in jobs_to_save:
                            if not job.get('jeweller_name'):
                                job['jeweller_name'] = request.get('jeweller_name', jeweller_name)

                except Exception as e:
                    self.log(f"col⚠️ Error using hidden fields: {e}", 'acknowledge')

                if hasattr(self, 'save_job_api_url_var') and getattr(
                    self, 'save_job_data_var', tk.BooleanVar(value=True)
                ).get():
                    self._save_acknowledge_jobs_batch(
                        jobs_to_save,
                        request.get('request_no', request_no),
                    )

            except Exception as e:
                 self.log(f"❌ Error during data extraction: {e}", 'acknowledge')

            # Step 4: Live portal uses Add; UAT/demo submits on same page
            add_button_clicked = False
            try:
                add_button = driver.find_element(By.XPATH, "//input[@type='button' and @value='Add']")
                if add_button.is_displayed() and add_button.is_enabled():
                    add_button.click()
                    self.log("✅ Clicked Add button", 'acknowledge')
                    time.sleep(1.5)
                    add_button_clicked = True
            except Exception as e:
                self.log(f"ℹ️ Add button not found (UAT uses Submit on same page): {e}", 'acknowledge')

            if not add_button_clicked:
                self.log("🔄 Submitting acknowledge on current page...", 'acknowledge')
                if self._click_acknowledge_submit_on_page(driver):
                    time.sleep(2)
                    if 'message=' not in driver.current_url:
                        self.log("✅ Acknowledge submitted on portal", 'acknowledge')
                        return True
                else:
                    self.log("❌ Could not find or click Submit button", 'acknowledge')
                    try:
                        debug_file = f"debug_acknowledge_{request['request_no']}.html"
                        with open(debug_file, 'w', encoding='utf-8') as f:
                            f.write(driver.page_source)
                        self.log(f"💾 Page source saved to {debug_file}", 'acknowledge')
                    except Exception:
                        pass
                    return False

            # Step 5: Handle redirect after Add (live portal)
            current_url = driver.current_url
            if 'message=' in current_url:
                self.log("🔄 Redirected to accept page, accepting all items...", 'acknowledge')
                
                # Wait for page to fully load
                time.sleep(1.0) 
                
                select_all_clicked = False
                
                try:
                    WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, "//th[contains(text(), 'Accept')]"))
                    )
                    select_all_checkbox = WebDriverWait(driver, 2).until(
                        EC.presence_of_element_located((By.XPATH, "//th[contains(text(), 'Accept')]//input[@type='checkbox']"))
                    )
                    if select_all_checkbox.is_displayed():
                        if not select_all_checkbox.is_selected():
                            select_all_checkbox.click()
                            time.sleep(0.3)
                            self.log("✅ Clicked 'Select All' checkbox in Accept header (Method 1)", 'acknowledge')
                            select_all_clicked = True
                        else:
                            self.log("✅ Select All checkbox already selected", 'acknowledge')
                            select_all_clicked = True
                except Exception as e:
                    self.log(f"⚠️ Method 1 failed: {str(e)}", 'acknowledge')
                
                if not select_all_clicked:
                    try:
                        tables = driver.find_elements(By.TAG_NAME, "table")
                        for table in tables:
                            try:
                                accept_header = table.find_element(By.XPATH, ".//th[contains(text(), 'Accept')]")
                                select_all_checkbox = accept_header.find_element(By.XPATH, ".//input[@type='checkbox']")
                                if select_all_checkbox.is_displayed():
                                    if not select_all_checkbox.is_selected():
                                        select_all_checkbox.click()
                                        time.sleep(0.3)  # Reduced from 1 to 0.3 seconds
                                        self.log("✅ Clicked 'Select All' checkbox (Method 2)", 'acknowledge')
                                        select_all_clicked = True
                                        break
                            except:
                                continue
                    except Exception as e:
                        self.log(f"⚠️ Method 2 failed: {str(e)}", 'acknowledge')
                
                if not select_all_clicked:
                    try:
                        select_all_checkbox = driver.find_element(By.XPATH, "//table//input[@type='checkbox'][1]")
                        if select_all_checkbox.is_displayed():
                            if not select_all_checkbox.is_selected():
                                select_all_checkbox.click()
                                time.sleep(0.3)  # Reduced from 1 to 0.3 seconds
                                self.log("✅ Clicked first checkbox in table (Method 3)", 'acknowledge')
                                select_all_clicked = True
                    except Exception as e:
                        self.log(f"⚠️ Method 3 failed: {str(e)}", 'acknowledge')
                
                if not select_all_clicked:
                    self.log("❌ Could not find or click Select All checkbox", 'acknowledge')
                
                # Step 6: Click Voucher Print with multiple methods
                voucher_clicked = False
                
                # Method 1: Try by href containing getAHCRceiptJrxmlReportVoucher
                try:
                    voucher_link = driver.find_element(By.XPATH, "//a[contains(@href, 'getAHCRceiptJrxmlReportVoucher')]")
                    if voucher_link.is_displayed():
                        voucher_link.click()
                        time.sleep(0.5)  # Reduced from 2 to 0.5 seconds
                        self.log("✅ Clicked Voucher Print link (Method 1)", 'acknowledge')
                        voucher_clicked = True
                except Exception as e:
                    self.log(f"⚠️ Voucher Method 1 failed: {str(e)}", 'acknowledge')
                
                # Method 2: Try by text containing "Voucher Print"
                if not voucher_clicked:
                    try:
                        voucher_link = driver.find_element(By.XPATH, "//a[contains(text(), 'Voucher Print')]")
                        if voucher_link.is_displayed():
                            voucher_link.click()
                            time.sleep(0.5)  # Reduced from 2 to 0.5 seconds
                            self.log("✅ Clicked Voucher Print link (Method 2)", 'acknowledge')
                            voucher_clicked = True
                    except Exception as e:
                        self.log(f"⚠️ Voucher Method 2 failed: {str(e)}", 'acknowledge')
                
                # Method 3: Try by button with Voucher Print text
                if not voucher_clicked:
                    try:
                        voucher_button = driver.find_element(By.XPATH, "//input[@type='button' and contains(@value, 'Voucher')]")
                        if voucher_button.is_displayed():
                            voucher_button.click()
                            time.sleep(0.5)  # Reduced from 2 to 0.5 seconds
                            self.log("✅ Clicked Voucher Print button (Method 3)", 'acknowledge')
                            voucher_clicked = True
                    except Exception as e:
                        self.log(f"⚠️ Voucher Method 3 failed: {str(e)}", 'acknowledge')
                
                # Method 4: Try by any element containing "Voucher"
                if not voucher_clicked:
                    try:
                        voucher_element = driver.find_element(By.XPATH, "//*[contains(text(), 'Voucher') and contains(text(), 'Print')]")
                        if voucher_element.is_displayed():
                            voucher_element.click()
                            time.sleep(0.5)  # Reduced from 2 to 0.5 seconds
                            self.log("✅ Clicked Voucher Print element (Method 4)", 'acknowledge')
                            voucher_clicked = True
                    except Exception as e:
                        self.log(f"⚠️ Voucher Method 4 failed: {str(e)}", 'acknowledge')
                
                if not voucher_clicked:
                    self.log("❌ Could not find or click Voucher Print", 'acknowledge')
                else:
                    self.log("✅ Clicked Voucher Print - PDF will download in background", 'acknowledge')
                
                # Step 7: Click Submit with multiple methods
                submit_clicked = False
                
                # Method 1: Try by value="Submit"
                try:
                    submit_button = driver.find_element(By.XPATH, "//input[@type='button' and @value='Submit']")
                    if submit_button.is_displayed() and submit_button.is_enabled():
                        submit_button.click()
                        time.sleep(0.5)  # Reduced from 2 to 0.5 seconds
                        self.log("✅ Clicked Submit button (Method 1)", 'acknowledge')
                        submit_clicked = True
                except Exception as e:
                    self.log(f"⚠️ Submit Method 1 failed: {str(e)}", 'acknowledge')
                
                # Method 2: Try by text containing "Submit"
                if not submit_clicked:
                    try:
                        submit_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Submit')]")
                        if submit_button.is_displayed():
                            submit_button.click()
                            time.sleep(0.5)  # Reduced from 2 to 0.5 seconds
                            self.log("✅ Clicked Submit button (Method 2)", 'acknowledge')
                            submit_clicked = True
                    except Exception as e:
                        self.log(f"⚠️ Submit Method 2 failed: {str(e)}", 'acknowledge')
                
                # Method 3: Try by any element with Submit text
                if not submit_clicked:
                    try:
                        submit_element = driver.find_element(By.XPATH, "//*[contains(text(), 'Submit')]")
                        if submit_element.is_displayed():
                            submit_element.click()
                            time.sleep(0.5)  # Reduced from 2 to 0.5 seconds
                            self.log("✅ Clicked Submit element (Method 3)", 'acknowledge')
                            submit_clicked = True
                    except Exception as e:
                        self.log(f"⚠️ Submit Method 3 failed: {str(e)}", 'acknowledge')
                
                if not submit_clicked:
                    self.log("❌ Could not find or click Submit button", 'acknowledge')
                    return False
                
                # Handle any confirmation dialogs
                try:
                    alert = driver.switch_to.alert
                    alert_text = alert.text
                    self.log(f"🔔 Alert: {alert_text}", 'acknowledge')
                    alert.accept()
                    time.sleep(1)
                except:
                    pass
                    
                return True
            else:
                self.log("⚠️ Add clicked but redirect did not occur — trying Submit on page", 'acknowledge')
                if self._click_acknowledge_submit_on_page(driver):
                    return True
                return False
                
        except Exception as e:
            self.log(f"❌ Error in acknowledge workflow: {str(e)}", 'acknowledge')
            return False
            
    def _auto_fill_quantity_and_weight(self, driver=None):
        """Auto-fill quantity and weight fields from declaration table"""
        if not driver:
            driver = self.driver
        if not driver:
            return

        try:
            self.log("🔄 Auto-filling quantity and weight...", 'acknowledge')
            
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
                            self.log("📊 Found item declaration table", 'acknowledge')
                            col = self._map_acknowledge_table_columns(header_texts)
                            filled_count = 0
                            for row in rows[1:]:
                                cells = row.find_elements(By.TAG_NAME, "td")
                                if len(cells) < 4:
                                    continue
                                try:
                                    declared_qty = (
                                        self._cell_text_or_input(cells[col['qty']])
                                        if 'qty' in col else ''
                                    )
                                    wcol = col.get('declared_weight', col.get('weight'))
                                    declared_weight = (
                                        self._cell_text_or_input(cells[wcol])
                                        if wcol is not None else ''
                                    )
                                    try:
                                        qty_val = int(float(declared_qty)) if declared_qty else 0
                                        wt_val = float(declared_weight) if declared_weight else 0
                                    except (ValueError, TypeError):
                                        qty_val, wt_val = 0, 0
                                    if qty_val <= 0 and wt_val <= 0:
                                        continue
                                    for cell in cells:
                                        try:
                                            for inp in cell.find_elements(By.TAG_NAME, 'input'):
                                                cls = inp.get_attribute('class') or ''
                                                if 'recquantity' in cls and declared_qty:
                                                    self._portal_set_input_value(
                                                        driver, inp, declared_qty
                                                    )
                                                if 'totItemCatgWeight' in cls and declared_weight:
                                                    self._portal_set_input_value(
                                                        driver, inp, declared_weight
                                                    )
                                        except Exception:
                                            continue
                                    filled_count += 1
                                except Exception:
                                    continue
                            if filled_count:
                                self.log(f"✅ Auto-filled {filled_count} table row(s)", 'acknowledge')
                                self._sync_observed_net_totals(driver)
                            self._fill_uat_article_weights(driver)
                            self._sync_observed_net_totals(driver)
                            break
                            
                except Exception as e:
                    continue
            
            # Also fill the main observed weight and quantity fields
            try:
                # Observed Net Weight AHC (Fixed selector)
                try:
                    observed_weight_field = driver.find_element(By.ID, "observed_weight_ahc")
                except:
                    # Try by Name if ID fails
                    observed_weight_field = driver.find_element(By.NAME, "observed_weight_ahc")
                    
                if observed_weight_field.is_displayed(): # field might be read-only but script fills it? 
                    # Actually html says readonly="readonly". 
                    # If it's readonly, we might need to remove readonly attribute or it might be auto-calculated?
                    # But the User Request said "Error filling main fields... no such element... [name="observedNetWeightAHC"]"
                    # So the code was trying to find it by name observedNetWeightAHC.
                    
                    self._sync_observed_net_totals(driver)
                    total_weight = self._get_total_weight_from_table(driver)
                    if total_weight:
                        self._portal_set_input_value(
                            driver, observed_weight_field, total_weight
                        )
                        self.log(f"✅ Auto-filled Observed Net Weight: {total_weight}", 'acknowledge')
                
                # Observed Net Quantity (Fixed selector)
                try:
                    total_qty_field = driver.find_element(By.ID, "total_net_quantity")
                except:
                    total_qty_field = driver.find_element(By.NAME, "total_net_quantity")
                    
                if total_qty_field.is_displayed():
                     # Get total qty
                    total_qty = self._get_total_quantity_from_table(driver)
                    if total_qty:
                        self._portal_set_input_value(driver, total_qty_field, total_qty)
                        self.log(f"✅ Auto-filled Observed Quantity: {total_qty}", 'acknowledge')

            except Exception as e:
                self.log(f"⚠️ Error filling main fields: {str(e)}", 'acknowledge')
                
        except Exception as e:
            self.log(f"❌ Error in auto-fill quantity and weight: {str(e)}", 'acknowledge')
            
    def _get_total_weight_from_table(self, driver):
        """Get total weight from item rows (.totItemCatgWeight) or declared weight column."""
        try:
            total = 0.0
            for inp in driver.find_elements(By.CSS_SELECTOR, 'input.totItemCatgWeight'):
                try:
                    if inp.is_displayed():
                        v = float((inp.get_attribute('value') or '0').strip() or 0)
                        total += v
                except (ValueError, TypeError):
                    continue
            if total > 0:
                return f"{total:.3f}".rstrip('0').rstrip('.') if total != int(total) else str(int(total))

            tables = driver.find_elements(By.TAG_NAME, "table")
            for table in tables:
                try:
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    if len(rows) <= 1:
                        continue
                    header_cells = rows[0].find_elements(By.XPATH, './th|./td')
                    header_texts = [c.text.strip() for c in header_cells]
                    if not any('item category' in (h or '').lower() for h in header_texts):
                        continue
                    col = self._map_acknowledge_table_columns(header_texts)
                    wcol = col.get('declared_weight', col.get('weight'))
                    if wcol is None:
                        continue
                    for row in rows[1:]:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) <= wcol:
                            continue
                        wt_text = self._cell_text_or_input(cells[wcol])
                        try:
                            total += float(wt_text) if wt_text else 0
                        except (ValueError, TypeError):
                            continue
                    if total > 0:
                        return f"{total:.3f}".rstrip('0').rstrip('.')
                except Exception:
                    continue
            return None
        except Exception:
            return None
            
    def _get_total_quantity_from_table(self, driver):
        """Get total quantity from the item declaration table"""
        try:
            tables = driver.find_elements(By.TAG_NAME, "table")
            
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
        self.notebook.add(generate_frame, text="📝 Generate Request")
        
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
        controls_card = ttk.LabelFrame(parent, text="🎮 Controls", style='Compact.TLabelframe')
        controls_card.pack(fill='x', pady=(0, 8))
        
        controls_frame = ttk.Frame(controls_card)
        controls_frame.pack(fill='x', padx=8, pady=8)
        
        # Fetch Orders button
        self.fetch_orders_btn = ttk.Button(controls_frame, text="📋 Fetch Orders", 
                                         style='Info.TButton', command=self.fetch_order_list)
        self.fetch_orders_btn.pack(fill='x', pady=2)
        
        # Auto Generate All button
        self.auto_generate_all_btn = ttk.Button(controls_frame, text="🤖 Auto Generate All", 
                                              style='Success.TButton', command=self.auto_generate_all_requests,
                                              state='disabled')
        self.auto_generate_all_btn.pack(fill='x', pady=2)
        
        # Clear List button
        self.clear_orders_btn = ttk.Button(controls_frame, text="🧹 Clear List", 
                                         style='Danger.TButton', command=self.clear_order_list)
        self.clear_orders_btn.pack(fill='x', pady=2)
        
        # Settings card
        settings_card = ttk.LabelFrame(parent, text="⚙️ Generate Settings", style='Compact.TLabelframe')
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
        status_card = ttk.LabelFrame(parent, text="📊 Status", style='Compact.TLabelframe')
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
        log_card = ttk.LabelFrame(parent, text="📝 Generate Log", style='Compact.TLabelframe')
        log_card.pack(fill='both', expand=True)
        
        self.generate_log = scrolledtext.ScrolledText(log_card, height=8, font=('Consolas', 7), 
                                                    bg='#f8f9fa', fg='#495057', wrap=tk.WORD)
        self.generate_log.pack(fill='both', expand=True, padx=8, pady=8)
        
    def setup_generate_request_right_section(self, parent):
        """Setup right section with order list table"""
        
        # Order List card
        list_card = ttk.LabelFrame(parent, text="📋 Order List", style='Compact.TLabelframe')
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
        # Check license before API operations
        if not self.check_license_before_action("order list fetching"):
            return
            
        if not self.driver or not self.logged_in:
            messagebox.showwarning("Not Ready", "Please open browser and login first")
            return
            
        self.log("🔍 Fetching order list...", 'generate')
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
                
                # Log without exposing full URL (it may contain sensitive params)
                base_url = orders_api_url.split('?')[0] if '?' in orders_api_url else orders_api_url
                self.log(f"🌐 Fetching orders from: {base_url}", 'generate')
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
                                self.log(f"⚠️ Error formatting order: {str(e)}", 'generate')
                                continue
                        
                        # Update UI with order data
                        self.root.after(0, self._update_order_list_ui, formatted_orders)
                        
                        loading_dialog.update_status("Done!")
                        loading_dialog.update_message(f"Found {len(formatted_orders)} orders")
                        time.sleep(1)
                        loading_dialog.close()
                        
                        if formatted_orders:
                            self.log(f"✅ Successfully fetched {len(formatted_orders)} orders", 'generate')
                            messagebox.showinfo("Success", f"✅ Found {len(formatted_orders)} orders to generate!")
                        else:
                            self.log("⚠️ No orders found to generate", 'generate')
                            messagebox.showwarning("No Orders", "No orders found to generate")
                            
                    except ValueError:
                        self.log("❌ Invalid JSON response from API", 'generate')
                        messagebox.showerror("API Error", "Invalid response format from API")
                else:
                    self.log(f"❌ API Error: Status {response.status_code}", 'generate')
                    messagebox.showerror("API Error", f"Server returned status code {response.status_code}")
                    
            except requests.exceptions.Timeout:
                self.log("⏱️ Request timeout - API took too long to respond", 'generate')
                messagebox.showerror("Timeout", "Request timeout - API took too long to respond")
            except requests.exceptions.ConnectionError:
                self.log("🌐 Connection error - Check internet connection", 'generate')
                messagebox.showerror("Connection Error", "Could not connect to API - Check internet connection")
            except Exception as e:
                self.log(f"❌ API Error: {str(e)}", 'generate')
                messagebox.showerror("API Error", f"Error fetching orders: {str(e)}")
                
        except Exception as e:
            if loading_dialog:
                loading_dialog.close()
            self.log(f"❌ Error fetching order list: {str(e)}", 'generate')
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
                "🔄 Generate"
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
        
        self.log("🧹 Order list cleared", 'generate')
        
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
        # Check license before automation
        if not self.check_license_before_action("order automation"):
            return
            
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
                        self.log(f"✅ Generated request for order {order['order_no']}", 'generate')
                    else:
                        failed += 1
                        self.log(f"❌ Failed to generate request for order {order['order_no']}", 'generate')
                        
                except Exception as e:
                    failed += 1
                    self.log(f"❌ Error generating request for order {order['order_no']}: {str(e)}", 'generate')
                
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
                              f"✅ Completed: {completed}\n❌ Failed: {failed}")
            
            # Refresh the order list
            self.fetch_order_list()
            
        except Exception as e:
            if loading_dialog:
                loading_dialog.close()
            self.log(f"❌ Error in auto generate: {str(e)}", 'generate')
            messagebox.showerror("Error", f"Error in auto generate: {str(e)}")
            
    def _generate_single_request(self, order):
        """Generate a single request (for manual generate)"""
        try:
            success = self._generate_single_request_internal(order)
            
            if success:
                self.log(f"✅ Successfully generated request for order {order['order_no']}", 'generate')
                messagebox.showinfo("Success", f"✅ Request generated successfully for order {order['order_no']}!")
            else:
                self.log(f"❌ Failed to generate request for order {order['order_no']}", 'generate')
                messagebox.showerror("Error", f"❌ Failed to generate request for order {order['order_no']}")
                
        except Exception as e:
            self.log(f"❌ Error generating request for order {order['order_no']}: {str(e)}", 'generate')
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
                        self.log(f"✅ Found {log_prefix} container with selector: {selector}", 'generate')
                        break
                except:
                    continue
            
            if not container:
                self.log(f"⚠️ Could not find {log_prefix} container", 'generate')
                return False
            
            # Scroll to and click the container
            self.driver.execute_script("arguments[0].scrollIntoView(true);", container)
            time.sleep(0.5)
            
            try:
                container.click()
            except:
                self.driver.execute_script("arguments[0].click();", container)
            
            time.sleep(1)
            self.log(f"✅ Clicked {log_prefix} container", 'generate')
            
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
                    self.log(f"✅ Typed {log_prefix} value: {search_value}", 'generate')
                    
                    # Wait for options and select
                    try:
                        WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".select2-results li"))
                        )
                        
                        options = self.driver.find_elements(By.CSS_SELECTOR, ".select2-results li")
                        self.log(f"📋 Found {len(options)} {log_prefix} options", 'generate')
                        
                        # Try to find exact match first
                        selected = False
                        for option in options:
                            if search_value.lower() in option.text.lower():
                                option.click()
                                time.sleep(1)
                                self.log(f"✅ Selected exact {log_prefix} match: {option.text}", 'generate')
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
                                    self.log(f"✅ Selected partial {log_prefix} match: {option.text}", 'generate')
                                    selected = True
                                    break
                        
                        # If still no match, select first option
                        if not selected and options:
                            options[0].click()
                            time.sleep(1)
                            self.log(f"✅ Selected first available {log_prefix}: {options[0].text}", 'generate')
                            selected = True
                        
                        return selected
                        
                    except Exception as e:
                        self.log(f"⚠️ Could not select {log_prefix} option: {str(e)}", 'generate')
                        return False
                else:
                    self.log(f"⚠️ {log_prefix} search input not interactable", 'generate')
                    return False
            except Exception as e:
                self.log(f"⚠️ Could not find {log_prefix} search input: {str(e)}", 'generate')
                return False
                
        except Exception as e:
            self.log(f"⚠️ Could not select {log_prefix}: {str(e)}", 'generate')
            return False

    def _generate_single_request_internal(self, order):
        """Internal method to generate a single request - delegated to RequestGenerator"""
        if RequestGenerator:
            # Get generate URL from settings if available
            generate_url = None
            try:
                if hasattr(self, 'settings') and isinstance(self.settings, dict):
                    generate_url = self.settings.get('portal_generate_url')
            except:
                pass
                
            generator = RequestGenerator(
                self.driver, 
                self.log, 
                self.default_state_var, 
                self.auto_fill_item_details_var,
                generate_url=generate_url
            )
            return generator.generate_single_request_internal(order)
        else:
            self.log("❌ RequestGenerator module not available", 'generate')
            return False

    def _select_lot_in_portal(self, lot_no):
        """Helper method to select lot in portal with proper clearing"""
        try:
            # First, clear any existing selection
            self.log(f"🔄 Clearing previous lot selection for Lot {lot_no}...", 'weight')
            try:
                # Clear Select2 container
                select2_container = self.driver.find_element(By.ID, "s2id_lotno")
                # Click to open dropdown
                select2_container.click()
                time.sleep(0.5)
                # Look for clear/remove button in Select2
                clear_buttons = self.driver.find_elements(By.CSS_SELECTOR, ".select2-selection__clear")
                if clear_buttons:
                    clear_buttons[0].click()
                    time.sleep(0.5)
                    self.log("✅ Cleared previous Select2 selection", 'weight')
            except Exception as clear_error:
                self.log(f"⚠️ Could not clear Select2 selection: {str(clear_error)}", 'weight')
            
            # Now select the new lot
            select2_container = self.driver.find_element(By.ID, "s2id_lotno")
            select2_container.click()
            time.sleep(0.5)
            options = self.driver.find_elements(By.CSS_SELECTOR, "ul.select2-results li")
            found = False
            for option in options:
                if option.text.strip().endswith(f"Lot {lot_no}") or option.text.strip() == f"Lot {lot_no}":
                    option.click()
                    found = True
                    self.log(f"✅ Selected Lot {lot_no} in portal via Select2", 'weight')
                    break
            if not found:
                raise Exception(f"Lot {lot_no} not found in Select2 options")
            time.sleep(1)
            lot_dropdown = self.driver.find_element(By.ID, "lotno")
            selected_value = lot_dropdown.get_attribute('value')
            if selected_value != str(lot_no):
                self.log(f"⚠️ Lot selection verification failed: expected {lot_no}, got {selected_value}", 'weight')
                return False
            else:
                self.log(f"✅ Lot selection verified: {selected_value}", 'weight')
                return True
        except Exception as select2_error:
            self.log(f"⚠️ Select2 lot selection failed: {str(select2_error)}. Trying fallback methods...", 'weight')
            try:
                wait = WebDriverWait(self.driver, 10)
                lot_dropdown = wait.until(EC.presence_of_element_located((By.ID, "lotno")))
                if not lot_dropdown.is_displayed() or not lot_dropdown.is_enabled():
                    self.driver.execute_script("arguments[0].style.display = 'block'; arguments[0].removeAttribute('readonly');", lot_dropdown)
                    time.sleep(0.5)
                
                # Clear the dropdown first
                self.driver.execute_script("arguments[0].value = '';", lot_dropdown)
                time.sleep(0.2)
                
                # Try to clear any existing selection
                try:
                    from selenium.webdriver.support.select import Select
                    select_element = Select(lot_dropdown)
                    # Deselect all options first
                    select_element.deselect_all()
                    time.sleep(0.2)
                except:
                    pass
                
                # Now select the new lot
                select_element = Select(lot_dropdown)
                select_element.select_by_value(lot_no)
                self.log(f"✅ Selected Lot {lot_no} in portal via Select fallback", 'weight')
                time.sleep(1)
                return True
            except Exception as fallback_error:
                self.log(f"❌ Could not select lot in portal: {str(fallback_error)}", 'weight')
                return False

    def _get_current_lot_selection(self):
        """Helper method to get the correct lot selection based on priority"""
        if hasattr(self, 'current_lot_no') and self.current_lot_no:
            return str(self.current_lot_no)
        elif hasattr(self, 'lot_var') and self.lot_var.get():
            return str(self.lot_var.get())
        else:
            return str(self.manual_lot_var.get())

    def clear_license(self):
        """Clear license and reset to trial mode"""
        if not self.license_manager:
            messagebox.showwarning("License Manager", "Device licensing is not enabled.")
            return
        
        response = messagebox.askyesno("Clear License", 
                                     "Are you sure you want to clear the current license?\n\n"
                                     "This will reset to trial mode and clear all cached license information.")
        if response:
            try:
                # Clear license cache
                self.license_manager.clear_cache()
                
                # Clear portal credentials
                if hasattr(self, 'portal_username_var'):
                    self.portal_username_var.set('')
                if hasattr(self, 'portal_password_var'):
                    self.portal_password_var.set('')
                
                # Reset license status
                self.license_verified = False
                self.license_status_label.config(text="⏳ Not Verified", foreground='#ffc107')
                
                # Stop periodic verification
                self.license_manager.stop_periodic_verification()
                
                messagebox.showinfo("License Cleared", "✅ License cleared successfully!\n\n"
                                   "You can now verify with new portal credentials or use trial mode.")
                self.log("🗑️ License cleared successfully", 'status')
                
            except Exception as e:
                messagebox.showerror("Error", f"Error clearing license: {str(e)}")
                self.log(f"❌ Error clearing license: {str(e)}", 'status')

    def calculate_deltas(self):
        """Calculate individual deltas and average delta from C1 and C2 values"""
        try:
            # Get C1 values
            c1_initial = self.weight_entries.get('num_strip_weight_goldM11', None)
            c1_m2 = self.weight_entries.get('num_cornet_weight_goldM11', None)
            
            # Get C2 values
            c2_initial = self.weight_entries.get('num_strip_weight_goldM12', None)
            c2_m2 = self.weight_entries.get('num_cornet_weight_goldM12', None)
            
            if not all([c1_initial, c1_m2, c2_initial, c2_m2]):
                return
            
            # Get values and convert to float
            try:
                c1_init_val = float((c1_initial.get() if c1_initial else "0").strip() or 0)
                c1_m2_val = float((c1_m2.get() if c1_m2 else "0").strip() or 0)
                c2_init_val = float((c2_initial.get() if c2_initial else "0").strip() or 0)
                c2_m2_val = float((c2_m2.get() if c2_m2 else "0").strip() or 0)
            except ValueError:
                return
            
            # Calculate individual deltas
            c1_delta = c1_init_val - c1_m2_val
            c2_delta = c2_init_val - c2_m2_val
            
            # Calculate average delta
            avg_delta = (c1_delta + c2_delta) / 2
            
            # Update displays
            self.c1_initial_display.config(text=f"{c1_init_val:.3f}")
            self.c1_m2_display.config(text=f"{c1_m2_val:.3f}")
            self.c1_delta_display.config(text=f"{c1_delta:.3f}")
            
            self.c2_initial_display.config(text=f"{c2_init_val:.3f}")
            self.c2_m2_display.config(text=f"{c2_m2_val:.3f}")
            self.c2_delta_display.config(text=f"{c2_delta:.3f}")
            
            self.avg_delta_display.config(text=f"{avg_delta:.3f}")
            
            # Update status
            self.delta_status_label.config(text="✅ Deltas calculated successfully", fg='#28a745')
            
            # Log the calculations
            self.log(f"🧮 Delta Calculations: C1={c1_delta:.3f}, C2={c2_delta:.3f}, Avg={avg_delta:.3f}", 'weight')
            
        except Exception as e:
            self.log(f"❌ Error calculating deltas: {str(e)}", 'weight')
            self.delta_status_label.config(text="❌ Calculation error", fg='#dc3545')
    
    def bind_delta_calculations(self):
        """Bind entry fields to automatically calculate deltas when values change"""
        try:
            # Fields that should trigger delta calculations
            delta_fields = [
                'num_strip_weight_goldM11',  # C1 Initial
                'num_cornet_weight_goldM11', # C1 M2
                'num_strip_weight_goldM12',  # C2 Initial
                'num_cornet_weight_goldM12'  # C2 M2
            ]
            
            for field_id in delta_fields:
                if field_id in self.weight_entries:
                    entry = self.weight_entries[field_id]
                    # Bind to key release and focus out for real-time updates
                    entry.bind('<KeyRelease>', lambda e: self.calculate_deltas())
                    entry.bind('<FocusOut>', lambda e: self.calculate_deltas())
                    entry.bind('<Return>', lambda e: self.calculate_deltas())
                    
            self.log("🔗 Delta calculation bindings added", 'weight')
            
        except Exception as e:
            self.log(f"❌ Error binding delta calculations: {str(e)}", 'weight')
            
    def calculate_all_fineness(self):
        """Calculate fineness for all strips and determine pass/fail based on average delta and purity threshold"""
        try:
            # Get purity threshold
            purity_threshold = float(self.purity_threshold_var.get() or 91.6)
            
            # First, ensure we have the average delta from C1/C2 calculations
            if not hasattr(self, 'avg_delta_display') or self.avg_delta_display.cget('text') == "0.000":
                self.log("⚠️ Please calculate deltas first (C1 and C2 values)", 'weight')
                self.delta_status_label.config(text="⚠️ Calculate deltas first", fg='#ffc107')
                return
            
            # Get the average delta value
            avg_delta_text = self.avg_delta_display.cget('text')
            try:
                avg_delta = float(avg_delta_text)
            except ValueError:
                self.log("⚠️ Invalid average delta value", 'weight')
                return
            
            # Get initial weights for delta-corrected calculations
            strip1_initial = self.get_field_value('num_strip_weight_M11')
            strip2_initial = self.get_field_value('num_strip_weight_M12')
            
            # Calculate fineness for Strip 1 using delta correction
            strip1_fineness = self.calculate_fineness_with_delta_correction(
                strip1_initial, 
                self.get_field_value('num_cornet_weightM11'), 
                avg_delta
            )
            
            # Calculate fineness for Strip 2 using delta correction
            strip2_fineness = self.calculate_fineness_with_delta_correction(
                strip2_initial, 
                self.get_field_value('num_cornet_weightM12'), 
                avg_delta
            )
            
            if strip1_fineness is not None and strip2_fineness is not None:
                # Calculate mean fineness
                mean_fineness = (strip1_fineness + strip2_fineness) / 2
                
                # Calculate fineness variation
                fineness_variation = abs(strip1_fineness - strip2_fineness)
                
                                # Determine pass/fail based on JavaScript logic and average delta
                if fineness_variation > 4.0:
                    pass_fail = "REPEAT"
                    result_color = "#ffc107"  # Yellow for REPEAT
                    result_icon = "🔄"
                    reason = f"Variation {fineness_variation:.3f} > 4.0 ppt"
                else:
                    # Check if individual strip fineness is below purity threshold
                    strip1_below_threshold = strip1_fineness < purity_threshold
                    strip2_below_threshold = strip2_fineness < purity_threshold
                    
                    if strip1_below_threshold or strip2_below_threshold:
                        pass_fail = "FAIL"
                        result_color = "#dc3545"  # Red for FAIL
                        result_icon = "❌"
                        reason = f"Strip fineness below threshold {purity_threshold}"
                    elif mean_fineness >= (purity_threshold + 0.1):
                        pass_fail = "PASS"
                        result_color = "#28a745"  # Green for PASS
                        result_icon = "✅"
                        reason = f"Mean {mean_fineness:.3f} ≥ {purity_threshold + 0.1}"
                    else:
                        pass_fail = "FAIL"
                        result_color = "#dc3545"  # Red for FAIL
                        result_icon = "❌"
                        reason = f"Mean {mean_fineness:.3f} < {purity_threshold + 0.1}"
                
                # Update the fineness fields in the table
                self.update_fineness_fields(strip1_fineness, strip2_fineness, mean_fineness, pass_fail, result_color, result_icon, fineness_variation)
                
                # Log results with average delta context
                self.log(f"🧮 Fineness Calculations (Avg Delta: {avg_delta:.3f}):", 'weight')
                self.log(f"   Strip 1: {strip1_fineness:.3f}", 'weight')
                self.log(f"   Strip 2: {strip2_fineness:.3f}", 'weight')
                self.log(f"   Mean: {mean_fineness:.3f}", 'weight')
                self.log(f"   Variation: {fineness_variation:.3f} ppt", 'weight')
                self.log(f"   Result: {pass_fail} {result_icon} - {reason}", 'weight')
                
                # Update status
                self.delta_status_label.config(text=f"✅ Fineness calculated: {pass_fail} (Δ{avg_delta:.3f})", fg=result_color)
                
            else:
                self.log("⚠️ Cannot calculate fineness - missing initial or cornet weights", 'weight')
                self.delta_status_label.config(text="⚠️ Missing weights for fineness calculation", fg='#ffc107')
                
        except Exception as e:
            self.log(f"❌ Error calculating fineness: {str(e)}", 'weight')
            self.delta_status_label.config(text="❌ Fineness calculation error", fg='#dc3545')
    
    def calculate_theoretical_fineness_from_delta(self, initial_weight, avg_delta):
        """Calculate theoretical fineness based on average delta: F = (Initial - AvgDelta) / Initial × 1000"""
        try:
            if initial_weight <= 0:
                return None
            
            # Theoretical fineness calculation based on average delta
            theoretical_fineness = ((initial_weight - avg_delta) / initial_weight) * 1000
            return theoretical_fineness
            
        except (ValueError, ZeroDivisionError):
            return None
    
    def calculate_fineness_with_delta_correction(self, initial_weight, cornet_weight, avg_delta):
        """Calculate fineness with delta correction: F = (Cornet + AvgDelta) / Initial × 1000"""
        try:
            if initial_weight <= 0:
                return None
            
            # Corrected fineness calculation using average delta
            corrected_fineness = ((cornet_weight + avg_delta) / initial_weight) * 1000
            return corrected_fineness
            
        except (ValueError, ZeroDivisionError):
            return None
    
    def calculate_strip_fineness(self, initial_field, cornet_field):
        """Calculate fineness for a single strip: (Cornet / Initial) × 1000"""
        try:
            initial_entry = self.weight_entries.get(initial_field)
            cornet_entry = self.weight_entries.get(cornet_field)
            
            if not initial_entry or not cornet_entry:
                return None
                
            initial_weight = initial_entry.get().strip()
            cornet_weight = cornet_entry.get().strip()
            
            if not initial_weight or not cornet_weight:
                return None
                
            initial_val = float(initial_weight)
            cornet_val = float(cornet_weight)
            
            if initial_val <= 0:
                return None
                
            # Calculate fineness: (Cornet / Initial) × 1000
            fineness = (cornet_val / initial_val) * 1000
            return fineness
            
        except (ValueError, ZeroDivisionError):
            return None
    
    def get_field_value(self, field_id):
        """Get numeric value from a field, returns 0 if empty or invalid"""
        try:
            if field_id in self.weight_entries:
                value = self.weight_entries[field_id].get().strip()
                return float(value) if value else 0.0
            return 0.0
        except (ValueError, TypeError):
            return 0.0
    
    def update_fineness_fields(self, strip1_fineness, strip2_fineness, mean_fineness, pass_fail, result_color, result_icon, fineness_variation):
        """Update all fineness-related fields in the table"""
        try:
            # Get purity threshold for individual strip validation
            purity_threshold = float(self.purity_threshold_var.get() or 91.6)
            
            # Update Strip 1 fineness with color coding
            if 'num_fineness_reportM11' in self.weight_entries:
                self.weight_entries['num_fineness_reportM11'].delete(0, tk.END)
                self.weight_entries['num_fineness_reportM11'].insert(0, f"{strip1_fineness:.3f}")
                
                # Color code based on individual strip fineness
                if strip1_fineness < purity_threshold:
                    self.weight_entries['num_fineness_reportM11'].configure(style='Danger.TEntry')  # Red for FAIL
                else:
                    self.weight_entries['num_fineness_reportM11'].configure(style='Success.TEntry')  # Green for PASS
            
            # Update Strip 2 fineness with color coding
            if 'num_fineness_report_goldM11' in self.weight_entries:
                self.weight_entries['num_fineness_report_goldM11'].delete(0, tk.END)
                self.weight_entries['num_fineness_report_goldM11'].insert(0, f"{strip2_fineness:.3f}")
                
                # Color code based on individual strip fineness
                if strip2_fineness < purity_threshold:
                    self.weight_entries['num_fineness_report_goldM11'].configure(style='Danger.TEntry')  # Red for FAIL
                else:
                    self.weight_entries['num_fineness_report_goldM11'].configure(style='Success.TEntry')  # Green for PASS
            
            # Update Mean Fineness for Strip 1
            if 'num_mean_finenessM11' in self.weight_entries:
                self.weight_entries['num_mean_finenessM11'].delete(0, tk.END)
                self.weight_entries['num_mean_finenessM11'].insert(0, f"{mean_fineness:.3f}")
                self.weight_entries['num_mean_finenessM11'].configure(style='Success.TEntry')
            
            # Update Remarks for Strip 1
            if 'str_remarksM11' in self.weight_entries:
                self.weight_entries['str_remarksM11'].delete(0, tk.END)
                self.weight_entries['str_remarksM11'].insert(0, pass_fail)
                self.weight_entries['str_remarksM11'].configure(style='Success.TEntry')
            
            # Update Remarks for Strip 2
            if 'str_remarksM12' in self.weight_entries:
                self.weight_entries['str_remarksM12'].delete(0, tk.END)
                self.weight_entries['str_remarksM12'].insert(0, pass_fail)
                self.weight_entries['str_remarksM12'].configure(style='Success.TEntry')
            
            # Add fineness variation info to remarks if > 4.0
            if fineness_variation > 4.0:
                if 'str_remarksM11' in self.weight_entries:
                    current_remark = self.weight_entries['str_remarksM11'].get()
                    variation_info = f" (Δ{fineness_variation:.3f} ppt)"
                    if variation_info not in current_remark:
                        self.weight_entries['str_remarksM11'].insert(tk.END, variation_info)
                
                if 'str_remarksM12' in self.weight_entries:
                    current_remark = self.weight_entries['str_remarksM12'].get()
                    variation_info = f" (Δ{fineness_variation:.3f} ppt)"
                    if variation_info not in current_remark:
                        self.weight_entries['str_remarksM12'].insert(tk.END, variation_info)
            
            # Update delta fields to show calculated deltas
            if 'averagedelta1' in self.weight_entries:
                # Calculate delta for Strip 1
                strip1_initial = self.weight_entries.get('num_strip_weight_M11')
                strip1_cornet = self.weight_entries.get('num_cornet_weightM11')
                if strip1_initial and strip1_cornet:
                    try:
                        initial_val = float(strip1_initial.get().strip() or 0)
                        cornet_val = float(strip1_cornet.get().strip() or 0)
                        delta = initial_val - cornet_val
                        self.weight_entries['averagedelta1'].delete(0, tk.END)
                        self.weight_entries['averagedelta1'].insert(0, f"{delta:.3f}")
                        self.weight_entries['averagedelta1'].configure(style='Success.TEntry')
                    except ValueError:
                        pass
            
            # Update delta for Strip 2 (if it exists)
            if 'delta12' in self.weight_entries:
                strip2_initial = self.weight_entries.get('num_strip_weight_M12')
                strip2_cornet = self.weight_entries.get('num_cornet_weightM12')
                if strip2_initial and strip2_cornet:
                    try:
                        initial_val = float(strip2_initial.get().strip() or 0)
                        cornet_val = float(strip2_cornet.get().strip() or 0)
                        delta = initial_val - cornet_val
                        self.weight_entries['delta12'].delete(0, tk.END)
                        self.weight_entries['delta12'].insert(0, f"{delta:.3f}")
                        self.weight_entries['delta12'].configure(style='Success.TEntry')
                    except ValueError:
                        pass
                        
        except Exception as e:
            self.log(f"❌ Error updating fineness fields: {str(e)}", 'weight')
    
    def bind_fineness_calculations(self):
        """Bind entry fields to automatically calculate fineness when values change"""
        try:
            # Fields that should trigger fineness calculations
            fineness_fields = [
                'num_strip_weight_M11',    # Strip 1 Initial
                'num_cornet_weightM11',    # Strip 1 Cornet
                'num_strip_weight_M12',    # Strip 2 Initial
                'num_cornet_weightM12',    # Strip 2 Cornet
            ]
            
            for field_id in fineness_fields:
                if field_id in self.weight_entries:
                    entry = self.weight_entries[field_id]
                    # Bind to key release and focus out for real-time updates
                    entry.bind('<KeyRelease>', lambda e: self.calculate_all_fineness())
                    entry.bind('<FocusOut>', lambda e: self.calculate_all_fineness())
                    entry.bind('<Return>', lambda e: self.calculate_all_fineness())
                    
            self.log("🔗 Fineness calculation bindings added", 'weight')
            
        except Exception as e:
            self.log(f"❌ Error binding fineness calculations: {str(e)}", 'weight')
    
    def show_theoretical_fineness(self):
        """Show theoretical fineness calculations based on average delta"""
        try:
            # Get average delta
            if not hasattr(self, 'avg_delta_display') or self.avg_delta_display.cget('text') == "0.000":
                messagebox.showwarning("No Delta", "Please calculate deltas first (C1 and C2 values)")
                return
            
            avg_delta = float(self.avg_delta_display.cget('text'))
            
            # Get initial weights
            strip1_initial = self.get_field_value('num_strip_weight_M11')
            strip2_initial = self.get_field_value('num_strip_weight_M12')
            
            if strip1_initial <= 0 or strip2_initial <= 0:
                messagebox.showwarning("No Initial Weights", "Please enter initial weights for both strips")
                return
            
            # Calculate theoretical fineness
            strip1_theoretical = self.calculate_theoretical_fineness_from_delta(strip1_initial, avg_delta)
            strip2_theoretical = self.calculate_theoretical_fineness_from_delta(strip2_initial, avg_delta)
            
            if strip1_theoretical and strip2_theoretical:
                mean_theoretical = (strip1_theoretical + strip2_theoretical) / 2
                
                # Show results
                result_text = f"""📊 Theoretical Fineness Calculations (Avg Delta: {avg_delta:.3f} mg)

🧮 Formula: F = (Initial - AvgDelta) / Initial × 1000

Strip 1:
• Initial: {strip1_initial:.3f} mg
• Theoretical Fineness: {strip1_theoretical:.3f}

Strip 2:
• Initial: {strip2_initial:.3f} mg  
• Theoretical Fineness: {strip2_theoretical:.3f}

📈 Mean Theoretical Fineness: {mean_theoretical:.3f}

💡 These are the expected fineness values based on the average delta from C1/C2 calculations."""
                
                messagebox.showinfo("Theoretical Fineness", result_text)
                
                # Log the calculations
                self.log(f"📊 Theoretical Fineness (Δ{avg_delta:.3f}):", 'weight')
                self.log(f"   Strip 1: {strip1_theoretical:.3f}", 'weight')
                self.log(f"   Strip 2: {strip2_theoretical:.3f}", 'weight')
                self.log(f"   Mean: {mean_theoretical:.3f}", 'weight')
                
            else:
                messagebox.showerror("Calculation Error", "Could not calculate theoretical fineness")
                
        except Exception as e:
            self.log(f"❌ Error showing theoretical fineness: {str(e)}", 'weight')
            messagebox.showerror("Error", f"Error calculating theoretical fineness: {str(e)}")

    def _display_strip_table(self, strips):
        """Display fetched strip data in compact table format"""
        # Group strips by lot_no
        lots = {}
        for strip in strips:
            lot_no = strip.get('lot_no', '1')
            lots.setdefault(lot_no, []).append(strip)
        self.lots_data = lots
        # Clear previous table
        for widget in self.strip_table_frame.winfo_children():
            widget.destroy()
        if not lots:
            ttk.Label(self.strip_table_frame, text="No data available", font=('Segoe UI', 9, 'italic')).pack(padx=8, pady=8)
            self.log("[DEBUG] No lots found to display in table.", 'weight')
            return
        table_container = ttk.Frame(self.strip_table_frame)
        table_container.pack(fill='x', padx=8, pady=8)
        lot_nos = sorted(lots.keys(), key=lambda x: int(x))
        # Lot selection if multiple lots
        if len(lot_nos) > 1:
            lot_frame = ttk.Frame(table_container)
            lot_frame.pack(fill='x', pady=(0, 8))
            ttk.Label(lot_frame, text="📦 Lot:", font=('Segoe UI', 8, 'bold')).pack(side='left', padx=(0, 5))
            self.lot_var = tk.StringVar(value=lot_nos[0])
            lot_dropdown = ttk.Combobox(lot_frame, textvariable=self.lot_var, values=lot_nos, state='readonly', width=8, font=('Segoe UI', 8))
            lot_dropdown.pack(side='left', padx=(0, 5))
            def on_lot_change(event):
                selected_lot = self.lot_var.get()
                self.current_lot_no = selected_lot
                self.log(f"📦 Lot selection changed to: {selected_lot}", 'weight')
                self._auto_fill_all_fields_for_lot(selected_lot)
            lot_dropdown.bind('<<ComboboxSelected>>', on_lot_change)
            self.current_lot_no = lot_nos[0]
            self.log(f"[DEBUG] Lot selection UI created for lots: {lot_nos}", 'weight')
        else:
            self.current_lot_no = lot_nos[0]
            self.log(f"[DEBUG] Only one lot present: {lot_nos[0]}", 'weight')
        # Show compact lot summary
        summary_text = f"📊 {len(lot_nos)} lot(s), {sum(len(strips) for strips in lots.values())} strips"
        ttk.Label(table_container, text=summary_text, font=('Segoe UI', 7, 'italic'), foreground='#6c757d').pack()
        # Optionally, you can add a preview of strips or other info here
        self.log(f"[DEBUG] Table and lot selection UI displayed.", 'weight')

    def get_settings(self):
        """Return current app settings as a dictionary."""
        settings = {}
        
        # Get configuration settings
        if hasattr(self, 'username_var'):
            settings['username'] = self.username_var.get()
        if hasattr(self, 'password_var'):
            settings['password'] = self.password_var.get()
        if hasattr(self, 'firm_id_var'):
            settings['firm_id'] = self.firm_id_var.get()
        if hasattr(self, 'api_url_var'):
            settings['api_url'] = self.api_url_var.get()
        if hasattr(self, 'request_api_url_var'):
            settings['request_api_url'] = self.request_api_url_var.get()
        if hasattr(self, 'orders_api_url_var'):
            settings['orders_api_url'] = self.orders_api_url_var.get()
        if hasattr(self, 'report_api_url_var'):
            settings['report_api_url'] = self.report_api_url_var.get()
        if hasattr(self, 'api_key_var'):
            settings['api_key'] = self.api_key_var.get()
            
        # Get portal credentials
        if hasattr(self, 'portal_username_var'):
            settings['portal_username'] = self.portal_username_var.get()
        if hasattr(self, 'portal_password_var'):
            settings['portal_password'] = self.portal_password_var.get()
            
        # Get reception credentials
        if hasattr(self, 'reception_username_var'):
            settings['reception_username'] = self.reception_username_var.get()
        if hasattr(self, 'reception_password_var'):
            settings['reception_password'] = self.reception_password_var.get()
            
        # Save API configuration
        if hasattr(self, 'jeweller_api_url_var'):
            settings['jeweller_api_url'] = self.jeweller_api_url_var.get()
        if hasattr(self, 'check_jobs_api_url_var'):
            settings['check_jobs_api_url'] = self.check_jobs_api_url_var.get()
        if hasattr(self, 'save_job_api_url_var'):
            settings['save_job_api_url'] = self.save_job_api_url_var.get()
        if hasattr(self, 'manage_jeweller_api_url_var'):
            settings['manage_jeweller_api_url'] = self.manage_jeweller_api_url_var.get()
        if hasattr(self, 'get_jobs_api_url_var'):
            settings['get_jobs_api_url'] = self.get_jobs_api_url_var.get()
            
        # Save API Base URL
        if hasattr(self, 'api_base_url_var'):
            settings['api_base_url'] = self.api_base_url_var.get()
            
        # Save Portal Configuration
        if hasattr(self, 'portal_generate_url_var'):
            settings['portal_generate_url'] = self.portal_generate_url_var.get()

        # Save MANAK portal environment and login URL
        if hasattr(self, 'portal_env_var'):
            settings['portal_env'] = self.portal_env_var.get()
            portal_config.set_portal_env(self.portal_env_var.get())
        if hasattr(self, 'login_url_var'):
            settings['login_url'] = self.login_url_var.get()
            
        return settings


    
    def get_memory_usage(self):
        """Get current memory usage for monitoring"""
        import psutil
        import os
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024  # Convert to MB
        return memory_mb
    
    def log_memory_usage(self, operation=""):
        """Log current memory usage"""
        try:
            memory_mb = self.get_memory_usage()
            self.log(f"💾 Memory Usage: {memory_mb:.1f} MB {operation}", 'status')
        except Exception as e:
            self.log(f"⚠️ Could not get memory usage: {str(e)}", 'status')

    def _handle_voucher_download(self, request_no):
        """Handle voucher PDF download and extraction"""
        try:
            import glob
            import os
            import time
            import re
            
            # Identify download directories to monitor
            dirs_to_check = []
            
            # 1. Configured download dir
            config_dir = getattr(self, 'download_dir', None)
            if config_dir and os.path.exists(config_dir):
                dirs_to_check.append(config_dir)
            else:
                dirs_to_check.append(os.path.join(os.getcwd(), 'downloads'))
                
            # 2. User Downloads dir (fallback)
            user_downloads = os.path.join(os.path.expanduser('~'), 'Downloads')
            if os.path.exists(user_downloads) and user_downloads not in dirs_to_check:
                dirs_to_check.append(user_downloads)
            
            self.log(f"DEBUG: Monitoring dirs: {dirs_to_check}", 'acknowledge')
            
            # Snapshot existing keys
            existing_files = set()
            for d in dirs_to_check:
                if os.path.exists(d):
                    existing_files.update(glob.glob(os.path.join(d, "*.pdf")))
            
            # Wait for new file (max 30 seconds)
            new_pdf = None
            found_dir = None
            
            for _ in range(60): # 30 seconds
                current_files = set()
                for d in dirs_to_check:
                    if os.path.exists(d):
                        current_files.update(glob.glob(os.path.join(d, "*.pdf")))
                
                new_files = current_files - existing_files
                
                if new_files:
                    # Filter out temporary download files (.crdownload etc)
                    valid_new_files = [f for f in new_files if not f.endswith('.crdownload') and not f.endswith('.tmp')]
                    if valid_new_files:
                        # Find the most recent one if multiple appeared
                        # Just take the first one logic for simplicity, or sort by mtime?
                        # Let's take the one that is valid
                        new_pdf = list(valid_new_files)[0] 
                        found_dir = os.path.dirname(new_pdf)
                        self.log(f"DEBUG: Found new file: {new_pdf}", 'acknowledge')
                        break
                time.sleep(0.5)
                
            if not new_pdf:
                self.log("⚠️ No new PDF downloaded (timeout)", 'acknowledge')
                return None
                
            # Wait for file to be fully written (size stable)
            time.sleep(1.5) 
            
            extracted_license = None
            
            # Extract License No from original file first
            try:
                extracted_license = self._extract_license_from_pdf(new_pdf)
            except Exception as e:
                self.log(f"⚠️ Extraction from temp file failed: {e}", 'acknowledge')
            
            # Rename for organization
            try:
                extension = os.path.splitext(new_pdf)[1]
                new_filename = f"Voucher_{request_no}{extension}"
                
                # Use target directory: configured download dir if available, else found dir
                target_dir = getattr(self, 'download_dir', found_dir)
                if not target_dir or not os.path.exists(target_dir):
                     target_dir = found_dir
                     
                new_path = os.path.join(target_dir, new_filename)
                
                # Handle existing file
                if os.path.exists(new_path):
                    try:
                        os.remove(new_path)
                    except:
                        pass # Ignore if permission error
                    
                if not os.path.exists(new_path):
                    os.rename(new_pdf, new_path)
                    self.log(f"✅ Downloaded voucher: {new_filename}", 'acknowledge')
                else:
                    self.log(f"⚠️ Could not overwrite existing voucher {new_filename}", 'acknowledge')
                    
            except Exception as e:
                self.log(f"⚠️ Could not rename file: {e}", 'acknowledge')
                
            return extracted_license
            
        except Exception as e:
            self.log(f"❌ Error handling download: {str(e)}", 'acknowledge')
            return None

    def _get_save_job_firm_id(self):
        firm_id = 2
        if hasattr(self, 'license_manager') and self.license_manager:
            if hasattr(self.license_manager, 'firm_id') and self.license_manager.firm_id:
                try:
                    firm_id = int(self.license_manager.firm_id)
                except (TypeError, ValueError):
                    pass
        return firm_id

    def _build_save_job_payload(self, job_data, firm_id):
        """Build save_job / save_jobs API payload for one row (job_no only if portal provided it)."""
        req = job_data.get('request_no', '')
        j_no = (job_data.get('job_no') or '').strip()
        job = {
            'request_no': req,
            'licence_no': job_data.get('licence_no', ''),
            'item': job_data.get('item', ''),
            'pcs': job_data.get('pcs', 0),
            'weight': job_data.get('weight', 0.0),
            'purity': job_data.get('purity', ''),
            'material_type': job_data.get('material_type', 'Gold'),
            'date_of_request': job_data.get('date_of_request', ''),
            'status': job_data.get('status', 'XRF'),
            'huid_pcs': job_data.get('pcs', 0),
            'is_billed': 0,
            'cornet_weight': 0.0,
            'scrp_cornet_weight': 0.0,
            'bill_no': '',
            'created_at': (job_data.get('date_of_request', '') or '') + ' 00:00:00',
        }
        if j_no:
            job['job_no'] = j_no
        return job

    def _log_save_job_api_line(self, job):
        self.log(
            f"💾 API save → Req#{job.get('request_no')} | item={job.get('item')!r} | "
            f"pcs={job.get('pcs')} | weight={job.get('weight')}g | purity={job.get('purity')!r} | "
            f"licence={job.get('licence_no')} | material={job.get('material_type')}"
            + (f" | job_no={job.get('job_no')}" if job.get('job_no') else ''),
            'acknowledge',
        )

    def _handle_save_job_api_result(self, result, job):
        """Log outcome of one save_job / save_jobs row."""
        if not result.get('success'):
            self.log(f"⚠️ API returned error: {result.get('message')}", 'acknowledge')
            return False
        msg = result.get('message', '')
        if result.get('saved'):
            row_id = result.get('id', '')
            extra = f" (id={row_id})" if row_id else ''
            self.log(
                f"✅ Job card saved: Req#{job.get('request_no')} "
                f"{job.get('item')} {job.get('pcs')}pc {job.get('weight')}g{extra}",
                'acknowledge',
            )
            return True
        self.log(f"ℹ️ Job not inserted: {msg}", 'acknowledge')
        return False

    def _is_legacy_request_only_duplicate(self, message):
        """Old save_job_api blocked any 2nd row with same request_no (ignored item)."""
        m = (message or '').lower()
        return 'already exists for request' in m and 'same item' not in m

    def _try_save_jobs_batch(self, jobs_with_data, request_no):
        """POST all items in one request (needs updated save_job_api.php on server)."""
        api_url = getattr(self, 'save_job_api_url_var', None)
        if not api_url:
            return False
        url = api_url.get().strip()
        if not url:
            return False
        try:
            import requests
            firm_id = self._get_save_job_firm_id()
            jobs = [
                self._build_save_job_payload(j) for j in jobs_with_data
            ]
            payload = {'action': 'save_jobs', 'firm_id': firm_id, 'jobs': jobs}
            self.log(
                f"💾 Batch API save ({len(jobs)} items) for Request #{request_no}...",
                'acknowledge',
            )
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code != 200:
                return False
            result = response.json()
            if not result.get('success'):
                return False
            for i, row in enumerate(result.get('results', []), 1):
                item = row.get('item', jobs[i - 1].get('item', '') if i <= len(jobs) else '')
                if row.get('saved'):
                    self.log(
                        f"✅ Batch row {i}/{len(jobs)} saved: {item}",
                        'acknowledge',
                    )
                else:
                    self.log(
                        f"ℹ️ Batch row {i}/{len(jobs)} skipped: {row.get('message', '')}",
                        'acknowledge',
                    )
            self.log(
                f"✅ Batch complete: {result.get('saved_count', 0)}/{result.get('total', len(jobs))} saved",
                'acknowledge',
            )
            return int(result.get('saved_count', 0) or 0) > 0
        except Exception as e:
            self.log(f"ℹ️ Batch save not available ({e}), saving row-by-row...", 'acknowledge')
            return False

    def _save_job_via_api(self, job_data):
        """Save one job row via API. job_no is left empty at acknowledge (assigned later on portal)."""
        try:
            import requests

            api_url = getattr(self, 'save_job_api_url_var', None)
            if not api_url:
                self.log("⚠️ No Save Job API URL configured - Skipping DB save", 'acknowledge')
                return

            url = api_url.get().strip()
            if not url:
                return

            firm_id = self._get_save_job_firm_id()
            job = self._build_save_job_payload(job_data, firm_id)
            payload = {'action': 'save_job', 'firm_id': firm_id, 'job': job}
            self._log_save_job_api_line(job)

            response = requests.post(url, json=payload, timeout=10)
            if response.status_code != 200:
                self.log(
                    f"❌ API HTTP Error: {response.status_code} - {response.text[:100]}",
                    'acknowledge',
                )
                return

            result = response.json()
            if self._handle_save_job_api_result(result, job):
                return

            msg = result.get('message', '')
            if self._is_legacy_request_only_duplicate(msg):
                self.log(
                    "⚠️ Server rejected extra items for this request (old API). "
                    "Upload the updated server_scripts/save_job_api.php to hallmarkpro — "
                    "it saves multiple items per request with empty job_no.",
                    'acknowledge',
                )

        except Exception as e:
            self.log(f"❌ Error saving job via API: {str(e)}", 'acknowledge')
    def _extract_license_from_pdf(self, pdf_path):
        """Extract license number from PDF (basic raw extraction)"""
        try:
            import re
            
            with open(pdf_path, 'rb') as f:
                content = f.read()
                
            # Try to find "License No" pattern in raw bytes
            # Patterns to try:
            # 1. "License No. : CM/L-XXXXXXX"
            # 2. "Licence No : XXXXXXX"
            # 3. "CM/L-XXXXXXX"
            patterns = [
                rb'License\s*No[\s.:-]*([A-Z0-9/]+-\d+|[A-Z0-9/-]+)',
                rb'Licence\s*No[\s.:-]*([A-Z0-9/]+-\d+|[A-Z0-9/-]+)',
                rb'(CM/L-\d+)',
                rb'(CM/L\s*-\s*\d+)',
            ]
            
            for pattern in patterns:
                # Use DOTALL to match across lines if needed, but here simple search should work
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    # Decode bytes to string
                    try:
                        license_no = match.group(1).decode('utf-8', errors='ignore').strip()
                    except:
                        license_no = str(match.group(1))
                        
                    # Clean up if matched too much
                    # Remove trailing binary garbage if regex was greedy
                    license_no = re.split(r'[^A-Z0-9/-]', license_no)[0]
                    
                    if len(license_no) > 5: # Basic validation
                        self.log(f"🔍 Found License No in PDF: {license_no}", 'acknowledge')
                        return license_no
                    
            self.log("⚠️ Could not extract License No from PDF text", 'acknowledge')
            return None
            
        except Exception as e:
            self.log(f"❌ Error extracting license from PDF: {str(e)}", 'acknowledge')
            return None
    

if __name__ == "__main__":
    app = ManakDesktopApp()
    app.run()
