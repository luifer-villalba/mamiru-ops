import re

from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from django import forms
from unfold.admin import ModelAdmin, TabularInline
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from .models import Category, Product, ProductImage, Supplier


def format_guarani(value):
    if value in (None, ""):
        return ""
    return f"₲ {int(value):,}".replace(",", ".")


class ProductAdminForm(forms.ModelForm):
    cost_price = forms.CharField(label="Costo", required=True)
    wholesale_cost = forms.CharField(label="Costo mayorista", required=False)
    sale_price = forms.CharField(label="Precio de venta", required=True)

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.initial["cost_price"] = format_guarani(self.instance.cost_price)
            self.initial["wholesale_cost"] = format_guarani(self.instance.wholesale_cost)
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
        "category",
        "supplier",
        "formatted_sale_price",
        "stock",
        "status",
    ]
    list_filter = [StockLevelFilter, "category", "supplier", "status"]
    ordering = ["code", "name"]
    search_fields = ["code", "name"]
    actions = ["mark_as_active", "mark_as_sold_out", "mark_as_hidden"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductImageInline]
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

    @admin.display(description="Precio de venta", ordering="sale_price")
    def formatted_sale_price(self, obj):
        value = f"{obj.sale_price:,}".replace(",", ".")
        return f"₲ {value}"

    @admin.action(description="Marcar seleccionados como Activo")
    def mark_as_active(self, request, queryset):
        updated = queryset.update(status=Product.Status.ACTIVE)
        self.message_user(request, f"{updated} producto(s) actualizado(s) a Activo.", level=messages.SUCCESS)

    @admin.action(description="Marcar seleccionados como Sin stock")
    def mark_as_sold_out(self, request, queryset):
        updated = queryset.update(status=Product.Status.SOLD_OUT)
        self.message_user(request, f"{updated} producto(s) actualizado(s) a Sin stock.", level=messages.SUCCESS)

    @admin.action(description="Marcar seleccionados como Oculto")
    def mark_as_hidden(self, request, queryset):
        updated = queryset.update(status=Product.Status.HIDDEN)
        self.message_user(request, f"{updated} producto(s) actualizado(s) a Oculto.", level=messages.SUCCESS)

    class Media:
        js = ["catalog/js/product_price_format.js"]
