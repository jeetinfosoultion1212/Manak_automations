# 🔐 Secure Device License System

## Overview

The MANAK Automation app now features a **secure MAC-based device licensing system** with trial support that prevents unauthorized usage and multiple user abuse.

## 🎯 Key Features

### 1. **MAC-Based Device Identification**
- **Automatic MAC Detection**: The app automatically detects your device's unique MAC address
- **Device Binding**: Each device can only be used by one user account
- **No Manual Entry**: MAC address is read-only and cannot be changed

### 2. **Portal Credential Binding**
- **Single User Per Device**: Once verified, portal credentials are bound to the device
- **Prevents Multiple Users**: Users cannot change portal credentials to use different accounts
- **Secure Storage**: Credentials are encrypted and stored locally

### 3. **Trial System**
- **7-Day Trial**: New devices get a 7-day trial period
- **Per Device**: Trial is tied to the device MAC address
- **Automatic Start**: Trial starts when the app is first run on a device

### 4. **Real-Time Verification**
- **Startup Check**: License is verified every time the app starts
- **Periodic Checks**: Background verification every 30 minutes
- **Auto-Block**: App closes automatically if license expires

## 🔧 How It Works

### First Time Setup
1. **App Launch**: When you first run the app, it detects your MAC address
2. **Trial Start**: A 7-day trial automatically starts for your device
3. **Settings Page**: You're redirected to the Settings page
4. **Portal Credentials**: Enter your portal username and password
5. **Verification**: Click "Verify License" to bind credentials to your device

### Daily Usage
1. **Auto-Check**: App automatically verifies license on startup
2. **Background Monitoring**: Periodic checks every 30 minutes
3. **Action Protection**: All automation features require valid license
4. **Expiry Handling**: App closes with 5-second warning if license expires

## 🛡️ Security Features

### Device Protection
- **MAC Address Lock**: Device is identified by unique MAC address
- **No Bypass**: No way to skip or bypass license verification
- **Force Settings**: Users must verify license before using features

### User Protection
- **Single User Per Device**: One device = One user account
- **Credential Binding**: Portal credentials are bound to device
- **No Credential Switching**: Cannot change to different portal accounts

### Trial Protection
- **Time-Limited**: 7-day trial per device
- **Non-Renewable**: Trial cannot be restarted on same device
- **Secure Storage**: Trial info stored in encrypted format

## 📋 License Status Types

### ✅ **Authorized**
- Valid license verified with portal credentials
- All features available
- Periodic verification active

### ⏳ **Trial Active**
- Device in 7-day trial period
- All features available
- Trial countdown active

### ❌ **Not Authorized**
- No valid license or trial
- Features blocked
- Must verify license

### ⚠️ **Expired**
- License or trial has expired
- App will close automatically
- Must renew or verify new license

## 🔄 License Verification Process

### Step 1: Device Detection
```
App Start → Detect MAC Address → Generate Device ID → Check License Status
```

### Step 2: License Check
```
Check Cache → If Valid → Allow Access
Check Trial → If Active → Allow Access  
Check API → If Valid → Allow Access
Else → Force License Setup
```

### Step 3: Portal Verification
```
Enter Credentials → API Verification → Bind to Device → Start Periodic Checks
```

## 🚫 Prevention Features

### Multiple User Prevention
- **Device Binding**: Portal credentials are bound to device MAC
- **No Credential Change**: Cannot switch to different portal accounts
- **Single Session**: Only one user can use the device

### Unauthorized Usage Prevention
- **MAC Lock**: Device identified by hardware MAC address
- **No Manual Override**: Cannot manually change device identification
- **Force Verification**: Must verify license before any automation

### Trial Abuse Prevention
- **Per Device**: Trial tied to specific device MAC
- **Non-Renewable**: Cannot restart trial on same device
- **Time-Limited**: Strict 7-day limit

## 📱 User Interface

### Settings Page
- **Device Information**: Shows MAC address and Device ID (read-only)
- **Portal Credentials**: Username and password fields
- **License Status**: Current verification status
- **Verify Button**: Manual license verification
- **Clear Button**: Reset license and start fresh

### License Dialog
- **Device Info**: Displays MAC address and Device ID
- **Credential Entry**: Portal username and password
- **Verification**: Real-time license checking
- **Status Updates**: Clear feedback on verification progress

## 🔧 Technical Implementation

### MAC Address Detection
```python
def _get_mac_address(self):
    """Get the primary MAC address of the device"""
    try:
        result = subprocess.check_output(['ipconfig', '/all'], text=True)
        # Parse MAC address from Windows command output
        return mac_address
    except:
        return str(uuid.uuid4())  # Fallback
```

### Device ID Generation
```python
def _generate_device_id(self):
    """Generate unique device ID from MAC address"""
    return hashlib.md5(self.mac_address.encode()).hexdigest()[:16]
```

### Trial Management
```python
def _start_trial(self):
    """Start 7-day trial for this device"""
    trial_info = {
        'device_id': self.device_id,
        'mac_address': self.mac_address,
        'start_date': datetime.now().isoformat(),
        'expiry_date': (datetime.now() + timedelta(days=7)).isoformat()
    }
```

### License Verification
```python
def verify_device_license(self, username, password):
    """Verify license with portal credentials"""
    payload = {
        'action': 'verify_device',
        'device_id': self.device_id,
        'mac_address': self.mac_address,
        'portal_username': username,
        'portal_password': password
    }
    # API call to verify license
```

## 🚨 Error Handling

### Network Issues
- **Offline Mode**: App works with cached license
- **Retry Logic**: Automatic retry on network failure
- **Graceful Degradation**: Fallback to trial mode

### API Errors
- **Error Messages**: Clear feedback on verification issues
- **Retry Options**: Manual retry with different credentials
- **Support Contact**: Clear instructions for admin contact

### Device Changes
- **MAC Change**: New device requires new license verification
- **Hardware Changes**: May require re-verification
- **Migration Support**: Admin can transfer licenses

## 📞 Support

### For Users
- **License Issues**: Contact your administrator
- **Trial Expired**: Purchase a license from admin
- **Device Changes**: Re-verify license on new device

### For Administrators
- **License Management**: Use admin panel to manage licenses
- **Device Monitoring**: Track device usage and licenses
- **User Management**: Assign licenses to specific users

## 🔄 Migration Guide

### From Old System
1. **Backup Settings**: Save current app settings
2. **Install New Version**: Update to new version
3. **First Run**: App will detect device and start trial
4. **Verify License**: Enter portal credentials and verify
5. **Restore Settings**: Import previous settings

### To New Device
1. **Install App**: Install on new device
2. **Detect Device**: App will detect new MAC address
3. **Contact Admin**: Request license transfer
4. **Verify License**: Enter credentials and verify
5. **Start Using**: All features available

## 📊 Monitoring

### License Status Dashboard
- **Active Licenses**: Number of valid licenses
- **Trial Users**: Devices in trial period
- **Expired Licenses**: Licenses that need renewal
- **Device Usage**: Usage statistics per device

### Admin Alerts
- **License Expiry**: Notifications before license expires
- **Trial Expiry**: Alerts when trials are about to expire
- **Unauthorized Usage**: Detection of license violations
- **Device Changes**: Notifications of new device registrations

---

## 🎯 Summary

This secure license system provides:

✅ **Device-specific licensing**  
✅ **Prevention of multiple user abuse**  
✅ **7-day trial for new devices**  
✅ **Real-time license verification**  
✅ **Automatic blocking of expired licenses**  
✅ **Portal credential binding**  
✅ **No bypass mechanisms**  

The system ensures that each device can only be used by one authorized user, preventing the abuse of multiple users changing portal credentials on the same device. 