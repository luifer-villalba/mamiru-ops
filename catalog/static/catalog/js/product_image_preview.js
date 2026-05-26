(function () {
    const previewUrls = new WeakMap();

    function previewHtml(src, alt) {
        return `<img src="${src}" alt="${alt}" style="width: 72px; height: 72px; object-fit: cover; border-radius: 6px;" />`;
    }

    function updatePreview(input) {
        const row = input.closest("tr, .dynamic-images");
        if (!row) {
            return;
        }

        const previewCell = row.querySelector(".field-preview");
        if (!previewCell) {
            return;
        }

        const previousUrl = previewUrls.get(input);
        if (previousUrl) {
            URL.revokeObjectURL(previousUrl);
        }

        const file = input.files && input.files[0];
        if (!file) {
            return;
        }

        const url = URL.createObjectURL(file);
        previewUrls.set(input, url);
        previewCell.innerHTML = previewHtml(url, file.name);
    }

    function init() {
        document.addEventListener("change", function (event) {
            const input = event.target;
            if (!input.matches('input[type="file"][name$="-image"]')) {
                return;
            }

            updatePreview(input);
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
