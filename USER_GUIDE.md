# MANAK Automation - User Guide

## 🚀 Quick Start

### Option 1: Use the Launcher (Recommended)
1. **Double-click** `start_manak.bat` (Windows) or run `python start_app.py`
2. **Choose your startup mode** from the launcher window
3. **Follow the on-screen instructions**

### Option 2: Direct Start
- **Normal mode**: `python desktop_manak_app.py`
- **Development mode**: `python run_dev.py`
- **Test dialog**: `python test_dialog_standalone.py`

## 📋 Startup Options

### 🔐 Normal Mode (Production)
- **Full license verification required**
- **All features available** with valid license
- **Best for production use**
- **Shows license dialog** if no valid license found

### 🔧 Development Mode (Testing)
- **Bypasses license verification**
- **All features available** for testing
- **Good for development and testing**
- **No license dialog** appears

### 🧪 Test Dialog Mode
- **Tests just the license dialog**
- **Use test credentials** for verification
- **Good for troubleshooting**
- **Standalone dialog** for testing

## 🔑 License Setup

### First Time Setup
1. **Start the application** in normal mode
2. **License dialog will appear** automatically
3. **Enter your Device ID and User ID**
4. **Click "🔍 Verify License"** or press Enter
5. **Application will start** if verification succeeds

### Test Credentials
For testing purposes, use these credentials:
- **Device ID**: `fe80::a600:cd6b:c570:111d%17`
- **User ID**: `9810359334`

### Getting Your Credentials
- **Contact your administrator** for Device ID and User ID
- **Device ID** is usually your computer's MAC address
- **User ID** is provided by your organization

## 🎯 License Dialog Features

### Visual Improvements
- **Larger, more visible dialog** (600x400)
- **Better typography and spacing**
- **Clear visual hierarchy**
- **Improved button styling**

### User Experience
- **Clear instructions** and descriptions
- **Status feedback** for verification attempts
- **Keyboard shortcuts** (Enter to verify, Escape to exit)
- **Multiple options** (Verify, Skip, Exit)

### Buttons Available
- **🔍 Verify License** - Verify with entered credentials
- **⏭️ Skip for Now** - Continue without verification (limited features)
- **❌ Exit Application** - Close the application

## 🛠️ Troubleshooting

### Dialog Doesn't Show
1. **Check taskbar** for the dialog window
2. **Press Alt+Tab** to find the dialog
3. **Look behind other windows**
4. **Try development mode** if dialog won't appear

### Application Keeps Restarting
1. **Use development mode**: `python run_dev.py`
2. **Check license credentials** in settings
3. **Verify network connection** for API calls
4. **Use test credentials** for testing

### License Verification Fails
1. **Check Device ID and User ID format**
2. **Verify network connection**
3. **Try test credentials** for testing
4. **Check API server status**
5. **Contact administrator** for valid credentials

### Can't Find the Application
1. **Use the launcher**: `start_manak.bat` or `python start_app.py`
2. **Check Python installation**: `python --version`
3. **Verify file locations** are correct
4. **Run as administrator** if needed

## 📁 File Structure

```
manak-automation/
├── desktop_manak_app.py      # Main application
├── start_app.py              # User-friendly launcher
├── start_manak.bat           # Windows batch launcher
├── run_dev.py                # Development mode launcher
├── test_dialog_standalone.py # License dialog test
├── device_license.py         # License manager
├── device_license_api.php    # Server-side license API
└── USER_GUIDE.md            # This guide
```

## 🔧 Advanced Options

### Environment Variables
- **MANAK_DEV_MODE=1** - Bypass license verification
- **MANAK_DEBUG=1** - Enable debug logging

### Command Line Options
```bash
# Normal mode
python desktop_manak_app.py

# Development mode
python run_dev.py

# Test dialog
python test_dialog_standalone.py

# With environment variables
set MANAK_DEV_MODE=1
python desktop_manak_app.py
```

### Settings Location
- **Windows**: `%APPDATA%/manak-automation/config/`
- **Linux/Mac**: `~/.config/manak-automation/`
- **License cache**: `license_cache.json` in app directory

## 🆘 Support

### Common Issues
1. **"Python not found"** - Install Python and add to PATH
2. **"Module not found"** - Install required packages: `pip install selenium requests`
3. **"License verification failed"** - Check credentials and network
4. **"Dialog not visible"** - Use development mode or check window management

### Getting Help
1. **Check this user guide**
2. **Use development mode** for testing
3. **Test dialog functionality** with test credentials
4. **Contact your administrator** for license issues
5. **Review application logs** for error messages

### Contact Information
- **Administrator**: For license credentials and technical support
- **Developer**: For application bugs and feature requests
- **Documentation**: Check this guide and other README files

## 🎉 Success Indicators

### License Verification Success
- ✅ **"License verified successfully!"** message
- ✅ **Application starts** normally
- ✅ **All features available**
- ✅ **Settings saved** automatically

### Development Mode Success
- 🔧 **"Development mode detected"** message
- 🔧 **Application starts** without license dialog
- 🔧 **All features available** for testing
- 🔧 **No license verification** required

### Test Dialog Success
- 🧪 **Dialog appears** with test credentials
- 🧪 **Verification works** with test credentials
- 🧪 **Error handling** works with invalid credentials
- 🧪 **Dialog closes** properly after testing

## 📝 Notes

- **License verification** is required for production use
- **Development mode** is for testing only
- **Test credentials** are for testing only
- **Settings are saved** automatically after successful verification
- **Network connection** is required for license verification
- **Application logs** are available for troubleshooting 