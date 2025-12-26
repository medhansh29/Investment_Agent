#!/bin/bash

# Absolute path to the agent directory
AGENT_DIR="/Users/medhansh29/Investment Agent"
LOG_DIR="/tmp"

# Define the cron jobs
# 1. Daily Watchdog: 4:30 PM (16:30) every weekday (Mon-Fri)
JOB1="30 16 * * 1-5 '$AGENT_DIR/run_agent.sh' daily >> '$LOG_DIR/inv_agent_daily.log' 2>&1"

# 2. Bi-Weekly Rebalance: 4:35 PM every Friday, checking if it's an even week number (simple approximation or shell logic)
# Actually, the shell logic in the previous walkthrough was: [ $(( $(date +\%s) / 86400 \% 14 )) -eq 0 ]
# Let's simplify and just run it every Friday, but the script itself can check? 
# OR, use the shell logic in cron.
# Note: Escape % as \% in crontab.
JOB2="35 16 * * 5 [ \$(( \$(date +\%s) / 86400 \% 14 )) -eq 0 ] && '$AGENT_DIR/run_agent.sh' rebalance >> '$LOG_DIR/inv_agent_rebal.log' 2>&1"

# 3. Monthly Invest: 9:30 AM on the 1st of every month
JOB3="30 9 1 * * '$AGENT_DIR/run_agent.sh' invest >> '$LOG_DIR/inv_agent_invest.log' 2>&1"

# Combine into a temporary file
echo "$JOB1" > cron_dump.txt
echo "$JOB2" >> cron_dump.txt
echo "$JOB3" >> cron_dump.txt

# Install new crontab
crontab cron_dump.txt

# Clean up
rm cron_dump.txt

echo "Crontab installed successfully:"
crontab -l
