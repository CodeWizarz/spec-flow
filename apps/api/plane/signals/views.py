from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated
from plane.signals.models import Signal
from plane.signals.serializers import SignalSerializer
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
