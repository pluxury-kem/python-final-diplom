from django.contrib import admin
from .models import Contact, Order, OrderItem


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['user', 'city', 'street', 'house', 'phone']
    search_fields = ['user__email', 'city', 'phone']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product_info', 'quantity']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'dt', 'state', 'contact']
    list_filter = ['state']
    search_fields = ['user__email']
    readonly_fields = ['dt']
    inlines = [OrderItemInline]