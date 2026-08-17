"""
Gemini Vision Provider Implementation

Implements the VLMProvider interface using Google's Gemini Vision API.
"""

import os
import io
from typing import Union, Optional, List, Dict, Any
from PIL import Image
import google.generativeai as genai

from .vlm_provider import VLMProvider, VLMResponse


class GeminiVisionProvider(VLMProvider):
    """Google Gemini Vision API implementation."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-1.5-flash",
        **kwargs
    ):
        """
        Initialize Gemini Vision provider.
        
        Args:
            api_key: Gemini API key (uses GEMINI_API_KEY env var if not provided)
            model_name: Gemini model to use
            **kwargs: Additional configuration
        """
        super().__init__(api_key, **kwargs)
        
        # Get API key
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY not found. Set it in environment or pass to constructor."
            )
        
        # Configure Gemini
        try:
            genai.configure(api_key=self.api_key)
        except Exception as e:
            raise ValueError(f"Failed to configure Gemini API: {e}")
        
        # Initialize model
        self.model_name = model_name
        try:
            self.model = genai.GenerativeModel(model_name)
        except Exception as e:
            raise ValueError(f"Failed to initialize Gemini model '{model_name}': {e}")
        
        # Generation config
        self.generation_config = kwargs.get('generation_config', {
            'temperature': 0.4,
            'top_p': 1,
            'top_k': 32,
            'max_output_tokens': 2048,
        })
        
        # Safety settings
        self.safety_settings = kwargs.get('safety_settings', [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ])
    
    def _load_image(self, image: Union[Image.Image, str]) -> Image.Image:
        """Load image from path or return PIL Image as-is."""
        if isinstance(image, str):
            if not os.path.exists(image):
                raise FileNotFoundError(f"Image file not found: {image}")
            return Image.open(image)
        elif isinstance(image, Image.Image):
            return image
        else:
            raise TypeError(f"Unsupported image type: {type(image)}")
    
    def _optimize_image(
        self,
        image: Image.Image,
        max_size: tuple = (1920, 1080)
    ) -> Image.Image:
        """Optimize image for API while maintaining quality."""
        # Check if image needs resizing
        if image.size[0] <= max_size[0] and image.size[1] <= max_size[1]:
            return image
        
        # Calculate new size maintaining aspect ratio
        aspect = image.size[0] / image.size[1]
        
        if aspect > max_size[0] / max_size[1]:
            new_width = max_size[0]
            new_height = int(new_width / aspect)
        else:
            new_height = max_size[1]
            new_width = int(new_height * aspect)
        
        # Resize with high-quality resampling
        optimized = image.copy()
        optimized.thumbnail((new_width, new_height), Image.Resampling.LANCZOS)
        
        return optimized
    
    def analyze_image(
        self,
        image: Union[Image.Image, str],
        prompt: str,
        use_cache: bool = True,
        **kwargs
    ) -> VLMResponse:
        """
        Analyze an image with Gemini Vision.
        
        Args:
            image: PIL Image or path to image file
            prompt: Analysis prompt
            use_cache: Whether to use cache
            **kwargs: Additional Gemini-specific parameters
            
        Returns:
            VLMResponse with analysis
        """
        # Check cache first
        if use_cache:
            cache_key = self._get_cache_key(image, prompt)
            cached = self._check_cache(cache_key)
            if cached:
                return cached
        
        try:
            # Load and optimize image
            img = self._load_image(image)
            img = self._optimize_image(img)
            
            # Generate content
            response = self.model.generate_content(
                [prompt, img],
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )
            
            # Create response object
            vlm_response = VLMResponse(
                text=response.text if response.text else "",
                provider=self.provider_name,
                model=self.model_name,
                metadata={
                    "image_size": img.size,
                    "image_mode": img.mode,
                    "finish_reason": getattr(response, 'finish_reason', None),
                }
            )
            
            # Try to extract JSON if present
            vlm_response.extract_json()
            
            # Cache the response
            if use_cache:
                self._add_to_cache(cache_key, vlm_response)
            
            return vlm_response
            
        except Exception as e:
            # Return error response
            return VLMResponse(
                text=f"Error analyzing image: {str(e)}",
                provider=self.provider_name,
                model=self.model_name,
                confidence=0.0,
                metadata={"error": str(e)}
            )
    
    def extract_text(
        self,
        image: Union[Image.Image, str],
        use_cache: bool = True,
        **kwargs
    ) -> VLMResponse:
        """
        Extract text from image using Gemini Vision OCR.
        
        Args:
            image: PIL Image or path to image file
            use_cache: Whether to use cache
            **kwargs: Additional parameters
            
        Returns:
            VLMResponse with extracted text
        """
        prompt = """Extract all visible text from this image.

Instructions:
1. Extract ALL text you can see, including:
   - Main content text
   - Headings and titles
   - Buttons and UI labels
   - Small or faint text
   
2. Preserve the structure and formatting as much as possible
3. If there are multiple columns, read left to right
4. If the text is in a table, try to maintain the table structure

Return the extracted text without additional commentary.
"""
        
        return self.analyze_image(image, prompt, use_cache=use_cache, **kwargs)
    
    def detect_objects(
        self,
        image: Union[Image.Image, str],
        use_cache: bool = True,
        **kwargs
    ) -> VLMResponse:
        """
        Detect and describe objects in the image.
        
        Args:
            image: PIL Image or path to image file
            use_cache: Whether to use cache
            **kwargs: Additional parameters
            
        Returns:
            VLMResponse with detected objects
        """
        prompt = """Identify and list all objects visible in this image.

For each object, provide:
1. Object name/type
2. Brief description
3. Approximate location in the image
4. Any notable characteristics

Format as a JSON array:
[
  {
    "object": "name",
    "description": "brief description",
    "location": "top-left/center/etc",
    "characteristics": ["characteristic1", "characteristic2"]
  }
]
"""
        
        return self.analyze_image(image, prompt, use_cache=use_cache, **kwargs)
    
    def analyze_document(
        self,
        image: Union[Image.Image, str],
        doc_type: Optional[str] = None,
        use_cache: bool = True,
        **kwargs
    ) -> VLMResponse:
        """
        Analyze a document image with structure understanding.
        
        Args:
            image: Document image
            doc_type: Type hint (invoice, receipt, form, etc.)
            use_cache: Whether to use cache
            **kwargs: Additional parameters
            
        Returns:
            VLMResponse with document analysis
        """
        if doc_type == "invoice" or doc_type == "receipt":
            prompt = """Analyze this invoice/receipt and extract structured data.

Return a JSON object with:
{
  "document_type": "invoice/receipt",
  "vendor": "vendor name",
  "date": "date",
  "invoice_number": "invoice/receipt number",
  "line_items": [
    {"description": "item", "quantity": 1, "price": "amount"}
  ],
  "subtotal": "amount",
  "tax": "amount",
  "total": "total amount",
  "payment_method": "if visible",
  "additional_info": "any other relevant information"
}
"""
        elif doc_type == "form":
            prompt = """Analyze this form and extract all fields and values.

Return a JSON object with:
{
  "form_title": "title if visible",
  "fields": [
    {"label": "field label", "value": "field value", "type": "text/checkbox/etc"}
  ]
}
"""
        else:
            prompt = """Analyze this document and extract:
1. Document type
2. Main headings/sections
3. Key information
4. Tables (if any)
5. Overall structure

Provide a comprehensive analysis with structured data if possible.
"""
        
        return self.analyze_image(image, prompt, use_cache=use_cache, **kwargs)
    
    def analyze_table(
        self,
        image: Union[Image.Image, str],
        use_cache: bool = True,
        **kwargs
    ) -> VLMResponse:
        """
        Extract table data from image.
        
        Args:
            image: Image containing table
            use_cache: Whether to use cache
            **kwargs: Additional parameters
            
        Returns:
            VLMResponse with table data
        """
        prompt = """Extract the table data from this image.

Return as JSON:
{
  "headers": ["column1", "column2", ...],
  "rows": [
    ["value1", "value2", ...],
    ["value1", "value2", ...]
  ],
  "notes": "any additional context about the table"
}

If multiple tables, return array of table objects.
"""
        
        return self.analyze_image(image, prompt, use_cache=use_cache, **kwargs)
    
    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "gemini_vision"
    
    @property
    def supported_features(self) -> List[str]:
        """Return list of supported features."""
        return [
            "image_analysis",
            "ocr",
            "object_detection",
            "ui_element_detection",
            "document_analysis",
            "table_extraction",
            "coordinate_estimation",
            "visual_qa"
        ]
