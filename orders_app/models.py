from django.db import models
from users.models import User
from products.models import ProductInfo

STATE_CHOICES = [
    ('basket', 'Корзина'),
    ('new', 'Новый'),
    ('confirmed', 'Подтвержден'),
    ('assembled', 'Собран'),
    ('sent', 'Отправлен'),
    ('delivered', 'Доставлен'),
    ('canceled', 'Отменен'),
]


class Contact(models.Model):
    """
    Контактная информация пользователя (адрес доставки)
    """
    user = models.ForeignKey(
        User,
        verbose_name='Пользователь',
        related_name='contacts',
        on_delete=models.CASCADE
    )
    city = models.CharField(max_length=50, verbose_name='Город')
    street = models.CharField(max_length=100, verbose_name='Улица')
    house = models.CharField(max_length=15, verbose_name='Дом')
    structure = models.CharField(max_length=15, verbose_name='Корпус', blank=True)
    building = models.CharField(max_length=15, verbose_name='Строение', blank=True)
    apartment = models.CharField(max_length=15, verbose_name='Квартира', blank=True)
    phone = models.CharField(max_length=20, verbose_name='Телефон')

    class Meta:
        verbose_name = 'Контакт'
        verbose_name_plural = 'Контакты'

    def __str__(self):
        return f"{self.city}, {self.street}, {self.house}"


class Order(models.Model):
    """
    Заказ
    """
    user = models.ForeignKey(
        User,
        verbose_name='Пользователь',
        related_name='orders',
        on_delete=models.CASCADE
    )
    dt = models.DateTimeField(auto_now_add=True, verbose_name='Дата заказа')
    state = models.CharField(
        verbose_name='Статус',
        choices=STATE_CHOICES,
        max_length=15,
        default='basket'
    )
    contact = models.ForeignKey(
        Contact,
        verbose_name='Контакт',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-dt']

    def __str__(self):
        return f"Заказ №{self.id} от {self.dt.strftime('%d.%m.%Y')}"


class OrderItem(models.Model):
    """
    Позиция заказа
    """
    order = models.ForeignKey(
        Order,
        verbose_name='Заказ',
        related_name='items',
        on_delete=models.CASCADE
    )
    product_info = models.ForeignKey(
        ProductInfo,
        verbose_name='Товар',
        related_name='order_items',
        on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(verbose_name='Количество')

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказа'
        constraints = [
            models.UniqueConstraint(
                fields=['order', 'product_info'],
                name='unique_order_item'
            )
        ]

    def __str__(self):
        return f"{self.product_info.product.name} - {self.quantity} шт."