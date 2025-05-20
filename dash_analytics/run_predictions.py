#!/usr/bin/env python
"""
Script to run the Random Forest prediction generation command.
This script replaces the old time series predictions with Random Forest Regressor predictions.
"""
from django.core.management import call_command
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dash_analytics.settings')
django.setup()


def main():
    """Run the command to generate predictions using Random Forest"""
    print("Starting Random Forest prediction generation...")

    # Delete existing predictions first
    print("Running prediction generation command...")
    call_command('generate_predictions_with_random_forest')

    print("Prediction generation complete!")


if __name__ == "__main__":
    main()
