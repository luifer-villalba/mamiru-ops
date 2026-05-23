from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalog.admin import ProductAdminForm

from .models import Category, Product, Supplier


class ProductCodeTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Prueba", slug="prueba")
        self.supplier = Supplier.objects.create(name="Proveedor")

    def test_product_code_is_generated_when_empty(self):
        next_code = Product.generate_code()
        product = Product.objects.create(
            name="Producto sin código",
            slug="producto-sin-codigo",
            category=self.category,
            supplier=self.supplier,
        )

        self.assertEqual(product.code, next_code)

    def test_product_code_keeps_incrementing(self):
        first_code = Product.generate_code()
        first_product = Product.objects.create(
            name="Producto uno",
            slug="producto-uno",
            category=self.category,
            supplier=self.supplier,
        )
        product = Product.objects.create(
            name="Producto dos",
            slug="producto-dos",
            category=self.category,
            supplier=self.supplier,
        )

        current_year = timezone.now().strftime("%y")
        expected_number = int(first_code[2:]) + 1
        self.assertEqual(first_product.code, first_code)
        self.assertTrue(first_product.code.startswith(current_year))
        self.assertEqual(product.code, f"{current_year}{expected_number:04d}")


class AdminHomeTests(TestCase):
    def test_admin_root_redirects_to_product_changelist(self):
        response = self.client.get("/")

        self.assertRedirects(
            response,
            reverse("admin:catalog_product_changelist"),
            fetch_redirect_response=False,
        )

    def test_product_admin_uses_pagination(self):
        from catalog.admin import ProductAdmin

        self.assertEqual(ProductAdmin.list_per_page, 25)

    def test_product_admin_uses_visual_badges(self):
        from catalog.admin import ProductAdmin

        self.assertIn("stock_badge", ProductAdmin.list_display)
        self.assertIn("status_badge", ProductAdmin.list_display)
        self.assertNotIn("stock", ProductAdmin.list_display)
        self.assertNotIn("status", ProductAdmin.list_display)

    def test_product_admin_renders_price_sync_source_field(self):
        from catalog.admin import ProductAdmin

        price_fields = ProductAdmin.fieldsets[2][1]["fields"]
        self.assertIn("price_sync_source", price_fields)


class ProductAdminFormPriceSyncTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Formulario", slug="formulario")
        self.supplier = Supplier.objects.create(name="Proveedor formulario")

    def form_data(self, **overrides):
        data = {
            "name": "Producto formulario",
            "slug": "producto-formulario",
            "category": self.category.pk,
            "supplier": self.supplier.pk,
            "material": "",
            "product_type": "",
            "cost_price": "10000",
            "wholesale_cost": "",
            "margin_percent": "0.40",
            "sale_price": "10000",
            "stock": "1",
            "status": Product.Status.ACTIVE,
            "notes": "",
            "price_sync_source": "margin_percent",
        }
        data.update(overrides)
        return data

    def test_margin_percent_updates_sale_price_rounded_up_to_hundred(self):
        form = ProductAdminForm(
            data=self.form_data(
                cost_price="10000",
                margin_percent="0.40",
                sale_price="10000",
                price_sync_source="margin_percent",
            )
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["sale_price"], 10100)

    def test_sale_price_updates_margin_percent(self):
        form = ProductAdminForm(
            data=self.form_data(
                cost_price="55000",
                margin_percent="0",
                sale_price="90000",
                price_sync_source="sale_price",
            )
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["margin_percent"], Decimal("63.64"))
