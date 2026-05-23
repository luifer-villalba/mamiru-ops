from decimal import Decimal

from django.contrib.auth import authenticate, get_user_model
from django.forms import modelformset_factory
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalog.admin import ProductAdminForm
from config.forms import UsernameOrEmailAuthenticationForm

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

    def test_product_admin_uses_inline_editable_fields(self):
        from catalog.admin import ProductAdmin

        self.assertEqual(
            ProductAdmin.list_editable,
            [
                "stock",
                "sale_price",
                "cost_price",
                "margin_percent",
                "supplier",
                "category",
                "status",
            ],
        )

    def test_product_admin_list_display_order(self):
        from catalog.admin import ProductAdmin

        self.assertEqual(
            ProductAdmin.list_display,
            [
                "code",
                "name",
                "stock",
                "sale_price",
                "cost_price",
                "margin_percent",
                "supplier",
                "category",
                "status",
            ],
        )

    def test_product_admin_renders_price_sync_source_field(self):
        from catalog.admin import ProductAdmin

        price_fields = ProductAdmin.fieldsets[2][1]["fields"]
        self.assertIn("price_sync_source", price_fields)

    def test_sale_price_column_label_is_short(self):
        field = Product._meta.get_field("sale_price")

        self.assertEqual(field.verbose_name, "Precio")


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


class ProductChangeListInlineEditTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Inline", slug="inline")
        self.supplier = Supplier.objects.create(name="Proveedor inline")
        self.product = Product.objects.create(
            name="Producto inline",
            slug="producto-inline",
            category=self.category,
            supplier=self.supplier,
            cost_price=10000,
            sale_price=10000,
            margin_percent=Decimal("0.00"),
            stock=1,
            status=Product.Status.ACTIVE,
        )

    def formset_data(self, **overrides):
        data = {
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "1",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
            "form-0-id": str(self.product.pk),
            "form-0-stock": str(self.product.stock),
            "form-0-sale_price": str(self.product.sale_price),
            "form-0-cost_price": str(self.product.cost_price),
            "form-0-margin_percent": str(self.product.margin_percent),
            "form-0-supplier": str(self.supplier.pk),
            "form-0-category": str(self.category.pk),
            "form-0-status": self.product.status,
        }
        data.update(overrides)
        return data

    def build_formset(self, data):
        from catalog.admin import ProductChangeListForm, ProductChangeListFormSet

        formset_class = modelformset_factory(
            Product,
            form=ProductChangeListForm,
            formset=ProductChangeListFormSet,
            fields=[
                "stock",
                "sale_price",
                "cost_price",
                "margin_percent",
                "supplier",
                "category",
                "status",
            ],
            extra=0,
        )
        return formset_class(
            data=data,
            queryset=Product.objects.filter(pk=self.product.pk),
        )

    def test_inline_margin_change_updates_sale_price(self):
        formset = self.build_formset(
            self.formset_data(**{"form-0-margin_percent": "0.40"})
        )

        self.assertTrue(formset.is_valid(), formset.errors)
        formset.save()
        self.product.refresh_from_db()
        self.assertEqual(self.product.sale_price, 10100)

    def test_inline_sale_price_change_updates_margin_percent(self):
        formset = self.build_formset(
            self.formset_data(**{"form-0-sale_price": "18000"})
        )

        self.assertTrue(formset.is_valid(), formset.errors)
        formset.save()
        self.product.refresh_from_db()
        self.assertEqual(self.product.margin_percent, Decimal("80.00"))


class UsernameOrEmailBackendTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="luifer",
            email="luifer@example.com",
            password="super-secret",
        )

    def test_authenticates_with_username(self):
        user = authenticate(username="luifer", password="super-secret")

        self.assertEqual(user, self.user)

    def test_authenticates_with_email(self):
        user = authenticate(username="luifer@example.com", password="super-secret")

        self.assertEqual(user, self.user)

    def test_authenticates_with_email_case_insensitive(self):
        user = authenticate(username="LUIFER@EXAMPLE.COM", password="super-secret")

        self.assertEqual(user, self.user)

    def test_admin_login_form_labels_username_as_username_or_email(self):
        form = UsernameOrEmailAuthenticationForm()

        self.assertEqual(form.fields["username"].label, "Usuario o correo")
