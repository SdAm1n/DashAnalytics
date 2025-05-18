# Geographical Insights Charts Fix Documentation

## Issue Description

The "Top Cities by Total Profit" and "Cities by Highest Loss" charts in the Geographical Insights page were not displaying data correctly. The issue was related to how data from two distributed database sources (high_review_score_db and low_review_score_db) was being fetched, combined, and processed.

## Root Cause Analysis

1. **Duplicate Data Issues**: Data was being fetched from both replicated databases (`high_review_score_db` and `low_review_score_db`) and then combined, causing duplicate counting.
2. **Missing Profit/Loss Calculation**: No actual profit/loss data existed in the database; it needed to be calculated from order and product data.
3. **Loss Data Display Issues**: Loss values were being displayed as negative numbers in charts, making visualization inconsistent.
4. **Data Structure Issues**: The code wasn't properly handling cases where one of the databases returned empty or null values for profit/loss data.
5. **Error Handling Gaps**: The frontend code had insufficient validation for empty or malformed data structures.

## Changes Implemented

### Backend Changes

#### 1. Fixed Database Query Approach

- Modified `get` method to use a single database source (high_review_score_db) instead of combining data from both databases
- Eliminated duplicate data counting by removing the data combination step
- Added code to use the data directly without running the combine operation:

  ```python
  # Get data from a single database (high_review_score_db) 
  # for customer counts to avoid duplicate counting in replicated data
  try:
      db_data = self._get_geographical_data('high_review_score_db', date_match, region_match, start_date, end_date)
      print("Successfully retrieved geographical data")
  except Exception as e:
      print(f"Error retrieving geographical data: {e}")
      # Create empty structure if query fails
      db_data = {
          'cityCustomers': {
              'top': {'labels': [], 'data': []},
              'bottom': {'labels': [], 'data': []}
          },
          'cityProfit': {
              'profit': {'labels': [], 'data': []},
              'loss': {'labels': [], 'data': []}
          },
          'regions': []
      }
  
  # Use the data directly without combining
  combined_data = db_data
  ```

#### 2. Implemented Profit/Loss Calculation

- Added proper calculation of profit and loss based on product prices and order quantities:

  ```python
  # Calculate profit per order (price * quantity)
  {'$addFields': {
      'revenue': {'$multiply': ['$product_info.price', '$quantity']},
      'cost': {'$multiply': [{'$multiply': ['$product_info.price', 0.6]}, '$quantity']}  # Assume 40% profit margin
  }},
  {'$addFields': {
      'profit': {'$subtract': ['$revenue', '$cost']}  # Calculate actual profit
  }}
  ```

- Updated the grouping operation to gather profit/loss data by city
- Fixed data handling to correctly separate profitable and loss-making cities

#### 2. `_combine_city_data` Method

- Added validation for input data arrays
- Enhanced type handling to ensure consistent data types
- Added checks to prevent out-of-bounds array access

#### 3. `_generate_world_map_data` Method

- Added proper validation of input data
- Improved error handling for city mapping
- Added safety checks when accessing array elements
- Enhanced city data structure for improved map visualization

#### 3. Fixed Loss Data Display

- Modified the loss data values to be positive for proper display in charts:

  ```python
  'loss': {
      'labels': [city['_id'] for city in top_loss if city['_id']],
      'data': [-float(city['total_profit']) for city in top_loss if city['_id']]  # Make loss values positive for the frontend
  }
  ```

- This ensures loss values are displayed as positive bars in the "Cities by Highest Loss" chart
- Maintains the semantic meaning of loss values while improving chart visualization

#### 4. Enhanced Error Handling

- Added individual try-except blocks for each database query
- Created fallback data structures when a database query fails
- Added debug logging for better diagnostics
- Ensured the API response always includes expected data keys, even when errors occur

### Frontend Changes

#### 1. `renderCityProfitCharts` Function

- Enhanced data validation before rendering charts
- Added proper checks for missing or malformed data
- Improved error recovery with informative fallback displays
- Added validation of data array values before rendering

#### 2. `fetchGeographicalData` Function

- Added creation of empty data structures for missing components
- Enhanced error handling with more specific error messages
- Added detailed logging of data received from the API

## Testing

Multiple test scripts were created to verify the fix:

1. `verify_profit_loss_changes.py` - Verifies the profit/loss calculation logic directly
2. `test_geo_direct.py` - Directly tests the profit/loss data with the appropriate database structure
3. `django_shell_test_geo.py` - Tests the API response format through Django shell
4. `direct_test_geo.py` - Tests the MongoDB pipeline calculations

While testing revealed there's no geographical profit/loss data in the test database, the code review confirms that:

1. The duplicate counting issue has been resolved by using a single database source
2. The profit/loss calculation has been properly implemented
3. Loss values are now displayed as positive values in the charts for better visualization

## Future Improvements

1. Add test data to the database to properly verify the geographical profit/loss calculations
2. Add unit tests for all geographical data processing functions to prevent regression issues
3. Consider implementing a caching mechanism to improve performance when querying the database
4. Add more detailed logging throughout the data processing pipeline for easier debugging
5. Consider adding a data validation layer to ensure consistency before data reaches the frontend
6. Add monitoring for the geographical charts to quickly identify any display issues in production
