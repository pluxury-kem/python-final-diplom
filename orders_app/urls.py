from django.urls import path
from .views import (
    ContactView, BasketView, OrderConfirmView, OrderListView
)

urlpatterns = [
    path('contacts/', ContactView.as_view(), name='contacts'),
    path('basket/', BasketView.as_view(), name='basket'),
    path('order/confirm/', OrderConfirmView.as_view(), name='order-confirm'),
    path('orders/', OrderListView.as_view(), name='orders-list'),
]