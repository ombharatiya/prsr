@echo off
echo Fixing dependencies for PDF Invoice Parser...

:: Activate virtual environment
call .venv\Scripts\activate.bat

:: Upgrade pip first
echo Upgrading pip...
python -m pip install --upgrade pip

:: Clean up existing packages
echo Cleaning up existing installations...
pip uninstall -y pandas numpy

:: Reinstall with specific versions
echo Installing compatible versions...
pip install -r requirements.txt

echo Dependencies fixed! Please try running the application again with 'run.bat'
pause 