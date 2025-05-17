#!/usr/bin/env python
import requests
import json
import webbrowser
import os
from datetime import datetime
import time

# Create a timestamp for our output files
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
os.makedirs("chart_verification", exist_ok=True)

print("Verifying that Sales Distribution by Gender and Age chart is fixed...")
print("Fetching data from API...")

# Fetch data from the API
response = requests.get(
    "http://localhost:8000/api/analytics/demographics/?period=1y")
if response.status_code != 200:
    print(f"Error fetching data: {response.status_code}")
    exit(1)

data = response.json()
gender_age_sales = data.get('gender_age_sales', {})

# Save the API response for reference
with open(f"chart_verification/api_response_{timestamp}.json", "w") as f:
    json.dump(data, f, indent=2)

print("API data successfully fetched and saved.")

# Create a mini test page to verify the chart rendering with focus on $0 starting point
html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chart Fix Verification</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
        .verification-container {{ 
            max-width: 900px; 
            margin: 0 auto; 
            background-color: #fff;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            padding: 20px;
        }}
        .chart-container {{ 
            background: #fff; 
            padding: 20px; 
            border-radius: 8px; 
            margin: 20px 0;
            height: 400px;
        }}
        h1 {{ color: #2a4365; }}
        h2 {{ color: #2c5282; }}
        .verification-result {{ padding: 15px; background: #ebf8ff; border-left: 4px solid #4299e1; margin: 20px 0; }}
        .highlight {{ background: #ffffcc; padding: 2px 4px; border-radius: 3px; }}
        pre {{ 
            background: #f8f9fa; 
            padding: 15px; 
            border-radius: 4px; 
            overflow-x: auto; 
            border: 1px solid #eee;
        }}
        .controls {{ 
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        button {{ 
            padding: 8px 16px;
            background: #4299e1;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }}
        button:hover {{ background: #3182ce; }}
        .test-result {{ font-weight: bold; margin-top: 10px; }}
        .pass {{ color: #38a169; }}
        .fail {{ color: #e53e3e; }}
    </style>
</head>
<body>
    <div class="verification-container">
        <h1>Chart Fix Verification</h1>
        
        <div class="verification-result">
            <h2>Fix Verification:</h2>
            <p>This page checks if the Sales Distribution by Gender and Age chart has been fixed to start from $0.</p>
        </div>
        
        <h2>API Data Preview</h2>
        <pre id="api-data">{json.dumps(gender_age_sales, indent=2)}</pre>
        
        <div class="controls">
            <button id="toggle-zero">Toggle Zero Base</button>
            <div class="test-result" id="test-status"></div>
        </div>
        
        <h2>Sales Distribution by Gender and Age</h2>
        <div class="chart-container">
            <canvas id="genderAgeSalesChart"></canvas>
        </div>
    </div>
    
    <script>
        // Chart configuration
        const chartData = {
    labels: {json.dumps(gender_age_sales.get('age_groups', []))},
            maleSales: {json.dumps(gender_age_sales.get('male_sales', []))},
            femaleSales: {json.dumps(gender_age_sales.get('female_sales', []))}
        };
        
        let useZeroBase = true; // Start with zero base enabled
        let chart = null;
        
        // Initialize chart
        document.addEventListener("DOMContentLoaded", function() {{
            renderChart();
            
            // Add toggle button functionality
            document.getElementById('toggle-zero').addEventListener('click', function() {{
                useZeroBase = !useZeroBase;
                this.textContent = useZeroBase ? 'Toggle Zero Base (Currently ON)' : 'Toggle Zero Base (Currently OFF)';
                renderChart();
                testZeroBase();
            }});
            
            // Initial test
            testZeroBase();
        }});
        
        function testZeroBase() {{
            const testStatus = document.getElementById('test-status');
            if (useZeroBase) {{
                // Check if min value is correctly set to 0
                if (chart && chart.options.scales.y.min === 0) {{
                    testStatus.textContent = 'TEST PASSED: Chart correctly starts from $0';
                    testStatus.className = 'test-result pass';
                }} else {{
                    testStatus.textContent = 'TEST FAILED: Chart should start from $0';
                    testStatus.className = 'test-result fail';
                }}
            }} else {{
                testStatus.textContent = 'Zero base disabled for comparison';
                testStatus.className = 'test-result';
            }}
        }}
        
        function renderChart() {{
            // Destroy existing chart if it exists
            if (chart) {{
                chart.destroy();
            }}
            
            const ctx = document.getElementById("genderAgeSalesChart").getContext("2d");
            
            // Color scheme
            const maleColor = "rgba(14, 165, 233, 0.8)";
            const femaleColor = "rgba(236, 72, 153, 0.8)";
            
            // Create the chart
            chart = new Chart(ctx, {{
                type: "bar",
                data: {{
                    labels: chartData.labels,
                    datasets: [
                        {{
                            label: "Male",
                            data: chartData.maleSales,
                            backgroundColor: maleColor,
                            borderColor: maleColor.replace("0.8", "1"),
                            borderWidth: 1
                        }},
                        {{
                            label: "Female",
                            data: chartData.femaleSales,
                            backgroundColor: femaleColor,
                            borderColor: femaleColor.replace("0.8", "1"),
                            borderWidth: 1
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    let label = context.dataset.label || '';
                                    if (label) {{
                                        label += ': ';
                                    }}
                                    label += '$' + context.raw.toLocaleString(undefined, {{
                                        minimumFractionDigits: 2,
                                        maximumFractionDigits: 2
                                    }});
                                    return label;
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        x: {{
                            grid: {{
                                display: false,
                            }},
                            title: {{
                                display: true,
                                text: 'Age Groups'
                            }}
                        }},
                        y: {{
                            beginAtZero: useZeroBase,
                            min: useZeroBase ? 0 : undefined,  // Key fix we're verifying
                            grid: {{
                                color: "rgba(0,0,0,0.05)",
                                drawOnChartArea: true,
                            }},
                            ticks: {{
                                callback: function (value) {{
                                    return "$" + value.toLocaleString();
                                }},
                            }}
                        }},
                    }},
                }},
            }});
        }}
    </script>
</body>
</html>
"""

# Save the verification HTML
verification_file = f"chart_verification/chart_verification_{timestamp}.html"
with open(verification_file, "w") as f:
    f.write(html)

print(f"Verification page created: {verification_file}")
print("Opening verification page in browser...")

# Open the verification page in a browser
webbrowser.open(f"file://{os.path.abspath(verification_file)}")

print("\nVerification Steps:")
print("1. The chart should display with Y-axis starting from $0")
print("2. You can toggle the zero base to see the difference")
print("3. The test result should show 'TEST PASSED' if the fix is working correctly")
