(function () {
    const priceFieldIds = ["id_cost_price", "id_wholesale_cost", "id_sale_price"];

    function onlyDigits(value) {
        return (value || "").replace(/\D+/g, "");
    }

    function formatGuarani(value) {
        const digits = onlyDigits(value);
        if (!digits) {
            return "";
        }

        const number = Number.parseInt(digits, 10);
        if (Number.isNaN(number)) {
            return "";
        }

        return `₲ ${number.toLocaleString("es-PY")}`;
    }

    function setupField(field) {
        if (!field) {
            return;
        }

        if (field.value) {
            field.value = formatGuarani(field.value);
        }

        field.addEventListener("focus", function () {
            field.value = onlyDigits(field.value);
        });

        field.addEventListener("blur", function () {
            field.value = formatGuarani(field.value);
        });
    }

    function setupFormSubmitSanitizer(fields) {
        if (fields.length === 0) {
            return;
        }

        const form = fields[0].form;
        if (!form) {
            return;
        }

        form.addEventListener("submit", function () {
            fields.forEach(function (field) {
                field.value = onlyDigits(field.value);
            });
        });
    }

    function init() {
        const fields = priceFieldIds
            .map(function (fieldId) {
                return document.getElementById(fieldId);
            })
            .filter(Boolean);

        fields.forEach(setupField);
        setupFormSubmitSanitizer(fields);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
