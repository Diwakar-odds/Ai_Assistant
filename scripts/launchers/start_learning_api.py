"""
Start Learning API Server
Simple wrapper to start the FastAPI learning systems server
"""

import sys
import os
# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from fastapi import FastAPI
from ai_assistant.services.learning_api import router
import uvicorn

app = FastAPI(title="Learning Systems API", version="1.0.0")
app.include_router(router)

if __name__ == "__main__":
    print("🚀 Starting Learning Systems API Server...")
    print("📍 URL: http://127.0.0.1:8000")
    print("📚 Docs: http://127.0.0.1:8000/docs")
    print("=" * 60)
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
