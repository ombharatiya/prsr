@echo off
echo Starting PDF Invoice Parser...

:: Check if virtual environment exists and activate it
if exist .venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
)

:: Ensure required directories exist
if not exist temp mkdir temp
if not exist output mkdir output
if not exist static mkdir static

:: Run the application
echo Starting server...
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

pause 