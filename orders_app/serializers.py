from rest_framework import serializers
from .models import Contact, Order, OrderItem, STATE_CHOICES
from products.models import ProductInfo
from products.serializers import ProductInfoSerializer


class ContactSerializer(serializers.ModelSerializer):
    """
    Сериализатор для контактов
    """
    full_address = serializers.CharField(read_only=True)

    class Meta:
        model = Contact
        fields = ['id', 'city', 'street', 'house', 'structure',
                  'building', 'apartment', 'phone', 'full_address']
        read_only_fields = ['id']


class OrderItemSerializer(serializers.ModelSerializer):
    """
    Сериализатор для позиций заказа
    """
    product_name = serializers.CharField(source='product_info.product.name', read_only=True)
    shop_name = serializers.CharField(source='product_info.shop.name', read_only=True)
    price = serializers.DecimalField(source='product_info.price', max_digits=10, decimal_places=2, read_only=True)
    price_at_order = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total = serializers.DecimalField(source='total_price', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product_info', 'product_name', 'shop_name',
                  'quantity', 'price', 'price_at_order', 'total']
        read_only_fields = ['id', 'price_at_order']


class OrderItemCreateSerializer(serializers.Serializer):
    """
    Сериализатор для создания позиции заказа
    """
    product_info_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)


class OrderSerializer(serializers.ModelSerializer):
    """
    Сериализатор для заказов
    """
    items = OrderItemSerializer(many=True, read_only=True)
    contact = ContactSerializer(read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_quantity = serializers.IntegerField(read_only=True)
    order_number = serializers.CharField(read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'order_number', 'user', 'user_email', 'dt', 'state',
                  'contact', 'items', 'total_price', 'total_quantity']
        read_only_fields = ['id', 'user', 'dt']


class OrderCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания/обновления заказа
    """
    items = OrderItemCreateSerializer(many=True, required=False)
    contact_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Order
        fields = ['id', 'contact_id', 'items']

    def validate_items(self, value):
        """Валидация списка товаров"""
        if not value:
            return value

        for item in value:
            product_info_id = item.get('product_info_id')
            try:
                product_info = ProductInfo.objects.get(id=product_info_id)
                if product_info.quantity < item.get('quantity', 1):
                    raise serializers.ValidationError(
                        f"Недостаточно товара {product_info.product.name}. "
                        f"Доступно: {product_info.quantity}"
                    )
            except ProductInfo.DoesNotExist:
                raise serializers.ValidationError(
                    f"Товар с id {product_info_id} не существует"
                )
        return value

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        contact_id = validated_data.pop('contact_id', None)

        #Создаем заказ
        order = Order.objects.create(
            user=self.context['request'].user,
            state='basket',
            **validated_data
        )

        #Добавляем товары
        self._add_items_to_order(order, items_data)

        #Если указан контакт, привязываем его
        if contact_id:
            self._set_contact(order, contact_id)

        return order

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        contact_id = validated_data.pop('contact_id', None)

        #Обновляем основные поля
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        #Обновляем контакт если указан
        if contact_id:
            self._set_contact(instance, contact_id)

        instance.save()

        #Если переданы товары - обновляем их
        if items_data is not None:
            # Удаляем старые позиции
            instance.items.all().delete()
            # Создаем новые
            self._add_items_to_order(instance, items_data)

        return instance

    def _add_items_to_order(self, order, items_data):
        """Вспомогательный метод для добавления товаров в заказ"""
        for item_data in items_data:
            product_info_id = item_data.get('product_info_id')
            quantity = item_data.get('quantity', 1)

            product_info = ProductInfo.objects.get(id=product_info_id)
            OrderItem.objects.create(
                order=order,
                product_info=product_info,
                quantity=quantity
            )

    def _set_contact(self, order, contact_id):
        """Вспомогательный метод для установки контакта"""
        try:
            contact = Contact.objects.get(id=contact_id, user=order.user)
            order.contact = contact
        except Contact.DoesNotExist:
            raise serializers.ValidationError({"contact_id": "Контакт не найден"})


class OrderConfirmSerializer(serializers.Serializer):
    """
    Сериализатор для подтверждения заказа
    """
    contact_id = serializers.IntegerField(required=True)

    def validate_contact_id(self, value):
        """Проверка, что контакт принадлежит пользователю"""
        user = self.context['request'].user
        try:
            Contact.objects.get(id=value, user=user)
        except Contact.DoesNotExist:
            raise serializers.ValidationError("Контакт не найден")
        return value


class OrderStatusUpdateSerializer(serializers.Serializer):
    """
    Сериализатор для обновления статуса заказа
    """
    state = serializers.ChoiceField(choices=STATE_CHOICES)

    def validate_state(self, value):
        """Дополнительная валидация статуса"""
        order = self.context['order']

        # Проверка переходов статусов
        allowed_transitions = {
            'new': ['confirmed', 'canceled'],
            'confirmed': ['assembled', 'canceled'],
            'assembled': ['sent', 'canceled'],
            'sent': ['delivered', 'canceled'],
            'delivered': [],
            'canceled': [],
            'basket': ['new'],
        }

        if order.state in allowed_transitions:
            if value not in allowed_transitions[order.state]:
                raise serializers.ValidationError(
                    f"Нельзя перейти из статуса '{order.state}' в '{value}'"
                )

        return value