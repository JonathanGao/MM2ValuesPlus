#!/bin/bash

# Change directory to the project directory
cd /home/jonat/MM2ValuesPlus

# Activate venv
source .venv/bin/activate

# Create logs directory if it doesn't exist
mkdir -p /home/jonat/MM2ValuesPlus/logs

# Create logFile variable
logFile="/home/jonat/MM2ValuesPlus/logs/cron.log"

# Log the start of the run
echo "===== Run started: $(date '+%Y-%m-%d %H:%M:%S') =====" >> "$logFile"

# Run the main.py file

python3 main.py >> "$logFile" 2>&1
exitCode=$?

# Log the end of the run
if [ $exitCode -eq 0 ]; then
    echo "===== Run finished successfully: $(date '+%Y-%m-%d %H:%M:%S') =====" >> "$logFile"
else
    echo "===== Run FAILED (exit $exitCode): $(date '+%Y-%m-%d %H:%M:%S') =====" >> "$logFile"
fi
