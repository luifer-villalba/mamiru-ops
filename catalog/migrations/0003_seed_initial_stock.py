import csv
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.db import migrations
from django.utils import timezone
from django.utils.text import slugify


def clean_price(value):
    if not value:
        return 0
    cleaned = re.sub(r"[^\d,\.]", "", value.strip())
    if not cleaned:
        return 0
    cleaned = cleaned.replace(".", "").replace(",", "")
    try:
        return int(cleaned)
    except ValueError:
        return 0


def clean_percent(value):
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


def clean_text(value):
    return " ".join(value.strip().split()) if value else ""


def clean_row(row):
    return {clean_text(key): value for key, value in row.items() if key}


def unique_slug(name, existing_slugs):
    base = slugify(name)
    slug = base
    counter = 1
    while slug in existing_slugs:
        slug = f"{base}-{counter}"
        counter += 1
    existing_slugs.add(slug)
    return slug


def seed_initial_stock(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    Product = apps.get_model("catalog", "Product")
    Supplier = apps.get_model("catalog", "Supplier")
    stock_file = Path(settings.BASE_DIR) / "data" / "stock.csv"

    if not stock_file.exists():
        return

    existing_slugs = set(Product.objects.values_list("slug", flat=True))
    existing_category_slugs = set(Category.objects.values_list("slug", flat=True))
    year_prefix = timezone.now().strftime("%y")

    with stock_file.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row_number, row in enumerate(reader, start=2):
            row = clean_row(row)
            if not any(clean_text(value) for value in row.values()):
                continue

            code = clean_text(row.get("Codigo", ""))
            name = clean_text(row.get("Producto", ""))
            category_name = clean_text(
                row.get("Categoría", "") or row.get("Categoria", "")
            )
            material = clean_text(row.get("Material", ""))
            product_type = clean_text(row.get("Tipo", ""))
            supplier_name = clean_text(row.get("Proveedor", ""))

            if not name:
                continue

            if not code:
                code = f"{year_prefix}{row_number - 1:04d}"

            if Product.objects.filter(code=code).exists():
                continue

            if not category_name:
                category_name = "Sin categoría"
            category_slug = unique_slug(category_name, existing_category_slugs)
            category, _created = Category.objects.get_or_create(
                name=category_name,
                defaults={"slug": category_slug},
            )

            if not supplier_name:
                supplier_name = "Sin proveedor"
            supplier, _created = Supplier.objects.get_or_create(name=supplier_name)

            Product.objects.create(
                code=code,
                name=name,
                slug=unique_slug(name, existing_slugs),
                category=category,
                supplier=supplier,
                material=material,
                product_type=product_type,
                cost_price=clean_price(row.get("Costo", "")),
                wholesale_cost=clean_price(row.get("Costo Mayorista", "")) or None,
                margin_percent=clean_percent(row.get("Margen %", "")),
                sale_price=clean_price(row.get("Precio Venta", "")),
                stock=int(clean_text(row.get("Stock Actual", "0")) or 0),
                status="active",
            )


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0002_alter_category_name_alter_category_slug_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_initial_stock, migrations.RunPython.noop),
    ]
