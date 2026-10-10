# Django URL Confi. Imports

from django.urls import path

# Local Project Imports

from . import views


# Application Namespace

app_name = 'doctor'


# Doctor URL Patterns

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('api/notes/', views.DoctorNoteCreateView.as_view(), name='create-note'),
    path('api/session/<uuid:session_id>/review/', views.MarkSessionReviewedView.as_view(), name='review-session'),
    path('api/session/<uuid:session_id>/summarize-consultation/', views.DoctorConsultationSummarizeView.as_view(), name='summarize-consultation'),
]