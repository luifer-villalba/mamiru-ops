from decimal import Decimal
from io import BytesIO
from pathlib import Path
from unittest import mock
from xml.etree import ElementTree

from django.contrib import admin
from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import clear_url_caches, resolve, reverse
from django.utils import timezone
from django.views.static import serve
from PIL import Image

from catalog.admin import (
    CustomerAdmin,
    OrderAdmin,
    PriceHistoryInline,
    ProductAdmin,
    ProductAdminForm,
    ProductImageAdminForm,
    ProductImageInline,
    PurchaseOrderAdmin,
    build_purchase_lines,
    main_image_url,
    validate_product_image_upload,
)
from catalog.serializers import ProductSerializer
from config.forms import UsernameOrEmailAuthenticationForm
from config.settings import env_bool

from .models import (
    Category,
    Customer,
    Order,
    OrderLine,
    PriceHistory,
    Product,
    ProductImage,
    PurchaseOrder,
    PurchaseOrderLine,
    Supplier,
)


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

    @mock.patch.dict("os.environ", {"SERVE_MEDIA_FILES": "TRUE"})
    def test_env_bool_accepts_uppercase_true(self):
        self.assertTrue(env_bool("SERVE_MEDIA_FILES"))

    @override_settings(
        STORAGES={
            "default": {
                "BACKEND": "django.core.files.storage.FileSystemStorage",
            },
            "staticfiles": {
                "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
            },
        }
    )
    def test_admin_login_includes_ops_metadata(self):
        response = self.client.get(reverse("admin:login"))

        self.assertContains(response, '<meta name="description"', html=False)
        self.assertContains(response, 'content="Mamiru Ops"', html=False)
        self.assertContains(
            response,
            "Panel interno de operaciones de Mamiru",
            html=False,
        )
        self.assertContains(response, '<meta property="og:title"', html=False)

    def test_media_route_is_available_when_serving_media_in_production(self):
        from importlib import reload

        import config.urls

        with override_settings(
            DEBUG=False,
            SERVE_MEDIA_FILES=True,
            MEDIA_URL="/uploads/",
        ):
            reloaded_urls = reload(config.urls)
            clear_url_caches()

            self.assertTrue(
                any(
                    getattr(pattern.pattern, "_regex", "") == r"^uploads/(?P<path>.*)$"
                    for pattern in reloaded_urls.urlpatterns
                )
            )
            self.assertEqual(resolve("/uploads/products/test.jpg").func, serve)

        reload(config.urls)
        clear_url_caches()


class ProductAdminImagePreviewTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Fotos", slug="fotos")
        self.supplier = Supplier.objects.create(name="Proveedor fotos")
        self.product = Product.objects.create(
            name="Producto con foto",
            slug="producto-con-foto",
            category=self.category,
            supplier=self.supplier,
        )

    @mock.patch("django.core.files.storage.FileSystemStorage.exists", return_value=True)
    def test_thumbnail_uses_main_image(self, storage_exists):
        ProductImage.objects.create(
            product=self.product,
            image="products/secondary.jpg",
            sort_order=1,
        )
        ProductImage.objects.create(
            product=self.product,
            image="products/main.jpg",
            is_main=True,
            sort_order=2,
        )
        product_admin = ProductAdmin(Product, admin.site)
        product = Product.objects.prefetch_related("images").get(pk=self.product.pk)

        thumbnail = str(product_admin.thumbnail(product))

        self.assertIn("/media/products/main.jpg", thumbnail)
        self.assertIn("Producto con foto", thumbnail)
        storage_exists.assert_called_once_with("products/main.jpg")

    @mock.patch("django.core.files.storage.FileSystemStorage.exists", return_value=False)
    def test_thumbnail_ignores_missing_image_file(self, storage_exists):
        ProductImage.objects.create(
            product=self.product,
            image="products/missing.jpg",
            is_main=True,
        )
        product_admin = ProductAdmin(Product, admin.site)
        product = Product.objects.prefetch_related("images").get(pk=self.product.pk)

        self.assertEqual(main_image_url(product), "")
        self.assertEqual(product_admin.thumbnail(product), "Sin foto")
        storage_exists.assert_has_calls(
            [
                mock.call("products/missing.jpg"),
                mock.call("products/missing.jpg"),
            ]
        )

    @mock.patch("django.core.files.storage.FileSystemStorage.exists", return_value=True)
    def test_inline_preview_renders_uploaded_image(self, storage_exists):
        product_image = ProductImage.objects.create(
            product=self.product,
            image="products/preview.jpg",
        )
        inline = ProductImageInline(Product, admin.site)

        preview = str(inline.preview(product_image))

        self.assertIn("/media/products/preview.jpg", preview)
        self.assertIn("Producto con foto", preview)
        storage_exists.assert_called_once_with("products/preview.jpg")

    @mock.patch("django.core.files.storage.FileSystemStorage.exists", return_value=True)
    def test_form_preview_uses_main_image(self, storage_exists):
        ProductImage.objects.create(
            product=self.product,
            image="products/secondary.jpg",
            sort_order=1,
        )
        ProductImage.objects.create(
            product=self.product,
            image="products/main.jpg",
            is_main=True,
            sort_order=2,
        )
        product_admin = ProductAdmin(Product, admin.site)
        product = Product.objects.prefetch_related("images").get(pk=self.product.pk)

        preview = str(product_admin.product_form_image_preview(product))

        self.assertIn("data-product-form-image-preview", preview)
        self.assertIn("/media/products/main.jpg", preview)
        self.assertIn("Producto con foto", preview)
        storage_exists.assert_called_once_with("products/main.jpg")

    @mock.patch("django.core.files.storage.FileSystemStorage.exists", return_value=True)
    def test_form_preview_uses_first_image_when_no_main_image(self, storage_exists):
        ProductImage.objects.create(
            product=self.product,
            image="products/first.jpg",
            sort_order=1,
        )
        ProductImage.objects.create(
            product=self.product,
            image="products/second.jpg",
            sort_order=2,
        )
        product_admin = ProductAdmin(Product, admin.site)
        product = Product.objects.prefetch_related("images").get(pk=self.product.pk)

        preview = str(product_admin.product_form_image_preview(product))

        self.assertIn("/media/products/first.jpg", preview)
        storage_exists.assert_called_once_with("products/first.jpg")

    def test_form_preview_renders_placeholder_without_image(self):
        product_admin = ProductAdmin(Product, admin.site)

        existing_preview = str(product_admin.product_form_image_preview(self.product))
        create_preview = str(product_admin.product_form_image_preview(None))

        self.assertIn("data-product-form-image-preview", existing_preview)
        self.assertIn("Sin imagen", existing_preview)
        self.assertIn("data-product-form-image-preview", create_preview)
        self.assertIn("Sin imagen", create_preview)

    def test_product_image_save_keeps_only_one_main_image(self):
        first_image = ProductImage.objects.create(
            product=self.product,
            image="products/first.jpg",
            is_main=True,
        )
        second_image = ProductImage.objects.create(
            product=self.product,
            image="products/second.jpg",
            is_main=True,
        )

        first_image.refresh_from_db()
        second_image.refresh_from_db()

        self.assertFalse(first_image.is_main)
        self.assertTrue(second_image.is_main)

    @mock.patch("django.core.files.storage.FileSystemStorage.delete")
    @mock.patch("django.core.files.storage.FileSystemStorage.exists", return_value=True)
    def test_product_image_delete_removes_existing_file(
        self,
        storage_exists,
        storage_delete,
    ):
        product_image = ProductImage.objects.create(
            product=self.product,
            image="products/delete-me.jpg",
        )

        product_image.delete()

        self.assertFalse(ProductImage.objects.filter(pk=product_image.pk).exists())
        storage_exists.assert_called_once_with("products/delete-me.jpg")
        storage_delete.assert_called_once_with("products/delete-me.jpg")

    @mock.patch("django.core.files.storage.FileSystemStorage.delete")
    @mock.patch("django.core.files.storage.FileSystemStorage.exists", return_value=False)
    def test_product_image_delete_ignores_missing_file(
        self,
        storage_exists,
        storage_delete,
    ):
        product_image = ProductImage.objects.create(
            product=self.product,
            image="products/already-gone.jpg",
        )

        product_image.delete()

        self.assertFalse(ProductImage.objects.filter(pk=product_image.pk).exists())
        storage_exists.assert_called_once_with("products/already-gone.jpg")
        storage_delete.assert_not_called()

    def test_image_form_accepts_expected_formats(self):
        buffer = BytesIO()
        Image.new("RGB", (1, 1), color="white").save(buffer, format="PNG")
        upload = SimpleUploadedFile(
            "foto.png",
            buffer.getvalue(),
            content_type="image/png",
        )
        form = ProductImageAdminForm(
            data={
                "product": self.product.pk,
                "is_main": "",
                "sort_order": "0",
            },
            files={"image": upload},
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_image_form_rejects_unsupported_formats(self):
        upload = SimpleUploadedFile(
            "foto.gif",
            b"GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00\xff\xff\xff,"
            b"\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;",
            content_type="image/gif",
        )
        form = ProductImageAdminForm(
            data={
                "product": self.product.pk,
                "is_main": "",
                "sort_order": "0",
            },
            files={"image": upload},
        )

        self.assertFalse(form.is_valid())
        self.assertIn("La imagen debe ser JPEG, PNG, WebP.", form.errors["image"])

    def test_image_validation_rejects_large_files(self):
        image = SimpleUploadedFile(
            "grande.png",
            b"x" * ((5 * 1024 * 1024) + 1),
            content_type="image/png",
        )

        with self.assertRaisesMessage(ValidationError, "La imagen no puede superar"):
            validate_product_image_upload(image)

    def test_image_validation_ignores_existing_image_fields(self):
        product_image = ProductImage.objects.create(
            product=self.product,
            image="products/missing.jpg",
        )

        validate_product_image_upload(product_image.image)

    def test_product_admin_loads_live_preview_script(self):
        self.assertIn(
            "catalog/js/product_image_preview.js",
            ProductAdmin.Media.js,
        )

    def test_product_change_form_includes_preview_layout_styles(self):
        template = Path("templates/admin/catalog/product/change_form.html").read_text()

        self.assertIn(
            "product-identification-preview-layout",
            template,
        )

    def test_product_admin_loads_clickable_rows_script(self):
        self.assertIn(
            "catalog/js/admin_clickable_rows.js",
            ProductAdmin.Media.js,
        )

    def test_product_admin_uses_pagination(self):
        from catalog.admin import ProductAdmin

        self.assertEqual(ProductAdmin.list_per_page, 25)

    def test_product_admin_list_display_order(self):
        from catalog.admin import ProductAdmin

        self.assertEqual(
            ProductAdmin.list_display,
            [
                "thumbnail",
                "code",
                "name",
                "category",
                "supplier",
                "status",
                "stock",
                "sale_price",
                "cost_price",
                "margin_percent",
                "visible_on_web",
                "is_featured",
                "display_priority",
                "classification",
            ],
        )

    def test_product_admin_renders_price_sync_source_field(self):
        from catalog.admin import ProductAdmin

        price_fields = ProductAdmin.fieldsets[2][1]["fields"]
        self.assertIn("price_sync_source", price_fields)

    def test_product_admin_groups_web_fields(self):
        from catalog.admin import ProductAdmin

        identification_fields = ProductAdmin.fieldsets[0][1]["fields"]
        identification_classes = ProductAdmin.fieldsets[0][1]["classes"]
        web_fields = ProductAdmin.fieldsets[3][1]["fields"]
        detail_fields = ProductAdmin.fieldsets[4][1]["fields"]
        care_fields = ProductAdmin.fieldsets[5][1]["fields"]
        seo_fields = ProductAdmin.fieldsets[7][1]["fields"]

        self.assertIn("code", identification_fields)
        self.assertIn("product_form_image_preview", identification_fields)
        self.assertNotIn(("code", "product_form_image_preview"), identification_fields)
        self.assertEqual(identification_fields[0], "code")
        self.assertEqual(identification_fields[-1], "product_form_image_preview")
        self.assertIn(
            "product-identification-preview-layout",
            identification_classes,
        )
        self.assertIn("visible_on_web", web_fields)
        self.assertIn("short_description", web_fields)
        self.assertIn("detailed_material", detail_fields)
        self.assertIn("is_water_resistant", care_fields)
        self.assertIn("seo_title", seo_fields)

    @override_settings(
        STORAGES={
            "default": {
                "BACKEND": "django.core.files.storage.FileSystemStorage",
            },
            "staticfiles": {
                "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
            },
        }
    )
    def test_product_change_page_includes_product_metadata(self):
        user = get_user_model().objects.create_superuser(
            username="metadata",
            email="metadata@example.com",
            password="secret",
        )
        self.client.force_login(user)
        self.product.seo_title = "Aro admin Mamiru Ops"
        self.product.seo_description = (
            "Metadata específica para la ficha interna del producto."
        )
        self.product.save()

        response = self.client.get(
            reverse("admin:catalog_product_change", args=[self.product.pk])
        )

        self.assertContains(response, "Aro admin Mamiru Ops")
        self.assertContains(
            response,
            '<meta property="og:type" content="product">',
            html=False,
        )
        self.assertContains(
            response,
            "Metadata específica para la ficha interna del producto.",
        )

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
            "classification": Product.Classification.ESSENTIALS,
            "cost_price": "10000",
            "wholesale_cost": "",
            "margin_percent": "0.40",
            "sale_price": "10000",
            "stock": "1",
            "status": Product.Status.ACTIVE,
            "short_description": "",
            "description": "",
            "detailed_material": "",
            "color": "",
            "finish": "",
            "measurements": "",
            "care_instructions": "",
            "is_water_resistant": "",
            "is_hypoallergenic": "",
            "visible_on_web": "",
            "is_featured": "",
            "display_priority": "0",
            "public_tags": "",
            "seo_title": "",
            "seo_description": "",
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


class ProductWebFieldsTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Web", slug="web")
        self.supplier = Supplier.objects.create(name="Proveedor web")

    def test_web_fields_have_operator_friendly_defaults(self):
        product = Product.objects.create(
            name="Producto web",
            slug="producto-web",
            category=self.category,
            supplier=self.supplier,
        )

        self.assertEqual(product.classification, Product.Classification.ESSENTIALS)
        self.assertFalse(product.visible_on_web)
        self.assertFalse(product.is_featured)
        self.assertFalse(product.is_water_resistant)
        self.assertFalse(product.is_hypoallergenic)
        self.assertEqual(product.display_priority, 0)
        self.assertEqual(product.short_description, "")

    def test_serializer_exposes_web_fields(self):
        product = Product.objects.create(
            name="Producto visible",
            slug="producto-visible",
            category=self.category,
            supplier=self.supplier,
            short_description="Aros delicados para todos los días.",
            description="Descripción pensada para la ficha web.",
            detailed_material="Acero inoxidable 316L con PVD 18K",
            color="Dorado",
            finish="Pulido",
            measurements="2 cm",
            care_instructions="Guardar seco.",
            is_water_resistant=True,
            is_hypoallergenic=True,
            visible_on_web=True,
            is_featured=True,
            display_priority=10,
            public_tags="minimalista, regalo",
            seo_title="Aros dorados Mamiru",
            seo_description="Aros dorados delicados de Mamiru.",
        )

        data = ProductSerializer(product).data

        self.assertEqual(data["short_description"], "Aros delicados para todos los días.")
        self.assertEqual(data["detailed_material"], "Acero inoxidable 316L con PVD 18K")
        self.assertEqual(data["color"], "Dorado")
        self.assertTrue(data["visible_on_web"])
        self.assertTrue(data["is_featured"])
        self.assertEqual(data["display_priority"], 10)
        self.assertEqual(data["seo_title"], "Aros dorados Mamiru")

    def test_serializer_exposes_computed_seo_metadata(self):
        product = Product.objects.create(
            name="Collar Aurora",
            slug="collar-aurora",
            category=self.category,
            supplier=self.supplier,
            short_description="Collar delicado para uso diario.",
        )

        data = ProductSerializer(product).data

        self.assertEqual(data["meta_title"], "Collar Aurora | Mamiru")
        self.assertEqual(data["meta_description"], "Collar delicado para uso diario.")
        self.assertEqual(data["canonical_path"], "/productos/collar-aurora/")


class SeoEndpointTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="SEO Aros", slug="seo-aros")
        self.supplier = Supplier.objects.create(name="Proveedor SEO")

    @override_settings(PUBLIC_SITE_URL="https://mamiru.example")
    def test_robots_txt_points_to_sitemap_and_blocks_private_paths(self):
        response = self.client.get("/robots.txt")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain; charset=utf-8")
        body = response.content.decode()
        self.assertIn("Disallow: /admin/", body)
        self.assertIn("Disallow: /api/", body)
        self.assertIn("Sitemap: https://mamiru.example/sitemap.xml", body)

    @override_settings(PUBLIC_SITE_URL="https://mamiru.example")
    def test_sitemap_lists_only_active_web_products_and_their_categories(self):
        visible_product = Product.objects.create(
            name="Aro visible",
            slug="aro-visible",
            category=self.category,
            supplier=self.supplier,
            status=Product.Status.ACTIVE,
            visible_on_web=True,
        )
        Product.objects.create(
            name="Aro borrador",
            slug="aro-borrador",
            category=self.category,
            supplier=self.supplier,
            status=Product.Status.DRAFT,
            visible_on_web=True,
        )
        Product.objects.create(
            name="Aro interno",
            slug="aro-interno",
            category=self.category,
            supplier=self.supplier,
            status=Product.Status.ACTIVE,
            visible_on_web=False,
        )

        response = self.client.get("/sitemap.xml")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/xml; charset=utf-8")
        root = ElementTree.fromstring(response.content)
        namespace = {"sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = [
            loc.text
            for loc in root.findall(".//sitemap:loc", namespace)
            if loc.text
        ]
        self.assertEqual(
            urls,
            [
                "https://mamiru.example/categorias/seo-aros/",
                "https://mamiru.example/productos/aro-visible/",
            ],
        )
        self.assertNotIn("https://mamiru.example/productos/aro-borrador/", urls)
        self.assertNotIn("https://mamiru.example/productos/aro-interno/", urls)
        self.assertContains(response, visible_product.updated_at.date().isoformat())

    @override_settings(PUBLIC_SITE_URL="https://mamiru.example")
    def test_product_preview_includes_product_metadata(self):
        product = Product.objects.create(
            name="Aro dorado",
            slug="aro-dorado",
            category=self.category,
            supplier=self.supplier,
            status=Product.Status.ACTIVE,
            visible_on_web=True,
            seo_title="Aro dorado Mamiru",
            seo_description="Aro dorado delicado para todos los días.",
        )
        ProductImage.objects.create(
            product=product,
            image="products/aro-dorado.jpg",
            is_main=True,
        )

        response = self.client.get("/productos/aro-dorado/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<title>Aro dorado Mamiru</title>", html=False)
        self.assertContains(
            response,
            '<meta property="og:type" content="product">',
            html=False,
        )
        self.assertContains(
            response,
            '<meta property="og:image" '
            'content="https://mamiru.example/media/products/aro-dorado.jpg">',
            html=False,
        )
        self.assertContains(
            response,
            '<link rel="canonical" href="https://mamiru.example/productos/aro-dorado/">',
            html=False,
        )

    def test_product_preview_hides_internal_products(self):
        Product.objects.create(
            name="Aro interno",
            slug="aro-interno-preview",
            category=self.category,
            supplier=self.supplier,
            status=Product.Status.ACTIVE,
            visible_on_web=False,
        )

        response = self.client.get("/productos/aro-interno-preview/")

        self.assertEqual(response.status_code, 404)

    @override_settings(PUBLIC_SITE_URL="https://mamiru.example")
    def test_category_preview_includes_category_metadata(self):
        Product.objects.create(
            name="Aro visible categoría",
            slug="aro-visible-categoria",
            category=self.category,
            supplier=self.supplier,
            status=Product.Status.ACTIVE,
            visible_on_web=True,
        )

        response = self.client.get("/categorias/seo-aros/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<title>SEO Aros | Mamiru</title>", html=False)
        self.assertContains(
            response,
            '<link rel="canonical" href="https://mamiru.example/categorias/seo-aros/">',
            html=False,
        )


class PriceHistoryTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="historial",
            email="historial@example.com",
            password="secret",
        )
        self.client.force_login(self.user)
        self.category = Category.objects.create(name="Historial", slug="historial")
        self.supplier = Supplier.objects.create(name="Proveedor historial")
        self.product = Product.objects.create(
            name="Producto historial",
            slug="producto-historial",
            category=self.category,
            supplier=self.supplier,
            cost_price=10000,
            margin_percent=Decimal("40.00"),
            sale_price=14000,
            stock=1,
            status=Product.Status.ACTIVE,
        )

    def admin_payload(self, **overrides):
        data = {
            "name": self.product.name,
            "slug": self.product.slug,
            "category": self.category.pk,
            "supplier": self.supplier.pk,
            "material": self.product.material,
            "classification": self.product.classification,
            "cost_price": "10.000",
            "wholesale_cost": "",
            "margin_percent": "40.00",
            "sale_price": "14.000",
            "price_sync_source": "sale_price",
            "stock": str(self.product.stock),
            "status": self.product.status,
            "short_description": self.product.short_description,
            "description": self.product.description,
            "detailed_material": self.product.detailed_material,
            "color": self.product.color,
            "finish": self.product.finish,
            "measurements": self.product.measurements,
            "care_instructions": self.product.care_instructions,
            "is_water_resistant": "",
            "is_hypoallergenic": "",
            "visible_on_web": "",
            "is_featured": "",
            "display_priority": str(self.product.display_priority),
            "public_tags": self.product.public_tags,
            "seo_title": self.product.seo_title,
            "seo_description": self.product.seo_description,
            "notes": self.product.notes,
            "images-TOTAL_FORMS": "0",
            "images-INITIAL_FORMS": "0",
            "images-MIN_NUM_FORMS": "0",
            "images-MAX_NUM_FORMS": "1000",
            "price_history-TOTAL_FORMS": "0",
            "price_history-INITIAL_FORMS": "0",
            "price_history-MIN_NUM_FORMS": "0",
            "price_history-MAX_NUM_FORMS": "0",
        }
        data.update(overrides)
        return data

    def test_first_save_does_not_create_price_history(self):
        self.assertEqual(PriceHistory.objects.count(), 0)

    def test_name_change_does_not_create_price_history(self):
        self.product.name = "Producto historial editado"
        self.product.save()

        self.assertEqual(PriceHistory.objects.count(), 0)

    def test_admin_price_change_creates_price_history_with_user(self):
        response = self.client.post(
            reverse("admin:catalog_product_change", args=[self.product.pk]),
            data=self.admin_payload(sale_price="15.000"),
        )

        self.assertRedirects(
            response,
            reverse("admin:catalog_product_changelist"),
            fetch_redirect_response=False,
        )
        history = PriceHistory.objects.get()
        self.assertEqual(history.product, self.product)
        self.assertEqual(history.changed_by, self.user)
        self.assertEqual(history.old_cost_price, 10000)
        self.assertEqual(history.new_cost_price, 10000)
        self.assertEqual(history.old_sale_price, 14000)
        self.assertEqual(history.new_sale_price, 15000)
        self.assertEqual(history.old_margin_percent, Decimal("40.00"))
        self.assertEqual(history.new_margin_percent, Decimal("50.00"))

    def test_price_history_inline_is_read_only_on_product_admin(self):
        from catalog.admin import ProductAdmin

        inline = ProductAdmin.inlines[1]

        self.assertEqual(inline, PriceHistoryInline)
        self.assertIn("changed_at", inline.readonly_fields)
        self.assertIn("changed_by", inline.readonly_fields)


class PurchaseOrderAdminTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="secret",
        )
        self.client.force_login(self.user)
        self.category = Category.objects.create(
            name="Compra test",
            slug="compra-test",
        )
        self.supplier = Supplier.objects.create(name="Proveedor compras")
        self.product = Product.objects.create(
            code="269999",
            name="Aro existente",
            slug="aro-existente",
            category=self.category,
            supplier=self.supplier,
            cost_price=10000,
            margin_percent=Decimal("40.00"),
            sale_price=14000,
            stock=5,
            status=Product.Status.ACTIVE,
        )
        ProductImage.objects.create(
            product=self.product,
            image="products/purchase.jpg",
            is_main=True,
        )

    def purchase_payload(self, **overrides):
        data = {
            "supplier": self.supplier.pk,
            "date": timezone.localdate().isoformat(),
            "invoice_number": "001-001-0000007",
            "notes": "Reposición semanal",
            "total_rows": "2",
            "lines-0-code": self.product.code,
            "lines-0-name": "",
            "lines-0-quantity": "3",
            "lines-0-unit_cost": "10.000",
            "lines-0-category": self.category.pk,
            "lines-0-material": "",
            "lines-0-margin_percent": "",
            "lines-1-code": "",
            "lines-1-name": "Aro nuevo",
            "lines-1-quantity": "2",
            "lines-1-unit_cost": "55.000Gs.",
            "lines-1-category": self.category.pk,
            "lines-1-material": "Acero",
            "lines-1-margin_percent": "40",
        }
        data.update(overrides)
        return data

    @mock.patch("django.core.files.storage.FileSystemStorage.exists", return_value=True)
    def test_product_lookup_returns_existing_product_data(self, storage_exists):
        response = self.client.get(
            reverse("admin:catalog_product_lookup"),
            {"code": self.product.code},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "found": True,
                "name": "Aro existente",
                "category_id": self.category.pk,
                "category_name": "Compra test",
                "supplier_name": "Proveedor compras",
                "cost_price": 10000,
                "sale_price": 14000,
                "stock": 5,
                "classification": Product.Classification.ESSENTIALS,
                "thumbnail_url": "/media/products/purchase.jpg",
                "margin_percent": "40.00",
            },
        )
        storage_exists.assert_called_once_with("products/purchase.jpg")

    @mock.patch("django.core.files.storage.FileSystemStorage.exists", return_value=True)
    def test_media_debug_reports_storage_status(self, storage_exists):
        response = self.client.get(
            reverse("admin:catalog_media_debug"),
            {"path": "products/purchase.jpg"},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["path"], "products/purchase.jpg")
        self.assertTrue(data["exists"])
        self.assertEqual(data["url"], "/media/products/purchase.jpg")
        self.assertIn("FileSystemStorage", data["storage_class"])
        storage_exists.assert_called_once_with("products/purchase.jpg")

    @mock.patch("django.core.files.storage.FileSystemStorage.exists", return_value=True)
    def test_product_search_returns_products_by_name(self, storage_exists):
        response = self.client.get(
            reverse("admin:catalog_product_search"),
            {"q": "existente"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["results"][0],
            {
                "code": "269999",
                "name": "Aro existente",
                "category_id": self.category.pk,
                "category_name": "Compra test",
                "supplier_name": "Proveedor compras",
                "cost_price": 10000,
                "sale_price": 14000,
                "stock": 5,
                "classification": Product.Classification.ESSENTIALS,
                "thumbnail_url": "/media/products/purchase.jpg",
                "margin_percent": "40.00",
            },
        )
        storage_exists.assert_called_once_with("products/purchase.jpg")

    def test_new_purchase_updates_existing_stock_and_creates_new_product(self):
        response = self.client.post(
            reverse("admin:catalog_purchase_new"),
            data=self.purchase_payload(),
        )

        order = PurchaseOrder.objects.get()
        self.assertRedirects(
            response,
            reverse("admin:catalog_purchaseorder_change", args=[order.pk]),
            fetch_redirect_response=False,
        )

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 8)

        new_product = Product.objects.get(name="Aro nuevo")
        self.assertNotEqual(new_product.code, "NO-EXISTE")
        self.assertEqual(new_product.stock, 2)
        self.assertEqual(new_product.cost_price, 55000)
        self.assertEqual(new_product.margin_percent, Decimal("40.00"))
        self.assertEqual(new_product.sale_price, 77000)
        self.assertEqual(new_product.status, Product.Status.ACTIVE)

        self.assertEqual(order.supplier, self.supplier)
        self.assertEqual(order.invoice_number, "001-001-0000007")
        self.assertEqual(order.created_by, self.user)
        self.assertEqual(order.lines.count(), 2)
        self.assertEqual(
            PurchaseOrderLine.objects.get(product=self.product).quantity,
            3,
        )
        self.assertEqual(
            PurchaseOrderLine.objects.get(product_name="Aro nuevo").product,
            new_product,
        )

    def test_new_purchase_rejects_unknown_code(self):
        lines, errors = build_purchase_lines(
            self.purchase_payload(
                total_rows="1",
                **{"lines-0-code": "NO-EXISTE", "lines-0-name": "Aro manual"},
            )
        )

        self.assertEqual(lines, [])
        self.assertEqual(
            errors,
            [
                "Fila 1: el código NO-EXISTE no existe. "
                "Dejá el código vacío para crear un producto nuevo.",
                "Agregá al menos una línea de compra.",
            ],
        )

    def test_new_purchase_rejects_blank_category_without_value_error(self):
        lines, errors = build_purchase_lines(
            self.purchase_payload(
                total_rows="1",
                **{
                    "lines-0-code": "",
                    "lines-0-name": "Aro manual",
                    "lines-0-category": "",
                },
            )
        )

        self.assertEqual(lines, [])
        self.assertEqual(
            errors,
            [
                "Fila 1: la categoría es obligatoria para productos nuevos.",
                "Agregá al menos una línea de compra.",
            ],
        )

    def test_purchase_order_summary_links_to_products(self):
        order = PurchaseOrder.objects.create(
            supplier=self.supplier,
            date=timezone.localdate(),
            created_by=self.user,
        )
        PurchaseOrderLine.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.name,
            quantity=1,
            unit_cost=10000,
            category=self.category,
            margin_percent=Decimal("40.00"),
        )
        admin_instance = PurchaseOrderAdmin(PurchaseOrder, admin.site)

        summary = str(admin_instance.line_summary(order))

        self.assertIn(self.product.code, summary)
        self.assertIn(
            reverse("admin:catalog_product_change", args=[self.product.pk]),
            summary,
        )

    def test_new_purchase_rolls_back_if_line_history_fails(self):
        with mock.patch(
            "catalog.admin.PurchaseOrderLine.objects.create",
            side_effect=RuntimeError("boom"),
        ):
            with self.assertRaises(RuntimeError):
                self.client.post(
                    reverse("admin:catalog_purchase_new"),
                    data=self.purchase_payload(total_rows="1"),
                )

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)
        self.assertEqual(PurchaseOrder.objects.count(), 0)
        self.assertEqual(PurchaseOrderLine.objects.count(), 0)


class CustomerOrderTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="pedidos",
            email="pedidos@example.com",
            password="secret",
        )
        self.client.force_login(self.user)
        self.category = Category.objects.create(name="Pedidos", slug="pedidos")
        self.supplier = Supplier.objects.create(name="Proveedor pedidos")
        self.product = Product.objects.create(
            code="260123",
            name="Collar inicial",
            slug="collar-inicial",
            category=self.category,
            supplier=self.supplier,
            cost_price=10000,
            margin_percent=Decimal("50.00"),
            sale_price=15000,
            stock=4,
            status=Product.Status.ACTIVE,
        )
        self.customer = Customer.objects.create(
            name="Eli Cliente",
            whatsapp="0981123456",
            city="Asunción",
        )

    def test_customer_with_whatsapp_appears_in_admin_list(self):
        admin_instance = CustomerAdmin(Customer, admin.site)

        self.assertIn("name", admin_instance.list_display)
        self.assertIn("whatsapp", admin_instance.list_display)
        self.assertEqual(str(self.customer), "Eli Cliente")
        self.assertEqual(self.customer.whatsapp, "0981123456")

    def test_order_total_uses_current_product_price_before_confirmation(self):
        order = Order.objects.create(customer=self.customer, created_by=self.user)
        OrderLine.objects.create(order=order, product=self.product, quantity=2)

        self.assertEqual(order.total, 30000)

    def test_confirming_order_saves_product_snapshot(self):
        order = Order.objects.create(customer=self.customer, created_by=self.user)
        line = OrderLine.objects.create(order=order, product=self.product, quantity=2)

        self.product.name = "Collar editado"
        self.product.code = "260124"
        self.product.sale_price = 18000
        self.product.save()

        order.status = Order.Status.CONFIRMED
        order.save()

        line.refresh_from_db()
        self.assertEqual(line.product_name, "Collar editado")
        self.assertEqual(line.product_code, "260124")
        self.assertEqual(line.unit_price, 18000)
        self.assertEqual(order.total, 36000)

        self.product.sale_price = 22000
        self.product.name = "Collar posterior"
        self.product.save()

        line.quantity = 3
        line.save()

        line.refresh_from_db()
        self.assertEqual(line.product_name, "Collar editado")
        self.assertEqual(line.unit_price, 18000)
        self.assertEqual(line.total, 54000)

    def test_customer_detail_shows_order_history_inline(self):
        order = Order.objects.create(
            customer=self.customer,
            status=Order.Status.CONFIRMED,
            created_by=self.user,
        )
        OrderLine.objects.create(order=order, product=self.product, quantity=1)
        admin_instance = CustomerAdmin(Customer, admin.site)
        inline = admin_instance.inlines[0](Customer, admin.site)

        self.assertEqual(admin_instance.inlines[0].model, Order)
        self.assertEqual(inline.total_display(order), "₲ 15.000")

    def test_order_admin_sets_created_by_and_displays_total(self):
        order = Order(customer=self.customer, status=Order.Status.DRAFT)
        admin_instance = OrderAdmin(Order, admin.site)

        admin_instance.save_model(
            request=mock.Mock(user=self.user),
            obj=order,
            form=None,
            change=False,
        )
        OrderLine.objects.create(order=order, product=self.product, quantity=3)

        self.assertEqual(order.created_by, self.user)
        self.assertEqual(admin_instance.total_display(order), "₲ 45.000")


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
