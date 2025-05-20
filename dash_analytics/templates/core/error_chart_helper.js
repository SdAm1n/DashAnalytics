// Function to display error message in charts when data cannot be loaded
function renderErrorInCharts(errorMessage) {
    const chartCanvases = [
        "bestSellingChart",
        "categoryPerformanceChart",
        "volumeChart",
        "avgRevenueChart",
    ];

    chartCanvases.forEach((canvasId) => {
        const ctx = document.getElementById(canvasId).getContext("2d");
        // Clear any existing chart
        if (window[canvasId]) {
            window[canvasId].destroy();
        }

        // Clear canvas
        ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);

        // Display error message
        ctx.font = "16px Arial";
        ctx.fillStyle = isDarkMode ? "#cbd5e0" : "#4a5568";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(errorMessage, ctx.canvas.width / 2, ctx.canvas.height / 2);
    });
}
