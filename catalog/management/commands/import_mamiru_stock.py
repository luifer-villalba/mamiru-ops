"""
Comando para importar stock desde un archivo CSV de Mamiru.

Uso:
    python manage.py import_mamiru_stock ruta/al/archivo.csv
"""

import csv
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.text import slugify

from catalog.models import Category, Product, Supplier


def clean_price(value: str) -> int:
    """
    Convierte precios como "55,000Gs.", "55.000" o "55000" a entero.
    Devuelve 0 si el valor esta vacio o no se puede interpretar.
    """
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


def clean_percent(value: str) -> Decimal | None:
    """Convierte margen porcentual como "25%" o "25,5" a Decimal."""
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
    """Limpia espacios sobrantes."""
    return " ".join(value.strip().split()) if value else ""


def clean_row(row: dict) -> dict:
    """Normaliza nombres de columnas y valores del CSV."""
    return {clean_text(key): value for key, value in row.items() if key}


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
    help = "Importa stock de Mamiru desde un archivo CSV"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Ruta al archivo CSV")
        parser.add_argument(
            "--skip-existing",
            action="store_true",
            help="No actualiza productos existentes; solo crea los que falten.",
        )
        parser.add_argument(
            "--seed-codes",
            action="store_true",
            help="Genera códigos determinísticos por fila para seeds idempotentes.",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv_file"])
        if not csv_path.exists():
            raise CommandError(f"Archivo no encontrado: {csv_path}")
        skip_existing = options["skip_existing"]
        seed_codes = options["seed_codes"]

        stats = {
            "created": 0,
            "updated": 0,
            "categories_created": 0,
            "suppliers_created": 0,
            "errors": 0,
        }

        existing_slugs: set = set(Product.objects.values_list("slug", flat=True))
        existing_category_slugs: set = set(Category.objects.values_list("slug", flat=True))

        with open(csv_path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            for row_number, row in enumerate(reader, start=2):
                try:
                    row = clean_row(row)
                    if not any(clean_text(value) for value in row.values()):
                        continue

                    code = clean_text(row.get("Codigo", ""))
                    name = clean_text(row.get("Producto", ""))
                    category_name = clean_text(
                        row.get("Categoría", "")
                        or row.get("Categoria", "")
                    )
                    material = clean_text(row.get("Material", ""))
                    supplier_name = clean_text(row.get("Proveedor", ""))
                    cost_raw = row.get("Costo", "")
                    wholesale_raw = row.get("Costo Mayorista", "")
                    margin_raw = row.get("Margen %", "")
                    sale_raw = row.get("Precio Venta", "")
                    stock_raw = row.get("Stock Actual", "0")

                    if not name:
                        continue

                    if not category_name:
                        category_name = "Sin categoría"
                    category_slug = unique_slug(category_name, existing_category_slugs)
                    category, cat_created = Category.objects.get_or_create(
                        name=category_name,
                        defaults={"slug": category_slug},
                    )
                    if cat_created:
                        stats["categories_created"] += 1

                    if not supplier_name:
                        supplier_name = "Sin proveedor"
                    supplier, sup_created = Supplier.objects.get_or_create(
                        name=supplier_name,
                    )
                    if sup_created:
                        stats["suppliers_created"] += 1

                    cost_price = clean_price(cost_raw)
                    wholesale_cost = clean_price(wholesale_raw) or None
                    margin_percent = clean_percent(margin_raw)
                    sale_price = clean_price(sale_raw)

                    try:
                        stock = int(clean_text(stock_raw)) if stock_raw else 0
                    except ValueError:
                        stock = 0

                    if code:
                        product = Product.objects.filter(code=code).first()
                    elif seed_codes:
                        year_prefix = timezone.now().strftime("%y")
                        code = f"{year_prefix}{row_number - 1:04d}"
                        product = Product.objects.filter(code=code).first()
                    else:
                        product = None
                        code = Product.generate_code()

                    if product:
                        if skip_existing:
                            continue
                        product.name = name
                        product.category = category
                        product.supplier = supplier
                        product.material = material
                        product.cost_price = cost_price
                        product.wholesale_cost = wholesale_cost
                        product.margin_percent = margin_percent
                        product.sale_price = sale_price
                        product.stock = stock
                        product.save()
                        stats["updated"] += 1
                    else:
                        slug = unique_slug(name, existing_slugs)
                        Product.objects.create(
                            code=code,
                            name=name,
                            slug=slug,
                            category=category,
                            supplier=supplier,
                            material=material,
                            cost_price=cost_price,
                            wholesale_cost=wholesale_cost,
                            margin_percent=margin_percent,
                            sale_price=sale_price,
                            stock=stock,
                            status=Product.Status.ACTIVE,
                        )
                        stats["created"] += 1

                except Exception as exc:  # noqa: BLE001
                    self.stderr.write(f"Fila {row_number}: error - {exc}")
                    stats["errors"] += 1

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("Importación completada"))
        self.stdout.write(f"  Productos creados      : {stats['created']}")
        self.stdout.write(f"  Productos actualizados : {stats['updated']}")
        self.stdout.write(f"  Categorías creadas     : {stats['categories_created']}")
        self.stdout.write(f"  Proveedores creados    : {stats['suppliers_created']}")
        self.stdout.write(f"  Errores encontrados    : {stats['errors']}")
        self.stdout.write("=" * 50 + "\n")
