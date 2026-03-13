from django.http import JsonResponse
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import TokenAuthentication
from .models import User, ConfirmEmailToken
from .serializers import (
    RegisterSerializer, ConfirmEmailSerializer,
    LoginSerializer, UserSerializer
)


class RegisterView(APIView):
    """
    Регистрация нового пользователя
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            return JsonResponse({
                'Status': True,
                'Message': 'Пользователь создан. Проверьте email для подтверждения.',
                'user': {
                    'email': user.email,
                    'type': user.type
                }
            }, status=201)

        return JsonResponse({
            'Status': False,
            'Errors': serializer.errors
        }, status=400)


class ConfirmEmailView(APIView):
    """
    Подтверждение email по токену
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ConfirmEmailSerializer(data=request.data)
        if serializer.is_valid():
            token = serializer.validated_data['token']

            # Активируем пользователя
            user = token.user
            user.is_active = True
            user.save()

            # Удаляем использованный токен
            token.delete()

            return JsonResponse({
                'Status': True,
                'Message': 'Email успешно подтвержден. Теперь вы можете войти.'
            })

        return JsonResponse({
            'Status': False,
            'Errors': serializer.errors
        }, status=400)


class LoginView(APIView):
    """
    Авторизация пользователя
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']

            # Аутентификация пользователя
            user = authenticate(request, username=email, password=password)

            if user is None:
                return JsonResponse({
                    'Status': False,
                    'Error': 'Неверный email или пароль'
                }, status=401)

            if not user.is_active:
                return JsonResponse({
                    'Status': False,
                    'Error': 'Email не подтвержден. Проверьте почту.'
                }, status=401)

            # Создаем или получаем токен
            token, _ = Token.objects.get_or_create(user=user)

            return JsonResponse({
                'Status': True,
                'Token': token.key,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'type': user.type
                }
            })

        return JsonResponse({
            'Status': False,
            'Errors': serializer.errors
        }, status=400)


class ProfileView(APIView):
    """
    Просмотр и редактирование профиля
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Получение информации о текущем пользователе"""
        serializer = UserSerializer(request.user)
        return JsonResponse({
            'Status': True,
            'user': serializer.data
        })

    def post(self, request):
        """Обновление профиля"""
        serializer = UserSerializer(
            request.user,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return JsonResponse({
                'Status': True,
                'user': serializer.data
            })

        return JsonResponse({
            'Status': False,
            'Errors': serializer.errors
        }, status=400)


class LogoutView(APIView):
    """
    Выход из системы (удаление токена)
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Удаляем токен пользователя
        request.user.auth_token.delete()
        return JsonResponse({
            'Status': True,
            'Message': 'Вы успешно вышли из системы'
        })