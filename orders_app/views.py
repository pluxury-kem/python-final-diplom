from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from .models import Order, Contact
from .serializers import (
    OrderSerializer, OrderCreateSerializer,
    ContactSerializer
)


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
            serializer.save(user=request.user)
            return JsonResponse({
                'Status': True,
                'contact': serializer.data
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
        # Ищем корзину пользователя
        basket = Order.objects.filter(
            user=request.user,
            state='basket'
        ).first()

        if not basket:
            return JsonResponse({
                'Status': True,
                'basket': {'items': []}
            })

        serializer = OrderSerializer(basket)
        return JsonResponse({
            'Status': True,
            'basket': serializer.data
        })

    def post(self, request):
        """Добавление товара в корзину"""
        # Получаем или создаем корзину
        basket, created = Order.objects.get_or_create(
            user=request.user,
            state='basket'
        )

        #Используем сериализатор для добавления товаров
        serializer = OrderCreateSerializer(
            basket,
            data=request.data,
            context={'request': request},
            partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return JsonResponse({
                'Status': True,
                'basket': serializer.data
            })

        return JsonResponse({
            'Status': False,
            'Errors': serializer.errors
        }, status=400)

    def delete(self, request):
        """Удаление товара из корзины"""
        basket = Order.objects.filter(
            user=request.user,
            state='basket'
        ).first()

        if not basket:
            return JsonResponse({
                'Status': False,
                'Error': 'Корзина пуста'
            }, status=404)

        item_id = request.data.get('item_id')
        if item_id:
            #Удаляем конкретную позицию
            basket.items.filter(id=item_id).delete()
        else:
            #Очищаем всю корзину
            basket.items.all().delete()

        serializer = OrderSerializer(basket)
        return JsonResponse({
            'Status': True,
            'basket': serializer.data
        })


class OrderConfirmView(APIView):
    """
    API для подтверждения заказа
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Подтверждение заказа и отправка email"""
        #Получаем корзину
        basket = Order.objects.filter(
            user=request.user,
            state='basket'
        ).first()

        if not basket:
            return JsonResponse({
                'Status': False,
                'Error': 'Корзина пуста'
            }, status=400)

        if basket.items.count() == 0:
            return JsonResponse({
                'Status': False,
                'Error': 'Нет товаров в корзине'
            }, status=400)

        contact_id = request.data.get('contact_id')
        if not contact_id:
            return JsonResponse({
                'Status': False,
                'Error': 'Не указан контакт для доставки'
            }, status=400)

        try:
            contact = Contact.objects.get(id=contact_id, user=request.user)
        except Contact.DoesNotExist:
            return JsonResponse({
                'Status': False,
                'Error': 'Контакт не найден'
            }, status=404)

        #Обновляем заказ
        basket.state = 'new'
        basket.contact = contact
        basket.save()

        #Формируем email для подтверждения
        order_items = basket.items.all()
        items_list = "\n".join([
            f"- {item.product_info.product.name}: {item.quantity} шт. "
            f"по {item.product_info.price} руб."
            for item in order_items
        ])

        total = sum(
            item.product_info.price * item.quantity
            for item in order_items
        )

        email_subject = f"Заказ №{basket.id} подтвержден"
        email_message = (
            f"Ваш заказ №{basket.id} подтвержден.\n\n"
            f"Состав заказа:\n{items_list}\n\n"
            f"Сумма заказа: {total} руб.\n"
            f"Адрес доставки: {contact}\n"
            f"Телефон: {contact.phone}\n\n"
            f"Статус заказа можно отслеживать в личном кабинете."
        )

        #Отправляем email
        try:
            send_mail(
                email_subject,
                email_message,
                settings.EMAIL_HOST_USER or 'noreply@shop.local',
                [request.user.email],
                fail_silently=False,
            )
        except Exception as e:
            # Логируем ошибку, но не прерываем процесс
            print(f"Ошибка отправки email: {e}")

        #Возвращаем информацию о созданном заказе
        serializer = OrderSerializer(basket)
        return JsonResponse({
            'Status': True,
            'Message': 'Заказ успешно оформлен',
            'order': serializer.data
        })


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
        ).exclude(state='basket')

        serializer = OrderSerializer(orders, many=True)
        return JsonResponse({
            'Status': True,
            'orders': serializer.data
        })