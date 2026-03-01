#!/bin/bash

# --- Investment Agent Automation Script ---

# Get absolute path to the script directory (scripts/)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Project Root is one level up
PROJECT_ROOT="$(dirname "$DIR")"
cd "$PROJECT_ROOT"

# Set PYTHONPATH to Project Root so imports like 'from src.core...' work
export PYTHONPATH=$PROJECT_ROOT

# Helper function for email alerts (using send_notification.py in src/utils)
trigger_email_template() {
    TEMPLATE_NAME=$1
    echo "Sending email alert (Template: $TEMPLATE_NAME)..."
    python3 src/utils/send_notification.py --template "$TEMPLATE_NAME"
}

if [ -z "$1" ]; then
    echo "Usage: ./scripts/run_agent.sh [daily|rebalance|invest|interactive]"
    exit 1
fi

MODE=$1

if [ "$MODE" == "daily" ]; then
    echo "--- Running Daily Watchdog ---"
    python3 src/core/main.py --mode daily
elif [ "$MODE" == "rebalance" ]; then
    echo "--- Checking Bi-Weekly Rebalance ---"
    python3 src/core/main.py --mode rebalance --auto
elif [ "$MODE" == "invest" ]; then
    echo "--- Checking Monthly Investment ---"
    python3 src/core/main.py --mode invest --auto
elif [ "$MODE" == "interactive" ]; then
    echo "--- Running Interactive Investment Mode ---"
    
    SUBMODE=$2
    
    if [ -z "$SUBMODE" ]; then
        echo "Choose interactive mode:"
        echo "1) rebalance (Bi-Weekly)"
        echo "2) invest (Monthly)"
        read -p "Enter choice [1/2]: " CHOICE
        
        if [ "$CHOICE" == "1" ] || [ "$CHOICE" == "rebalance" ]; then
            SUBMODE="rebalance"
        elif [ "$CHOICE" == "2" ] || [ "$CHOICE" == "invest" ]; then
            SUBMODE="invest"
        else
            echo "Invalid choice. Exiting."
            exit 1
        fi
    fi

    if [ "$SUBMODE" == "rebalance" ]; then
       python3 src/core/main.py --mode rebalance
    elif [ "$SUBMODE" == "invest" ]; then
       python3 src/core/main.py --mode invest
    else
       echo "Invalid interactive submode. Use 'rebalance' or 'invest'."
       exit 1
    fi
else
    echo "Invalid mode. Please choose: daily, rebalance, invest, interactive"
    exit 1
fi
