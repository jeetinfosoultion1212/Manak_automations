"""
License verification methods to be added to ManakDesktopApp class
"""

def start_periodic_verification(self):
    """Start background license verification"""
    if not hasattr(self, '_verification_timer'):
        self._verification_timer = self.root.after(1800000, self._verify_periodic)  # 30 minutes

def _verify_periodic(self):
    """Periodic license verification"""
    if self.license_manager:
        if not self.license_manager.check_license():
            self.license_verified = False
            self.update_ui_state()
            self.force_license_setup()
        else:
            self._verification_timer = self.root.after(1800000, self._verify_periodic)

def update_ui_state(self, enabled=None):
    """Update UI elements based on license status"""
    if enabled is None:
        enabled = self.license_verified
    
    # Update main action buttons
    for btn_name in ['save_btn', 'auto_btn', 'submit_btn']:
        if hasattr(self, btn_name):
            btn = getattr(self, btn_name)
            if isinstance(btn, (tk.Button, ttk.Button)):
                btn.config(state='normal' if enabled else 'disabled')
    
    # Update weight entry fields
    if hasattr(self, 'weight_entries'):
        for entry in self.weight_entries.values():
            if isinstance(entry, (tk.Entry, ttk.Entry)):
                entry.config(state='normal' if enabled else 'disabled')
    
    # Update status indicators
    if hasattr(self, 'status_label'):
        self.status_label.config(
            text="✅ Ready" if enabled else "⚠️ License Required",
            foreground="#2ecc71" if enabled else "#e74c3c"
        )

def force_license_setup(self):
    """Force user to license setup page"""
    if hasattr(self, 'root') and self.root:
        messagebox.showwarning(
            "License Required", 
            "Device license verification is required.\n\n"
            "You will be redirected to the Settings page to verify your license."
        )
        
        if hasattr(self, 'notebook'):
            # Find settings tab index
            for i in range(self.notebook.index('end')):
                if "Settings" in str(self.notebook.tab(i, 'text')):
                    self.notebook.select(i)
                    break
        
        # Disable all features until license is verified
        self.update_ui_state(False)

def check_license_before_action(self, action_name="this action"):
    """Check license before performing critical actions"""
    if not self.license_manager or not self.license_verified:
        if hasattr(self, 'root') and self.root:
            result = messagebox.askquestion(
                "License Required",
                f"You need a valid license to perform {action_name}.\n"
                "Would you like to verify your license now?",
                icon='warning'
            )
            
            if result == 'yes':
                self.force_license_setup()
                return False
        return False
        
    # Check if license is still valid
    if not self.license_manager.check_license():
        self.license_verified = False
        self.force_license_setup()
        return False
        
    return True
