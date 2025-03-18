#!/bin/bash
# Test script for OpenAI API integration

# Set up environment
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Check if Python is installed
if ! command -v python &> /dev/null; then
    echo "Python is not installed. Please install Python 3.7+ and try again."
    exit 1
fi

# Make test script executable
chmod +x test_openai.py

# Run the test script
python test_openai.py

# Exit with the same code as the test script
exit $? 