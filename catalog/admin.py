import re
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import F, Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from unfold.admin import ModelAdmin, TabularInline
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from catalog.management.commands.import_mamiru_stock import (
    clean_percent,
    clean_price,
    clean_text,
    unique_slug,
)

from .models import (
    Category,
    PriceHistory,
    Product,
    ProductImage,
    PurchaseOrder,
    PurchaseOrderLine,
    Supplier,
)
from .price_history import price_history_user


def format_guarani(value):
    if value in (None, ""):
        return ""
    return f"₲ {int(value):,}".replace(",", ".")


def round_up_to_hundred(value):
    value = Decimal(value)
    return int((value / Decimal("100")).to_integral_value(rounding=ROUND_CEILING) * 100)


def calculate_sale_price(cost_price, margin_percent):
    multiplier = Decimal("1") + (Decimal(margin_percent) / Decimal("100"))
    return round_up_to_hundred(Decimal(cost_price) * multiplier)


def calculate_margin_percent(cost_price, sale_price):
    if not cost_price:
        return None

    margin = (
        (Decimal(sale_price) - Decimal(cost_price)) / Decimal(cost_price)
    ) * Decimal("100")
    return margin.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def parse_positive_int(value, field_name):
    number = clean_price(value)
    if number <= 0:
        raise ValidationError(f"{field_name} debe ser mayor a cero.")
    return number


def parse_optional_pk(value):
    value = clean_text(str(value or ""))
    return int(value) if value.isdigit() else None


def product_lookup_view(request):
    code = clean_text(request.GET.get("code", ""))
    product = (
        Product.objects.select_related("category", "supplier")
        .filter(code=code)
        .first()
    )
    if not product:
        return JsonResponse({"found": False})

    return JsonResponse(
        {
            "found": True,
            "name": product.name,
            "category_id": product.category_id,
            "category_name": product.category.name,
            "supplier_name": product.supplier.name,
            "cost_price": product.cost_price,
            "sale_price": product.sale_price,
            "stock": product.stock,
            "margin_percent": (
                str(product.margin_percent)
                if product.margin_percent is not None
                else ""
            ),
        }
    )


def product_search_view(request):
    query = clean_text(request.GET.get("q", ""))
    products = Product.objects.select_related("category", "supplier")
    if query:
        products = products.filter(Q(code__icontains=query) | Q(name__icontains=query))
    products = products.order_by("code", "name")[:12]

    return JsonResponse(
        {
            "results": [
                {
                    "code": product.code,
                    "name": product.name,
                    "category_id": product.category_id,
                    "category_name": product.category.name,
                    "supplier_name": product.supplier.name,
                    "cost_price": product.cost_price,
                    "sale_price": product.sale_price,
                    "stock": product.stock,
                    "margin_percent": (
                        str(product.margin_percent)
                        if product.margin_percent is not None
                        else ""
                    ),
                }
                for product in products
            ]
        }
    )


def build_purchase_lines(post_data):
    total_rows = int(post_data.get("total_rows", "0") or 0)
    lines = []
    errors = []

    for index in range(total_rows):
        prefix = f"lines-{index}-"
        code = clean_text(post_data.get(f"{prefix}code", ""))
        name = clean_text(post_data.get(f"{prefix}name", ""))
        quantity_raw = post_data.get(f"{prefix}quantity", "")
        unit_cost_raw = post_data.get(f"{prefix}unit_cost", "")
        sale_price_raw = post_data.get(f"{prefix}sale_price", "")
        category_id = parse_optional_pk(post_data.get(f"{prefix}category", ""))
        material = clean_text(post_data.get(f"{prefix}material", ""))
        margin_percent = clean_percent(post_data.get(f"{prefix}margin_percent", ""))

        if not any(
            [code, name, quantity_raw, unit_cost_raw, sale_price_raw, category_id, material]
        ):
            continue

        try:
            quantity = parse_positive_int(quantity_raw, "Cantidad")
            unit_cost = parse_positive_int(unit_cost_raw, "Costo")
        except ValidationError as exc:
            errors.append(f"Fila {index + 1}: {exc.message}")
            continue

        sale_price = clean_price(sale_price_raw)
        if margin_percent is None and sale_price:
            margin_percent = calculate_margin_percent(unit_cost, sale_price)

        product = Product.objects.filter(code=code).first() if code else None
        if product:
            name = product.name
            category = product.category
            if not sale_price:
                sale_price = product.sale_price
            if margin_percent is None:
                margin_percent = product.margin_percent
            if not material:
                material = product.material
        else:
            if code:
                errors.append(
                    f"Fila {index + 1}: el código {code} no existe. "
                    "Dejá el código vacío para crear un producto nuevo."
                )
                continue
            if not name:
                errors.append(
                    f"Fila {index + 1}: el nombre es obligatorio para productos nuevos."
                )
                continue
            category = (
                Category.objects.filter(pk=category_id).first()
                if category_id is not None
                else None
            )
            if category is None:
                errors.append(
                    f"Fila {index + 1}: la categoría es obligatoria para productos nuevos."
                )
                continue

        lines.append(
            {
                "code": code,
                "product": product,
                "product_name": name,
                "quantity": quantity,
                "unit_cost": unit_cost,
                "sale_price": sale_price,
                "category": category,
                "material": material,
                "margin_percent": margin_percent,
            }
        )

    if not lines:
        errors.append("Agregá al menos una línea de compra.")

    return lines, errors


def new_purchase_view(request):
    if not request.user.has_perm("catalog.add_purchaseorder"):
        raise PermissionDenied

    categories = Category.objects.all()
    suppliers = Supplier.objects.all()
    context = {
        **admin.site.each_context(request),
        "title": "Nueva compra",
        "categories": categories,
        "suppliers": suppliers,
        "today": timezone.localdate().isoformat(),
        "opts": PurchaseOrder._meta,
    }

    if request.method == "POST":
        supplier_id = parse_optional_pk(request.POST.get("supplier"))
        supplier = (
            Supplier.objects.filter(pk=supplier_id).first()
            if supplier_id is not None
            else None
        )
        date = request.POST.get("date") or timezone.localdate()
        invoice_number = clean_text(request.POST.get("invoice_number", ""))
        notes = clean_text(request.POST.get("notes", ""))
        lines, errors = build_purchase_lines(request.POST)

        if supplier is None:
            errors.append("Seleccioná un proveedor.")

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, "admin/catalog/purchase/new.html", context)

        existing_slugs = set(Product.objects.values_list("slug", flat=True))
        created_count = 0
        updated_count = 0

        with transaction.atomic():
            order = PurchaseOrder.objects.create(
                supplier=supplier,
                date=date,
                invoice_number=invoice_number,
                notes=notes,
                created_by=request.user,
            )

            for line in lines:
                product = line["product"]
                line_product = product

                if product:
                    Product.objects.filter(pk=product.pk).update(
                        stock=F("stock") + line["quantity"]
                    )
                    updated_count += 1
                else:
                    slug = unique_slug(line["product_name"], existing_slugs)
                    line_product = Product.objects.create(
                        name=line["product_name"],
                        slug=slug,
                        category=line["category"],
                        supplier=supplier,
                        material=line["material"],
                        cost_price=line["unit_cost"],
                        margin_percent=line["margin_percent"],
                        sale_price=line["sale_price"]
                        or (
                            calculate_sale_price(
                                line["unit_cost"],
                                line["margin_percent"],
                            )
                            if line["margin_percent"] is not None
                            else 0
                        ),
                        stock=line["quantity"],
                        status=Product.Status.ACTIVE,
                    )
                    created_count += 1

                PurchaseOrderLine.objects.create(
                    order=order,
                    product=line_product,
                    product_name=line["product_name"],
                    quantity=line["quantity"],
                    unit_cost=line["unit_cost"],
                    category=line["category"],
                    material=line["material"],
                    margin_percent=line["margin_percent"],
                )

        messages.success(
            request,
            f"Compra confirmada: {updated_count} producto(s) actualizados, "
            f"{created_count} producto(s) nuevos.",
        )
        return redirect(reverse("admin:catalog_purchaseorder_change", args=[order.pk]))

    return render(request, "admin/catalog/purchase/new.html", context)


class ProductAdminForm(forms.ModelForm):
    cost_price = forms.CharField(label="Costo", required=True)
    wholesale_cost = forms.CharField(label="Costo mayorista", required=False)
    sale_price = forms.CharField(label="Precio de venta", required=True)
    price_sync_source = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Product
        fields = "__all__"
        widgets = {
            "cost_price": forms.TextInput(attrs={"inputmode": "numeric"}),
            "wholesale_cost": forms.TextInput(attrs={"inputmode": "numeric"}),
            "sale_price": forms.TextInput(attrs={"inputmode": "numeric"}),
        }

    def _clean_numeric_string(self, value, *, allow_empty=False):
        digits = re.sub(r"\D+", "", value or "")
        if not digits:
            if allow_empty:
                return None
            raise forms.ValidationError("Este campo es obligatorio.")
        return int(digits)

    def clean_cost_price(self):
        return self._clean_numeric_string(self.cleaned_data.get("cost_price"))

    def clean_wholesale_cost(self):
        return self._clean_numeric_string(
            self.cleaned_data.get("wholesale_cost"),
            allow_empty=True,
        )

    def clean_sale_price(self):
        return self._clean_numeric_string(self.cleaned_data.get("sale_price"))

    def clean(self):
        cleaned_data = super().clean()
        cost_price = cleaned_data.get("cost_price")
        margin_percent = cleaned_data.get("margin_percent")
        sale_price = cleaned_data.get("sale_price")
        sync_source = cleaned_data.get("price_sync_source")

        if not cost_price:
            return cleaned_data

        if sync_source == "sale_price" and sale_price is not None:
            cleaned_data["margin_percent"] = calculate_margin_percent(
                cost_price,
                sale_price,
            )
        elif margin_percent is not None:
            cleaned_data["sale_price"] = calculate_sale_price(
                cost_price,
                margin_percent,
            )
        elif sale_price is not None:
            cleaned_data["margin_percent"] = calculate_margin_percent(
                cost_price,
                sale_price,
            )

        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.initial["cost_price"] = format_guarani(self.instance.cost_price)
            self.initial["wholesale_cost"] = format_guarani(
                self.instance.wholesale_cost
            )
            self.initial["sale_price"] = format_guarani(self.instance.sale_price)


admin.site.site_header = "Mamiru Ops"
admin.site.site_title = "Mamiru Ops"
admin.site.index_title = "Panel de administración"


admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


@admin.register(Supplier)
class SupplierAdmin(ModelAdmin):
    list_display = ["name", "contact_name", "whatsapp", "country"]
    search_fields = ["name", "contact_name"]


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ["name", "slug"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}


class ProductImageInline(TabularInline):
    model = ProductImage
    extra = 1
    fields = ["image", "is_main", "sort_order"]
    tab = True


class PriceHistoryInline(TabularInline):
    model = PriceHistory
    extra = 0
    can_delete = False
    fields = [
        "changed_at",
        "changed_by",
        "old_cost_price",
        "new_cost_price",
        "old_sale_price",
        "new_sale_price",
        "old_margin_percent",
        "new_margin_percent",
    ]
    readonly_fields = fields
    tab = True
    verbose_name = "Historial de precio"
    verbose_name_plural = "Historial de precios"

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class StockLevelFilter(admin.SimpleListFilter):
    title = "Stock"
    parameter_name = "stock_level"

    def lookups(self, request, model_admin):
        return [
            ("low", "Stock bajo (<5)"),
            ("out", "Sin stock"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "low":
            return queryset.filter(stock__gt=0, stock__lt=5)
        if self.value() == "out":
            return queryset.filter(stock=0)
        return queryset


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    form = ProductAdminForm
    list_display = [
        "code",
        "name",
        "stock",
        "sale_price",
        "cost_price",
        "margin_percent",
        "supplier",
        "category",
        "status",
    ]
    list_filter = [StockLevelFilter, "category", "supplier", "status"]
    list_per_page = 25
    ordering = ["code", "name"]
    search_fields = ["code", "name"]
    actions = ["mark_as_active", "mark_as_sold_out", "mark_as_hidden"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductImageInline, PriceHistoryInline]
    readonly_fields = ["code", "created_at", "updated_at"]
    fieldsets = [
        (
            "Identificación",
            {
                "fields": ["code", "name", "slug", "status"],
                "description": "El código se genera automáticamente al guardar.",
            },
        ),
        (
            "Clasificación",
            {
                "fields": ["category", "supplier", "material", "product_type"],
            },
        ),
        (
            "Precios y stock",
            {
                "fields": [
                    "cost_price",
                    "wholesale_cost",
                    "margin_percent",
                    "sale_price",
                    "price_sync_source",
                    "stock",
                ],
            },
        ),
        (
            "Notas",
            {
                "fields": ["notes"],
            },
        ),
        (
            "Fechas",
            {
                "fields": ["created_at", "updated_at"],
                "classes": ["collapse"],
            },
        ),
    ]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related("category", "supplier")

    def save_model(self, request, obj, form, change):
        with price_history_user(request.user):
            super().save_model(request, obj, form, change)

    @admin.action(description="Marcar seleccionados como Activo")
    def mark_as_active(self, request, queryset):
        updated = queryset.update(status=Product.Status.ACTIVE)
        self.message_user(
            request,
            f"{updated} producto(s) actualizado(s) a Activo.",
            level=messages.SUCCESS,
        )

    @admin.action(description="Marcar seleccionados como Sin stock")
    def mark_as_sold_out(self, request, queryset):
        updated = queryset.update(status=Product.Status.SOLD_OUT)
        self.message_user(
            request,
            f"{updated} producto(s) actualizado(s) a Sin stock.",
            level=messages.SUCCESS,
        )

    @admin.action(description="Marcar seleccionados como Oculto")
    def mark_as_hidden(self, request, queryset):
        updated = queryset.update(status=Product.Status.HIDDEN)
        self.message_user(
            request,
            f"{updated} producto(s) actualizado(s) a Oculto.",
            level=messages.SUCCESS,
        )

    class Media:
        js = ["catalog/js/product_price_format.js"]


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(ModelAdmin):
    list_display = [
        "id",
        "supplier",
        "invoice_number",
        "date",
        "line_count",
        "created_by",
        "created_at",
    ]
    list_filter = ["supplier", "date"]
    search_fields = [
        "invoice_number",
        "supplier__name",
        "lines__product_name",
        "lines__product__code",
    ]
    readonly_fields = ["created_by", "created_at", "line_summary"]
    fieldsets = [
        (
            "Compra",
            {
                "fields": ["supplier", "invoice_number", "date", "notes"],
            },
        ),
        (
            "Auditoría",
            {
                "fields": ["created_by", "created_at"],
                "classes": ["collapse"],
            },
        ),
        (
            "Líneas de compra",
            {
                "fields": ["line_summary"],
            },
        ),
    ]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related("supplier", "created_by").prefetch_related(
            "lines"
        )

    @admin.display(description="Líneas")
    def line_count(self, obj):
        return obj.lines.count()

    @admin.display(description="Resumen de líneas")
    def line_summary(self, obj):
        if not obj or not obj.pk:
            return "Guardá la compra para ver sus líneas."

        lines = list(
            obj.lines.select_related("product", "category").order_by("id")
        )
        if not lines:
            return "Sin líneas."

        total_units = sum(line.quantity for line in lines)
        total_cost = sum(line.quantity * line.unit_cost for line in lines)

        def product_code_link(line):
            if not line.product:
                return "Nuevo"

            return format_html(
                '<a href="{}">{}</a>',
                reverse("admin:catalog_product_change", args=[line.product_id]),
                line.product.code,
            )

        rows = format_html_join(
            "",
            """
            <tr>
              <td>{}</td>
              <td>{}</td>
              <td class="po-num">{}</td>
              <td class="po-num">{}</td>
              <td>{}</td>
              <td>{}</td>
              <td class="po-num">{}</td>
            </tr>
            """,
            (
                (
                    product_code_link(line),
                    line.product_name,
                    line.quantity,
                    format_guarani(line.unit_cost),
                    line.category.name if line.category else "-",
                    line.material or "-",
                    line.margin_percent if line.margin_percent is not None else "-",
                )
                for line in lines
            ),
        )

        return format_html(
            """
            <style>
              .po-summary-table {{
                border: 1px solid #d8dee8;
                border-collapse: collapse;
                border-radius: 8px;
                overflow: hidden;
                width: 100%;
              }}
              .po-summary-table th,
              .po-summary-table td {{
                border-bottom: 1px solid #e5e7eb;
                padding: 10px 12px;
                text-align: left;
              }}
              .po-summary-table th {{
                background: #f8fafc;
                color: #374151;
                font-weight: 700;
              }}
              .po-summary-table tr:nth-child(even) td {{
                background: rgba(148, 163, 184, 0.04);
              }}
              .po-summary-table tr:last-child td {{
                border-bottom: 0;
              }}
              .po-num {{
                font-variant-numeric: tabular-nums;
                text-align: right !important;
              }}
              .po-summary-total {{
                display: flex;
                gap: 18px;
                justify-content: flex-end;
                margin-top: 12px;
              }}
            </style>
            <table class="po-summary-table">
              <thead>
                <tr>
                  <th>Código</th>
                  <th>Producto</th>
                  <th class="po-num">Qty</th>
                  <th class="po-num">Costo unit.</th>
                  <th>Categoría</th>
                  <th>Material</th>
                  <th class="po-num">Margen %</th>
                </tr>
              </thead>
              <tbody>{}</tbody>
            </table>
            <div class="po-summary-total">
              <strong>Unidades: {}</strong>
              <strong>Total costo: {}</strong>
            </div>
            """,
            rows,
            total_units,
            format_guarani(total_cost),
        )

    def has_add_permission(self, request):
        return request.user.has_perm("catalog.add_purchaseorder")

    def add_view(self, request, form_url="", extra_context=None):
        return redirect("admin:catalog_purchase_new")


_admin_get_urls = admin.site.get_urls


def get_admin_urls():
    custom_urls = [
        path(
            "catalog/purchase/new/",
            admin.site.admin_view(new_purchase_view),
            name="catalog_purchase_new",
        ),
        path(
            "catalog/product/lookup/",
            admin.site.admin_view(product_lookup_view),
            name="catalog_product_lookup",
        ),
        path(
            "catalog/product/search/",
            admin.site.admin_view(product_search_view),
            name="catalog_product_search",
        ),
    ]
    return custom_urls + _admin_get_urls()


admin.site.get_urls = get_admin_urls
