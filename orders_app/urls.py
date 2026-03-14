from django.urls import path
from .views import (
    ContactView, BasketView, OrderConfirmView,
    OrderListView, OrderDetailView, OrderStatusUpdateView
)

urlpatterns = [
    path('contacts/', ContactView.as_view(), name='contacts'),
    path('basket/', BasketView.as_view(), name='basket'),
    path('order/confirm/', OrderConfirmView.as_view(), name='order-confirm'),
    path('orders/', OrderListView.as_view(), name='orders-list'),
    path('orders/<int:order_id>/', OrderDetailView.as_view(), name='order-detail'),
    path('orders/<int:order_id>/status/', OrderStatusUpdateView.as_view(), name='order-status-update'),
]