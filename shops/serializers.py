from rest_framework import serializers


class PartnerUpdateSerializer(serializers.Serializer):
    """
    Сериализатор для обновления прайса поставщика
    """
    url = serializers.URLField(
        required=True,
        help_text="Ссылка на YAML файл с прайс-листом"
    )

    def validate_url(self, value):
        """Дополнительная валидация URL"""
        allowed_domains = ['github.com', 'raw.githubusercontent.com', 'drive.google.com']
        if not any(domain in value for domain in allowed_domains):
            raise serializers.ValidationError("URL должен быть с доверенного домена")
        return value