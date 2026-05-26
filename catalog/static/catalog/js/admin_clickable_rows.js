(function () {
    const interactiveSelector = [
        "a",
        "button",
        "input",
        "select",
        "textarea",
        "label",
        "[role='button']",
    ].join(",");

    function findChangeLink(row) {
        return row.querySelector('a[href*="/change/"]');
    }

    function setupClickableRows() {
        document.querySelectorAll("body.change-list table tbody tr").forEach(function (row) {
            if (findChangeLink(row)) {
                row.style.cursor = "pointer";
            }
        });
    }

    document.addEventListener("click", function (event) {
        const row = event.target.closest("body.change-list table tbody tr");
        if (!row || event.target.closest(interactiveSelector)) {
            return;
        }

        const link = findChangeLink(row);
        if (!link) {
            return;
        }

        if (event.metaKey || event.ctrlKey) {
            window.open(link.href, "_blank", "noopener");
            return;
        }

        window.location.href = link.href;
    });

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", setupClickableRows);
    } else {
        setupClickableRows();
    }
})();
