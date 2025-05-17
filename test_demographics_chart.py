#!/usr/bin/env python
import requests
import os

# Create directory for output
os.makedirs("test_output", exist_ok=True)

# Get the demographics page HTML
response = requests.get(
    "http://localhost:8000/api/analytics/demographics/?period=1y")
data = response.json()

# Print the data
print("Gender-Age Sales Data:")
print(f"Age Groups: {data.get('gender_age_sales', {}).get('age_groups', [])}")
print(f"Male Sales: {data.get('gender_age_sales', {}).get('male_sales', [])}")
print(
    f"Female Sales: {data.get('gender_age_sales', {}).get('female_sales', [])}")

# Create HTML to visualize the chart with our improved code
html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Demographics Data Visualization</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .chart-container {
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 20px;
            margin-bottom: 30px;
            height: 500px;
        }
        h1, h2 {
            color: #333;
        }
        pre {
            background: #f4f4f4;
            border: 1px solid #ddd;
            border-left: 3px solid #3498db;
            color: #333;
            page-break-inside: avoid;
            font-family: monospace;
            font-size: 15px;
            line-height: 1.6;
            margin-bottom: 1.6em;
            max-width: 100%;
            overflow: auto;
            padding: 1em 1.5em;
            display: block;
            word-wrap: break-word;
        }
    </style>
</head>
<body>
    <h1>DashAnalytics - Demographics Data</h1>
    
    <div id="data-container">
        <h2>Gender and Age Sales Data</h2>
        <pre id="gender-age-data"></pre>
    </div>
    
    <h2>Sales Distribution by Gender and Age</h2>
    <div class="chart-container">
        <canvas id="genderAgeSalesChart"></canvas>
    </div>
    
    <script>
        // Fill the data from API
        const genderAgeData = JSON.parse(document.getElementById('gender-age-data').getAttribute('data-json'));
        document.getElementById('gender-age-data').textContent = JSON.stringify(genderAgeData, null, 2);
        
        // Chart rendering
        function renderGenderAgeSalesChart() {
            const ctx = document.getElementById("genderAgeSalesChart").getContext("2d");
            
            // Validate data
            const maleSales = genderAgeData.male_sales.map(val => typeof val === 'number' ? val : 0);
            const femaleSales = genderAgeData.female_sales.map(val => typeof val === 'number' ? val : 0);
            
            // Create consistent colors
            const maleColor = "rgba(14, 165, 233, 0.8)";  // Blue
            const femaleColor = "rgba(236, 72, 153, 0.8)"; // Pink
            
            // Check if we have any non-zero data
            const hasData = maleSales.some(val => val > 0) || femaleSales.some(val => val > 0);
            
            if (!hasData) {
                console.log("No sales data available for gender/age chart");
                
                // Create a message chart
                new Chart(ctx, {
                    type: 'bar',
                    data: {
                        datasets: []
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            title: {
                                display: true,
                                text: 'No sales data available for the selected period',
                                font: {
                                    size: 16
                                },
                                color: '#333'
                            }
                        }
                    }
                });
                return;
            }

            // Create the chart with proper zero baseline
            new Chart(ctx, {
                type: "bar",
                data: {
                    labels: genderAgeData.age_groups,
                    datasets: [
                        {
                            label: "Male",
                            data: maleSales,
                            backgroundColor: maleColor,
                            borderColor: maleColor.replace("0.8", "1"),
                            borderWidth: 1
                        },
                        {
                            label: "Female",
                            data: femaleSales,
                            backgroundColor: femaleColor,
                            borderColor: femaleColor.replace("0.8", "1"),
                            borderWidth: 1
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: {
                        duration: 1000,
                        easing: 'easeOutQuart'
                    },
                    layout: {
                        padding: {
                            left: 10,
                            right: 10,
                            top: 10,
                            bottom: 10
                        }
                    },
                    plugins: {
                        legend: {
                            position: "top",
                            labels: {
                                usePointStyle: true,
                                pointStyle: "circle",
                                padding: 20,
                                font: {
                                    size: 12
                                }
                            }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(255, 255, 255, 0.9)',
                            titleColor: '#000000',
                            bodyColor: '#1a202c',
                            borderColor: '#e2e8f0',
                            borderWidth: 1,
                            padding: 12,
                            displayColors: true,
                            callbacks: {
                                title: function(tooltipItems) {
                                    return tooltipItems[0].label;
                                },
                                label: function(context) {
                                    let label = context.dataset.label || '';
                                    if (label) {
                                        label += ': ';
                                    }
                                    label += '$' + context.raw.toLocaleString(undefined, {
                                        minimumFractionDigits: 2,
                                        maximumFractionDigits: 2
                                    });
                                    return label;
                                }
                            }
                        },
                        title: {
                            display: true,
                            text: 'Sales Distribution by Gender and Age',
                            color: '#333',
                            font: {
                                size: 16,
                                weight: 'bold'
                            },
                            padding: {
                                top: 10,
                                bottom: 20
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: {
                                display: false,
                            },
                            ticks: {
                                font: {
                                    weight: 'bold',
                                },
                                padding: 5
                            },
                            title: {
                                display: true,
                                text: 'Age Groups',
                                font: {
                                    size: 14,
                                    weight: 'bold'
                                },
                                padding: {
                                    top: 10
                                }
                            }
                        },
                        y: {
                            beginAtZero: true,
                            min: 0,  // Force minimum to be exactly 0
                            grid: {
                                drawOnChartArea: true,
                                drawTicks: true,
                                z: 1,
                                tickBorderDash: [],
                                tickBorderDashOffset: 0,
                            },
                            border: {
                                display: true,
                            },
                            ticks: {
                                // Ensure we show zero and format all values as currency
                                callback: function (value) {
                                    return "$" + value.toLocaleString(undefined, {
                                        minimumFractionDigits: 0,
                                        maximumFractionDigits: 0
                                    });
                                },
                                includeBounds: true,
                            },
                            // Not stacked - show side by side for better comparison
                            stacked: false,
                        },
                    },
                },
            });
        }

        // Initialize chart when page loads
        document.addEventListener("DOMContentLoaded", function() {
            renderGenderAgeSalesChart();
        });
    </script>
</body>
</html>
"""

# Insert the API data into the HTML
gender_age_data = data.get('gender_age_sales', {})
html = html.replace('<pre id="gender-age-data"></pre>',
                    f'<pre id="gender-age-data" data-json=\'{{"age_groups": {gender_age_data.get("age_groups", [])}, "male_sales": {gender_age_data.get("male_sales", [])}, "female_sales": {gender_age_data.get("female_sales", [])}}}\'>Loading...</pre>')

# Save the HTML to a file
with open("test_output/demographics_chart_test.html", "w") as f:
    f.write(html)

print("\nGenerated visualization saved to test_output/demographics_chart_test.html")
print("You can open this file in a browser to see the chart with proper zero starting scale")
