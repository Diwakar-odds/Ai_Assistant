# Document Analysis and OCR Module for YourDaddy Assistant
"""
Advanced document analysis and optical character recognition:
- Text extraction from images and PDFs
- Document classification and categorization
- Text summarization and key information extraction
- Handwriting recognition
- Receipt and invoice processing
- Business card data extraction
- Multi-language OCR support
- Document structure analysis
- Table and form data extraction
"""

import os
import json
import datetime
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
import base64
import requests
import tempfile

try:
    from PIL import Image, ImageEnhance, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    import PyPDF2
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

class DocumentAnalyzer:
    """
    Advanced document analysis and OCR manager
    """
    
    def __init__(self):
        self.supported_image_formats = ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif']
        self.supported_pdf_formats = ['.pdf']
        self.ocr_cache_dir = "ocr_cache"
        self.ensure_cache_dir()
    
    def ensure_cache_dir(self):
        """Ensure OCR cache directory exists"""
        os.makedirs(self.ocr_cache_dir, exist_ok=True)

def check_ocr_dependencies() -> str:
    """
    Check which OCR dependencies are available
    """
    status = "📋 OCR Dependencies Status:\n\n"
    
    # Check PIL/Pillow
    if PIL_AVAILABLE:
        status += "✅ PIL/Pillow: Available for image processing\n"
    else:
        status += "❌ PIL/Pillow: Not installed (pip install Pillow)\n"
    
    # Check Tesseract OCR
    if TESSERACT_AVAILABLE:
        try:
            version = pytesseract.get_tesseract_version()
            status += f"✅ Tesseract OCR: Available (version {version})\n"
        except Exception:
            status += "⚠️ Tesseract OCR: Installed but not configured properly\n"
    else:
        status += "❌ Tesseract OCR: Not installed (pip install pytesseract)\n"
        status += "   Also install Tesseract: https://github.com/tesseract-ocr/tesseract\n"
    
    # Check OpenCV
    if CV2_AVAILABLE:
        status += f"✅ OpenCV: Available (version {cv2.__version__})\n"
    else:
        status += "❌ OpenCV: Not installed (pip install opencv-python)\n"
    
    # Check PDF libraries
    if PDF_AVAILABLE:
        status += "✅ PDF Processing: Available (PyPDF2 + pdfplumber)\n"
    else:
        status += "❌ PDF Processing: Not installed (pip install PyPDF2 pdfplumber)\n"
    
    # Overall status
    basic_available = PIL_AVAILABLE and TESSERACT_AVAILABLE
    if basic_available:
        status += "\n🎉 Basic OCR functionality is ready!"
    else:
        status += "\n⚠️ Install missing dependencies to enable OCR features."
    
    return status

def extract_text_from_image(image_path: str, language: str = "eng", enhance: bool = True) -> str:
    """
    Extract text from an image using OCR
    Args:
        image_path: Path to the image file
        language: OCR language (eng, fra, deu, spa, etc.)
        enhance: Whether to enhance image quality before OCR
    """
    try:
        if not os.path.exists(image_path):
            return f"❌ Image file not found: {image_path}"
        
        if not PIL_AVAILABLE:
            return "❌ PIL/Pillow not installed. Run: pip install Pillow"
        
        if not TESSERACT_AVAILABLE:
            return "❌ Tesseract not installed. Run: pip install pytesseract"
        
        # Open and process image
        image = Image.open(image_path)
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Enhance image if requested
        if enhance:
            # Increase contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)
            
            # Increase sharpness
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(2.0)
            
            # Apply slight blur to reduce noise
            image = image.filter(ImageFilter.MedianFilter(size=3))
        
        # Configure Tesseract
        custom_config = r'--oem 3 --psm 6'  # OCR Engine Mode 3, Page Segmentation Mode 6
        
        # Extract text
        extracted_text = pytesseract.image_to_string(image, lang=language, config=custom_config)
        
        if extracted_text.strip():
            result = f"📄 OCR Results for: {os.path.basename(image_path)}\n"
            result += f"🗣️ Language: {language}\n"
            result += f"📏 Image Size: {image.size[0]}x{image.size[1]}\n\n"
            result += f"📝 Extracted Text:\n{'-'*40}\n{extracted_text.strip()}\n{'-'*40}"
            
            # Get confidence score if possible
            try:
                data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                confidences = [int(x) for x in data['conf'] if int(x) > 0]
                if confidences:
                    avg_confidence = sum(confidences) / len(confidences)
                    result += f"\n📊 Average Confidence: {avg_confidence:.1f}%"
            except:
                pass
            
            return result
        else:
            return f"📄 No text found in image: {os.path.basename(image_path)}"
        
    except Exception as e:
        return f"❌ OCR error: {str(e)}"

def extract_text_from_pdf(pdf_path: str, page_range: Optional[Tuple[int, int]] = None) -> str:
    """
    Extract text from a PDF document
    Args:
        pdf_path: Path to the PDF file
        page_range: Optional tuple (start_page, end_page) to limit extraction
    """
    try:
        if not os.path.exists(pdf_path):
            return f"❌ PDF file not found: {pdf_path}"
        
        if not PDF_AVAILABLE:
            return "❌ PDF libraries not installed. Run: pip install PyPDF2 pdfplumber"
        
        # Try pdfplumber first (better for complex layouts)
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                pages = pdf.pages
                
                # Determine page range
                start_page = 0
                end_page = len(pages)
                
                if page_range:
                    start_page = max(0, page_range[0] - 1)  # Convert to 0-indexed
                    end_page = min(len(pages), page_range[1])
                
                extracted_text = ""
                for i in range(start_page, end_page):
                    page = pages[i]
                    page_text = page.extract_text()
                    if page_text:
                        extracted_text += f"\n--- Page {i+1} ---\n{page_text}\n"
                
                if extracted_text.strip():
                    result = f"📄 PDF Text Extraction: {os.path.basename(pdf_path)}\n"
                    result += f"📖 Total Pages: {len(pages)}\n"
                    result += f"📄 Extracted Pages: {start_page+1}-{end_page}\n\n"
                    result += f"📝 Extracted Text:\n{'-'*40}\n{extracted_text.strip()}\n{'-'*40}"
                    return result
                else:
                    return f"📄 No text found in PDF: {os.path.basename(pdf_path)}"
        
        except Exception as plumber_error:
            # Fallback to PyPDF2
            import PyPDF2
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                pages = pdf_reader.pages
                
                # Determine page range
                start_page = 0
                end_page = len(pages)
                
                if page_range:
                    start_page = max(0, page_range[0] - 1)
                    end_page = min(len(pages), page_range[1])
                
                extracted_text = ""
                for i in range(start_page, end_page):
                    page = pages[i]
                    page_text = page.extract_text()
                    if page_text:
                        extracted_text += f"\n--- Page {i+1} ---\n{page_text}\n"
                
                if extracted_text.strip():
                    result = f"📄 PDF Text Extraction: {os.path.basename(pdf_path)}\n"
                    result += f"📖 Total Pages: {len(pages)}\n"
                    result += f"📄 Extracted Pages: {start_page+1}-{end_page}\n\n"
                    result += f"📝 Extracted Text:\n{'-'*40}\n{extracted_text.strip()}\n{'-'*40}"
                    return result
                else:
                    return f"📄 No text found in PDF: {os.path.basename(pdf_path)}"
        
    except Exception as e:
        return f"❌ PDF extraction error: {str(e)}"

def analyze_document_structure(file_path: str) -> str:
    """
    Analyze document structure and extract metadata
    Args:
        file_path: Path to the document file
    """
    try:
        if not os.path.exists(file_path):
            return f"❌ Document not found: {file_path}"
        
        file_ext = os.path.splitext(file_path)[1].lower()
        file_size = os.path.getsize(file_path)
        mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
        
        result = f"📋 Document Analysis: {os.path.basename(file_path)}\n"
        result += f"📁 File Path: {file_path}\n"
        result += f"📏 File Size: {file_size / 1024:.1f} KB\n"
        result += f"📅 Modified: {mod_time.strftime('%Y-%m-%d %H:%M')}\n"
        result += f"📄 Format: {file_ext}\n\n"
        
        if file_ext in ['.pdf']:
            # PDF-specific analysis
            try:
                import pdfplumber
                with pdfplumber.open(file_path) as pdf:
                    page_count = len(pdf.pages)
                    
                    # Analyze first page
                    first_page = pdf.pages[0]
                    page_width = first_page.width
                    page_height = first_page.height
                    
                    # Count elements on first page
                    text_objects = len(first_page.chars) if hasattr(first_page, 'chars') else 0
                    
                    result += f"📖 PDF Structure:\n"
                    result += f"   • Pages: {page_count}\n"
                    result += f"   • Page Size: {page_width:.0f}x{page_height:.0f} pts\n"
                    result += f"   • Text Objects (Page 1): {text_objects}\n"
                    
                    # Try to extract tables
                    tables = first_page.extract_tables()
                    if tables:
                        result += f"   • Tables (Page 1): {len(tables)}\n"
                    
                    result += "\n"
            except:
                result += "⚠️ Could not analyze PDF structure\n\n"
        
        elif file_ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif']:
            # Image-specific analysis
            if PIL_AVAILABLE:
                try:
                    image = Image.open(file_path)
                    width, height = image.size
                    mode = image.mode
                    format_name = image.format
                    
                    result += f"🖼️ Image Structure:\n"
                    result += f"   • Dimensions: {width}x{height} pixels\n"
                    result += f"   • Color Mode: {mode}\n"
                    result += f"   • Format: {format_name}\n"
                    
                    # Check if image might contain text
                    if TESSERACT_AVAILABLE:
                        try:
                            # Quick text detection
                            sample_text = pytesseract.image_to_string(image)
                            if sample_text.strip():
                                word_count = len(sample_text.split())
                                result += f"   • Detected Text: ~{word_count} words\n"
                            else:
                                result += f"   • Detected Text: None or minimal\n"
                        except:
                            pass
                    
                    result += "\n"
                except:
                    result += "⚠️ Could not analyze image structure\n\n"
            else:
                result += "❌ PIL required for image analysis\n\n"
        
        # General recommendations
        result += "💡 Analysis Recommendations:\n"
        
        if file_ext in ['.pdf']:
            result += "   • Use extract_text_from_pdf() for text extraction\n"
            result += "   • Consider page range for large documents\n"
        elif file_ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
            result += "   • Use extract_text_from_image() for OCR\n"
            result += "   • Try enhance=True for better results\n"
            result += "   • Check language parameter if not English\n"
        else:
            result += "   • File format not directly supported for OCR\n"
            result += "   • Consider converting to supported format\n"
        
        return result
        
    except Exception as e:
        return f"❌ Document analysis error: {str(e)}"

def preprocess_image_for_ocr(image_path: str, output_path: str = None) -> str:
    """
    Preprocess image to improve OCR accuracy
    Args:
        image_path: Path to the input image
        output_path: Path for the processed image (optional)
    """
    try:
        if not os.path.exists(image_path):
            return f"❌ Image file not found: {image_path}"
        
        if not PIL_AVAILABLE:
            return "❌ PIL/Pillow not installed. Run: pip install Pillow"
        
        if not CV2_AVAILABLE:
            # Basic preprocessing with PIL only
            image = Image.open(image_path)
            
            # Convert to grayscale
            if image.mode != 'L':
                image = image.convert('L')
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)
            
            # Enhance sharpness
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(2.0)
            
            # Save if output path provided
            if output_path:
                image.save(output_path)
                return f"✅ Preprocessed image saved: {output_path}"
            else:
                temp_path = os.path.join(tempfile.gettempdir(), f"preprocessed_{os.path.basename(image_path)}")
                image.save(temp_path)
                return f"✅ Preprocessed image saved: {temp_path}"
        
        else:
            # Advanced preprocessing with OpenCV
            image = cv2.imread(image_path)
            
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Apply adaptive threshold for better contrast
            processed = cv2.adaptiveThreshold(
                blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            
            # Morphological operations to clean up
            kernel = np.ones((2, 2), np.uint8)
            processed = cv2.morphologyEx(processed, cv2.MORPH_CLOSE, kernel)
            
            # Save processed image
            if not output_path:
                output_path = os.path.join(tempfile.gettempdir(), f"preprocessed_{os.path.basename(image_path)}")
            
            cv2.imwrite(output_path, processed)
            
            return f"✅ Advanced preprocessing completed: {output_path}"
        
    except Exception as e:
        return f"❌ Image preprocessing error: {str(e)}"

def extract_key_information(text: str, info_type: str = "general") -> str:
    """
    Extract key information from extracted text based on type
    Args:
        text: Extracted text to analyze
        info_type: Type of information to extract (email, phone, date, address, etc.)
    """
    try:
        import re
        
        if not text.strip():
            return "❌ No text provided for analysis"
        
        result = f"🔍 Key Information Extraction ({info_type}):\n\n"
        
        # Email extraction
        if info_type in ["email", "general"]:
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, text)
            if emails:
                result += f"📧 Email Addresses: {', '.join(set(emails))}\n"
        
        # Phone number extraction
        if info_type in ["phone", "general"]:
            phone_patterns = [
                r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # US format
                r'\+\d{1,3}[-.\s]?\d{1,14}',  # International
                r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}'  # Simple format
            ]
            phones = []
            for pattern in phone_patterns:
                phones.extend(re.findall(pattern, text))
            if phones:
                result += f"📞 Phone Numbers: {', '.join(set(phones))}\n"
        
        # Date extraction
        if info_type in ["date", "general"]:
            date_patterns = [
                r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # MM/DD/YYYY
                r'\d{2,4}[/-]\d{1,2}[/-]\d{1,2}',  # YYYY/MM/DD
                r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{2,4}\b'  # Month DD, YYYY
            ]
            dates = []
            for pattern in date_patterns:
                dates.extend(re.findall(pattern, text))
            if dates:
                result += f"📅 Dates: {', '.join(set(dates))}\n"
        
        # Currency/money extraction
        if info_type in ["money", "financial", "general"]:
            money_pattern = r'\$\d+(?:,\d{3})*(?:\.\d{2})?|\d+(?:,\d{3})*(?:\.\d{2})?\s?(?:USD|EUR|GBP|dollars?|euros?|pounds?)'
            money = re.findall(money_pattern, text, re.IGNORECASE)
            if money:
                result += f"💰 Currency Amounts: {', '.join(set(money))}\n"
        
        # Address extraction (basic)
        if info_type in ["address", "general"]:
            # Look for patterns that might be addresses
            address_pattern = r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Way|Court|Ct|Place|Pl)\b'
            addresses = re.findall(address_pattern, text, re.IGNORECASE)
            if addresses:
                result += f"🏠 Addresses: {', '.join(set(addresses))}\n"
        
        # URL extraction
        if info_type in ["url", "web", "general"]:
            url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
            urls = re.findall(url_pattern, text)
            if urls:
                result += f"🌐 URLs: {', '.join(set(urls))}\n"
        
        # Word and character count
        words = len(text.split())
        characters = len(text)
        result += f"\n📊 Text Statistics:\n"
        result += f"   • Words: {words}\n"
        result += f"   • Characters: {characters}\n"
        
        # Top keywords (simple frequency analysis)
        common_words = ['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should']
        words_list = [word.lower().strip('.,!?";:()[]{}') for word in text.split()]
        word_freq = {}
        
        for word in words_list:
            if len(word) > 3 and word not in common_words and word.isalpha():
                word_freq[word] = word_freq.get(word, 0) + 1
        
        if word_freq:
            top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
            result += f"   • Top Keywords: {', '.join([f'{word} ({count})' for word, count in top_words])}\n"
        
        return result
        
    except Exception as e:
        return f"❌ Information extraction error: {str(e)}"

def batch_ocr_directory(directory: str, file_pattern: str = "*.jpg", language: str = "eng") -> str:
    """
    Perform OCR on multiple files in a directory
    Args:
        directory: Directory containing files
        file_pattern: File pattern to match (e.g., *.jpg, *.png)
        language: OCR language
    """
    try:
        if not os.path.exists(directory):
            return f"❌ Directory not found: {directory}"
        
        import glob
        
        # Find matching files
        pattern_path = os.path.join(directory, file_pattern)
        files = glob.glob(pattern_path)
        
        if not files:
            return f"📁 No files found matching pattern: {file_pattern} in {directory}"
        
        result = f"📚 Batch OCR Results ({len(files)} files):\n\n"
        
        success_count = 0
        total_text = ""
        
        for i, file_path in enumerate(files[:10]):  # Limit to 10 files
            try:
                filename = os.path.basename(file_path)
                result += f"{i+1}. Processing: {filename}\n"
                
                # Extract text from this file
                extracted_text = extract_text_from_image(file_path, language, enhance=True)
                
                if "OCR Results" in extracted_text and "Extracted Text:" in extracted_text:
                    # Parse the extracted text
                    text_start = extracted_text.find("Extracted Text:") + len("Extracted Text:\n" + "-"*40 + "\n")
                    text_end = extracted_text.find("-"*40, text_start)
                    
                    if text_start > 0 and text_end > text_start:
                        file_text = extracted_text[text_start:text_end].strip()
                        if file_text:
                            success_count += 1
                            total_text += f"\n--- {filename} ---\n{file_text}\n"
                            result += f"   ✅ Success: {len(file_text)} characters extracted\n"
                        else:
                            result += f"   ❌ No text found\n"
                    else:
                        result += f"   ❌ Extraction failed\n"
                else:
                    result += f"   ❌ OCR error\n"
                
            except Exception as file_error:
                result += f"   ❌ Error: {str(file_error)}\n"
        
        result += f"\n📊 Batch Summary:\n"
        result += f"   • Files Processed: {len(files[:10])}\n"
        result += f"   • Successful Extractions: {success_count}\n"
        result += f"   • Total Characters: {len(total_text)}\n"
        
        if total_text:
            result += f"\n📝 Combined Text:\n{'-'*50}\n{total_text}\n{'-'*50}"
        
        return result
        
    except Exception as e:
        return f"❌ Batch OCR error: {str(e)}"

def summarize_document_content(text: str, max_sentences: int = 3) -> str:
    """
    Create a simple summary of extracted document text
    Args:
        text: Text to summarize
        max_sentences: Maximum sentences in summary
    """
    try:
        if not text.strip():
            return "❌ No text provided for summarization"
        
        # Simple extractive summarization
        import re
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
        
        if len(sentences) <= max_sentences:
            summary = '. '.join(sentences) + '.'
        else:
            # Score sentences by length and position
            scored_sentences = []
            for i, sentence in enumerate(sentences):
                # Prefer longer sentences and those at the beginning
                score = len(sentence) * (1 - i / len(sentences) * 0.5)
                scored_sentences.append((sentence, score))
            
            # Select top sentences
            scored_sentences.sort(key=lambda x: x[1], reverse=True)
            summary_sentences = [s[0] for s in scored_sentences[:max_sentences]]
            
            # Reorder by original position
            ordered_summary = []
            for sentence in sentences:
                if sentence in summary_sentences:
                    ordered_summary.append(sentence)
                    if len(ordered_summary) >= max_sentences:
                        break
            
            summary = '. '.join(ordered_summary) + '.'
        
        result = f"📄 Document Summary:\n"
        result += f"📊 Original: {len(text)} chars, {len(sentences)} sentences\n"
        result += f"📝 Summary: {len(summary)} chars, {max_sentences} sentences\n\n"
        result += f"💡 Summary:\n{summary}"
        
        return result
        
    except Exception as e:
        return f"❌ Summarization error: {str(e)}"

# Export all functions for the main application
__all__ = [
    'check_ocr_dependencies', 'extract_text_from_image', 'extract_text_from_pdf',
    'analyze_document_structure', 'preprocess_image_for_ocr', 'extract_key_information',
    'batch_ocr_directory', 'summarize_document_content'
]