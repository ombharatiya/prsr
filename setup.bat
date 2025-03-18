@echo off
echo Setting up PDF Invoice Parser...

:: Create virtual environment if it doesn't exist
if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
    echo Virtual environment created at .venv\
)

:: Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

:: Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

:: Create necessary directories
echo Creating necessary directories...
if not exist temp mkdir temp
if not exist output mkdir output
if not exist static mkdir static

echo Setup completed successfully!
echo Run 'run.bat' to start the application

pause 