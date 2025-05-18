# DashAnalytics Project

This project provides analytics and predictions for sales data using Random Forest Regressor.

## Setup and Running Instructions

The project includes a helper script that simplifies the process of running the application and generating predictions.

### Prerequisites

- Python 3.8+
- Virtual environment (already set up in `/home/s010p/SWE_DB_Project_NEW/DashAnalytics/venv`)
- MongoDB server configured for the application

### Helper Script

We've added a helper script `run_dashanalytics.sh` to make it easier to run the project. The script can:

- Start the Django server on 127.0.0.1:8000
- Generate Random Forest predictions
- Check predictions in the database
- Check the prediction API endpoint

### Basic Commands

1. **Start Django Server**:

   ```
   ./run_dashanalytics.sh start
   ```

2. **Generate Random Forest Predictions**:

   ```
   ./run_dashanalytics.sh predictions
   ```

3. **Check Predictions in Database**:

   ```
   ./run_dashanalytics.sh check
   ```

4. **Check Prediction API**:

   ```
   ./run_dashanalytics.sh check-api
   ```

5. **Show Help**:

   ```
   ./run_dashanalytics.sh help
   ```

### Manual Steps (if helper script doesn't work)

If the helper script doesn't work for any reason, you can perform the steps manually:

1. **Activate the virtual environment**:

   ```
   source /home/s010p/SWE_DB_Project_NEW/DashAnalytics/venv/bin/activate
   ```

2. **Change to the Django project directory**:

   ```
   cd /home/s010p/SWE_DB_Project_NEW/DashAnalytics/dash_analytics
   ```

3. **Run the Django server**:

   ```
   python manage.py runserver 127.0.0.1:8000
   ```

4. **Generate predictions** (in a separate terminal):

   ```
   python run_predictions.py
   ```

5. **Check predictions in the database**:

   ```
   python check_predictions_db.py
   ```

6. **Check the API** (with server running):

   ```
   python check_prediction_api.py
   ```

## Implementation Details

The project now uses Random Forest Regressor for generating predictions instead of the previous time series algorithm. This provides:

- More accurate predictions based on multiple features
- Better top product predictions
- More detailed prediction information with confidence scores

The predictions are stored in both `high_review_score_db` and `low_review_score_db` databases and are accessible via the API at `/api/analytics/predictions/`.
