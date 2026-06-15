from rest_framework import serializers

from catalog.models import Game, Genre, Platform


class GenreSerializer(serializers.ModelSerializer):
    """
    Serializer for Genre reference data.
    """

    class Meta:
        model = Genre
        fields = ("id", "name", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_name(self, value):
        normalized = " ".join(value.split())

        qs = Genre.objects.filter(name__iexact=normalized)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError(
                "Genre with this name already exists.",
                code="unique",
            )

        return normalized


class PlatformSerializer(serializers.ModelSerializer):
    """
    Serializer for Genre reference data.
    """

    class Meta:
        model = Platform
        fields = ("id", "name", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_name(self, value):
        normalized = " ".join(value.split())

        qs = Platform.objects.filter(name__iexact=normalized)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError(
                "Platform with this name already exists.",
                code="unique",
            )

        return normalized


class GameSerializer(serializers.ModelSerializer):
    """
    Serializer for Games
    """

    class Meta:
        model = Game
        fields = (
            "id",
            "title",
            "description",
            "release_date",
            "genre",
            "platforms",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_title(self, value):
        normalized = " ".join(value.split())

        qs = Game.objects.filter(title__iexact=normalized)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError(
                "Game with this name already exists.",
                code="unique",
            )

        return normalized
