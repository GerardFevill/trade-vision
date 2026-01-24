@echo off
echo Starting MT5 Monitor Backend...
cd /d %~dp0backend
pip install -r requirements.txt
python main.py
pause
