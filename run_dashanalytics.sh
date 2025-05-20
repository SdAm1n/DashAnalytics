#!/bin/bash
# Helper script to set up and run the DashAnalytics project

# Configuration
PORT=8000
HOST="127.0.0.1"
PROJECT_DIR="/home/s010p/SWE_DB_Project_NEW/DashAnalytics"
VENV_DIR="$PROJECT_DIR/venv"
DJANGO_PROJECT_DIR="$PROJECT_DIR/dash_analytics"

# Colors for better visibility
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to display section headers
section() {
    echo -e "\n${YELLOW}==== $1 ====${NC}"
}

# Function to run commands and check status
run_command() {
    echo -e "${GREEN}$ $1${NC}"
    eval $1
    status=$?
    if [ $status -ne 0 ]; then
        echo -e "${RED}Command failed with exit code $status${NC}"
        return $status
    fi
    return 0
}

# Display help
show_help() {
    echo "Usage: ./run_dashanalytics.sh [OPTION]"
    echo "Helper script for DashAnalytics project"
    echo ""
    echo "Options:"
    echo "  start         Activate venv and start Django server on $HOST:$PORT"
    echo "  predictions   Run the Random Forest predictions generation script"
    echo "  check         Check if predictions exist in the database"
    echo "  check-api     Check the prediction API endpoint (requires server running)"
    echo "  help          Show this help message"
    echo ""
}

# Main script
case "$1" in
    start)
        section "ACTIVATING VIRTUAL ENVIRONMENT"
        run_command "source $VENV_DIR/bin/activate"
        
        section "RUNNING DJANGO SERVER"
        echo "Starting Django server on http://$HOST:$PORT/"
        cd $DJANGO_PROJECT_DIR
        python manage.py runserver $HOST:$PORT
        ;;
        
    predictions)
        section "ACTIVATING VIRTUAL ENVIRONMENT"
        run_command "source $VENV_DIR/bin/activate"
        
        section "RUNNING RANDOM FOREST PREDICTIONS SCRIPT"
        cd $DJANGO_PROJECT_DIR
        run_command "python run_predictions.py"
        ;;
        
    check)
        section "ACTIVATING VIRTUAL ENVIRONMENT"
        run_command "source $VENV_DIR/bin/activate"
        
        section "CHECKING PREDICTIONS IN DATABASE"
        cd $DJANGO_PROJECT_DIR
        run_command "python check_predictions_db.py"
        ;;
        
    check-api)
        section "ACTIVATING VIRTUAL ENVIRONMENT"
        run_command "source $VENV_DIR/bin/activate"
        
        section "CHECKING PREDICTION API"
        cd $DJANGO_PROJECT_DIR
        run_command "python check_prediction_api.py"
        ;;
        
    help|*)
        show_help
        ;;
esac

# If we're exiting after activating venv, let the user know
if [ -n "$VIRTUAL_ENV" ]; then
    echo -e "\n${GREEN}Virtual environment is active. To deactivate, run: deactivate${NC}"
fi
