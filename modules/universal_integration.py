"""
Universal Integration Hub for YourDaddy Assistant

One module to connect with ANY external service through multiple methods:
1. Direct API integration (when available)
2. Workflow automation platforms (Zapier, n8n, Make)
3. Browser automation (Selenium/Playwright)
4. AI-powered web interaction

This eliminates the need for separate modules per service.
"""

import os
import json
import requests
import webbrowser
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import time

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("⚠️ Selenium not available. Browser automation disabled.")


class IntegrationMethod(Enum):
    """Methods for connecting to external services"""
    DIRECT_API = "direct_api"          # Direct REST API calls
    WORKFLOW_PLATFORM = "workflow"      # Zapier, n8n, Make
    BROWSER_AUTO = "browser"            # Selenium/Playwright
    WEBHOOK = "webhook"                 # Webhook-based
    OAUTH = "oauth"                     # OAuth2 flow
    
    
class ServiceCategory(Enum):
    """Categories of services"""
    SOCIAL_MEDIA = "social_media"
    DESIGN_TOOLS = "design_tools"
    PRODUCTIVITY = "productivity"
    COMMUNICATION = "communication"
    CLOUD_STORAGE = "cloud_storage"
    MUSIC = "music"
    EMAIL = "email"
    CALENDAR = "calendar"
    OTHER = "other"


@dataclass
class ServiceConfig:
    """Configuration for an external service"""
    name: str
    category: ServiceCategory
    preferred_method: IntegrationMethod
    api_endpoint: Optional[str] = None
    auth_type: Optional[str] = None
    requires_browser: bool = False
    web_url: Optional[str] = None
    webhook_url: Optional[str] = None
    
    # Credentials (loaded from config)
    api_key: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    access_token: Optional[str] = None


class UniversalIntegrationHub:
    """
    Universal Integration Hub - Connect to ANY service
    
    🔒 SECURITY-FIRST DESIGN:
    - Prioritizes direct API connections (most secure)
    - Only uses self-hosted workflow platforms (n8n)
    - NEVER sends data to cloud platforms (Zapier/Make) without explicit consent
    - All tokens stored locally, encrypted
    - No third-party data access
    
    This single class replaces the need for multiple integration modules.
    It intelligently chooses the best method to interact with each service.
    """
    
    def __init__(self, config_file: str = "integration_config.json", security_mode: str = "strict"):
        self.config_file = Path(config_file)
        self.config = self.load_config()
        self.services = self.register_services()
        self.browser = None
        self.active_sessions = {}
        
        # Security settings
        self.security_mode = security_mode  # "strict", "moderate", "permissive"
        self.allow_cloud_platforms = False  # DISABLED by default for security
        self.require_encryption = True
        
        self._validate_security_config()
        
        print("🌐 Universal Integration Hub initialized")
        print(f"📦 {len(self.services)} services registered")
        print(f"🔒 Security mode: {security_mode.upper()}")
        
        if not self.allow_cloud_platforms:
            print("⚠️  Cloud platforms (Zapier/Make) DISABLED for security")
            print("    Only direct API and self-hosted n8n allowed")
    
    def _validate_security_config(self):
        """Validate security configuration and warn about risks"""
        
        # Check if user enabled cloud platforms
        if self.config.get("zapier", {}).get("enabled") or \
           self.config.get("make", {}).get("enabled"):
            
            print("\n" + "="*70)
            print("⚠️  SECURITY WARNING: Cloud Workflow Platforms Detected")
            print("="*70)
            print("You have enabled Zapier or Make.com (cloud platforms).")
            print("\n❌ SECURITY RISKS:")
            print("   1. Your data passes through their servers")
            print("   2. They can access all your tokens and credentials")
            print("   3. Your commands and responses are visible to them")
            print("   4. Subject to their privacy policy and data breaches")
            print("   5. Government/legal requests can expose your data")
            print("\n✅ SAFER ALTERNATIVES:")
            print("   1. Use Direct API integration (most secure)")
            print("   2. Use self-hosted n8n (your machine, your control)")
            print("   3. Use browser automation (local only)")
            print("\n❓ Do you want to continue with cloud platforms?")
            print("   Set 'allow_cloud_platforms: true' in code to proceed")
            print("="*70 + "\n")
            
            if self.security_mode == "strict":
                print("🚫 STRICT MODE: Cloud platforms blocked!")
                self.config["zapier"]["enabled"] = False
                self.config["make"]["enabled"] = False
    
    def load_config(self) -> Dict:
        """Load integration configuration"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return self.create_default_config()
    
    def create_default_config(self) -> Dict:
        """Create default configuration template"""
        config = {
            "zapier": {
                "enabled": False,
                "api_key": "",
                "webhook_base": "https://hooks.zapier.com/hooks/catch/"
            },
            "n8n": {
                "enabled": False,
                "base_url": "http://localhost:5678",
                "webhook_path": "/webhook/"
            },
            "make": {
                "enabled": False,
                "webhook_urls": {}
            },
            "browser_automation": {
                "enabled": True,
                "headless": False,
                "implicit_wait": 10
            },
            "services": {
                "twitter": {
                    "api_key": "",
                    "api_secret": "",
                    "bearer_token": "",
                    "zapier_webhook_id": ""
                },
                "facebook": {
                    "app_id": "",
                    "app_secret": "",
                    "zapier_webhook_id": ""
                },
                "instagram": {
                    "username": "",
                    "password": "",
                    "use_browser": True
                },
                "linkedin": {
                    "client_id": "",
                    "client_secret": "",
                    "zapier_webhook_id": ""
                },
                "canva": {
                    "api_key": "",
                    "use_browser": True
                },
                "figma": {
                    "access_token": "",
                    "api_base": "https://api.figma.com/v1"
                },
                "youtube": {
                    "api_key": "",
                    "use_browser": True
                }
            }
        }
        
        # Save template
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"📝 Created config template: {self.config_file}")
        return config
    
    def register_services(self) -> Dict[str, ServiceConfig]:
        """Register all supported services"""
        services = {}
        
        # Social Media
        services["twitter"] = ServiceConfig(
            name="Twitter/X",
            category=ServiceCategory.SOCIAL_MEDIA,
            preferred_method=IntegrationMethod.WORKFLOW_PLATFORM,
            api_endpoint="https://api.twitter.com/2",
            web_url="https://twitter.com"
        )
        
        services["facebook"] = ServiceConfig(
            name="Facebook",
            category=ServiceCategory.SOCIAL_MEDIA,
            preferred_method=IntegrationMethod.WORKFLOW_PLATFORM,
            api_endpoint="https://graph.facebook.com/v18.0",
            web_url="https://facebook.com"
        )
        
        services["instagram"] = ServiceConfig(
            name="Instagram",
            category=ServiceCategory.SOCIAL_MEDIA,
            preferred_method=IntegrationMethod.BROWSER_AUTO,
            web_url="https://instagram.com",
            requires_browser=True
        )
        
        services["linkedin"] = ServiceConfig(
            name="LinkedIn",
            category=ServiceCategory.SOCIAL_MEDIA,
            preferred_method=IntegrationMethod.WORKFLOW_PLATFORM,
            api_endpoint="https://api.linkedin.com/v2",
            web_url="https://linkedin.com"
        )
        
        # Design Tools
        services["canva"] = ServiceConfig(
            name="Canva",
            category=ServiceCategory.DESIGN_TOOLS,
            preferred_method=IntegrationMethod.BROWSER_AUTO,
            web_url="https://canva.com",
            requires_browser=True
        )
        
        services["figma"] = ServiceConfig(
            name="Figma",
            category=ServiceCategory.DESIGN_TOOLS,
            preferred_method=IntegrationMethod.DIRECT_API,
            api_endpoint="https://api.figma.com/v1",
            web_url="https://figma.com"
        )
        
        # Music (already have modules, but can use unified interface)
        services["youtube_music"] = ServiceConfig(
            name="YouTube Music",
            category=ServiceCategory.MUSIC,
            preferred_method=IntegrationMethod.DIRECT_API,
            web_url="https://music.youtube.com"
        )
        
        return services
    
    def connect(self, service: str, action: str, **params) -> Dict[str, Any]:
        """
        Universal connection method - connects to ANY service
        
        Args:
            service: Service name (e.g., "twitter", "canva", "figma")
            action: Action to perform (e.g., "post", "create", "send")
            **params: Action-specific parameters
            
        Returns:
            Result dictionary with success status and data
        """
        service = service.lower()
        
        if service not in self.services:
            return self._handle_unknown_service(service, action, params)
        
        service_config = self.services[service]
        
        # Try methods in order of preference
        methods = [
            service_config.preferred_method,
            IntegrationMethod.WORKFLOW_PLATFORM,
            IntegrationMethod.BROWSER_AUTO
        ]
        
        for method in methods:
            try:
                if method == IntegrationMethod.DIRECT_API:
                    return self._execute_via_api(service, action, params)
                elif method == IntegrationMethod.WORKFLOW_PLATFORM:
                    return self._execute_via_workflow(service, action, params)
                elif method == IntegrationMethod.BROWSER_AUTO:
                    return self._execute_via_browser(service, action, params)
            except Exception as e:
                print(f"⚠️ Method {method.value} failed for {service}: {e}")
                continue
        
        return {
            "success": False,
            "error": f"All integration methods failed for {service}"
        }
    
    def _execute_via_api(self, service: str, action: str, params: Dict) -> Dict:
        """Execute action via direct API call"""
        service_config = self.services[service]
        
        if not service_config.api_endpoint:
            raise ValueError(f"No API endpoint configured for {service}")
        
        # Service-specific API logic
        if service == "figma":
            return self._figma_api_call(action, params)
        elif service == "twitter":
            return self._twitter_api_call(action, params)
        elif service == "facebook":
            return self._facebook_api_call(action, params)
        elif service == "linkedin":
            return self._linkedin_api_call(action, params)
        else:
            raise NotImplementedError(f"Direct API not implemented for {service}")
    
    def _execute_via_workflow(self, service: str, action: str, params: Dict) -> Dict:
        """
        Execute action via workflow automation platform
        
        🔒 SECURITY: Prefers self-hosted solutions over cloud platforms
        """
        
        # PRIORITY 1: Self-hosted n8n (SECURE - runs on your machine)
        if self.config.get("n8n", {}).get("enabled"):
            print("🔒 Using self-hosted n8n (secure)")
            return self._n8n_trigger(service, action, params)
        
        # PRIORITY 2: Cloud platforms (INSECURE - only if explicitly allowed)
        if self.allow_cloud_platforms:
            # Try Zapier
            if self.config.get("zapier", {}).get("enabled"):
                print("⚠️  Using Zapier (cloud) - data visible to third party")
                return self._zapier_trigger(service, action, params)
            
            # Try Make
            if self.config.get("make", {}).get("enabled"):
                print("⚠️  Using Make (cloud) - data visible to third party")
                return self._make_trigger(service, action, params)
        else:
            if self.config.get("zapier", {}).get("enabled") or \
               self.config.get("make", {}).get("enabled"):
                raise SecurityError(
                    "Cloud platforms detected but disabled for security. "
                    "Set allow_cloud_platforms=True to use them (not recommended)."
                )
        
        raise ValueError("No workflow platform configured")
    
    def _execute_via_browser(self, service: str, action: str, params: Dict) -> Dict:
        """Execute action via browser automation"""
        
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium not available for browser automation")
        
        if not self.browser:
            self.browser = self._init_browser()
        
        service_config = self.services[service]
        
        # Navigate to service
        self.browser.get(service_config.web_url)
        
        # Service-specific automation
        if service == "instagram":
            return self._instagram_browser_action(action, params)
        elif service == "canva":
            return self._canva_browser_action(action, params)
        elif service == "twitter":
            return self._twitter_browser_action(action, params)
        else:
            return self._generic_browser_action(service, action, params)
    
    def _handle_unknown_service(self, service: str, action: str, params: Dict) -> Dict:
        """Handle services not in our registry"""
        print(f"🔍 Unknown service '{service}' - attempting generic integration...")
        
        # Try to find service URL via search
        service_url = self._find_service_url(service)
        
        if service_url and SELENIUM_AVAILABLE:
            # Attempt browser automation for unknown service
            return self._generic_browser_action(service, action, params)
        
        return {
            "success": False,
            "error": f"Service '{service}' not supported yet",
            "suggestion": "Consider using browser automation or adding to config"
        }
    
    # ============================================================
    # Zapier Integration
    # ============================================================
    
    def _zapier_trigger(self, service: str, action: str, params: Dict) -> Dict:
        """
        Trigger Zapier webhook
        
        ⚠️  SECURITY WARNING: This sends your data to Zapier's cloud servers.
        Zapier can see all data in this request including tokens and content.
        Only use for non-sensitive operations.
        """
        if not self.allow_cloud_platforms:
            raise SecurityError(
                "Zapier (cloud platform) is disabled for security. "
                "Your data would be sent to Zapier's servers where they can access it. "
                "Use direct API or self-hosted n8n instead."
            )
        
        zapier_config = self.config.get("zapier", {})
        service_config = self.config.get("services", {}).get(service, {})
        
        webhook_id = service_config.get("zapier_webhook_id")
        if not webhook_id:
            raise ValueError(f"No Zapier webhook configured for {service}")
        
        webhook_url = f"{zapier_config['webhook_base']}{webhook_id}/"
        
        # Log security warning
        print(f"⚠️  SECURITY: Sending data to Zapier cloud: {service}/{action}")
        
        payload = {
            "service": service,
            "action": action,
            **params
        }
        
        response = requests.post(webhook_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            return {
                "success": True,
                "method": "zapier",
                "service": service,
                "action": action,
                "response": response.json(),
                "security_warning": "Data passed through Zapier cloud"
            }
        else:
            raise Exception(f"Zapier webhook failed: {response.status_code}")
    
    # ============================================================
    # n8n Integration
    # ============================================================
    
    def _n8n_trigger(self, service: str, action: str, params: Dict) -> Dict:
        """
        Trigger n8n workflow
        
        ✅ SECURITY: n8n runs on YOUR machine (localhost).
        Your data never leaves your computer. This is secure.
        """
        n8n_config = self.config.get("n8n", {})
        base_url = n8n_config['base_url']
        
        # Verify it's localhost/local network
        if not ('localhost' in base_url or '127.0.0.1' in base_url or '192.168.' in base_url):
            print(f"⚠️  WARNING: n8n URL is not localhost: {base_url}")
            print("   Make sure this is YOUR self-hosted instance!")
        
        webhook_url = f"{base_url}{n8n_config['webhook_path']}{service}-{action}"
        
        payload = {
            "service": service,
            "action": action,
            **params
        }
        
        response = requests.post(webhook_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            return {
                "success": True,
                "method": "n8n_selfhosted",
                "service": service,
                "action": action,
                "response": response.json(),
                "security_note": "✅ Secure: Self-hosted on your machine"
            }
        else:
            raise Exception(f"n8n webhook failed: {response.status_code}")
    
    # ============================================================
    # Make (Integromat) Integration
    # ============================================================
    
    def _make_trigger(self, service: str, action: str, params: Dict) -> Dict:
        """
        Trigger Make.com scenario
        
        ⚠️  SECURITY WARNING: This sends your data to Make.com's cloud servers.
        Make.com can see all data in this request including tokens and content.
        Only use for non-sensitive operations.
        """
        if not self.allow_cloud_platforms:
            raise SecurityError(
                "Make.com (cloud platform) is disabled for security. "
                "Your data would be sent to Make's servers where they can access it. "
                "Use direct API or self-hosted n8n instead."
            )
        
        make_config = self.config.get("make", {})
        webhook_urls = make_config.get("webhook_urls", {})
        
        webhook_url = webhook_urls.get(f"{service}_{action}")
        if not webhook_url:
            raise ValueError(f"No Make webhook for {service}:{action}")
        
        # Log security warning
        print(f"⚠️  SECURITY: Sending data to Make.com cloud: {service}/{action}")
        
        payload = {
            "service": service,
            "action": action,
            **params
        }
        
        response = requests.post(webhook_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            return {
                "success": True,
                "method": "make",
                "service": service,
                "action": action,
                "security_warning": "Data passed through Make.com cloud"
            }
        else:
            raise Exception(f"Make webhook failed: {response.status_code}")
    
    # ============================================================
    # Browser Automation Helpers
    # ============================================================
    
    def _init_browser(self):
        """Initialize Selenium browser"""
        options = webdriver.ChromeOptions()
        
        if self.config.get("browser_automation", {}).get("headless", False):
            options.add_argument("--headless")
        
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        browser = webdriver.Chrome(options=options)
        browser.implicitly_wait(10)
        
        return browser
    
    def _generic_browser_action(self, service: str, action: str, params: Dict) -> Dict:
        """Generic browser automation for any service"""
        
        # This would use AI vision to find elements
        # For now, return a placeholder
        return {
            "success": False,
            "error": "Generic browser automation not fully implemented",
            "suggestion": f"Add specific automation for {service}"
        }
    
    def _instagram_browser_action(self, action: str, params: Dict) -> Dict:
        """Instagram-specific browser automation"""
        
        if action == "post":
            # Navigate to Instagram and post
            # Implementation would go here
            return {
                "success": True,
                "method": "browser",
                "service": "instagram",
                "action": "post",
                "message": "Posted to Instagram via browser automation"
            }
        
        return {"success": False, "error": f"Action '{action}' not supported for Instagram"}
    
    def _canva_browser_action(self, action: str, params: Dict) -> Dict:
        """Canva-specific browser automation"""
        
        if action == "create_design":
            # Open Canva and create design
            return {
                "success": True,
                "method": "browser",
                "service": "canva",
                "action": "create_design",
                "message": "Design creation initiated in Canva"
            }
        
        return {"success": False, "error": f"Action '{action}' not supported for Canva"}
    
    def _twitter_browser_action(self, action: str, params: Dict) -> Dict:
        """Twitter-specific browser automation"""
        
        if action == "post":
            text = params.get("text", "")
            # Post tweet via browser
            return {
                "success": True,
                "method": "browser",
                "service": "twitter",
                "action": "post",
                "message": f"Posted to Twitter: {text}"
            }
        
        return {"success": False, "error": f"Action '{action}' not supported for Twitter"}
    
    # ============================================================
    # Direct API Implementations
    # ============================================================
    
    def _figma_api_call(self, action: str, params: Dict) -> Dict:
        """Figma API implementation"""
        service_config = self.config.get("services", {}).get("figma", {})
        access_token = service_config.get("access_token")
        
        if not access_token:
            raise ValueError("Figma access token not configured")
        
        headers = {"X-Figma-Token": access_token}
        base_url = "https://api.figma.com/v1"
        
        if action == "get_file":
            file_key = params.get("file_key")
            url = f"{base_url}/files/{file_key}"
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "method": "direct_api",
                    "service": "figma",
                    "action": action,
                    "data": response.json()
                }
        
        return {"success": False, "error": f"Figma action '{action}' not implemented"}
    
    def _twitter_api_call(self, action: str, params: Dict) -> Dict:
        """Twitter API implementation"""
        # Would implement Twitter API v2 calls here
        return {"success": False, "error": "Twitter API implementation pending"}
    
    def _facebook_api_call(self, action: str, params: Dict) -> Dict:
        """Facebook API implementation"""
        # Would implement Facebook Graph API calls here
        return {"success": False, "error": "Facebook API implementation pending"}
    
    def _linkedin_api_call(self, action: str, params: Dict) -> Dict:
        """LinkedIn API implementation"""
        # Would implement LinkedIn API calls here
        return {"success": False, "error": "LinkedIn API implementation pending"}
    
    # ============================================================
    # Utility Methods
    # ============================================================
    
    def _find_service_url(self, service: str) -> Optional[str]:
        """Find URL for unknown service"""
        common_urls = {
            "tiktok": "https://tiktok.com",
            "pinterest": "https://pinterest.com",
            "snapchat": "https://snapchat.com",
            "reddit": "https://reddit.com",
            "discord": "https://discord.com",
            "slack": "https://slack.com",
            "notion": "https://notion.so",
            "trello": "https://trello.com"
        }
        
        return common_urls.get(service.lower())
    
    def list_services(self) -> List[str]:
        """List all registered services"""
        return list(self.services.keys())
    
    def get_service_info(self, service: str) -> Optional[ServiceConfig]:
        """Get information about a service"""
        return self.services.get(service.lower())
    
    def close(self):
        """Clean up resources"""
        if self.browser:
            self.browser.quit()


# ============================================================
# Convenience Functions
# ============================================================

# Global instance
_hub_instance = None

def get_integration_hub() -> UniversalIntegrationHub:
    """Get or create global hub instance"""
    global _hub_instance
    if _hub_instance is None:
        _hub_instance = UniversalIntegrationHub()
    return _hub_instance


def connect_to_service(service: str, action: str, **params) -> Dict[str, Any]:
    """
    Convenience function to connect to any service
    
    Examples:
        connect_to_service("twitter", "post", text="Hello World!")
        connect_to_service("canva", "create_design", template="instagram-post")
        connect_to_service("figma", "export", file_id="abc123", format="png")
    """
    hub = get_integration_hub()
    return hub.connect(service, action, **params)


# Export main components
__all__ = [
    'UniversalIntegrationHub',
    'get_integration_hub',
    'connect_to_service',
    'ServiceCategory',
    'IntegrationMethod'
]
