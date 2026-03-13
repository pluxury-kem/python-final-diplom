# users/models.py (дополнение)

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_rest_passwordreset.tokens import get_token_generator

USER_TYPE_CHOICES = (
    ('shop', 'Магазин'),
    ('buyer', 'Покупатель'),
)


class UserManager(BaseUserManager):
    """
    Менеджер для создания пользователей
    """
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('Email должен быть указан')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('is_active', False)  # Требуется подтверждение email
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('type', 'shop')
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Модель пользователя
    """
    username = None  # Убираем поле username, используем email
    email = models.EmailField(_('email address'), unique=True)

    first_name = models.CharField(_('first name'), max_length=150, blank=True)
    last_name = models.CharField(_('last name'), max_length=150, blank=True)

    company = models.CharField(verbose_name='Компания', max_length=40, blank=True)
    position = models.CharField(verbose_name='Должность', max_length=40, blank=True)

    type = models.CharField(
        verbose_name='Тип пользователя',
        choices=USER_TYPE_CHOICES,
        max_length=5,
        default='buyer'
    )

    is_active = models.BooleanField(
        _('active'),
        default=False,  # По умолчанию неактивен до подтверждения email
        help_text=_('Активен ли пользователь (подтвердил email)')
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = "Список пользователей"
        ordering = ('email',)

    def __str__(self):
        return f"{self.email} ({self.get_type_display()})"


class ConfirmEmailToken(models.Model):
    """
    Токен для подтверждения email
    """
    user = models.ForeignKey(
        User,
        related_name='confirm_email_tokens',
        on_delete=models.CASCADE,
        verbose_name="Пользователь"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания"
    )

    key = models.CharField(
        "Ключ",
        max_length=64,
        db_index=True,
        unique=True
    )

    class Meta:
        verbose_name = 'Токен подтверждения Email'
        verbose_name_plural = 'Токены подтверждения Email'

    @staticmethod
    def generate_key():
        return get_token_generator().generate_token()

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Токен для {self.user.email}"