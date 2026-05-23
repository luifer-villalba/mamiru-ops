from django.db.models import Avg, Count, Q
from django.urls import reverse

from catalog.models import Product


def _format_guarani(value):
    return f"₲ {int(value):,}".replace(",", ".")


def admin_dashboard_callback(request, context):
    metrics = Product.objects.aggregate(
        total=Count("id"),
        out_of_stock=Count("id", filter=Q(stock=0)),
        low_stock=Count("id", filter=Q(stock__gt=0, stock__lt=5)),
        draft=Count("id", filter=Q(status=Product.Status.DRAFT)),
        avg_margin=Avg("margin_percent"),
    )

    changelist_url = reverse("admin:catalog_product_changelist")
    add_url = reverse("admin:catalog_product_add")
    avg_margin = metrics["avg_margin"] or 0

    context["dashboard_metrics"] = [
        {
            "title": "Productos",
            "value": metrics["total"],
            "description": "Total en catálogo",
            "url": changelist_url,
        },
        {
            "title": "Sin stock",
            "value": metrics["out_of_stock"],
            "description": "Productos con stock en 0",
            "url": f"{changelist_url}?stock_level=out",
        },
        {
            "title": "Stock bajo",
            "value": metrics["low_stock"],
            "description": "Productos con menos de 5 unidades",
            "url": f"{changelist_url}?stock_level=low",
        },
        {
            "title": "Margen promedio",
            "value": f"{avg_margin:.2f}%",
            "description": "Promedio actual de margen",
            "url": f"{changelist_url}?margin_percent__isnull=0",
        },
    ]
    context["product_changelist_url"] = changelist_url
    context["product_add_url"] = add_url
    context["dashboard_products"] = [
        {
            "code": product.code,
            "name": product.name,
            "category": product.category.name,
            "supplier": product.supplier.name,
            "stock": product.stock,
            "status": product.get_status_display(),
            "status_value": product.status,
            "price": _format_guarani(product.sale_price),
            "url": reverse("admin:catalog_product_change", args=[product.pk]),
        }
        for product in Product.objects.select_related("category", "supplier").order_by(
            "code", "name"
        )[:25]
    ]

    return context
