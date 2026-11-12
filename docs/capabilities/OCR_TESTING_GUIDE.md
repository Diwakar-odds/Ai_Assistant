# OCR Testing Guide

## Overview

The OCR test suite has been restructured to handle external binary dependencies properly. Tests are now categorized with pytest markers to allow selective execution based on environment capabilities.

## Test Categories

### Mock-Only Tests (`@pytest.mark.mock_only`)
- Tests that run with mocked dependencies
- No external binaries required
- Fast execution
- Suitable for CI/CD environments

### OCR Required Tests (`@pytest.mark.ocr_required`) 
- Tests that require Tesseract OCR to be installed
- Needs system fonts for image generation
- May fail in headless environments

### External Binary Tests (`@pytest.mark.external_binary`)
- Tests that depend on system-level binaries
- Includes Tesseract, fonts, reportlab dependencies
- Platform-specific behavior

## Running Tests

### Run All Tests (Default)
```bash
pytest tests/test_document_ocr.py
```

### Run Only Mock Tests (CI-Safe)
```bash
pytest tests/test_document_ocr.py -m "mock_only"
```

### Skip OCR-Dependent Tests
```bash
pytest tests/test_document_ocr.py -m "not ocr_required"
```

### Skip All External Binary Tests
```bash
pytest tests/test_document_ocr.py -m "not external_binary"
```

### Run Only Integration Tests with Full Dependencies
```bash
pytest tests/test_document_ocr.py -m "ocr_required and external_binary"
```

## Dependencies for Full Testing

### Required System Packages
- **Tesseract OCR**: Download from https://github.com/tesseract-ocr/tesseract
- **System Fonts**: Arial or similar TrueType fonts
- **Python Packages**: Listed in requirements.txt

### Windows Installation
```bash
# Install Tesseract
winget install UB-Mannheim.TesseractOCR

# Add to PATH: C:\Program Files\Tesseract-OCR
```

### Linux Installation
```bash
sudo apt-get install tesseract-ocr
sudo apt-get install fonts-dejavu-core
```

### macOS Installation
```bash
brew install tesseract
```

## CI/CD Configuration

### GitHub Actions Example
```yaml
# Fast CI run (mocked tests only)
- name: Run Mock Tests
  run: pytest tests/test_document_ocr.py -m "mock_only"

# Full integration testing
- name: Install Tesseract
  run: sudo apt-get install tesseract-ocr fonts-dejavu-core
  
- name: Run Full OCR Tests  
  run: pytest tests/test_document_ocr.py -m "ocr_required"
```

### Docker Testing
```dockerfile
# Minimal testing image (mocks only)
FROM python:3.9-slim
RUN pip install -r requirements.txt
CMD ["pytest", "-m", "mock_only"]

# Full testing image (with Tesseract)
FROM python:3.9
RUN apt-get update && apt-get install -y tesseract-ocr fonts-dejavu-core
RUN pip install -r requirements.txt  
CMD ["pytest", "-m", "ocr_required"]
```

## Test Structure

### MockedOCR Tests
- Use `unittest.mock.patch` to mock external dependencies
- Test business logic without external binaries
- Verify correct API calls to mocked services
- Fast and reliable in any environment

### Real OCR Tests  
- Create actual images and PDFs
- Test end-to-end functionality
- Verify OCR accuracy and output format
- Require full dependency stack

## Benefits

1. **Faster CI**: Mock tests run in seconds
2. **Environment Independence**: Core logic tested without external deps
3. **Selective Testing**: Choose test level based on environment
4. **Better Debugging**: Separate mocked vs real dependency issues
5. **Documentation**: Clear requirements for each test category

## Migration Guide

### Before (Problematic)
```python
def test_ocr_function(self):
    # Would fail if Tesseract not installed
    result = extract_text_from_image("test.png")
    assert "expected" in result
```

### After (Improved)
```python
@pytest.mark.mock_only
@patch('modules.document_ocr.pytesseract')  
def test_ocr_function_mocked(self, mock_tesseract):
    mock_tesseract.image_to_string.return_value = "expected text"
    result = extract_text_from_image("test.png") 
    assert "expected" in result

@pytest.mark.ocr_required
@pytest.mark.external_binary
def test_ocr_function_real(self):
    # Only runs when Tesseract is available
    result = extract_text_from_image("test.png")
    assert "expected" in result or "Tesseract not installed" in result
```