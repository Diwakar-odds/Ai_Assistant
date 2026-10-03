"""
TTS Text Cleaner Module
Sanitizes and transforms text for Text-To-Speech (TTS) engines.
Removes Markdown syntax, converts LaTeX/math into spoken English,
strips emojis, and cleans up symbols for natural-sounding voice output.
"""

import re
from typing import Optional


# Pre-compiled regex patterns for performance

# Math & LaTeX patterns
RE_DISPLAY_MATH = re.compile(r'\$\$(.*?)\$\$', re.DOTALL)
RE_INLINE_MATH = re.compile(r'\$(.*?)\$')
RE_LATEX_PAREN = re.compile(r'\\\((.*?)\\\)')
RE_LATEX_BRACKET = re.compile(r'\\\[(.*?)\\\]', re.DOTALL)

# Markdown code blocks
RE_CODE_BLOCK = re.compile(r'```[\w]*\n?(.*?)```', re.DOTALL)
RE_INLINE_CODE = re.compile(r'`([^`]+)`')

# Markdown links & images
RE_MD_IMAGE = re.compile(r'!\[([^\]]*)\]\([^\)]+\)')
RE_MD_LINK = re.compile(r'\[([^\]]+)\]\([^\)]+\)')
RE_RAW_URL = re.compile(r'https?://(?:www\.)?([^\s/\?#]+)(?:/[^\s]*)?', re.IGNORECASE)

# Markdown headers & formatting
RE_MD_HEADER = re.compile(r'^\s*#{1,6}\s+', re.MULTILINE)
RE_MD_BOLD_ITALIC = re.compile(r'(\*{1,3}|_{1,3})((?:(?!\1).)+?)\1')
RE_MD_STRIKETHROUGH = re.compile(r'~~(.*?)~~')
RE_MD_BLOCKQUOTE = re.compile(r'^\s*>\s+', re.MULTILINE)
RE_MD_BULLETS = re.compile(r'^\s*[-*+]\s+', re.MULTILINE)
RE_MD_NUMBERED_LIST = re.compile(r'^\s*\d+\.\s+', re.MULTILINE)
RE_MD_HR = re.compile(r'^\s*[-*_]{3,}\s*$', re.MULTILINE)
RE_TABLE_PIPES = re.compile(r'\|')

# HTML tags
RE_HTML_TAGS = re.compile(r'<[^>]+>')

# Unicode Emojis and miscellaneous symbols
RE_EMOJIS = re.compile(
    r'[\U00010000-\U0010ffff]|'  # Astral planes (SMP, SIP, TIP, etc. includes emojis)
    r'[\u2600-\u27BF]|'          # Misc symbols & dingbats
    r'[\u2300-\u23FF]|'          # Misc technical
    r'[\u2B50\u2B55\u2934\u2935\u25AA\u25AB\u25FE\u25FD\u25FB\u25FC\u25B6\u25C0]|'
    r'[\u200d\ufe0f]'            # Zero width joiner / variation selectors
)


def _convert_math_to_speech(math_text: str) -> str:
    """Convert LaTeX math fragments to natural spoken language."""
    text = math_text.strip()
    if not text:
        return ""

    # Fractions: \frac{a}{b} -> a divided by b
    text = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'\1 divided by \2', text)

    # Square roots: \sqrt[n]{x} -> nth root of x, \sqrt{x} -> square root of x
    text = re.sub(r'\\sqrt\[([^\]]+)\]\{([^}]+)\}', r'\1 root of \2', text)
    text = re.sub(r'\\sqrt\{([^}]+)\}', r'square root of \1', text)

    # Common LaTeX math symbols & operators
    latex_replacements = [
        (r'\\neq', ' is not equal to '),
        (r'\\ne\b', ' is not equal to '),
        (r'!=', ' is not equal to '),
        (r'\\approx', ' is approximately '),
        (r'\\leq', ' is less than or equal to '),
        (r'\\le\b', ' is less than or equal to '),
        (r'\\geq', ' is greater than or equal to '),
        (r'\\ge\b', ' is greater than or equal to '),
        (r'<=', ' is less than or equal to '),
        (r'>=', ' is greater than or equal to '),
        (r'\\times', ' times '),
        (r'\\cdot', ' times '),
        (r'\\div', ' divided by '),
        (r'\\pm', ' plus or minus '),
        (r'\\mp', ' minus or plus '),
        (r'\\infty', ' infinity '),
        (r'\\degree', ' degrees '),
        (r'\\sum', ' sum '),
        (r'\\prod', ' product '),
        (r'\\int', ' integral '),
        (r'\\partial', ' partial '),
        (r'\\nabla', ' del '),
        # Greek letters
        (r'\\alpha', ' alpha '),
        (r'\\beta', ' beta '),
        (r'\\gamma', ' gamma '),
        (r'\\delta', ' delta '),
        (r'\\epsilon', ' epsilon '),
        (r'\\theta', ' theta '),
        (r'\\lambda', ' lambda '),
        (r'\\mu', ' mu '),
        (r'\\pi', ' pi '),
        (r'\\sigma', ' sigma '),
        (r'\\tau', ' tau '),
        (r'\\phi', ' phi '),
        (r'\\omega', ' omega '),
        # Formatting wrappers
        (r'\\text\{([^}]+)\}', r'\1'),
        (r'\\mathbf\{([^}]+)\}', r'\1'),
        (r'\\mathit\{([^}]+)\}', r'\1'),
        (r'\\mathrm\{([^}]+)\}', r'\1'),
        (r'\\left', ''),
        (r'\\right', ''),
    ]

    for pattern, replacement in latex_replacements:
        text = re.sub(pattern, replacement, text)

    # Exponents: x^2 -> x squared, x^3 -> x cubed, x^n -> x to the power of n
    text = re.sub(r'(\w+)\^2(?!\d)', r'\1 squared', text)
    text = re.sub(r'(\w+)\^3(?!\d)', r'\1 cubed', text)
    text = re.sub(r'(\w+)\^\{([^}]+)\}', r'\1 to the power of \2', text)
    text = re.sub(r'(\w+)\^(\w+)', r'\1 to the power of \2', text)

    # Subscripts: x_1 -> x 1, x_{n} -> x n
    text = re.sub(r'(\w+)_\{([^}]+)\}', r'\1 \2', text)
    text = re.sub(r'(\w+)_(\w+)', r'\1 \2', text)

    # Replace equals sign with spoken equivalent when padded
    text = re.sub(r'\s*=\s*', ' equals ', text)
    text = re.sub(r'\s*\+\s*', ' plus ', text)
    text = re.sub(r'\s*-\s*', ' minus ', text)

    # Strip any remaining backslashes and braces
    text = text.replace('\\', ' ').replace('{', '').replace('}', '')
    return text.strip()


def clean_text_for_tts(text: Optional[str]) -> str:
    """
    Cleans and prepares text for Text-to-Speech synthesis.
    
    Transforms:
    - Code blocks -> "Here is the code."
    - Inline code -> Plain text content
    - LaTeX Math ($...$, $$...$$) -> Spoken math phrases ("ax squared + bx + c equals 0")
    - Markdown headers, bold, italics, strikethrough -> Clean text
    - Markdown links [text](url) -> "text"
    - Raw URLs -> Domain name
    - HTML tags -> Removed
    - Unicode emojis -> Removed
    - Excessive symbols and punctuation -> Normalized
    
    Returns clean, natural-sounding text suitable for TTS engines.
    """
    if not text:
        return ""

    s = text

    # 1. Handle Code Blocks
    # If there's a multi-line code block, replace with a brief verbal indicator
    s = RE_CODE_BLOCK.sub(' Here is the code. ', s)
    # Inline code: retain the text without backticks
    s = RE_INLINE_CODE.sub(r'\1', s)

    # 2. Handle Math / LaTeX before markdown stripping
    # Display math ($$...$$ and \[...\])
    s = RE_DISPLAY_MATH.sub(lambda m: f" {_convert_math_to_speech(m.group(1))} ", s)
    s = RE_LATEX_BRACKET.sub(lambda m: f" {_convert_math_to_speech(m.group(1))} ", s)
    # Inline math ($...$ and \(...\))
    s = RE_INLINE_MATH.sub(lambda m: f" {_convert_math_to_speech(m.group(1))} ", s)
    s = RE_LATEX_PAREN.sub(lambda m: f" {_convert_math_to_speech(m.group(1))} ", s)

    # 3. Handle Images and Links
    s = RE_MD_IMAGE.sub(r'\1', s)
    s = RE_MD_LINK.sub(r'\1', s)
    # Convert raw URLs (http://example.com/xyz -> example.com)
    s = RE_RAW_URL.sub(r'\1', s)

    # 4. Handle HTML tags
    s = RE_HTML_TAGS.sub(' ', s)

    # 5. Handle Markdown structural elements
    s = RE_MD_HEADER.sub('', s)
    s = RE_MD_BLOCKQUOTE.sub('', s)
    s = RE_MD_HR.sub('', s)
    s = RE_MD_BULLETS.sub('', s)
    s = RE_MD_NUMBERED_LIST.sub('', s)
    s = RE_TABLE_PIPES.sub(' ', s)

    # 6. Handle Markdown inline formatting (bold, italic, strikethrough)
    # Repeat once in case of nested bold/italic e.g. ***bold italic***
    s = RE_MD_BOLD_ITALIC.sub(r'\2', s)
    s = RE_MD_BOLD_ITALIC.sub(r'\2', s)
    s = RE_MD_STRIKETHROUGH.sub(r'\1', s)

    # 7. Remove Emojis
    s = RE_EMOJIS.sub('', s)

    # 8. Clean up stray punctuation/symbols that engines mispronounce
    # Symbols to spoken or space
    s = s.replace('&', ' and ')
    s = s.replace('@', ' at ')
    s = s.replace('%', ' percent ')
    s = s.replace('*', ' ')
    s = s.replace('_', ' ')
    s = s.replace('~', ' ')
    s = s.replace('^', ' ')
    s = s.replace('`', ' ')
    s = s.replace('$', ' ')
    s = s.replace('\\', ' ')

    # 9. Clean up multiple dots (e.g. ellipses '...') to a single period
    s = re.sub(r'\.{2,}', '.', s)
    # Clean up multiple question marks or exclamation marks
    s = re.sub(r'!{2,}', '!', s)
    s = re.sub(r'\?{2,}', '?', s)

    # Remove awkward spaces before punctuation marks: e.g. "0 , where" -> "0, where"
    s = re.sub(r'\s+([,.:;?!])', r'\1', s)

    # 10. Normalize whitespace
    s = re.sub(r'[ \t]+', ' ', s)
    s = re.sub(r'\n+', ' ', s)
    s = s.strip()

    # If only punctuation remains, return empty string
    if not re.search(r'\w', s):
        return ""

    return s
