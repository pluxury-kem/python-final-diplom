# test_import_fixed.py

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from shops.models import Shop
from products.models import Product, Category, ProductInfo, Parameter, ProductParameter
from django.contrib.auth import get_user_model

User = get_user_model()


def clear_previous_imports(user):
    """Очистка предыдущих импортов для пользователя"""
    print("\nОчистка предыдущих данных...")

    # Удаляем магазины пользователя
    shops = Shop.objects.filter(user=user)
    for shop in shops:
        # Удаляем связанные товары
        ProductInfo.objects.filter(shop=shop).delete()
        # Удаляем магазин
        shop.delete()
        print(f"   ✓ Удален магазин: {shop.name}")

    # Очищаем категории без магазинов (опционально)
    empty_categories = Category.objects.filter(shops__isnull=True)
    count = empty_categories.count()
    empty_categories.delete()
    if count:
        print(f"   ✓ Удалено пустых категорий: {count}")


def import_from_yaml_file(yaml_file_path, user):
    """Импорт товаров из локального YAML файла"""
    print(f"\n2. Импортируем товары из файла: {yaml_file_path}")

    try:
        import yaml
        from yaml.loader import SafeLoader

        # Читаем YAML файл
        with open(yaml_file_path, 'r', encoding='utf-8') as file:
            data = yaml.load(file, Loader=SafeLoader)

        print(f"   ✓ YAML файл успешно загружен")
        print(f"   Название магазина: {data.get('shop')}")
        print(f"   Категорий: {len(data.get('categories', []))}")
        print(f"   Товаров: {len(data.get('goods', []))}")

        # Создаем магазин (без лишних полей)
        shop = Shop.objects.create(
            name=data['shop'],
            user=user,
            state=True
        )
        print(f"   ✓ Создан новый магазин: {shop.name} (ID: {shop.id})")

        # Обрабатываем категории
        categories_count = 0
        for category_data in data['categories']:
            # Создаем или получаем категорию
            category, created = Category.objects.get_or_create(
                id=category_data['id'],
                defaults={'name': category_data['name']}
            )
            if not created:
                category.name = category_data['name']
                category.save()

            # Добавляем магазин к категории
            category.shops.add(shop)
            categories_count += 1
            print(f"     ✓ Категория: {category.name}")

        print(f"   ✓ Добавлено категорий: {categories_count}")

        # Обрабатываем товары
        products_added = 0
        for item in data['goods']:
            # Получаем или создаем товар
            product, _ = Product.objects.get_or_create(
                name=item['name'],
                category_id=item['category']
            )

            # Создаем информацию о товаре
            product_info = ProductInfo.objects.create(
                product=product,
                external_id=item['id'],
                model=item.get('model', ''),
                price=item['price'],
                price_rrc=item['price_rrc'],
                quantity=item['quantity'],
                shop=shop
            )

            # Создаем параметры товара
            for param_name, param_value in item.get('parameters', {}).items():
                parameter, _ = Parameter.objects.get_or_create(name=param_name)
                ProductParameter.objects.create(
                    product_info=product_info,
                    parameter=parameter,
                    value=str(param_value)
                )

            products_added += 1
            if products_added <= 3:  # Показываем первые 3 товара для примера
                print(f"     ✓ Товар: {product.name} - {item['price']} руб.")

        print(f"   ✓ Добавлено товаров: {products_added}")
        return shop

    except FileNotFoundError:
        print(f"   ✗ Ошибка: Файл {yaml_file_path} не найден!")
        return None
    except KeyError as e:
        print(f"   ✗ Ошибка: Отсутствует обязательное поле в YAML: {e}")
        return None
    except Exception as e:
        print(f"   ✗ Ошибка при импорте: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None


def check_results(shop):
    """Проверка результатов импорта"""
    print("\n3. Проверяем результаты импорта:")

    if not shop:
        print("   ✗ Магазин не создан")
        return

    print(f"\n   Магазин: {shop.name}")

    # Категории магазина
    categories = shop.categories.all()
    print(f"   Категории ({categories.count()}):")
    for cat in categories:
        print(f"     - {cat.name}")

    # Товары в магазине
    products = ProductInfo.objects.filter(shop=shop).select_related('product')
    print(f"\n   Товары в магазине ({products.count()}):")

    for info in products:
        print(f"\n     • {info.product.name}")
        print(f"       Цена: {info.price} руб. (РРЦ: {info.price_rrc} руб.)")
        print(f"       Количество: {info.quantity} шт.")

        # Параметры товара
        params = ProductParameter.objects.filter(product_info=info).select_related('parameter')
        if params:
            print("       Параметры:")
            for param in params:
                print(f"         - {param.parameter.name}: {param.value}")


def main():
    """Главная функция тестирования"""
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ ИМПОРТА ТОВАРОВ")
    print("=" * 60)

    # Получаем или создаем пользователя
    user, created = User.objects.get_or_create(
        email='test_shop@example.com',
        defaults={
            'first_name': 'Тестовый',
            'last_name': 'Магазин',
            'type': 'shop',
            'is_active': True
        }
    )

    if created:
        user.set_password('testpass123')
        user.save()
        print(f"\n1. Создан новый пользователь: {user.email}")
    else:
        print(f"\n1. Используем существующего пользователя: {user.email}")

    # Очищаем предыдущие импорты (опционально - закомментируйте, если не нужно)
    clear_previous_imports(user)

    # Путь к YAML файлу
    yaml_file = "data/shop1.yaml"

    if not os.path.exists(yaml_file):
        print(f"\n! Ошибка: Файл {yaml_file} не найден!")
        print(f"Текущая директория: {os.getcwd()}")
        print("Файлы в текущей директории:")
        for f in os.listdir('.'):
            print(f"  - {f}")
        return

    print(f"\nНайден YAML файл: {os.path.abspath(yaml_file)}")

    # Выполняем импорт
    shop = import_from_yaml_file(yaml_file, user)

    if shop:
        # Проверяем результаты
        check_results(shop)
        print(f"\n✓ Импорт успешно завершен!")
    else:
        print(f"\n✗ Импорт не удался!")

    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 60)


if __name__ == "__main__":
    main()