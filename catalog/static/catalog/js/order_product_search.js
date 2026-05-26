(() => {
  const shortcutsBox = document.querySelector("[data-order-product-search-url]");
  const linesGroup = document.querySelector("#lines-group");
  const modal = document.querySelector("#order-product-search-modal");

  if (!shortcutsBox || !linesGroup || !modal) {
    return;
  }

  const searchUrl = shortcutsBox.dataset.orderProductSearchUrl;
  const lookupUrl = shortcutsBox.dataset.orderProductLookupUrl;
  const input = modal.querySelector(".order-product-search-input");
  const results = modal.querySelector(".order-product-search-results");
  const closeButton = modal.querySelector(".order-product-search-close");
  let activeRow = null;
  let isFillingProduct = false;
  let searchTimer = null;

  const formatGuarani = (value) => `₲ ${Number(value || 0).toLocaleString("es-PY")}`;
  const rows = () => Array.from(linesGroup.querySelectorAll("tbody.form-group"));
  const lastRow = () => rows().at(-1) || null;
  const rowFromElement = (element) => element?.closest?.("tbody.form-group") || null;
  const currentRow = () => rowFromElement(document.activeElement) || lastRow();
  const productSelect = (row) => row?.querySelector('select[name$="-product"]');
  const quantityInput = (row) => row?.querySelector('input[name$="-quantity"]');
  const readonlyCell = (row, fieldName) =>
    row?.querySelector(`.field-${fieldName} .readonly`);

  const updateLineTotal = (row) => {
    const quantity = Number(quantityInput(row)?.value || 0);
    const unitPrice = Number(row?.dataset.orderUnitPrice || 0);
    const total = readonlyCell(row, "line_total");

    if (total) {
      total.textContent = quantity && unitPrice ? formatGuarani(quantity * unitPrice) : "-";
    }
  };

  const triggerChange = (element) => {
    element.dispatchEvent(new Event("change", { bubbles: true }));

    if (window.django?.jQuery) {
      window.django.jQuery(element).trigger("change");
    }
  };

  const focusRow = (row) => {
    const select = productSelect(row);
    const select2 = row?.querySelector(".select2-selection");
    if (select2) {
      select2.focus();
      return;
    }
    select?.focus();
  };

  const addRow = () => {
    const addLink = linesGroup.querySelector(".add-row");
    addLink?.click();
    window.setTimeout(() => focusRow(lastRow()), 0);
  };

  const renderEmpty = () => {
    const empty = document.createElement("div");
    empty.className = "order-product-search-result";
    empty.textContent = "Sin resultados";
    results.replaceChildren(empty);
  };

  const fillProduct = (row, product) => {
    const select = productSelect(row);
    const quantity = quantityInput(row);

    if (!select || !product.id) {
      return;
    }

    const label = `${product.code} · ${product.name}`;
    const existingOption = Array.from(select.options).find(
      (option) => option.value === String(product.id),
    );
    const option = existingOption || new Option(label, product.id, true, true);
    option.selected = true;
    option.textContent = label;

    if (!existingOption) {
      select.append(option);
    }

    isFillingProduct = true;
    triggerChange(select);
    isFillingProduct = false;
    const code = readonlyCell(row, "product_code_display");
    const name = readonlyCell(row, "product_name_display");
    const unitPrice = readonlyCell(row, "unit_price_display");
    row.dataset.orderUnitPrice = String(product.sale_price || 0);

    if (code) {
      code.textContent = product.code || "-";
    }
    if (name) {
      name.textContent = product.name || "-";
    }
    if (unitPrice) {
      unitPrice.textContent = formatGuarani(product.sale_price);
    }

    if (quantity && !quantity.value) {
      quantity.value = "1";
      triggerChange(quantity);
    }

    updateLineTotal(row);

    quantity?.focus();
  };

  const loadSelectedProduct = async (row) => {
    if (isFillingProduct) {
      return;
    }

    const select = productSelect(row);
    if (!select?.value || !lookupUrl) {
      return;
    }

    const response = await fetch(`${lookupUrl}?id=${encodeURIComponent(select.value)}`, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });
    const product = await response.json();
    if (product.found) {
      fillProduct(row, product);
    }
  };

  const closeSearch = () => {
    modal.hidden = true;
    activeRow = null;
    results.replaceChildren();
  };

  const renderResults = (products) => {
    if (!products.length) {
      renderEmpty();
      return;
    }

    const buttons = products.map((product) => {
      const button = document.createElement("button");
      const copy = document.createElement("span");
      const main = document.createElement("span");
      const meta = document.createElement("span");
      const stats = document.createElement("span");

      button.className = "order-product-search-result";
      button.type = "button";
      copy.className = "order-product-search-copy";
      main.className = "order-product-search-main";
      meta.className = "order-product-search-meta";
      stats.className = "order-product-search-stats";
      main.textContent = `${product.code} · ${product.name}`;
      meta.textContent = [product.category_name, product.supplier_name]
        .filter(Boolean)
        .join(" · ");
      stats.innerHTML = `
        <span>Stock ${product.stock || 0}</span>
        <span>Precio ${formatGuarani(product.sale_price)}</span>
      `;
      copy.append(main, meta);

      if (product.thumbnail_url) {
        const thumb = document.createElement("img");
        thumb.className = "order-product-search-thumb";
        thumb.alt = product.name;
        thumb.src = product.thumbnail_url;
        thumb.addEventListener("error", () => thumb.remove());
        button.append(thumb);
      }

      button.append(copy, stats);
      button.addEventListener("click", () => {
        if (activeRow) {
          fillProduct(activeRow, product);
        }
        closeSearch();
      });
      return button;
    });

    results.replaceChildren(...buttons);
  };

  const searchProducts = async () => {
    const query = input.value.trim();
    const response = await fetch(`${searchUrl}?q=${encodeURIComponent(query)}`, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });
    const data = await response.json();
    renderResults(data.results || []);
  };

  const openSearch = (row) => {
    activeRow = row || lastRow();
    if (!activeRow) {
      addRow();
      activeRow = lastRow();
    }

    modal.hidden = false;
    input.value = "";
    input.focus();
    searchProducts();
  };

  const buildSearchButton = () => {
    const button = document.createElement("button");
    button.className = "order-product-search-button";
    button.type = "button";
    button.title = "Buscar producto";
    button.setAttribute("aria-label", "Buscar producto");
    button.innerHTML = `
      <svg viewBox="0 0 20 20" aria-hidden="true" focusable="false">
        <path d="M8.5 14a5.5 5.5 0 1 1 3.89-1.61L16 16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"></path>
      </svg>
    `;
    return button;
  };

  const attachSearchButtons = () => {
    rows().forEach((row) => {
      const select = productSelect(row);
      const field = select?.closest(".field-product");
      const control = select?.closest(".flex");

      if (!field || !control || field.querySelector(".order-product-search-button")) {
        return;
      }

      control.classList.add("order-product-cell");
      const button = buildSearchButton();
      button.addEventListener("click", () => openSearch(row));
      control.append(button);
    });
  };

  linesGroup.addEventListener("change", (event) => {
    const row = rowFromElement(event.target);
    if (!row) {
      return;
    }

    if (event.target.matches('select[name$="-product"]')) {
      loadSelectedProduct(row);
    }
  });

  linesGroup.addEventListener("input", (event) => {
    const row = rowFromElement(event.target);
    if (row && event.target.matches('input[name$="-quantity"]')) {
      updateLineTotal(row);
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !modal.hidden) {
      event.preventDefault();
      closeSearch();
      return;
    }

    if (!event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) {
      return;
    }

    const key = event.key.toLowerCase();
    if (key === "a") {
      event.preventDefault();
      addRow();
    }

    if (key === "b") {
      event.preventDefault();
      openSearch(currentRow());
    }

    if (key === "c") {
      event.preventDefault();
      focusRow(lastRow());
    }
  });

  closeButton.addEventListener("click", closeSearch);
  modal.addEventListener("click", (event) => {
    if (event.target === modal) {
      closeSearch();
    }
  });
  input.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = window.setTimeout(searchProducts, 180);
  });

  attachSearchButtons();
  new MutationObserver(attachSearchButtons).observe(linesGroup, {
    childList: true,
    subtree: true,
  });
})();
