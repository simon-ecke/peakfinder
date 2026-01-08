@echo off
setlocal

REM Go to repo folder (where this .bat is)
cd /d "%~dp0"

REM --- Activate conda env (EDIT env name if needed) ---
REM Option 1: If conda is in your PATH, use this:
call conda.bat activate peakfinder

REM Option 2: Or uncomment and edit this line with your conda path:
REM call "%USERPROFILE%\Anaconda3\Scripts\activate.bat" peakfinder
REM call "%USERPROFILE%\Miniconda3\Scripts\activate.bat" peakfinder

REM --- Run Streamlit ---
python -m streamlit run app.py --server.address 127.0.0.1 --browser.gatherUsageStats false

endlocal
