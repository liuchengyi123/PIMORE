@echo off
cd /d "%~dp0"
if not exist node_modules (
  echo Installing dependencies...
  call npm install --no-fund --no-audit
)
echo Starting Harbor CS Desktop...
call npm start
