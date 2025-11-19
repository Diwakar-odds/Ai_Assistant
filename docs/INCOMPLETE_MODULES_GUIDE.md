# Incomplete Modules Documentation

## Overview
This document provides comprehensive usage documentation for the recently completed modules in Week 8-9 of the YourDaddy Assistant project.

---

## Table of Contents
1. [File Operations Module](#file-operations-module)
2. [Document OCR Module](#document-ocr-module)
3. [Web Scraping Module](#web-scraping-module)
4. [Taskbar Detection Module](#taskbar-detection-module)
5. [API Endpoints](#api-endpoints)
6. [Testing](#testing)

---

## File Operations Module

### Overview
The File Operations module provides advanced file management capabilities including organization, duplicate detection, intelligent search, and batch operations.

### Features
- **File Organization**: Automatically organize files by type into categorized folders
- **Duplicate Detection**: Find and optionally remove duplicate files based on content hash
- **Smart Search**: Search files by name pattern or content with advanced filtering
- **Batch Rename**: Rename multiple files using patterns and placeholders
- **Directory Analysis**: Get comprehensive statistics about directory structure
- **Directory Sync**: Synchronize files between two directories
- **Backup Creation**: Create compressed archives of directories

### Installation
```bash
# No additional dependencies required - uses Python standard library
```

### Usage Examples

#### 1. Organize Files by Type
```python
from modules.file_ops import organize_files_by_type

# Organize all files in Downloads folder
result = organize_files_by_type(
    directory="C:/Users/YourName/Downloads",
    create_subfolders=True
)
print(result)
# Output: "🗂️ Organized 45 files into 6 categories"
```

#### 2. Find Duplicate Files
```python
from modules.file_ops import find_duplicate_files

# Find duplicates in Documents folder including subdirectories
result = find_duplicate_files(
    directory="C:/Users/YourName/Documents",
    include_subdirs=True
)
print(result)
# Shows list of duplicate files and potential space savings
```

#### 3. Smart File Search
```python
from modules.file_ops import smart_file_search

# Search for Python files containing "import requests"
result = smart_file_search(
    directory="C:/Projects",
    pattern="import requests",
    search_content=True,
    file_types=['.py']
)
print(result)
```

#### 4. Batch Rename Files
```python
from modules.file_ops import batch_rename_files

# Preview renaming vacation photos
result = batch_rename_files(
    directory="C:/Photos/Vacation",
    pattern="IMG_*.jpg",
    replacement="vacation_2024_{n}",
    preview=True  # Set to False to actually rename
)
print(result)
```

#### 5. Analyze Directory Structure
```python
from modules.file_ops import analyze_directory_structure

# Get insights about project directory
result = analyze_directory_structure(
    directory="C:/Projects/MyApp",
    max_depth=3
)
print(result)
# Shows file counts, types, large files, old files, etc.
```

#### 6. Sync Directories
```python
from modules.file_ops import sync_directories

# Sync backup with source (dry run first)
result = sync_directories(
    source_dir="C:/Important/Documents",
    dest_dir="D:/Backup/Documents",
    delete_extra=False,
    dry_run=True  # Set to False to actually sync
)
print(result)
```

### API Endpoints

#### POST `/api/files/organize`
Organize files by type
```javascript
fetch('/api/files/organize', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        directory: 'C:/Users/Me/Downloads',
        create_subfolders: true
    })
})
```

#### POST `/api/files/find-duplicates`
Find duplicate files
```javascript
fetch('/api/files/find-duplicates', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        directory: 'C:/Users/Me/Documents',
        include_subdirs: true
    })
})
```

#### POST `/api/files/search`
Search for files
```javascript
fetch('/api/files/search', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        directory: 'C:/Projects',
        pattern: '*.py',
        search_content: true,
        file_types: ['.py', '.txt']
    })
})
```

---

## Document OCR Module

### Overview
The Document OCR module provides optical character recognition and document analysis capabilities for images and PDFs.

### Features
- **Image OCR**: Extract text from images using Tesseract
- **PDF Text Extraction**: Extract text from PDF documents
- **Document Analysis**: Analyze document structure and metadata
- **Image Preprocessing**: Enhance images for better OCR accuracy
- **Key Information Extraction**: Extract emails, phones, dates, URLs, etc.
- **Batch OCR**: Process multiple files at once
- **Content Summarization**: Generate summaries of extracted text

### Installation
```bash
# Install required packages
pip install pytesseract Pillow opencv-python PyPDF2 pdfplumber

# Install Tesseract OCR engine
# Windows: Download from https://github.com/tesseract-ocr/tesseract
# macOS: brew install tesseract
# Linux: sudo apt-get install tesseract-ocr
```

### Usage Examples

#### 1. Check OCR Dependencies
```python
from modules.document_ocr import check_ocr_dependencies

status = check_ocr_dependencies()
print(status)
# Shows which OCR libraries are available
```

#### 2. Extract Text from Image
```python
from modules.document_ocr import extract_text_from_image

# Extract text from a scanned document
result = extract_text_from_image(
    image_path="C:/Scans/receipt.jpg",
    language="eng",  # or "fra", "deu", "spa", etc.
    enhance=True  # Improve image quality for better OCR
)
print(result)
```

#### 3. Extract Text from PDF
```python
from modules.document_ocr import extract_text_from_pdf

# Extract text from specific pages
result = extract_text_from_pdf(
    pdf_path="C:/Documents/report.pdf",
    page_range=(1, 5)  # Extract pages 1-5
)
print(result)
```

#### 4. Analyze Document Structure
```python
from modules.document_ocr import analyze_document_structure

# Get document metadata and structure
result = analyze_document_structure(
    file_path="C:/Documents/contract.pdf"
)
print(result)
# Shows page count, dimensions, file size, etc.
```

#### 5. Extract Key Information
```python
from modules.document_ocr import extract_key_information

# Extract contact information from text
text = """
Contact us at support@company.com or call (555) 123-4567.
Meeting scheduled for 12/25/2024 at our office.
Invoice total: $1,299.99
"""

result = extract_key_information(text, info_type="general")
print(result)
# Extracts emails, phones, dates, currency amounts
```

#### 6. Batch OCR Multiple Files
```python
from modules.document_ocr import batch_ocr_directory

# Process all images in a folder
result = batch_ocr_directory(
    directory="C:/Scans",
    file_pattern="*.jpg",
    language="eng"
)
print(result)
```

### API Endpoints

#### GET `/api/ocr/check-dependencies`
Check OCR dependencies
```javascript
fetch('/api/ocr/check-dependencies')
```

#### POST `/api/ocr/extract-image`
Extract text from image
```javascript
fetch('/api/ocr/extract-image', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        image_path: 'C:/Scans/document.jpg',
        language: 'eng',
        enhance: true
    })
})
```

#### POST `/api/ocr/extract-pdf`
Extract text from PDF
```javascript
fetch('/api/ocr/extract-pdf', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        pdf_path: 'C:/Documents/report.pdf',
        page_range: [1, 10]
    })
})
```

---

## Web Scraping Module

### Overview
The Web Scraping module provides capabilities to fetch and process data from various online sources including weather, news, financial data, and general web content.

### Features
- **Weather Information**: Real-time weather data
- **News Headlines**: Latest news from multiple categories
- **Stock Prices**: Real-time stock market data
- **Cryptocurrency Prices**: Crypto market information
- **Web Scraping**: Extract content from websites
- **Trending Topics**: Get trending from Reddit, GitHub, etc.
- **RSS Monitoring**: Track multiple RSS feeds
- **Search**: Web search functionality

### Installation
```bash
pip install requests beautifulsoup4 feedparser lxml
```

### Usage Examples

#### 1. Get Weather Information
```python
from modules.web_scraping import get_weather_info

# Get weather for any city
weather = get_weather_info(
    location="London",
    api_key=None  # Uses free service if no key provided
)
print(weather)
```

#### 2. Get Latest News
```python
from modules.web_scraping import get_latest_news

# Get technology news
news = get_latest_news(
    category="technology",
    country="us",
    max_articles=5
)
print(news)
```

#### 3. Get Stock Price
```python
from modules.web_scraping import get_stock_price

# Get Apple stock info
stock_info = get_stock_price("AAPL")
print(stock_info)
```

#### 4. Get Cryptocurrency Price
```python
from modules.web_scraping import get_crypto_price

# Get Bitcoin price
crypto_info = get_crypto_price("bitcoin")
print(crypto_info)
```

#### 5. Scrape Website Content
```python
from modules.web_scraping import scrape_website_content

# Extract text from any website
content = scrape_website_content(
    url="https://example.com/article",
    extract_text=True,
    max_length=1000
)
print(content)
```

#### 6. Get Trending Topics
```python
from modules.web_scraping import get_trending_topics

# Get trending from Reddit
trending = get_trending_topics(platform="reddit")
print(trending)

# Get trending GitHub repositories
trending_repos = get_trending_topics(platform="github")
print(trending_repos)
```

#### 7. Monitor RSS Feeds
```python
from modules.web_scraping import monitor_rss_feeds

# Monitor multiple RSS feeds
feeds = [
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://rss.cnn.com/rss/edition.rss"
]

updates = monitor_rss_feeds(feeds, max_items=5)
print(updates)
```

### API Endpoints

#### GET `/api/web/weather?location=London`
Get weather information
```javascript
fetch('/api/web/weather?location=London')
```

#### GET `/api/web/news?category=technology`
Get news headlines
```javascript
fetch('/api/web/news?category=technology&max_articles=10')
```

#### GET `/api/web/stock?symbol=AAPL`
Get stock price
```javascript
fetch('/api/web/stock?symbol=AAPL')
```

#### GET `/api/web/crypto?symbol=bitcoin`
Get cryptocurrency price
```javascript
fetch('/api/web/crypto?symbol=bitcoin')
```

#### POST `/api/web/scrape`
Scrape website content
```javascript
fetch('/api/web/scrape', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        url: 'https://example.com',
        extract_text: true,
        max_length: 1000
    })
})
```

---

## Taskbar Detection Module

### Overview
The Taskbar Detection module provides capabilities to detect, analyze, and interact with running applications and the Windows taskbar.

### Features
- **Process Detection**: List all running processes
- **Window Information**: Get detailed window data
- **Taskbar Analysis**: Analyze taskbar contents
- **Visual Detection**: Use computer vision for taskbar analysis (if multimodal available)
- **App Search**: Find specific applications
- **Complete Desktop Analysis**: Comprehensive system overview

### Installation
```bash
pip install psutil pywin32 Pillow
# Note: pywin32 is Windows-only
```

### Usage Examples

#### 1. Get Running Applications
```python
from modules.taskbar_detection import TaskbarDetector

detector = TaskbarDetector()
apps = detector.get_running_applications()

print(f"Total processes: {apps['summary']['total_processes']}")
print(f"Visible windows: {apps['summary']['total_windows']}")

# Show top memory consumers
for proc in sorted(apps['processes'], key=lambda x: x.get('memory_mb', 0), reverse=True)[:5]:
    print(f"{proc['name']}: {proc['memory_mb']:.1f} MB")
```

#### 2. Detect Taskbar Apps
```python
from modules.taskbar_detection import detect_taskbar_apps

# Get human-readable taskbar analysis
analysis = detect_taskbar_apps()
print(analysis)
```

#### 3. Check Taskbar Capabilities
```python
from modules.taskbar_detection import can_see_taskbar

# Check what detection methods are available
capabilities = can_see_taskbar()
print(capabilities)
```

#### 4. Find Specific App
```python
from modules.taskbar_detection import TaskbarDetector

detector = TaskbarDetector()
result = detector.find_specific_app_in_taskbar("chrome")

if result['found_in_processes']:
    print(f"Found {len(result['matching_processes'])} Chrome processes")
else:
    print("Chrome not running")
```

#### 5. Complete Desktop Analysis
```python
from modules.taskbar_detection import TaskbarDetector

detector = TaskbarDetector()
analysis = detector.get_complete_desktop_analysis()

print(f"Timestamp: {analysis['timestamp']}")
print(f"Detection methods: {', '.join(analysis['summary']['detection_methods'])}")
```

### API Endpoints

#### GET `/api/taskbar/detect`
Detect taskbar applications
```javascript
fetch('/api/taskbar/detect', {
    headers: {
        'Authorization': 'Bearer ' + token
    }
})
```

#### GET `/api/taskbar/capabilities`
Check taskbar capabilities
```javascript
fetch('/api/taskbar/capabilities')
```

#### POST `/api/taskbar/find-app`
Find specific application
```javascript
fetch('/api/taskbar/find-app', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        app_name: 'chrome'
    })
})
```

#### GET `/api/taskbar/running-apps`
Get all running applications
```javascript
fetch('/api/taskbar/running-apps', {
    headers: {
        'Authorization': 'Bearer ' + token
    }
})
```

---

## Testing

### Running Tests

Run all tests:
```bash
# From project root
python -m pytest tests/ -v

# Or using unittest
python -m unittest discover tests -v
```

Run specific module tests:
```bash
# File operations
python tests/test_file_ops.py

# Document OCR
python tests/test_document_ocr.py

# Web scraping
python tests/test_web_scraping.py

# Taskbar detection
python tests/test_taskbar_detection.py
```

### Test Coverage

All modules have comprehensive test suites covering:
- ✅ Basic functionality
- ✅ Edge cases
- ✅ Error handling
- ✅ Input validation
- ✅ Integration scenarios

---

## Best Practices

### File Operations
1. **Always use absolute paths** for reliability
2. **Use dry_run=True** first for destructive operations
3. **Validate paths** before operations
4. **Handle permissions errors** gracefully
5. **Backup important files** before batch operations

### Document OCR
1. **Check dependencies** before using OCR features
2. **Preprocess images** for better accuracy
3. **Choose correct language** for OCR
4. **Handle large PDFs** in chunks
5. **Validate extracted data** before use

### Web Scraping
1. **Respect robots.txt** and terms of service
2. **Implement rate limiting** for multiple requests
3. **Cache responses** when appropriate
4. **Handle network errors** gracefully
5. **Validate scraped data** before processing

### Taskbar Detection
1. **Check permissions** before accessing processes
2. **Handle access denied** errors for system processes
3. **Use appropriate detection** methods for your needs
4. **Cache process lists** if querying frequently
5. **Be mindful of performance** impact

---

## Troubleshooting

### File Operations Issues
**Problem**: Permission denied errors
**Solution**: Run with administrator privileges or check file permissions

**Problem**: Files not organizing correctly
**Solution**: Check that create_subfolders=True and directory exists

### OCR Issues
**Problem**: "Tesseract not installed"
**Solution**: Install Tesseract OCR engine from official sources

**Problem**: Poor OCR accuracy
**Solution**: Use enhance=True and preprocess images before OCR

### Web Scraping Issues
**Problem**: Connection timeout
**Solution**: Check internet connection and increase timeout values

**Problem**: Empty results
**Solution**: Verify URL is accessible and site structure hasn't changed

### Taskbar Detection Issues
**Problem**: Limited window information
**Solution**: Install pywin32 for full Windows API access

**Problem**: Access denied for some processes
**Solution**: Normal behavior for system processes; handle gracefully

---

## Additional Resources

- **API Documentation**: See `docs/API_DOCUMENTATION.md`
- **Contributing**: See `CONTRIBUTING.md`
- **Security**: See `docs/SECURITY.md`
- **Roadmap**: See `ANALYSIS_REPORTS/10_FIX_ROADMAP.md`

---

## Support

For issues, questions, or contributions:
1. Check this documentation
2. Review test files for usage examples
3. Check existing issues on GitHub
4. Create a new issue with detailed information

---

**Last Updated**: November 17, 2025
**Version**: 1.0.0
**Status**: ✅ Complete
