#!/bin/bash
# Setup script for Financial Advisor Backend

echo "Setting up Python virtual environment..."

# Try to create virtual environment
if python3 -m venv venv 2>/dev/null; then
    echo "✓ Virtual environment created successfully"
else
    echo "⚠ System Python has restrictions. Trying alternative method..."
    
    # Try using virtualenv if available
    if python3 -m pip install --user virtualenv 2>/dev/null; then
        python3 -m virtualenv venv
        echo "✓ Virtual environment created with virtualenv"
    else
        echo "❌ Could not create virtual environment."
        echo ""
        echo "Please install Python via one of these methods:"
        echo "  1. Install Homebrew: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        echo "  2. Then install Python: brew install python3"
        echo "  3. Or download from: https://www.python.org/downloads/"
        echo ""
        echo "Alternatively, you can install packages globally (not recommended):"
        echo "  python3 -m pip install --user -r requirements.txt"
        exit 1
    fi
fi

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✓ Virtual environment activated"
    
    # Upgrade pip
    pip install --upgrade pip --quiet
    
    # Install dependencies
    echo "Installing dependencies..."
    pip install -r requirements.txt
    
    echo ""
    echo "✅ Setup complete! To activate the virtual environment, run:"
    echo "  source venv/bin/activate"
    echo ""
    echo "Then start the server with:"
    echo "  python -m uvicorn app.main:app --reload --port 8000"
else
    echo "❌ Virtual environment activation script not found"
    exit 1
fi
