"""
Management command to import stock from a Mamiru CSV file.

Usage:
    python manage.py import_mamiru_stock path/to/file.csv
"""

import csv
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from catalog.models import Category, Product, Supplier


def clean_price(value: str) -> int:
    """
    Convert price strings like "55,000Gs." or "55.000" or "55000" to integer.
    Returns 0 if value is empty or cannot be parsed.
    """
    if not value:
        return 0
    # Remove currency symbols, letters, spaces
    cleaned = re.sub(r"[^\d,\.]", "", value.strip())
    if not cleaned:
        return 0
    # If there's a comma and a dot, determine which is the thousands separator
    # Paraguay format: 55,000 means 55000 (comma is thousands separator)
    # Remove commas (thousands separator) and dots that are not decimal
    # Heuristic: if last separator is comma treat it as decimal; otherwise dots are decimal
    cleaned = cleaned.replace(".", "").replace(",", "")
    try:
        return int(cleaned)
    except ValueError:
        return 0


def clean_percent(value: str) -> Decimal | None:
    """Convert margin percent string like "25%" or "25,5" to Decimal. Returns None if empty."""
    if not value:
        return None
    cleaned = re.sub(r"[^\d,.]", "", value.strip())
    if not cleaned:
        return None
    cleaned = cleaned.replace(",", ".")
    try:
        return Decimal(cleaned).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def clean_text(value: str) -> str:
    """Strip and normalize whitespace."""
    return " ".join(value.strip().split()) if value else ""


def generate_code(counter: int) -> str:
    return f"MAM-{counter:04d}"


def unique_slug(name: str, existing_slugs: set) -> str:
    base = slugify(name)
    slug = base
    counter = 1
    while slug in existing_slugs:
        slug = f"{base}-{counter}"
        counter += 1
    existing_slugs.add(slug)
    return slug


class Command(BaseCommand):
    help = "Import Mamiru stock from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Path to the CSV file")

    def handle(self, *args, **options):
        csv_path = Path(options["csv_file"])
        if not csv_path.exists():
            raise CommandError(f"File not found: {csv_path}")

        stats = {
            "created": 0,
            "updated": 0,
            "categories_created": 0,
            "suppliers_created": 0,
            "errors": 0,
        }

        # Pre-load existing slugs to avoid duplicates during import
        existing_slugs: set = set(Product.objects.values_list("slug", flat=True))
        existing_category_slugs: set = set(Category.objects.values_list("slug", flat=True))

        # Track next auto-code counter
        max_auto = (
            Product.objects.filter(code__startswith="MAM-")
            .values_list("code", flat=True)
        )
        auto_counter = 1
        for code in max_auto:
            try:
                num = int(code.split("-")[1])
                if num >= auto_counter:
                    auto_counter = num + 1
            except (IndexError, ValueError):
                pass

        with open(csv_path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            for row_number, row in enumerate(reader, start=2):  # start=2: header is row 1
                try:
                    # --- Extract fields ---
                    code = clean_text(row.get("Codigo", ""))
                    name = clean_text(row.get("Producto", ""))
                    category_name = clean_text(row.get("Categoría", "") or row.get("Categoria", ""))
                    material = clean_text(row.get("Material", ""))
                    product_type = clean_text(row.get("Tipo", ""))
                    supplier_name = clean_text(row.get("Proveedor", ""))
                    cost_raw = row.get("Costo", "")
                    wholesale_raw = row.get("Costo Mayorista", "")
                    margin_raw = row.get("Margen %", "")
                    sale_raw = row.get("Precio Venta", "")
                    stock_raw = row.get("Stock Actual", "0")

                    # --- Validate minimum required fields ---
                    if not name:
                        self.stderr.write(
                            f"Row {row_number}: skipped – missing product name."
                        )
                        stats["errors"] += 1
                        continue

                    # --- Auto-generate code if empty ---
                    if not code:
                        code = generate_code(auto_counter)
                        auto_counter += 1

                    # --- Ensure category exists ---
                    if not category_name:
                        category_name = "Sin categoría"
                    category_slug = unique_slug(category_name, existing_category_slugs)
                    category, cat_created = Category.objects.get_or_create(
                        name=category_name,
                        defaults={"slug": category_slug},
                    )
                    if cat_created:
                        stats["categories_created"] += 1

                    # --- Ensure supplier exists ---
                    if not supplier_name:
                        supplier_name = "Sin proveedor"
                    supplier, sup_created = Supplier.objects.get_or_create(
                        name=supplier_name,
                    )
                    if sup_created:
                        stats["suppliers_created"] += 1

                    # --- Clean prices ---
                    cost_price = clean_price(cost_raw)
                    wholesale_cost = clean_price(wholesale_raw) or None
                    margin_percent = clean_percent(margin_raw)
                    sale_price = clean_price(sale_raw)

                    # --- Parse stock ---
                    try:
                        stock = int(clean_text(stock_raw)) if stock_raw else 0
                    except ValueError:
                        stock = 0

                    # --- Create or update product ---
                    try:
                        product = Product.objects.get(code=code)
                        # Update
                        product.name = name
                        product.category = category
                        product.supplier = supplier
                        product.material = material
                        product.product_type = product_type
                        product.cost_price = cost_price
                        product.wholesale_cost = wholesale_cost
                        product.margin_percent = margin_percent
                        product.sale_price = sale_price
                        product.stock = stock
                        product.save()
                        stats["updated"] += 1
                    except Product.DoesNotExist:
                        slug = unique_slug(name, existing_slugs)
                        Product.objects.create(
                            code=code,
                            name=name,
                            slug=slug,
                            category=category,
                            supplier=supplier,
                            material=material,
                            product_type=product_type,
                            cost_price=cost_price,
                            wholesale_cost=wholesale_cost,
                            margin_percent=margin_percent,
                            sale_price=sale_price,
                            stock=stock,
                            status=Product.Status.ACTIVE,
                        )
                        stats["created"] += 1

                except Exception as exc:  # noqa: BLE001
                    self.stderr.write(f"Row {row_number}: error – {exc}")
                    stats["errors"] += 1

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("Import complete"))
        self.stdout.write(f"  Products created : {stats['created']}")
        self.stdout.write(f"  Products updated : {stats['updated']}")
        self.stdout.write(f"  Categories created: {stats['categories_created']}")
        self.stdout.write(f"  Suppliers created : {stats['suppliers_created']}")
        if stats["errors"]:
            self.stdout.write(self.style.WARNING(f"  Errors found     : {stats['errors']}"))
        else:
            self.stdout.write(f"  Errors found     : {stats['errors']}")
        self.stdout.write("=" * 50 + "\n")
