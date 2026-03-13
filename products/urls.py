from django.urls import path
from .views import (
    ProductListView, ProductDetailView, CategoryListView,
    ShopListView, ProductByCategoryView
)

urlpatterns = [
    path('', ProductListView.as_view(), name='product-list'),
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('shops/', ShopListView.as_view(), name='shop-list'),
    path('by-category/', ProductByCategoryView.as_view(), name='products-by-category'),
    path('<int:product_id>/', ProductDetailView.as_view(), name='product-detail'),
]