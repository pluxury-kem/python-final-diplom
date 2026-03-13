from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_rest_passwordreset.tokens import get_token_generator

USER_TYPE_CHOICES = (
    ('shop', 'Магазин'),
    ('buyer', 'Покупатель'),
)


class UserManager(BaseUserManager):
    """
    Менеджер для управления пользователями
    """
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('Электронная почта должна быть указана')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Расширенная модель пользователя
    """
    REQUIRED_FIELDS = []
    objects = UserManager()

    USERNAME_FIELD = 'email'
    email = models.EmailField(_('email'), unique=True)

    username_validator = UnicodeUsernameValidator()
    username = models.CharField(
        _('Логин'),
        max_length=150,
        validators=[username_validator],
        blank=True,
        help_text=_("Обязательно. Не более 150 символов. Только буквы, цифры и @/./+/-/_"),
    )

    company = models.CharField(verbose_name='Компания', max_length=40, blank=True)
    position = models.CharField(verbose_name='Должность', max_length=40, blank=True)

    is_active = models.BooleanField(
        _('Активен'),
        default=False,
        help_text=_("Указание того, является ли пользователь активным"),
    )

    type = models.CharField(
        verbose_name="Тип пользователя",
        choices=USER_TYPE_CHOICES,
        max_length=5,
        default='buyer'
    )


    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = "Список пользователей"
        ordering = ('email',)


    def __str__(self):
        return f'{self.first_name} {self.last_name}' if self.first_name else self.email


class ConfirmEmailToken(models.Model):
    """
    Токен для подтверждения email
    """
    class Meta:
        verbose_name = "Токен подтверждения email"
        verbose_name_plural = "Токены подтверждения email"

    @staticmethod
    def generate_key():
        return get_token_generator().generate_token()

    user = models.ForeignKey(
        User,
        related_name='confirm_email_tokens',
        on_delete=models.CASCADE,
        verbose_name='Пользователь'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата генерации"
    )

    key = models.CharField(
        'Ключ',
        max_length=64,
        db_index=True,
        unique=True
    )

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Токен подтверждения для {self.user.email}"