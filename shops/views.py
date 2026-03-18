from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from .serializers import PartnerUpdateSerializer
import yaml
import logging
from yaml.loader import SafeLoader
import requests

from shops.models import Shop
from products.models import Category, Product, ProductInfo, Parameter, ProductParameter

logger = logging.getLogger(__name__)


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
        #Проверяем права доступа
        if not request.user.is_authenticated:
            return JsonResponse({
                'Status': False,
                'Error': "Требуется авторизация"
            }, status=403)

        if request.user.type != 'shop':
            return JsonResponse({
                'Status': False,
                'Error': "Только для магазинов"
            }, status=403)

        #Валидация входных данных
        serializer = PartnerUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return JsonResponse({
                'Status': False,
                'Errors': serializer.errors
            }, status=400)

        url = serializer.validated_data['url']

        try:
            #Загружаем файл по URL с таймаутом
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            #Проверяем размер файла (не больше 10 мб)
            if len(response.content) > 10 * 1024 * 1024:
                return JsonResponse({
                    'Status': False,
                    'Error': "Файл слишком большой (максимум 10 МБ)"
                }, status=400)

            #Парсим YAML
            try:
                data = yaml.load(response.content, Loader=SafeLoader)
            except yaml.YAMLError as e:
                logger.error(f"Ошибка парсинга YAML: {e}")
                return JsonResponse({
                    'Status': False,
                    'Error': f"Ошибка парсинга YAML: {str(e)}"
                }, status=400)

            if not data:
                return JsonResponse({
                    'Status': False,
                    'Error': "Пустой файл"
                }, status=400)

            #Валидация структуры данных
            required_keys = ['shop', 'categories', 'goods']
            missing_keys = [key for key in required_keys if key not in data]
            if missing_keys:
                return JsonResponse({
                    'Status': False,
                    'Error': f"Отсутствуют обязательные поля: {missing_keys}"
                }, status=400)

            #Используем транзакцию для атомарности
            with transaction.atomic():
                #Получаем или создаем магазин
                shop, created = Shop.objects.get_or_create(
                    name=data['shop'],
                    defaults={'user': request.user}
                )

                #Если магазин уже существует, проверяем принадлежность
                if not created and shop.user != request.user:
                    return JsonResponse({
                        'Status': False,
                        'Error': "Магазин с таким именем уже принадлежит другому пользователю"
                    }, status=400)

                #Обновляем URL магазина
                shop.url = url
                shop.save()

                #Обработка категорий
                categories_processed = []
                for category_data in data['categories']:
                    if 'id' not in category_data or 'name' not in category_data:
                        continue

                    category, _ = Category.objects.update_or_create(
                        id=category_data['id'],
                        defaults={'name': category_data['name']}
                    )
                    category.shops.add(shop)
                    categories_processed.append(category.id)

                #Удаляем связи с категориями, которых нет в новом файле
                shop.categories.exclude(id__in=categories_processed).remove(shop)

                #Обработка товаров
                goods_processed = []
                errors = []

                for item in data['goods']:
                    try:
                        #Валидация обязательных полей товара
                        required_item_keys = ['id', 'category', 'name', 'price', 'quantity']
                        missing_item_keys = [key for key in required_item_keys if key not in item]
                        if missing_item_keys:
                            errors.append(f"Товар пропущен: отсутствуют поля {missing_item_keys}")
                            continue

                        #Проверяем существование категории
                        if not Category.objects.filter(id=item['category']).exists():
                            errors.append(f"Товар '{item['name']}' пропущен: категория {item['category']} не найдена")
                            continue

                        #Аолучаем или создаем товар
                        product, _ = Product.objects.get_or_create(
                            name=item['name'],
                            defaults={'category_id': item['category']}
                        )

                        #Если товар уже существовал, обновляем категорию
                        if product.category_id != item['category']:
                            product.category_id = item['category']
                            product.save()

                        #Создаем или обновляем информацию о товаре
                        product_info, created = ProductInfo.objects.update_or_create(
                            external_id=item['id'],
                            shop=shop,
                            defaults={
                                'product': product,
                                'model': item.get('model', ''),
                                'price': item['price'],
                                'price_rrc': item.get('price_rrc', item['price']),
                                'quantity': item['quantity']
                            }
                        )

                        #Обработка параметров товара
                        if 'parameters' in item and isinstance(item['parameters'], dict):
                            #Удаляем старые параметры
                            ProductParameter.objects.filter(product_info=product_info).delete()

                            #Создаем новые параметры
                            for param_name, param_value in item['parameters'].items():
                                parameter, _ = Parameter.objects.get_or_create(name=param_name)
                                ProductParameter.objects.create(
                                    product_info=product_info,
                                    parameter=parameter,
                                    value=str(param_value)
                                )

                        goods_processed.append(item['id'])

                    except Exception as e:
                        errors.append(f"Ошибка обработки товара {item.get('name', 'unknown')}: {str(e)}")
                        logger.error(f"Ошибка импорта товара: {e}", exc_info=True)

                #Удаляем товары, которых нет в новом файле (если нужно)
                ProductInfo.objects.filter(shop=shop).exclude(
                    external_id__in=goods_processed
                ).delete()

                #Формируем результат
                result = {
                    'Status': True,
                    'Message': f'Импорт завершен. Обработано товаров: {len(goods_processed)}',
                    'Details': {
                        'shop': shop.name,
                        'categories_processed': len(categories_processed),
                        'goods_processed': len(goods_processed)
                    }
                }

                if errors:
                    result['Warnings'] = errors
                    result['Message'] += f" с {len(errors)} предупреждениями"

                logger.info(f"Импорт успешно завершен для магазина {shop.name}")
                return JsonResponse(result)

        except requests.exceptions.Timeout:
            logger.error("Таймаут при загрузке файла")
            return JsonResponse({
                'Status': False,
                'Error': 'Превышено время ожидания при загрузке файла'
            }, status=408)

        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка загрузки файла: {e}")
            return JsonResponse({
                'Status': False,
                'Error': f'Ошибка загрузки файла: {str(e)}'
            }, status=400)

        except yaml.YAMLError as e:
            logger.error(f"Ошибка парсинга YAML: {e}")
            return JsonResponse({
                'Status': False,
                'Error': f'Ошибка парсинга YAML: {str(e)}'
            }, status=400)

        except KeyError as e:
            logger.error(f"Отсутствует обязательное поле: {e}")
            return JsonResponse({
                'Status': False,
                'Error': f'Отсутствует обязательное поле в файле: {str(e)}'
            }, status=400)

        except Exception as e:
            logger.error(f"Неизвестная ошибка: {e}", exc_info=True)
            return JsonResponse({
                'Status': False,
                'Error': f'Неизвестная ошибка: {str(e)}'
            }, status=500)