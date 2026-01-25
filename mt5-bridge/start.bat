@echo off
echo Starting MT5 Bridge Service...
echo This provides MT5 access to Docker containers on port 8001
cd /d %~dp0
pip install -r requirements.txt
python main.py
pause
