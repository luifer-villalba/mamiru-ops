from urllib.parse import urljoin
from xml.etree import ElementTree

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from .models import Category, Product, Supplier
from .serializers import CategorySerializer, ProductSerializer, SupplierSerializer


def _absolute_public_url(request, path: str) -> str:
    base_url = settings.PUBLIC_SITE_URL or request.build_absolute_uri("/")
    return urljoin(f"{base_url.rstrip('/')}/", path.lstrip("/"))


def _product_share_image_url(request, product: Product) -> str:
    images = list(product.images.all())
    image = next((image for image in images if image.is_main), None)
    if image is None:
        image = next(iter(images), None)
    if image is None or not image.image:
        return ""

    try:
        return _absolute_public_url(request, image.image.url)
    except ValueError:
        return ""


def robots_txt(request):
    sitemap_url = _absolute_public_url(request, "/sitemap.xml")
    body = "\n".join(
        [
            "User-agent: *",
            "Disallow: /admin/",
            "Disallow: /api/",
            f"Sitemap: {sitemap_url}",
            "",
        ]
    )
    return HttpResponse(body, content_type="text/plain; charset=utf-8")


def sitemap_xml(request):
    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ElementTree.register_namespace("", namespace)
    urlset = ElementTree.Element(f"{{{namespace}}}urlset")

    categories = Category.objects.filter(
        products__status=Product.Status.ACTIVE,
        products__visible_on_web=True,
    ).distinct()
    products = Product.objects.filter(
        status=Product.Status.ACTIVE,
        visible_on_web=True,
    ).order_by("-updated_at")

    for category in categories:
        url = ElementTree.SubElement(urlset, f"{{{namespace}}}url")
        ElementTree.SubElement(url, f"{{{namespace}}}loc").text = _absolute_public_url(
            request, category.get_absolute_url()
        )
        ElementTree.SubElement(url, f"{{{namespace}}}changefreq").text = "weekly"

    for product in products:
        url = ElementTree.SubElement(urlset, f"{{{namespace}}}url")
        ElementTree.SubElement(url, f"{{{namespace}}}loc").text = _absolute_public_url(
            request, product.get_absolute_url()
        )
        ElementTree.SubElement(url, f"{{{namespace}}}lastmod").text = (
            product.updated_at.date().isoformat()
        )
        ElementTree.SubElement(url, f"{{{namespace}}}changefreq").text = "weekly"

    xml = ElementTree.tostring(urlset, encoding="unicode", xml_declaration=True)
    return HttpResponse(xml, content_type="application/xml; charset=utf-8")


def product_meta_preview(request, slug: str):
    product = get_object_or_404(
        Product.objects.select_related("category", "supplier").prefetch_related(
            "images"
        ),
        slug=slug,
        status=Product.Status.ACTIVE,
        visible_on_web=True,
    )
    canonical_url = _absolute_public_url(request, product.get_absolute_url())
    image_url = _product_share_image_url(request, product)
    return render(
        request,
        "catalog/product_meta_preview.html",
        {
            "product": product,
            "meta_title": product.meta_title,
            "meta_description": product.meta_description,
            "canonical_url": canonical_url,
            "image_url": image_url,
        },
    )


def category_meta_preview(request, slug: str):
    category = get_object_or_404(
        Category.objects.filter(
            products__status=Product.Status.ACTIVE,
            products__visible_on_web=True,
        ).distinct(),
        slug=slug,
    )
    canonical_url = _absolute_public_url(request, category.get_absolute_url())
    return render(
        request,
        "catalog/category_meta_preview.html",
        {
            "category": category,
            "meta_title": f"{category.name} | Mamiru",
            "meta_description": f"Productos de {category.name} disponibles en Mamiru.",
            "canonical_url": canonical_url,
        },
    )


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.select_related("category", "supplier").prefetch_related(
        "images"
    )
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"


class SupplierViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [AllowAny]
