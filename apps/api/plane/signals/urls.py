from django.urls import path
from plane.signals.views import WorkspaceSignalViewSet

signal_list = WorkspaceSignalViewSet.as_view({
    'get': 'list',
    'post': 'create'
})

signal_detail = WorkspaceSignalViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

urlpatterns = [
    path("api/workspaces/<slug:slug>/signals/", signal_list, name="workspace-signals"),
    path("api/workspaces/<slug:slug>/signals/<uuid:pk>/", signal_detail, name="workspace-signal-detail"),
]
