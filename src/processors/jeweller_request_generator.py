"""
Jeweller Request Generator
Allows users to select a jeweller from the database and automatically fill the AHC Request Submission form
"""

import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
from config import JEWELLER_API_URL, DB_CONFIG
import config
import requests
import base64
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
import time




class JewellerRequestGenerator:
    def __init__(self, notebook, driver=None, main_log_callback=None, license_manager=None):
        self.notebook = notebook
        self.driver = driver
        self.log = main_log_callback if main_log_callback else print
        self.license_manager = license_manager
        
        # Data storage
        self.jewellers_data = []
        self.selected_jeweller = None
        
        # Create UI
        self.create_ui()
        
    def create_ui(self):
        """Create the main UI for jeweller request generator"""
        # Create tab frame
        jeweller_frame = ttk.Frame(self.notebook)
        self.notebook.add(jeweller_frame, text="💎 Generate Request")
        
        # Main container
        main_container = ttk.Frame(jeweller_frame)
        main_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Header
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill='x', pady=(0, 10))
        
        header_label = ttk.Label(header_frame, text="Jeweller Request Generator", 
                                font=('Segoe UI', 14, 'bold'))
        header_label.pack(side='left')
        
        # Add Jeweller button
        add_btn = ttk.Button(header_frame, text="➕ Add Jeweller", 
                            style='Primary.TButton', command=self._show_add_jeweller_modal)
        add_btn.pack(side='right', padx=5)

        # Refresh button
        refresh_btn = ttk.Button(header_frame, text="🔄 Refresh List", 
                                style='Info.TButton', command=self.load_jewellers)
        refresh_btn.pack(side='right', padx=5)
        
        # Generate Request button
        self.generate_btn = ttk.Button(header_frame, text="📝 Generate Request", 
                                      style='Success.TButton', command=self.generate_request,
                                      state='disabled')
        self.generate_btn.pack(side='right')
        
        # Search frame
        search_frame = ttk.LabelFrame(main_container, text="🔍 Search Jeweller", 
                                     style='Compact.TLabelframe')
        search_frame.pack(fill='x', pady=(0, 10))
        
        search_container = ttk.Frame(search_frame)
        search_container.pack(fill='x', padx=8, pady=8)
        
        ttk.Label(search_container, text="Search:", font=('Segoe UI', 9, 'bold')).pack(side='left', padx=(0, 5))
        
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_container, textvariable=self.search_var, width=40)
        self.search_entry.pack(side='left', fill='x', expand=True)
        self.search_entry.bind('<KeyRelease>', self.on_search)
        
        # Jewellers table frame
        table_frame = ttk.LabelFrame(main_container, text="📋 Jewellers List", 
                                    style='Compact.TLabelframe')
        table_frame.pack(fill='both', expand=True)
        
        table_container = ttk.Frame(table_frame)
        table_container.pack(fill='both', expand=True, padx=8, pady=8)
        
        # Create treeview with scrollbars
        tree_scroll_y = ttk.Scrollbar(table_container, orient='vertical')
        tree_scroll_y.pack(side='right', fill='y')
        
        tree_scroll_x = ttk.Scrollbar(table_container, orient='horizontal')
        tree_scroll_x.pack(side='bottom', fill='x')
        
        self.jewellers_tree = ttk.Treeview(
            table_container,
            columns=('serial_no', 'name', 'licence_no', 'address', 'state', 'contact', 'gst'),
            show='headings',
            yscrollcommand=tree_scroll_y.set,
            xscrollcommand=tree_scroll_x.set,
            height=15
        )
        
        tree_scroll_y.config(command=self.jewellers_tree.yview)
        tree_scroll_x.config(command=self.jewellers_tree.xview)
        
        # Define columns
        self.jewellers_tree.heading('serial_no', text='S.No')
        self.jewellers_tree.heading('name', text='Jeweller Name')
        self.jewellers_tree.heading('licence_no', text='License No')
        self.jewellers_tree.heading('address', text='Address')
        self.jewellers_tree.heading('state', text='State')
        self.jewellers_tree.heading('contact', text='Contact')
        self.jewellers_tree.heading('gst', text='GST')
        
        # Set column widths
        self.jewellers_tree.column('serial_no', width=50)
        self.jewellers_tree.column('name', width=250)
        self.jewellers_tree.column('licence_no', width=150)
        self.jewellers_tree.column('address', width=240)
        self.jewellers_tree.column('state', width=120)
        self.jewellers_tree.column('contact', width=120)
        self.jewellers_tree.column('gst', width=150)
        
        self.jewellers_tree.pack(fill='both', expand=True)
        
        # Bind selection event
        self.jewellers_tree.bind('<<TreeviewSelect>>', self.on_jeweller_select)
        
        # Status bar
        status_frame = ttk.Frame(main_container)
        status_frame.pack(fill='x', pady=(10, 0))
        
        self.status_label = ttk.Label(status_frame, text="Ready. Click 'Refresh List' to load jewellers.", 
                                     font=('Segoe UI', 9))
        self.status_label.pack(side='left')
        
        # Auto-load jewellers
        # Auto-load jewellers - MOVED to main app after license check
        # self.load_jewellers()
        
    def load_jewellers(self):
        """Load jewellers from database"""
        try:
            self.log(f"📊 Loading jewellers...", 'status')
            self.status_label.config(text="Loading jewellers...")
            
            # Clear existing data
            for item in self.jewellers_tree.get_children():
                self.jewellers_tree.delete(item)
            self.jewellers_data = []
            
            # Fetch from API
            firm_id = 2
            if hasattr(self, 'license_manager') and self.license_manager:
                firm_id = getattr(self.license_manager, 'firm_id', 2)
                
            try:
                response = requests.get(f"{config.JEWELLER_API_URL}?firm_id={firm_id}", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success', False):
                        original_jewellers_data = data.get('data', [])
                        # Remap keys if necessary (API returns exact column names, so minimal mapping)
                        jewellers = original_jewellers_data
                    else:
                        raise Exception(f"API returned error: {data.get('message', 'Unknown error')}")
                else:
                    raise Exception(f"Failed to connect to API (Status: {response.status_code})")
                    
            except requests.exceptions.RequestException as req_err:
                # If API fails, try direct DB connection as fallback (optional, or just raise)
                # For shared hosting, direct connection likely fails too, so we report the API error
                raise Exception(f"Connection Error: {str(req_err)}")
            
            # Populate table
            for idx, jeweller in enumerate(jewellers, 1):
                self.jewellers_data.append(jeweller)
                self.jewellers_tree.insert('', 'end', values=(
                    idx,
                    jeweller.get('Jewellers_Name', ''),
                    jeweller.get('licence_no', ''),
                    jeweller.get('Address1', jeweller.get('address1', '')),
                    jeweller.get('State', ''),
                    jeweller.get('Contact_no', ''),
                    jeweller.get('GST', '')
                ))
            
            count = len(jewellers)
            self.status_label.config(text=f"✅ Loaded {count} jewellers")
            self.log(f"✅ Loaded {count} jewellers from API", 'status')
            
        except Exception as e:
            self.log(f"❌ Error loading jewellers: {str(e)}", 'status')
            self.status_label.config(text=f"❌ Error: {str(e)}")
            messagebox.showerror("Database Error", f"Failed to load jewellers:\n{str(e)}")
            
    def on_search(self, event=None):
        """Filter jewellers based on search text"""
        search_text = self.search_var.get().lower()
        
        # Clear tree
        for item in self.jewellers_tree.get_children():
            self.jewellers_tree.delete(item)
        
        # Repopulate with filtered data
        for idx, jeweller in enumerate(self.jewellers_data, 1):
            name = str(jeweller.get('Jewellers_Name', '')).lower()
            licence = str(jeweller.get('licence_no', '')).lower()
            address = str(jeweller.get('Address1', jeweller.get('address1', ''))).lower()
            state = str(jeweller.get('State', '')).lower()
            
            if (search_text in name or search_text in licence or 
                search_text in address or search_text in state):
                self.jewellers_tree.insert('', 'end', values=(
                    idx,
                    jeweller.get('Jewellers_Name', ''),
                    jeweller.get('licence_no', ''),
                    jeweller.get('Address1', jeweller.get('address1', '')),
                    jeweller.get('State', ''),
                    jeweller.get('Contact_no', ''),
                    jeweller.get('GST', '')
                ))
                
    def on_jeweller_select(self, event=None):
        """Handle jeweller selection"""
        selection = self.jewellers_tree.selection()
        if selection:
            item = self.jewellers_tree.item(selection[0])
            licence_no = item['values'][2]
            
            # Find full jeweller data
            for jeweller in self.jewellers_data:
                if str(jeweller.get('licence_no', '')) == str(licence_no):
                    self.selected_jeweller = jeweller
                    self.generate_btn.config(state='normal')
                    self.status_label.config(
                        text=f"✅ Selected: {jeweller.get('Jewellers_Name', '')} - {jeweller.get('licence_no', '')}"
                    )
                    self.log(f"✅ Selected jeweller: {jeweller.get('Jewellers_Name', '')}", 'status')
                    break
        else:
            self.selected_jeweller = None
            self.generate_btn.config(state='disabled')
            self.status_label.config(text="Select a jeweller to generate request")
            
    def generate_request(self):
        """Navigate to AHC Request Submission and auto-fill"""
        if not self.selected_jeweller:
            messagebox.showwarning("No Selection", "Please select a jeweller first")
            return
            
        if not self.driver:
            messagebox.showwarning("Browser Not Open", "Please open browser first from the Browser Control tab")
            return
            
        # Check driver validity
        try:
            _ = self.driver.current_url
        except:
            self.driver = None
            messagebox.showerror("Browser Disconnected", "Browser is closed or disconnected. Please open it again from the Login tab.")
            return
            
        try:
            self.log("🚀 Generating AHC request for jeweller...", 'status')
            self.status_label.config(text="Generating request...")
            
            # Get jeweller details
            jeweller_name = self.selected_jeweller.get('Jewellers_Name', '')
            licence_no = self.selected_jeweller.get('licence_no', '')
            state = self.selected_jeweller.get('State', '')
            
            self.log(f"📋 Jeweller: {jeweller_name}", 'status')
            self.log(f"📜 License: {licence_no}", 'status')
            self.log(f"📍 State: {state}", 'status')
            
            # 1. Get dynamic URL from app settings if available
            try:
                import json
                with open('config/app_settings.json', 'r') as f:
                    settings = json.load(f)
                    from portal_config import get_default_portal_generate_url, swap_portal_base_in_url
                    env = settings.get('portal_env')
                    raw = settings.get('portal_generate_url') or get_default_portal_generate_url(env)
                    BASE_URL = swap_portal_base_in_url(raw, env) if env else raw
            except:
                from portal_config import get_default_portal_generate_url
                BASE_URL = get_default_portal_generate_url()

            self.log(f"🔗 Using URL: {BASE_URL}", 'status')
            self.driver.get(BASE_URL)
            self.log("✅ Navigated to AHC Request Submission page", 'status')
            
            # Wait for page to load quickly by checking for the hidden select elements
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "state"))
                )
                self.log("✅ Page elements loaded", 'status')
            except:
                self.log("⚠️ Page load timeout or element not found, attempting to continue anyway", 'status')
            
            time.sleep(0.5) # Wait lightly just to be safe for JS initialization
            
            # --- FAST JAVASCRIPT SELECTION ---
            import json
            state_candidates = [s for s in [state] if s]
            try:
                import json as _json
                with open('config/app_settings.json', 'r', encoding='utf-8') as _f:
                    _settings = _json.load(_f)
                default_st = (_settings.get('default_state') or '').strip()
                if default_st and default_st not in state_candidates:
                    state_candidates.append(default_st)
            except Exception:
                pass
            if not state_candidates:
                import re
                addr = self.selected_jeweller.get('Address1', self.selected_jeweller.get('address1', ''))
                m = re.search(r'\b(110\d{3})\b', str(addr))
                if m:
                    state_candidates.append('Delhi')

            # 1. State Selection via JS
            try:
                self.log(f"⚡ Fast JS selection for state: {state_candidates}", 'status')
                states_json = json.dumps([str(s).lower() for s in state_candidates if s])
                state_js = f"""
                var s = document.getElementById('state');
                var candidates = {states_json};
                var found = false;
                if (s && candidates.length) {{
                    for (var i = 0; i < s.options.length; i++) {{
                        var opt = s.options[i].text.toLowerCase();
                        for (var c = 0; c < candidates.length; c++) {{
                            if (opt.includes(candidates[c]) || candidates[c].includes(opt)) {{
                                s.selectedIndex = i;
                                found = true;
                                break;
                            }}
                        }}
                        if (found) break;
                    }}
                    if (found && typeof jQuery !== 'undefined') {{ $(s).trigger('change'); }}
                }}
                return found;
                """
                success = self.driver.execute_script(state_js)
                
                if success:
                    self.log(f"✅ State selected instantly", 'status')
                else:
                    self.log(f"⚠️ State '{state}' not found in dropdown", 'status')
                
                # Wait for AJAX to load Jewellers in 'city' (jeweller) dropdown
                self.log("⏳ Waiting 1s for Jewellers list to load...", 'status')
                time.sleep(1.0) 
            except Exception as e:
                self.log(f"❌ JS State selection failed: {str(e)}", 'status')

            # 2. Jeweller Selection via JS (license no, then jeweller name)
            try:
                self.log(f"⚡ Fast JS selection for jeweller: {jeweller_name} / {licence_no}", 'status')
                match_terms = json.dumps([
                    str(licence_no).lower(),
                    str(jeweller_name).lower(),
                ])
                jeweller_js = f"""
                var j = document.getElementById('city');
                var terms = {match_terms};
                var found = false;
                if (j) {{
                    for (var i = 0; i < j.options.length; i++) {{
                        var opt = j.options[i].text.toLowerCase();
                        for (var t = 0; t < terms.length; t++) {{
                            if (terms[t] && opt.includes(terms[t])) {{
                                j.selectedIndex = i;
                                found = true;
                                break;
                            }}
                        }}
                        if (found) break;
                    }}
                    if (found && typeof jQuery !== 'undefined') {{ $(j).trigger('change'); }}
                }}
                return found;
                """
                success = self.driver.execute_script(jeweller_js)
                
                if success:
                    self.log(f"✅ Jeweller selected instantly", 'status')
                else:
                    self.log(f"⚠️ Jeweller with license '{licence_no}' not found in dropdown", 'status')
                    
            except Exception as e:
                self.log(f"❌ JS Jeweller selection failed: {str(e)}", 'status')
                
            # 3. Auto-Click "Add Items" button
            try:
                self.log("🖱️ Clicking 'Add Items' button...", 'status')
                time.sleep(0.5)
                
                # First try click via explicit Wait
                try:
                    add_items_btn = WebDriverWait(self.driver, 2).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Add Items')] | //input[@value='Add Items'] | //a[contains(text(), 'Add Items')]"))
                    )
                    add_items_btn.click()
                    self.log("✅ 'Add Items' button clicked via UI", 'status')
                except:
                    # Fallback to JS click
                    click_js = """
                    var btns = document.querySelectorAll('button, input[type="button"], input[type="submit"], a');
                    for(var i=0; i<btns.length; i++){
                        if(btns[i].innerText.includes('Add Items') || btns[i].value.includes('Add Items')){
                            btns[i].click();
                            return true;
                        }
                    }
                    return false;
                    """
                    success = self.driver.execute_script(click_js)
                    if success:
                        self.log("✅ 'Add Items' button clicked via JS fallback", 'status')
                    else:
                        self.log("⚠️ Could not find 'Add Items' button via JS", 'status')
                        
            except Exception as e:
                self.log(f"❌ Add Items click failed: {str(e)}", 'status')

            self.status_label.config(text=f"✅ Form ready for: {jeweller_name}")
            self.log("✅ AHC Request form auto-filled successfully!", 'status')
            
            messagebox.showinfo("Success", 
                              f"Request form opened and auto-filled for:\n\n"
                              f"Jeweller: {jeweller_name}\n"
                              f"License: {licence_no}\n"
                              f"State: {state}\n\n"
                              f"Please review the form and click 'Add Items'.")
            
        except Exception as e:
            error_msg = f"Error generating request: {str(e)}"
            self.log(f"❌ {error_msg}", 'status')
            self.status_label.config(text="❌ Error generating request")
            messagebox.showerror("Error", error_msg)

    def _show_add_jeweller_modal(self):
        """Show modal dialog to add a new jeweller"""
        modal = tk.Toplevel(self.notebook)
        modal.title("Add New Jeweller")
        modal.geometry("500x600")
        modal.transient(self.notebook.winfo_toplevel())  # Set as dialog
        modal.grab_set()  # Modal behavior
        
        # Center the modal
        modal.update_idletasks()
        width = modal.winfo_width()
        height = modal.winfo_height()
        x = (modal.winfo_screenwidth() // 2) - (width // 2)
        y = (modal.winfo_screenheight() // 2) - (height // 2)
        modal.geometry(f'{width}x{height}+{x}+{y}')
        
        container = ttk.Frame(modal, padding="20")
        container.pack(fill='both', expand=True)
        
        ttk.Label(container, text="Add New Jeweller", font=('Segoe UI', 12, 'bold')).pack(pady=(0, 20))
        
        fields_frame = ttk.Frame(container)
        fields_frame.pack(fill='both', expand=True)
        
        # Fields Configuration
        fields = [
            ("Jeweller Name *", "name"),
            ("License Number *", "licence_no"),
            ("Address", "address"),
            ("City", "city"),
            ("State", "state"),
            ("Contact No", "contact"),
            ("GST No", "gst"),
            ("PAN No", "pan")
        ]
        
        entries = {}
        
        for i, (label_text, key) in enumerate(fields):
            row_frame = ttk.Frame(fields_frame)
            row_frame.pack(fill='x', pady=5)
            
            ttk.Label(row_frame, text=label_text, width=15).pack(side='left')
            entry = ttk.Entry(row_frame)
            entry.pack(side='right', fill='x', expand=True)
            entries[key] = entry
            
        # Error Label
        error_lbl = ttk.Label(container, text="", foreground="red")
        error_lbl.pack(pady=5)
        
        def save():
            data = {k: v.get().strip() for k, v in entries.items()}
            
            # Validation
            if not data['name']:
                error_lbl.config(text="Jeweller Name is required!")
                return
            if not data['licence_no']:
                error_lbl.config(text="License Number is required!")
                return
                
            # Call API
            try:
                firm_id = 2
                if hasattr(self, 'license_manager') and self.license_manager:
                    firm_id = getattr(self.license_manager, 'firm_id', 2)
                
                payload = {
                    "action": "create",
                    "firm_id": firm_id,
                    "name": data['name'],
                    "licence_no": data['licence_no'],
                    "address": data['address'],
                    "city": data['city'],
                    "state": data['state'],
                    "contact_no": data['contact'], # Map to correct DB columns if API exposes them
                    "gst": data['gst'],
                    "pan": data['pan']
                }
                
                # Note: The server PHP script currently only handles name, address, city, state. 
                # Extended fields might be ignored unless script is updated, but sending them is fine.
                
                response = requests.post(config.JEWELLER_API_URL, json=payload, timeout=10)
                
                if response.status_code == 200:
                    resp_data = response.json()
                    if resp_data.get('success'):
                        messagebox.showinfo("Success", "Jeweller added successfully!")
                        modal.destroy()
                        self.load_jewellers() # Refresh list
                    else:
                        error_lbl.config(text=f"Error: {resp_data.get('message')}")
                else:
                    error_lbl.config(text=f"Server Error: {response.status_code}")
                    
            except Exception as e:
                error_lbl.config(text=f"Connection Error: {str(e)}")
        
        # Buttons
        btn_frame = ttk.Frame(container)
        btn_frame.pack(fill='x', pady=20)
        
        ttk.Button(btn_frame, text="Cancel", command=modal.destroy).pack(side='right', padx=5)
        ttk.Button(btn_frame, text="Save Jeweller", style='Success.TButton', command=save).pack(side='right', padx=5)
