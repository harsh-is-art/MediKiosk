from django.urls import path
from . import views

app_name = 'terminology'

urlpatterns = [
    path('map/', views.TerminologyMapView.as_view(), name='terminology-map'),
    path('search/', views.TerminologySearchView.as_view(), name='terminology-search'),
    path('session/<uuid:session_id>/', views.SessionTerminologyView.as_view(), name='session-terminology'),
    path('mapping/<int:mapping_id>/confirm/', views.ConfirmMappingView.as_view(), name='confirm-mapping'),
]
