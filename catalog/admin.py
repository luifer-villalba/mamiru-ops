from django.contrib import admin

from .models import Category, Product, ProductImage, Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ["name", "contact_name", "whatsapp", "country"]
    search_fields = ["name", "contact_name"]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ["image", "is_main", "sort_order"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "category", "supplier", "sale_price", "stock", "status"]
    list_filter = ["category", "supplier", "status"]
    search_fields = ["code", "name"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductImageInline]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = [
        (
            "Identificación",
            {
                "fields": ["code", "name", "slug", "status"],
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
