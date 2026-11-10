"""
Browser Profile Manager
Handles multi-profile browser launching for Google Chrome, Brave, and Microsoft Edge.
Supports named profiles like 'Rancho', 'DIWAKAR', 'DIWAKAR Saurashtra', etc.
"""

import os
import json
import logging
import subprocess
import re
from typing import Dict, Optional, List, Tuple, Any

logger = logging.getLogger(__name__)

CHROME_USER_DATA = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
CHROME_LOCAL_STATE = os.path.join(CHROME_USER_DATA, "Local State")

# Known explicit alias overrides for user convenience and disambiguation
PROFILE_ALIASES = {
    "rancho": "Profile 9",
    "diwakar": "Profile 3",
    "diwakar saurashtra": "Profile 5",
    "saurashtra": "Profile 5",
    "kit": "Profile 5",
    "rajat": "Profile 15",
    "codeforeveryone": "Profile 4"
}

def get_chrome_executable() -> Optional[str]:
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

def get_chrome_profiles() -> Dict[str, Dict]:
    """
    Reads Chrome's Local State file to discover all configured profiles dynamically.
    Returns mapping from profile directory (e.g. 'Profile 9') to profile info.
    """
    profiles = {}
    if not os.path.exists(CHROME_LOCAL_STATE):
        return profiles
        
    try:
        with open(CHROME_LOCAL_STATE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        cache = data.get('profile', {}).get('info_cache', {})
        for dir_name, info in cache.items():
            name = info.get('name', '')
            user_name = info.get('user_name', '')
            gaia_name = info.get('gaia_name', '')
            shortcut_name = info.get('shortcut_name', '')
            
            keys = [
                dir_name.lower(),
                name.lower(),
                user_name.lower(),
                gaia_name.lower(),
                shortcut_name.lower()
            ]
            
            profiles[dir_name] = {
                'directory': dir_name,
                'name': name,
                'email': user_name,
                'gaia_name': gaia_name,
                'shortcut_name': shortcut_name,
                'keys': [k for k in keys if k]
            }
    except Exception as e:
        logger.error(f"Failed to read Chrome profiles: {e}")
        
    return profiles

def resolve_chrome_profile(profile_query: str) -> Optional[str]:
    """
    Resolves a profile query like 'Rancho', 'Diwakar', 'Saurashtra', 'KIT', 'Rajat'
    or 'Profile 9' to the exact directory name (e.g. 'Profile 9').
    Dynamically checks Chrome Local State and falls back/matches against known aliases.
    """
    if not profile_query:
        return None
        
    q = str(profile_query).strip().lower()
    
    # Generic browser words without a profile should not resolve to an arbitrary profile
    if q in ['chrome', 'google chrome', 'browser', 'web browser']:
        return None
        
    # 1. Exact directory match directly (e.g. 'profile 9', 'Profile 15', 'default')
    m = re.match(r'^profile\s*(\d+)$', q, re.IGNORECASE)
    if m:
        dir_candidate = f"Profile {m.group(1)}"
        profiles = get_chrome_profiles()
        if not profiles or dir_candidate in profiles:
            return dir_candidate
            
    # Check exact match on discovered directory names
    discovered = get_chrome_profiles()
    for dir_name in discovered.keys():
        if q == dir_name.lower():
            return dir_name
            
    # 2. Exact match in explicit aliases
    if q in PROFILE_ALIASES:
        return PROFILE_ALIASES[q]
        
    # Strip common wrapper words like 'profile', 'chrome', 'browser'
    clean_q = re.sub(r'\b(chrome|profile|browser|google|account|open|kholo)\b', '', q, flags=re.IGNORECASE).strip()
    if clean_q and clean_q in PROFILE_ALIASES:
        return PROFILE_ALIASES[clean_q]
        
    # 3. Substring / word-boundary matches on known aliases (longest alias first)
    for alias in sorted(PROFILE_ALIASES.keys(), key=len, reverse=True):
        pattern = r'\b' + re.escape(alias) + r'\b'
        if re.search(pattern, q) or (clean_q and re.search(pattern, clean_q)):
            return PROFILE_ALIASES[alias]
            
    # 4. Dynamic matches against Chrome Local State
    # Pass A: Exact match on name, email, gaia_name, shortcut_name, email user, or email domain
    for dir_name, info in discovered.items():
        name = info.get('name', '').lower()
        email = info.get('email', '').lower()
        gaia_name = info.get('gaia_name', '').lower()
        shortcut = info.get('shortcut_name', '').lower()
        email_user = email.split('@')[0] if '@' in email else ''
        domain_parts = email.split('@')[1].split('.') if '@' in email else []
        
        for cand in [clean_q, q]:
            if not cand:
                continue
            if cand in (name, email, gaia_name, shortcut, email_user):
                return dir_name
            if cand in domain_parts and len(cand) >= 3:
                return dir_name

    # Pass B: Word-boundary match on name, gaia_name, or shortcut_name
    for dir_name, info in discovered.items():
        name = info.get('name', '').lower()
        gaia_name = info.get('gaia_name', '').lower()
        shortcut = info.get('shortcut_name', '').lower()
        for field in [name, gaia_name, shortcut]:
            if field and len(field) >= 3:
                pattern = r'\b' + re.escape(field) + r'\b'
                if re.search(pattern, q) or (clean_q and re.search(pattern, clean_q)):
                    return dir_name
                    
    return None

def extract_profile_from_text(text: str) -> Tuple[Optional[str], str]:
    """
    Extracts a browser profile query or alias from user text, returning (profile_name, cleaned_text).
    
    Examples:
        'play Arijit Singh in Rancho' -> ('rancho', 'play Arijit Singh')
        'Rancho kholo' -> ('rancho', '')
        'open saurashtra profile' -> ('saurashtra', 'open')
        'search python in KIT' -> ('kit', 'search python')
    """
    if not text:
        return None, text
    t = text.strip()
    
    # 1. Match against known aliases (longest alias first)
    for alias in sorted(PROFILE_ALIASES.keys(), key=len, reverse=True):
        pattern = r'\b(?:in|on|with|profile|profile\s+of)?\s*' + re.escape(alias) + r'(?:\s+profile|\s+kholo|\s+open)?\b'
        match = re.search(pattern, t, flags=re.IGNORECASE)
        if match:
            cleaned = (t[:match.start()] + ' ' + t[match.end():]).strip()
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            return alias, cleaned
            
    # 2. Match against dynamic profiles discovered from Chrome Local State
    profiles = get_chrome_profiles()
    for dir_name, info in profiles.items():
        name = info.get('name', '').strip().lower()
        if name and len(name) >= 3 and name not in ['default', 'person', 'profile']:
            pattern = r'\b(?:in|on|with|profile|profile\s+of)?\s*' + re.escape(name) + r'(?:\s+profile|\s+kholo|\s+open)?\b'
            match = re.search(pattern, t, flags=re.IGNORECASE)
            if match:
                cleaned = (t[:match.start()] + ' ' + t[match.end():]).strip()
                cleaned = re.sub(r'\s+', ' ', cleaned).strip()
                return dir_name, cleaned
                
    return None, t

def find_profile_in_text(text: str) -> Optional[str]:
    """Returns just the profile alias or name found in the text, or None."""
    prof, _ = extract_profile_from_text(text)
    return prof

def get_requested_profile(
    params: Optional[Dict[str, Any]] = None,
    text: Optional[str] = None,
    ctx: Any = None,
    default: Optional[str] = "Profile 3"
) -> Tuple[Optional[str], str]:
    """
    Dynamically determines the target browser profile following priority:
    1. params['profile'] or params['browser_profile']
    2. Profile name mentioned in query/text (and cleans query of the profile mention)
    3. Context variable 'current_browser_profile'
    4. Sensible default (e.g. 'Profile 3' or 'DIWAKAR')
    
    Returns:
        (resolved_profile_directory, cleaned_text)
    """
    params = params or {}
    text_to_check = text or params.get('query') or params.get('target') or params.get('text') or ''
    cleaned_text = text_to_check
    
    # 1. Explicit profile parameter
    explicit = params.get('profile') or params.get('browser_profile')
    if explicit:
        res = resolve_chrome_profile(str(explicit))
        if res:
            return res, cleaned_text
            
    # 2. Scan text for profile mentions
    if text_to_check:
        found, cleaned = extract_profile_from_text(text_to_check)
        if found:
            res = resolve_chrome_profile(found)
            if res:
                return res, cleaned
                
    # 3. Context variable
    if ctx and hasattr(ctx, 'get_var'):
        ctx_prof = ctx.get_var('current_browser_profile')
        if ctx_prof:
            res = resolve_chrome_profile(str(ctx_prof))
            if res:
                return res, cleaned_text
                
    # 4. Sensible default fallback
    if default:
        res = resolve_chrome_profile(default) or default
        return res, cleaned_text
        
    return None, cleaned_text

def launch_browser_profile(browser: str = "chrome", profile_query: Optional[str] = None, url: Optional[str] = None) -> bool:
    """
    Launch browser with specific profile and optional URL.
    
    Args:
        browser: 'chrome', 'brave', 'edge'
        profile_query: 'Rancho', 'Diwakar', 'DIWAKAR Saurashtra', 'Profile 9', etc.
        url: URL to open (e.g. 'https://www.youtube.com')
    """
    browser_lower = (browser or 'chrome').lower()
    
    if 'chrome' in browser_lower or 'browser' in browser_lower:
        chrome_exe = get_chrome_executable()
        if not chrome_exe:
            logger.error("Google Chrome executable not found")
            return False
            
        profile_dir = resolve_chrome_profile(profile_query) if profile_query else None
        
        args = [chrome_exe]
        if profile_dir:
            args.append(f"--profile-directory={profile_dir}")
            logger.info(f"🌐 Launching Chrome with profile directory: {profile_dir} ('{profile_query}')")
        else:
            logger.info("🌐 Launching Chrome with default profile")
            
        if url:
            args.append(url)
            
        try:
            subprocess.Popen(args)
            return True
        except Exception as e:
            logger.error(f"Failed to launch Chrome: {e}")
            return False
            
    return False
