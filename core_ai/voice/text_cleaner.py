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
    s = re.sub(r'\s+([,.:;?!।])', r'\1', s)

    # 10. Normalize whitespace
    s = re.sub(r'[ \t]+', ' ', s)
    s = re.sub(r'\n+', ' ', s)
    s = s.strip()

    # If only punctuation remains, return empty string (preserve Devanagari scripts)
    if not re.search(r'[\w\u0900-\u097F]', s):
        return ""

    try:
        from ai_assistant.voice.vocabulary_registry import get_vocabulary_registry
        reg = get_vocabulary_registry()
        s = reg.enforce_grammar_and_tone(s)
        s = reg.apply_tts_phonetics(s, target="spoken")
    except Exception:
        pass

    return s


# Phonetic Devanagari fallback map if indic_transliteration is unavailable
_DEVANAGARI_FALLBACK_MAP = {
    'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo', 'ऋ': 'ri',
    'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au', 'अं': 'an', 'अः': 'ah',
    'ऑ': 'o', 'ऍ': 'e',
    'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ng',
    'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'ny',
    'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n',
    'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
    'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
    'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v', 'श': 'sh',
    'ष': 'sh', 'स': 's', 'ह': 'h',
    'क्ष': 'ksh', 'त्र': 'tr', 'ज्ञ': 'gy', 'श्र': 'shr',
    'ड़': 'd', 'ढ़': 'dh', 'क़': 'q', 'ख़': 'kh', 'ग़': 'gh', 'ज़': 'z', 'फ़': 'f',
    'ा': 'aa', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo', 'ृ': 'ri',
    'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au', 'ॉ': 'o', 'ॅ': 'e',
    'ं': 'n', 'ँ': 'n', 'ः': 'h', '्': '', '़': '',
    '।': '.', '॥': '.',
    '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
    '५': '5', '६': '6', '७': '7', '८': '8', '९': '9',
}

_RE_DEVANAGARI_RUN = re.compile(r'[\u0900-\u097F]+')


def _itrans_word_to_hinglish(word: str) -> str:
    """Convert an ITRANS token into natural Romanized Hinglish for English/eSpeak G2P."""
    w = word
    # Normalize special ITRANS digraphs & nasalizations
    w = w.replace('R^i', 'ri').replace('R^I', 'ree').replace('L^i', 'li')
    w = w.replace('.N', 'n').replace('.n', 'n').replace('~N', 'ng').replace('~n', 'ny')
    w = w.replace('.Dh', 'dh').replace('.D', 'd')
    w = w.replace('Ch', 'chh').replace('chh', 'chh')
    w = w.replace('kSh', 'ksh').replace('x', 'ksh').replace('GY', 'gy')
    w = w.replace('Sh', 'sh').replace('shh', 'sh')
    w = w.replace('H', 'h').replace('.a', '')

    # Word-final anusvara (M) is almost always nasal 'n' ("main", "hain", "hoon")
    w = re.sub(r'M(?=[pbm])', 'm', w)
    w = w.replace('M', 'n')

    # Map long vowels & retroflex capitals to clean phonetic ASCII
    repl = (
        ('A', 'aa'),
        ('I', 'ee'),
        ('U', 'oo'),
        ('T', 't'),
        ('D', 'd'),
        ('N', 'n'),
        ('S', 'sh'),
    )
    for src, dst in repl:
        w = w.replace(src, dst)

    # Collapse triple vowels/letters created by replacement
    w = re.sub(r'aaa+', 'aa', w)
    w = re.sub(r'eee+', 'ee', w)
    w = re.sub(r'ooo+', 'oo', w)

    # Common ITRANS medial-schwa artifacts -> natural Hindi/Hinglish spellings
    _medial_fixes = {
        'palsara': 'pulsar',
        'palasar': 'pulsar',
        'palsar': 'pulsar',
        'bosa': 'boss',
        'bos': 'boss',
        'sistama': 'system',
        'sistam': 'system',
        'onalaaina': 'online',
        'onalaain': 'online',
        'onalain': 'online',
        'karanaa': 'karna',
        'karatee': 'kartee',
        'karataa': 'kartaa',
        'karane': 'karne',
        'karanee': 'karnee',
        'karado': 'kardo',
        'sakatee': 'saktee',
        'sakataa': 'saktaa',
        'sunane': 'sunne',
        'sunanaa': 'sunna',
    }
    w_low = w.lower()
    if w_low in _medial_fixes:
        return _medial_fixes[w_low]

    # Hindi schwa deletion on word-final inherent 'a' for multi-char consonant-ending words
    # (e.g. "Aja" -> "aaj", "palsara" -> "palsar", "sisTama" -> "sistam"), while keeping long "aa"
    if len(w) >= 3 and w.endswith('a') and not w.endswith(('aa', 'ia', 'ea', 'oa', 'ua', 'ya')):
        if re.search(r'[bcdfghjklmnpqrstvwxyz]a$', w):
            w = w[:-1]
    if w.lower() in _medial_fixes:
        return _medial_fixes[w.lower()]

    # Clean common short particles for natural eSpeak pronunciation
    if w == 'kyaa':
        w = 'kya'
    elif w == 'naa':
        w = 'na'
    return w


# Empirically tuned Hinglish -> US-eSpeak single-stress phonetic spellings for KittenTTS mini-0.8
# (Zero intra-word hyphens so eSpeak/KittenTTS never splits words into choppy multi-stress breaks.)
_KITTEN_PHONETIC_WORDS = {
    'palsar': 'pulsar',
    'palasar': 'pulsar',
    'palsara': 'pulsar',
    'sistam': 'system',
    'sisatam': 'system',
    'onalaain': 'online',
    'onalain': 'online',
    'bos': 'boss',
    'ye': 'yeh',
    'yah': 'yeh',
    'yeh': 'yeh',
    'ji': 'jee',
    'jee': 'jee',
    'haan': 'haa',
    'han': 'haa',
    'hai': 'hay',
    'hain': 'hen',
    'theek': 'teek',
    'thik': 'teek',
    'khol': 'khole',
    'kholo': 'kholo',
    'rahi': 'rahhee',
    'rahee': 'rahhee',
    'raha': 'rahhaa',
    'rahaa': 'rahhaa',
    'rahe': 'rahhay',
    'abhi': 'abhee',
    'abhee': 'abhee',
    'yahin': 'yaheen',
    'yaheen': 'yaheen',
    'acha': 'achhaa',
    'achha': 'achhaa',
    'achhaa': 'achhaa',
    'nahi': 'nahhee',
    'nahee': 'nahhee',
    'nahin': 'nahheen',
    'naheen': 'nahheen',
    'pe': 'pay',
    'se': 'say',
    'ke': 'kay',
    'liye': 'liyay',
    'kiya': 'kiyaa',
    'kiye': 'kiyay',
    'diya': 'diyaa',
    'diye': 'diyay',
    'liya': 'liyaa',
    'boliye': 'bohliyeh',
    'bolie': 'bohliyeh',
    'suniye': 'sooniyay',
    'sunie': 'sooniyay',
    'bataiye': 'bahtaayen',
    'bataaie': 'bahtaayen',
    'batayein': 'bahtaayen',
    'bataayein': 'bahtaayen',
    'bataaen': 'bahtaayen',
    'batati': 'bahtaatti',
    'bataati': 'bahtaatti',
    'bataatee': 'bahtaatti',
    'batata': 'bahtaattaa',
    'bataata': 'bahtaattaa',
    'karke': 'karkay',
    'karkey': 'karkay',
    'karti': 'kartee',
    'kartee': 'kartee',
    'karatee': 'kartee',
    'karta': 'kartaa',
    'kartaa': 'kartaa',
    'karataa': 'kartaa',
    'karni': 'karnee',
    'karnee': 'karnee',
    'karne': 'karnay',
    'karane': 'karnay',
    'karna': 'karnaa',
    'karnaa': 'karnaa',
    'karanaa': 'karnaa',
    'samajh': 'summujh',
    'chahiye': 'chaahiyay',
    'chaahiye': 'chaahiyay',
    'chaahie': 'chaahiyay',
    'batao': 'bahtao',
    'bataao': 'bahtao',
    'karo': 'karo',
    'karein': 'karrayn',
    'karen': 'karrayn',
    'kardo': 'kardo',
    'karado': 'kardo',
    'dekhiye': 'dekhiyay',
    'dekhie': 'dekhiyay',
    'hoon': 'hoo',
    'hun': 'hoo',
    'kya': 'kiyaa',
    'kyaa': 'kiyaa',
    'berozgaar': 'bayrohzgaar',
    'berozgar': 'bayrohzgaar',
    'rozgaar': 'rohzgaar',
    'rozgar': 'rohzgaar',
    'zaroorat': 'zahroorut',
    'zarurat': 'zahroorut',
    'jaroorat': 'jahroorut',
    'jarurat': 'jahroorut',
    'zaroori': 'zahrooree',
    'zaruri': 'zahrooree',
    'jaroori': 'jahrooree',
    'jaruri': 'jahrooree',
    'zaroor': 'zahroor',
    'jaroor': 'jahroor',
    'pasandeeda': 'pahssandeedaa',
    'pasandida': 'pahssandeedaa',
    'pasand': 'pussund',
    'shukriya': 'shookriyaa',
    'dhanyavaad': 'dhunyavaad',
    'namaste': 'nuhmustay',
    'bilkul': 'billkool',
    'madad': 'muddud',
    'samasya': 'summussyaa',
    'mushkil': 'mooshkill',
    'aasaan': 'aasaan',
    'asan': 'aasaan',
    'behtareen': 'beyhtareen',
    'behtar': 'beyhtur',
    'khabar': 'khuhbur',
    'jaankari': 'jaankahree',
    'jankari': 'jaankahree',
    'ummeed': 'oommeed',
    'umeed': 'oommeed',
    'kismat': 'kissmut',
    'taqat': 'taakut',
    'musibat': 'mooseebut',
    'dost': 'dohst',
    'samay': 'suhmay',
    'waqt': 'wukt',
    'zindagi': 'zinduhgee',
    'duniya': 'dooniyaa',
    'khushi': 'khooshee',
    'pareshan': 'puhreshahn',
    'pareshani': 'puhreshahnee',
    'intezaar': 'intehzahr',
    'intezar': 'intehzahr',
    'tayyar': 'taiyaar',
    'taiyar': 'taiyaar',
    'khub': 'khoob',
    'khoob': 'khoob',
    'khubsoorat': 'khoobsoorut',
    'khubsurat': 'khoobsoorut',
    'khoobsoorat': 'khoobsoorut',
    'khoobsurat': 'khoobsoorut',
    'madadgaar': 'muddudgaar',
    'madadgar': 'muddudgaar',
    'imaandaar': 'imaandaar',
    'imandaar': 'imaandaar',
    'imandar': 'imaandaar',
    'chuneeda': 'chuneedaa',
    'chunida': 'chuneedaa',
    'sanjeeda': 'sunjeedaa',
    'sanjida': 'sunjeedaa',
    'pecheeda': 'peycheedaa',
    'pechida': 'peycheedaa',
}

_HINGLISH_EEDA_ENGLISH_ALLOWLIST = frozenset({"florida", "candida", "valida", "ida", "aida", "frida"})


def _normalize_unmapped_hinglish_token(tok: str) -> str:
    """Apply conservative Roman-Hindi G2P respelling for clear unmapped Hinglish patterns."""
    low = tok.lower()
    if len(low) < 5 or low in _HINGLISH_EEDA_ENGLISH_ALLOWLIST:
        return tok
    out = low
    changed = False
    if out.startswith("khub"):
        out = "khoob" + out[4:]
        changed = True
    elif out.startswith("zar") and "aa" not in out[:3]:
        out = "zah" + out[2:]
        changed = True
    elif out.startswith("beroz"):
        out = "bayrohz" + out[5:]
        changed = True
    if out.endswith(("oorat", "urat")):
        out = re.sub(r"(?:oo|u)rat$", "oorut", out)
        changed = True
    elif out.endswith("eeda") and len(out) >= 6:
        out = re.sub(r"eeda$", "eedaa", out)
        changed = True
    return out if changed else tok

_KITTEN_MAPPED_VALUES = frozenset(v.lower() for v in _KITTEN_PHONETIC_WORDS.values())

_RE_KITTEN_WORD = re.compile(
    r'\b(' + '|'.join(sorted(_KITTEN_PHONETIC_WORDS.keys(), key=len, reverse=True)) + r')\b',
    re.IGNORECASE,
)

# Context-sensitive Hindi "main" ("मैं") and "sun" ("सुन") so English "main file" / "sun" stay untouched
_RE_HINDI_MAIN_AFTER = re.compile(
    r'\bmain(?=\s+(?:abhi|abhee|aaj|yahan|yahin|yaheen|wahan|ghar|ready|online|free|'
    r'theek|thik|teek|bilkul|toh|bhi|hi|bas|khud|ek|is|us|sab|koi|kuch|sun|soon|'
    r'dekh|bol|bata|bataa|bahtao|kar|karun|karungi|karunga|karti|kartee|karta|raha|rahaa|rahhaa|'
    r'rahi|rahee|rahhee|hoon|hun|hoo|hu|pulsar|aap|aapka|aapki|aapko|tum|'
    r'poori|puri|ekdam|tayar|taiyar)\b)',
    re.IGNORECASE,
)
_RE_HINDI_MAIN_BEFORE = re.compile(
    r'(\b(?:haan|haa|ji|jee|aur|toh|lekin|par|magar|kyunki|boss|sir)[,\s]+)main\b'
    r'(?!\s+(?:file|folder|menu|page|window|screen|branch|code|app|function|class|module|server|thread|loop|issue|problem|reason|point|thing)\b)',
    re.IGNORECASE,
)
_RE_HINDI_SUN_AFTER = re.compile(
    r'\bsun(?=\s+(?:raha|rahaa|rahhaa|rahi|rahee|rahhee|rahe|rahhay|lo|le|lena|liya|liyaa|liye|liyay|sakta|sakti|saktee|pa|paye|kar|ke|bhi|na)\b)',
    re.IGNORECASE,
)
_RE_HINDI_SUN_BEFORE = re.compile(
    r'(\b(?:main|meh|haan|haa|ji|jee|abhi|abhee|bilkul|zara|yeh|ye)[,\s]+)sun\b',
    re.IGNORECASE,
)


def prepare_text_for_kitten_tts(text: Optional[str]) -> str:
    """
    Clean text, transliterate any Devanagari spans to Romanized Hinglish, and apply
    empirical US-eSpeak phonetic respelling for natural KittenTTS mini-0.8 speech.
    """
    if not text:
        return ""
    raw = str(text)
    had_devanagari_main = 'मैं' in raw
    had_devanagari_sun = 'सुन' in raw

    hinglish = devanagari_to_hinglish(raw)
    cleaned = clean_text_for_tts(hinglish) or clean_text_for_tts(raw) or ""
    if not cleaned:
        return ""

    # Replace em-dash / en-dash separators with natural commas so KittenTTS doesn't over-pause
    cleaned = re.sub(r'\s*[—–]+\s*', ', ', cleaned)

    # Replace unambiguous Devanagari-derived "main" / "sun" first, then Hinglish context patterns
    if had_devanagari_main:
        cleaned = re.sub(
            r'\bmain\b(?!\s+(?:file|folder|menu|page|window|screen|branch|code|app|function|class|module|server|thread|loop|issue|problem|reason|point|thing)\b)',
            'meh',
            cleaned,
            flags=re.IGNORECASE,
        )
    else:
        cleaned = _RE_HINDI_MAIN_AFTER.sub('meh', cleaned)
        cleaned = _RE_HINDI_MAIN_BEFORE.sub(r'\g<1>meh', cleaned)

    if had_devanagari_sun:
        cleaned = re.sub(r'\bsun\b', 'soon', cleaned, flags=re.IGNORECASE)
    else:
        cleaned = _RE_HINDI_SUN_AFTER.sub('soon', cleaned)
        cleaned = _RE_HINDI_SUN_BEFORE.sub(r'\g<1>soon', cleaned)

    def _phonetic_sub(match: re.Match) -> str:
        tok = match.group(0)
        if len(tok) >= 2 and tok.isupper():
            return tok
        mapped = _KITTEN_PHONETIC_WORDS.get(tok.lower())
        if mapped is not None:
            return mapped
        return _normalize_unmapped_hinglish_token(tok)

    cleaned = _RE_KITTEN_WORD.sub(_phonetic_sub, cleaned)
    # Apply conservative suffix respelling to any remaining unmapped Roman-Hindi tokens
    cleaned = re.sub(
        r'\b[a-z]{5,}\b',
        lambda m: (
            m.group(0)
            if (m.group(0).isupper() or m.group(0).lower() in _KITTEN_MAPPED_VALUES)
            else _normalize_unmapped_hinglish_token(m.group(0))
        ),
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r'\s+,', ',', cleaned)
    cleaned = re.sub(r'\s{2,}', ' ', cleaned).strip()

    try:
        from ai_assistant.voice.vocabulary_registry import get_vocabulary_registry
        reg = get_vocabulary_registry()
        cleaned = reg.enforce_grammar_and_tone(cleaned)
        cleaned = reg.apply_tts_phonetics(cleaned, target="kitten")
    except Exception:
        pass

    return cleaned


def devanagari_to_hinglish(text: Optional[str]) -> str:
    """
    Transliterate Devanagari spans inside mixed Hindi/English text to readable
    Romanized Hinglish while leaving English words untouched.
    """
    if not text:
        return ""
    if not re.search(r'[\u0900-\u097F]', text):
        return text

    # Pre-map registered Devanagari words to their natural Romanized spoken form
    try:
        from ai_assistant.voice.vocabulary_registry import get_vocabulary_registry
        reg = get_vocabulary_registry()
        for _, meta in reg._words.items():
            dev = meta.get("devanagari")
            spk = meta.get("spoken")
            if dev and spk and dev in text:
                text = text.replace(dev, spk)
    except Exception:
        pass

    # Normalize candra vowels and danda before transliteration
    normalized = (
        text.replace('\u0965', '. ')
            .replace('\u0964', '. ')
            .replace('\u0949', '\u094b')  # ॉ -> ो
            .replace('\u0911', '\u0913')  # ऑ -> ओ
            .replace('\u0945', '\u0947')  # ॅ -> े
            .replace('\u090d', '\u090f')  # ऍ -> ए
    )

    try:
        from indic_transliteration import sanscript

        def _replace_run(match: re.Match) -> str:
            token = match.group(0)
            itrans = sanscript.transliterate(token, sanscript.DEVANAGARI, sanscript.ITRANS)
            return _itrans_word_to_hinglish(itrans)

        out = _RE_DEVANAGARI_RUN.sub(_replace_run, normalized)
    except Exception:
        def _replace_fallback(match: re.Match) -> str:
            token = match.group(0)
            out_chars = []
            i = 0
            while i < len(token):
                tri = token[i:i+3]
                bi = token[i:i+2]
                if tri in _DEVANAGARI_FALLBACK_MAP:
                    out_chars.append(_DEVANAGARI_FALLBACK_MAP[tri])
                    i += 3
                elif bi in _DEVANAGARI_FALLBACK_MAP:
                    out_chars.append(_DEVANAGARI_FALLBACK_MAP[bi])
                    i += 2
                else:
                    out_chars.append(_DEVANAGARI_FALLBACK_MAP.get(token[i], ''))
                    i += 1
            return ''.join(out_chars)

        out = _RE_DEVANAGARI_RUN.sub(_replace_fallback, normalized)

    out = re.sub(r'\s+([,.:;?!])', r'\1', out)
    out = re.sub(r'\s{2,}', ' ', out).strip()
    return out


# ── Transparent Roman-Hinglish to Devanagari Mapping for EdgeTTS ─────────────────

_HINGLISH_TO_DEVANAGARI_PHRASES = [
    (re.compile(r'\bho\s+gaya\s+hai\b', re.IGNORECASE), 'हो गया है'),
    (re.compile(r'\bho\s+gayi\s+hai\b', re.IGNORECASE), 'हो गई है'),
    (re.compile(r'\bho\s+gaye\s+hain\b', re.IGNORECASE), 'हो गए हैं'),
    (re.compile(r'\bho\s+gaya\b', re.IGNORECASE), 'हो गया'),
    (re.compile(r'\bho\s+gayi\b', re.IGNORECASE), 'हो गई'),
    (re.compile(r'\bho\s+gaye\b', re.IGNORECASE), 'हो गए'),
    (re.compile(r'\bkar\s+rahi\s+hoon\b', re.IGNORECASE), 'कर रही हूँ'),
    (re.compile(r'\bkar\s+raha\s+hoon\b', re.IGNORECASE), 'कर रहा हूँ'),
    (re.compile(r'\bkar\s+rahi\s+hai\b', re.IGNORECASE), 'कर रही है'),
    (re.compile(r'\bkar\s+rahe\s+hain\b', re.IGNORECASE), 'कर रहे हैं'),
    (re.compile(r'\bkar\s+diya\s+hai\b', re.IGNORECASE), 'कर दिया है'),
    (re.compile(r'\bkar\s+di\s+hai\b', re.IGNORECASE), 'कर दी है'),
    (re.compile(r'\bkar\s+diya\b', re.IGNORECASE), 'कर दिया'),
    (re.compile(r'\bkar\s+di\b', re.IGNORECASE), 'कर दी'),
    (re.compile(r'\bkar\s+deti\s+hoon\b', re.IGNORECASE), 'कर देती हूँ'),
    (re.compile(r'\bkar\s+deta\s+hoon\b', re.IGNORECASE), 'कर देता हूँ'),
    (re.compile(r'\bkar\s+sakti\s+hoon\b', re.IGNORECASE), 'कर सकती हूँ'),
    (re.compile(r'\bkar\s+sakta\s+hoon\b', re.IGNORECASE), 'कर सकता हूँ'),
    (re.compile(r'\bsun\s+rahi\s+hoon\b', re.IGNORECASE), 'सुन रही हूँ'),
    (re.compile(r'\bsun\s+raha\s+hoon\b', re.IGNORECASE), 'सुन रहा हूँ'),
    (re.compile(r'\bsoch\s+kar\b', re.IGNORECASE), 'सोचकर'),
    (re.compile(r'\bsoch\s+ke\b', re.IGNORECASE), 'सोचकर'),
    (re.compile(r'\bek\s+second\b', re.IGNORECASE), 'एक सेकंड'),
    (re.compile(r'\bek\s+pal\b', re.IGNORECASE), 'एक पल'),
    (re.compile(r'\bopen\s+kar\b', re.IGNORECASE), 'ओपन कर'),
    (re.compile(r'\bclose\s+kar\b', re.IGNORECASE), 'क्लोज़ कर'),
    (re.compile(r'\bband\s+kar\b', re.IGNORECASE), 'बंद कर'),
    (re.compile(r'\bshuru\s+kar\b', re.IGNORECASE), 'शुरू कर'),
    (re.compile(r'\bchalu\s+kar\b', re.IGNORECASE), 'चालू कर'),
    (re.compile(r'\bsamajh\s+gayi\b', re.IGNORECASE), 'समझ गई'),
    (re.compile(r'\bsamajh\s+gaya\b', re.IGNORECASE), 'समझ गया'),
    (re.compile(r'\bmulti-step\b', re.IGNORECASE), 'मल्टी-स्टेप'),
    (re.compile(r'\btask\s+chain\b', re.IGNORECASE), 'टास्क चेन'),
    (re.compile(r'\ball\s+set\b', re.IGNORECASE), 'ऑल सेट'),
    (re.compile(r'\bright\s+away\b', re.IGNORECASE), 'तुरंत'),
    (re.compile(r'\bdark\s+mode\b', re.IGNORECASE), 'डार्क मोड'),
    (re.compile(r'\bnight\s+light\b', re.IGNORECASE), 'नाइट लाइट'),
    (re.compile(r'\bopened\s+', re.IGNORECASE), 'ओपन हो गया '),
    (re.compile(r'\bclosed\s+', re.IGNORECASE), 'बंद हो गया '),
    (re.compile(r'\blaunched\s+', re.IGNORECASE), 'लॉन्च हो गया '),
    (re.compile(r'\bset\s+to\s+', re.IGNORECASE), 'सेट हो गया '),
    (re.compile(r'\bswitched\s+to\s+', re.IGNORECASE), 'स्विच हो गया '),
    (re.compile(r'\bturned\s+on\s+', re.IGNORECASE), 'चालू हो गया '),
    (re.compile(r'\bturned\s+off\s+', re.IGNORECASE), 'बंद हो गया '),
    (re.compile(r'\bpaused\b', re.IGNORECASE), 'पॉज़ हो गया'),
    (re.compile(r'\bresumed\b', re.IGNORECASE), 'रेज़्यूमे हो गया'),
    (re.compile(r'\bmuted\b', re.IGNORECASE), 'म्यूट हो गया'),
    (re.compile(r'\bunmuted\b', re.IGNORECASE), 'अनम्यूट हो गया'),
]

_HINGLISH_TO_DEVANAGARI_WORDS = {
    'opened': 'ओपन हो गया',
    'closed': 'बंद हो गया',
    'launched': 'लॉन्च हो गया',
    'started': 'स्टार्ट हो गया',
    'haan': 'हाँ', 'haa': 'हाँ', 'han': 'हाँ', 'ha': 'हाँ',
    'ji': 'जी', 'jee': 'जी',
    'main': 'मैं', 'mai': 'मैं', 'meh': 'मैं',
    'sun': 'सुन', 'soon': 'सुन', 'suno': 'सुनो', 'suniye': 'सुनिए',
    'bol': 'बोल', 'bolo': 'बोलो', 'boliye': 'बोलिए',
    'batana': 'बताना', 'batao': 'बताओ', 'bataiye': 'बताइए', 'batayein': 'बताएं',
    'batata': 'बताता', 'batati': 'बताती', 'batate': 'बताते',
    'bataunga': 'बताऊँगा', 'bataungi': 'बताऊँगी',
    'kar': 'कर', 'karo': 'करो', 'kardo': 'कर दो', 'kijiye': 'कीजिए',
    'karna': 'करना', 'karni': 'करनी', 'karne': 'करने',
    'karta': 'करता', 'karti': 'करती', 'karte': 'करते',
    'karunga': 'करूँगा', 'karungi': 'करूँगी', 'karenge': 'करेंगे',
    'karein': 'करें', 'karen': 'करें',
    'kiya': 'किया', 'kiye': 'किए', 'kiyi': 'की',
    'de': 'दे', 'do': 'दो', 'dein': 'दें', 'dijiye': 'दीजिए',
    'dena': 'देना', 'deni': 'देनी', 'dene': 'देने',
    'diya': 'दिया', 'diye': 'दिए', 'diyi': 'दी',
    'le': 'ले', 'lo': 'लो', 'lein': 'लें', 'lijiye': 'लीजिए',
    'lena': 'लेना', 'leni': 'लेनी', 'lene': 'लेने',
    'liya': 'लिया', 'liye': 'लिए', 'liyi': 'ली',
    'khol': 'खोल', 'kholo': 'खोलो', 'kholi': 'खोली', 'kholna': 'खोलना',
    'kholti': 'खोलती', 'kholta': 'खोलता', 'kholte': 'खोलते',
    'kholunga': 'खोलूँगा', 'kholungi': 'खोलूँगी',
    'band': 'बंद', 'rok': 'रोक', 'roko': 'रोको', 'rokiye': 'रोकिए',
    'chala': 'चला', 'chalao': 'चलाओ', 'chalaiye': 'चलाइए', 'chalana': 'चलाना',
    'chalti': 'चलती', 'chalta': 'चलता', 'chalte': 'चलते',
    'chalega': 'चलेगा', 'chalegi': 'चलेगी', 'chalu': 'चालू',
    'dekh': 'देख', 'dekho': 'देखो', 'dekhiye': 'देखिए', 'dekhna': 'देखना',
    'dekhti': 'देखती', 'dekhta': 'देखता', 'dekhte': 'देखते',
    'dekhunga': 'देखूँगा', 'dekhungi': 'देखूँगी',
    'samajh': 'समझ', 'samajhti': 'समझती', 'samajhta': 'समझता',
    'gaya': 'गया', 'gayi': 'गई', 'gaye': 'गए',
    'soch': 'सोच', 'socho': 'सोचो', 'sochiye': 'सोचिए', 'sochna': 'सोचना',
    'sochti': 'सोचती', 'sochta': 'सोचता', 'sochkar': 'सोचकर',
    'bhej': 'भेज', 'bhejo': 'भेजो', 'bhejiye': 'भेजिए', 'bhejna': 'भेजना',
    'padh': 'पढ़', 'padho': 'पढ़ो', 'padhiye': 'पढ़िए', 'padhna': 'पढ़ना',
    'likh': 'लिख', 'likho': 'लिखो', 'likhiye': 'लिखिए', 'likhna': 'लिखना',
    'aana': 'आना', 'aao': 'आओ', 'aaiye': 'आइए',
    'aata': 'आता', 'aati': 'आती', 'aate': 'आते',
    'ja': 'जा', 'jao': 'जाओ', 'jaiye': 'जाइए', 'jaana': 'जाना',
    'jata': 'जाता', 'jati': 'जाती', 'jate': 'जाते',
    'rakh': 'रख', 'rakho': 'रखो', 'rakhiye': 'रखिए', 'rakhna': 'रखना',
    'uth': 'उठ', 'uthao': 'उठाओ', 'uthaiye': 'उठाइए',
    'la': 'ला', 'lao': 'लाओ', 'laiye': 'लाइए', 'laana': 'लाना',
    'lati': 'लाती', 'lata': 'लाता', 'late': 'लाते',
    'launga': 'लाऊँगा', 'laungi': 'लाऊँगी',
    'badha': 'बढ़ा', 'badhao': 'बढ़ाओ', 'badhaiye': 'बढ़ाइए', 'badhana': 'बढ़ाना',
    'ghata': 'घटा', 'ghatao': 'घटाओ',
    'hai': 'है', 'hain': 'हैं', 'hoon': 'हूँ', 'hun': 'हूँ', 'hu': 'हूँ', 'ho': 'हो',
    'tha': 'था', 'thi': 'थी', 'the': 'थे',
    'hoga': 'होगा', 'hogi': 'होगी', 'honge': 'होंगे',
    'raha': 'रहा', 'rahi': 'रही', 'rahe': 'रहे',
    'sakta': 'सकता', 'sakti': 'सकती', 'sakte': 'सकते',
    'sakunga': 'सकूँगा', 'sakungi': 'सकूँगी',
    'chahiye': 'चाहिए',
    'kya': 'क्या', 'kaise': 'कैसे', 'kaisa': 'कैसा', 'kaisi': 'कैसी',
    'kaun': 'कौन', 'kiska': 'किसका', 'kiske': 'किसके', 'kiski': 'किसकी',
    'kise': 'किसे', 'kisko': 'किसको', 'kis': 'किस',
    'kab': 'कब', 'kyun': 'क्यों', 'kyu': 'क्यों', 'kitna': 'कितना', 'kitne': 'कितने', 'kitni': 'कितनी',
    'aaj': 'आज', 'kal': 'कल', 'parso': 'परसों',
    'subah': 'सुबह', 'dopahar': 'दोपहर', 'shaam': 'शाम', 'raat': 'रात',
    'ab': 'अब', 'abhi': 'अभी', 'turant': 'तुरंत', 'jaldi': 'जल्दी',
    'pehle': 'पहले', 'baad': 'बाद',
    'ek': 'एक', 'do': 'दो', 'teen': 'तीन', 'char': 'चार', 'chaar': 'चार',
    'paanch': 'पाँच', 'che': 'छह', 'chheh': 'छह', 'saat': 'सात', 'aath': 'आठ', 'nau': 'नौ', 'das': 'दस',
    'second': 'सेकंड', 'seconds': 'सेकंड', 'minute': 'मिनट', 'minutes': 'मिनट', 'ghanta': 'घंटा',
    'thoda': 'थोड़ा', 'thodi': 'थोड़ी', 'thode': 'थोड़े',
    'zyada': 'ज़्यादा', 'jyada': 'ज्यादा', 'bahut': 'बहुत', 'bohot': 'बहुत',
    'poora': 'पूरा', 'poori': 'पूरी', 'poore': 'पूरे',
    'aur': 'और', 'ya': 'या', 'lekin': 'लेकिन', 'magar': 'मगर', 'par': 'पर',
    'kyunki': 'क्योंकि', 'kyonki': 'क्योंकि', 'isliye': 'इसलिए',
    'toh': 'तो', 'to': 'तो', 'bhi': 'भी', 'hi': 'ही',
    'bas': 'बस', 'sirf': 'सिर्फ', 'pe': 'पर', 'se': 'से', 'ko': 'को',
    'ka': 'का', 'ke': 'के', 'ki': 'की', 'mein': 'में', 'me': 'में', 'ne': 'ने',
    'saath': 'साथ', 'bina': 'बिना',
    'jaise': 'जैसे', 'waise': 'वैसे', 'aise': 'ऐसे',
    'yahan': 'यहाँ', 'wahan': 'वहाँ', 'kahan': 'कहाँ', 'jahan': 'जहाँ',
    'yahin': 'यहीं', 'wahin': 'वहीं', 'kahin': 'कहीं',
    'andar': 'अंदर', 'baahar': 'बाहर', 'bahar': 'बाहर',
    'upar': 'ऊपर', 'neeche': 'नीचे', 'aage': 'आगे', 'peeche': 'पीछे',
    'saamne': 'सामने', 'samne': 'सामने', 'paas': 'पास', 'door': 'दूर',
    'theek': 'ठीक', 'thik': 'ठीक', 'sahi': 'सही', 'galat': 'गलत',
    'bilkul': 'बिल्कुल', 'zaroor': 'ज़रूर', 'zarur': 'ज़रूर', 'jaroor': 'जरूर',
    'badhiya': 'बढ़िया', 'mast': 'मस्त', 'achha': 'अच्छा', 'achhi': 'अच्छी', 'achhe': 'अच्छे',
    'shandaar': 'शानदार', 'zabardast': 'ज़बरदस्त',
    'ready': 'रेडी', 'tayyar': 'तैयार', 'taiyar': 'तैयार',
    'fresh': 'फ्रेश', 'clean': 'क्लीन', 'saaf': 'साफ़',
    'naya': 'नया', 'nayi': 'नयी', 'naye': 'नये',
    'purana': 'पुराना', 'purani': 'पुरानी', 'purane': 'पुराने',
    'chhota': 'छोटा', 'chhoti': 'छोटी', 'chhote': 'छोटे',
    'bada': 'बड़ा', 'badi': 'बड़ी', 'bade': 'बड़े',
    'namaste': 'नमस्ते', 'shukriya': 'शुक्रिया', 'dhanyavaad': 'धन्यवाद', 'dhanyavad': 'धन्यवाद',
    'kaam': 'काम', 'aadesh': 'आदेश', 'intezaar': 'इंतज़ार', 'intezar': 'इंतज़ार',
    'shuru': 'शुरू', 'shuruat': 'शुरुआत',
    'sawaal': 'सवाल', 'jawab': 'जवाब', 'baat': 'बात', 'baatchit': 'बातचीत',
    'aawaz': 'आवाज़', 'awaz': 'आवाज़', 'pata': 'पता',
    'sab': 'सब', 'sabhi': 'सभी', 'kuch': 'कुछ', 'kuchh': 'कुछ', 'koi': 'कोई',
    'yeh': 'यह', 'ye': 'यह', 'yah': 'यह', 'woh': 'वह', 'wo': 'वह',
    'iska': 'इसका', 'iske': 'इसके', 'iski': 'इसकी',
    'uska': 'उसका', 'uske': 'उसके', 'uski': 'उसकी',
    'inhe': 'इन्हें', 'unhe': 'उन्हें', 'isse': 'इससे', 'usse': 'उससे',
    'isme': 'इसमें', 'ismein': 'इसमें', 'usme': 'उसमें', 'usmein': 'उसमें',
    'aap': 'आप', 'aapka': 'आपका', 'aapke': 'आपके', 'aapki': 'आपकी', 'aapko': 'आपको',
    'tum': 'तुम', 'tumhara': 'तुम्हारा', 'tumhare': 'तुम्हारे', 'tumhari': 'तुम्हारी', 'tumhe': 'तुम्हें',
    'mera': 'मेरा', 'mere': 'मेरे', 'meri': 'मेरी', 'mujhe': 'मुझे', 'mujhko': 'मुझको',
    'hum': 'हम', 'ham': 'हम', 'humein': 'हमें', 'hume': 'हमें',
    'hamaara': 'हमारा', 'hamaare': 'हमारे', 'hamaari': 'हमारी',
    'dost': 'दोस्त', 'bhai': 'भाई', 'yaar': 'यार',
    'boss': 'बॉस', 'sir': 'सर', 'pulsar': 'पल्सर',
    'system': 'सिस्टम', 'systems': 'सिस्टम्स',
    'online': 'ऑनलाइन', 'offline': 'ऑफलाइन',
    'screen': 'स्क्रीन', 'display': 'डिस्प्ले',
    'app': 'ऐप', 'apps': 'ऐप्स',
    'window': 'विंडो', 'windows': 'विंडोज़',
    'chrome': 'क्रोम', 'google': 'गूगल', 'youtube': 'यूट्यूब',
    'whatsapp': 'व्हाट्सएप', 'spotify': 'स्पॉटिफाई',
    'notepad': 'नोटपैड', 'calculator': 'कैलकुलेटर',
    'browser': 'ब्राउज़र', 'settings': 'सेटिंग्स',
    'volume': 'वॉल्यूम', 'sound': 'साउंड', 'audio': 'ऑडियो',
    'brightness': 'ब्राइटनेस',
    'wifi': 'वाई-फाई', 'bluetooth': 'ब्लूटूथ',
    'music': 'म्यूजिक', 'song': 'गाना', 'gaana': 'गाना',
    'video': 'वीडियो', 'media': 'मीडिया', 'playback': 'प्लेबैक',
    'search': 'सर्च', 'lookup': 'लुकअप',
    'open': 'ओपन', 'launch': 'लॉन्च', 'start': 'स्टार्ट',
    'close': 'क्लोज़', 'exit': 'एग्ज़िट', 'quit': 'क्विट',
    'restart': 'रीस्टार्ट', 'shutdown': 'शटडाउन',
    'mute': 'म्यूट', 'unmute': 'अनम्यूट',
    'play': 'प्ले', 'pause': 'पॉज़', 'stop': 'स्टॉप',
    'next': 'नेक्स्ट', 'previous': 'पिछला', 'prev': 'पिछला',
    'track': 'ट्रैक',
    'task': 'टास्क', 'tasks': 'टास्क्स',
    'command': 'कमांड', 'commands': 'कमांड्स',
    'help': 'हेल्प', 'madad': 'मदद', 'order': 'ऑर्डर',
    'plan': 'प्लान', 'scene': 'सीन', 'focus': 'फोकस',
    'done': 'डन', 'complete': 'कम्प्लीट', 'finished': 'फिनिश',
    'update': 'अपडेट', 'adjust': 'एडजस्ट', 'set': 'सेट', 'level': 'लेवल',
    'message': 'मैसेज', 'mail': 'मेल', 'email': 'ईमेल',
    'inbox': 'इनबॉक्स', 'calendar': 'कैलेंडर', 'meeting': 'मीटिंग',
    'error': 'एरर', 'issue': 'इश्यू', 'problem': 'प्रॉब्लम',
    'dikkat': 'दिक्कत', 'pareshaani': 'परेशानी', 'pareshani': 'परेशानी',
    'step': 'स्टेप', 'steps': 'स्टेप्स',
    'sequence': 'सीक्वेंस', 'chain': 'चेन',
    'reset': 'रीसेट', 'clear': 'क्लियर',
    'hello': 'हैलो', 'helo': 'हैलो', 'hey': 'हे', 'hi': 'हाय', 'yo': 'यो',
    'sorry': 'सॉरी', 'welcome': 'वेलकम',
    'percent': 'प्रतिशत', 'percentage': 'प्रतिशत',
}


def hinglish_to_devanagari(text: Optional[str]) -> str:
    """
    Transparently convert Romanized Hindi / Hinglish phrases and tokens into clean
    Devanagari script so EdgeTTS hi-IN-* neural voices synthesize crystal-clear,
    natural human Hindi without any broken American/English phonetic accent.
    """
    if not text:
        return ""
    raw = str(text)

    # If text has no Latin letters at all, it's already purely Devanagari/punctuation
    if not re.search(r'[a-zA-Z]', raw):
        try:
            from ai_assistant.voice.vocabulary_registry import get_vocabulary_registry
            return get_vocabulary_registry().enforce_grammar_and_tone(raw)
        except Exception:
            return raw

    s = raw

    # 0. User custom vocabulary & phonetics (Devanagari for EdgeTTS)
    try:
        from ai_assistant.voice.vocabulary_registry import get_vocabulary_registry
        s = get_vocabulary_registry().apply_tts_phonetics(s, target="devanagari")
    except Exception:
        pass

    # 1. Apply multi-word Hinglish phrases first
    for pat, rep in _HINGLISH_TO_DEVANAGARI_PHRASES:
        s = pat.sub(rep, s)

    # 2. Token-level dictionary transliteration
    def _word_sub(match: re.Match) -> str:
        word = match.group(0)
        low = word.lower()
        mapped = _HINGLISH_TO_DEVANAGARI_WORDS.get(low)
        if mapped:
            return mapped
        return word

    s = re.sub(r'\b[a-zA-Z]+\b', _word_sub, s)

    # 3. Deterministic grammar and tone check
    try:
        from ai_assistant.voice.vocabulary_registry import get_vocabulary_registry
        s = get_vocabulary_registry().enforce_grammar_and_tone(s)
    except Exception:
        pass

    # 4. Clean up spacing and trailing symbols
    s = re.sub(r'\s+([,.:;?!।])', r'\1', s)
    s = re.sub(r'\s{2,}', ' ', s).strip()
    return s
