"""
Unit tests for Document OCR Module

Tests for:
- check_ocr_dependencies()
- extract_text_from_image()
- extract_text_from_pdf()
- analyze_document_structure()
- preprocess_image_for_ocr()
- extract_key_information()
- batch_ocr_directory()
- summarize_document_content()
"""

import unittest
import os
import tempfile
import shutil
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.document_ocr import (
    check_ocr_dependencies,
    extract_text_from_image,
    extract_text_from_pdf,
    analyze_document_structure,
    preprocess_image_for_ocr,
    extract_key_information,
    batch_ocr_directory,
    summarize_document_content
)


class TestOCRDependencies(unittest.TestCase):
    """Test OCR dependencies checking"""
    
    def test_check_ocr_dependencies(self):
        """Test checking which OCR dependencies are available"""
        result = check_ocr_dependencies()
        
        self.assertIn("OCR Dependencies Status", result)
        self.assertIn("PIL", result)
        self.assertIn("Tesseract", result)
        self.assertIn("OpenCV", result)
        self.assertIn("PDF", result)
    
    def test_dependencies_status_format(self):
        """Test that dependency status is properly formatted"""
        result = check_ocr_dependencies()
        
        # Should have checkmarks or X marks
        self.assertTrue("✅" in result or "❌" in result)


class TestDocumentOCR(unittest.TestCase):
    """Test suite for document OCR functions"""
    
    def setUp(self):
        """Set up test fixtures before each test"""
        self.test_dir = tempfile.mkdtemp(prefix="ocr_test_")
        self.addCleanup(self.cleanup_test_dir)
    
    def cleanup_test_dir(self):
        """Clean up test directory after test"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def create_simple_text_image(self, filename="test.png"):
        """Create a simple test image with text (if PIL is available)"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # Create a simple image with text
            img = Image.new('RGB', (400, 100), color='white')
            draw = ImageDraw.Draw(img)
            
            # Try to use default font
            try:
                font = ImageFont.truetype("arial.ttf", 32)
            except:
                font = ImageFont.load_default()
            
            draw.text((10, 30), "Test OCR Text", fill='black', font=font)
            
            filepath = os.path.join(self.test_dir, filename)
            img.save(filepath)
            return filepath
        except ImportError:
            return None
    
    def create_sample_pdf(self, filename="test.pdf"):
        """Create a simple test PDF (if reportlab is available)"""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            
            filepath = os.path.join(self.test_dir, filename)
            c = canvas.Canvas(filepath, pagesize=letter)
            c.drawString(100, 750, "This is a test PDF document")
            c.drawString(100, 730, "Line 2 of text")
            c.save()
            return filepath
        except ImportError:
            # Create a minimal PDF manually
            filepath = os.path.join(self.test_dir, filename)
            # This is a minimal but valid PDF
            pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources 4 0 R /MediaBox [0 0 612 792] /Contents 5 0 R >>
endobj
4 0 obj
<< /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >>
endobj
5 0 obj
<< /Length 44 >>
stream
BT /F1 12 Tf 100 700 Td (Test PDF) Tj ET
endstream
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000214 00000 n 
0000000304 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
398
%%EOF"""
            with open(filepath, 'wb') as f:
                f.write(pdf_content)
            return filepath
    
    # Test extract_text_from_image
    def test_extract_text_from_image_invalid_path(self):
        """Test OCR with non-existent image file"""
        result = extract_text_from_image("/nonexistent/image.png")
        self.assertIn("not found", result)
    
    def test_extract_text_from_image_dependencies(self):
        """Test that function checks for dependencies"""
        # Create a dummy file
        test_file = os.path.join(self.test_dir, "test.png")
        with open(test_file, 'wb') as f:
            f.write(b"fake image data")
        
        result = extract_text_from_image(test_file)
        
        # Should either process or indicate missing dependencies
        self.assertTrue(
            "not installed" in result or 
            "OCR Results" in result or 
            "error" in result.lower()
        )
    
    def test_extract_text_from_image_with_test_image(self):
        """Test OCR on actual test image if possible"""
        test_image = self.create_simple_text_image()
        
        if test_image is None:
            self.skipTest("PIL not available to create test image")
        
        result = extract_text_from_image(test_image)
        
        # Should either extract text or indicate missing Tesseract
        self.assertTrue(
            "Test" in result or 
            "Tesseract not installed" in result or
            "OCR Results" in result
        )
    
    # Test extract_text_from_pdf
    def test_extract_text_from_pdf_invalid_path(self):
        """Test PDF extraction with non-existent file"""
        result = extract_text_from_pdf("/nonexistent/file.pdf")
        self.assertIn("not found", result)
    
    def test_extract_text_from_pdf_dependencies(self):
        """Test that function checks for PDF dependencies"""
        test_pdf = self.create_sample_pdf()
        
        result = extract_text_from_pdf(test_pdf)
        
        # Should either process or indicate missing dependencies
        self.assertTrue(
            "not installed" in result or 
            "PDF Text Extraction" in result or
            "error" in result.lower()
        )
    
    def test_extract_text_from_pdf_with_page_range(self):
        """Test PDF extraction with page range"""
        test_pdf = self.create_sample_pdf()
        
        result = extract_text_from_pdf(test_pdf, page_range=(1, 1))
        
        # Should process or indicate missing dependencies
        self.assertTrue(
            "not installed" in result or 
            "Extracted Pages: 1-1" in result or
            "error" in result.lower()
        )
    
    # Test analyze_document_structure
    def test_analyze_document_structure_invalid_path(self):
        """Test document analysis with non-existent file"""
        result = analyze_document_structure("/nonexistent/doc.pdf")
        self.assertIn("not found", result)
    
    def test_analyze_document_structure_pdf(self):
        """Test analyzing PDF document structure"""
        test_pdf = self.create_sample_pdf()
        
        result = analyze_document_structure(test_pdf)
        
        self.assertIn("Document Analysis", result)
        self.assertIn("File Path:", result)
        self.assertIn("File Size:", result)
    
    def test_analyze_document_structure_image(self):
        """Test analyzing image document structure"""
        test_image = self.create_simple_text_image()
        
        if test_image is None:
            self.skipTest("PIL not available to create test image")
        
        result = analyze_document_structure(test_image)
        
        self.assertIn("Document Analysis", result)
        self.assertIn(".png", result)
    
    # Test preprocess_image_for_ocr
    def test_preprocess_image_invalid_path(self):
        """Test preprocessing with non-existent image"""
        result = preprocess_image_for_ocr("/nonexistent/image.png")
        self.assertIn("not found", result)
    
    def test_preprocess_image_dependencies(self):
        """Test that preprocessing checks dependencies"""
        test_image = self.create_simple_text_image()
        
        if test_image is None:
            self.skipTest("PIL not available to create test image")
        
        result = preprocess_image_for_ocr(test_image)
        
        # Should either process or indicate missing PIL
        self.assertTrue(
            "not installed" in result or 
            "Preprocessed" in result or
            "error" in result.lower()
        )
    
    # Test extract_key_information
    def test_extract_key_information_empty_text(self):
        """Test information extraction with empty text"""
        result = extract_key_information("")
        self.assertIn("No text provided", result)
    
    def test_extract_key_information_email(self):
        """Test extracting email addresses"""
        text = "Contact us at support@example.com or sales@company.org"
        
        result = extract_key_information(text, info_type="email")
        
        self.assertIn("support@example.com", result)
        self.assertIn("sales@company.org", result)
    
    def test_extract_key_information_phone(self):
        """Test extracting phone numbers"""
        text = "Call us at (555) 123-4567 or 555-987-6543"
        
        result = extract_key_information(text, info_type="phone")
        
        self.assertIn("Phone", result)
    
    def test_extract_key_information_dates(self):
        """Test extracting dates"""
        text = "Meeting on 12/25/2024 and Jan 15, 2025"
        
        result = extract_key_information(text, info_type="date")
        
        self.assertIn("Dates:", result)
    
    def test_extract_key_information_money(self):
        """Test extracting currency amounts"""
        text = "The price is $1,299.99 and €500"
        
        result = extract_key_information(text, info_type="money")
        
        self.assertIn("Currency", result)
    
    def test_extract_key_information_urls(self):
        """Test extracting URLs"""
        text = "Visit https://example.com and http://test.org"
        
        result = extract_key_information(text, info_type="url")
        
        self.assertIn("https://example.com", result)
    
    def test_extract_key_information_general(self):
        """Test general information extraction"""
        text = """
        Contact: john@example.com
        Phone: 555-1234
        Date: Jan 15, 2025
        Amount: $1,000
        Website: https://example.com
        """
        
        result = extract_key_information(text, info_type="general")
        
        # Should extract multiple types
        self.assertIn("Email", result)
        self.assertIn("Text Statistics", result)
    
    # Test batch_ocr_directory
    def test_batch_ocr_invalid_directory(self):
        """Test batch OCR with non-existent directory"""
        result = batch_ocr_directory("/nonexistent/path")
        self.assertIn("not found", result)
    
    def test_batch_ocr_no_matching_files(self):
        """Test batch OCR when no files match pattern"""
        result = batch_ocr_directory(self.test_dir, file_pattern="*.jpg")
        self.assertIn("No files found", result)
    
    def test_batch_ocr_with_images(self):
        """Test batch OCR on multiple images"""
        # Create test images
        img1 = self.create_simple_text_image("test1.jpg")
        img2 = self.create_simple_text_image("test2.jpg")
        
        if img1 is None or img2 is None:
            self.skipTest("PIL not available to create test images")
        
        result = batch_ocr_directory(self.test_dir, file_pattern="*.jpg")
        
        self.assertIn("Batch OCR Results", result)
        self.assertIn("files", result)
    
    # Test summarize_document_content
    def test_summarize_empty_text(self):
        """Test summarization with empty text"""
        result = summarize_document_content("")
        self.assertIn("No text provided", result)
    
    def test_summarize_short_text(self):
        """Test summarization of short text"""
        text = "This is a short sentence. It has only two sentences."
        
        result = summarize_document_content(text, max_sentences=2)
        
        self.assertIn("Document Summary", result)
        self.assertIn("Summary:", result)
    
    def test_summarize_long_text(self):
        """Test summarization of longer text"""
        text = """
        Artificial intelligence is transforming the modern world.
        Machine learning algorithms can now process vast amounts of data.
        Natural language processing enables computers to understand human language.
        Computer vision allows machines to interpret visual information.
        Deep learning has revolutionized many fields of AI research.
        The future of AI holds tremendous potential for innovation.
        """
        
        result = summarize_document_content(text, max_sentences=3)
        
        self.assertIn("Document Summary", result)
        self.assertIn("Original:", result)
        self.assertIn("Summary:", result)
    
    def test_summarize_with_custom_sentence_count(self):
        """Test summarization with custom sentence count"""
        text = "Sentence one. Sentence two. Sentence three. Sentence four. Sentence five."
        
        result = summarize_document_content(text, max_sentences=2)
        
        # Should limit to 2 sentences
        self.assertIn("2 sentences", result)


class TestOCREdgeCases(unittest.TestCase):
    """Test suite for edge cases and error handling"""
    
    def test_extract_text_special_characters(self):
        """Test extracting text with special characters"""
        text = "Special chars: @#$%^&*()_+-=[]{}|;':\",./<>?"
        
        result = extract_key_information(text)
        
        # Should not crash
        self.assertIn("Text Statistics", result)
    
    def test_extract_text_unicode(self):
        """Test extracting text with unicode characters"""
        text = "Unicode: café, naïve, 你好, مرحبا"
        
        result = extract_key_information(text)
        
        # Should handle unicode
        self.assertIn("Text Statistics", result)
    
    def test_summarize_single_sentence(self):
        """Test summarization with only one sentence"""
        text = "This is a single sentence."
        
        result = summarize_document_content(text, max_sentences=3)
        
        self.assertIn("Document Summary", result)
    
    def test_extract_key_info_no_matches(self):
        """Test extraction when no patterns match"""
        text = "This text has no emails phones or dates"
        
        result = extract_key_information(text, info_type="email")
        
        # Should still provide statistics
        self.assertIn("Text Statistics", result)


def suite():
    """Create test suite"""
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(TestOCRDependencies))
    test_suite.addTest(unittest.makeSuite(TestDocumentOCR))
    test_suite.addTest(unittest.makeSuite(TestOCREdgeCases))
    return test_suite


if __name__ == '__main__':
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())
