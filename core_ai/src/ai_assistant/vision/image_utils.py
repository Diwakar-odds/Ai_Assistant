# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

"""
Image Processing Utilities for VLM

Provides image preprocessing, optimization, and manipulation utilities
for Vision Language Model operations.
"""

import os
from typing import Tuple, Optional, List, Dict, Any
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import io


class ImageProcessor:
    """Utilities for image processing and optimization."""
    
    @staticmethod
    def optimize_for_vlm(
        image: Image.Image,
        max_size: Tuple[int, int] = (1920, 1080),
        quality: int = 85
    ) -> Image.Image:
        """
        Optimize image for VLM processing.
        
        Args:
            image: Input PIL Image
            max_size: Maximum dimensions (width, height)
            quality: JPEG quality (1-100)
            
        Returns:
            Optimized PIL Image
        """
        # Make a copy
        optimized = image.copy()
        
        # Resize if needed
        if optimized.size[0] > max_size[0] or optimized.size[1] > max_size[1]:
            optimized.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Convert to RGB if needed (VLMs prefer RGB)
        if optimized.mode not in ('RGB', 'L'):
            optimized = optimized.convert('RGB')
        
        return optimized
    
    @staticmethod
    def enhance_for_ocr(image: Image.Image) -> Image.Image:
        """
        Enhance image for better OCR results.
        
        Args:
            image: Input PIL Image
            
        Returns:
            Enhanced PIL Image
        """
        # Convert to RGB
        if image.mode != 'RGB':
            enhanced = image.convert('RGB')
        else:
            enhanced = image.copy()
        
        # Increase contrast
        enhancer = ImageEnhance.Contrast(enhanced)
        enhanced = enhancer.enhance(1.5)
        
        # Increase sharpness
        enhancer = ImageEnhance.Sharpness(enhanced)
        enhanced = enhancer.enhance(2.0)
        
        # Reduce noise with median filter
        enhanced = enhanced.filter(ImageFilter.MedianFilter(size=3))
        
        return enhanced
    
    @staticmethod
    def draw_bounding_box(
        image: Image.Image,
        coordinates: Dict[str, int],
        label: Optional[str] = None,
        color: str = "red",
        width: int = 3
    ) -> Image.Image:
        """
        Draw a bounding box on the image.
        
        Args:
            image: Input PIL Image
            coordinates: Dict with 'x', 'y', 'width', 'height' or bbox
            label: Optional label text
            color: Box color
            width: Line width
            
        Returns:
            Image with bounding box drawn
        """
        # Make a copy
        result = image.copy()
        draw = ImageDraw.Draw(result)
        
        # Extract coordinates
        if 'x' in coordinates and 'y' in coordinates:
            x, y = coordinates['x'], coordinates['y']
            w = coordinates.get('width', 50)
            h = coordinates.get('height', 50)
            bbox = [x - w//2, y - h//2, x + w//2, y + h//2]
        elif 'bbox' in coordinates:
            bbox = coordinates['bbox']
        else:
            # Just draw a point
            x, y = coordinates.get('x', 0), coordinates.get('y', 0)
            bbox = [x-5, y-5, x+5, y+5]
        
        # Draw rectangle
        draw.rectangle(bbox, outline=color, width=width)
        
        # Draw label if provided
        if label:
            try:
                # Try to use a nice font
                font = ImageFont.truetype("arial.ttf", 16)
            except:
                font = ImageFont.load_default()
            
            # Draw label background
            text_bbox = draw.textbbox((bbox[0], bbox[1] - 25), label, font=font)
            draw.rectangle(text_bbox, fill=color)
            draw.text((bbox[0], bbox[1] - 25), label, fill="white", font=font)
        
        return result
    
    @staticmethod
    def annotate_screenshot(
        image: Image.Image,
        elements: List[Dict[str, Any]]
    ) -> Image.Image:
        """
        Annotate screenshot with multiple elements.
        
        Args:
            image: Screenshot image
            elements: List of element dicts with coordinates and labels
            
        Returns:
            Annotated image
        """
        result = image.copy()
        
        colors = ["red", "blue", "green", "yellow", "purple", "orange"]
        
        for i, element in enumerate(elements):
            color = colors[i % len(colors)]
            label = element.get('label') or element.get('text') or f"Element {i+1}"
            coords = element.get('coordinates', {})
            
            if coords:
                result = ImageProcessor.draw_bounding_box(
                    result,
                    coords,
                    label=label,
                    color=color
                )
        
        return result
    
    @staticmethod
    def convert_to_base64(image: Image.Image, format: str = "PNG") -> str:
        """
        Convert PIL Image to base64 string.
        
        Args:
            image: PIL Image
            format: Image format (PNG, JPEG, etc.)
            
        Returns:
            Base64 encoded string
        """
        import base64
        
        buffer = io.BytesIO()
        image.save(buffer, format=format)
        img_bytes = buffer.getvalue()
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
        
        return img_base64
    
    @staticmethod
    def from_base64(base64_str: str) -> Image.Image:
        """
        Create PIL Image from base64 string.
        
        Args:
            base64_str: Base64 encoded image
            
        Returns:
            PIL Image
        """
        import base64
        
        img_bytes = base64.b64decode(base64_str)
        buffer = io.BytesIO(img_bytes)
        image = Image.open(buffer)
        
        return image
    
    @staticmethod
    def convert_pdf_page_to_image(
        pdf_path: str,
        page_num: int = 0,
        dpi: int = 200
    ) -> Optional[Image.Image]:
        """
        Convert a PDF page to image.
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number (0-indexed)
            dpi: Resolution in DPI
            
        Returns:
            PIL Image or None if conversion fails
        """
        try:
            from pdf2image import convert_from_path
            
            images = convert_from_path(
                pdf_path,
                first_page=page_num + 1,
                last_page=page_num + 1,
                dpi=dpi
            )
            
            if images:
                return images[0]
            return None
            
        except ImportError:
            print("pdf2image not installed. Run: pip install pdf2image")
            print("Also requires poppler: https://github.com/oschwartz10612/poppler-windows/releases/")
            return None
        except Exception as e:
            logger.error(f"Error converting PDF to image: {e}")
            return None
    
    @staticmethod
    def convert_pdf_to_images(
        pdf_path: str,
        dpi: int = 200,
        max_pages: Optional[int] = None
    ) -> List[Image.Image]:
        """
        Convert all PDF pages to images.
        
        Args:
            pdf_path: Path to PDF file
            dpi: Resolution in DPI
            max_pages: Maximum number of pages to convert
            
        Returns:
            List of PIL Images
        """
        try:
            from pdf2image import convert_from_path
            
            kwargs = {'dpi': dpi}
            if max_pages:
                kwargs['last_page'] = max_pages
            
            images = convert_from_path(pdf_path, **kwargs)
            return images
            
        except ImportError:
            print("pdf2image not installed. Run: pip install pdf2image")
            return []
        except Exception as e:
            logger.error(f"Error converting PDF to images: {e}")
            return []
    
    @staticmethod
    def crop_region(
        image: Image.Image,
        region: Tuple[int, int, int, int]
    ) -> Image.Image:
        """
        Crop a region from the image.
        
        Args:
            image: Input image
            region: (left, top, right, bottom) coordinates
            
        Returns:
            Cropped image
        """
        return image.crop(region)
    
    @staticmethod
    def resize_maintaining_aspect(
        image: Image.Image,
        target_size: Tuple[int, int]
    ) -> Image.Image:
        """
        Resize image maintaining aspect ratio.
        
        Args:
            image: Input image
            target_size: Target (width, height)
            
        Returns:
            Resized image
        """
        resized = image.copy()
        resized.thumbnail(target_size, Image.Resampling.LANCZOS)
        return resized
    
    @staticmethod
    def get_image_info(image: Image.Image) -> Dict[str, Any]:
        """
        Get information about an image.
        
        Args:
            image: PIL Image
            
        Returns:
            Dictionary with image information
        """
        return {
            "size": image.size,
            "width": image.width,
            "height": image.height,
            "mode": image.mode,
            "format": getattr(image, 'format', None),
            "has_transparency": image.mode in ('RGBA', 'LA', 'P'),
        }
