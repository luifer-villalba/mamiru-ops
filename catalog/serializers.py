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
            "classification",
            "cost_price",
            "wholesale_cost",
            "margin_percent",
            "sale_price",
            "stock",
            "status",
            "short_description",
            "description",
            "detailed_material",
            "color",
            "finish",
            "measurements",
            "care_instructions",
            "is_water_resistant",
            "is_hypoallergenic",
            "visible_on_web",
            "is_featured",
            "display_priority",
            "public_tags",
            "seo_title",
            "seo_description",
            "images",
            "created_at",
            "updated_at",
        ]
