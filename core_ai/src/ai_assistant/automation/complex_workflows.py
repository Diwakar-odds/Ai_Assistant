# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

import os
import logging
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    logger.warning("WARNING: PyPDF2 not found. PDF features in workflows will be disabled.")

from typing import Optional
from ai_assistant.utils.file_ops import smart_file_search
from ai_assistant.integrations.whatsapp import send_whatsapp_message
from ai_assistant.ai.llm_provider import UnifiedChatInterface
import platform

logger = logging.getLogger(__name__)

def find_file_path(filename: str, search_root: str = None) -> Optional[str]:
    """
    Searches for a file and returns its absolute path.
    If search_root is not provided, it tries to guess common locations or search all drives (slow).
    For now, let's default to user's home directory to be safe and fast.
    """
    if not search_root:
        search_root = os.path.expanduser("~")
    
    print(f" Searching for '{filename}' in {search_root}...")
    
    # Simple walk for exact or partial match
    for root, dirs, files in os.walk(search_root):
        for file in files:
            if filename.lower() in file.lower():
                return os.path.join(root, file)
    
    return None

def read_pdf_content(file_path: str) -> Optional[str]:
    """
    Reads text content from a PDF file.
    """
    try:
        print(f"– Reading PDF: {file_path}")
        text = ""
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            # Limit to first 10 pages to avoid token limits and slowness
            num_pages = min(len(reader.pages), 10)
            for i in range(num_pages):
                page = reader.pages[i]
                text += page.extract_text() + "\n"
        return text
    except Exception as e:
        logger.error(f"Error reading PDF {file_path}: {e}")
        return None

def summarize_text(text: str) -> str:
    """
    Summarizes the given text using the LLM.
    """
    print("  Summarizing content...")
    llm = UnifiedChatInterface()
    prompt = (
        "Please provide a concise summary of the following text. "
        "Focus on the key points and main ideas.\n\n"
        f"Text:\n{text[:4000]}" # Limit characters
    )
    try:
        summary = llm.chat(prompt)
        return summary
    except Exception as e:
        return f"Error generating summary: {e}"

def process_file_workflow(filename: str, contact_name: str) -> str:
    """
    Orchestrates the workflow: Find -> Open -> Summarize -> Send WhatsApp.
    """
    # 1. Find
    file_path = find_file_path(filename)
    if not file_path:
        # Try searching in specific drives if on Windows and not found in Home
        if platform.system() == "Windows":
            drives = [f"{d}:\\" for d in "DEF"] # Common data drives
            for drive in drives:
                if os.path.exists(drive):
                    file_path = find_file_path(filename, drive)
                    if file_path:
                        break
        
        if not file_path:
            return f"Œ I couldn't find a file named '{filename}' in your home folder or common drives."

    # 2. Open (Visual confirmation for user)
    try:
        if platform.system() == "Windows":
            os.startfile(file_path)
        else:
            # Linux/Mac fallback
            import subprocess
            subprocess.call(('xdg-open', file_path))
    except Exception as e:
        print(f"š  Could not open file visually: {e}")

    # 3. Summarize (if PDF)
    if file_path.lower().endswith('.pdf'):
        content = read_pdf_content(file_path)
        if not content:
            return f"Œ I found '{file_path}' but couldn't read its content."
        
        summary = summarize_text(content)
    else:
        return f"Œ I found '{file_path}', but I currently only support summarizing PDF files."

    # 4. Send WhatsApp
    message = f"„ Summary of {os.path.basename(file_path)}:\n\n{summary}"
    result = send_whatsapp_message(contact_name, message)
    
    return result


