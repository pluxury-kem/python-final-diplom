from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import TokenAuthentication
from .models import Order, Contact, OrderItem
from .serializers import (
    OrderSerializer, OrderCreateSerializer, ContactSerializer,
    OrderConfirmSerializer, OrderStatusUpdateSerializer
)
from products.models import ProductInfo

User = get_user_model()


class ContactView(APIView):
    """
    API для работы с контактами пользователя
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Получение списка контактов пользователя"""
        contacts = Contact.objects.filter(user=request.user)
        serializer = ContactSerializer(contacts, many=True)
        return JsonResponse({
            'Status': True,
            'contacts': serializer.data
        })

    def post(self, request):
        """Добавление нового контакта"""
        serializer = ContactSerializer(data=request.data)
        if serializer.is_valid():
            contact = serializer.save(user=request.user)
            return JsonResponse({
                'Status': True,
                'contact': ContactSerializer(contact).data
            }, status=201)
        return JsonResponse({
            'Status': False,
            'Errors': serializer.errors
        }, status=400)

    def delete(self, request):
        """Удаление контакта"""
        contact_id = request.data.get('id')
        if not contact_id:
            return JsonResponse({
                'Status': False,
                'Error': 'Не указан ID контакта'
            }, status=400)

        try:
            contact = Contact.objects.get(id=contact_id, user=request.user)
            contact.delete()
            return JsonResponse({'Status': True})
        except Contact.DoesNotExist:
            return JsonResponse({
                'Status': False,
                'Error': 'Контакт не найден'
            }, status=404)


class BasketView(APIView):
    """
    API для работы с корзиной
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Просмотр корзины"""
        basket = self._get_or_create_basket(request.user)
        serializer = OrderSerializer(basket)
        return JsonResponse({
            'Status': True,
            'basket': serializer.data
        })

    def post(self, request):
        """Добавление товара в корзину"""
        basket = self._get_or_create_basket(request.user)

        serializer = OrderCreateSerializer(
            basket,
            data=request.data,
            context={'request': request},
            partial=True
        )

        if serializer.is_valid():
            with transaction.atomic():
                order = serializer.save()

            #Возвращаем обновленную корзину
            result_serializer = OrderSerializer(order)
            return JsonResponse({
                'Status': True,
                'basket': result_serializer.data
            })

        return JsonResponse({
            'Status': False,
            'Errors': serializer.errors
        }, status=400)

    def delete(self, request):
        """Удаление товара из корзины"""
        basket = self._get_or_create_basket(request.user)

        item_id = request.data.get('item_id')
        if item_id:
            #Удаляем конкретную позицию
            try:
                item = basket.items.get(id=item_id)
                item.delete()
                message = "Товар удален из корзины"
            except OrderItem.DoesNotExist:
                return JsonResponse({
                    'Status': False,
                    'Error': 'Позиция не найдена'
                }, status=404)
        else:
            #Очищаем всю корзину
            basket.items.all().delete()
            message = "Корзина очищена"

        #Возвращаем обновленную корзину
        serializer = OrderSerializer(basket)
        return JsonResponse({
            'Status': True,
            'Message': message,
            'basket': serializer.data
        })

    def _get_or_create_basket(self, user):
        """Получить или создать корзину для пользователя"""
        basket, created = Order.objects.get_or_create(
            user=user,
            state='basket'
        )
        return basket


class OrderConfirmView(APIView):
    """
    API для подтверждения заказа
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Подтверждение заказа и отправка email"""
        basket = Order.objects.filter(
            user=request.user,
            state='basket'
        ).first()

        if not basket:
            return JsonResponse({
                'Status': False,
                'Error': 'Корзина не найдена'
            }, status=404)

        if basket.items.count() == 0:
            return JsonResponse({
                'Status': False,
                'Error': 'Корзина пуста'
            }, status=400)

        serializer = OrderConfirmSerializer(
            data=request.data,
            context={'request': request}
        )

        if not serializer.is_valid():
            return JsonResponse({
                'Status': False,
                'Errors': serializer.errors
            }, status=400)

        contact_id = serializer.validated_data['contact_id']

        try:
            with transaction.atomic():
                basket = Order.objects.select_for_update().get(
                    id=basket.id
                )

                if basket.state != 'basket':
                    return JsonResponse({
                        'Status': False,
                        'Error': 'Заказ уже оформлен'
                    }, status=400)

                contact = Contact.objects.select_for_update().get(
                    id=contact_id,
                    user=request.user
                )

                #Обновляем заказ
                basket.state = 'new'
                basket.contact = contact
                basket.save()

                #уменьшаем количество товаров на складе
                insufficient_goods = []
                for item in basket.items.all():
                    try:
                        product_info = ProductInfo.objects.select_for_update().get(
                            id=item.product_info.id
                        )

                        if product_info.quantity >= item.quantity:
                            product_info.quantity -= item.quantity
                            product_info.save()
                        else:
                            insufficient_goods.append(
                                f"{product_info.product.name} (доступно: {product_info.quantity}, "
                                f"запрошено: {item.quantity})"
                            )
                    except ProductInfo.DoesNotExist:
                        insufficient_goods.append(f"Товар ID {item.product_info.id} не найден")
                            #Если товара недостаточно, отменяем транзакцию

                if insufficient_goods:
                    raise Exception(f"Недостаточно товаров: {', '.join(insufficient_goods)}")

            #Отправляем email с подтверждением
            self._send_confirmation_email(request.user, basket, contact)

            #Отправляем email администратору
            self._send_admin_notification(basket)

            #Возвращаем информацию о созданном заказе
            result_serializer = OrderSerializer(basket)
            return JsonResponse({
                'Status': True,
                'Message': 'Заказ успешно оформлен',
                'order': result_serializer.data
            })

        except Contact.DoesNotExist:
            return JsonResponse({
                'Status': False,
                'Error': 'Контакт не найден'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'Status': False,
                'Error': str(e)
            }, status=400)

    def _send_admin_notification(self, order):
        """Отправка уведомления администратору о новом заказе"""
        #Получаем всех администраторов
        admins = User.objects.filter(is_staff=True, is_active=True)
        admin_emails = list(admins.values_list('email', flat=True))

        if not admin_emails:
            #Если нет администраторов, используем email из настроек
            admin_emails = [settings.ADMIN_EMAIL] if hasattr(settings, 'ADMIN_EMAIL') else []

        if not admin_emails:
            print("Нет email администраторов для уведомления")
            return

        items_list = []
        total_sum = 0

        for item in order.items.all():
            price = item.price_at_order or item.product_info.price
            item_sum = price * item.quantity
            total_sum += item_sum

            items_list.append(
                f"{item.product_info.product.name} "
                f"(магазин: {item.product_info.shop.name}) - "
                f"{item.quantity} шт. х {price} руб. = {item_sum} руб."
            )

        items_text = "\n".join(items_list)

        subject = f"Новый заказ №{order.order_number}"
        message = f"""
Уважаемый администратор!

Поступил новый заказ № {order.order_number}.

ИНФОРМАЦИЯ О ЗАКАЗЕ:
Номер заказа: {order.order_number}
Дата и время: {order.dt.strftime('%d.%m.%Y %H:%M')}
Покупатель: {order.user.email} ({order.user.first_name} {order.user.last_name})
Телефон: {order.contact.phone if order.contact else 'Не указан'}

АДРЕС ДОСТАВКИ:
{order.contact.full_address if order.contact else 'Не указан'}

СОСТАВ ЗАКАЗА:
{items_text}

ИТОГОВАЯ СУММА: {total_sum} руб.

Ссылка на заказ в админке:
{settings.SITE_URL}/admin/orders_app/order/{order.id}/

---
Это автоматическое уведомление. Пожалуйста, не отвечайте на него.
"""

        try:
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER or 'noreply@shop.example',
                admin_emails,
                fail_silently=False,
            )
            print(f"Уведомление отправлено администраторам: {admin_emails}")
        except Exception as e:
            print(f"Ошибка отправки email администратору {e}")

    def _send_confirmation_email(self, user, order, contact):
        """Отправка email с подтверждением заказа"""
        #Формируем список товаров
        items_list = []
        total_sum = 0

        for item in order.items.all():
            price = item.price_at_order or item.product_info.price
            item_sum = price * item.quantity
            total_sum += item_sum

            items_list.append(
                f"• {item.product_info.product.name} - {item.quantity} шт. × {price} руб. = {item_sum} руб."
            )

        items_text = "\n".join(items_list)

        subject = f"Заказ №{order.order_number} подтвержден"
        message = f"""
Здравствуйте, {user.first_name or user.email}!

Ваш заказ №{order.order_number} успешно оформлен и принят в обработку.

СОСТАВ ЗАКАЗА:
{items_text}

ИТОГО: {total_sum} руб.

АДРЕС ДОСТАВКИ:
{contact.full_address}
Телефон: {contact.phone}

СТАТУС ЗАКАЗА:
Вы можете отслеживать статус заказа в личном кабинете.

Спасибо за покупку!
"""

        try:
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER or 'noreply@shop.local',
                [user.email],
                fail_silently=False,
            )
        except Exception as e:
            #Логируем ошибку, но не прерываем процесс
            print(f"Ошибка отправки email: {e}")


class OrderListView(APIView):
    """
    API для просмотра списка заказов
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Получение списка заказов пользователя"""
        #Исключаем корзину из списка заказов
        orders = Order.objects.filter(
            user=request.user
        ).exclude(state='basket').prefetch_related(
            'items', 'items__product_info', 'items__product_info__product',
            'items__product_info__shop', 'contact'
        )

        serializer = OrderSerializer(orders, many=True)
        return JsonResponse({
            'Status': True,
            'count': orders.count(),
            'orders': serializer.data
        })


class OrderDetailView(APIView):
    """
    API для просмотра деталей заказа
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        """Получение детальной информации о заказе"""
        try:
            order = Order.objects.prefetch_related(
                'items', 'items__product_info', 'items__product_info__product',
                'items__product_info__shop', 'contact'
            ).get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return JsonResponse({
                'Status': False,
                'Error': 'Заказ не найден'
            }, status=404)

        serializer = OrderSerializer(order)
        return JsonResponse({
            'Status': True,
            'order': serializer.data
        })


class OrderStatusUpdateView(APIView):
    """
    API для обновления статуса заказа (для админки или поставщиков)
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        """Обновление статуса заказа"""
        #Проверяем права (только для магазинов или админов)
        if request.user.type != 'shop' and not request.user.is_staff:
            return JsonResponse({
                'Status': False,
                'Error': 'Недостаточно прав'
            }, status=403)

        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return JsonResponse({
                'Status': False,
                'Error': 'Заказ не найден'
            }, status=404)

        serializer = OrderStatusUpdateSerializer(
            data=request.data,
            context={'order': order}
        )

        if not serializer.is_valid():
            return JsonResponse({
                'Status': False,
                'Errors': serializer.errors
            }, status=400)

        old_state = order.state
        new_state = serializer.validated_data['state']

        order.state = new_state
        order.save()

        #Отправляем уведомление пользователю об изменении статуса
        self._send_status_email(order.user, order, old_state, new_state)

        return JsonResponse({
            'Status': True,
            'Message': f'Статус заказа изменен с "{old_state}" на "{new_state}"'
        })

    def _send_status_email(self, user, order, old_state, new_state):
        """Отправка уведомления об изменении статуса заказа"""
        state_names = dict(STATE_CHOICES)

        subject = f"Статус заказа №{order.order_number} изменен"
        message = f"""
Здравствуйте, {user.first_name or user.email}!

Статус вашего заказа №{order.order_number} изменен.

Было: {state_names.get(old_state, old_state)}
Стало: {state_names.get(new_state, new_state)}

Вы можете следить за статусом заказа в личном кабинете.
"""

        try:
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER or 'noreply@shop.local',
                [user.email],
                fail_silently=True,
            )
        except Exception as e:
            print(f"Ошибка отправки email: {e}")