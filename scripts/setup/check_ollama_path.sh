#!/bin/bash
# Check Ollama Storage Path - All Methods

echo "╔════════════════════════════════════════════════════════════╗"
echo "║          OLLAMA STORAGE PATH CHECK                        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Method 1: Check bashrc (permanent setting)
echo "📋 Method 1: Permanent Setting in ~/.bashrc"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if grep -q "OLLAMA_MODELS" ~/.bashrc; then
    echo "✅ Found in bashrc:"
    grep "OLLAMA_MODELS" ~/.bashrc
else
    echo "❌ Not set in bashrc (using default)"
fi
echo ""

# Method 2: Check current session variable
echo "🔧 Method 2: Current Session Variable"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -z "$OLLAMA_MODELS" ]; then
    echo "❌ Not set in current session"
    echo "💡 Will use default: /c/Users/hp/AppData/Local/Ollama/models"
else
    echo "✅ Set to: $OLLAMA_MODELS"
fi
echo ""

# Method 3: Check default location
echo "📁 Method 3: Check Both Locations"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

DEFAULT_PATH="/c/Users/hp/AppData/Local/Ollama/models"
CUSTOM_PATH=${OLLAMA_MODELS}

echo "Default location:"
if [ -d "$DEFAULT_PATH" ]; then
    echo "  ✅ Exists: $DEFAULT_PATH"
    echo "  Size: $(du -sh "$DEFAULT_PATH" 2>/dev/null || echo 'N/A')"
else
    echo "  ❌ Does not exist: $DEFAULT_PATH"
fi
echo ""

if [ -n "$CUSTOM_PATH" ]; then
    echo "Custom location (OLLAMA_MODELS):"
    if [ -d "$CUSTOM_PATH" ]; then
        echo "  ✅ Exists: $CUSTOM_PATH"
        echo "  Size: $(du -sh "$CUSTOM_PATH" 2>/dev/null || echo 'N/A')"
    else
        echo "  ❌ Does not exist: $CUSTOM_PATH"
        echo "  💡 Will be created on first download"
    fi
fi
echo ""

# Method 4: List existing models
echo "📦 Method 4: List Downloaded Models"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if command -v ollama &> /dev/null; then
    echo "Running: ollama list"
    echo ""
    ollama list 2>/dev/null || echo "⚠️  Ollama service not running. Start with: ollama serve"
else
    echo "❌ ollama command not found. Add to PATH first."
fi
echo ""

# Summary
echo "═════════════════════════════════════════════════════════════"
echo "📍 SUMMARY: Models will be saved to:"
if [ -n "$CUSTOM_PATH" ]; then
    echo "   🎯 $CUSTOM_PATH (Custom Path)"
else
    echo "   🎯 /c/Users/hp/AppData/Local/Ollama/models (Default)"
fi
echo "═════════════════════════════════════════════════════════════"
