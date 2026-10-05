from collections.abc import Mapping

from rest_framework import serializers


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            extra = set(data) - set(self.fields)
            if extra:
                raise serializers.ValidationError(
                    {key: "Неизвестное поле." for key in sorted(extra)}
                )
        return super().to_internal_value(data)


class ListQuery(StrictSerializer):
    limit = serializers.IntegerField(min_value=1, max_value=100, default=50)
    offset = serializers.IntegerField(min_value=0, default=0)


def validated(serializer_class, data):
    serializer = serializer_class(data=data)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data
