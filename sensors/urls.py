# Django URL Confi. Imports

from django.urls import path


# Local Application Imports

from . import views


# Application Namespace

app_name = 'sensors'


# Sensor URL Patterns

urlpatterns = [
    path(
        'post/',
        views.VitalsPostView.as_view(),
        name='vitals-post'
    ),
    
    path(
        'latest/<uuid:session_id>/',
        views.LatestVitalsView.as_view(),
        name='vitals-latest'
    ),
    path(
        'flagged/<uuid:session_id>/',
        views.FlaggedVitalsView.as_view(),
        name='vitals-flagged'
    ),
]