# MANAK Automation - Device Licensing Setup Guide

## Overview
This guide will help you set up device licensing for the MANAK Automation application. The system ensures that only authorized devices can use the application.

## 🔧 Server Setup

### 1. Database Setup
1. Create a new database or use your existing database
2. Run the SQL script to create the device_licenses table:

```sql
-- Run this in your MySQL database
source device_licenses.sql
```

### 2. API Configuration
1. Upload `device_license_api.php` to your server (e.g., `https://hallmarkpro.prosenjittechhub.com/admin/`)
2. Edit the database configuration in `device_license_api.php`:

```php
// Update these values with your database details
$db_host = 'localhost';
$db_name = 'your_database_name';
$db_user = 'your_db_username';
$db_pass = 'your_db_password';
```

3. Set an API key for security (optional):
```php
$api_key = 'your_secret_api_key_here';
```

### 3. Admin Panel Setup
1. Upload `admin_panel.html` to your server
2. Access it via: `https://hallmarkpro.prosenjittechhub.com/admin/admin_panel.html`

## 🖥️ Client Application Setup

### 1. Update Application
The main application (`desktop_manak_app.py`) has been updated to include device licensing. The changes include:

- Device license verification on startup
- License status display in Settings tab
- Automatic MAC address detection
- User ID prompt for first-time users

### 2. Build Executable
Run the build script to create the executable:

```bash
python build_exe.py
```

Or use the quick setup:
```bash
quick_setup.bat
```

## 📋 Device Registration Process

### For Administrators:
1. **Get Device ID**: When a user first runs the application, it will show their Device ID (MAC address)
2. **Register Device**: Use the admin panel to register the device:
   - Device ID: The MAC address shown by the application
   - User ID: The user's identifier
   - License Type: Choose appropriate license type
   - Notes: Optional notes about the device

### For Users:
1. **First Run**: The application will prompt for User ID
2. **Wait for Approval**: Administrator needs to register the device
3. **Use Application**: Once registered, the application will work normally

## 🔐 License Management

### License Types:
- **Standard**: 1 year license
- **Premium**: 2 year license  
- **Trial**: 30 day license

### License Status:
- **Active**: Device can use the application
- **Inactive**: Device temporarily disabled
- **Revoked**: Device permanently disabled
- **Expired**: License has expired

### Admin Actions:
- **Register**: Add new device to the system
- **Activate**: Enable a disabled device
- **Revoke**: Permanently disable a device
- **Extend**: Extend license expiration date

## 🚀 Distribution

### 1. Create Distribution Package
```bash
distribute.bat
```

This creates:
- `MANAK_Automation_Distribution/` folder
- `MANAK_Automation_Package.zip` file

### 2. Distribute to Users
- Copy the distribution folder to target computers
- Or share the ZIP file
- Users run `Run_MANAK_Automation.bat` to start

## 🔍 Troubleshooting

### Common Issues:

1. **"Device not authorized"**
   - Device needs to be registered in admin panel
   - Check if User ID matches registration

2. **"API connection error"**
   - Check internet connection
   - Verify API URL in device_license.py
   - Check server is accessible

3. **"MAC address not found"**
   - Application will use fallback device ID
   - This is normal for some systems

4. **"License expired"**
   - Contact administrator to extend license
   - Or upgrade to different license type

### Debug Information:
- Device ID is shown in Settings tab
- License status is displayed in Settings tab
- Application logs show verification attempts

## 📊 Monitoring

### Admin Panel Features:
- **Register Device**: Add new devices
- **Manage Licenses**: View and modify existing licenses
- **Status Overview**: See license statistics
- **Search**: Find specific devices

### API Endpoints:
- `verify_device`: Check if device is authorized
- `register_device`: Add new device
- `revoke_device`: Disable device
- `get_device_status`: Get device information
- `search_devices`: Find devices by criteria
- `get_status_summary`: Get license statistics

## 🔒 Security Features

1. **MAC Address Verification**: Each device has unique identifier
2. **User ID Association**: Devices are tied to specific users
3. **License Expiration**: Automatic expiration dates
4. **API Key Protection**: Optional API key for additional security
5. **Cache System**: Reduces API calls for better performance

## 📝 Configuration Files

### device_license.py
- `api_url`: Your API endpoint URL
- `cache_file`: Local cache file location
- `cache_duration`: How long to cache verification

### device_license_api.php
- Database connection settings
- API key configuration
- License expiration logic

## 🎯 Best Practices

1. **Regular Monitoring**: Check admin panel regularly
2. **License Management**: Set appropriate expiration dates
3. **User Communication**: Inform users about device registration
4. **Backup**: Keep database backups
5. **Documentation**: Maintain user and admin documentation

## 📞 Support

For technical support:
1. Check the troubleshooting section
2. Verify server configuration
3. Check database connectivity
4. Review application logs
5. Contact development team

---

**Note**: This licensing system ensures that only authorized devices can use the MANAK Automation application. Make sure to properly register all devices and manage licenses through the admin panel. 