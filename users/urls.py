from django.urls import path
from .views import (
    RegisterView, ConfirmEmailView, LoginView,
    ProfileView, LogoutView
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('confirm/', ConfirmEmailView.as_view(), name='confirm-email'),
    path('login/', LoginView.as_view(), name='login'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('logout/', LogoutView.as_view(), name='logout'),
]