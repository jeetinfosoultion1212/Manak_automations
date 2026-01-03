#!/usr/bin/env python3
"""
MANAK Portal Desktop Application
Enhanced Compact UI with Responsive Design - No Scrolling Required
"""

# Fix MySQL localization issue BEFORE any imports
import os
os.environ['LANG'] = 'C'
os.environ['LC_ALL'] = 'C'
os.environ['LC_MESSAGES'] = 'C'

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
import threading
import time
from datetime import datetime
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, UnexpectedAlertPresentException, NoAlertPresentException
import random
import json
import os
import sys
import sqlite3

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


__version__ = "3.0"

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
        
        # Setup executable-specific configurations
        self.setup_executable_config()
        
        # Test critical imports before proceeding
        self.test_critical_imports()
        
        # Automation state
        self.driver = None
        self.logged_in = False
        self.page_loaded = False
        self.license_verified = False  # Track license verification status
        
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
        
        self.setup_ui()
        # Load saved settings
        self.load_settings()
        # Clear fields on app start
        self.clear_fields_on_start()
        
        # Update fetch button text based on initial job number
        self.root.after(100, self.on_job_number_change)
        
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
        mac_address = self.license_manager.mac_address if self.license_manager else "Unknown"
        mac_label = tk.Label(device_grid, text=mac_address, font=('Segoe UI', 9),
                           bg='#f8f9fa', fg='#495057', relief='sunken', padx=5, pady=2)
        mac_label.grid(row=0, column=1, sticky='ew', padx=(5,5), pady=2)
        ttk.Button(device_grid, text="📋", width=3, 
                  command=lambda: copy_to_clipboard(mac_address, "MAC Address")).grid(row=0, column=2, pady=2)
        
        # Device ID (read-only) with copy button
        ttk.Label(device_grid, text="Device ID:", font=('Segoe UI', 9, 'bold')).grid(row=1, column=0, sticky='w', pady=2)
        device_id = self.license_manager.device_id if self.license_manager else "Unknown"
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
                
                if self.license_manager.verify_device_license(username, password):
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
                
                tk.Tk.report_callback_exception = custom_report_callback_exception
            except Exception as e:
                print(f"Failed to setup tkinter exception handler: {e}")
        
        handle_tkinter_exception()
    
    def setup_executable_config(self):
        """Setup configurations specific to executable environment"""
        try:
            # Check if running as executable
            if getattr(sys, 'frozen', False):
                # Running as executable
                self.is_executable = True
                self.base_path = sys._MEIPASS
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
                print(f"✓ {module} imported successfully")
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
        
        # 2. Accept Request Tab
        self.setup_accept_request_tab()
        
        # 2. Create Jobs Tab (Job Cards Processing)
        try:
            from processors.job_cards_processor import JobCardsProcessor
            from processors.delivery_voucher_processor import DeliveryVoucherProcessor
            from processors.weight_capture_processor import WeightCaptureProcessor
            
            self.job_cards_processor = JobCardsProcessor(
                None,  # Driver will be set later when browser opens
                self.log,
                self.check_license_before_action,
                self  # Pass app context for settings access
            )
            self.job_cards_processor.setup_job_cards_tab(self.notebook)
            self.log("✅ Create Jobs module loaded successfully", 'system')
            
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
            self.job_cards_processor = None
            self.delivery_voucher_processor = None
            self.weight_capture_processor = None
            self.log(f"⚠️ Create Jobs module not available: {e}", 'system')
            placeholder_frame = ttk.Frame(self.notebook)
            self.notebook.add(placeholder_frame, text="📋 Create Jobs (Unavailable)")
            ttk.Label(placeholder_frame, text="Create Jobs module not available", 
                     font=('Segoe UI', 12)).pack(expand=True)
        except Exception as e:
            self.job_cards_processor = None
            self.delivery_voucher_processor = None
            self.weight_capture_processor = None
            self.log(f"❌ Error loading Create Jobs: {e}", 'system')
            placeholder_frame = ttk.Frame(self.notebook)
            self.notebook.add(placeholder_frame, text="📋 Create Jobs (Error)")
            ttk.Label(placeholder_frame, text=f"Error loading Create Jobs: {str(e)}", 
                     font=('Segoe UI', 12)).pack(expand=True)
        
        # 4. Bulk Jobs Tab (Multiple Jobs Processing)
        if MultipleJobsProcessor:
            self.multiple_jobs_processor = MultipleJobsProcessor(
                None,  # Driver will be set later when browser opens
                self.log,
                self.check_license_before_action,
                self  # Pass main app reference for settings access
            )
            self.multiple_jobs_processor.setup_multiple_jobs_tab(self.notebook)
        
        # 5. Single Jobs Tab (Weight Entry)
        self.setup_weight_tab_compact()
        
        # 6. Weight Capture Tab - NEW
        if hasattr(self, 'weight_capture_processor') and self.weight_capture_processor:
            self.weight_capture_processor.setup_weight_capture_tab(self.notebook)
            self.log("✅ Weight Capture module loaded successfully", 'system')
        
        # 7. Delivery Voucher Tab
        if hasattr(self, 'delivery_voucher_processor') and self.delivery_voucher_processor:
            self.delivery_voucher_processor.setup_delivery_voucher_tab(self.notebook)
            self.log("✅ Delivery Voucher module loaded successfully", 'system')
        
        # 8. Settings Tab
        self.setup_settings_tab()
        
        
    def setup_browser_tab(self):
        """Setup Login in MANAK tab with enhanced UI"""
        browser_frame = ttk.Frame(self.notebook)
        self.notebook.add(browser_frame, text="🔐 Login in MANAK")
        
        # Browser controls card
        control_card = ttk.LabelFrame(browser_frame, text="🎛️ Browser Controls", style='Compact.TLabelframe')
        control_card.pack(fill='x', padx=10, pady=(10, 8))
        
        # Button grid
        btn_container = ttk.Frame(control_card)
        btn_container.pack(fill='x', padx=10, pady=10)
        
        # Row 1
        btn_row1 = ttk.Frame(btn_container)
        btn_row1.pack(fill='x', pady=(0, 8))
        
        self.open_btn = ttk.Button(btn_row1, text="🚀 Open Browser", style='Compact.TButton', command=self.open_browser)
        self.open_btn.pack(side='left', padx=(0, 8))
        
        self.login_btn = ttk.Button(btn_row1, text="🔑 Navigate to Login", style='Info.TButton', command=self.navigate_to_login, state='disabled')
        self.login_btn.pack(side='left', padx=(0, 8))
        
        # Row 2
        btn_row2 = ttk.Frame(btn_container)
        btn_row2.pack(fill='x')
        
        self.check_btn = ttk.Button(btn_row2, text="🔍 Check Login Status", style='Success.TButton', command=self.check_login, state='disabled')
        self.check_btn.pack(side='left', padx=(0, 8))
        
        self.close_btn = ttk.Button(btn_row2, text="❌ Close Browser", style='Danger.TButton', command=self.close_browser, state='disabled')
        self.close_btn.pack(side='left')
        
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
            weight_url = f"https://huid.manakonline.in/MANAK/SamplingweightingDeatils?requestNo={request_no}&jobNo={job_no}"
            self.driver.get(weight_url)
            time.sleep(3)
            current_url = self.driver.current_url
            if 'SamplingweightingDeatils' not in current_url:
                raise Exception("Failed to load weight page")
            self.page_loaded = True
            self.log(f"✅ Weight page loaded: {current_url}", 'weight')
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
                        self.log(f"✅ Selected Lot {selected_lot} in portal via Select2", 'weight')
                        break
                if not found:
                    raise Exception(f"Lot {selected_lot} not found in Select2 options")
                time.sleep(1)
                lot_dropdown = self.driver.find_element(By.ID, "lotno")
                selected_value = lot_dropdown.get_attribute('value')
                if selected_value != str(selected_lot):
                    self.log(f"⚠️ Lot selection verification failed: expected {selected_lot}, got {selected_value}", 'weight')
                else:
                    self.log(f"✅ Lot selection verified: {selected_value}", 'weight')
            except Exception as select2_error:
                self.log(f"⚠️ Select2 lot selection failed: {str(select2_error)}. Trying fallback methods...", 'weight')
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
                    element = self.driver.find_element(By.ID, field_name)
                    if element.is_displayed() and element.is_enabled():
                        element.clear()
                        element.send_keys(value)
                        filled_count += 1
                        self.log(f"✅ Filled {field_name}: {value}", 'weight')
                        # Click savesampleweight button
                        try:
                            save_btn = self.driver.find_element(By.ID, 'savesampleweight')
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
                    element = self.driver.find_element(By.ID, field_name)
                    if element.is_displayed() and element.is_enabled():
                        element.clear()
                        element.send_keys(value)
                        filled_count += 1
                        self.log(f"✅ Filled {field_name}: {value}", 'weight')
                        # Click savebuttonweight button
                        try:
                            save_btn = self.driver.find_element(By.ID, 'savebuttonweight')
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
                    element = self.driver.find_element(By.ID, field_name)
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
                save_btn = self.driver.find_element(By.ID, 'chechkgoldM12')
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
            weight_url = f"https://huid.manakonline.in/MANAK/SamplingweightingDeatils?requestNo={request_no}&jobNo={job_no}"
            self.driver.get(weight_url)
            time.sleep(3)
            current_url = self.driver.current_url
            if 'SamplingweightingDeatils' not in current_url:
                raise Exception("Failed to load weight page")
            self.page_loaded = True
            self.log(f"✅ Weight page loaded: {current_url}", 'weight')
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
                        self.log(f"✅ Selected Lot {selected_lot} in portal via Select2", 'weight')
                        break
                if not found:
                    raise Exception(f"Lot {selected_lot} not found in Select2 options")
                time.sleep(1)
                lot_dropdown = self.driver.find_element(By.ID, "lotno")
                selected_value = lot_dropdown.get_attribute('value')
                if selected_value != str(selected_lot):
                    self.log(f"⚠️ Lot selection verification failed: expected {selected_lot}, got {selected_value}", 'weight')
                else:
                    self.log(f"✅ Lot selection verified: {selected_value}", 'weight')
            except Exception as select2_error:
                self.log(f"⚠️ Select2 lot selection failed: {str(select2_error)}. Trying fallback methods...", 'weight')
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
                    element = self.driver.find_element(By.ID, field_name)
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
                    element = self.driver.find_element(By.ID, field_id)
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
                    selected_value = lot_dropdown.get_attribute('value')
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
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            import time
            # Get the correct lot number using helper method
            lot_no = self._get_current_lot_selection()
            request_no = self.request_entry.get().strip()
            job_no = self.job_entry.get().strip()
            loading_dialog = LoadingDialog(self.root, "Save Cornet Weights", "Filling cornet weights and saving...")
            loading_dialog.update_status("Loading weight page...")
            loading_dialog.update_message("Loading weight entry page for the request...")
            weight_url = f"https://huid.manakonline.in/MANAK/SamplingweightingDeatils?requestNo={request_no}&jobNo={job_no}"
            self.driver.get(weight_url)
            time.sleep(3)
            current_url = self.driver.current_url
            if 'SamplingweightingDeatils' not in current_url:
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
                            element = self.driver.find_element(By.ID, field_id)
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
                save_btn = self.driver.find_element(By.ID, 'savecornetvalues')
                if save_btn.is_displayed() and save_btn.is_enabled():
                    save_btn.click()
                    self.log("💾 Clicked Save Cornet Weight button", 'weight')
                    time.sleep(1)
                    # Handle first alert (Are you sure you want to save?)
                    try:
                        alert = self.driver.switch_to.alert
                        alert_text = alert.text
                        self.log(f"🔔 Alert: {alert_text}", 'weight')
                        alert.accept()
                        time.sleep(1)
                    except Exception as e:
                        self.log(f"❌ Error handling first alert: {str(e)}", 'weight')
                    # Handle second alert (result)
                    try:
                        alert = self.driver.switch_to.alert
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
                    submit_btn = self.driver.find_element(By.ID, 'submitQM')
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
    
    def setup_settings_tab(self):
        """Setup settings tab with scrollable content"""
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
        
        canvas.create_window((0, 0), window=settings_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Device Information Card - Compact layout
        if self.license_manager:
            device_card = ttk.LabelFrame(settings_frame, text="📱 Device Info", style='Compact.TLabelframe')
            device_card.pack(fill='x', padx=10, pady=(5, 3))
            
            device_frame = ttk.Frame(device_card)
            device_frame.pack(fill='x', padx=8, pady=5)
            
            # MAC Address (read-only)
            ttk.Label(device_frame, text="MAC:", font=('Segoe UI', 8, 'bold')).grid(row=0, column=0, padx=(0, 5), pady=2, sticky='w')
            mac_address = self.license_manager.mac_address if self.license_manager else "Unknown"
            mac_label = tk.Label(device_frame, text=mac_address, font=('Segoe UI', 9), 
                               bg='#f8f9fa', fg='#495057', relief='sunken', padx=5, pady=2)
            mac_label.grid(row=0, column=1, padx=(0, 5), pady=2, sticky='w')
            
            # Device ID (read-only)
            ttk.Label(device_frame, text="ID:", font=('Segoe UI', 8, 'bold')).grid(row=1, column=0, padx=(0, 5), pady=2, sticky='w')
            device_id = self.license_manager.device_id if self.license_manager else "Unknown"
            device_id_label = tk.Label(device_frame, text=device_id, font=('Segoe UI', 9), 
                                     bg='#f8f9fa', fg='#495057', relief='sunken', padx=5, pady=2)
            device_id_label.grid(row=1, column=1, padx=(0, 5), pady=2, sticky='w')
            
            # License status with details
            ttk.Label(device_frame, text="Status:", font=('Segoe UI', 8, 'bold')).grid(row=2, column=0, padx=(0, 5), pady=2, sticky='w')
            status_frame = ttk.Frame(device_frame)
            status_frame.grid(row=2, column=1, sticky='w', padx=(0, 5), pady=2)
            
            self.license_status_label = ttk.Label(status_frame, text="⏳ Not Verified", font=('Segoe UI', 9, 'bold'), foreground='#ffc107')
            self.license_status_label.pack(side='left', padx=(0, 5))
            
            # Add expiry date/trial info
            self.license_info_label = ttk.Label(status_frame, text="", font=('Segoe UI', 8))
            self.license_info_label.pack(side='left')
            
        # License Verification Card
        if self.license_manager:
            portal_card = ttk.LabelFrame(settings_frame, text="🔐 License Verification", style='Compact.TLabelframe')
            portal_card.pack(fill='x', padx=10, pady=3)
            
            portal_frame = ttk.Frame(portal_card)
            portal_frame.pack(fill='x', padx=8, pady=5)
            
            # Portal Username
            ttk.Label(portal_frame, text="Username:", font=('Segoe UI', 8, 'bold')).grid(row=0, column=0, padx=(0, 5), pady=2, sticky='w')
            self.portal_username_var = tk.StringVar()
            portal_username_entry = ttk.Entry(portal_frame, textvariable=self.portal_username_var, width=25, style='Compact.TEntry', font=('Segoe UI', 9))
            portal_username_entry.grid(row=0, column=1, padx=(0, 5), pady=2, sticky='w')
            
            # Portal Password
            ttk.Label(portal_frame, text="Password:", font=('Segoe UI', 8, 'bold')).grid(row=1, column=0, padx=(0, 5), pady=2, sticky='w')
            self.portal_password_var = tk.StringVar()
            portal_password_entry = ttk.Entry(portal_frame, textvariable=self.portal_password_var, width=25, style='Compact.TEntry', show='*', font=('Segoe UI', 9))
            portal_password_entry.grid(row=1, column=1, padx=(0, 5), pady=2, sticky='w')
            
            # Action buttons
            btn_frame = ttk.Frame(portal_frame)
            btn_frame.grid(row=2, column=0, columnspan=2, pady=8)
            
            verify_btn = ttk.Button(btn_frame, text="🔍 Verify License", style='Info.TButton', command=self.verify_license)
            verify_btn.pack(side='left', padx=(0, 5))
            
            clear_btn = ttk.Button(btn_frame, text="🗑️ Clear License", style='Danger.TButton', command=self.clear_license)
            clear_btn.pack(side='left')
        
        # BIS Portal Configuration Card
        settings_card = ttk.LabelFrame(settings_frame, text="🌐 BIS Portal Configuration", style='Compact.TLabelframe')
        settings_card.pack(fill='x', padx=10, pady=3)
        
        settings_grid = ttk.Frame(settings_card)
        settings_grid.pack(fill='x', padx=8, pady=5)
        
        # Username
        ttk.Label(settings_grid, text="Username:", font=('Segoe UI', 8, 'bold')).grid(row=0, column=0, padx=(0, 5), pady=3, sticky='w')
        self.username_var = tk.StringVar(value='qmhmc1')
        username_entry = ttk.Entry(settings_grid, textvariable=self.username_var, width=20, style='Compact.TEntry', font=('Segoe UI', 9))
        username_entry.grid(row=0, column=1, padx=(0, 5), pady=3, sticky='w')
        
        # Password
        ttk.Label(settings_grid, text="Password:", font=('Segoe UI', 8, 'bold')).grid(row=1, column=0, padx=(0, 5), pady=3, sticky='w')
        self.password_var = tk.StringVar(value='Mahalaxmi14')
        password_entry = ttk.Entry(settings_grid, textvariable=self.password_var, width=20, style='Compact.TEntry', show='*', font=('Segoe UI', 9))
        password_entry.grid(row=1, column=1, padx=(0, 5), pady=3, sticky='w')
        
        # Firm ID
        ttk.Label(settings_grid, text="Firm ID:", font=('Segoe UI', 8, 'bold')).grid(row=2, column=0, padx=(0, 5), pady=3, sticky='w')
        self.firm_id_var = tk.StringVar(value='2')
        self.firm_id_display_label = tk.Label(settings_grid, text='2', font=('Segoe UI', 9, 'bold'), 
                                             fg='#17a2b8', bg='#f8f9fa', relief='sunken', padx=5, pady=2)
        self.firm_id_display_label.grid(row=2, column=1, padx=(0, 5), pady=3, sticky='w')
        
        # Advanced Settings Card
        api_card = ttk.LabelFrame(settings_frame, text="⚙️ Advanced Settings", style='Compact.TLabelframe')
        api_card.pack(fill='x', padx=10, pady=3)
        
        api_main_frame = ttk.Frame(api_card)
        api_main_frame.pack(fill='x', padx=8, pady=5)
        
        # Password reveal controls (no hint text for security)
        reveal_frame = ttk.Frame(api_main_frame)
        reveal_frame.pack(fill='x', pady=3)
        
        ttk.Label(reveal_frame, text="Password:", font=('Segoe UI', 8)).pack(side='left', padx=(0, 5))
        
        self.api_password_var = tk.StringVar()
        self.api_password_entry = ttk.Entry(reveal_frame, textvariable=self.api_password_var, 
                                          show='*', width=20, style='Compact.TEntry', font=('Segoe UI', 9))
        self.api_password_entry.pack(side='left', padx=(0, 8))
        
        self.reveal_btn = ttk.Button(reveal_frame, text="⚙️ Show Settings", 
                                    style='Warning.TButton', command=self.toggle_api_visibility)
        self.reveal_btn.pack(side='left')
        
        # Hidden API fields frame
        self.api_fields_frame = ttk.Frame(api_main_frame)
        self.api_fields_frame.pack(fill='x', pady=(8, 0))
        
        # Configure grid to allow proper sizing
        self.api_fields_frame.columnconfigure(1, weight=1)
        
        # Job Data API URL
        ttk.Label(self.api_fields_frame, text="Job Data API:", font=('Segoe UI', 8, 'bold')).grid(row=0, column=0, padx=(0, 5), pady=3, sticky='w')
        self.api_url_var = tk.StringVar(value='https://hallmarkpro.prosenjittechhub.com/admin/get_job_report.php?job_no=')
        self.api_url_entry = ttk.Entry(self.api_fields_frame, textvariable=self.api_url_var, width=55, style='Compact.TEntry', font=('Segoe UI', 8))
        self.api_url_entry.grid(row=0, column=1, padx=(0, 5), pady=3, sticky='ew')
        
        # Request No API URL
        ttk.Label(self.api_fields_frame, text="Request No API:", font=('Segoe UI', 8, 'bold')).grid(row=1, column=0, padx=(0, 5), pady=3, sticky='w')
        self.request_api_url_var = tk.StringVar(value='https://hallmarkpro.prosenjittechhub.com/admin/API/get_request_no.php?job_no=')
        self.request_api_entry = ttk.Entry(self.api_fields_frame, textvariable=self.request_api_url_var, width=55, style='Compact.TEntry', font=('Segoe UI', 8))
        self.request_api_entry.grid(row=1, column=1, padx=(0, 5), pady=3, sticky='ew')
        
        # Orders API URL
        ttk.Label(self.api_fields_frame, text="Orders API:", font=('Segoe UI', 8, 'bold')).grid(row=2, column=0, padx=(0, 5), pady=3, sticky='w')
        self.orders_api_url_var = tk.StringVar(value='http://localhost/manak_auto_fill/get_orders.php')
        self.orders_api_entry = ttk.Entry(self.api_fields_frame, textvariable=self.orders_api_url_var, width=55, style='Compact.TEntry', font=('Segoe UI', 8))
        self.orders_api_entry.grid(row=2, column=1, padx=(0, 5), pady=3, sticky='ew')
        
        # Report API URL
        ttk.Label(self.api_fields_frame, text="Report API:", font=('Segoe UI', 8, 'bold')).grid(row=3, column=0, padx=(0, 5), pady=3, sticky='w')
        self.report_api_url_var = tk.StringVar(value='https://hallmarkpro.prosenjittechhub.com/admin/get_report_by_id.php')
        self.report_api_entry = ttk.Entry(self.api_fields_frame, textvariable=self.report_api_url_var, width=55, style='Compact.TEntry', font=('Segoe UI', 8))
        self.report_api_entry.grid(row=3, column=1, padx=(0, 5), pady=3, sticky='ew')
        
        # API Key
        ttk.Label(self.api_fields_frame, text="API Key:", font=('Segoe UI', 8, 'bold')).grid(row=4, column=0, padx=(0, 5), pady=3, sticky='w')
        self.api_key_var = tk.StringVar(value='')
        self.api_key_entry = ttk.Entry(self.api_fields_frame, textvariable=self.api_key_var, width=55, style='Compact.TEntry', show='*', font=('Segoe UI', 8))
        self.api_key_entry.grid(row=4, column=1, padx=(0, 5), pady=3, sticky='ew')
        
        # Initially hide API fields
        self.api_fields_frame.pack_forget()
        
        # Bind keyboard shortcut Ctrl+Shift+P
        self.root.bind('<Control-Shift-Key-P>', lambda e: self.toggle_api_visibility())
        
        # Save Settings Button - Always visible at bottom
        save_frame = ttk.Frame(settings_frame)
        save_frame.pack(fill='x', padx=10, pady=10)
        
        save_btn = ttk.Button(save_frame, text="💾 Save Settings", style='Success.TButton', command=self.save_settings, width=20)
        save_btn.pack()
        
    def toggle_api_visibility(self):
        """Toggle API settings visibility based on password or shortcut"""
        try:
            # Check if password is entered or shortcut was used
            password = self.api_password_var.get().strip()
            
            # Default password for API access (you can change this)
            default_password = "manak2024"
            
            # Check if API fields are currently visible
            is_visible = hasattr(self, '_api_visible') and self._api_visible
            
            if is_visible:
                # If visible, hide without password
                self.api_fields_frame.pack_forget()
                self.reveal_btn.configure(text="⚙️ Show Settings")
                self._api_visible = False
                self.api_password_var.set("")
                self.log("🔒 Settings hidden", 'status')
            else:
                # If hidden, require password to reveal
                if password == default_password:
                    # Show API fields
                    self.api_fields_frame.pack(fill='x', pady=(8, 0))
                    self.reveal_btn.configure(text="🔒 Hide Settings")
                    self._api_visible = True
                    self.api_password_var.set("")
                    self.log("🔓 Settings revealed", 'status')
                else:
                    messagebox.showwarning("Access Denied", "Incorrect password")
                    self.api_password_var.set("")
                
        except Exception as e:
            self.log(f"❌ Error toggling API visibility: {str(e)}", 'status')
        
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
                self.submit_btn.configure(state='disabled')
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
    
    def open_browser(self):
        """Open visible Chrome browser and go directly to login page"""
        try:
            self.log("🚀 Starting Chrome browser...")
            chrome_options = Options()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1280,720")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--allow-running-insecure-content")
            chrome_options.add_experimental_option("detach", True)
            
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
                self.multiple_jobs_processor.driver = self.driver
                self.multiple_jobs_processor.main_log_callback = self.log
            
            
            if self.job_cards_processor:
                self.job_cards_processor.driver = self.driver
                self.job_cards_processor.main_log_callback = self.log
            
            if self.delivery_voucher_processor:
                self.delivery_voucher_processor.driver = self.driver
                self.delivery_voucher_processor.main_log_callback = self.log
            
            if hasattr(self, 'weight_capture_processor') and self.weight_capture_processor:
                self.weight_capture_processor.driver = self.driver
                self.weight_capture_processor.main_log_callback = self.log
            
            # Update HUID data processor with driver now that it's available
            if hasattr(self, 'huid_data_processor') and self.huid_data_processor:
                self.huid_data_processor.driver = self.driver
                self.huid_data_processor.main_log_callback = self.log
            
            self.log("✅ Browser opened successfully!")
            
            # Go directly to login page
            self.driver.get("https://huid.manakonline.in/MANAK/eBISLogin")
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
        """Navigate to MANAK portal login page"""
        if not self.driver:
            messagebox.showwarning("No Browser", "Please open browser first")
            return
            
        try:
            self.log("🔑 Navigating to MANAK portal login page...")
            portal_url = "https://huid.manakonline.in/MANAK/eBISLogin"
            self.driver.get(portal_url)
            time.sleep(3)
            self._auto_fill_login_credentials()
            
            current_url = self.driver.current_url
            self.log(f"✅ Navigated to: {current_url}")
            self.log("👤 Please complete login manually (including CAPTCHA)")
            
        except Exception as e:
            self.log(f"❌ Error navigating to portal: {str(e)}")

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
            else:
                            self.logged_in = True
            self.log("✅ Login appears successful!")
            self.submit_manak_btn.config(state='normal')
                
        except Exception as e:
            self.log(f"❌ Error checking login: {str(e)}")
            
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
            weight_url = f"https://huid.manakonline.in/MANAK/SamplingweightingDeatils?requestNo={request_no}"
            if job_no:
                weight_url += f"&jobNo={job_no}"
                
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
                self.auto_fill_btn.config(state='normal')
                self.select_lot_btn.config(state='normal')
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
            self.submit_manak_btn.config(state='disabled')
            
            self.log("✅ Browser closed")
            
        except Exception as e:
            self.log(f"❌ Error closing browser: {str(e)}")

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
        """Setup Accept Request tab with full automation"""
        accept_frame = ttk.Frame(self.notebook)
        self.notebook.add(accept_frame, text="✅ Accept Request")
        
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
        
        # Auto-print voucher checkbox (always enabled now)
        auto_print_label = ttk.Label(settings_frame, text="✅ Voucher Print: Always enabled", 
                                   font=('Segoe UI', 8, 'italic'), foreground='#28a745')
        auto_print_label.pack(anchor='w', pady=2)
        
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
        
    def fetch_request_list(self):
        """Fetch request list from MANAK portal"""
        # Check license before API operations
        if not self.check_license_before_action("request list fetching"):
            return
            
        if not self.driver or not self.logged_in:
            messagebox.showwarning("Not Ready", "Please open browser and login first")
            return
            
        self.log("🔍 Fetching request list...", 'acknowledge')
        threading.Thread(target=self._fetch_request_list_worker, daemon=True).start()
        
    def _fetch_request_list_worker(self):
        """Worker thread for fetching request list"""
        loading_dialog = None
        try:
            loading_dialog = LoadingDialog(self.root, "Fetching Requests", "Loading request list from MANAK portal...")
            
            # Navigate to request list page
            loading_dialog.update_status("Navigating to request list page...")
            request_list_url = "https://huid.manakonline.in/MANAK/assayingAH_List?hmType=HMRD"
            self.driver.get(request_list_url)
            time.sleep(1)  # Reduced from 3 to 1 second
            
            # Wait for page to load
            loading_dialog.update_status("Waiting for page to load...")
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            
            # Find the request table
            loading_dialog.update_status("Parsing request table...")
            tables = self.driver.find_elements(By.TAG_NAME, "table")
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
                raise Exception("Request table not found")
            
            # Parse table data
            loading_dialog.update_status("Extracting request data...")
            rows = request_table.find_elements(By.TAG_NAME, "tr")
            requests = []
            
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
                            requests.append({
                                's_no': s_no,
                                'request_no': request_no,
                                'request_date': request_date,
                                'jeweller_name': jeweller_name,
                                'jeweller_address': jeweller_address,
                                'status': status,
                                'acknowledge_url': acknowledge_link
                            })
                            
                except Exception as e:
                    self.log(f"⚠️ Error parsing row {i}: {str(e)}", 'acknowledge')
                    continue
            
            # Update UI with request data
            self.root.after(0, self._update_request_list_ui, requests)
            
            loading_dialog.update_status("Done!")
            loading_dialog.update_message(f"Found {len(requests)} requests")
            time.sleep(1)
            loading_dialog.close()
            
            if requests:
                self.log(f"✅ Successfully fetched {len(requests)} requests", 'acknowledge')
                messagebox.showinfo("Success", f"✅ Found {len(requests)} requests to acknowledge!")
            else:
                self.log("⚠️ No requests found to acknowledge", 'acknowledge')
                messagebox.showwarning("No Requests", "No requests found to acknowledge")
                
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
        
        # Add requests to treeview
        for request in requests:
            self.request_tree.insert('', 'end', values=(
                request['s_no'],
                request['request_no'],
                request['request_date'],
                request['jeweller_name'],
                request['jeweller_address'],
                request['status'],
                "🔄 Acknowledge"
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
            
    def _acknowledge_single_request_internal(self, request):
        """Internal method to acknowledge a single request"""
        try:
            # Step 1: Open acknowledge page
            self.log(f"🔗 Opening acknowledge page for request {request['request_no']}", 'acknowledge')
            self.driver.get(request['acknowledge_url'])
            time.sleep(2)  # Give page time to load
            
            # Step 2: Wait for page to load and verify we're on the right page
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "form"))
                )
                
                # Check if we're on the acknowledge page by looking for key elements
                page_title = self.driver.title
                self.log(f"📄 Page loaded: {page_title}", 'acknowledge')
                
                # Check current URL
                current_url = self.driver.current_url
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
                tag_id_yes_radio = self.driver.find_element(By.ID, "strRadioTag_yes")
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
                    tag_id_yes_radio = self.driver.find_element(By.XPATH, "//input[@name='strRadioTag' and @value='Y']")
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
                        yes_label = self.driver.find_element(By.XPATH, "//label[contains(text(), 'Yes')]//input[@type='radio']")
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
            
            # Auto-fill quantity and weight if enabled
            if self.auto_fill_qty_weight_var.get():
                self._auto_fill_quantity_and_weight()
            else:
                self.log("ℹ️ Auto-fill quantity/weight is disabled", 'acknowledge')
            
            # Skip filling AHC Receiving Remarks - not needed
            self.log("ℹ️ Skipping AHC Receiving Remarks (not required)", 'acknowledge')
            
            # Step 4: Click Add button - Try multiple methods
            add_button_clicked = False
            
            # Method 1: Standard Add button
            try:
                add_button = self.driver.find_element(By.XPATH, "//input[@type='button' and @value='Add']")
                if add_button.is_displayed() and add_button.is_enabled():
                    add_button.click()
                    self.log("✅ Clicked Add button (Method 1)", 'acknowledge')
                    time.sleep(1.5)
                    add_button_clicked = True
                else:
                    self.log("⚠️ Add button found but not interactable", 'acknowledge')
            except Exception as e:
                self.log(f"⚠️ Add button Method 1 failed: {str(e)}", 'acknowledge')
            
            # Method 2: Try button tag
            if not add_button_clicked:
                try:
                    add_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Add')]")
                    if add_button.is_displayed() and add_button.is_enabled():
                        add_button.click()
                        self.log("✅ Clicked Add button (Method 2)", 'acknowledge')
                        time.sleep(1.5)
                        add_button_clicked = True
                except Exception as e:
                    self.log(f"⚠️ Add button Method 2 failed: {str(e)}", 'acknowledge')
            
            # Method 3: Try submit button
            if not add_button_clicked:
                try:
                    submit_button = self.driver.find_element(By.XPATH, "//input[@type='submit']")
                    if submit_button.is_displayed() and submit_button.is_enabled():
                        submit_button.click()
                        self.log("✅ Clicked Submit button (Method 3)", 'acknowledge')
                        time.sleep(1.5)
                        add_button_clicked = True
                except Exception as e:
                    self.log(f"⚠️ Submit button Method 3 failed: {str(e)}", 'acknowledge')
            
            if not add_button_clicked:
                self.log("❌ Could not find or click Add/Submit button", 'acknowledge')
                self.log("📸 Saving page source for debugging...", 'acknowledge')
                try:
                    # Save page source to help debug
                    page_source = self.driver.page_source
                    debug_file = f"debug_acknowledge_{request['request_no']}.html"
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(page_source)
                    self.log(f"💾 Page source saved to {debug_file}", 'acknowledge')
                except:
                    pass
                return False
            
            # Step 5: Handle the redirect and accept all items
            current_url = self.driver.current_url
            if 'message=' in current_url:
                self.log("🔄 Redirected to accept page, accepting all items...", 'acknowledge')
                
                # Wait for page to fully load
                time.sleep(0.5)  # Reduced from 2 to 0.5 seconds
                
                # Step 5a: Find and click the "select all" checkbox with multiple methods
                select_all_clicked = False
                
                # Method 1: Try by exact class name and structure
                try:
                    select_all_checkbox = self.driver.find_element(By.XPATH, "//th[contains(text(), 'Accept')]//input[@type='checkbox' and contains(@class, 'selectall')]")
                    if select_all_checkbox.is_displayed():
                        if not select_all_checkbox.is_selected():
                            select_all_checkbox.click()
                            time.sleep(0.3)  # Reduced from 1 to 0.3 seconds
                            self.log("✅ Clicked 'Select All' checkbox in Accept header (Method 1)", 'acknowledge')
                            select_all_clicked = True
                        else:
                            self.log("✅ Select All checkbox already selected", 'acknowledge')
                            select_all_clicked = True
                except Exception as e:
                    self.log(f"⚠️ Method 1 failed: {str(e)}", 'acknowledge')
                
                # Method 2: Try by finding checkbox in Accept column header
                if not select_all_clicked:
                    try:
                        # Find table with Accept column
                        tables = self.driver.find_elements(By.TAG_NAME, "table")
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
                                        self.log("✅ Clicked 'Select All' checkbox (Method 2)", 'acknowledge')
                                        select_all_clicked = True
                                        break
                            except:
                                continue
                    except Exception as e:
                        self.log(f"⚠️ Method 2 failed: {str(e)}", 'acknowledge')
                
                # Method 3: Try by finding first checkbox in table
                if not select_all_clicked:
                    try:
                        select_all_checkbox = self.driver.find_element(By.XPATH, "//table//input[@type='checkbox'][1]")
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
                    voucher_link = self.driver.find_element(By.XPATH, "//a[contains(@href, 'getAHCRceiptJrxmlReportVoucher')]")
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
                        voucher_link = self.driver.find_element(By.XPATH, "//a[contains(text(), 'Voucher Print')]")
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
                        voucher_button = self.driver.find_element(By.XPATH, "//input[@type='button' and contains(@value, 'Voucher')]")
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
                        voucher_element = self.driver.find_element(By.XPATH, "//*[contains(text(), 'Voucher') and contains(text(), 'Print')]")
                        if voucher_element.is_displayed():
                            voucher_element.click()
                            time.sleep(0.5)  # Reduced from 2 to 0.5 seconds
                            self.log("✅ Clicked Voucher Print element (Method 4)", 'acknowledge')
                            voucher_clicked = True
                    except Exception as e:
                        self.log(f"⚠️ Voucher Method 4 failed: {str(e)}", 'acknowledge')
                
                if not voucher_clicked:
                    self.log("❌ Could not find or click Voucher Print", 'acknowledge')
                
                # Step 7: Click Submit with multiple methods
                submit_clicked = False
                
                # Method 1: Try by value="Submit"
                try:
                    submit_button = self.driver.find_element(By.XPATH, "//input[@type='button' and @value='Submit']")
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
                        submit_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Submit')]")
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
                        submit_element = self.driver.find_element(By.XPATH, "//*[contains(text(), 'Submit')]")
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
                    alert = self.driver.switch_to.alert
                    alert_text = alert.text
                    self.log(f"🔔 Alert: {alert_text}", 'acknowledge')
                    alert.accept()
                    time.sleep(1)
                except:
                    pass
                    
                return True
            else:
                self.log("⚠️ Expected redirect did not occur", 'acknowledge')
                return False
                
        except Exception as e:
            self.log(f"❌ Error in acknowledge workflow: {str(e)}", 'acknowledge')
            return False
            
    def _auto_fill_quantity_and_weight(self):
        """Auto-fill quantity and weight from the item declaration table"""
        try:
            # Find the item declaration table
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            
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
                            self.log("📊 Found item declaration table", 'acknowledge')
                            
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
                                            
                                        self.log(f"✅ Auto-filled: Qty={declared_qty}, Weight={declared_weight}", 'acknowledge')
                                        
                                    except Exception as e:
                                        self.log(f"⚠️ Error filling row data: {str(e)}", 'acknowledge')
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
                        self.log(f"✅ Auto-filled Observed Net Weight: {total_weight}", 'acknowledge')
                
                # Observed net Quantity
                observed_qty_field = self.driver.find_element(By.NAME, "observedNetQuantity")
                if observed_qty_field.is_displayed() and observed_qty_field.is_enabled():
                    # Get total quantity from the table
                    total_qty = self._get_total_quantity_from_table()
                    if total_qty:
                        observed_qty_field.clear()
                        observed_qty_field.send_keys(total_qty)
                        self.log(f"✅ Auto-filled Observed Net Quantity: {total_qty}", 'acknowledge')
                        
            except Exception as e:
                self.log(f"⚠️ Error filling main fields: {str(e)}", 'acknowledge')
                
        except Exception as e:
            self.log(f"❌ Error in auto-fill quantity and weight: {str(e)}", 'acknowledge')
            
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
            generator = RequestGenerator(
                self.driver, 
                self.log, 
                self.default_state_var, 
                self.auto_fill_item_details_var
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
                    from selenium.webdriver.support.ui import Select
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
                c1_init_val = float(c1_initial.get().strip() or 0)
                c1_m2_val = float(c1_m2.get().strip() or 0)
                c2_init_val = float(c2_initial.get().strip() or 0)
                c2_m2_val = float(c2_m2.get().strip() or 0)
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
    

if __name__ == "__main__":
    app = ManakDesktopApp()
    app.run()