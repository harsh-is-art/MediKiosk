# Application URL Routing Definition

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """GET /api/health/ — Basic system health check and V1/V2 subsystem status."""
    return Response({
        'status': 'healthy',
        'application': 'MediKiosk Smart Patient Intake Backend',
        'environment': 'development' if settings.DEBUG else 'production',
        'privacy_mode': getattr(settings, 'MEDIKIOSK_PRIVACY_MODE', False),
        'terminology_services': {
            'icd11': 'ready',
            'snomed_ct': 'ready',
            'loinc': 'ready',
        },
        'document_pipeline': {
            'status': 'ready',
            'confidence_threshold': getattr(settings, 'DOCUMENT_CONFIDENCE_THRESHOLD', 0.75),
        }
    }, status=status.HTTP_200_OK)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check, name='health-check'),
    path('api/', include('kiosk.urls')),
    path('api/vitals/', include('sensors.urls')),
    path('api/medicines/', include('medicines.urls')),
    path('api/terminology/', include('terminology.urls')),
    path('doctor/', include('doctor.urls')),
    # Serve kiosk SPA at root
    path('', TemplateView.as_view(template_name='kiosk/index.html'), name='kiosk-home'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / 'static')
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

