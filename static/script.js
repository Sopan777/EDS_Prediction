// ==============================
// WSA Global Script
// ==============================

document.addEventListener("DOMContentLoaded", function () {

    // Smooth fade-in for main content
    const content = document.querySelector(".center-card, .welcome-container");

    if (content) {
        content.style.opacity = "0";
        content.style.transform = "translateY(15px)";

        setTimeout(() => {
            content.style.transition = "all 0.5s ease";
            content.style.opacity = "1";
            content.style.transform = "translateY(0)";
        }, 100);
    }

    // Auto-hide alert messages after 4 seconds
    const alerts = document.querySelectorAll("div[style*='background-color: #FEE2E2']");

    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = "opacity 0.5s ease";
            alert.style.opacity = "0";
        }, 4000);
    });

});