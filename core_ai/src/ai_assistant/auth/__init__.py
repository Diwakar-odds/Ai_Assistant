"""
Authentication module for YourDaddy AI Assistant

Provides PIN-based authentication system for secure access.
"""

from .pin_auth import PINAuth, authenticate, setup_pin_cli, require_pin_auth

__all__ = ['PINAuth', 'authenticate', 'setup_pin_cli', 'require_pin_auth']