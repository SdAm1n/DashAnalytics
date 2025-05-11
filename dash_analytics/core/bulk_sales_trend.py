"""
Enhanced Sales Trend Processing for Bulk Operations

This module provides enhanced functionality for processing sales trend data in bulk,
significantly improving performance for large dataset uploads.
"""

import logging
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from mongoengine import get_db

logger = logging.getLogger(__name__)

def _get_date_column(df):
    """Find the appropriate date column from common naming patterns"""
    date_columns = ['sale_date', 'order_date', 'date', 'transaction_date']
    for col in date_columns:
        if col in df.columns:
            return col
    raise ValueError("No valid date column found in DataFrame")

def _ensure_revenue_column(df):
    """Ensure revenue column exists, calculating if necessary"""
    if 'revenue' not in df.columns:
        if 'price' in df.columns and 'quantity' in df.columns:
            df['revenue'] = df['price'] * df['quantity']
        elif 'total_amount' in df.columns:
            df['revenue'] = df['total_amount']
        else:
            logger.warning("Could not determine revenue - defaulting to 0")
            df['revenue'] = 0
    return df

def _ensure_order_id_column(df):
    """Ensure order_id column exists for counting orders"""
    if 'id' not in df.columns:
        df['order_id'] = range(1, len(df) + 1)
        return 'order_id'
    return 'id'

def update_sales_trend_in_bulk(sales_df):
    """
    Update all sales trend records in bulk from a dataframe
    
    Args:
        sales_df: DataFrame containing sales data
    """
    try:
        # Prepare database connections
        low_db = get_db('low_review_score_db')
        high_db = get_db('high_review_score_db')
        
        # Create different trend period types
        periods = {
            'daily': _create_daily_trends(sales_df),
            'weekly': _create_weekly_trends(sales_df),
            'monthly': _create_monthly_trends(sales_df),
            'quarterly': _create_quarterly_trends(sales_df),
            'yearly': _create_yearly_trends(sales_df)
        }
        
        # Bulk upsert all period types
        for period_type, period_data in periods.items():
            if not period_data:
                continue
                
            bulk_operations = []
            
            for period_value, data in period_data.items():
                # Create or update sales trend record
                trend_id = f"TREND-{period_type}-{period_value}"
                
                # Prepare document for upsert
                bulk_operations.append({
                    'updateOne': {
                        'filter': {'id': trend_id},
                        'update': {
                            '$set': {
                                'id': trend_id,
                                'period_type': period_type,
                                'period_value': period_value,
                                'total_sales': data['total_sales'],
                                'total_orders': data['total_orders'],
                                'total_quantity': data['total_quantity'],
                                'average_order_value': data['average_order_value'],
                                'sales_growth_rate': data.get('sales_growth_rate', 0)
                            }
                        },
                        'upsert': True
                    }
                })
            
            # Execute bulk operations on both databases
            if bulk_operations:
                low_db.sales_trends.bulk_write(bulk_operations, ordered=False)
                high_db.sales_trends.bulk_write(bulk_operations, ordered=False)
                logger.info(f"Successfully bulk updated {len(bulk_operations)} {period_type} sales trends")
        
        return True
        
    except Exception as e:
        logger.error(f"Error updating sales trends in bulk: {str(e)}")
        raise

def _create_daily_trends(sales_df):
    """Create daily sales trend data from sales DataFrame"""
    try:
        # Determine date column
        date_column = _get_date_column(sales_df)
        
        # Convert date column to datetime if not already
        if not pd.api.types.is_datetime64_dtype(sales_df[date_column]):
            sales_df[date_column] = pd.to_datetime(sales_df[date_column])
        
        # Ensure revenue column exists
        sales_df = _ensure_revenue_column(sales_df)
        
        # Create date column for grouping
        sales_df['date'] = sales_df[date_column].dt.date.astype(str)
        
        # Group by date
        daily_data = sales_df.groupby('date').agg({
            'revenue': 'sum',
            'id': 'count',
            'quantity': 'sum'
        }).reset_index()
        
        # Calculate average order value
        daily_data['avg_order_value'] = daily_data['revenue'] / daily_data['id']
        
        # Convert to dictionary
        trends = {}
        for _, row in daily_data.iterrows():
            date_str = row['date']
            trends[date_str] = {
                'total_sales': float(row['revenue']),
                'total_orders': int(row['id']),
                'total_quantity': int(row['quantity']),
                'average_order_value': float(row['avg_order_value'])
            }
        
        # Calculate growth rates
        dates = sorted(trends.keys())
        for i in range(1, len(dates)):
            current_date = dates[i]
            prev_date = dates[i-1]
            
            current_sales = trends[current_date]['total_sales']
            prev_sales = trends[prev_date]['total_sales']
            
            growth_rate = ((current_sales - prev_sales) / prev_sales) * 100 if prev_sales > 0 else 0
            trends[current_date]['sales_growth_rate'] = float(growth_rate)
        
        return trends
        
    except Exception as e:
        logger.error(f"Error creating daily trends: {str(e)}")
        return {}

def _create_weekly_trends(sales_df):
    """Create weekly sales trend data from sales DataFrame"""
    try:
        # Determine date column
        date_column = _get_date_column(sales_df)
        
        # Convert date column to datetime if not already
        if not pd.api.types.is_datetime64_dtype(sales_df[date_column]):
            sales_df[date_column] = pd.to_datetime(sales_df[date_column])
        
        # Ensure revenue column exists
        sales_df = _ensure_revenue_column(sales_df)
        
        # Create week column for grouping (YYYY-WW format)
        sales_df['week'] = sales_df[date_column].dt.strftime('%Y-W%U')
        
        # Group by week
        weekly_data = sales_df.groupby('week').agg({
            'revenue': 'sum',
            'id': 'count',
            'quantity': 'sum'
        }).reset_index()
        
        # Calculate average order value
        weekly_data['avg_order_value'] = weekly_data['revenue'] / weekly_data['id']
        
        # Convert to dictionary
        trends = {}
        for _, row in weekly_data.iterrows():
            week_str = row['week']
            trends[week_str] = {
                'total_sales': float(row['revenue']),
                'total_orders': int(row['id']),
                'total_quantity': int(row['quantity']),
                'average_order_value': float(row['avg_order_value'])
            }
        
        # Calculate growth rates
        weeks = sorted(trends.keys())
        for i in range(1, len(weeks)):
            current_week = weeks[i]
            prev_week = weeks[i-1]
            
            current_sales = trends[current_week]['total_sales']
            prev_sales = trends[prev_week]['total_sales']
            
            growth_rate = ((current_sales - prev_sales) / prev_sales) * 100 if prev_sales > 0 else 0
            trends[current_week]['sales_growth_rate'] = float(growth_rate)
        
        return trends
        
    except Exception as e:
        logger.error(f"Error creating weekly trends: {str(e)}")
        return {}

def _create_monthly_trends(sales_df):
    """Create monthly sales trend data from sales DataFrame"""
    try:
        # Determine date column
        date_column = _get_date_column(sales_df)
        
        # Convert date column to datetime if not already
        if not pd.api.types.is_datetime64_dtype(sales_df[date_column]):
            sales_df[date_column] = pd.to_datetime(sales_df[date_column])
        
        # Ensure revenue column exists
        sales_df = _ensure_revenue_column(sales_df)
        
        # Create month column for grouping (YYYY-MM format)
        sales_df['month'] = sales_df[date_column].dt.strftime('%Y-%m')
        
        # Group by month
        monthly_data = sales_df.groupby('month').agg({
            'revenue': 'sum',
            'id': 'count',
            'quantity': 'sum'
        }).reset_index()
        
        # Calculate average order value
        monthly_data['avg_order_value'] = monthly_data['revenue'] / monthly_data['id']
        
        # Convert to dictionary
        trends = {}
        for _, row in monthly_data.iterrows():
            month_str = row['month']
            trends[month_str] = {
                'total_sales': float(row['revenue']),
                'total_orders': int(row['id']),
                'total_quantity': int(row['quantity']),
                'average_order_value': float(row['avg_order_value'])
            }
        
        # Calculate growth rates
        months = sorted(trends.keys())
        for i in range(1, len(months)):
            current_month = months[i]
            prev_month = months[i-1]
            
            current_sales = trends[current_month]['total_sales']
            prev_sales = trends[prev_month]['total_sales']
            
            growth_rate = ((current_sales - prev_sales) / prev_sales) * 100 if prev_sales > 0 else 0
            trends[current_month]['sales_growth_rate'] = float(growth_rate)
        
        return trends
        
    except Exception as e:
        logger.error(f"Error creating monthly trends: {str(e)}")
        return {}

def _create_quarterly_trends(sales_df):
    """Create quarterly sales trend data from sales DataFrame"""
    try:
        # Determine date column
        date_column = _get_date_column(sales_df)
        
        # Convert date column to datetime if not already
        if not pd.api.types.is_datetime64_dtype(sales_df[date_column]):
            sales_df[date_column] = pd.to_datetime(sales_df[date_column])
        
        # Ensure revenue column exists
        sales_df = _ensure_revenue_column(sales_df)
        
        # Create quarter column for grouping (YYYY-Q# format)
        sales_df['quarter'] = sales_df[date_column].dt.to_period('Q').astype(str)
        
        # Group by quarter
        quarterly_data = sales_df.groupby('quarter').agg({
            'revenue': 'sum',
            'id': 'count',
            'quantity': 'sum'
        }).reset_index()
        
        # Calculate average order value
        quarterly_data['avg_order_value'] = quarterly_data['revenue'] / quarterly_data['id']
        
        # Convert to dictionary
        trends = {}
        for _, row in quarterly_data.iterrows():
            quarter_str = row['quarter']
            trends[quarter_str] = {
                'total_sales': float(row['revenue']),
                'total_orders': int(row['id']),
                'total_quantity': int(row['quantity']),
                'average_order_value': float(row['avg_order_value'])
            }
        
        # Calculate growth rates
        quarters = sorted(trends.keys())
        for i in range(1, len(quarters)):
            current_quarter = quarters[i]
            prev_quarter = quarters[i-1]
            
            current_sales = trends[current_quarter]['total_sales']
            prev_sales = trends[prev_quarter]['total_sales']
            
            growth_rate = ((current_sales - prev_sales) / prev_sales) * 100 if prev_sales > 0 else 0
            trends[current_quarter]['sales_growth_rate'] = float(growth_rate)
        
        return trends
        
    except Exception as e:
        logger.error(f"Error creating quarterly trends: {str(e)}")
        return {}

def _create_yearly_trends(sales_df):
    """Create yearly sales trend data from sales DataFrame"""
    try:
        # Determine date column
        date_column = _get_date_column(sales_df)
        
        # Convert date column to datetime if not already
        if not pd.api.types.is_datetime64_dtype(sales_df[date_column]):
            sales_df[date_column] = pd.to_datetime(sales_df[date_column])
        
        # Ensure revenue column exists
        sales_df = _ensure_revenue_column(sales_df)
        
        # Create year column for grouping
        sales_df['year'] = sales_df[date_column].dt.year.astype(str)
        
        # Group by year
        yearly_data = sales_df.groupby('year').agg({
            'revenue': 'sum',
            'id': 'count',
            'quantity': 'sum'
        }).reset_index()
        
        # Calculate average order value
        yearly_data['avg_order_value'] = yearly_data['revenue'] / yearly_data['id']
        
        # Convert to dictionary
        trends = {}
        for _, row in yearly_data.iterrows():
            year_str = row['year']
            trends[year_str] = {
                'total_sales': float(row['revenue']),
                'total_orders': int(row['id']),
                'total_quantity': int(row['quantity']),
                'average_order_value': float(row['avg_order_value'])
            }
        
        # Calculate growth rates
        years = sorted(trends.keys())
        for i in range(1, len(years)):
            current_year = years[i]
            prev_year = years[i-1]
            
            current_sales = trends[current_year]['total_sales']
            prev_sales = trends[prev_year]['total_sales']
            
            growth_rate = ((current_sales - prev_sales) / prev_sales) * 100 if prev_sales > 0 else 0
            trends[current_year]['sales_growth_rate'] = float(growth_rate)
        
        return trends
        
    except Exception as e:
        logger.error(f"Error creating yearly trends: {str(e)}")
        return {}
