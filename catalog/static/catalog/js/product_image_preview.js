(function () {
    const previewUrls = new WeakMap();

    function styleImage(image, size) {
        image.style.width = `${size}px`;
        image.style.height = `${size}px`;
        image.style.objectFit = "cover";
        image.style.borderRadius = size > 100 ? "8px" : "6px";
    }

    function buildPreviewImage(src, alt, size) {
        const image = document.createElement("img");
        image.src = src;
        image.alt = alt;
        styleImage(image, size);
        return image;
    }

    function buildMainPlaceholder() {
        const placeholder = document.createElement("div");
        placeholder.dataset.productFormImagePlaceholder = "";
        placeholder.textContent = "Sin imagen";
        placeholder.style.alignItems = "center";
        placeholder.style.background = "#f3f4f6";
        placeholder.style.border = "1px dashed #d1d5db";
        placeholder.style.borderRadius = "8px";
        placeholder.style.color = "#6b7280";
        placeholder.style.display = "flex";
        placeholder.style.fontSize = "13px";
        placeholder.style.fontWeight = "600";
        placeholder.style.height = "160px";
        placeholder.style.justifyContent = "center";
        placeholder.style.textAlign = "center";
        placeholder.style.width = "160px";
        return placeholder;
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
        previewCell.replaceChildren(buildPreviewImage(url, file.name, 72));
    }

    function rowImageUrl(row) {
        const input = row.querySelector('input[type="file"][name$="-image"]');
        const file = input && input.files && input.files[0];
        if (file) {
            if (!previewUrls.get(input)) {
                previewUrls.set(input, URL.createObjectURL(file));
            }

            return {
                alt: file.name,
                src: previewUrls.get(input),
            };
        }

        const image = row.querySelector(".field-preview img");
        if (!image) {
            return null;
        }

        return {
            alt: image.alt || "Imagen del producto",
            src: image.currentSrc || image.src,
        };
    }

    function imageRows() {
        const inputs = document.querySelectorAll('input[type="file"][name$="-image"]');
        return Array.from(inputs)
            .map((input) => input.closest("tr, .dynamic-images"))
            .filter(Boolean);
    }

    function isDeleted(row) {
        const deleteInput = row.querySelector('input[type="checkbox"][name$="-DELETE"]');
        return Boolean(deleteInput && deleteInput.checked);
    }

    function isMain(row) {
        const mainInput = row.querySelector('input[type="checkbox"][name$="-is_main"]');
        return Boolean(mainInput && mainInput.checked);
    }

    function selectedMainImage() {
        const rows = imageRows().filter((row) => !isDeleted(row));
        const mainRow = rows.find((row) => isMain(row) && rowImageUrl(row));
        if (mainRow) {
            return rowImageUrl(mainRow);
        }

        const firstRow = rows.find((row) => rowImageUrl(row));
        return firstRow ? rowImageUrl(firstRow) : null;
    }

    function updateMainPreview() {
        const preview = document.querySelector("[data-product-form-image-preview]");
        if (!preview) {
            return;
        }

        const image = selectedMainImage();
        if (!image) {
            preview.replaceChildren(buildMainPlaceholder());
            return;
        }

        const previewImage = buildPreviewImage(image.src, image.alt, 160);
        previewImage.dataset.productFormImagePreviewImg = "";
        preview.replaceChildren(previewImage);
    }

    function init() {
        document.addEventListener("change", function (event) {
            const input = event.target;
            if (!input.matches('input[type="file"][name$="-image"]')) {
                if (
                    input.matches('input[type="checkbox"][name$="-is_main"]') ||
                    input.matches('input[type="checkbox"][name$="-DELETE"]')
                ) {
                    updateMainPreview();
                }
                return;
            }

            updatePreview(input);
            updateMainPreview();
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
