from django.contrib import admin
from .models import User, ConfirmEmailToken

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'type', 'is_active')
    list_filter = ('type', 'is_active')
    search_fields = ('email', 'first_name', 'last_name')

@admin.register(ConfirmEmailToken)
class ConfirmEmailTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'key', 'created_at')