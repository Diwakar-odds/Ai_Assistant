"""
App Integration CLI for AI Assistant

Provides command-line interface for managing secure app integrations.
This tool helps users register, configure, and manage third-party applications
with proper security measures.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.app_integrator import secure_app_integrator
from core.app_security import secure_app_manager

def register_app_interactive():
    """Interactive app registration process."""
    print("\n=== AI Assistant App Registration ===")
    print("This tool will help you securely register an application with your AI assistant.")
    print("Sensitive information like API keys will be encrypted and stored securely.\n")
    
    # Basic information
    name = input("App name (lowercase, alphanumeric): ").strip().lower()
    if not name.replace('_', '').replace('-', '').isalnum():
        print("❌ Error: App name must contain only letters, numbers, hyphens, and underscores")
        return False
    
    display_name = input("Display name: ").strip()
    description = input("Description (optional): ").strip()
    
    # Category selection
    categories = ['productivity', 'media', 'development', 'communication', 'social', 'utility', 'entertainment', 'business']
    print(f"\nAvailable categories: {', '.join(categories)}")
    category = input("Category: ").strip().lower()
    if category not in categories:
        print(f"❌ Error: Invalid category. Choose from: {', '.join(categories)}")
        return False
    
    # Integration type
    integration_types = ['basic', 'api', 'oauth', 'webhook']
    print(f"\nIntegration types:")
    print("- basic: Simple executable launch")
    print("- api: API-based integration")
    print("- oauth: OAuth-based authentication")
    print("- webhook: Webhook-based integration")
    integration_type = input("Integration type: ").strip().lower()
    if integration_type not in integration_types:
        print(f"❌ Error: Invalid integration type. Choose from: {', '.join(integration_types)}")
        return False
    
    # Build app config
    app_config = {
        'name': name,
        'display_name': display_name,
        'category': category,
        'integration_type': integration_type
    }
    
    if description:
        app_config['description'] = description
    
    # Executable path for basic integrations
    if integration_type == 'basic':
        executable_path = input("Executable path: ").strip()
        if executable_path and Path(executable_path).exists():
            app_config['executable_path'] = executable_path
        else:
            print("⚠️  Warning: Executable path not found or empty")
    
    # API configuration
    if integration_type in ['api', 'oauth']:
        api_endpoint = input("API endpoint (optional): ").strip()
        if api_endpoint:
            app_config['api_endpoint'] = api_endpoint
        
        # API credentials
        print("\n--- API Credentials ---")
        print("Enter your API credentials. These will be encrypted and stored securely.")
        
        api_key = input("API Key (optional): ").strip()
        if api_key:
            app_config['api_key'] = api_key
        
        client_secret = input("Client Secret (optional): ").strip()
        if client_secret:
            app_config['client_secret'] = client_secret
        
        if integration_type == 'oauth':
            access_token = input("Access Token (optional): ").strip()
            if access_token:
                app_config['access_token'] = access_token
            
            refresh_token = input("Refresh Token (optional): ").strip()
            if refresh_token:
                app_config['refresh_token'] = refresh_token
    
    # Advanced options
    print("\n--- Advanced Options ---")
    auto_start = input("Auto-start with assistant? (y/n): ").strip().lower() == 'y'
    app_config['auto_start'] = auto_start
    
    startup_delay = input("Startup delay in seconds (0 for immediate): ").strip()
    try:
        app_config['startup_delay'] = int(startup_delay) if startup_delay else 0
    except ValueError:
        app_config['startup_delay'] = 0
    
    # Custom permissions
    print("\nDefault permissions will be assigned based on category.")
    custom_perms = input("Add custom permissions (comma-separated, optional): ").strip()
    if custom_perms:
        permissions = [p.strip() for p in custom_perms.split(',') if p.strip()]
        app_config['permissions'] = permissions
    
    # Summary
    print(f"\n=== Registration Summary ===")
    print(f"App: {display_name} ({name})")
    print(f"Category: {category}")
    print(f"Integration Type: {integration_type}")
    print(f"Auto-start: {auto_start}")
    if 'executable_path' in app_config:
        print(f"Executable: {app_config['executable_path']}")
    if 'api_endpoint' in app_config:
        print(f"API Endpoint: {app_config['api_endpoint']}")
    
    confirm = input("\nRegister this app? (y/n): ").strip().lower() == 'y'
    if not confirm:
        print("❌ Registration cancelled.")
        return False
    
    # Register the app
    success, message = secure_app_integrator.register_app(app_config)
    if success:
        print(f"✅ {message}")
        print("\n🔒 Security Notes:")
        print("- API keys and secrets have been encrypted")
        print("- Credentials are stored in config/secure/ (excluded from git)")
        print("- Only you can decrypt these credentials on this machine")
        return True
    else:
        print(f"❌ Registration failed: {message}")
        return False

def list_apps():
    """List all registered apps."""
    apps = secure_app_manager.list_registered_apps()
    
    if not apps:
        print("No apps registered.")
        return
    
    print(f"\n=== Registered Apps ({len(apps)}) ===")
    for app_name, app_config in apps.items():
        status_info = secure_app_integrator.get_app_status(app_name)
        status = "🟢 Running" if status_info['status'] == 'running' else "⚫ Stopped"
        enabled = "✅ Enabled" if app_config.get('enabled', True) else "❌ Disabled"
        
        print(f"\n{app_config['display_name']} ({app_name})")
        print(f"  Category: {app_config['category']}")
        print(f"  Type: {app_config['integration_type']}")
        print(f"  Status: {status}")
        print(f"  State: {enabled}")
        print(f"  Security Level: {app_config.get('security_level', 'unknown')}")

def launch_app(app_name: str):
    """Launch an app."""
    success, message = secure_app_integrator.launch_app(app_name)
    if success:
        print(f"✅ {message}")
    else:
        print(f"❌ {message}")

def stop_app(app_name: str):
    """Stop an app."""
    success, message = secure_app_integrator.stop_app(app_name)
    if success:
        print(f"✅ {message}")
    else:
        print(f"❌ {message}")

def remove_app(app_name: str):
    """Remove an app."""
    apps = secure_app_manager.list_registered_apps()
    if app_name.lower() not in apps:
        print(f"❌ App '{app_name}' is not registered.")
        return
    
    app_config = apps[app_name.lower()]
    print(f"\nRemoving app: {app_config['display_name']}")
    print("⚠️  This will delete all stored credentials and configuration.")
    
    confirm = input("Are you sure? (y/n): ").strip().lower() == 'y'
    if not confirm:
        print("❌ Removal cancelled.")
        return
    
    success = secure_app_manager.remove_app(app_name)
    if success:
        print(f"✅ App '{app_config['display_name']}' removed successfully.")
    else:
        print(f"❌ Failed to remove app '{app_name}'.")

def app_status(app_name: str):
    """Show detailed app status."""
    status_info = secure_app_integrator.get_app_status(app_name)
    
    if status_info['status'] == 'not_registered':
        print(f"❌ App '{app_name}' is not registered.")
        return
    
    print(f"\n=== {status_info['display_name']} Status ===")
    print(f"Name: {app_name}")
    print(f"Category: {status_info['category']}")
    print(f"Integration Type: {status_info['integration_type']}")
    print(f"Security Level: {status_info['security_level']}")
    print(f"Enabled: {status_info['enabled']}")
    print(f"Permissions: {', '.join(status_info['permissions'])}")
    
    if status_info['status'] == 'running':
        print(f"Status: 🟢 Running (PID: {status_info['pid']})")
        print(f"Started: {status_info['launched_at']}")
    else:
        print("Status: ⚫ Stopped")

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="AI Assistant App Integration Manager")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Register command
    register_parser = subparsers.add_parser('register', help='Register a new app')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all registered apps')
    
    # Launch command
    launch_parser = subparsers.add_parser('launch', help='Launch an app')
    launch_parser.add_argument('app_name', help='Name of the app to launch')
    
    # Stop command
    stop_parser = subparsers.add_parser('stop', help='Stop an app')
    stop_parser.add_argument('app_name', help='Name of the app to stop')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show app status')
    status_parser.add_argument('app_name', help='Name of the app')
    
    # Remove command
    remove_parser = subparsers.add_parser('remove', help='Remove an app')
    remove_parser.add_argument('app_name', help='Name of the app to remove')
    
    # Auto-start command
    autostart_parser = subparsers.add_parser('autostart', help='Start all auto-start apps')
    
    args = parser.parse_args()
    
    if args.command == 'register':
        register_app_interactive()
    elif args.command == 'list':
        list_apps()
    elif args.command == 'launch':
        launch_app(args.app_name)
    elif args.command == 'stop':
        stop_app(args.app_name)
    elif args.command == 'status':
        app_status(args.app_name)
    elif args.command == 'remove':
        remove_app(args.app_name)
    elif args.command == 'autostart':
        secure_app_integrator.auto_start_apps()
        print("✅ Auto-start process initiated.")
    else:
        parser.print_help()

if __name__ == '__main__':
    main()