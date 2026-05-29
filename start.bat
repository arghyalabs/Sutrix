@echo off
echo Starting SUTRIX...
start cmd /k "cd frontend && npm install && npm run dev"
start cmd /k "pip install -r requirements.txt && python -m uvicorn backend.main:app --reload --port 8000"
echo Servers are starting in separate windows.
pause
