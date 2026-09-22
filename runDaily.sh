#!/bin/bash

# Resolve project directory from this script's location (works for any user/path)
projectDir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$projectDir"

# Create logs directory if it doesn't exist
mkdir -p "$projectDir/logs"

# Create logFile variable
logFile="$projectDir/logs/cron.log"
stampFile="$projectDir/logs/last_daily_run.date"
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

if [ $exitCode -eq 0 ]; then
    python3 runPredictions.py >> "$logFile" 2>&1
    exitCode=$?
fi

if [ $exitCode -eq 0 ]; then
    python3 downloadWeaponIcons.py >> "$logFile" 2>&1
    exitCode=$?
fi

# Log the end of the run
if [ $exitCode -eq 0 ]; then
    echo "$today" > "$stampFile"
    echo "===== Run finished successfully: $(date '+%Y-%m-%d %H:%M:%S') =====" >> "$logFile"
else
    echo "===== Run FAILED (exit $exitCode): $(date '+%Y-%m-%d %H:%M:%S') =====" >> "$logFile"
fi
