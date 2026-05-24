# AI Agent Instructions - mamiru-ops

## Project Context

mamiru-ops is the internal operations backend for Mamiru. It manages the product
catalog, suppliers, categories, product images, stock, prices, and a read-only
public API. The admin is the main working surface for operators.

This is production software deployed on Railway with Docker. Prefer small,
working changes over broad rewrites.

## Stack

- Python 3.12
- Django 6
- Django REST Framework
- PostgreSQL in Docker/Railway via `DATABASE_URL`; SQLite is acceptable for
  quick local checks
- Unfold for the Django admin
- WhiteNoise for static files
- Pillow for uploaded product images
- Ruff for linting and formatting
- Django `TestCase` tests today, with pytest/pytest-django configured for local
  runs

## Current Structure

- `config/`: Django settings, URLs, auth backend, middleware, admin form wiring
- `catalog/`: core app for suppliers, categories, products, images, admin, API,
  serializers, tests, and import command
- `catalog/management/commands/import_mamiru_stock.py`: CSV stock importer
- `templates/admin/login.html`: custom admin login template
- `data/stock.csv`: sample or seed stock data

## Domain Rules

- `Supplier` stores provider name, contact data, country, and notes.
- `Category` stores name and slug.
- `Product` stores catalog identity, classification, pricing, stock, status,
  notes, timestamps, category, and supplier.
- Product codes are generated as the current two-digit year plus a four-digit
  sequence, for example `260001`. Do not document or implement `MAM-0001`
  unless the product requirement changes.
- `ProductImage` stores uploaded product images, main image flag, and sort
  order.
- Prices are stored as positive integers in guaranies.
- `margin_percent` is a percent value, not a multiplier. For example `40` means
  forty percent.

## API Rules

- The API is read-only and currently uses `AllowAny`.
- Product and category detail routes use `slug` as the lookup field.
- Product querysets should keep `select_related("category", "supplier")` and
  `prefetch_related("images")` to avoid N+1 queries.
- Avoid exposing write endpoints unless explicitly requested.

## Admin Rules

- The Django admin is an operator tool, not a marketing surface.
- Preserve the compact product list and useful filters/search.
- Keep price input friendly for local formats such as `55.000` or `55,000Gs.`.
- Product `code`, `created_at`, and `updated_at` should remain read-only in the
  admin.

## Code Style

- Follow existing Django patterns in the repo before introducing new layers.
- Use service functions only when logic is shared, complex, or crossing module
  boundaries. Do not create a service layer just to satisfy an abstract rule.
- Type-hint new helper functions where it improves clarity; do not churn whole
  files just to add hints.
- Keep imports ordered as stdlib, third-party, local. Ruff enforces this.
- Prefer ORM queries over raw SQL.
- Do not hardcode credentials, production URLs, or secrets.
- Keep public text in Spanish unless the surrounding file is clearly English
  documentation for developers.

## Testing And Checks

Use the lightest check that proves the change:

- `python manage.py check`
- `python manage.py test`
- `pytest`
- `ruff check .`
- `ruff format .`

The existing tests are in `catalog/tests.py` and use `django.test.TestCase`.
Adding pytest-style tests is fine, but do not rewrite the suite just because
pytest is available.

For quick local DB isolation, use:

```bash
DATABASE_URL=sqlite:////tmp/mamiru-ops-test.sqlite3 python manage.py test
```

## Change Discipline

- Keep changes focused on the user request.
- Do not rewrite migrations unless the user explicitly asks and the data impact
  is understood.
- Be careful with uploaded media and production storage assumptions; Railway
  does not provide persistent local disk for media by default.
- When changing models, include migrations and tests.
- When changing import behavior, test realistic CSV formats from the Mamiru
  stock sheet.
