@echo off
setlocal

REM Go to repo folder (where this .bat is)
cd /d "%~dp0"

REM --- Activate conda env (EDIT env name if needed) ---
call conda activate peakfinder

REM --- Run Streamlit ---
python -m streamlit run app.py --server.address 127.0.0.1 --browser.gatherUsageStats false

endlocal
