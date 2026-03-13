from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from .models import Product, ProductInfo
from shops.models import Shop


class ProductListView(APIView):
    """
    Просмотр списка товаров
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        products = Product.objects.all()
        result = []
        for product in products:
            product_infos = ProductInfo.objects.filter(product=product)
            result.append({
                'id': product.id,
                'name': product.name,
                'category': product.category.name if product.category else None,
                'offers': [
                    {
                        'shop': info.shop.name,
                        'price': info.price,
                        'price_rrc': info.price_rrc,
                        'quantity': info.quantity,
                        'parameters': [
                            {
                                'name': param.parameter.name,
                                'value': param.value
                            } for param in info.product_parameters.all()
                        ]
                    } for info in product_infos
                ]
            })
        return JsonResponse({'products': result}, safe=False)


class ShopListView(APIView):
    """
    Просмотр списка магазинов
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        shops = Shop.objects.filter(state=True)
        result = [
            {
                'id': shop.id,
                'name': shop.name,
                'url': shop.url,
                'categories': [
                    {
                        'id': cat.id,
                        'name': cat.name
                    } for cat in shop.categories.all()
                ]
            } for shop in shops
        ]
        return JsonResponse({'shops': result}, safe=False)