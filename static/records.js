// ==============================
// WSA Records Script
// ==============================

document.addEventListener("DOMContentLoaded", function () {

    // Confirm before delete
    const deleteButtons = document.querySelectorAll(".btn-danger");

    deleteButtons.forEach(button => {
        button.addEventListener("click", function (e) {

            const confirmed = confirm("Are you sure you want to delete this record?");

            if (!confirmed) {
                e.preventDefault();
            }
        });
    });

    // Table row hover highlight enhancement
    const tableRows = document.querySelectorAll("table tbody tr");

    tableRows.forEach(row => {
        row.addEventListener("mouseenter", function () {
            row.style.cursor = "pointer";
        });
    });

});