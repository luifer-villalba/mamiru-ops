from django.db import models
from django.utils.text import slugify


class Supplier(models.Model):
    name = models.CharField("Nombre", max_length=200, unique=True)
    contact_name = models.CharField("Nombre de contacto", max_length=200, blank=True)
    whatsapp = models.CharField("WhatsApp", max_length=50, blank=True)
    country = models.CharField("País", max_length=100, blank=True)
    notes = models.TextField("Notas", blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField("Nombre", max_length=200, unique=True)
    slug = models.SlugField("Slug", max_length=200, unique=True)

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
        SOLD_OUT = "sold_out", "Sin stock"
        HIDDEN = "hidden", "Oculto"

    code = models.CharField("Código", max_length=50, unique=True, blank=True)
    name = models.CharField("Nombre", max_length=300)
    slug = models.SlugField("Slug", max_length=300, unique=True)
    category = models.ForeignKey(
        Category,
        verbose_name="Categoría",
        on_delete=models.PROTECT,
        related_name="products",
    )
    supplier = models.ForeignKey(
        Supplier,
        verbose_name="Proveedor",
        on_delete=models.PROTECT,
        related_name="products",
    )
    material = models.CharField("Material", max_length=200, blank=True)
    product_type = models.CharField("Tipo de producto", max_length=200, blank=True)
    cost_price = models.PositiveIntegerField("Costo", default=0)
    wholesale_cost = models.PositiveIntegerField(
        "Costo mayorista", null=True, blank=True
    )
    margin_percent = models.DecimalField(
        "Margen %",
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )
    sale_price = models.PositiveIntegerField("Precio de venta", default=0)
    stock = models.PositiveIntegerField("Stock", default=0)
    status = models.CharField(
        "Estado",
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    notes = models.TextField("Notas", blank=True)
    created_at = models.DateTimeField("Creado", auto_now_add=True)
    updated_at = models.DateTimeField("Actualizado", auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

    def __str__(self):
        return f"[{self.code}] {self.name}"

    @classmethod
    def generate_code(cls) -> str:
        last_code = (
            cls.objects.filter(code__startswith="MAM-")
            .order_by("-code")
            .values_list("code", flat=True)
            .first()
        )
        if not last_code:
            return "MAM-0001"

        try:
            next_number = int(last_code.split("-")[1]) + 1
        except (IndexError, ValueError):
            next_number = cls.objects.filter(code__startswith="MAM-").count() + 1

        code = f"MAM-{next_number:04d}"
        while cls.objects.filter(code=code).exists():
            next_number += 1
            code = f"MAM-{next_number:04d}"
        return code

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.generate_code()

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
        Product,
        verbose_name="Producto",
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField("Imagen", upload_to="products/")
    is_main = models.BooleanField("Imagen principal", default=False)
    sort_order = models.PositiveIntegerField("Orden", default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Imagen de producto"
        verbose_name_plural = "Imágenes de producto"

    def __str__(self):
        return f"Imagen de {self.product.name} ({self.id})"
