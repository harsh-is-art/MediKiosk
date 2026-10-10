# Django URL Confi. Imports

from django.urls import path


# Local Application Imports

from . import views


# Application Namespace

app_name = 'kiosk'


# Kiosk URL Patterns

urlpatterns = [

    # Patient Session Start Endpoint

    path('session/start/', views.SessionStartView.as_view(), name='session-start'),

    # Patient Symptoms Submission Endpoint

    path('symptoms/', views.SymptomSubmitView.as_view(), name='symptoms'),

    # Patient Chat Endpoint

    path('chat/', views.ChatView.as_view(), name='chat'),

    # Patient Chat Streaming Endpoint (SSE)

    path('chat/stream/', views.ChatStreamView.as_view(), name='chat-stream'),

    # Automatic Speech Recognition Endpoint

    path('asr/', views.ASRView.as_view(), name='asr'),

    # Medical Document Upload Endpoint

    path('document/', views.DocumentUploadView.as_view(), name='document-upload'),

    # Patient Session Clinical Summary Endpoint

    path(
        'summary/<uuid:session_id>/',
        views.SessionSummaryView.as_view(),
        name='summary'
    ),
    path(
        'session/<uuid:session_id>/summary/',
        views.SessionSummaryView.as_view(),
        name='session-summary'
    ),

    # Active Patient Sessions Endpoint

    path(
        'sessions/active/',
        views.ActiveSessionsView.as_view(),
        name='active-sessions'
    ),

    # All Patient Sessions Endpoint

    path(
        'sessions/',
        views.AllSessionsView.as_view(),
        name='all-sessions'
    ),

    # Text-to-Speech Endpoint (Chatterbox / Sarvam AI)

    path('tts/', views.TTSView.as_view(), name='tts'),

    # Body Pointing Tracker Trigger Endpoint

    path('body-pointing/', views.TriggerBodyPointingView.as_view(), name='body-pointing'),

    # Health-Check Endpoints

    path('llm/health/', views.LLMHealthView.as_view(), name='llm-health'),
    path('tts/health/', views.TTSHealthView.as_view(), name='tts-health'),
    path('ocr/health/', views.OCRHealthView.as_view(), name='ocr-health'),
    path('sensor/health/', views.SensorHealthView.as_view(), name='sensor-health'),

    # Demo Sensor Trigger (synthetic vitals without hardware)

    path('sensor/trigger/', views.DemoSensorTriggerView.as_view(), name='sensor-trigger'),

    # Latest Vitals Endpoint

    path('vitals/latest/<uuid:session_id>/', views.LatestVitalsView.as_view(), name='latest-vitals'),

    # =====================================================================
    # V1: STRUCTURED HISTORY & REGIONS ENDPOINTS
    # =====================================================================

    path('session/<uuid:session_id>/history/', views.StructuredHistoryView.as_view(), name='session-history'),
    path('session/<uuid:session_id>/history/update/', views.StructuredHistoryUpdateView.as_view(), name='session-history-update'),
    path('body-pointing/regions/', views.BodyPointingRegionsView.as_view(), name='body-pointing-regions'),

    # =====================================================================
    # V2: DOCUMENT INTELLIGENCE ENDPOINTS
    # =====================================================================

    path('document/upload/', views.DocumentUploadPipelineView.as_view(), name='document-pipeline-upload'),
    path('document/<uuid:document_id>/', views.MedicalDocumentDetailView.as_view(), name='document-detail'),
    path('document/<uuid:document_id>/fields/', views.DocumentFieldsListView.as_view(), name='document-fields-list'),
    path('document/<uuid:document_id>/field/<int:field_id>/verify/', views.VerifyDocumentFieldView.as_view(), name='document-field-verify'),
    path('document/<uuid:document_id>/field/<int:field_id>/reject/', views.RejectDocumentFieldView.as_view(), name='document-field-reject'),
    path('document/session/<uuid:session_id>/', views.SessionMedicalDocumentsView.as_view(), name='session-documents'),
]