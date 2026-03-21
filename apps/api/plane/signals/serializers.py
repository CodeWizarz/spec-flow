from rest_framework import serializers
from plane.signals.models import Signal, Insight

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

class InsightSerializer(serializers.ModelSerializer):
    class Meta:
        model = Insight
        fields = [
            "id",
            "workspace",
            "theme",
            "problem",
            "root_cause",
            "evidence",
            "frequency",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "workspace",
            "created_at",
            "updated_at",
        ]
