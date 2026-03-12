from django.contrib import admin
from .models import Shop

@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'state')
    list_filter = ('state',)
    search_fields = ('name',)