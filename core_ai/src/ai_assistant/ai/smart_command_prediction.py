"""
Smart Command Prediction (Alias / Wrapper for CommandPredictor)
Forwards to command_predictor.py for unified sequential command forecasting.
"""

from ai_assistant.ai.command_predictor import CommandPredictor

SmartCommandPredictor = CommandPredictor

__all__ = ['SmartCommandPredictor', 'CommandPredictor']
