import requests
import json
import sys
from pprint import pprint

#Базовый URL API
BASE_URL = "http://127.0.0.1:8000/api/v1"


#Цвета для вывода
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    END = '\033[0m'


def print_step(step_num, description):
    print(f"\n{Colors.BLUE}=== Шаг {step_num}: {description} ==={Colors.END}\n")


def print_success(message):
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")


def print_error(message):
    print(f"{Colors.RED}✗ {message}{Colors.END}")


def print_info(message):
    print(f"{Colors.YELLOW}ℹ {message}{Colors.END}")


def run_full_scenario():
    """
    Полный сценарий тестирования:
    1. Регистрация нового пользователя
    2. Подтверждение email
    3. Авторизация и получение токена
    4. Импорт товаров от поставщика
    5. Добавление товаров в корзину
    6. Создание контакта
    7. Подтверждение заказа
    8. Проверка списка заказов
    """

    print(f"{Colors.BLUE}{'=' * 60}{Colors.END}")
    print(f"{Colors.BLUE}ТЕСТИРОВАНИЕ ПОЛНОГО СЦЕНАРИЯ РАБОТЫ{Colors.END}")
    print(f"{Colors.BLUE}{'=' * 60}{Colors.END}")

    #Данные для тестирования
    test_user = {
        "email": "test_buyer@example.com",
        "password": "TestPass123!",
        "password2": "TestPass123!",
        "first_name": "Иван",
        "last_name": "Петров",
        "type": "buyer"
    }

    test_shop_user = {
        "email": "test_shop@example.com",
        "password": "ShopPass123!",
        "password2": "ShopPass123!",
        "first_name": "Магазин",
        "last_name": "Тестовый",
        "type": "shop"
    }

    test_contact = {
        "city": "Москва",
        "street": "Ленина",
        "house": "10",
        "apartment": "42",
        "phone": "+79991234567"
    }

    #Шаг 1: Регистрация покупателя
    print_step(1, "Регистрация нового покупателя")

    response = requests.post(
        f"{BASE_URL}/users/register/",
        json=test_user
    )

    if response.status_code == 201:
        print_success("Покупатель успешно зарегистрирован")
        print_info(f"Email для подтверждения отправлен на {test_user['email']}")
        pprint(response.json())
    else:
        print_error("Ошибка регистрации")
        pprint(response.json())
        return False

    #Шаг 2: Регистрация поставщика (для импорта товаров)
    print_step(2, "Регистрация поставщика")

    response = requests.post(
        f"{BASE_URL}/users/register/",
        json=test_shop_user
    )

    if response.status_code == 201:
        print_success("Поставщик успешно зарегистрирован")
    else:
        print_error("Ошибка регистрации поставщика")
        pprint(response.json())
        return False

    print_info("  ВАЖНО: Сейчас нужно подтвердить email пользователей")
    print_info("1. Откройте консоль, где запущен Django сервер")
    print_info("2. Найдите там токены подтверждения для обоих пользователей")
    print_info("3. Скопируйте токены и введите их ниже")

    input("\nНажмите Enter, когда будете готовы продолжить...")

    #Шаг 3: Подтверждение email покупателя
    print_step(3, "Подтверждение email покупателя")

    token_buyer = input("Введите токен подтверждения для покупателя: ").strip()

    response = requests.post(
        f"{BASE_URL}/users/confirm/",
        json={"token": token_buyer}
    )

    if response.status_code == 200:
        print_success("Email покупателя подтвержден")
    else:
        print_error("Ошибка подтверждения email")
        pprint(response.json())
        return False

    #Шаг 4: Подтверждение email поставщика
    print_step(4, "Подтверждение email поставщика")

    token_shop = input("Введите токен подтверждения для поставщика: ").strip()

    response = requests.post(
        f"{BASE_URL}/users/confirm/",
        json={"token": token_shop}
    )

    if response.status_code == 200:
        print_success("Email поставщика подтвержден")
    else:
        print_error("Ошибка подтверждения email")
        pprint(response.json())
        return False

    #Шаг 5: Авторизация покупателя
    print_step(5, "Авторизация покупателя")

    response = requests.post(
        f"{BASE_URL}/users/login/",
        json={
            "email": test_user["email"],
            "password": test_user["password"]
        }
    )

    if response.status_code == 200:
        data = response.json()
        user_token = data.get('Token')
        print_success("Успешная авторизация покупателя")
        print_info(f"Токен: {user_token[:20]}...")
    else:
        print_error("Ошибка авторизации")
        pprint(response.json())
        return False

    #Шаг 6: Авторизация поставщика
    print_step(6, "Авторизация поставщика")

    response = requests.post(
        f"{BASE_URL}/users/login/",
        json={
            "email": test_shop_user["email"],
            "password": test_shop_user["password"]
        }
    )

    if response.status_code == 200:
        data = response.json()
        shop_token = data.get('Token')
        print_success("Успешная авторизация поставщика")
        print_info(f"Токен: {shop_token[:20]}...")
    else:
        print_error("Ошибка авторизации поставщика")
        pprint(response.json())
        return False

    #Шаг 7: Импорт товаров поставщиком
    print_step(7, "Импорт товаров поставщиком")

    #URL с тестовым прайс-листом (можно использовать локальный файл)
    #Для теста используем ранее созданный example_shop.yaml
    price_url = "http://127.0.0.1:8000/media/example_shop.yaml"  # или ваш URL

    print_info("Для импорта нужно загрузить YAML файл на какой-либо хостинг")
    print_info("Или можно использовать локальный файл через тестовый сервер")

    custom_url = input("Введите URL с YAML прайс-листом (или нажмите Enter для пропуска): ").strip()

    if custom_url:
        response = requests.post(
            f"{BASE_URL}/shops/partner/update/",
            headers={"Authorization": f"Token {shop_token}"},
            json={"url": custom_url}
        )

        if response.status_code == 200:
            print_success("Товары успешно импортированы")
            pprint(response.json())
        else:
            print_error("Ошибка импорта товаров")
            pprint(response.json())
            print_info("Продолжаем тестирование с существующими товарами...")
    else:
        print_info("Импорт пропущен. Используем существующие товары в БД")

    #Шаг 8: Просмотр списка товаров
    print_step(8, "Просмотр списка товаров")

    response = requests.get(f"{BASE_URL}/products/")

    if response.status_code == 200:
        data = response.json()
        products = data.get('products', [])
        print_success(f"Получен список товаров. Всего: {len(products)}")
        if products:
            print_info("Первые 3 товара:")
            for i, product in enumerate(products[:3]):
                print(f"  {i + 1}. {product.get('name')} - {len(product.get('offers', []))} предложений")
    else:
        print_error("Ошибка получения списка товаров")
        pprint(response.json())

    #Шаг 9: Добавление товаров в корзину
    print_step(9, "Добавление товаров в корзину")

    #Получаем ID товаров для добавления
    response = requests.get(f"{BASE_URL}/products/")
    if response.status_code == 200:
        data = response.json()
        products = data.get('products', [])

        if products and len(products) >= 2:
            # Берем первые два товара
            product1 = products[0]
            product2 = products[1]

            #Получаем ID product_info для первого товара
            if product1.get('offers'):
                product_info_id1 = product1['offers'][0]['id']

                #Добавляем первый товар
                response = requests.post(
                    f"{BASE_URL}/orders/basket/",
                    headers={"Authorization": f"Token {user_token}"},
                    json={
                        "items": [
                            {"product_info_id": product_info_id1, "quantity": 2}
                        ]
                    }
                )

                if response.status_code == 200:
                    print_success(f"Товар '{product1['name']}' добавлен в корзину (2 шт)")
                else:
                    print_error("Ошибка добавления первого товара")

            #Добавляем второй товар
            if product2.get('offers'):
                product_info_id2 = product2['offers'][0]['id']

                response = requests.post(
                    f"{BASE_URL}/orders/basket/",
                    headers={"Authorization": f"Token {user_token}"},
                    json={
                        "items": [
                            {"product_info_id": product_info_id2, "quantity": 1}
                        ]
                    }
                )

                if response.status_code == 200:
                    print_success(f"Товар '{product2['name']}' добавлен в корзину (1 шт)")
                else:
                    print_error("Ошибка добавления второго товара")
        else:
            print_error("Недостаточно товаров в БД для тестирования")

    #Шаг 10: Просмотр корзины
    print_step(10, "Просмотр корзины")

    response = requests.get(
        f"{BASE_URL}/orders/basket/",
        headers={"Authorization": f"Token {user_token}"}
    )

    if response.status_code == 200:
        data = response.json()
        basket = data.get('basket', {})
        items = basket.get('items', [])
        print_success(f"Корзина содержит {len(items)} позиций")

        total = 0
        for item in items:
            price = item.get('price', 0)
            quantity = item.get('quantity', 0)
            item_total = price * quantity
            total += item_total
            print(f"  - {item.get('product_name')}: {quantity} x {price} = {item_total} руб.")

        print_info(f"Общая сумма: {total} руб.")
    else:
        print_error("Ошибка получения корзины")
        pprint(response.json())

    #Шаг 11: Создание контакта
    print_step(11, "Создание контакта (адреса доставки)")

    response = requests.post(
        f"{BASE_URL}/orders/contacts/",
        headers={"Authorization": f"Token {user_token}"},
        json=test_contact
    )

    if response.status_code == 201:
        data = response.json()
        contact_id = data.get('contact', {}).get('id')
        print_success("Контакт успешно создан")
        print_info(f"ID контакта: {contact_id}")
        print_info(f"Адрес: {test_contact['city']}, {test_contact['street']} {test_contact['house']}")
    else:
        print_error("Ошибка создания контакта")
        pprint(response.json())
        return False

    #Шаг 12: Подтверждение заказа
    print_step(12, "Подтверждение заказа")

    response = requests.post(
        f"{BASE_URL}/orders/order/confirm/",
        headers={"Authorization": f"Token {user_token}"},
        json={"contact_id": contact_id}
    )

    if response.status_code == 200:
        data = response.json()
        print_success("Заказ успешно подтвержден")
        print_info("Email с подтверждением отправлен на почту пользователя")
        order = data.get('order', {})
        print_info(f"Номер заказа: {order.get('id')}")
        print_info(f"Сумма заказа: {order.get('total_price')} руб.")
    else:
        print_error("Ошибка подтверждения заказа")
        pprint(response.json())

    #Шаг 13: Получение списка заказов
    print_step(13, "Получение списка заказов")

    response = requests.get(
        f"{BASE_URL}/orders/orders/",
        headers={"Authorization": f"Token {user_token}"}
    )

    if response.status_code == 200:
        data = response.json()
        orders = data.get('orders', [])
        print_success(f"Получен список заказов. Всего заказов: {len(orders)}")

        for order in orders:
            print(f"\n  Заказ №{order.get('id')}:")
            print(f"    Дата: {order.get('dt')}")
            print(f"    Статус: {order.get('state')}")
            print(f"    Сумма: {order.get('total_price')} руб.")
            print(f"    Товаров: {len(order.get('items', []))}")
    else:
        print_error("Ошибка получения списка заказов")
        pprint(response.json())

    #Шаг 14: Проверка email в консоли
    print_step(14, "Проверка email-уведомлений")
    print_info("Проверьте консоль, где запущен Django сервер")
    print_info("Там должны быть два email:")
    print_info("1. Email с подтверждением регистрации (был в начале)")
    print_info("2. Email с подтверждением заказа (только что)")

    print(f"\n{Colors.GREEN}{'=' * 60}{Colors.END}")
    print(f"{Colors.GREEN}ТЕСТИРОВАНИЕ ЗАВЕРШЕНО{Colors.END}")
    print(f"{Colors.GREEN}{'=' * 60}{Colors.END}")

    return True


if __name__ == "__main__":
    #Проверяем, что сервер запущен
    try:
        response = requests.get(f"{BASE_URL}/products/")
        if response.status_code == 200:
            run_full_scenario()
        else:
            print_error("Сервер недоступен. Запустите сервер командой:")
            print_info("python manage.py runserver")
    except requests.exceptions.ConnectionError:
        print_error("Не удалось подключиться к серверу. Убедитесь, что сервер запущен:")
        print_info("python manage.py runserver")