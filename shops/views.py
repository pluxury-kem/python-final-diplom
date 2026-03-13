from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
import yaml
from yaml.loader import SafeLoader
import requests

from shops.models import Shop
from products.models import Category, Product, ProductInfo, Parameter, ProductParameter


class PartnerUpdate(APIView):
    """
    Класс для обновления прайса от поставщика
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def post(self, request, *args, **kwargs):
        """
        Обновление прайса от поставщика
        Ожидает JSON с полем url, указывающим на YAML файл с прайс-листом
        """
        #Проверяем, что пользователь авторизован
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': "Требуется авторизация"}, status=403)

        #Проверяем, что пользователь является поставщиком
        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': "Только для магазинов"}, status=403)

        #Получаем URL из запроса
        url = request.data.get('url')
        if not url:
            return JsonResponse({'Status': False, 'Errors': "Не указан URL файла"}, status=400)

        #Валидируем URL
        validate_url = URLValidator()
        try:
            validate_url(url)
        except ValidationError as e:
            return JsonResponse({'Status': False, 'Error': str(e)}, status=400)

        try:
            #Загружаем файл по URL
            stream = requests.get(url).content

            #Парсим YAML
            data = yaml.load(stream, Loader=SafeLoader)

            if not data:
                return JsonResponse({'Status': False, 'Error': "Пустой файл"}, status=400)

            #Получаем или создаем магазин
            shop, _ = Shop.objects.get_or_create(
                name=data['shop'],
                user=request.user
            )

            #Обрабатываем категории
            for category in data['categories']:
                category_object, _ = Category.objects.get_or_create(
                    id=category['id'],
                    defaults={'name': category['name']}
                )
                category_object.name = category['name']  #Обновляем название на случай изменения
                category_object.save()
                category_object.shops.add(shop)

            #Удаляем старую информацию о товарах этого магазина
            ProductInfo.objects.filter(shop=shop).delete()

            #Обрабатываем товары
            for item in data['goods']:
                #Получаем или создаем товар
                product, _ = Product.objects.get_or_create(
                    name=item['name'],
                    category_id=item['category']
                )

                #Создаем информацию о товаре для данного магазина
                product_info = ProductInfo.objects.create(
                    product=product,
                    external_id=item['id'],
                    model=item.get('model', ''),
                    price=item['price'],
                    price_rrc=item['price_rrc'],
                    quantity=item['quantity'],
                    shop=shop
                )

                #Обрабатываем параметры товара
                for param_name, param_value in item['parameters'].items():
                    parameter_object, _ = Parameter.objects.get_or_create(name=param_name)
                    ProductParameter.objects.create(
                        product_info=product_info,
                        parameter=parameter_object,
                        value=param_value
                    )

            return JsonResponse({
                'Status': True,
                'Message': f"Прайс успешно обновлен. Добавлено товаров: {len(data['goods'])}"
            })

        except requests.exceptions.RequestException as e:
            return JsonResponse({'Status': False, 'Error': f"Ошибка загрузки файла: {str(e)}"}, status=400)
        except yaml.YAMLError as e:
            return JsonResponse({'Status': False, 'Error': f"Ошибка парсинга YAML: {str(e)}"}, status=400)
        except KeyError as e:
            return JsonResponse({'Status': False, 'Error': f"Отсутствует обязательное поле в файле: {str(e)}"}, status=400)
        except Exception as e:
            return JsonResponse({'Status': False, 'Error': f"Неизвестная ошибка: {str(e)}"}, status=500)