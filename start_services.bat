@echo off
echo ===================================================
echo FinGuard AI - Financial Fraud Detection System
echo Starting All Services...
echo ===================================================

:: Start Backend
echo [1/2] Starting Backend (API + ML Engine + Explainability)...
start "FinGuard Backend" cmd /k "cd backend && venv\Scripts\activate && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

:: Wait for Backend to initialize (optional, but good for cleanliness)
timeout /t 5

:: Start Frontend
echo [2/2] Starting Frontend (Dashboard)...
start "FinGuard Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ===================================================
echo Services are starting in new windows.
echo Backend API: http://localhost:8000/docs
echo Frontend UI: http://localhost:5173
echo.
echo NOTE: If this is your first time running after a reset,
echo please REGISTER a new user at the login screen.
echo ===================================================
pause
