(function () {
    const priceFieldIds = ["id_cost_price", "id_wholesale_cost", "id_sale_price"];
    const costFieldId = "id_cost_price";
    const wholesaleCostFieldId = "id_wholesale_cost";
    const marginFieldId = "id_margin_percent";
    const salePriceFieldId = "id_sale_price";
    const priceSyncSourceFieldId = "id_price_sync_source";
    let syncingCalculatedFields = false;

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

    function parseIntegerField(field) {
        if (!field) {
            return null;
        }

        const digits = onlyDigits(field.value);
        if (!digits) {
            return null;
        }

        const value = Number.parseInt(digits, 10);
        return Number.isNaN(value) ? null : value;
    }

    function parseDecimalField(field) {
        if (!field || !field.value) {
            return null;
        }

        const normalized = field.value.replace(",", ".").trim();
        const value = Number.parseFloat(normalized);
        return Number.isNaN(value) ? null : value;
    }

    function roundUpToHundred(value) {
        return Math.ceil(value / 100) * 100;
    }

    function calculateSalePrice(cost, marginPercent) {
        const multiplier = 1 - marginPercent / 100;
        if (multiplier <= 0) {
            return null;
        }

        return roundUpToHundred(cost / multiplier);
    }

    function calculateMarginPercent(cost, salePrice) {
        if (!salePrice) {
            return null;
        }

        return ((salePrice - cost) / salePrice) * 100;
    }

    function getMarginBaseCost(costField, wholesaleCostField) {
        const wholesaleCost = parseIntegerField(wholesaleCostField);
        if (wholesaleCost !== null) {
            return wholesaleCost;
        }

        return parseIntegerField(costField);
    }

    function updateSalePriceFromMargin(costField, wholesaleCostField, marginField, salePriceField) {
        if (syncingCalculatedFields) {
            return;
        }

        const cost = getMarginBaseCost(costField, wholesaleCostField);
        const marginPercent = parseDecimalField(marginField);
        if (cost === null || marginPercent === null) {
            return;
        }

        const salePrice = calculateSalePrice(cost, marginPercent);
        if (salePrice === null) {
            return;
        }

        syncingCalculatedFields = true;
        setPriceSyncSource("margin_percent");
        salePriceField.value = formatGuarani(String(salePrice));
        syncingCalculatedFields = false;
    }

    function updateMarginFromSalePrice(costField, wholesaleCostField, marginField, salePriceField) {
        if (syncingCalculatedFields) {
            return;
        }

        const cost = getMarginBaseCost(costField, wholesaleCostField);
        const salePrice = parseIntegerField(salePriceField);
        if (cost === null) {
            return;
        }

        const marginPercent = calculateMarginPercent(cost, salePrice);
        if (marginPercent === null) {
            return;
        }

        syncingCalculatedFields = true;
        setPriceSyncSource("sale_price");
        marginField.value = marginPercent.toFixed(2);
        syncingCalculatedFields = false;
    }

    function setPriceSyncSource(source) {
        const sourceField = document.getElementById(priceSyncSourceFieldId);
        if (sourceField) {
            sourceField.value = source;
        }
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

    function setupPriceCalculator() {
        const costField = document.getElementById(costFieldId);
        const wholesaleCostField = document.getElementById(wholesaleCostFieldId);
        const marginField = document.getElementById(marginFieldId);
        const salePriceField = document.getElementById(salePriceFieldId);

        if (!costField || !marginField || !salePriceField) {
            return;
        }

        costField.addEventListener("blur", function () {
            updateSalePriceFromMargin(costField, wholesaleCostField, marginField, salePriceField);
        });

        if (wholesaleCostField) {
            wholesaleCostField.addEventListener("blur", function () {
                updateSalePriceFromMargin(costField, wholesaleCostField, marginField, salePriceField);
            });
        }

        marginField.addEventListener("input", function () {
            updateSalePriceFromMargin(costField, wholesaleCostField, marginField, salePriceField);
        });

        marginField.addEventListener("blur", function () {
            updateSalePriceFromMargin(costField, wholesaleCostField, marginField, salePriceField);
        });

        salePriceField.addEventListener("input", function () {
            updateMarginFromSalePrice(costField, wholesaleCostField, marginField, salePriceField);
        });

        salePriceField.addEventListener("blur", function () {
            updateMarginFromSalePrice(costField, wholesaleCostField, marginField, salePriceField);
        });
    }

    function init() {
        const fields = priceFieldIds
            .map(function (fieldId) {
                return document.getElementById(fieldId);
            })
            .filter(Boolean);

        fields.forEach(setupField);
        setupPriceCalculator();
        setupFormSubmitSanitizer(fields);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
