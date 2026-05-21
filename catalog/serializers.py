from rest_framework import serializers

from .models import Category, Product, ProductImage, Supplier


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ["id", "name", "contact_name", "whatsapp", "country", "notes"]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "is_main", "sort_order"]


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    supplier = SupplierSerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "code",
            "name",
            "slug",
            "category",
            "supplier",
            "material",
            "product_type",
            "cost_price",
            "wholesale_cost",
            "margin_percent",
            "sale_price",
            "stock",
            "status",
            "images",
            "created_at",
            "updated_at",
        ]
