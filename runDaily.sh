#!/bin/bash

# Change directory to the project directory
cd /home/jonat/MM2ValuesPlus

# Create logs directory if it doesn't exist
mkdir -p /home/jonat/MM2ValuesPlus/logs

# Create logFile variable
logFile="/home/jonat/MM2ValuesPlus/logs/cron.log"
stampFile="/home/jonat/MM2ValuesPlus/logs/last_daily_run.date"
today="$(date -u '+%Y-%m-%d')"

# Skip if a successful run already completed today (UTC, matches scrapedToday)
if [ -f "$stampFile" ] && [ "$(cat "$stampFile")" = "$today" ]; then
    echo "===== Run skipped (already ran successfully on $today UTC): $(date '+%Y-%m-%d %H:%M:%S') =====" >> "$logFile"
    exit 0
fi

# Activate venv
source .venv/bin/activate

# Log the start of the run
echo "===== Run started: $(date '+%Y-%m-%d %H:%M:%S') =====" >> "$logFile"

# Run the main.py file
python3 main.py >> "$logFile" 2>&1
exitCode=$?

if [ $exitCode -eq 0 ]; then
    python3 dedupeDatabase.py >> "$logFile" 2>&1
    exitCode=$?
fi

# Log the end of the run
if [ $exitCode -eq 0 ]; then
    echo "$today" > "$stampFile"
    echo "===== Run finished successfully: $(date '+%Y-%m-%d %H:%M:%S') =====" >> "$logFile"
else
    echo "===== Run FAILED (exit $exitCode): $(date '+%Y-%m-%d %H:%M:%S') =====" >> "$logFile"
fi
