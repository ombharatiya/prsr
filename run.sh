#!/bin/bash

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Ensure required directories exist
mkdir -p temp output static

# Run the application
echo "Starting PDF Invoice Parser..."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload 