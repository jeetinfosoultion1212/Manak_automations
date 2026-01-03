#!/usr/bin/env python3
"""
Enhanced Device License Manager for MANAK Automation
MAC-based licensing with trial support and portal user binding
"""

import requests
import json
import os
import time
import threading
import uuid
import hashlib
import subprocess
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import messagebox

class DeviceLicenseManager:
    def __init__(self):
        self.api_url = "https://hallmarkpro.prosenjittechhub.com/admin/device_license_api.php"
        self.device_id = None
        self.mac_address = None
        self.user_id = None
        self.portal_username = None
        self.portal_password = None
        self.firm_id = None  # Firm ID from device license
        self.cache_file = "license_cache.json"
        self.cache_duration = 1800000000# 30 minutes
        self.last_check_time = 0
        self.check_interval = 1800000  # Check every 30 minutes
        self.license_valid = False
        self.trial_active = False
        self.verification_thread = None
        self.stop_verification = False
        
        # Get device MAC address
        self.mac_address = self._get_mac_address()
        self.device_id = self._generate_device_id()
        
        # Load cached credentials if available
        self._load_cached_credentials()
        
    def _get_mac_address(self):
        """Get the primary MAC address of the device"""
        try:
            # Get MAC address using Windows command
            result = subprocess.check_output(['ipconfig', '/all'], text=True)
            lines = result.split('\n')
            
            for i, line in enumerate(lines):
                if 'Physical Address' in line or 'MAC Address' in line:
                    mac = line.split(':')[-1].strip()
                    if mac and len(mac) == 17:  # Valid MAC format
                        return mac.replace('-', ':')
            
            # Fallback: use UUID as device identifier
            return str(uuid.uuid4())
        except Exception as e:
            print(f"Error getting MAC address: {e}")
            return str(uuid.uuid4())
    
    def _generate_device_id(self):
        """Generate a unique device ID based on MAC address"""
        if self.mac_address:
            return hashlib.md5(self.mac_address.encode()).hexdigest()[:16]
        return str(uuid.uuid4())[:16]
    
    def _load_cached_credentials(self):
        """Load cached credentials from license cache"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
                
                # Check if cache is for this device and has credentials
                if (cache.get('device_id') == self.device_id and 
                    cache.get('portal_username') and 
                    cache.get('portal_password')):
                    
                    self.portal_username = cache.get('portal_username')
                    self.portal_password = cache.get('portal_password')
                    self.license_valid = cache.get('license_valid', False)
                    self.trial_active = cache.get('trial_active', False)
                    
                    print(f"✅ Loaded cached credentials for user: {self.portal_username}")
                    
        except Exception as e:
            print(f"Error loading cached credentials: {e}")
    
    def get_trial_status(self):
        """Get current trial status from server"""
        if not self.device_id:
            return None
            
        try:
            payload = {
                'action': 'check_trial',
                'device_id': self.device_id,
                'portal_username': self.portal_username
            }
            
            response = requests.post(self.api_url, data=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return data.get('trial_info')
            return None
            
        except Exception as e:
            print(f"Error getting trial status: {e}")
            return None
            
    def _get_trial_info(self):
        """Get trial information from cache file"""
        try:
            if os.path.exists('trial_info.json'):
                with open('trial_info.json', 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error reading trial info: {e}")
        return {}
        
    def _save_trial_info(self, trial_info):
        """Save trial information to cache file"""
        try:
            with open('trial_info.json', 'w') as f:
                json.dump(trial_info, f)
        except Exception as e:
            print(f"Error saving trial info: {e}")
    
    def _bind_portal_credentials(self, username, password):
        """Bind portal credentials to this device"""
        # Set the credentials in the instance
        self.portal_username = username
        self.portal_password = password
        
        # Also save to trial info for compatibility
        trial_info = self._get_trial_info()
        trial_info['portal_username'] = username
        trial_info['portal_password'] = password
        self._save_trial_info(trial_info)
    
    def verify_device_license(self, username=None, password=None):
        """Verify device license with device ID and portal credentials - Simplified version"""
        try:
            print("\n🔍 Starting license verification...")
            print(f"Device ID: {self.device_id}")
            print(f"Username: {username}")
            print(f"Password: {'*' * len(password) if password else None}")
            
            if not self.device_id:
                print("❌ No device ID available")
                self.license_valid = False
                return False
                
            # Check cache first - if we have a valid cached license, just check status
            if self.check_cache():
                print("✅ Valid license found in cache - checking status only")
                # Just check if license is still active without full verification
                if self.check_license_status_only():
                    self.license_valid = True
                    return True
                else:
                    print("⚠️ Cached license is no longer active")
                    # Clear cache and proceed with full verification
                    self.clear_cache()
            
            # Step 1: Try license verification
            current_time = time.time()
            payload = {
                'action': 'verify_device',
                'device_id': self.device_id,
                'user_id': username,  # Use the portal username as user_id to match database
                'portal_username': username,
                'portal_password': password,
                'timestamp': int(current_time)
            }
            
            print(f"📡 Sending verification request to: {self.api_url}")
            print(f"Payload: {payload}")
            
            # Make API request
            response = requests.post(self.api_url, data=payload, timeout=10)
            print(f"📥 Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Server response: {data}")
                
                if data.get('success'):
                    print("✅ Device license verified successfully")
                    
                    # Extract firm_id from license response
                    firm_id = data.get('firm_id')
                    if firm_id:
                        print(f"🏢 Firm ID from license: {firm_id}")
                        self.firm_id = firm_id
                    else:
                        print("⚠️ No firm_id found in license response")
                    
                    if username and password:
                        print("🔐 Binding portal credentials")
                        self._bind_portal_credentials(username, password)
                    
                    expires_at = data.get('expires_at')
                    self.save_cache(expires_at=expires_at, firm_id=firm_id)
                    self.last_check_time = current_time
                    self.license_valid = True
                    self.trial_active = False
                    print("🎉 Returning True from license verification")
                    return True
                else:
                    print(f"❌ License verification failed: {data.get('message', 'Unknown error')}")
                    print(f"🔍 Debug info - Device ID: {self.device_id}, Username: {username}")
                    return False
            
            # Step 2: Check trial status
            print("📝 Checking trial status...")
            payload['action'] = 'check_trial'
            response = requests.post(self.api_url, data=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"Trial check response: {data}")
                if data.get('success'):
                    print("✅ Active trial found")
                    self.trial_active = True
                    self.license_valid = True
                    if username and password:
                        self._bind_portal_credentials(username, password)
                    return True
                else:
                    print(f"❌ Trial check failed: {data.get('message', 'No active trial')}")
            
            # Step 3: Try to start trial
            print("🆕 Attempting to start trial...")
            payload['action'] = 'register_trial'
            response = requests.post(self.api_url, data=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"Trial registration response: {data}")
                if data.get('success'):
                    print("✅ Trial started successfully")
                    self.trial_active = True
                    self.license_valid = True
                    if username and password:
                        self._bind_portal_credentials(username, password)
                    return True
                else:
                    print(f"❌ Trial registration failed: {data.get('message', 'Unknown error')}")
            
            print("❌ All verification attempts failed")
            print(f"🔍 Final debug info:")
            print(f"   Device ID: {self.device_id}")
            print(f"   Username: {username}")
            print(f"   API URL: {self.api_url}")
            self.license_valid = False
            self.trial_active = False
            return False
            
        except Exception as e:
            print(f"❌ License verification error: {str(e)}")
            self.license_valid = False
            self.trial_active = False
            return False
    
    def check_license(self):
        """Check device license with enhanced verification"""
        if not self.mac_address:
            return False
            
        # Use cached credentials if available, otherwise just check status
        if self.portal_username and self.portal_password:
            return self.verify_device_license(self.portal_username, self.portal_password)
        else:
            # If no cached credentials, just check if we have a valid cached license
            return self.check_cache()
    
    def check_license_status_only(self):
        """Check if license is still active without full verification - Simplified status check"""
        try:
            if not self.device_id:
                return False
                
            # Simple status check - just verify the device is still active
            payload = {
                'action': 'get_device_status',
                'device_id': self.device_id
            }
            
            print(f"📡 Checking license status only: {self.api_url}")
            response = requests.post(self.api_url, data=payload, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('device'):
                    device_info = data.get('device')
                    status = device_info.get('status', 'inactive')
                    expires_at = device_info.get('expires_at')
                    
                    # Check if license is active and not expired
                    if status == 'active':
                        if expires_at:
                            # Check if license has expired
                            import datetime
                            try:
                                expiry_time = datetime.datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                                if datetime.datetime.now(datetime.timezone.utc) > expiry_time:
                                    print("❌ License status: EXPIRED")
                                    return False
                            except:
                                pass  # If date parsing fails, assume it's still valid
                        
                        print("✅ License status: ACTIVE")
                        return True
                    else:
                        print(f"❌ License status: {status.upper()}")
                        return False
                else:
                    print("❌ License status: NOT FOUND")
                    return False
            else:
                print(f"⚠️ Status check failed: {response.status_code}")
                # If status check fails, assume license is still valid (network issue)
                return True
                
        except Exception as e:
            print(f"⚠️ Status check error: {str(e)}")
            # If status check fails, assume license is still valid (network issue)
            return True
    
    def check_cache(self):
        """Check if we have a valid cached license - Simplified persistent cache"""
        try:
            if not os.path.exists(self.cache_file):
                return False
                
            with open(self.cache_file, 'r') as f:
                cache = json.load(f)
                
            # Check if cache is for this device
            if cache.get('device_id') != self.device_id:
                print("❌ Cache is for different device")
                return False
                
            # Check if license has expired
            expires_at = cache.get('expires_at')
            if expires_at:
                try:
                    # Handle both timestamp and datetime string formats
                    if isinstance(expires_at, str):
                        # Parse datetime string like "2026-08-29 16:07:41"
                        from datetime import datetime
                        expire_datetime = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')
                        expire_timestamp = expire_datetime.timestamp()
                    else:
                        # Handle numeric timestamp
                        expire_timestamp = float(expires_at)
                    
                    if time.time() > expire_timestamp:
                        print('❌ Cached license expired')
                        return False
                except Exception as e:
                    print(f"⚠️ Error parsing expiry date: {e}")
                    # If we can't parse the date, consider it expired
                return False
                
            # If we have a verified license in cache, it's valid until expiry
            if cache.get('verified') and cache.get('portal_username'):
                print("✅ Valid cached license found")
                # Restore portal credentials from cache
                self.portal_username = cache.get('portal_username')
                self.portal_password = cache.get('portal_password')
                self.license_valid = cache.get('license_valid', True)
                self.trial_active = cache.get('trial_active', False)
                
                # Restore firm_id from cache
                firm_id = cache.get('firm_id')
                if firm_id:
                    self.firm_id = firm_id
                    print(f"🏢 Firm ID restored from cache: {firm_id}")
                
                return True
                
        except Exception as e:
            print(f"Cache check error: {e}")
            
        return False
    
    def save_cache(self, expires_at=None, firm_id=None):
        """Save license verification to cache - Enhanced with credentials"""
        try:
            cache = {
                'device_id': self.device_id,
                'portal_username': self.portal_username,
                'portal_password': self.portal_password,  # Store password for auto-login
                'timestamp': time.time(),
                'verified': True,
                'license_valid': True,  # Always set to True when saving successful verification
                'trial_active': self.trial_active
            }
            
            if expires_at is not None:
                cache['expires_at'] = expires_at
                
            if firm_id is not None:
                cache['firm_id'] = firm_id
                
            with open(self.cache_file, 'w') as f:
                json.dump(cache, f)
                
            print("💾 License cache saved successfully")
                
        except Exception as e:
            print(f"Cache save error: {e}")
    
    def clear_cache(self):
        """Clear license cache"""
        try:
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
        except Exception as e:
            print(f"Cache clear error: {e}")
    
    def get_license_status(self):
        """Get current license status"""
        trial_info = self._get_trial_info()
        expires_at = None
        if os.path.exists(self.cache_file):
            with open(self.cache_file, 'r') as f:
                cache = json.load(f)
                expires_at = cache.get('expires_at')
        return {
            'valid': self.license_valid,
            'trial_active': self.trial_active,
            'device_id': self.device_id,
            'mac_address': self.mac_address,
            'user_id': self.user_id,
            'portal_username': self.portal_username,
            'last_check': self.last_check_time,
            'next_check': self.last_check_time + self.check_interval,
            'trial_info': trial_info,
            'expires_at': expires_at
        }
    
    def enforce_license(self):
        """Enforce license - enhanced version with trial support"""
        if not self.check_license():
            print("❌ Device not authorized. Please verify your license.")
            return False
        return True
    
    def start_periodic_verification(self, app_instance):
        """Start periodic license verification in background thread"""
        if self.verification_thread and self.verification_thread.is_alive():
            return
            
        self.stop_verification = False
        self.verification_thread = threading.Thread(
            target=self._periodic_verification_worker,
            args=(app_instance,),
            daemon=True
        )
        self.verification_thread.start()
    
    def stop_periodic_verification(self):
        """Stop periodic license verification"""
        self.stop_verification = True
        if self.verification_thread:
            self.verification_thread.join(timeout=1)
    
    def _periodic_verification_worker(self, app_instance):
        """Background worker for periodic license verification - Simplified status check only"""
        while not self.stop_verification:
            try:
                time.sleep(self.check_interval)  # Wait for next check
                
                if self.stop_verification:
                    break
                    
                # Only check status, not full verification
                if not self.check_license_status_only():
                    # License is no longer active
                    self.license_valid = False
                    
                    # Show alert and block access
                    if hasattr(app_instance, 'root') and app_instance.root:
                        app_instance.root.after(0, self._show_license_expired_dialog, app_instance)
                    break
                    
            except Exception as e:
                print(f"Periodic verification error: {e}")
                time.sleep(60)  # Wait 1 minute before retry
    
    def _show_license_expired_dialog(self, app_instance):
        """Show license expired dialog and block access"""
        try:
            result = messagebox.askyesno(
                "License Expired",
                "Your device license has expired or is no longer valid.\n\n"
                "The application will be closed in 5 seconds. Please contact your administrator "
                "to renew your license.\n\n"
                "Do you want to exit the application now?",
                icon='warning'
            )
            
            if result:
                # Close the application immediately
                if hasattr(app_instance, 'root') and app_instance.root:
                    app_instance.root.quit()
                    app_instance.root.destroy()
                import sys
                sys.exit(0)
            else:
                # Force close after 5 seconds
                if hasattr(app_instance, 'root') and app_instance.root:
                    app_instance.root.after(5000, lambda: self._force_close_app(app_instance))
                    
        except Exception as e:
            print(f"Error showing license dialog: {e}")
            # Force close if dialog fails
            self._force_close_app(app_instance)
    
    def _force_close_app(self, app_instance):
        """Force close the application"""
        try:
            if hasattr(app_instance, 'root') and app_instance.root:
                app_instance.root.quit()
                app_instance.root.destroy()
            import sys
            sys.exit(0)
        except:
            import os
            os._exit(0) 