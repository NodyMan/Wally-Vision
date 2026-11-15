from rest_framework import serializers

from .models import Finding


class FindingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Finding
        fields = ["id", "ra", "dec", "note", "nickname", "created_at", "status"]
        read_only_fields = ["id", "created_at", "status"]

    def validate_note(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Note cannot be empty.")
        if len(cleaned) > 500:
            raise serializers.ValidationError("Note must be 500 characters or fewer.")
        return cleaned

    def validate_nickname(self, value: str) -> str:
        return value.strip()[:80]
