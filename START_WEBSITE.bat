@echo off
title JobPilot Website
cd /d "E:\DataSciiecne\JobPilot\web"

echo ============================================================
echo   Starting your JobPilot website...
echo ============================================================
echo.
echo   WAIT until you see the line:  "Starting development server"
echo.
echo   THEN open Google Chrome and go to this address:
echo.
echo        http://localhost:8010
echo.
echo   Keep THIS black window OPEN while you use the website.
echo   To stop the website later, just close this window.
echo ============================================================
echo.

python manage.py runserver 8010

echo.
echo (If you see a red error above, take a screenshot and send it.)
pause
