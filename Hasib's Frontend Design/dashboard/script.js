document.addEventListener('DOMContentLoaded', function() {
    if (localStorage.getItem('isLoggedIn') !== 'true') {
        window.location.href = '../auth/login.html';
        return;
    }

    
    let revenueChart; 

    
    const initCharts = () => {
       
        const revenueCtx = document.getElementById('revenueChart');
        if (revenueCtx) {
            revenueChart = new Chart(revenueCtx.getContext('2d'), {
                type: 'line',
                data: {
                    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                    datasets: [
                        {
                            label: 'Sales',
                            data: [120, 190, 170, 220, 300, 280],
                            borderColor: '#4361ee',
                            backgroundColor: 'rgba(67, 97, 238, 0.1)',
                            tension: 0.4,
                            borderWidth: 2,
                            fill: true
                        },
                        {
                            label: 'Profit',
                            data: [60, 80, 70, 90, 120, 110],
                            borderColor: '#4cc9f0',
                            backgroundColor: 'rgba(76, 201, 240, 0.1)',
                            tension: 0.4,
                            borderWidth: 2,
                            hidden: true,
                            fill: true
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top'
                        }
                    }
                }
            });
        }

        
        const salesCtx = document.getElementById('salesChart');
        if (salesCtx) {
            new Chart(salesCtx.getContext('2d'), {
                type: 'line',
                data: {
                    labels: ['2015', '2016', '2017', '2018', '2019'],
                    datasets: [{
                        label: 'Sales',
                        data: [100, 75, 80, 25, 0],
                        borderColor: '#4cc9f0',
                        backgroundColor: 'rgba(76, 201, 240, 0.1)',
                        tension: 0.4,
                        borderWidth: 2,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });
        }

        
        const customersCtx = document.getElementById('customersChart');
        if (customersCtx) {
            new Chart(customersCtx.getContext('2d'), {
                type: 'doughnut',
                data: {
                    labels: ['New', 'Returning'],
                    datasets: [{
                        data: [1420, 32229],
                        backgroundColor: ['#4361ee', '#4cc9f0'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '70%'
                }
            });
        }
    };

    
    const initToggleButtons = () => {
        document.querySelectorAll('.toggle-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                document.querySelectorAll('.toggle-btn').forEach(b => {
                    b.classList.remove('active');
                });
                this.classList.add('active');
                
                const type = this.dataset.type;
                revenueChart.data.datasets.forEach(dataset => {
                    dataset.hidden = (dataset.label.toLowerCase() !== type);
                });
                revenueChart.update();
            });
        });
    };

    
    const initLogout = () => {
        document.querySelector('.logout')?.addEventListener('click', function(e) {
            e.preventDefault();
            localStorage.removeItem('isLoggedIn');
            window.location.href = '../auth/login.html';
        });
    };

    initCharts();
    initToggleButtons();
    initLogout();
});