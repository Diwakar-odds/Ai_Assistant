#!/usr/bin/env python3
"""Proxy launcher to run the web backend from the repository root.

This allows running `python modern_web_backend.py` from the project root
without changing how the existing package modules import sibling packages.
It simply executes the package module as a script.
"""
import runpy
import runpy
import sys
import os

# Add src directory to path to allow importing ai_assistant
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == "__main__":
    # Run the module as if executed with `python -m ai_assistant.services.modern_web_backend`
    sys.exit(runpy.run_module('ai_assistant.services.modern_web_backend', run_name='__main__'))
