#!/usr/bin/env python
import webbrowser
import time
import subprocess
import os

# This script opens the actual demographics page in a browser to verify the chart

print("Opening demographics page to verify chart fix...")

# Check if the Django server is running
try:
    response = subprocess.check_output(
        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost:8000"])
    if response.decode('utf-8') != "200":
        print("Django server does not appear to be running. Starting server...")
        # Start the Django server
        subprocess.Popen(["python", "manage.py", "runserver"],
                         cwd="/home/s010p/SWE_DB_Project/DashAnalytics")
        print("Waiting for server to start...")
        time.sleep(5)  # Give it time to start
except Exception as e:
    print(f"Error checking server status: {e}")
    print("Starting Django server...")
    subprocess.Popen(["python", "manage.py", "runserver"],
                     cwd="/home/s010p/SWE_DB_Project/DashAnalytics")
    print("Waiting for server to start...")
    time.sleep(5)  # Give it time to start

# Now open the demographics page
print("Opening demographics page in browser...")
webbrowser.open("http://localhost:8000/demographics/")

print("\nVerification Steps:")
print("1. Navigate to the demographics page")
print("2. Verify that the 'Sales Distribution by Gender and Age' chart starts from $0")
print("3. Check that the chart displays properly with correct formatting and tooltips")
print("4. Try different time periods to ensure data is loaded correctly")
print("\nNote: If the page doesn't load, ensure the Django server is running with:")
print("cd /home/s010p/SWE_DB_Project/DashAnalytics && python manage.py runserver")
