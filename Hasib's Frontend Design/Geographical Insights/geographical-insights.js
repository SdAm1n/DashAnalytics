document.addEventListener('DOMContentLoaded', function() {

    if (localStorage.getItem('isLoggedIn') !== 'true') {
        window.location.href = '../auth/login.html';
        return;
    }

    const chartData = {
        monthly: {
            units: [65, 59, 80, 81, 56, 55, 40, 72, 88, 76, 90, 85],
            revenue: [6500, 5900, 8000, 8100, 5600, 5500, 4000, 7200, 8800, 7600, 9000, 8500],
            profit: [1950, 1770, 2400, 2430, 1680, 1650, 1200, 2160, 2640, 2280, 2700, 2550]
        },
        yearly: {
            units: [750, 890, 920, 1050, 1200],
            revenue: [75000, 89000, 92000, 105000, 120000],
            profit: [22500, 26700, 27600, 31500, 36000]
        }
    };

    let monthlySalesChart, yearlySalesChart;

    const initCharts = () => {
        // Monthly Sales Chart
        const monthlyCtx = document.getElementById('monthlySalesChart').getContext('2d');
        monthlySalesChart = new Chart(monthlyCtx, {
            type: 'line',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                datasets: [{
                    label: 'Units Sold',
                    data: chartData.monthly.units,
                    backgroundColor: 'rgba(67, 97, 238, 0.2)',
                    borderColor: 'rgba(67, 97, 238, 1)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true
                }]
            },
            options: getChartOptions('Monthly Sales', 'Months')
        });

        const yearlyCtx = document.getElementById('yearlySalesChart').getContext('2d');
        yearlySalesChart = new Chart(yearlyCtx, {
            type: 'line',
            data: {
                labels: ['2020', '2021', '2022', '2023', '2024'],
                datasets: [{
                    label: 'Units Sold',
                    data: chartData.yearly.units,
                    backgroundColor: 'rgba(67, 97, 238, 0.2)',
                    borderColor: 'rgba(67, 97, 238, 1)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true
                }]
            },
            options: getChartOptions('Yearly Sales', 'Years')
        });
    };

    const getChartOptions = (title, xAxisLabel) => {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${context.raw}`;
                        }
                    }
                },
                title: {
                    display: true,
                    text: title,
                    font: {
                        size: 16
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Value'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: xAxisLabel
                    }
                }
            }
        };
    };

    const setupChartControls = () => {
        // Month selector
        document.getElementById('monthSelector').addEventListener('change', function() {
            const selectedMonth = this.value;
            if (selectedMonth === 'all') {
                monthlySalesChart.data.datasets[0].data = chartData.monthly.units;
            } else {
                const monthIndex = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'].indexOf(selectedMonth);
                monthlySalesChart.data.datasets[0].data = Array(12).fill(0).map((_, i) => 
                    i === monthIndex ? chartData.monthly.units[i] : null
                );
            }
            monthlySalesChart.update();
        });

        document.getElementById('yearSelector').addEventListener('change', function() {
            const selectedYear = this.value;
            if (selectedYear === 'all') {
                yearlySalesChart.data.datasets[0].data = chartData.yearly.units;
            } else {
                const yearIndex = ['2020', '2021', '2022', '2023', '2024'].indexOf(selectedYear);
                yearlySalesChart.data.datasets[0].data = Array(5).fill(0).map((_, i) => 
                    i === yearIndex ? chartData.yearly.units[i] : null
                );
            }
            yearlySalesChart.update();
        });

        document.querySelectorAll('.sales-option').forEach(option => {
            option.addEventListener('click', function() {
                const metric = this.dataset.metric;
                const isMonthly = this.closest('.chart-card').querySelector('#monthlySalesChart');
                
                this.closest('.chart-options').querySelectorAll('.sales-option').forEach(opt => {
                    opt.classList.remove('active');
                });
                this.classList.add('active');
                
                if (isMonthly) {
                    monthlySalesChart.data.datasets[0].data = chartData.monthly[metric];
                    monthlySalesChart.data.datasets[0].label = this.textContent;
                    monthlySalesChart.update();
                } else {
                    yearlySalesChart.data.datasets[0].data = chartData.yearly[metric];
                    yearlySalesChart.data.datasets[0].label = this.textContent;
                    yearlySalesChart.update();
                }
            });
        });
    };

    const setupLogout = () => {
        document.querySelector('.logout').addEventListener('click', function(e) {
            e.preventDefault();
            localStorage.removeItem('isLoggedIn');
            window.location.href = '../auth/login.html';
        });
    };

    const setupMenuItems = () => {
        document.querySelectorAll('.menu-item').forEach(item => {
            item.addEventListener('click', function() {
                if (!this.classList.contains('logout') && !this.classList.contains('active')) {
                    document.querySelectorAll('.menu-item').forEach(i => {
                        i.classList.remove('active');
                    });
                    this.classList.add('active');
                }
            });
        });
    };

    const updateNotificationBadge = () => {
        const badge = document.querySelector('.notification-badge');
        if (badge) {
           // const notificationCount = ;
            badge.textContent = notificationCount;
            badge.style.display = notificationCount > 0 ? 'flex' : 'none';
        }
    };

    initCharts();
    setupChartControls();
    setupLogout();
    setupMenuItems();
    updateNotificationBadge();
});