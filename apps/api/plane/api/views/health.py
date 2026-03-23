"""
SpecFlow Health Check Endpoint
"""

from django.http import JsonResponse
from django.views import View
from django.db import connection
from django.core.cache import cache
from redis import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from plane.config.branding import APP_NAME, VERSION


class HealthCheckView(View):
    """Health check endpoint for container orchestration."""
    
    def get(self, request):
        status = {
            "status": "healthy",
            "app": APP_NAME,
            "version": VERSION,
            "checks": {}
        }
        
        # Check database
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            status["checks"]["database"] = "ok"
        except Exception as e:
            status["checks"]["database"] = f"error: {str(e)}"
            status["status"] = "degraded"
        
        # Check Redis
        try:
            cache.set("health_check", "ok", 10)
            status["checks"]["redis"] = "ok"
        except RedisConnectionError as e:
            status["checks"]["redis"] = f"error: {str(e)}"
            status["status"] = "degraded"
        except Exception as e:
            status["checks"]["redis"] = f"error: {str(e)}"
            status["status"] = "degraded"
        
        http_status = 200 if status["status"] == "healthy" else 503
        
        return JsonResponse(status, status=http_status)


health_check = HealthCheckView.as_view()