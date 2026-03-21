from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from plane.signals.models import Signal, Insight, GeneratedSpec
from plane.signals.serializers import SignalSerializer, InsightSerializer, GeneratedSpecSerializer
from plane.db.models import Workspace
from plane.bgtasks.signals_tasks import process_signal_file_task
from django.shortcuts import get_object_or_404

class WorkspaceSignalViewSet(viewsets.ModelViewSet):
    serializer_class = SignalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Signal.objects.filter(workspace__slug=self.kwargs.get("slug"))

    def perform_create(self, serializer):
        workspace = get_object_or_404(Workspace, slug=self.kwargs.get("slug"))
        instance = serializer.save(workspace=workspace)
        
        # If a file is uploaded, dispatch to background task
        if instance.file:
            process_signal_file_task.delay(instance.id)

    @action(detail=False, methods=['post'])
    def generate(self, request, slug):
        workspace = get_object_or_404(Workspace, slug=slug)
        generate_insights_task.delay(workspace.id)
        return Response({"message": "Insights generation queued"})

class WorkspaceInsightViewSet(viewsets.ModelViewSet):
    serializer_class = InsightSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Insight.objects.filter(workspace__slug=self.kwargs.get("slug"))

class WorkspaceSpecViewSet(viewsets.ModelViewSet):
    serializer_class = GeneratedSpecSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return GeneratedSpec.objects.filter(workspace__slug=self.kwargs.get("slug"))

    @action(detail=False, methods=['post'])
    def generate(self, request, slug):
        from plane.db.models import Workspace
        from plane.bgtasks.signals_tasks import generate_spec_task
        from django.shortcuts import get_object_or_404
        workspace = get_object_or_404(Workspace, slug=slug)
        insight_ids = request.data.get("insight_ids", None)
        generate_spec_task.delay(workspace.id, insight_ids)
        return Response({"message": "Spec generation queued"})
