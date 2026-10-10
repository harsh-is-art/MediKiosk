# Django URL Confi. Imports

from django.urls import path


# Local Application Imports

from . import views

# Application Namespace

app_name = 'medicines'


# Medicine URL Patterns

urlpatterns = [

    # Medicine List Endpoint

    path('', views.MedicineListView.as_view(), name='medicine-list'),

    # Medicine Search Endpoint

    path('search/', views.MedicineSearchView.as_view(), name='medicine-search'),

]