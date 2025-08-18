@echo off
:: Activate the virtual environment
call "%~dp0_venv\Scripts\activate.bat"

:: Run the app.py using the Python from the virtual environment
python "%~dp0add_account.py"

pause
