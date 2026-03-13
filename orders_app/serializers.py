from rest_framework import serializers
from .models import Contact, Order, OrderItem
from products.models import ProductInfo


class ContactSerializer(serializers.ModelSerializer):
    """
    Сериализатор для контактов
    """

    class Meta:
        model = Contact
        fields = ['id', 'city', 'street', 'house', 'structure',
                  'building', 'apartment', 'phone']
        read_only_fields = ['id']


class OrderItemSerializer(serializers.ModelSerializer):
    """
    Сериализатор для позиций заказа
    """
    product_name = serializers.CharField(source='product_info.product.name', read_only=True)
    shop_name = serializers.CharField(source='product_info.shop.name', read_only=True)
    price = serializers.IntegerField(source='product_info.price', read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product_info', 'product_name', 'shop_name',
                  'price', 'quantity']
        read_only_fields = ['id']


class OrderSerializer(serializers.ModelSerializer):
    """
    Сериализатор для заказов
    """
    items = OrderItemSerializer(many=True, read_only=True)
    contact = ContactSerializer(read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'dt', 'state', 'contact', 'items', 'total_price']
        read_only_fields = ['id', 'dt']

    def get_total_price(self, obj):
        total = 0
        for item in obj.items.all():
            total += item.product_info.price * item.quantity
        return total


class OrderCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания/обновления заказа
    """
    items = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False
    )
    contact_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Order
        fields = ['id', 'contact_id', 'items']

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
        for item_data in items_data:
            product_info_id = item_data.get('product_info_id')
            quantity = item_data.get('quantity', 1)

            try:
                product_info = ProductInfo.objects.get(id=product_info_id)
                OrderItem.objects.create(
                    order=order,
                    product_info=product_info,
                    quantity=quantity
                )
            except ProductInfo.DoesNotExist:
                raise serializers.ValidationError(
                    f"Товар с id {product_info_id} не существует"
                )

        return order

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', [])
        contact_id = validated_data.pop('contact_id', None)

        #Обновляем основные поля
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        #Jбновляем контакт если указан
        if contact_id:
            try:
                contact = Contact.objects.get(id=contact_id, user=instance.user)
                instance.contact = contact
            except Contact.DoesNotExist:
                raise serializers.ValidationError("Контакт не найден")

        instance.save()

        #Если переданы товары - обновляем их
        if items_data:
            #Удаляем старые позиции
            instance.items.all().delete()

            #Создаем новые
            for item_data in items_data:
                product_info_id = item_data.get('product_info_id')
                quantity = item_data.get('quantity', 1)

                try:
                    product_info = ProductInfo.objects.get(id=product_info_id)
                    OrderItem.objects.create(
                        order=instance,
                        product_info=product_info,
                        quantity=quantity
                    )
                except ProductInfo.DoesNotExist:
                    raise serializers.ValidationError(
                        f"Товар с id {product_info_id} не существует"
                    )

        return instance