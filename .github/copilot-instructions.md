# GitHub Copilot Instructions - mamiru-ops

## Project Overview

mamiru-ops is the internal operations backend for Mamiru: product catalog,
suppliers, categories, product images, prices, stock, a read-only REST API, and
a Django admin panel for operators.

Repo: luifer-villalba/mamiru-ops — deployed on Railway (Docker).

Production software. Ship working, focused changes only.

---

## Stack

- Django 6 + Django REST Framework
- PostgreSQL (dj-database-url)
- ruff (linter + formatter, line length 88)
- Django TestCase tests today; pytest + pytest-django are also configured
- unfold (admin theme)
- Pillow (product images)
- WhiteNoise (static files)

---

## Project Structure

    config/          Django project settings, urls, wsgi, auth_backends
    catalog/         Main app: models, admin, serializers, views, urls
    catalog/management/commands/import_mamiru_stock.py
    templates/       Custom admin templates
    data/            Stock CSV fixtures/sample data
    tests/           Shared pytest configuration

---

## Architecture Rules That Match This Repo

- Follow existing Django patterns before introducing new layers.
- Use service/helper functions when logic is shared, complex, or crosses module
  boundaries. Do not create a service layer just to satisfy an abstract rule.
- Prefer pure helper functions for calculations and parsing.
- Use the Django ORM instead of raw SQL.
- Type-hint new helper functions where it improves clarity; avoid churn-only
  rewrites.
- Keep public/operator-facing text in Spanish unless the surrounding developer
  documentation is already English.

---

## Models (catalog/models.py)

    Supplier: name, contact_name, whatsapp, country, notes
    Category: name, slug
    Product: code (YYNNNN, e.g. 260001), name, slug, category, supplier, material,
             product_type, cost_price, wholesale_cost, margin_percent,
             sale_price, stock, status, created_at, updated_at
    ProductImage: product (FK), image, is_main, sort_order

Prices are positive integers in guaranies. `margin_percent` is a percent value:
`40` means forty percent.

---

## API (read-only, AllowAny)

    GET /api/products/        lookup_field = slug
    GET /api/products/<slug>/
    GET /api/categories/      lookup_field = slug
    GET /api/suppliers/

Keep `select_related("category", "supplier")` and `prefetch_related("images")`
on product list/detail querysets to avoid N+1 queries.

---

## Code Style

- snake_case variables/functions, PascalCase classes
- Max line length: 88
- Imports: stdlib → third-party → local
- Test naming: `test_<behavior>_<expected_result>` or the nearest existing
  local pattern

---

## What Copilot Should Suggest

- Focused diffs that preserve current app behavior
- Django ORM queries and existing model/admin/viewset patterns
- Tests close to the changed behavior
- `select_related`/`prefetch_related` on product querysets
- Ruff-compatible formatting

---

## What Copilot Should NOT Suggest

- Broad rewrites, new frameworks, or unnecessary service layers
- Raw SQL when the ORM is enough
- Rewriting all tests from `TestCase` to pytest without a direct reason
- Hardcoded credentials, production URLs, or secrets
- Changing the generated product code format without an explicit requirement
- Write API endpoints unless explicitly requested
