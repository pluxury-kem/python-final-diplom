from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    #API эндпоинты
    path('api/v1/shops/', include('shops.urls')),
    path('api/v1/products/', include('products.urls')),
    path('api/v1/users/', include('users.urls')),
    #path('api/v1/orders/', include('orders.urls')),

    path('api-auth', include('rest_framework.urls'))
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)