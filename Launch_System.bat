@echo off
echo ========================================
echo   AI TRADING SYSTEM LAUNCHER
echo ========================================

:: Launch the Dashboard and force it into the D: drive folder
echo Launching the Control Room...
start "Control Room (Streamlit)" /D "D:\Projects\Python\Trading" cmd /k ".venv\Scripts\activate && streamlit run app.py"

:: Wait 3 seconds to ensure the dashboard starts first
timeout /t 3 /nobreak > NUL

:: Launch the Autonomous Bot and force it into the D: drive folder
echo Launching the Autonomous Bot...
start "Autonomous Engine (Bot)" /D "D:\Projects\Python\Trading" cmd /k ".venv\Scripts\activate && python auto_trader.py"

echo System successfully launched.
exit