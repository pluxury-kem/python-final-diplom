from django.http import JsonResponse
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from django_filters.rest_framework import DjangoFilterBackend
from .models import Product, Category, ProductInfo
from .serializers import (
    ProductSerializer, CategorySerializer, ShopSerializer
)
from shops.models import Shop


class ProductListView(APIView):
    """
    Просмотр списка товаров с фильтрацией
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """
        Получение списка товаров
        Поддерживаемые параметры:
        - category_id: фильтр по категории
        - shop_id: фильтр по магазину
        - search: поиск по названию
        - min_price: минимальная цена
        - max_price: максимальная цена
        - ordering: сортировка (price, -price, name, -name)
        """
        # Базовый запрос
        products = Product.objects.all()

        # Фильтрация по категории
        category_id = request.GET.get('category_id')
        if category_id:
            products = products.filter(category_id=category_id)

        # Фильтрация по магазину
        shop_id = request.GET.get('shop_id')
        if shop_id:
            products = products.filter(
                product_infos__shop_id=shop_id
            ).distinct()

        # Поиск по названию
        search = request.GET.get('search')
        if search:
            products = products.filter(
                Q(name__icontains=search) |
                Q(product_infos__model__icontains=search)
            ).distinct()

        # Фильтрация по цене через ProductInfo
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        if min_price or max_price:
            # Находим товары, у которых есть предложения в указанном диапазоне цен
            product_ids = set()
            for product in products:
                infos = product.product_infos.all()
                if min_price:
                    infos = infos.filter(price__gte=min_price)
                if max_price:
                    infos = infos.filter(price__lte=max_price)
                if infos.exists():
                    product_ids.add(product.id)

            products = products.filter(id__in=product_ids)

        # Сортировка
        ordering = request.GET.get('ordering', 'name')
        if ordering.lstrip('-') in ['price', 'name']:
            if ordering == 'price':
                # Сортировка по минимальной цене среди предложений
                products = sorted(
                    products,
                    key=lambda p: min(
                        [info.price for info in p.product_infos.all()] or [0]
                    )
                )
                if ordering.startswith('-'):
                    products = reversed(products)
            else:
                products = products.order_by(ordering)
        else:
            products = products.order_by('name')

        # Сериализация
        serializer = ProductSerializer(products, many=True)

        return JsonResponse({
            'Status': True,
            'count': products.count() if isinstance(products, list) else products.count(),
            'products': serializer.data
        })


class ProductDetailView(APIView):
    """
    Просмотр детальной информации о товаре
    """
    permission_classes = [AllowAny]

    def get(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return JsonResponse({
                'Status': False,
                'Error': 'Товар не найден'
            }, status=404)

        serializer = ProductSerializer(product)
        return JsonResponse({
            'Status': True,
            'product': serializer.data
        })


class CategoryListView(APIView):
    """
    Просмотр списка категорий
    """
    permission_classes = [AllowAny]

    def get(self, request):
        categories = Category.objects.all()

        # Фильтр по магазину
        shop_id = request.GET.get('shop_id')
        if shop_id:
            categories = categories.filter(shops__id=shop_id)

        # Поиск по названию
        search = request.GET.get('search')
        if search:
            categories = categories.filter(name__icontains=search)

        serializer = CategorySerializer(categories, many=True)

        return JsonResponse({
            'Status': True,
            'categories': serializer.data
        })


class ShopListView(APIView):
    """
    Просмотр списка магазинов
    """
    permission_classes = [AllowAny]

    def get(self, request):
        shops = Shop.objects.filter(state=True)

        # Поиск по названию
        search = request.GET.get('search')
        if search:
            shops = shops.filter(name__icontains=search)

        serializer = ShopSerializer(shops, many=True)

        return JsonResponse({
            'Status': True,
            'shops': serializer.data
        })


class ProductByCategoryView(APIView):
    """
    Просмотр товаров по категории (с вложенностью)
    """
    permission_classes = [AllowAny]

    def get(self, request):
        categories = Category.objects.prefetch_related('products').all()

        result = []
        for category in categories:
            products = ProductSerializer(
                category.products.all(),
                many=True
            ).data

            result.append({
                'id': category.id,
                'name': category.name,
                'products': products
            })

        return JsonResponse({
            'Status': True,
            'categories': result
        })