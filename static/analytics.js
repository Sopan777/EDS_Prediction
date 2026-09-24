// ==============================
// WSA Analytics Chart Script
// ==============================

document.addEventListener("DOMContentLoaded", function () {

    if (typeof categoryData === "undefined" || !categoryData) {
        console.warn("No analytics data available.");
        return;
    }

    const labels = Object.keys(categoryData);
    const values = Object.values(categoryData);

    const ctx = document.getElementById("categoryChart");

    if (!ctx) return;

    new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [{
                label: "Records per Category",
                data: values,
                backgroundColor: [
                    "#1E3A8A",
                    "#3B82F6",
                    "#2563EB",
                    "#60A5FA",
                    "#93C5FD",
                    "#1D4ED8",
                    "#1E40AF"
                ],
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0
                    }
                }
            }
        }
    });

});