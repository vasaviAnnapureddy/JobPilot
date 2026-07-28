@echo off
:: Called by Task Scheduler every morning. Runs the full JobPilot daily cycle.
cd /d "E:\DataSciiecne\JobPilot"
python run_daily.py >> logs\daily.log 2>&1
