#!/usr/bin/env python3
"""
Weight Capture Processor Module - CLEAN VERSION
Handles automated weight entry from huid_data table to MANAK portal
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import base64

from config import DB_CONFIG

class WeightCaptureProcessor:
    """Handles automated weight capture from database to portal"""
    
    def __init__(self, driver, log_callback, license_check_callback, app_context=None):
        self.driver = driver
        self.log_callback = log_callback
        self.license_check_callback = license_check_callback
        self.app_context = app_context
        self.current_firm_id = 2
        self.current_material_type = "Gold"
        self.jobs_data = []
        self.selected_jobs = set()
        self.weights_cache = {}
        self.log_text = None
        self.jobs_tree = None
        self.progress_var = None
        self.progress_label = None
        self.material_type_label = None
        self.firm_id_label = None
        self.speed_var = None
        self.notebook = None
        self.log_visible = None
        self.log_toggle_btn = None
        self.right_panel = None
        
        # Get firm ID from settings
        self.current_firm_id = self.get_firm_id_from_settings()
    
    def get_firm_id_from_settings(self):
        """Get Firm ID from settings page or device license"""
        try:
            if self.app_context and hasattr(self.app_context, 'device_license'):
                license_data = self.app_context.device_license
                if license_data and 'firm_id' in license_data:
                    return int(license_data['firm_id'])
            return 2
        except Exception as e:
            self.log_callback(f"⚠️ Could not get firm_id: {e}")
            return 2
    
    def refresh_firm_id(self):
        """Refresh firm_id from settings and update display"""
        old_firm_id = self.current_firm_id
        self.current_firm_id = self.get_firm_id_from_settings()
        
        if self.firm_id_label:
            self.firm_id_label.config(text=f"Firm {self.current_firm_id}")
        
        if old_firm_id != self.current_firm_id:
            self.log_weight(f"🏢 Firm ID updated from {old_firm_id} to {self.current_firm_id}")
