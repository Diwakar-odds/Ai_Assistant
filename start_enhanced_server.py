#!/usr/bin/env python3
"""
Enhanced Server Launcher - Start the complete YourDaddy Assistant with all features
"""

import os
import sys
import time

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    print("🚀 Starting YourDaddy Assistant Enhanced Server...")
    print("=" * 60)
    
    try:
        # Import after path setup
        from modern_web_backend import app
        
        print("✅ All modules loaded successfully")
        print("🌐 Starting Flask server on http://localhost:5001")
        print("📱 Web UI available at: http://localhost:5001")
        print("🔧 Enhanced Chat API: http://localhost:5001/chat")
        print("📋 All features enabled and integrated!")
        print("=" * 60)
        
        # Start the server
        app.run(
            host='0.0.0.0',
            port=5001,
            debug=True,
            use_reloader=False,  # Prevent double loading
            threaded=True
        )
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()