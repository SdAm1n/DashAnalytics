# Sales Trend API Documentation

This document provides technical details on the Sales Trend API implementation for the DashAnalytics project.

## API Endpoint

```
GET /api/analytics/sales_trend/
```

## Authentication

- The API requires authentication via Django's authentication system
- Authentication has been temporarily disabled for testing, but should be re-enabled in production

## Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| period | string | No | Time period for data aggregation. Options: 'daily', 'weekly', 'monthly', 'quarterly', 'yearly'. Default: 'monthly' |
| category | string | No | Product category to filter by. Use 'all' for all categories. Default: 'all' |
| date_from | string | No | Start date in YYYY-MM-DD format. Default: 6 months ago |
| date_to | string | No | End date in YYYY-MM-DD format. Default: current date |

## Response Format

The API returns a JSON array of data points, each containing:

```json
[
  {
    "period": "2024-May",
    "total_sales": 34715.3,
    "order_count": 49,
    "total_profit": 10414.59,
    "total_quantity": 148,
    "growth_rate": 10.5,
    
    // Only included in first record:
    "category_sales": {
      "Electronics": 155599.86,
      "Sports & Outdoors": 129479.25,
      "Fashion": 124919.51,
      "Books & Stationery": 111801.94,
      "Home & Living": 107797.06
    },
    "region_sales": {
      "Port Melissaborough": 3941.29,
      "Patriciaville": 3324.1,
      "Johnsonborough": 3045.09
      // ... more regions
    },
    "metadata": {
      "total_records": 838,
      "period_type": "monthly",
      "date_range": {
        "from": "2024-05-17",
        "to": "2025-05-17"
      },
      "filters_applied": {
        "category": "Electronics"
      }
    }
  },
  // ... more data points
]
```

## Period Formats

- **Daily**: YYYY-MM-DD (e.g., "2024-05-17")
- **Weekly**: YYYY-Wnn (e.g., "2024-W19")
- **Monthly**: YYYY-Month (e.g., "2024-May")
- **Quarterly**: YYYYQn (e.g., "2024Q2")
- **Yearly**: YYYY (e.g., "2024")

## Implementation Notes

1. **MongoDB Compatibility**:
   - The implementation uses MongoDB/mongoengine queries that are compatible with Django's ORM pattern
   - Uses `distinct()` instead of `values_list(..., flat=True)` for obtaining unique categories

2. **Performance Optimizations**:
   - Limits large query results to prevent memory issues
   - Uses efficient dictionary mapping for category lookups instead of multiple database joins
   - Returns sorted categories based on total sales

3. **Error Handling**:
   - Validates and handles improper date formats
   - Gracefully handles missing or malformed data
   - Provides informative error messages for debugging

4. **Category Filtering**:
   - Dynamically detects which field stores category information
   - Falls back to text search on category name or product name if direct match fails

## Testing

A test script (`test_sales_trend_api.py`) is provided that:

1. Tests all time period options
2. Tests category filtering
3. Creates visualizations of the returned data
4. Validates response structure and data integrity

Run the test script with:

```bash
python test_sales_trend_api.py --url http://localhost:8001/api
```

## Front-end Integration

The sales trend page expects data in this format to render four charts:

1. Sales Trend over Time (line chart)
2. Growth Rate (line chart)
3. Sales by Category (pie chart)
4. Sales by Region (pie chart)

## Future Improvements

1. Add pagination for very large datasets
2. Implement caching for frequently accessed data
3. Add additional filter options (e.g., by price range, by product)
4. Implement MongoDB aggregation pipeline for better performance on large datasets
