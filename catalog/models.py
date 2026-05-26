from django.db import models
from django.utils import timezone
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

    class Classification(models.TextChoices):
        SIGNATURE = "A", "A / Signature"
        ESSENTIALS = "B", "B / Essentials"
        BIJOU = "C", "C / Bijou"

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
    classification = models.CharField(
        "Clasificación",
        max_length=1,
        choices=Classification.choices,
        default=Classification.ESSENTIALS,
    )
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
    sale_price = models.PositiveIntegerField("Precio", default=0)
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
        ordering = ["code", "name"]
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

    def __str__(self):
        return f"[{self.code}] {self.name}"

    @classmethod
    def generate_code(cls) -> str:
        year_prefix = timezone.now().strftime("%y")
        current_year_codes = cls.objects.filter(
            code__startswith=year_prefix
        ).values_list("code", flat=True)

        max_sequence = 0
        for existing_code in current_year_codes:
            if len(existing_code) == 6 and existing_code.isdigit():
                sequence = int(existing_code[2:])
                if sequence > max_sequence:
                    max_sequence = sequence

        next_number = max_sequence + 1
        code = f"{year_prefix}{next_number:04d}"
        while cls.objects.filter(code=code).exists():
            next_number += 1
            code = f"{year_prefix}{next_number:04d}"
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

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_main:
            ProductImage.objects.filter(product=self.product, is_main=True).exclude(
                pk=self.pk
            ).update(is_main=False)

    def delete(self, *args, **kwargs):
        image_name = self.image.name
        storage = self.image.storage if image_name else None

        result = super().delete(*args, **kwargs)

        if storage and image_name:
            try:
                if storage.exists(image_name):
                    storage.delete(image_name)
            except OSError:
                pass

        return result


class PriceHistory(models.Model):
    product = models.ForeignKey(
        Product,
        verbose_name="Producto",
        on_delete=models.CASCADE,
        related_name="price_history",
    )
    changed_by = models.ForeignKey(
        "auth.User",
        verbose_name="Cambiado por",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="price_history_entries",
    )
    changed_at = models.DateTimeField("Fecha", auto_now_add=True)
    old_cost_price = models.PositiveIntegerField("Costo anterior")
    new_cost_price = models.PositiveIntegerField("Costo nuevo")
    old_sale_price = models.PositiveIntegerField("Precio anterior")
    new_sale_price = models.PositiveIntegerField("Precio nuevo")
    old_margin_percent = models.DecimalField(
        "Margen anterior %",
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )
    new_margin_percent = models.DecimalField(
        "Margen nuevo %",
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-changed_at", "-id"]
        verbose_name = "Historial de precio"
        verbose_name_plural = "Historial de precios"

    def __str__(self):
        return f"{self.product} - {self.changed_at:%d/%m/%Y %H:%M}"


class Customer(models.Model):
    name = models.CharField("Nombre", max_length=200)
    whatsapp = models.CharField("WhatsApp", max_length=50, blank=True)
    city = models.CharField("Ciudad", max_length=100, blank=True)
    notes = models.TextField("Notas", blank=True)
    created_at = models.DateTimeField("Creado", auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"

    def __str__(self):
        return self.name


class Order(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Borrador"
        CONFIRMED = "confirmed", "Confirmado"
        DELIVERED = "delivered", "Entregado"
        CANCELLED = "cancelled", "Cancelado"

    customer = models.ForeignKey(
        Customer,
        verbose_name="Cliente",
        on_delete=models.PROTECT,
        related_name="orders",
    )
    date = models.DateField("Fecha", default=timezone.localdate)
    status = models.CharField(
        "Estado",
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    notes = models.TextField("Notas", blank=True)
    created_by = models.ForeignKey(
        "auth.User",
        verbose_name="Creado por",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customer_orders",
    )
    created_at = models.DateTimeField("Creado", auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"

    def __str__(self):
        return f"Pedido #{self.pk} - {self.customer} ({self.date:%d/%m/%Y})"

    @property
    def total(self):
        return sum(line.total for line in self.lines.all())

    def confirm_lines(self):
        for line in self.lines.select_related("product"):
            line.snapshot_product()
            line.save(update_fields=["product_name", "product_code", "unit_price"])

    def save(self, *args, **kwargs):
        was_confirmed = False
        if self.pk:
            previous_status = (
                Order.objects.filter(pk=self.pk)
                .values_list("status", flat=True)
                .first()
            )
            was_confirmed = previous_status == self.Status.CONFIRMED

        super().save(*args, **kwargs)

        if self.status == self.Status.CONFIRMED and not was_confirmed:
            self.confirm_lines()


class OrderLine(models.Model):
    order = models.ForeignKey(
        Order,
        verbose_name="Pedido",
        on_delete=models.CASCADE,
        related_name="lines",
    )
    product = models.ForeignKey(
        Product,
        verbose_name="Producto",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_lines",
    )
    product_name = models.CharField("Producto", max_length=300, blank=True)
    product_code = models.CharField("Código", max_length=50, blank=True)
    quantity = models.PositiveIntegerField("Cantidad")
    unit_price = models.PositiveIntegerField("Precio unitario", default=0)

    class Meta:
        ordering = ["id"]
        verbose_name = "Línea de pedido"
        verbose_name_plural = "Líneas de pedido"

    def __str__(self):
        return f"{self.product_name or self.product} x {self.quantity}"

    @property
    def effective_unit_price(self):
        if self.unit_price:
            return self.unit_price
        if self.product_id and self.product:
            return self.product.sale_price
        return 0

    @property
    def total(self):
        return self.quantity * self.effective_unit_price

    def snapshot_product(self):
        if not self.product:
            return
        self.product_name = self.product.name
        self.product_code = self.product.code
        self.unit_price = self.product.sale_price

    def save(self, *args, **kwargs):
        has_snapshot = self.product_name and self.product_code and self.unit_price
        if (
            self.order.status == Order.Status.CONFIRMED
            and self.product
            and not has_snapshot
        ):
            self.snapshot_product()
        super().save(*args, **kwargs)


class PurchaseOrder(models.Model):
    supplier = models.ForeignKey(
        Supplier,
        verbose_name="Proveedor",
        on_delete=models.PROTECT,
        related_name="purchase_orders",
    )
    date = models.DateField("Fecha", default=timezone.localdate)
    invoice_number = models.CharField(
        "Factura o comprobante nro.", max_length=80, blank=True
    )
    notes = models.TextField("Notas", blank=True)
    created_by = models.ForeignKey(
        "auth.User",
        verbose_name="Creado por",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchase_orders",
    )
    created_at = models.DateTimeField("Creado", auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        verbose_name = "Compra"
        verbose_name_plural = "Compras"

    def __str__(self):
        return f"Compra #{self.pk} - {self.supplier} ({self.date:%d/%m/%Y})"


class PurchaseOrderLine(models.Model):
    order = models.ForeignKey(
        PurchaseOrder,
        verbose_name="Compra",
        on_delete=models.CASCADE,
        related_name="lines",
    )
    product = models.ForeignKey(
        Product,
        verbose_name="Producto existente",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchase_lines",
    )
    product_name = models.CharField("Producto", max_length=300)
    quantity = models.PositiveIntegerField("Cantidad")
    unit_cost = models.PositiveIntegerField("Costo unitario")
    category = models.ForeignKey(
        Category,
        verbose_name="Categoría",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="purchase_lines",
    )
    material = models.CharField("Material", max_length=200, blank=True)
    margin_percent = models.DecimalField(
        "Margen %",
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["id"]
        verbose_name = "Línea de compra"
        verbose_name_plural = "Líneas de compra"

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"
