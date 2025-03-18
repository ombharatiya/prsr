@echo off
REM Test script for OpenAI API integration

REM Set up environment
if exist .venv (
    echo Activating virtual environment...
    call .venv\Scripts\activate
)

REM Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Python is not installed. Please install Python 3.7+ and try again.
    exit /b 1
)

REM Run the test script
python test_openai.py

REM Exit with the same code as the test script
exit /b %ERRORLEVEL% 