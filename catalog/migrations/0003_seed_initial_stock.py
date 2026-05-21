from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.db import migrations


def seed_initial_stock(apps, schema_editor):
    stock_file = Path(settings.BASE_DIR) / "data" / "stock.csv"
    call_command(
        "import_mamiru_stock",
        str(stock_file),
        skip_existing=True,
        seed_codes=True,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0002_alter_category_name_alter_category_slug_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_initial_stock, migrations.RunPython.noop),
    ]
