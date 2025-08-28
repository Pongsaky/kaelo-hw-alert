#!/bin/bash

# Hardware Alert API Setup Script for Raspberry Pi
# Python 3.11 FastAPI project with GPIO control

set -e

echo "🚀 Setting up Hardware Alert API..."

# Check if Python 3.11 is available
if ! command -v python3.11 &> /dev/null; then
    echo "❌ Python 3.11 not found. Please install Python 3.11 first."
    echo "Run: sudo apt update && sudo apt install python3.11 python3.11-venv python3.11-dev"
    exit 1
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python3.11 -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📋 Installing requirements..."
pip install -r requirements.txt

echo "✅ Setup complete!"
echo ""
echo "To run the application:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Start the server: uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
echo ""
echo "API will be available at: http://0.0.0.0:8000"
echo "API docs at: http://0.0.0.0:8000/docs"
