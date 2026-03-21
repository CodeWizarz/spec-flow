from rest_framework import serializers
from plane.signals.models import Signal

class SignalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Signal
        fields = [
            "id",
            "workspace",
            "title",
            "content",
            "file",
            "source",
            "processing_status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "workspace",
            "processing_status",
            "created_at",
            "updated_at",
        ]
