from django.urls import path
from plane.signals.views import WorkspaceSignalViewSet, WorkspaceInsightViewSet

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

signal_generate = WorkspaceSignalViewSet.as_view({
    'post': 'generate'
})

insight_list = WorkspaceInsightViewSet.as_view({
    'get': 'list',
    'post': 'create'
})

insight_detail = WorkspaceInsightViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})

urlpatterns = [
    path("api/workspaces/<slug:slug>/signals/", signal_list, name="workspace-signals"),
    path("api/workspaces/<slug:slug>/signals/<uuid:pk>/", signal_detail, name="workspace-signal-detail"),
    path("api/workspaces/<slug:slug>/signals/generate/", signal_generate, name="workspace-signal-generate"),
    path("api/workspaces/<slug:slug>/insights/", insight_list, name="workspace-insights"),
    path("api/workspaces/<slug:slug>/insights/<uuid:pk>/", insight_detail, name="workspace-insight-detail"),
]
