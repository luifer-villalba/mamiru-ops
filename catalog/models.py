from django.db import models
from django.utils.text import slugify


class Supplier(models.Model):
    name = models.CharField(max_length=200, unique=True)
    contact_name = models.CharField(max_length=200, blank=True)
    whatsapp = models.CharField(max_length=50, blank=True)
    country = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Borrador"
        ACTIVE = "active", "Activo"
        SOLD_OUT = "sold_out", "Sin Stock"
        HIDDEN = "hidden", "Oculto"

    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=300)
    slug = models.SlugField(max_length=300, unique=True)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products"
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT, related_name="products"
    )
    material = models.CharField(max_length=200, blank=True)
    product_type = models.CharField(max_length=200, blank=True)
    cost_price = models.PositiveIntegerField(default=0)
    wholesale_cost = models.PositiveIntegerField(null=True, blank=True)
    margin_percent = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    sale_price = models.PositiveIntegerField(default=0)
    stock = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

    def __str__(self):
        return f"[{self.code}] {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="products/")
    is_main = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Imagen de producto"
        verbose_name_plural = "Imágenes de producto"

    def __str__(self):
        return f"Imagen de {self.product.name} ({self.id})"
