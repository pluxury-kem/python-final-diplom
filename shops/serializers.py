from rest_framework import serializers
from shops.models import Shop


class PartnerUpdateSerializer(serializers.Serializer):
    """
    Сериализатор для обновления прайса поставщика
    """
    url = serializers.URLField(help_text="Ссылка на YAML файл с прайс-листом")


    class Meta:
        fields = ['url']