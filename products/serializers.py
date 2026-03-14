from rest_framework import serializers
from .models import Category, Product, ProductInfo, Parameter, ProductParameter
from shops.models import Shop


class ParameterSerializer(serializers.ModelSerializer):
    """
    Сериализатор для параметров
    """

    class Meta:
        model = Parameter
        fields = ['id', 'name']


class ProductParameterSerializer(serializers.ModelSerializer):
    """
    Сериализатор для значений параметров товара
    """
    parameter_name = serializers.CharField(source='parameter.name', read_only=True)

    class Meta:
        model = ProductParameter
        fields = ['id', 'parameter_name', 'value']


class ProductInfoSerializer(serializers.ModelSerializer):
    """
    Сериализатор для информации о товаре в магазине
    """
    shop_name = serializers.CharField(source='shop.name', read_only=True)
    parameters = ProductParameterSerializer(
        source='product_parameters',
        many=True,
        read_only=True
    )

    class Meta:
        model = ProductInfo
        fields = [
            'id', 'shop_name', 'model', 'quantity',
            'price', 'price_rrc', 'parameters'
        ]


class ProductSerializer(serializers.ModelSerializer):
    """
    Сериализатор для товара
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    offers = ProductInfoSerializer(
        source='product_infos',
        many=True,
        read_only=True
    )

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'category', 'category_name', 'offers'
        ]


class CategorySerializer(serializers.ModelSerializer):
    """
    Сериализатор для категорий
    """
    products_count = serializers.IntegerField(
        source='products.count',
        read_only=True
    )

    class Meta:
        model = Category
        fields = ['id', 'name', 'products_count']


class ShopSerializer(serializers.ModelSerializer):
    """
    Сериализатор для магазинов
    """
    categories = CategorySerializer(many=True, read_only=True)

    class Meta:
        model = Shop
        fields = ['id', 'name', 'state', 'categories']