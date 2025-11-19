# Quick Start Guide: Incomplete Modules

## 🚀 Quick Start

This guide gets you up and running with the newly completed modules in under 5 minutes.

---

## 📋 Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# For OCR features, install Tesseract:
# Windows: https://github.com/tesseract-ocr/tesseract/releases
# macOS: brew install tesseract
# Linux: sudo apt-get install tesseract-ocr
```

---

## 🎯 Quick Examples

### 1. Organize Your Downloads Folder (30 seconds)

```python
from modules.file_ops import organize_files_by_type

# Organize your messy Downloads folder
result = organize_files_by_type("C:/Users/YourName/Downloads")
print(result)

# Output: 🗂️ Organized 45 files into 6 categories
#         📁 Created folders: Images, Documents, Videos, Audio, Code
```

### 2. Find Duplicate Files (1 minute)

```python
from modules.file_ops import find_duplicate_files

# Find duplicates in your Documents
result = find_duplicate_files("C:/Users/YourName/Documents")
print(result)

# Output: 🔍 Found 12 duplicate files from 1,234 scanned
#         💾 Potential space savings: 234.5 MB
```

### 3. Extract Text from Image (30 seconds)

```python
from modules.document_ocr import extract_text_from_image

# Extract text from a scanned document or screenshot
result = extract_text_from_image("C:/Scans/receipt.jpg")
print(result)

# Output: 📄 OCR Results for: receipt.jpg
#         📝 Extracted Text: [full text content]
```

### 4. Get Current Weather (10 seconds)

```python
from modules.web_scraping import get_weather_info

# Get weather for any city
weather = get_weather_info("London")
print(weather)

# Output: 🌤️ Weather in London:
#         🌡️ Temperature: 15°C (feels like 13°C)
#         ☁️ Conditions: Partly cloudy
```

### 5. Check What's Running in Taskbar (20 seconds)

```python
from modules.taskbar_detection import detect_taskbar_apps

# Get a report of running applications
report = detect_taskbar_apps()
print(report)

# Output: 📊 TASKBAR & RUNNING APPS ANALYSIS
#         🔄 Total Running Processes: 156
#         🪟 Visible Windows: 8
```

---

## 🌐 Using the Web API

### Start the Backend Server

```bash
# Start the Flask backend
python modern_web_backend.py

# Server will start at: http://localhost:5000
```

### Login to Get Token

```javascript
// Get authentication token
const response = await fetch('http://localhost:5000/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        username: 'admin',
        password: 'changeme123'  // Change in .env!
    })
});
const { access_token } = await response.json();
```

### Call API Endpoints

```javascript
// Organize files
fetch('http://localhost:5000/api/files/organize', {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${access_token}`,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        directory: 'C:/Users/Me/Downloads',
        create_subfolders: true
    })
});

// Get weather (no auth needed)
fetch('http://localhost:5000/api/web/weather?location=Paris')
    .then(r => r.json())
    .then(data => console.log(data.weather));

// Extract text from image
fetch('http://localhost:5000/api/ocr/extract-image', {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${access_token}`,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        image_path: 'C:/Scans/document.jpg',
        language: 'eng'
    })
});

// Get running apps
fetch('http://localhost:5000/api/taskbar/running-apps', {
    headers: { 'Authorization': `Bearer ${access_token}` }
});
```

---

## 🧪 Quick Test

Run the test suite to verify everything works:

```bash
# Test all modules
python -m pytest tests/ -v

# Or test individually
python tests/test_file_ops.py
python tests/test_document_ocr.py
python tests/test_web_scraping.py
python tests/test_taskbar_detection.py
```

---

## 🎨 Common Use Cases

### 1. Clean Up Your Computer

```python
from modules.file_ops import (
    organize_files_by_type,
    find_duplicate_files,
    analyze_directory_structure
)

# 1. Analyze what's taking up space
analysis = analyze_directory_structure("C:/Users/YourName")
print(analysis)

# 2. Find and remove duplicates
duplicates = find_duplicate_files("C:/Users/YourName/Documents")
print(duplicates)

# 3. Organize Downloads
organize_files_by_type("C:/Users/YourName/Downloads")
```

### 2. Process Documents

```python
from modules.document_ocr import (
    extract_text_from_image,
    extract_text_from_pdf,
    extract_key_information
)

# 1. Scan a receipt
text = extract_text_from_image("receipt.jpg")

# 2. Extract key info (emails, dates, amounts)
info = extract_key_information(text, info_type="general")
print(info)

# 3. Process a PDF report
pdf_text = extract_text_from_pdf("report.pdf", page_range=(1, 5))
```

### 3. Monitor Information

```python
from modules.web_scraping import (
    get_weather_info,
    get_latest_news,
    get_stock_price,
    get_trending_topics
)

# Morning routine: Check everything at once
weather = get_weather_info("Your City")
news = get_latest_news("technology", max_articles=5)
stock = get_stock_price("AAPL")
trending = get_trending_topics("reddit")

print(f"{weather}\n\n{news}\n\n{stock}\n\n{trending}")
```

### 4. System Monitoring

```python
from modules.taskbar_detection import TaskbarDetector

detector = TaskbarDetector()

# Get complete system overview
analysis = detector.get_complete_desktop_analysis()

# Find specific app
chrome_status = detector.find_specific_app_in_taskbar("chrome")
if chrome_status['found_in_processes']:
    print("Chrome is running!")
else:
    print("Chrome is not running")
```

---

## 🔧 Configuration

### Environment Variables

Create a `.env` file:

```env
# Authentication
JWT_SECRET_KEY=your-super-secret-key-change-this
ADMIN_PASSWORD=your-strong-password

# API Keys (optional)
OPENWEATHER_API_KEY=your-api-key-here

# Server
HOST=127.0.0.1
PORT=5000
```

### Tesseract Path (if needed)

If Tesseract is not in your PATH:

```python
import pytesseract

# Windows
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Then use OCR functions normally
from modules.document_ocr import extract_text_from_image
result = extract_text_from_image("image.jpg")
```

---

## 📚 Learn More

- **Full Documentation**: `docs/INCOMPLETE_MODULES_GUIDE.md`
- **API Reference**: `docs/API_DOCUMENTATION.md`
- **Week 8-9 Summary**: `docs/WEEK_8_9_SUMMARY.md`
- **Test Examples**: Check `tests/` folder for usage patterns

---

## 🆘 Troubleshooting

### "Permission Denied" errors
```python
# Run Python as administrator (Windows)
# Or check file/folder permissions
```

### "Tesseract not installed"
```bash
# Install Tesseract OCR engine first
# Then pip install pytesseract
```

### "Module not found"
```bash
# Install all dependencies
pip install -r requirements.txt
```

### API authentication fails
```bash
# Check .env file exists
# Verify JWT_SECRET_KEY is set
# Use correct username/password
```

---

## 🎯 Next Steps

1. ✅ Try the quick examples above
2. ✅ Run the test suite
3. ✅ Start the web backend
4. ✅ Read the full documentation
5. ✅ Build something awesome!

---

## 💡 Pro Tips

1. **Always preview first** - Use `preview=True` or `dry_run=True` for destructive operations
2. **Check dependencies** - Run `check_ocr_dependencies()` before using OCR
3. **Use absolute paths** - More reliable than relative paths
4. **Handle errors** - Always wrap file operations in try-except
5. **Test with small datasets** - Before processing large folders

---

**Ready to go!** 🚀

Pick an example above and try it out. Check the full documentation for advanced features.

**Questions?** See `docs/INCOMPLETE_MODULES_GUIDE.md` for detailed information.
