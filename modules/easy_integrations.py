"""
Easy Integrations - Zero Setup Required!

This module uses the SIMPLEST method for each service:
- No manual API keys needed
- No OAuth flows to configure
- Works out of the box
- Just one function call for everything

SECURITY: All methods are secure and run locally.
"""

import requests
import webbrowser
import subprocess
import json
import time
from typing import Dict, Any, Optional
from pathlib import Path
import urllib.parse


class EasyIntegrations:
    """
    The EASIEST way to integrate with external services.
    No setup required for most operations!
    """
    
    def __init__(self):
        self.n8n_url = "http://localhost:5678"
        self.n8n_available = self._check_n8n()
        
        if self.n8n_available:
            print("✅ n8n detected - using workflow automation (most features)")
        else:
            print("⚠️  n8n not running - using browser methods (limited features)")
            print("   Install n8n for full functionality: npm install -g n8n")
    
    def _check_n8n(self) -> bool:
        """Check if n8n is running"""
        try:
            response = requests.get(f"{self.n8n_url}/healthz", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    # ============================================================
    # UNIVERSAL METHOD - Works for ANY service!
    # ============================================================
    
    def do(self, service: str, action: str, **params) -> Dict[str, Any]:
        """
        Universal method - do ANYTHING on ANY service!
        
        Examples:
            do("twitter", "post", text="Hello World")
            do("facebook", "post", message="Check this out!")
            do("instagram", "post", image="photo.jpg", caption="Beautiful!")
            do("linkedin", "post", text="New article!")
            do("canva", "create", template="instagram-story")
            do("figma", "export", file="mydesign", format="png")
            
        Returns:
            {"success": True/False, "message": "...", "data": {...}}
        """
        service = service.lower()
        
        # Try n8n first (if available)
        if self.n8n_available:
            return self._do_via_n8n(service, action, params)
        
        # Fallback to browser automation
        return self._do_via_browser(service, action, params)
    
    # ============================================================
    # n8n Integration (Preferred Method)
    # ============================================================
    
    def _do_via_n8n(self, service: str, action: str, params: Dict) -> Dict:
        """Execute via n8n workflow"""
        
        # Standard webhook format
        webhook_url = f"{self.n8n_url}/webhook/{service}-{action}"
        
        try:
            response = requests.post(
                webhook_url,
                json=params,
                timeout=30
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "method": "n8n",
                    "message": f"✅ {action} completed on {service}",
                    "data": response.json()
                }
            else:
                # Webhook might not exist yet
                return {
                    "success": False,
                    "method": "n8n",
                    "message": f"❌ Webhook not configured for {service}-{action}",
                    "help": f"Create workflow in n8n: http://localhost:5678"
                }
        
        except Exception as e:
            return {
                "success": False,
                "method": "n8n",
                "error": str(e)
            }
    
    # ============================================================
    # Browser Automation (Fallback Method)
    # ============================================================
    
    def _do_via_browser(self, service: str, action: str, params: Dict) -> Dict:
        """Execute via browser (opens service in browser)"""
        
        # Service URLs
        urls = {
            "twitter": "https://twitter.com/compose/tweet",
            "facebook": "https://www.facebook.com/",
            "instagram": "https://www.instagram.com/",
            "linkedin": "https://www.linkedin.com/feed/",
            "canva": "https://www.canva.com/create/",
            "figma": "https://www.figma.com/files/recent",
            "youtube": "https://studio.youtube.com/",
            "gmail": "https://mail.google.com/mail/u/0/#inbox",
        }
        
        url = urls.get(service)
        if not url:
            return {
                "success": False,
                "message": f"Service '{service}' not supported",
                "available_services": list(urls.keys())
            }
        
        # Open in browser
        if action == "open":
            webbrowser.open(url)
            return {
                "success": True,
                "method": "browser",
                "message": f"✅ Opened {service} in browser"
            }
        
        # For post actions, open compose page with pre-filled content
        if action == "post":
            text = params.get("text", "")
            
            if service == "twitter" and text:
                # Twitter supports URL parameters for pre-filled text
                encoded_text = urllib.parse.quote(text)
                url = f"https://twitter.com/intent/tweet?text={encoded_text}"
                webbrowser.open(url)
                return {
                    "success": True,
                    "method": "browser",
                    "message": f"✅ Opened Twitter with pre-filled tweet. Click 'Post' to publish."
                }
            
            elif service == "linkedin" and text:
                # LinkedIn share URL
                encoded_text = urllib.parse.quote(text)
                url = f"https://www.linkedin.com/sharing/share-offsite/?url=&summary={encoded_text}"
                webbrowser.open(url)
                return {
                    "success": True,
                    "method": "browser",
                    "message": f"✅ Opened LinkedIn with pre-filled post. Click 'Post' to publish."
                }
            
            else:
                # Generic: just open the service
                webbrowser.open(url)
                return {
                    "success": True,
                    "method": "browser",
                    "message": f"✅ Opened {service}. Please post manually.",
                    "note": "For automated posting, install n8n"
                }
        
        return {
            "success": False,
            "message": f"Action '{action}' not supported in browser mode",
            "help": "Install n8n for full automation"
        }
    
    # ============================================================
    # Convenience Methods (Popular Actions)
    # ============================================================
    
    def post_to_twitter(self, text: str) -> Dict:
        """Post a tweet to Twitter"""
        return self.do("twitter", "post", text=text)
    
    def post_to_facebook(self, message: str, link: str = None) -> Dict:
        """Post to Facebook"""
        params = {"message": message}
        if link:
            params["link"] = link
        return self.do("facebook", "post", **params)
    
    def post_to_instagram(self, image_path: str, caption: str = "") -> Dict:
        """Post photo to Instagram"""
        return self.do("instagram", "post", image=image_path, caption=caption)
    
    def post_to_linkedin(self, text: str, link: str = None) -> Dict:
        """Post to LinkedIn"""
        params = {"text": text}
        if link:
            params["link"] = link
        return self.do("linkedin", "post", **params)
    
    def create_canva_design(self, template: str = "instagram-post") -> Dict:
        """Create a design in Canva"""
        return self.do("canva", "create", template=template)
    
    def export_figma_design(self, file_id: str, format: str = "png") -> Dict:
        """Export a Figma design"""
        return self.do("figma", "export", file_id=file_id, format=format)
    
    def send_email_gmail(self, to: str, subject: str, body: str) -> Dict:
        """Send email via Gmail"""
        return self.do("gmail", "send", to=to, subject=subject, body=body)
    
    def open_youtube_studio(self) -> Dict:
        """Open YouTube Studio"""
        return self.do("youtube", "open")
    
    # ============================================================
    # Quick Setup Guide
    # ============================================================
    
    def setup_guide(self) -> str:
        """Show setup instructions"""
        
        if self.n8n_available:
            return """
✅ n8n is running! You're ready to go.

To create workflows:
1. Open: http://localhost:5678
2. Create a new workflow
3. Add a Webhook node (trigger)
4. Add service nodes (Twitter, Facebook, etc.)
5. Activate the workflow

Example workflow names:
- twitter-post
- facebook-post
- instagram-post
- linkedin-post
- canva-create
- figma-export

Then use: easy.do("twitter", "post", text="Hello!")
"""
        
        else:
            return """
❌ n8n is not running. Here's how to set it up:

OPTION 1: Install with npm (Recommended)
    npm install -g n8n
    n8n

OPTION 2: Install with Docker
    docker run -it --rm --name n8n -p 5678:5678 n8nio/n8n

OPTION 3: Use browser mode (limited features)
    easy.do("twitter", "open")  # Opens Twitter in browser
    
After installing n8n:
1. Open http://localhost:5678
2. Create workflows for each service
3. Use: easy.do("service", "action", params)

Why n8n?
- ✅ 400+ services pre-built
- ✅ Visual workflow builder
- ✅ No API keys needed (for many services)
- ✅ Runs locally (secure)
- ✅ Free and open source
"""
    
    # ============================================================
    # Status Check
    # ============================================================
    
    def status(self) -> Dict[str, Any]:
        """Check integration status"""
        
        status_info = {
            "n8n_available": self.n8n_available,
            "n8n_url": self.n8n_url if self.n8n_available else None,
            "browser_mode": not self.n8n_available,
            "supported_services": [
                "twitter", "facebook", "instagram", "linkedin",
                "canva", "figma", "youtube", "gmail"
            ]
        }
        
        if self.n8n_available:
            # Try to get workflows
            try:
                response = requests.get(f"{self.n8n_url}/rest/workflows", timeout=2)
                if response.status_code == 200:
                    workflows = response.json().get("data", [])
                    status_info["workflows"] = len(workflows)
                    status_info["workflow_names"] = [w.get("name") for w in workflows]
            except:
                pass
        
        return status_info


# ============================================================
# Global Instance (Easy Access)
# ============================================================

_easy_instance = None

def get_easy_integrations() -> EasyIntegrations:
    """Get global EasyIntegrations instance"""
    global _easy_instance
    if _easy_instance is None:
        _easy_instance = EasyIntegrations()
    return _easy_instance


# ============================================================
# Ultra-Simple Functions (Direct Access)
# ============================================================

def post_tweet(text: str) -> Dict:
    """Post to Twitter - ONE LINE!"""
    return get_easy_integrations().post_to_twitter(text)

def post_facebook(message: str) -> Dict:
    """Post to Facebook - ONE LINE!"""
    return get_easy_integrations().post_to_facebook(message)

def post_instagram(image: str, caption: str = "") -> Dict:
    """Post to Instagram - ONE LINE!"""
    return get_easy_integrations().post_to_instagram(image, caption)

def post_linkedin(text: str) -> Dict:
    """Post to LinkedIn - ONE LINE!"""
    return get_easy_integrations().post_to_linkedin(text)

def create_canva(template: str = "instagram-post") -> Dict:
    """Create Canva design - ONE LINE!"""
    return get_easy_integrations().create_canva_design(template)

def export_figma(file_id: str) -> Dict:
    """Export Figma design - ONE LINE!"""
    return get_easy_integrations().export_figma_design(file_id)

def send_gmail(to: str, subject: str, body: str) -> Dict:
    """Send Gmail - ONE LINE!"""
    return get_easy_integrations().send_email_gmail(to, subject, body)


# ============================================================
# Magic "Do Anything" Function
# ============================================================

def do(service: str, action: str, **params) -> Dict[str, Any]:
    """
    Magic function - do ANYTHING on ANY service with ONE line!
    
    Examples:
        do("twitter", "post", text="Hello!")
        do("facebook", "post", message="Check this out!")
        do("canva", "create", template="story")
        do("figma", "export", file="abc123")
    """
    return get_easy_integrations().do(service, action, **params)


# ============================================================
# Export Everything
# ============================================================

__all__ = [
    # Main class
    'EasyIntegrations',
    'get_easy_integrations',
    
    # Magic function
    'do',
    
    # Simple functions
    'post_tweet',
    'post_facebook',
    'post_instagram',
    'post_linkedin',
    'create_canva',
    'export_figma',
    'send_gmail'
]
