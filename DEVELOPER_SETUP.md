# Developer Setup Guide

Welcome to the development team! This document explains how to manually set up the project on your local machine if you've just cloned the repository (e.g., from GitHub).

## Prerequisites
- **Git**: To clone the repository.
- **Python 3.8+**: Make sure it's added to your PATH.
- **Node.js**: Required for the React frontend.

## Step 1: Clone the Repository
Open your terminal or command prompt and run:
```bash
git clone https://github.com/your-repo/Ai_Assistant.git
cd Ai_Assistant
```

## Step 2: Automated Setup (Recommended for Windows)
If you are on Windows, you can use the provided setup script which handles everything:
```powershell
.\install.ps1
```
This script will:
- Check for Python and Node.js
- Create a virtual environment (`.venv`)
- Install Python backend dependencies
- Install Node.js frontend dependencies
- Copy the environment variables template

## Step 3: Manual Setup (If you prefer doing it step-by-step)
If you want to manually set up the project or you are not on Windows, follow these steps:

### 1. Setup Python Virtual Environment (Backend)
First, create and activate a virtual environment in the project root:
**Windows:**
```powershell
python -m venv .venv
.\.venv\Scripts\activate
```
**Mac/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Python Dependencies
The requirements file is located in the `config/requirements` directory. Run:
```bash
pip install -r config/requirements/requirements.txt
```

### 3. Install Node.js Dependencies (Frontend)
Navigate to the frontend folder and install the NPM packages:
```bash
cd frontend/web-app
npm install
cd ../..
```

### 4. Environment Variables
Copy the example environment file to the root directory so you can configure your local settings:
**Windows (PowerShell):**
```powershell
Copy-Item config\.env.example .env
```
**Mac/Linux/CMD:**
```bash
cp config/.env.example .env
```
*Note: Make sure to open the `.env` file and add your required API keys (e.g., OpenAI API Key).*

## Step 4: Running the Application
To start both the backend and frontend servers, simply run:
**Windows:**
```cmd
.\start.bat
```
**Mac/Linux:**
```bash
./start.sh
```

Now you are all set up and ready to contribute to the project!
