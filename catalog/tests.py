from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalog.dashboard import admin_dashboard_callback

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


class AdminDashboardTests(TestCase):
    def setUp(self):
        Product.objects.all().delete()
        Category.objects.all().delete()
        Supplier.objects.all().delete()

        self.category = Category.objects.create(name="Test Aros", slug="test-aros")
        self.supplier = Supplier.objects.create(name="Test Mamiru")

    def create_product(self, **overrides):
        defaults = {
            "name": "Aro dorado",
            "slug": "aro-dorado",
            "category": self.category,
            "supplier": self.supplier,
            "sale_price": 55000,
            "stock": 8,
            "status": Product.Status.ACTIVE,
        }
        defaults.update(overrides)
        return Product.objects.create(**defaults)

    def test_dashboard_context_includes_metrics_and_products(self):
        product = self.create_product()
        context = admin_dashboard_callback(None, {})

        self.assertEqual(context["dashboard_metrics"][0]["value"], 1)
        self.assertEqual(context["dashboard_products"][0]["name"], product.name)
        self.assertEqual(context["dashboard_products"][0]["price"], "₲ 55.000")
        self.assertEqual(
            context["dashboard_products"][0]["url"],
            reverse("admin:catalog_product_change", args=[product.pk]),
        )
        self.assertEqual(
            context["product_changelist_url"],
            reverse("admin:catalog_product_changelist"),
        )
        self.assertEqual(context["product_add_url"], reverse("admin:catalog_product_add"))

    def test_dashboard_limits_products_to_first_25(self):
        for index in range(30):
            self.create_product(
                name=f"Producto {index:02d}",
                slug=f"producto-{index:02d}",
            )

        context = admin_dashboard_callback(None, {})

        self.assertEqual(len(context["dashboard_products"]), 25)
        self.assertEqual(context["dashboard_metrics"][0]["value"], 30)
