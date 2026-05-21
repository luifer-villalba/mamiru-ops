from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from unfold.admin import ModelAdmin, TabularInline
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from .models import Category, Product, ProductImage, Supplier


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


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = [
        "code",
        "name",
        "category",
        "supplier",
        "sale_price",
        "stock",
        "status",
    ]
    list_filter = ["category", "supplier", "status"]
    search_fields = ["code", "name"]
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
