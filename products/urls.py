from django.urls import path
from .views import ProductListView, ShopListView

urlpatterns = [
    path('', ProductListView.as_view(), name='product-list'),
    path('shops/', ShopListView.as_view(), name='shop-list'),
]