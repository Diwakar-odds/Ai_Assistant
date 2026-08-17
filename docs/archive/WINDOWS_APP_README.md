# AI Assistant - Windows Desktop App

## Quick Start Guide

### Method 1: Run in Development Mode (Recommended for Testing)

1. **Install dependencies:**
   ```bash
   pip install pywebview
   ```

2. **Run the app:**
   ```bash
   python windows_app.py
   ```
   
   Or use the quick launcher:
   ```bash
   python run_windows_app.py
   ```

### Method 2: Build Windows Executable (For Distribution)

1. **Run the build script:**
   ```bash
   build_windows_app.bat
   ```
   
   This will:
   - Install PyInstaller and required dependencies
   - Build the Windows executable
   - Create a distributable folder in `dist/AIAssistant/`

2. **Run the executable:**
   - Navigate to `dist/AIAssistant/`
   - Double-click `AIAssistant.exe`

3. **Share with others:**
   - Zip the entire `dist/AIAssistant/` folder
   - Users can extract and run `AIAssistant.exe` without installing Python

## Features

✅ **Native Windows App** - Runs as a desktop application  
✅ **Self-contained** - All your web UI wrapped in a desktop window  
✅ **No Browser Required** - Uses native webview  
✅ **System Tray Integration** - Minimize to tray (optional)  
✅ **Offline Capable** - Works without internet for local features  

## File Structure

```
windows_app.py          # Main Windows desktop app launcher
windows_app.spec        # PyInstaller build configuration
build_windows_app.bat   # Windows build script
run_windows_app.py      # Quick development launcher
app_icon.ico           # App icon (optional, create if needed)
```

## Customization

### Change Window Size
Edit `windows_app.py`:
```python
window = webview.create_window(
    width=1600,  # Change this
    height=1000, # Change this
    ...
)
```

### Add App Icon
1. Create or download an `.ico` file
2. Save it as `app_icon.ico` in the project root
3. The build script will automatically include it

### Change App Name
Edit `windows_app.spec`:
```python
name='YourAppName',  # Change this
```

## Troubleshooting

### "Backend server failed to start"
- Make sure all dependencies are installed: `pip install -r requirements.txt`
- Check if port 5000 is available

### Build errors
- Update PyInstaller: `pip install --upgrade pyinstaller`
- Try running with `--clean` flag

### App won't start
- Check `logs/` folder for error messages
- Run in dev mode first to see console output

## Advanced Options

### Run with Console Window (for debugging)
Edit `windows_app.spec`:
```python
console=True,  # Change to True
```

### Create Installer
Use tools like:
- **Inno Setup** - Free installer creator
- **NSIS** - Advanced installer tool
- **WiX** - Windows Installer XML toolset

## Requirements

- Python 3.8+
- Windows 10/11
- All dependencies from `requirements.txt`
- Additional: pywebview, pyinstaller
