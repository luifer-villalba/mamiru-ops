# GitHub Copilot Instructions — mamiru-ops

## Project Overview

mamiru-ops is the internal backend for Mamiru — product catalog, suppliers, and
categories with REST API and Django admin panel.
Repo: luifer-villalba/mamiru-ops — deployed on Railway (Docker).

Production software. Ship working code only.

---

## Stack

- Django 6 + Django REST Framework
- PostgreSQL (dj-database-url)
- ruff (linter + formatter, line length 88)
- pytest + pytest-django + pytest-cov
- unfold (admin theme)
- Pillow (product images)
- WhiteNoise (static files)

---

## Project Structure

    config/          Django project settings, urls, wsgi, auth_backends
    catalog/         Main app: models, admin, serializers, views, urls
    catalog/management/commands/import_mamiru_stock.py
    tests/           pytest test suite

---

## Architecture Rules

- No business logic in views or admin — service functions only
- Pure functions for business logic (no Django imports in core logic)
- DB access only through Django ORM inside service boundaries
- Type hints on every function signature
- Docstrings on all public functions

---

## Models (catalog/models.py)

    Supplier: name, contact_name, whatsapp, country, notes
    Category: name, slug
    Product: code (MAM-XXXX), name, slug, category, supplier, material,
             product_type, cost_price, wholesale_cost, margin_percent,
             sale_price, stock, status, created_at, updated_at
    ProductImage: product (FK), image, is_main, sort_order

---

## API (read-only, AllowAny)

    GET /api/products/        lookup_field = slug
    GET /api/products/<slug>/
    GET /api/categories/      lookup_field = slug
    GET /api/suppliers/

---

## Code Style

- snake_case variables/functions, PascalCase classes
- Max line length: 88
- Imports: stdlib → third-party → local
- Test naming: test_<function>_<scenario>_<expected_result>

---

## What Copilot Should Suggest

✅ Full file contents, not partial snippets
✅ Type hints on every function
✅ pytest-style tests (not unittest)
✅ select_related/prefetch_related on querysets
✅ Service functions for business logic

---

## What Copilot Should NOT Suggest

❌ Business logic in views or admin actions
❌ Raw SQL (use ORM)
❌ unittest.TestCase (use pytest)
❌ Hardcoded credentials or URLs
❌ Missing type hints
