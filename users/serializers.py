from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.mail import send_mail
from django.conf import settings
from .models import User, ConfirmEmailToken


class RegisterSerializer(serializers.ModelSerializer):
    """
    Сериализатор для регистрации пользователя
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ('email', 'password', 'password2', 'first_name',
                  'last_name', 'company', 'position', 'type')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError(
                {"password": "Пароли не совпадают"}
            )
        return attrs

    def create(self, validated_data):
        # Удаляем password2 из данных
        validated_data.pop('password2')

        # Создаем пользователя
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            company=validated_data.get('company', ''),
            position=validated_data.get('position', ''),
            type=validated_data.get('type', 'buyer')
        )

        # Создаем токен подтверждения
        token = ConfirmEmailToken.objects.create(user=user)

        # Отправляем email с токеном
        self.send_confirmation_email(user, token)

        return user

    def send_confirmation_email(self, user, token):
        """Отправка письма с подтверждением регистрации"""
        subject = "Подтверждение регистрации"
        message = f"""
        Здравствуйте, {user.email}!

        Для подтверждения регистрации перейдите по ссылке:
        http://localhost:8000/api/v1/users/confirm/?token={token.key}

        Спасибо за регистрацию!
        """

        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER or 'noreply@shop.local',
            [user.email],
            fail_silently=False,
        )


class ConfirmEmailSerializer(serializers.Serializer):
    """
    Сериализатор для подтверждения email
    """
    token = serializers.CharField(required=True)

    def validate_token(self, value):
        try:
            token = ConfirmEmailToken.objects.get(key=value)
        except ConfirmEmailToken.DoesNotExist:
            raise serializers.ValidationError("Неверный токен")

        # Проверяем, не истек ли токен (например, через 48 часов)
        from django.utils import timezone
        from datetime import timedelta

        if timezone.now() - token.created_at > timedelta(hours=48):
            token.delete()
            raise serializers.ValidationError("Токен истек")

        return token


class LoginSerializer(serializers.Serializer):
    """
    Сериализатор для входа
    """
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True,
        style={'input_type': 'password'},
        write_only=True
    )


class UserSerializer(serializers.ModelSerializer):
    """
    Сериализатор для получения информации о пользователе
    """

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name',
                  'company', 'position', 'type', 'is_active')
        read_only_fields = ('id', 'is_active')