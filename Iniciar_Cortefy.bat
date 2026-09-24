@echo off
cd /d "%~dp0"
echo ========================================================
echo             ⚡ CORTEFY AI — SERVER INICIANDO
echo ========================================================
start "" http://127.0.0.1:8000
python server.py
